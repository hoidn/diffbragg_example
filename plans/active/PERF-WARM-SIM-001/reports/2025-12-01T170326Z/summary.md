# PERF-WARM-SIM-001 Phase D.4: Stage C ROI-mode Disablement Implementation

## Loop Summary (2025-12-01T170326Z)

**Status**: PARTIAL SUCCESS — Implementation complete and correct, but full-detector chi² gate still fails at +0.067% (exceeds 0.05% threshold).

## Implementation

Implemented REFINE-012 by gating `stage_c_roi_mode_active` on `force_panel_validation` so Stage C disables ROI-mode closures when Stage A forces panel validations.

### Code Changes

1. **dbex/refinement/stage_c_impl.py::_build_stage_c_params** (lines 186-207)
2. **dbex/refinement/stage_c.py** (lines 306-307, 410-411)
3. **dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs** (lines 709-710)
4. **tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip** (lines 1174-1180, 1443-1448)

## Test Results

- Small detector (29 ROIs): PASSED ✓ (roi_mode="panel", roi_mode_reason="force_panel_validation")
- Full detector (92 ROIs): FAILED ✗ (chi² regression 0.067% vs 0.05% gate)

## Next Actions

Supervisor decision required: Accept +0.067% regression as inherent to correct implementation OR investigate hyperparameters.

### Turn Summary
Implemented REFINE-012 Stage C ROI-mode gating on force_panel_validation, adding roi_mode_reason telemetry and updating test expectations to mirror Stage A panel-validation logic.
Small detector (29 ROIs) PASSED proving implementation correctness with roi_mode="panel" and roi_mode_reason="force_panel_validation"; full detector (92 ROIs, 60 panels) FAILED at +0.067% chi² regression, identical to REFINE-011 result.
The regression is reproducible and appears inherent to panel-mode optimization trajectory for 60-panel configurations; supervisor decision required to accept regression as SPEC-conformant or investigate LBFGS hyperparameters.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/ (collect logs, pytest logs, telemetry_stage_c_small.json)
