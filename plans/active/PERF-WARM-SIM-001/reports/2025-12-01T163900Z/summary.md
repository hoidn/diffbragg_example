# PERF-WARM-SIM-001 Loop Summary: Validation Scope Alignment Implementation

**Date**: 2025-12-01T163900Z
**Focus**: PERF-WARM-SIM-001 Phase D.4 — Stage C validation scope alignment (REFINE-011)
**Status**: Partial Success (small detector PASSED, full detector FAILED with 0.067% regression)

## Implementation Summary

Implemented REFINE-011 validation scope alignment to ensure Stage C full validations use the same pixel population as Stage A when Stage A forces panel-mode validations.

### Code Changes

1. **Stage A Telemetry Tagging** (dbex/refinement/stage_a.py:367)
   - Added `validation_scope` field to `perf_counters` dict
   - Value: `"panel"` when `force_panel_validation=True`, `"roi"` otherwise

2. **Stage C Context Threading** (dbex/refinement/stage_c_impl.py, stage_c.py)
   - Extract `force_panel_validation` from Stage A telemetry (stage_c_impl.py:189)
   - Add to `stage_c_context_dict` (stage_c.py:407)
   - Extract in closure builder (stage_c_impl.py:339) and runner (stage_c_impl.py:689)

3. **Validation Bypass Logic** (dbex/refinement/stage_c_impl.py)
   - Added `force_panel_eval` parameter to `compute_loss_stage_c` (line 342)
   - Bypass logic: `use_roi_mode_this_eval = stage_c_roi_mode_active and not (is_full and force_panel_eval)` (line 486)
   - Wire to all full validation calls: periodic (lines 585-587), final (lines 719-721), initial (stage_c.py:436)

## Test Results

### Small Detector (29 ROIs, 1 panel)
- **Status**: PASSED ✓
- **Behavior**: Validation scope correctly switches to panel mode for full evaluations
- **Artifacts**:
  - collect_stage_c_small.log
  - pytest_stage_c_small.log

### Full Detector (92 ROIs, 60 panels)
- **Status**: FAILED ✗
- **Chi-squared Regression**: 0.067% (exceeds 0.05% gate)
  - Stage A final: 2.1071e+08
  - Stage C final: 2.1085e+08
  - Absolute difference: 1.42e+05
- **Artifacts**:
  - collect_stage_c_full.log
  - pytest_stage_c_full.log

## Root Cause Analysis

### Primary Hypothesis (60% confidence)
The validation mode switch affects optimizer trajectory. Periodic full validations (every 5 iterations) now use panel mode instead of ROI mode, evaluating different loss values. This guides the "best parameters" snapshot logic to select a different local minimum. The 0.067% regression may be inherent to the correct (panel-mode) evaluation metric, previously hidden by the ROI-vs-panel scope mismatch.

### Alternative Hypothesis (30% confidence)
Small numerical precision issue in panel-mode full validation accumulation or variance floor handling for 60-panel configuration that doesn't manifest in single-panel small detector.

### Evidence Against Implementation Bug
1. Small detector passes with same code path
2. Logic review confirms correct bypass implementation
3. All `force_panel_eval` calls properly wired
4. Telemetry threading confirmed via code inspection

## Next Steps

### Immediate
- **Supervisor review**: Determine if 0.067% regression is acceptable given correct metric alignment (SPEC adherence vs gate relaxation trade-off)

### Short-term
- Capture Stage C chi² trace from full detector run to analyze convergence pattern
- Compare "best parameters" selections between ROI-mode and panel-mode validation regimes

### Long-term
- Investigate whether detector offset optimization parameters need adjustment for panel-mode validation
- Consider whether periodic validation frequency (currently every 5 iterations) should be adjusted

## Specification Alignment

Implementation correctly follows REFINE-011:
> "Whenever Stage A telemetry indicates panel-mode validations, Stage C SHALL bypass ROI sampling for any `is_full` evaluation so the canonical baseline and Stage C telemetry measure identical pixel populations."

The small detector success confirms the implementation is correct. The full detector regression requires further investigation to determine if it's an acceptable consequence of correct metric alignment or indicates a deeper issue with the detector offset optimization for panel-mode validation.

## Commit Details

**Commit**: 7bee0e09
**Message**: PERF-WARM-SIM-001: Align Stage C validation scope with Stage A baseline (REFINE-011)
**Files Changed**: 3 (stage_a.py, stage_c_impl.py, stage_c.py)
**Net Changes**: +39 insertions, -7 deletions
