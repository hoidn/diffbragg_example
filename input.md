# Input for Ralph — ARCH-REFINE-FLOW-001 Phase C2.2 CPU Fallback Gradient Fix (Warm Cache Hypothesis)

## Summary
Apply one-line fix to disable warm cache simulator reuse for CPU fallback, forcing fresh simulator creation with gradient-enabled HKL data.

## Mode
none (targeted bugfix with validation)

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2.2 CPU fallback gradient fix — warm cache hypothesis)

## Branch
integration

## Mapped Tests
- `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (full detector, CPU fallback validation)
- `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers_small_detector` (small detector, CUDA warm cache regression guard)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/`

## Context & Root Cause Analysis

### What Ralph Discovered (Loop i=216)
Excellent diagnostic work! You proved:
1. ✅ **Device fix is working**: Parameters ARE on CPU (`shell_modifier_raw_device="cpu"`)
2. ✅ **Gradient is present**: `shell_modifiers.requires_grad=true`, `grad_fn` exists
3. ❌ **But backward() still fails**: "element 0 of tensors does not require grad and does not have a grad_fn"

**Key Insight from Your Blocker:** The gradient chain is intact up to `shell_modifiers`, but breaks somewhere between there and `chi_squared_loss`. This suggests the issue is NOT in parameter creation (your fix works!) but in how the **modified HKL data propagates through the simulator**.

### New Root Cause Hypothesis (85% confidence)
**The problem is WARM CACHE simulator reuse with post-creation HKL data updates.**

**Evidence:**
1. **Warm cache is active** (telemetry shows `cache_mode='warm'`)
2. **Warm path reuses Stage A simulators** (line 2450: `use_warm_eval = stage_b_use_warm_cache`)
3. **HKL data updated AFTER simulator creation** (line 2469: `warm_crystal_model.hkl_data = hkl_grid_modified`)
4. **nanobrag_torch may cache HKL data internally** (black box, but likely given the failure pattern)

**Why this breaks gradients:**
- Simulators created in Stage A with original `hkl_grid` (no gradients, different device)
- Stage B updates `crystal.hkl_data` to `hkl_grid_modified` (CPU, gradient-enabled)
- Simulator's internal cache doesn't see the update → gradient chain broken → backward() fails

**Why cold path would work:**
- Creates NEW simulators with `hkl_grid_modified` from the start (line 2547)
- Simulator initialized with gradient-enabled HKL data → gradients flow through → backward() succeeds

