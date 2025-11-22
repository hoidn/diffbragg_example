# Phase B4 Extended Diagnostic — U-Matrix/A*/Gradient Lifecycle Tracing

## Summary
Execute extended diagnostic to capture U_matrix checksums, A* reconstruction validation, and initialization gradient magnitude, definitively identifying whether root cause is U-matrix staleness, crystal_overrides aliasing, or gradient explosion (primary vs symptom).

## Mode
none (diagnostic evidence collection with production code instrumentation)

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard)
- Validation: 1-step diagnostic run with enhanced telemetry (no pytest selector, ad-hoc test script execution)

## Artifacts
`plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/`
- `phase_b4_extended_diagnostic.md` (root cause determination with checksums)
- `diagnostic_b4_1step/` (test outputs)
  - `zero_point_check.json`
  - `block_dof_results_u_matrix.json`
  - `telemetry/telemetry_step_000_init.json` (before optimizer.step, healthy chi² gradients)
  - `telemetry/telemetry_step_000_post.json` (after optimizer.step, catastrophic chi² gradients)
  - `u_matrix_lifecycle.json` (checksum tracking)
  - `a_star_lifecycle.json` (reconstruction validation)
- `pytest_regression.log`
- `summary.md`

---

## Do Now

### Context from Phase B3
Phase B3 (2025-11-22T195000Z) confirmed **H4 (Forward Model Bug) with HIGH confidence (~80%)**:
- Initialization healthy: chi²=1.13M (1000× improvement vs pre-fix 1.425B)
- Post-optimization catastrophic: chi²→1.425B after single step
- Gradient explosion: log_scale gradient ~295k (likely SYMPTOM not primary)
- Optimizer-agnostic failure (Adam + LBFGS identical signatures)
- Zero-point validation PASSED (B_ideal fix works for initialization)

**Gap:** Missing U_matrix/A* checksums and initialization gradient magnitude to distinguish staleness vs explosion hypotheses.

### Objective
Instrument the U-matrix closure with lifecycle tracing to capture:
1. **U_matrix checksum** at initialization (step 0) and after optimizer.step() (step 1) to test staleness hypothesis
2. **A* checksum** before crystal_overrides construction to validate reconstruction matches U @ B_ideal
3. **Gradient magnitude at healthy initialization** (chi²=1.13M) to test if explosion is PRIMARY or SYMPTOM
4. **Parameter values** (log_scale, q_params, q_norm) at both init and post-step

### Implementation Plan

#### Step 1: Review Phase B3 Artifacts
- [x] Read `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/phase_b3_forward_model_sanity_check.md`
- [x] Note: telemetry_step_000 was captured AFTER forward/backward (includes gradients at catastrophic chi²), need BEFORE optimizer.step() telemetry

#### Step 2: Extend Telemetry Schema in U-Matrix Closure
**File:** `dbex/nanobrag_refinement.py` (U-matrix branch of `build_stage_a_lbfgs_closure`, lines ~966-1116)

Add lifecycle tracking BEFORE the closure function definition:
```python
# After line 965 (before closure def):
u_matrix_lifecycle_log = []  # Track U checksum per closure call
a_star_lifecycle_log = []    # Track A* reconstruction per closure call
```

Inside the closure, after U-matrix computation (around line 987):
```python
# After line 987 (U_matrix = quaternion_to_matrix(...)):
U_checksum = U_matrix.sum().item()  # Simple checksum
A_star_new = torch.matmul(U_matrix, B_ideal_reciprocal_torch)
A_star_checksum = A_star_new.sum().item()
A_star_np = A_star_new.detach().cpu().numpy()

u_matrix_lifecycle_log.append({
    "closure_call_index": len(u_matrix_lifecycle_log),
    "U_checksum": U_checksum,
    "q_params_norm": torch.norm(q_params).item(),
    "log_scale_value": log_scale.item()
})

a_star_lifecycle_log.append({
    "closure_call_index": len(a_star_lifecycle_log),
    "A_star_checksum": A_star_checksum,
    "U_checksum": U_checksum,
    "B_ideal_checksum": B_ideal_reciprocal_torch.sum().item()
})
```

At the END of the closure (before return), emit lifecycle JSON if telemetry_output_dir exists:
```python
# Before return statement:
if telemetry_output_dir is not None:
    lifecycle_path = telemetry_output_dir / f"u_matrix_lifecycle_step_{step_counter.value}.json"
    with open(lifecycle_path, 'w') as f:
        json.dump({
            "u_matrix_lifecycle": u_matrix_lifecycle_log,
            "a_star_lifecycle": a_star_lifecycle_log
        }, f, indent=2)
```

