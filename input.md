# Input — TORCH-GEOMETRY-CONVERGENCE-001 Phase C4 First Closure Parameter Staleness Audit

## Summary
Audit first U-matrix closure evaluation for log_scale parameter staleness bug after Phase C3 confirmed catastrophic chi²=8.8M BEFORE first optimizer.step().

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` — Regression guard
- Evidence-only (no new test nodes until fix implemented)

## Artifacts
`plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232000Z/`

## Do Now

**CRITICAL FINDING (Phase C3):** Parameter lifecycle diagnostic proved catastrophic chi²=8.8M occurs **BEFORE** first optimizer.step(), NOT after. Pattern matches Phase B5 code path discrepancy (crystal_overrides["A_star"] bypassed MOSFLM tuple).

**Evidence:**
- chi² BEFORE step 0: 8,837,164 (catastrophic)
- chi² AFTER step 0: 8,837,085 (essentially unchanged, -79 = -0.0009%)
- Δlog_scale: +1e-5 (wrong direction AND magnitude)
- Expected Δ: -1.5 (from -LR × gradient)
- **Interpretation:** Forward model uses STALE log_scale (or other stale parameter) during FIRST closure call

**Phase C3 Verdict:** **Path C CONFIRMED** (forward model parameter staleness) with HIGH confidence (~90%)

**Root Cause Hypothesis:** Similar to Phase B5's B_ideal mismatch, there's a code path where:
1. Parameters (log_scale, q_params) are correctly initialized at zero-point
2. But when the first closure runs, the forward model uses DIFFERENT (stale or default) parameter values
3. This causes chi² to jump to 8.8M during first closure evaluation
4. The optimizer then tries to recover but can't (parameter update is only +1e-5 instead of -1.5)

### Step 1: Review Phase C3 Evidence
- **Read:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/phase_c3_parameter_lifecycle_decision.md`
- **Confirm:** Path C verdict (forward model staleness) with detailed lifecycle metrics
- **Note:** Zero-point validation continues to PASS (chi²=989k, correlation=1.0) while first closure is catastrophic

### Step 2: Audit First Closure U-Matrix/A* Derivation

**Target:** `dbex/nanobrag_refinement.py` — Stage A closure (U-matrix branch, lines ~966-1116)

**Checklist (Priority 1 from phase_c3_parameter_lifecycle_decision.md §Recommended Next Actions):**

1. **Verify log_scale tensor is SAME object:**
   - Locate log_scale_param definition (line ~925: `log_scale_param = torch.tensor(...)`)
   - Trace into closure: does closure use `log_scale_param` or a DIFFERENT tensor?
   - Check for `.clone()`, `.detach()`, or reassignment inside closure
   - **Expected:** Closure should compute `scale = torch.exp(log_scale_param)` directly

2. **Verify q_params tensor is SAME object:**
   - Locate q_params definition (line ~920: `q_params = torch.tensor(...)`)
   - Trace into closure: does quaternion_to_matrix use the CORRECT q_params?
   - Check for stale q_params_0 or default quaternion [1,0,0,0]
   - **Expected:** Closure should normalize THEN convert: `U = quaternion_to_matrix(q_params / ||q_params||)`

3. **Audit U-matrix derivation in first closure:**
   - Locate U-matrix computation in closure (line ~987: `U = quaternion_to_matrix(...)`)
   - Verify quaternion_to_matrix receives `q_params` (not q_params_0)
   - Verify normalization: `q_normed = q_params / torch.norm(q_params)`
   - **Expected:** U derived from CURRENT q_params, not initialization value

4. **Audit A* reconstruction formula:**
   - Locate A* reconstruction (line ~995: `A* = U @ B_ideal_reciprocal`)
   - Verify B_ideal_reciprocal comes from StageAContext (Phase B5 fix)
   - Verify U is computed from CURRENT q_params
   - **Expected:** A* = U_current @ B_ideal_mosflm

