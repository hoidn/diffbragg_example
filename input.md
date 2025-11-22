# Supervisor Handoff — TORCH-GEOMETRY-CONVERGENCE-001 Phase A Forward Model Diagnostic

## Summary
Diagnose why quaternion U-matrix forward model produces chi-squared 1.425B at zero parameters (1000× worse than expected ~1.13M), comparing zero-point check code path vs Adam loop code path.

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — regression guard (U-matrix path must not break cell+misset default)

## Artifacts
plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/

## Do Now

**Checklist Items:** Phase A Diagnostic (investigate forward model discrepancy between zero-point check and Adam loop)

**Critical Finding:** Phase A3 telemetry analysis revealed chi-squared catastrophic failure at step 0 (1.425B vs expected ~1.13M), **before optimizer runs**. Zero-point check in the same run shows perfect parity (corr ≈ 1.0), suggesting forward model discrepancy between:
- **Zero-point check code path** (produces correct chi-squared ~1.13M)
- **Adam optimization loop code path** (produces wrong chi-squared 1.425B)

**Your Task (Evidence Gathering + Optional Bugfix):**

### Step 1: Inspect Zero-Point Check Implementation

Read the zero-point check code in `stage_a_mapping_adam_debug.py` to understand how it computes forward model at zero parameters:

```bash
grep -n "zero_point_check" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py -A 50
```

**Key questions:**
1. Does zero-point check use `use_mapping_zero_geometry=True` or `False`?
2. Does it call `_stage_a_forward` with the same parameters as the Adam loop?
3. Are there any differences in how `q_params`, `log_scale`, or `B_ideal_reciprocal` are initialized?

### Step 2: Inspect Adam Loop Forward Model

Read the Adam optimization loop in `_stage_a_adam_core` (~line 783-870) to understand how it computes forward model:

```bash
grep -n "def _stage_a_adam_core" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py -A 100
```

**Key questions:**
1. Line 810 calls `_forward_once(use_mapping_zero_geometry=False)` — does this match zero-point check?
2. Are `q_params`, `log_scale`, `B_ideal_reciprocal` initialized differently than zero-point check?
3. Is there a difference in ROI sampling, HKL grid, or simulator settings between the two code paths?

### Step 3: Compare chi-squared Computation

**Hypothesis:** Zero-point check may compute chi-squared differently than Adam loop (e.g., different variance weighting, different ROI selection, or full-image vs sampled).

Read how chi-squared is computed in both code paths:
- Zero-point check: Likely uses `_compute_variance_weighted_loss` or similar
- Adam loop: Line 810 `bragg_t, chi_sq_t = _forward_once(use_mapping_zero_geometry=False)`

**Check if:**
1. Zero-point check uses full ROIs while Adam loop samples a subset
2. Variance-weighted denominator is different (sigma_floor, sigma_readout)
3. Masking is different (which pixels contribute to chi-squared)

### Step 4: Document Discrepancy (or Lack Thereof)

Write `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/forward_model_discrepancy_analysis.md`:

```markdown
# Forward Model Discrepancy Analysis

## Zero-Point Check Code Path
- Function: [function name and line number]
- Parameters: [q_params, log_scale, use_mapping_zero_geometry value]
- Forward model: [how A* is computed]
- Chi-squared computation: [variance weighting, ROI selection, masking]
- Result: chi-squared ≈ [value from zero_point_check.json]

## Adam Loop Code Path
- Function: [function name and line number]
- Parameters: [q_params, log_scale, use_mapping_zero_geometry value]
- Forward model: [how A* is computed]
- Chi-squared computation: [variance weighting, ROI selection, masking]
- Result: chi-squared ≈ [value from telemetry_step_000.json = 1.425B]

## Discrepancy Diagnosis

[If difference found:]
**Root Cause:** [Specific difference in code path, e.g., "Zero-point check uses `use_mapping_zero_geometry=True` which bypasses quaternion path and uses MOSFLM A* directly, while Adam loop uses `use_mapping_zero_geometry=False` which computes A* via quaternion → U → B_ideal but B_ideal_reciprocal has wrong shape/values"]

**Fix:** [Proposed fix to align the two code paths]

[If NO difference found:]
**Result:** No obvious code path difference detected. Zero-point check and Adam loop appear to use same forward model logic. Discrepancy may be due to:
1. Timing of initialization (q_params/B_ideal computed differently at different points in script)
2. Subtle numerical precision difference (float32 vs float64, detached tensors)
3. HKL grid difference (different panels built at different times)
4. Need deeper instrumentation to capture A_star, U_matrix, B_ideal_reciprocal tensor values at step 0
```

### Step 5 (CONDITIONAL): If Bug Found, Fix It