#### Step 3: Emit TWO Telemetry Points in Script
**File:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`

Modify Phase 5 U-matrix optimization loop to emit:
1. **telemetry_step_000_init.json** BEFORE optimizer.step() (healthy chi²=1.13M, captures init gradients)
2. **telemetry_step_000_post.json** AFTER optimizer.step() (catastrophic chi²=1.425B, captures post-step gradients)

Around line ~1700-1730 (Phase 5 optimization loop):
```python
# BEFORE optimizer.step():
if telemetry_dir is not None:
    emit_telemetry(
        telemetry_dir / f"telemetry_step_{step_index:03d}_init.json",
        step=step_index,
        closure_state="before_optimizer_step",
        log_scale=log_scale,
        q_params=q_params,
        # ... existing fields ...
    )

# Execute optimizer step
if use_lbfgs:
    optimizer.step(closure)
else:
    closure()
    optimizer.step()

# AFTER optimizer.step():
if telemetry_dir is not None:
    emit_telemetry(
        telemetry_dir / f"telemetry_step_{step_index:03d}_post.json",
        step=step_index,
        closure_state="after_optimizer_step",
        log_scale=log_scale,
        q_params=q_params,
        # ... existing fields ...
    )
```

#### Step 4: Execute 1-Step Diagnostic with Enhanced Logging
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix \
  --phases 5 \
  --dof-variants A_scale_only \
  --optimizer-steps 1 \
  --telemetry-dir telemetry \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step \
  --device cpu \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step.log 2>&1
```

**Expected duration:** ~10-15 minutes (CPU-bound, 1 optimizer step, ~29 HKL grid builds)

**NOTE:** Use `--optimizer-steps 1` (not `--use-lbfgs`), as Phase B3 showed the --use-lbfgs flag is not respected. Use Adam optimizer (default) which is fine since failure is optimizer-agnostic.

#### Step 5: Extract Diagnostic Metrics
After test completes, extract:

**A. Zero-Point Validation (B_ideal fix reconfirmation)**
```bash
jq '{chi_squared_mapping: .chi_squared_mapping, chi_squared_stage_a: .chi_squared_stage_a, abs_diff: .abs_diff, rel_diff: .rel_diff, correlation: .correlation}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step/zero_point_check.json \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/zero_point_metrics.txt
```

**B. Convergence Metrics (before/after chi²)**
```bash
jq '{before: .chi_squared.before, after: .chi_squared.after, ratio: (.chi_squared.after / .chi_squared.before), cc_before: .correlation.before, cc_after: .correlation.after}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step/block_dof_results_u_matrix.json \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/convergence_metrics.txt
```

**C. Initialization Gradients (healthy chi²=1.13M)**
```bash
jq '{step: .step, closure_state: .closure_state, log_scale: .log_scale, grad_log_scale: .grad_log_scale, q_params_norm: .q_params_norm, grad_has_nan: .grad_has_nan, grad_has_inf: .grad_has_inf, chi_squared: .chi_squared}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step/telemetry/telemetry_step_000_init.json \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/init_gradient_metrics.txt
```

**D. Post-Step Gradients (catastrophic chi²=1.425B)**
```bash
jq '{step: .step, closure_state: .closure_state, log_scale: .log_scale, grad_log_scale: .grad_log_scale, q_params_norm: .q_params_norm, grad_has_nan: .grad_has_nan, grad_has_inf: .grad_has_inf, chi_squared: .chi_squared}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step/telemetry/telemetry_step_000_post.json \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/post_step_gradient_metrics.txt
```

**E. U-Matrix Lifecycle (staleness test)**
```bash
jq '.' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step/telemetry/u_matrix_lifecycle_step_*.json \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/u_matrix_lifecycle.txt
```

**F. A* Lifecycle (reconstruction validation)**
```bash
jq '.' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step/telemetry/a_star_lifecycle_*.json \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/a_star_lifecycle.txt
```

#### Step 6: Synthesize Root Cause Determination (Decision Tree)
Create `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/phase_b4_extended_diagnostic.md` with decision analysis:

**Decision Tree:**

1. **Test for U-Matrix Staleness (H4a)**
   - **IF** `u_matrix_lifecycle` shows U_checksum DIFFERS between closure calls for A_scale_only (train_orientation=False):
     - **VERDICT:** H4a CONFIRMED (U-matrix staleness bug)
     - **Root Cause:** Quaternion normalization or U recomputation not happening per closure call
     - **Fix:** Ensure `U_matrix = quaternion_to_matrix(q_params / torch.norm(q_params))` executes EVERY closure invocation, not cached

   - **ELSE IF** U_checksum is CONSTANT across closure calls (expected for A_scale_only):
     - **VERDICT:** H4a RULED OUT (U-matrix is NOT stale)
     - **Proceed to Test 2**