5. **Audit scale application:**
   - Locate where `scale = torch.exp(log_scale_param)` is computed
   - Trace scale into forward model (crystal_config creation or N_cells override)
   - Check if scale comes from `log_scale_param` or a STALE/DEFAULT value
   - **Expected:** Scale derived from CURRENT log_scale_param

6. **Check crystal_overrides construction:**
   - Locate crystal_overrides dict (line ~1000: `crystal_overrides = {...}`)
   - Verify it uses:
     - `mosflm_a_star`: from A* = U @ B_ideal (CURRENT)
     - `mosflm_b_star`: from A* = U @ B_ideal (CURRENT)
     - `mosflm_c_star`: from A* = U @ B_ideal (CURRENT)
   - **Expected:** crystal_overrides built from CURRENT parameters, not initialization

**Side-by-side comparison:**
- Compare first closure (Phase 5 optimization loop) vs zero-point validation path
- Look for code path divergence similar to Phase B5 (script vs production paths)

### Step 3: Document Audit Findings

**Create:** `phase_c4_first_closure_audit.md`

**Template:**
```markdown
# Phase C4 First Closure Audit — Parameter Staleness Investigation

## Audit Scope
Trace log_scale and q_params from initialization through first closure evaluation to identify WHERE stale values are introduced.

## Findings

### 1. log_scale Tensor Identity
- Initialization: dbex/nanobrag_refinement.py:LINE
- Closure usage: dbex/nanobrag_refinement.py:LINE
- **Issue:** <SAME TENSOR / DIFFERENT TENSOR / STALE VALUE>
- **Evidence:** <code snippet>

### 2. q_params Tensor Identity
- Initialization: dbex/nanobrag_refinement.py:LINE
- Closure usage: dbex/nanobrag_refinement.py:LINE
- **Issue:** <SAME TENSOR / DIFFERENT TENSOR / STALE VALUE>
- **Evidence:** <code snippet>

### 3. U-Matrix Derivation
- Code path: dbex/nanobrag_refinement.py:LINE
- Formula: U = quaternion_to_matrix(q_params / ||q_params||)
- **Issue:** <CORRECT / USES STALE q_params / USES DEFAULT>
- **Evidence:** <code snippet>

### 4. A* Reconstruction
- Code path: dbex/nanobrag_refinement.py:LINE
- Formula: A* = U @ B_ideal_reciprocal
- **Issue:** <CORRECT / USES STALE U / USES STALE B_ideal>
- **Evidence:** <code snippet>

### 5. Scale Application
- Code path: dbex/nanobrag_refinement.py:LINE
- Formula: scale = exp(log_scale_param)
- **Issue:** <CORRECT / USES STALE log_scale / USES DEFAULT>
- **Evidence:** <code snippet>

### 6. crystal_overrides Construction
- Code path: dbex/nanobrag_refinement.py:LINE
- Keys: mosflm_a/b/c_star
- **Issue:** <CORRECT / USES STALE A* / MISSING OVERRIDE>
- **Evidence:** <code snippet>

## Root Cause Determination

**PRIMARY BUG:** <Describe the exact line/variable causing staleness>

**CONFIDENCE:** <HIGH/MEDIUM/LOW> (~XX%)

**MECHANISM:** <Explain HOW stale value is introduced>

## Recommended Fix

**Option 1 (if simple variable reference):**
- Change line XXX from `<old code>` to `<new code>`
- Rationale: <...>

**Option 2 (if code path discrepancy):**
- Refactor closure to use <...>
- Similar to Phase B5 fix (commit fe6048f)
```

### Step 4: Implement Fix (If Root Cause Found)

**Only if audit identifies CLEAR bug (HIGH confidence):**

1. Edit `dbex/nanobrag_refinement.py` to fix the staleness bug
2. Document fix rationale in `phase_c4_fix_implementation.md`
3. Proceed to Step 5 (validation)