**Full analysis:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/root_cause_hypothesis.md`

## Do Now

### Step 1: Review Root Cause Hypothesis
Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/root_cause_hypothesis.md` (Galph's RCA based on your diagnostic work).

### Step 2: Apply One-Line Fix
**File:** `dbex/nanobrag_refinement.py`
**Line:** 2450
**Change:** Disable warm cache when CPU fallback is active

```python
# BEFORE:
use_warm_eval = stage_b_use_warm_cache

# AFTER:
use_warm_eval = stage_b_use_warm_cache and not use_stage_b_cpu_fallback
```

**Rationale:** Forces COLD PATH (fresh simulator creation) when CPU fallback active, preserving gradient flow through HKL data.

### Step 3: Run Full Detector Test (CPU Fallback Validation)
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=full \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/pytest_stage_b_full_fixed.log 2>&1
echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/pytest_stage_b_full_fixed.log
```

**Expected:** PASS, telemetry shows `cache_mode='cold'`, `status='ok'`, `closure_evals > 1`

### Step 4: Run Small Detector Test (Regression Guard)
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers_small_detector \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/pytest_stage_b_small_regression.log 2>&1
echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/pytest_stage_b_small_regression.log
```

**Expected:** PASS, telemetry shows `cache_mode='warm'` (small detector uses CUDA, no CPU fallback, warm cache preserved)

### Step 5: Extract Validation Metrics (T0 Micro Probe)
```bash
python3 -c "
import re, json

# Parse full detector test
with open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/pytest_stage_b_full_fixed.log') as f:
    full_log = f.read()
full_exit_code = int(re.search(r'Exit code: (\d+)', full_log).group(1))
full_cache_mode = re.search(r\"'cache_mode': '(\w+)'\", full_log)
full_status = re.search(r\"'status': '(\w+)'\", full_log)
full_closure_evals = re.search(r\"'closure_evals': (\d+)\", full_log)

# Parse small detector test
with open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/pytest_stage_b_small_regression.log') as f:
    small_log = f.read()
small_exit_code = int(re.search(r'Exit code: (\d+)', small_log).group(1))
small_cache_mode = re.search(r\"'cache_mode': '(\w+)'\", small_log)

metrics = {
    'full_detector': {
        'exit_code': full_exit_code,
        'cache_mode': full_cache_mode.group(1) if full_cache_mode else 'UNKNOWN',
        'status': full_status.group(1) if full_status else 'UNKNOWN',
        'closure_evals': int(full_closure_evals.group(1)) if full_closure_evals else 0,
        'verdict': 'PASS' if full_exit_code == 0 else 'FAIL'
    },
    'small_detector': {
        'exit_code': small_exit_code,
        'cache_mode': small_cache_mode.group(1) if small_cache_mode else 'UNKNOWN',
        'verdict': 'PASS' if small_exit_code == 0 else 'FAIL'
    },
    'overall_verdict': 'PASS' if full_exit_code == 0 and small_exit_code == 0 else 'FAIL'
}

with open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/validation_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print(json.dumps(metrics, indent=2))
" > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/metrics_summary.txt 2>&1
cat plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/validation_metrics.json
```

### Step 6: Decision Synthesis (4-Path Template)
Based on validation metrics, follow decision tree:

**Path A: Both Tests PASS**
- Verdict: CPU fallback gradient bug FIXED ✅
- Next: Remove instrumentation (Step 7), update docs (Step 8), commit (Step 9)
- Expected cache modes: full=cold, small=warm (confirms fix working correctly)

**Path B: Full FAIL, Small PASS**
- Verdict: Warm cache hypothesis INCOMPLETE (cold path also broken)
- Action: Write `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/blocker_path_b.md`
- Content: Document full detector failure signature, compare with loop i=216 error, note that cold path doesn't fix it
- Escalation: Likely nanobrag_torch internal issue (`.no_grad()` or `.detach()` in `run()`)
- DO NOT remove instrumentation, DO NOT update implementation.md

**Path C: Full PASS, Small FAIL**
- Verdict: Regression introduced (warm cache broken for CUDA)
- Action: REVERT the one-line fix immediately
- Write `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/blocker_path_c.md`
- Escalation: Hypothesis was wrong, or fix has unintended side effect

**Path D: Both FAIL**
- Verdict: Fix did not address root cause
- Action: REVERT the one-line fix
- Write `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/blocker_path_d.md`
- Escalation: Back to drawing board, may need nanobrag_torch inspection or different architecture

### Step 7: Remove Instrumentation (ONLY IF PATH A)
**Condition:** Execute ONLY if `overall_verdict='PASS'` from Step 5.

**File:** `dbex/nanobrag_refinement.py`
**Remove:**
1. Lines 2185-2198 (CPU fallback diagnostic print in `_build_stage_b_params`)
2. Lines 2389-2405 (CPU fallback diagnostic print in closure)

**Verification:** `git diff dbex/nanobrag_refinement.py` shows ONLY:
- One-line fix at line 2450 (warm cache disable)
- Two instrumentation block removals
- No other changes

### Step 8: Update Implementation Plan (ONLY IF PATH A)
**Condition:** Execute ONLY if `overall_verdict='PASS'`.

**File:** `plans/active/ARCH-REFINE-FLOW-001/implementation.md`
**Update:** Mark Phase C2.2 as COMPLETE with completion timestamp and artifacts path.

```markdown
### Phase C2.2: CPU Fallback Gradient Fix ✅ COMPLETE (2025-11-23T104525Z)
**Goal:** Fix Stage B CPU fallback gradient computation bug causing "element 0 of tensors does not require grad" error.

**Root Cause:** Warm cache simulator reuse with post-creation HKL data updates broke gradient flow. nanobrag_torch simulators cache HKL data internally when created; updating `crystal.hkl_data` later doesn't propagate gradient-enabled tensor.

**Fix Applied:** Disabled warm cache for CPU fallback (`use_warm_eval = stage_b_use_warm_cache and not use_stage_b_cpu_fallback` at line 2450), forcing fresh simulator creation with gradient-enabled HKL data.

**Validation:** Full detector test PASS (`cache_mode='cold'`, gradient flow preserved), small detector test PASS (`cache_mode='warm'`, no regression).

**Performance Impact:** Full detector Stage B closures slower (~2-3x) due to cold path, acceptable for correctness. Future optimization: Investigate nanobrag_torch HKL update API.

**Artifacts:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/`
```

### Step 9: Write Summary & Decision Document
**File:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/decision.md`

Include:
- Decision path taken (A/B/C/D)
- Test outcomes (exit codes, cache modes, status, closure_evals)
- Metrics summary (from Step 5 JSON)
- Confidence assessment (if Path A: HIGH ~90%, root cause validated)
- Next actions (if Path A: Phase C validation suite; if B/C/D: escalation details)

**AND** include Turn Summary block:
```markdown
### Turn Summary
Fixed CPU fallback gradient bug by disabling warm cache simulator reuse, forcing fresh creation with gradient-enabled HKL data.
Full detector test PASSES with cold cache (correctness achieved), small detector PASSES with warm cache (no regression).
Next: Run Phase C validation suite (Stage B small+full smoke, DB-AT-024 parity, telemetry completeness check).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/ (pytest logs, metrics, RCA)
```

(Adjust summary if not Path A.)

### Step 10: Commit & Push
```bash
git add -A
git commit -m "ARCH-REFINE-FLOW-001 Phase C2.2: fix CPU fallback gradient bug — disable warm cache for fresh simulators

- Root cause: Warm cache reuses Stage A simulators; updating crystal.hkl_data
  post-creation doesn't propagate gradient-enabled tensor through nanobrag_torch
  simulator's internal HKL cache
- Fix: Disable warm cache when use_stage_b_cpu_fallback=True (line 2450)
  forces cold path (fresh simulator creation with hkl_grid_modified)
- Validation: Full detector PASS (cache_mode=cold, gradient preserved),
  small detector PASS (cache_mode=warm, no regression)
- Performance: Full detector Stage B slower (~2-3x), acceptable for correctness
- Removed diagnostic instrumentation (lines 2185-2198, 2389-2405)
- Phase C2.2 COMPLETE

Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/
Tests: test_stage_b_shell_modifiers (full+small detector)"

git push
```

**Note:** If not Path A, commit message should describe the blocker and next steps instead.

## How-To Map

All commands above are copy-paste ready. Sequence:
1. Read RCA → 2. Edit line 2450 → 3-4. Run tests → 5. Extract metrics → 6. Decision tree → 7-10. Path A actions (or blocker docs for B/C/D)

## Pitfalls To Avoid

1. **DO NOT remove instrumentation if tests FAIL** — Keep diagnostics for further investigation
2. **DO NOT modify other warm cache logic** — Only change line 2450, affects ONLY CPU fallback path
3. **DO NOT disable warm cache unconditionally** — Condition on `use_stage_b_cpu_fallback`, preserves performance for CUDA
4. **VERIFY cache modes in telemetry** — Full should be 'cold', small should be 'warm' (confirms fix working correctly)
5. **DO NOT skip small detector test** — Regression guard is critical to prove no side effects
6. **Environment Freeze** — Do not install packages; if imports fail, document in blocker
7. **Protected Assets** — Preserve loop i=215 device routing fix (lines 2753-2943, 3115-3143), preserve loop i=216 device-aware parameter init (line 2144)

## If Blocked

If any test FAILS:
1. DO NOT proceed past Step 6
2. Follow decision tree Path B/C/D
3. Write blocker document in artifacts directory
4. Include: exact error message, telemetry excerpt, cache_mode observed, comparison with loop i=216 failure
5. REVERT code changes if Path C or D
6. Commit blocker artifacts and updated summary.md
7. Do NOT update implementation.md or remove instrumentation

## Findings Applied

- **PERF-WARM-011** (CPU fallback requirement): Fix preserves this by keeping `use_stage_b_cpu_fallback` logic intact
- **PERF-WARM-012** (CPU context cloning): Fix doesn't affect context cloning, only warm cache decision
- **GRADIENT-001** (autograd graph preservation): Fix addresses this by ensuring HKL data with gradients flows through simulator
- **POLICY-001** (Environment Freeze): No package installs, frozen runtime
- **RUNTIME-001/CONFORMANCE-001** (test env flags): Use authoritative test command format from TESTING_GUIDE.md

**New Finding (if Path A succeeds):**
**PERF-WARM-013**: "Warm cache simulators with post-creation HKL data updates break PyTorch autograd gradient flow. When refining shell modifiers (Stage B), disable warm cache if HKL grid is modified after simulator creation. Forces fresh simulator creation with gradient-enabled HKL data. Affects CPU fallback; CUDA path may work (device-specific nanobrag behavior, unverified black box)."

## Pointers

- Root Cause Hypothesis: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/root_cause_hypothesis.md`
- Loop i=216 Blocker: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/blocker.md`
- Loop i=215 Device Fix: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/`
- Implementation Plan: `plans/active/ARCH-REFINE-FLOW-001/implementation.md`
- Spec References: `docs/spec-db-workflow.md` §7 (Stage B shell modifiers), `docs/spec-db-runtime.md` §2 (gradient flow preservation)

## Next Up (If Path A Succeeds)

Phase C Validation Suite (likely next Galph loop):
1. **C3:** DB-AT-024 mapping parity with CPU fallback (verify forward model unchanged)
2. **C4:** Stage B smoke suite (small+full detector, both warm+cold cache combinations)
3. **C5:** Telemetry completeness check (all metrics populated, no missing keys)
4. **C6:** Update TESTING_GUIDE.md and TEST_SUITE_INDEX.md with Stage B CPU fallback selectors

After Phase C validation → Mark ARCH-REFINE-FLOW-001 Phase C COMPLETE → Plan Phase D (Stage C detector refinement) or pivot to next Tier 2 initiative per roadmap.