**If Step 4 identifies a clear bug** (e.g., B_ideal_reciprocal has wrong shape, or zero-point check doesn't actually use quaternion path):

1. **Fix the bug** in `stage_a_mapping_adam_debug.py` or `dbex/nanobrag_refinement.py` as appropriate
2. **Rerun zero-point check** to verify it still achieves perfect parity
3. **Rerun Phase A2 instrumented run** (Step 6) to verify chi-squared is now correct at step 0
4. **Document fix** in `forward_model_discrepancy_analysis.md` with before/after chi-squared values

**If NO bug found** (code paths appear identical):
- Skip bugfix
- Proceed to Step 6 to gather more evidence (deeper instrumentation or variance telemetry)

### Step 6 (CONDITIONAL): Rerun Phase A2 with Deeper Instrumentation

**If bug not found in Step 4**, or **if fix needs validation**, rerun instrumented Phase A2:

**Option A (Full rerun with 10 steps):**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --phases 5 --dof-variants A_scale_only \
  --adam-steps 10 --device cpu \
  --telemetry-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/telemetry/ \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/stage_a_debug_rerun.log
```

**Expected outcomes:**
- If bug was fixed: chi-squared at step 0 should be ~1.13M (matching zero-point check), telemetry should show successful optimization or at least correct starting point
- If no bug found: chi-squared still 1.425B at step 0, confirming discrepancy is not in obvious code path difference

**Option B (Add logging to capture A_star/U_matrix/B_ideal at step 0):**

If Option A still shows 1.425B at step 0, add temporary logging to `_stage_a_forward` (U-matrix path, lines 426-436) to capture:
```python
# After line 434: A_star_new = U_matrix @ components.B_ideal_reciprocal
if step_idx == 0 and use_u_matrix:  # Only at first step
    print(f"[DEBUG step 0] q_norm: {q_norm.detach().cpu().numpy()}")
    print(f"[DEBUG step 0] U_matrix:\n{U_matrix.detach().cpu().numpy()}")
    print(f"[DEBUG step 0] B_ideal_reciprocal shape: {components.B_ideal_reciprocal.shape}")
    print(f"[DEBUG step 0] B_ideal_reciprocal:\n{components.B_ideal_reciprocal.detach().cpu().numpy()}")
    print(f"[DEBUG step 0] A_star_new:\n{A_star_new.detach().cpu().numpy()}")
```

Rerun and capture debug output to `debug_step_0.log`. Compare with expected values from zero-point check.

### Step 7: Regression Guard

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/pytest_stage_a_regression.log
```

**Expected:** PASSED (cell+misset default path unaffected; U-matrix path optional and gated by flag)

### Step 8: Update Implementation Plan Checklist

Mark diagnostic complete in `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md`:

If bug found and fixed:
- Mark A2 as complete (rerun successful, chi-squared correct at step 0)
- Add note to A3: "Root cause was [bug description]; fixed in [commit]"

If no bug found:
- Add note to A2: "Rerun with deeper instrumentation pending; forward model discrepancy analysis inconclusive"
- A4/A5/A6 remain pending deeper evidence

### Step 9: Emit Summary

Write `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/summary.md`:

```markdown
### Turn Summary
[If bug found:] Diagnosed forward model discrepancy: [bug description]. Fixed [file:line] by [fix description]. Reran Phase A2 with corrected forward model; chi-squared at step 0 now [value] (expected ~1.13M). Regression guard PASSED.
Next: Phase A4-A6 (gradient validation, variance analysis, hypothesis decision) or Phase B if bug fix resolved convergence.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/ (forward_model_discrepancy_analysis.md, telemetry/ if rerun, pytest_stage_a_regression.log)

[If no bug found:] Analyzed forward model code paths (zero-point check vs Adam loop); no obvious discrepancy detected. Chi-squared mismatch (1.425B vs ~1.13M) remains unexplained by code inspection. Need deeper instrumentation (A_star/U_matrix/B_ideal logging at step 0) or Phase A5 variance telemetry.
Next: Add debug logging to capture tensor values at step 0, or proceed to Phase A5 variance telemetry instrumentation in dbex/nanobrag_refinement.py closure.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/ (forward_model_discrepancy_analysis.md, pytest_stage_a_regression.log)
```

Prepend this to existing `summary.md` (keep Galph 2025-11-22T150000Z and Ralph 2025-11-22T140000Z entries below).

## How-To Map

**Code Inspection:**
```bash
# Find zero-point check implementation
grep -n "def.*zero_point" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py -A 30

# Find Adam loop forward call
grep -n "_forward_once" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py -B 5 -A 3

# Check _stage_a_forward U-matrix path
grep -n "if components.use_u_matrix:" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py -A 15

# Compare B_ideal_reciprocal initialization
grep -n "B_ideal_reciprocal" plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py
```

**Telemetry Inspection:**
```bash
# Zero-point check result
jq -r '.summary.corr_median_vs_mapping, .summary.max_abs_diff' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/zero_point_check.json

# Adam loop step 0 chi-squared
jq -r '.chi_squared' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/telemetry/telemetry_step_000.json
```

**Optional Rerun (if bug found or validation needed):**
```bash
# Create new telemetry directory
mkdir -p plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/telemetry/

# Run Phase A2 with telemetry
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --phases 5 --dof-variants A_scale_only \
  --adam-steps 10 --device cpu \
  --telemetry-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/telemetry/ \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/stage_a_debug_rerun.log

# Verify step 0 chi-squared
jq -r '.chi_squared' plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/telemetry/telemetry_step_000.json
```

## Pitfalls To Avoid

1. **Do NOT assume bug exists** — Code paths may be identical; discrepancy could be due to timing, numerical precision, or HKL grid differences. Document what you find honestly.

2. **Do NOT make speculative bugfixes** — Only fix if you have clear evidence of a bug (e.g., wrong shape, wrong tensor values, wrong use_mapping_zero_geometry flag).

3. **Telemetry path nesting bug** — Existing telemetry files are in `plans/active/.../plans/active/...` (double nesting). This is a path construction bug in the script. If you rerun, verify telemetry files go to the correct location (single-level nesting).

4. **Step 0 vs zero-point check** — Zero-point check is a separate validation run (before optimization loop). Step 0 telemetry is captured DURING the first optimizer closure call. They may not be exactly the same code path.

5. **Missing step_009 investigation** — The previous run captured only 9/10 steps. If you rerun, check if all 10 steps are captured. If not, investigate why (timeout, crash, early exit).

6. **Quaternion gradients in A_scale_only** — Do NOT expect q_params.grad to be populated in A_scale_only variant (train_orientation=False). This is expected behavior, not a bug.

7. **Regression guard environment** — Use exact environment flags from TESTING_GUIDE.md; do not omit DBEX_SMOKE_SIGMA_SOURCE or DBEX_SMOKE_DETECTOR_SIZE.

8. **Forward model complexity** — The quaternion U-matrix path involves multiple tensor operations (normalization, matrix multiplication, A* override). Bugs could be in any step. Capture intermediate values if code inspection doesn't reveal obvious issue.

## If Blocked

**If zero-point check and Adam loop code paths appear identical:**
- Document "No obvious discrepancy" in analysis
- Recommend next step: Add debug logging to capture A_star, U_matrix, B_ideal_reciprocal tensor values at step 0
- Or pivot to Phase A5 variance telemetry (check if variance denominator is causing massive gradients)

**If rerun still shows chi-squared 1.425B at step 0:**
- Confirm bug fix was applied correctly (check git diff)
- Check if B_ideal_reciprocal shape/values are correct (print tensors)
- Consider numerical precision issue (float32 vs float64)
- Document in blocker and escalate to Phase A5 variance analysis or deeper instrumentation

**If regression guard fails:**
- Check if failure is in cell+misset default path (blocker — revert changes) or U-matrix path (acceptable if experimental)
- Document regression details with exact pytest output
- Do NOT proceed to summary if regression breaks default path

## Findings Applied (Mandatory)

- **REFINE-001** (LBFGS scale warm-start, NaN/Inf guards): Not directly applicable to forward model diagnostic; deferred to Phase A4-A6.
- **PHYSICS-LOSS-002** (variance-weighted chi-squared sigma-floor guard): Potentially relevant if chi-squared discrepancy is due to variance denominator differences between zero-point check and Adam loop.
- **GRADIENT-001** (autograd graph preservation): Not applicable to forward model diagnostic (no graph mutations in this task).
- No other findings directly address quaternion U-matrix forward model pathology.

## Pointers

- **Phase A3 Analysis:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/phase_a_first_divergence.md (step 0 catastrophic failure diagnosis, hypothesis verdicts)
- **Telemetry Data:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/plans/active/.../telemetry/telemetry_step_000.json (chi-squared 1.425B)
- **Zero-Point Check:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/zero_point_check.json (corr ≈ 1.0, max_abs_diff 85)
- **Implementation Plan:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md (Phase A checklist, A2 partial, A4 blocked, A5/A6 pending)
- **Fix Plan:** docs/fix_plan.md line 40 (TORCH-GEOMETRY-CONVERGENCE-001 entry, Tier 1 top priority)
- **Spec:** docs/spec-db-workflow.md §Stage A (optimizer convergence), docs/spec-db-core.md §Variance Model (chi-squared definition)
- **Script:** plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py (zero-point check, Adam loop, _stage_a_forward)
- **Closure:** dbex/nanobrag_refinement.py (build_stage_a_lbfgs_closure, U-matrix path ~968-1116)

## Next Up (Optional)

If you finish forward model diagnostic early and find no clear bug:
- **Do NOT proceed to Phase A4** (gradient validation requires D_full variant)
- **Do NOT proceed to Phase A5** (variance telemetry requires deeper instrumentation in closure)
- Instead, add temporary debug logging to `_stage_a_forward` at lines 426-436 to capture A_star, U_matrix, B_ideal_reciprocal tensor values at step 0
- Rerun Phase A2 with debug logging and capture output
- This will provide evidence for next supervisor iteration to decide between Phase A5 (variance analysis) or Phase B (hypothesis testing with bugfix)

## Doc Sync Plan

Not applicable (no tests added/renamed this loop; diagnostic is analysis/evidence-gathering).