**If audit is INCONCLUSIVE or multiple candidates:**
- Skip implementation
- Proceed to Step 6 (decision doc) with recommendation for deeper diagnostic

### Step 5: Validation Diagnostic (If Fix Implemented)

**Command:**
```bash
timeout 1200 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix \
  --u-matrix-lr 1e-5 \
  --phases 5 \
  --dof-variants A_scale_only \
  --adam-steps 2 \
  --device cpu \
  --telemetry-dir telemetry \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232000Z/validation_postfix/ \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232000Z/validation_postfix.log 2>&1
```

**Extract validation metrics:**
```bash
python3 << 'PYEOF'
import json

with open('plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232000Z/validation_postfix/telemetry/telemetry_step_000_init.json') as f:
    init = json.load(f)
with open('plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232000Z/validation_postfix/zero_point_check.json') as f:
    zp = json.load(f)

print("=== VALIDATION METRICS ===")
print(f"Zero-point chi² (mapping): {zp.get('chi_squared_mapping', 'N/A'):,.0f}")
print(f"Zero-point chi² (stage_a):  {zp.get('chi_squared_stage_a', 'N/A'):,.0f}")
print(f"Zero-point correlation:    {zp.get('correlation', 'N/A'):.10f}")
print(f"\nFirst closure chi² (BEFORE step): {init['chi_squared']:,.0f}")
print(f"Expected (healthy):               ~1,130,000")
print(f"\nFIX STATUS:")
if init['chi_squared'] < 2_000_000:
    print("✓ SUCCESS — chi² healthy, staleness bug FIXED")
else:
    print("✗ FAIL — chi² still catastrophic, fix INCOMPLETE")
PYEOF
```

**Decision criteria:**
- **Path A (Fix SUCCESS):** chi² BEFORE step < 2M (healthy) → proceed to Phase C5 (full convergence test)
- **Path B (Fix INCOMPLETE):** chi² BEFORE step > 5M (catastrophic) → escalate to deeper diagnostic
- **Path C (Fix PARTIAL):** chi² BEFORE step 2M-5M → rerun with GPU or investigate secondary bug

### Step 6: Synthesize Decision

**Create:** `phase_c4_parameter_staleness_decision.md`

**Decision tree (3 paths):**

**Path A — Audit found clear bug, fix implemented and validated**
- Verdict: H5 (forward model staleness) CONFIRMED and FIXED
- Evidence: Audit identified line XXX using stale parameter YYY
- Fix: Changed <...> to <...>
- Validation: chi² BEFORE step dropped from 8.8M → ~1.13M
- Next action: Phase C5 (10-step convergence test to verify optimizer can now optimize)

**Path B — Audit found multiple bugs OR fix didn't resolve issue**
- Verdict: H5 (forward model staleness) CONFIRMED but fix INCOMPLETE
- Evidence: Audit identified <N> candidate bugs
- Validation (if fix attempted): chi² BEFORE step still > 5M
- Next action: Implement instrumentation to disambiguate (checksum logging per Priority 1 checklist items 1-6)

**Path C — Audit inconclusive, no clear staleness found**
- Verdict: H5 (forward model staleness) UNCERTAIN
- Evidence: Code path inspection shows no obvious staleness bugs
- Next action: Escalate to Priority 2 (test LBFGS optimizer to rule out Adam-specific bug) OR implement checksum logging to track parameter flow

### Step 7: Regression Guard
```bash
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -xvs \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232000Z/pytest_regression.log 2>&1
```

### Step 8: Update Implementation Plan

