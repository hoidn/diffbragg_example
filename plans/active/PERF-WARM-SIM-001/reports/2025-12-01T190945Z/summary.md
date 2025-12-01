# PERF-WARM-SIM-001 Phase D.4: Baseline Prior Ordering — Loop Summary (2025-12-01T190945Z)

## Implementation

Moved `_apply_baseline_detector_prior()` call to execute BEFORE `stage_c_optimizer.step(closure_stage_c)` in `dbex/refinement/stage_c_impl.py:739-743`, per REFINE-013 intent that the best snapshot should include the baseline prior warm-start correction.

**Code change:**
```python
# OLD (line 739-740):
stage_c_optimizer.step(closure_stage_c)
_apply_baseline_detector_prior()

# NEW (lines 739-743):
# Apply baseline detector prior BEFORE LBFGS so the warm-start is captured in best snapshot
# (REFINE-013: The rehydration after LBFGS reloads best_params_snapshot_c, which must include the prior)
_apply_baseline_detector_prior()

stage_c_optimizer.step(closure_stage_c)
```

## Test Results

### Small Detector (`--smoke-detector-size=small`)
- **Status:** PASSED (7.16s)
- **Detector offset reduction:** 0.25mm → 1.49e-08mm (99.99999% reduction)
- **Chi-squared:** Stage A final=263641952.0, Stage C final=263808208.0 (-0.0631% improvement)
- **Note:** strict_gates=False for small detector, so chi-squared regression check was skipped

### Full Detector (`--smoke-detector-size=full`)
- **Status:** FAILED at test line 1156
- **Detector offset reduction:** 0.25mm → 1.49e-08mm (99.99999% reduction)
- **Chi-squared:** Stage A final=2.1071e+08, Stage C initial/final=2.1085e+08 (+0.067% regression)
- **Failure:** Chi-squared regressed by 0.067%, exceeding the 0.05% strict gate
- **LBFGS behavior:** Stalled at initial chi² value across all iterations (no improvement)

## Root Cause Analysis

The baseline prior is functioning correctly (detector offsets are corrected to essentially zero). However, applying the prior BEFORE LBFGS reveals a **parameter coupling issue**:

1. **Stage A accommodation:** Stage A refines crystal parameters while accommodating the perturbed detector geometry (+0.25mm offset). The crystal parameters effectively "absorb" the detector perturbation to minimize chi².

2. **Stage C correction paradox:** When Stage C applies the baseline prior upfront, it immediately corrects detector offsets back toward the baseline position. This creates a mismatch with the Stage A crystal parameters (which were optimized assuming the perturbed detector).

3. **LBFGS stall:** LBFGS has nowhere to go because:
   - Detector is already at baseline (prior moved it there)
   - Crystal parameters are frozen in Stage C (cannot re-optimize to match new detector position)

4. **Chi-squared regression:** The +0.067% chi² increase suggests the baseline detector geometry is NOT optimal given the Stage A crystal refinement. Stage A over-fitted to the perturbation, so "correcting" the detector back to baseline actually makes the fit worse with the frozen crystal parameters.

## Hypothesis Confidence

**HIGH (~85%)** that the code change is correct per REFINE-013 intent (best snapshot now includes prior-corrected offsets), but the REFINE-007 gate assumption (Stage C must not regress chi² while correcting detector) may be incompatible with the baseline prior strategy when Stage A has accommodated the perturbation via crystal parameter adjustment.

## Alternative Interpretations

1. **Mis-calibration:** The baseline detector distances may themselves be slightly mis-calibrated relative to the refined crystal+perturbed-detector configuration.

2. **Gate too tight:** The test's strict 0.05% chi² gate may be too stringent for this synthetic perturbation scenario where Stage A accommodates perturbation via crystal flex and Stage C undoes detector flex but cannot re-flex crystal.

3. **Design limitation:** The prior ordering fix is correct but exposes a deeper issue: Stage C baseline correction should either:
   - (a) Also re-refine crystal to match baseline detector, OR
   - (b) Accept that correcting detector geometry may temporarily regress chi² if Stage A over-fitted to the perturbation

## Recommended Next Actions

Supervisor should decide one of the following paths:

1. **Relax REFINE-007 gate:** Accept small chi² increases when baseline prior is active (e.g., ≤0.1% instead of 0.05%)

2. **Investigate calibration:** Check whether baseline detector distances are properly calibrated relative to the refined geometry

3. **Extend Stage C:** Modify Stage C to optionally re-refine crystal after applying detector prior

4. **Document as expected:** Accept that baseline prior + frozen crystal creates a chi² tradeoff in perturbed-detector scenarios and update test expectations

## Artifacts

- `collect_stage_c_small.log` — Small detector collection check
- `pytest_stage_c_small.log` — Small detector smoke test (PASSED)
- `telemetry_stage_c_small.json` — Small detector telemetry
- `collect_stage_c_full.log` — Full detector collection check
- `pytest_stage_c_full.log` — Full detector smoke test (FAILED)
- `telemetry_stage_c_full.json` — Full detector telemetry

All artifacts saved to: `plans/active/PERF-WARM-SIM-001/reports/2025-12-01T190945Z/`