2. **Test for A* Aliasing (H4b)**
   - **IF** `a_star_lifecycle` shows A_star_checksum ≠ (U_checksum + B_ideal_checksum) for any closure call:
     - **VERDICT:** H4b CONFIRMED (crystal_overrides aliasing bug)
     - **Root Cause:** A* tuple constructed from stale/detached tensor
     - **Fix:** Ensure `A_star_np = A_star_new.detach().cpu().numpy()` happens AFTER fresh U @ B_ideal computation

   - **ELSE IF** A_star_checksum matches reconstruction:
     - **VERDICT:** H4b RULED OUT (A* reconstruction is correct)
     - **Proceed to Test 3**

3. **Test for Gradient Explosion PRIMARY vs SYMPTOM (H3b)**
   - **IF** `telemetry_step_000_init.json` (healthy chi²=1.13M) shows grad_log_scale ~295k:
     - **VERDICT:** H3b PRIMARY (gradient explosion independent of forward model)
     - **Root Cause:** Loss/variance numerical instability produces huge gradients even at healthy chi²
     - **Fix:** Implement gradient clipping (`torch.nn.utils.clip_grad_norm_(params, max_norm=100.0)`)

   - **ELSE IF** `telemetry_step_000_init.json` shows grad_log_scale O(1-100) AND `telemetry_step_000_post.json` shows ~295k:
     - **VERDICT:** H3b SYMPTOM (gradient explosion follows forward model bug)
     - **Root Cause:** Forward model pathology (H4a or H4b missed by checksums) causes chi² explosion, which then produces huge gradients
     - **Fix:** Deeper investigation (detach placement audit, parameter update propagation tracing)

4. **Escalation Path (if all tests inconclusive)**
   - **IF** U/A* checksums are correct AND gradients are healthy at init:
     - **VERDICT:** H4c (Detach Placement or Other Autograd Bug)
     - **Root Cause:** Parameter updates don't propagate to forward model due to premature .detach() or tensor aliasing
     - **Fix:** Audit all .detach() calls in U-matrix closure branch (lines 966-1003); trace autograd graph with `torch.autograd.grad`

**Output:** Document verdict with CONFIDENCE level (HIGH/MEDIUM/LOW) and recommend next action (Phase B5 Fix Implementation OR deeper investigation).

#### Step 7: Regression Guard
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/pytest_regression.log 2>&1
```

#### Step 8: Update Implementation Checklist
Edit `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`:
- Mark B4 as `[x] DONE` with verdict summary (e.g., "H4a CONFIRMED: U-matrix staleness" or "H3b PRIMARY: gradient explosion")
- Update B5 checklist item with recommended fix based on decision tree outcome

#### Step 9: Write Summary
Create `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/summary.md`:
```markdown
### Turn Summary
Executed Phase B4 extended diagnostic with U_matrix/A*/gradient lifecycle tracing to definitively identify root cause among staleness/aliasing/gradient hypotheses.
[Verdict: H4a/H4b/H3b CONFIRMED/RULED OUT with HIGH confidence based on checksum/gradient analysis].
Next: [Phase B5 Fix Implementation targeting X OR Deeper investigation of Y].
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/ (phase_b4_extended_diagnostic.md, u_matrix_lifecycle.txt, init_gradient_metrics.txt)
```

#### Step 10: Commit and Push
```bash
git add -A
git commit -m "TORCH-GEOMETRY-CONVERGENCE-001 Phase B4: Extended diagnostic - U_matrix/A*/gradient lifecycle tracing (tests: test_stage_a_expansion)"
git push
```

---

## How-To Map

### Environment Variables (Required)
```bash
export KMP_DUPLICATE_LIB_OK=TRUE          # Intel MKL + FFTW coexistence
export NANOBRAGG_DISABLE_COMPILE=1         # Disable torch.compile for gradient testing
```

### Execution Steps

**1. Implement Telemetry Extensions**
- Edit `dbex/nanobrag_refinement.py` (U-matrix closure, lines ~966-1116):
  - Add `u_matrix_lifecycle_log`, `a_star_lifecycle_log` lists before closure definition
  - After U-matrix computation (~line 987), append checksums to lifecycle logs
  - Before return, emit `u_matrix_lifecycle_step_{i}.json` if telemetry_output_dir exists
- Edit `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` (Phase 5 loop, ~line 1700-1730):
  - Emit `telemetry_step_000_init.json` BEFORE optimizer.step()
  - Emit `telemetry_step_000_post.json` AFTER optimizer.step()

**2. Run 1-Step Diagnostic**
```bash
cd /home/ollie/Documents/diffbragg_example
mkdir -p plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step

KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix \
  --phases 5 \
  --dof-variants A_scale_only \
  --optimizer-steps 1 \
  --telemetry-dir telemetry \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step \
  --device cpu \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/diagnostic_b4_1step.log 2>&1
```

**3. Extract Metrics**
```bash
cd plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z

# Zero-point validation
jq '{chi_squared_mapping, chi_squared_stage_a, abs_diff, rel_diff, correlation}' \
  diagnostic_b4_1step/zero_point_check.json > zero_point_metrics.txt

# Convergence metrics
jq '{before: .chi_squared.before, after: .chi_squared.after, ratio: (.chi_squared.after / .chi_squared.before), cc_before: .correlation.before, cc_after: .correlation.after}' \
  diagnostic_b4_1step/block_dof_results_u_matrix.json > convergence_metrics.txt

# Initialization gradients (healthy chi²)
jq '{step, closure_state, log_scale, grad_log_scale, q_params_norm, grad_has_nan, grad_has_inf, chi_squared}' \
  diagnostic_b4_1step/telemetry/telemetry_step_000_init.json > init_gradient_metrics.txt

# Post-step gradients (catastrophic chi²)
jq '{step, closure_state, log_scale, grad_log_scale, q_params_norm, grad_has_nan, grad_has_inf, chi_squared}' \
  diagnostic_b4_1step/telemetry/telemetry_step_000_post.json > post_step_gradient_metrics.txt

# U-matrix lifecycle (all closure calls)
cat diagnostic_b4_1step/telemetry/u_matrix_lifecycle_step_*.json > u_matrix_lifecycle.txt

# A* lifecycle (reconstruction validation)
cat diagnostic_b4_1step/telemetry/a_star_lifecycle_*.json > a_star_lifecycle.txt
```

**4. Synthesize Root Cause Determination**
- Create `phase_b4_extended_diagnostic.md` with decision tree analysis
- Follow 4-test protocol: (1) U_checksum staleness, (2) A*_checksum aliasing, (3) gradient PRIMARY vs SYMPTOM, (4) escalation
- Document VERDICT with confidence level and recommended fix

**5. Run Regression Guard**
```bash
cd /home/ollie/Documents/diffbragg_example
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/pytest_regression.log 2>&1
```

---

## Pitfalls To Avoid

1. **DO NOT** emit telemetry ONLY after optimizer.step() — need BOTH before (init) and after (post-step) to distinguish gradient PRIMARY vs SYMPTOM
2. **DO NOT** use LBFGS optimizer — Phase B3 showed --use-lbfgs flag is not respected, and failure is optimizer-agnostic anyway; use Adam (default)
3. **DO NOT** cache U_matrix across closure calls — each closure invocation must recompute U from normalized q_params to detect staleness bugs
4. **DO NOT** use `.detach()` on U_matrix or A_star before recording checksums — checksums are for lifecycle tracking only, not for breaking autograd
5. **DO NOT** run multiple optimizer steps — 1 step is sufficient to reproduce catastrophic failure and keeps diagnostic fast (~10-15 min)
6. **DO NOT** rely solely on zero-point validation — it uses use_mapping_zero_geometry=True which bypasses U @ B_ideal reconstruction; diagnostic must test the optimization loop path
7. **DO NOT** skip lifecycle JSON emission — checksums are the DECISIVE evidence distinguishing staleness/aliasing hypotheses
8. **DO NOT** guess root cause without data — decision tree requires actual checksum/gradient measurements to rule in/out hypotheses
9. **DO** ensure telemetry paths are correct (Phase B1 had double-prepending bug) — use simple relative path `--telemetry-dir telemetry`
10. **DO** capture full diagnostic log output — Phase B3 log was truncated, making post-mortem analysis harder

---

## If Blocked

**Scenario 1: Telemetry files missing (init or post or lifecycle JSONs)**
- Check diagnostic_b4_1step.log for errors during telemetry emission
- Verify script modifications are correct (two emit_telemetry calls in Phase 5 loop)
- Verify closure modifications emit lifecycle JSON before return statement
- If telemetry_output_dir is None, pass explicit `--telemetry-dir telemetry` flag

**Scenario 2: Test times out (>1200s)**
- Reduce to 1 optimizer step (already specified in Do Now)
- Check HKL grid build count (should be ~29 for canonical dataset)
- If still slow, check CPU load (ensure no other processes hogging cores)

**Scenario 3: Checksum analysis inconclusive (all tests RULED OUT)**
- Document in phase_b4_extended_diagnostic.md with MEDIUM-LOW confidence
- Recommend escalation to Path C (deeper autograd graph tracing, detach audit)
- Consider alternative parameterization pivot (hybrid cell+quaternion per PARITY-003 Option 1)

**Scenario 4: Regression guard fails**
- This is unexpected (cell+misset default path should be unaffected)
- Document failure in pytest_regression.log
- Mark B4 as BLOCKED and investigate regression before proceeding

---

## Findings Applied

**Mandatory Knowledge Base Adherence:**

1. **REFINE-001** (LBFGS scale warm-start, NaN/Inf guards)
   - Telemetry includes `grad_has_nan` and `grad_has_inf` flags
   - Zero-point validation reconfirms B_ideal fix (commit e86fd4e) works

2. **PHYSICS-LOSS-002** (variance-weighted chi-squared sigma-floor guard)
   - Variance telemetry schema includes clamp_fraction (though not captured in Phase B3 script-level telemetry)
   - Extended diagnostic focuses on U/A*/gradient lifecycle, not variance components (defer to B5 if needed)

3. **GRADIENT-001** (autograd graph preservation, crystal_overrides)
   - Decision tree explicitly tests for crystal_overrides aliasing (H4b)
   - Detach placement audit is escalation path if checksums are inconclusive

4. **GEOMETRY-003** (Stage-A baseline misset from dxtbx A* matrix)
   - B_ideal fix (commit e86fd4e) ensures MOSFLM-derived B_ideal is used consistently
   - Zero-point validation confirms parity with mapping path

5. **RUNTIME-001** (torch.compile disabled for gradient tests)
   - Environment flag `NANOBRAGG_DISABLE_COMPILE=1` is mandatory for all diagnostic runs

No relevant findings in the knowledge base contradict this diagnostic protocol.

---

## Pointers

**Spec/Arch Documents:**
- `docs/spec-db-workflow.md §Stage A` — Optimizer convergence criteria
- `docs/spec-db-runtime.md §Gradient stability` — NaN/Inf checks, autograd graph preservation
- `docs/spec-db-core.md §Variance Model` — Variance-weighted chi-squared definition

**Fix-Plan References:**
- `docs/fix_plan.md — Row [TORCH-GEOMETRY-CONVERGENCE-001]` — Initiative status, dependencies, exit criteria
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md:119-150` — Phase B checklist (B0-B4)