**Edit:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`

**Mark C3 as [x] DONE:**
```markdown
- [x] C3: **Parameter Lifecycle Investigation** — COMPLETED (2025-11-22T224717Z): Path C CONFIRMED with HIGH confidence (~90%). Catastrophic chi²=8.8M occurs BEFORE first optimizer.step(), proving forward model uses stale parameters during first closure evaluation. See `phase_c3_parameter_lifecycle_decision.md`.
```

**Add C4 entry:**
```markdown
- [x/~] C4: **First Closure Parameter Staleness Audit** — <Path A: Fix SUCCESS / Path B: Fix INCOMPLETE / Path C: Audit INCONCLUSIVE>. Audited log_scale/q_params/U/A*/crystal_overrides in first closure. <Root cause: line XXX uses stale YYY / No clear staleness found>. See `phase_c4_first_closure_audit.md`, `phase_c4_parameter_staleness_decision.md`.
```

### Step 9: Write Summary and Commit

**Summary:** Prepend to `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232000Z/summary.md`

**Template:**
```markdown
### Turn Summary
Audited first U-matrix closure for parameter staleness after Phase C3 confirmed chi²=8.8M BEFORE optimizer.step().
<Path A: Found and fixed stale <parameter> at line XXX; validation shows chi² healthy ~1.13M / Path B: Found candidate bug but fix incomplete; chi² still catastrophic / Path C: No clear staleness found; recommend checksum logging>.
Next: <Phase C5 convergence test / deeper diagnostic with checksums / test LBFGS optimizer>.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232000Z/ (phase_c4_first_closure_audit.md, phase_c4_parameter_staleness_decision.md, validation_postfix/)
```

**Commit:**
```bash
git add -A
git commit -m "TORCH-GEOMETRY-CONVERGENCE-001 Phase C4: First closure parameter staleness audit <+ fix if implemented> (tests: test_stage_a_expansion)"
git push
```

## How-To Map

### Audit Methodology (Step 2)

**Tool:** Manual code inspection + git blame for context

**Process:**
1. Open `dbex/nanobrag_refinement.py` in editor
2. Search for "def build_stage_a_lbfgs_closure" (line ~920)
3. Identify parameter initialization:
   ```python
   log_scale_param = torch.tensor([log_scale_0], dtype=torch.float32, requires_grad=True)
   q_params = torch.tensor(q_init, dtype=torch.float32, requires_grad=True)
   ```
4. Trace into closure definition (line ~970: `def closure():`)
5. For each parameter, verify closure uses THE SAME TENSOR (not a clone/copy/stale value)

**Specific searches:**
```bash
# Find all references to log_scale within closure
grep -n "log_scale" dbex/nanobrag_refinement.py | grep -A 5 -B 5 "def closure"

# Find all references to q_params within closure
grep -n "q_params" dbex/nanobrag_refinement.py | grep -A 5 -B 5 "def closure"