**Testing Guide:**
- `docs/TESTING_GUIDE.md §2.2` — test_stage_a_expansion selector (regression guard)
- `docs/development/TEST_SUITE_INDEX.md` — Stage A expansion test status

**Prior Phase Artifacts:**
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T195000Z/phase_b3_forward_model_sanity_check.md` — Phase B3 decision (H4 CONFIRMED HIGH confidence)
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/phase_b1_validation_decision.md` — Phase B1 LBFGS validation (Path B: fix incomplete)
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/phase_a_bugfix_decision.md` — Phase A B_ideal bugfix (initialization resolved, convergence persists)

---

## Next Up

**If Phase B4 identifies root cause with HIGH confidence (>75%):**
- Proceed to Phase B5 Fix Implementation
- Target: H4a (U-matrix recomputation fix), H4b (A* tuple freshness fix), or H3b (gradient clipping)
- Validation: Rerun Phase 5 A_scale_only + D_full convergence tests

**If Phase B4 is inconclusive (MEDIUM confidence <75%):**
- Escalate to deeper autograd graph tracing (Phase B6)
- Audit all `.detach()` calls in U-matrix closure branch
- Trace parameter update propagation with `torch.autograd.grad` manual gradient computation

**If all hypotheses RULED OUT:**
- Pivot to alternative parameterization (hybrid cell+quaternion per PARITY-003 Option 1)
- Or mark quaternion U-matrix approach as non-viable and revert to cell+misset only (TORCH-REFINE-002E)

---

## Doc Sync Plan

**Not applicable** — This is a diagnostic loop with no new tests added or renamed. Test registry updates deferred until Phase C (fix validation) when convergence tests may be promoted to acceptance selectors.

---

## Implementation Floor Enforcement

**This loop satisfies the implementation floor requirement:**
- **Production code changes:** Telemetry instrumentation in `dbex/nanobrag_refinement.py` (lifecycle logging) and `stage_a_mapping_adam_debug.py` (dual emission points)
- **Validating selector:** `test_stage_a_expansion` (regression guard)
- **Evidence collection:** 1-step diagnostic with checksum/gradient extraction

This is NOT a docs-only loop — production instrumentation code is required to emit lifecycle JSONs for root cause determination.