# Find crystal_overrides construction
grep -n "crystal_overrides" dbex/nanobrag_refinement.py | grep -A 10 "mosflm_a_star"
```

**Pattern to look for (similar to Phase B5 bug):**
- Phase B5 bug: `crystal_overrides["A_star"] = ...` (unsupported key) → create_crystal_config ignored it
- Phase C4 suspect: `crystal_overrides["mosflm_X_star"] = ...` using STALE A* or missing override entirely

### Validation Execution (Step 5)

**Precondition:** Fix implemented in Step 4

**Expected runtime:** ~5-10 min (2 Adam steps, A_scale_only, CPU)

**Success criteria:**
- chi² BEFORE step 0 < 2M (healthy, ~1.13M expected)
- Zero-point correlation ≥ 0.99999 (unchanged from Phase B5 fix)
- Δlog_scale magnitude ~ -1.5 (LR × gradient, not +1e-5)

**Failure signatures:**
- chi² still 8.8M → fix didn't work, need deeper diagnostic
- chi² 2M-5M → partial fix, possible secondary bug
- Regression guard fails → fix broke cell+misset path, revert

## Pitfalls to Avoid

1. **Don't edit production code before completing audit** — gather evidence first, implement fix second
2. **Check ALL parameter uses, not just one** — log_scale AND q_params AND B_ideal AND crystal_overrides
3. **Beware variable scope capture** — Python closures capture by reference; check if closure sees CURRENT value
4. **Don't assume fix works** — always run validation diagnostic after editing code
5. **Verify Phase B5 fix still works** — zero-point check must PASS after any edits
6. **Compare to zero-point code path** — why does zero-point succeed but first closure fail?
7. **Document exact line numbers** — phase_c4_first_closure_audit.md needs file:line citations
8. **Run regression guard** — cell+misset path must not break
9. **Don't batch multiple fixes** — if audit finds 2+ bugs, fix ONE at a time and validate
10. **Preserve telemetry** — don't remove lifecycle logging from Phase C3

## If Blocked

**Blocker 1: Audit finds no obvious staleness**
- Proceed to Path C decision
- Recommend checksum logging (Priority 1 checklist items 1-6)
- Don't implement speculative fixes without evidence

**Blocker 2: Fix implemented but validation still fails**
- Document in Path B decision
- Capture validation artifacts
- Recommend deeper diagnostic (checksum logging OR Priority 2 test LBFGS)

**Blocker 3: Regression guard fails after fix**
- Revert fix immediately
- Document in decision.md
- Recommend alternative fix approach

**Blocker 4: Validation diagnostic times out**
- Reduce to 1 step
- Capture whatever telemetry completed
- Mark validation as PARTIAL

## Findings Applied

**Relevant findings (HIGH priority):**

- **Phase B5 (Code path discrepancy):** Script `_stage_a_forward` set unsupported `crystal_overrides["A_star"]` key → create_crystal_config ignored MOSFLM tuple. Fix: Convert A* to `mosflm_a/b/c_star` keys. **Pattern recognition:** Current symptom (initialization healthy, first closure catastrophic) matches Phase B5 exactly → audit should focus on crystal_overrides construction.

- **Phase B4 (Extended diagnostic):** Script-level `_forward_once` produced chi²=1.425B while `run_nanobrag_refinement` produced chi²=1.13M at SAME parameters → code path divergence. **Implication:** First closure may use DIFFERENT code path than zero-point validation (which succeeds).

- **GRADIENT-001 (autograd graph preservation):** Production refinement must avoid `.item()`/`.numpy()`/`.detach()` on differentiable tensors. **Check:** Ensure log_scale_param not detached before closure.

**Findings NOT directly applicable (but keep in mind):**
- REFINE-001 (LBFGS scale warm-start) — not relevant (staleness not initialization)
- PHYSICS-LOSS-002 (variance sigma-floor) — not relevant (chi² catastrophic before loss computation)

## Pointers

- **Phase C3 Decision:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T224717Z/phase_c3_parameter_lifecycle_decision.md` — Path C verdict, Priority 1 recommendation
- **Phase B5 Fix:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/code_path_audit.md` — Similar diagnostic approach
- **Phase B5 Commit:** `fe6048f` — crystal_overrides fix pattern (convert A* to mosflm_X_star keys)
- **Closure Code:** `dbex/nanobrag_refinement.py:~920-1116` — Stage A closure (U-matrix branch)
- **Implementation Plan:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` — Phase C checklist
- **Spec:** `docs/spec-db-runtime.md` §Optimizer Convergence — Parameter lifecycle requirements

## Next Up

If audit completes early AND verdict is Path A (fix SUCCESS):

**Phase C5: Full Convergence Test (10 steps)**
- Run A_scale_only with 10 Adam steps
- Expect monotonic chi² improvement
- Expect median CC ≥ 0.99 final
- Validate optimizer can now optimize from healthy initialization

If verdict is Path B/C (fix INCOMPLETE or audit INCONCLUSIVE):

**Option 1: Checksum Logging (Priority 1 extension)**
- Implement U_matrix/A* checksum logging per priority 1 checklist items 1-6
- Run 2-step diagnostic
- Identify EXACT point where parameter diverges

**Option 2: Test LBFGS (Priority 2)**
- Switch optimizer to LBFGS
- Check if LBFGS shows healthy chi² BEFORE first step
- If yes → Adam-specific bug; if no → forward model bug confirmed
