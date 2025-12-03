# ARCH-SIM-CONSTRUCTION-001 Phase C.8 — Telemetry Replay Implementation

**Date:** 2025-12-13T120000Z
**Loop:** Ralph implementation
**Status:** Implementation complete, tests still fail (chi²/ROI gates not met)

## Summary

Implemented `param_state` switch in `build_final_bragg_from_stage_a_telemetry()` to replay Stage A telemetry at initial vs final parameter states, and updated `stage_a_smoke_result` fixture to use telemetry replay for both `bragg_before` (initial) and `bragg_after` (final) instead of `simulate_forward_once`. This ensures DB-AT-028/029 measure the same baseline that Stage A used internally, eliminating the double-application of `spot_scale` and aligning the test harness with the Stage A telemetry baseline.

## Changes Implemented

### 1. dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry
- Added `param_state` parameter ("initial"|"final", default="final") to function signature (line 41)
- Implemented helper function `_get_param_value()` (lines 82-94) to extract parameter values by state with fallback logic for legacy telemetry
- Updated parameter extraction to use `_get_param_value()` for all Stage A params (lines 97-103)
- Added misset parameter state handling with fallback chain: initial → delta → zero (lines 106-121)
- Extended log_scale_effective extraction to respect param_state:
  - For `param_state="initial"`: use log_scale_baseline (initial value) to compute scale_factor (lines 311-326)
  - For `param_state="final"`: use recorded scale_factor from telemetry (lines 328-339)

### 2. tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result
- Replaced `simulate_forward_once` call (old lines 176-188) with two `build_final_bragg_from_stage_a_telemetry` invocations:
  - `bragg_before` built with `param_state="initial"` (lines 180-194)
  - `bragg_after` built with `param_state="final"` (lines 197-211)
- Added `bragg_before_source="stage_a_telemetry_initial"` metadata to DB-AT-028 metrics (line 384)
- Added `bragg_before_source="stage_a_telemetry_initial"` metadata to DB-AT-029 metrics (line 473)

## Test Results

**Environment:** DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small
**Command:** pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"

### DB-AT-028 (loss scale sanity)
- **chi²/pixel initial:** 2.097e5 (FAIL, exceeds 1e2 bound)
- **chi²/pixel final:** 2.090e5 (FAIL, exceeds 1e2 bound)
- **log_scale_delta_clamped:** -0.0007 (✓ no saturation)
- **log_scale_baseline:** 22.373427
- **scale_factor (initial):** 5.207816e9
- **bragg_before_mean:** 18.75 ADU
- **target_mean_masked:** 87.12 ADU
- **Ratio (bragg/target):** 0.215 (4.6× too small)

### DB-AT-029 (structure parity)
- **median_corr_before:** -0.054 (FAIL, below 0.2 floor)
- **median_corr_after:** -0.056 (FAIL)
- **bragg_before_mean:** 18.75 ADU (same as DB-AT-028)
- **bragg_before_source:** "stage_a_telemetry_initial" (✓ metadata added)

## Key Findings

1. **Telemetry replay working as designed:** The fixture now rebuilds bragg_before/bragg_after from Stage A's initial/final telemetry parameters, achieving the design goal of Phase C.8 (test harness measures the same baseline Stage A used).

2. **Baseline adjustment confirmed:** log_scale_delta ≈ 0 (was +3.0 in prior loops), proving the masked-intensity baseline correction is working.

3. **Scale factor magnitude issue persists:** scale_factor = 5.2e9 is ~7.5× larger than expected sqrt(spot_scale) ≈ 6.9e8, and bragg_before (18.75 ADU) is 4.6× smaller than target (87.12 ADU).

4. **Improvement from prior loops:** bragg_before/target ratio improved from ~0.047 (47×) to 0.215 (4.6×), but still violates spec gates.

## Suspected Root Causes

1. **Additional calibration factors missing:** The telemetry-replayed bragg_before may be missing intensity calibration factors beyond sqrt(spot_scale) × exp(log_scale_baseline).

2. **DB-AT gates encode pre-adjustment expectations:** The chi²≤1e2 and ROI corr≥0.2 thresholds may have been calibrated against the old (unadjusted) baseline and no longer match the new baseline logic.

3. **Physics/test mismatch:** The persistent 4.6× discrepancy between bragg_before and target_mean_masked may reflect a fundamental issue in how the baseline is computed or how the gates expect the intensity to behave.

## Next Actions

Per repeat-failure guard and escalation requirement:

1. **Supervisor review of scale_factor magnitude:** Investigate why scale_factor (5.2e9) is 7.5× larger than expected sqrt(spot_scale) (6.9e8). Does this represent missing baseline corrections or incorrect calibration metadata?

2. **DB-AT-028/029 gate recalibration (spec_change):** If the new baseline logic is correct, the acceptance thresholds (chi²≤1e2, ROI≥0.2) may need adjustment to match the new baseline behavior.

3. **Architecture/physics investigation:** If neither (1) nor (2) resolve the issue, this may indicate a deeper architectural or physics mismatch requiring a new initiative.

## Artifacts

- **pytest log:** pytest_db_at_028_029.log
- **DB-AT-028 metrics:** db_at_028/db_at_028_metrics.json
- **DB-AT-029 metrics:** db_at_029/db_at_029_metrics.json
- **Mask coverage:** db_at_028/mask_coverage.json, db_at_029/mask_coverage.json

## Commit

**Commit:** 209e0bc8
**Message:** ARCH-SIM-CONSTRUCTION-001 reconstruction: Align DB-AT-028/029 baseline with Stage A telemetry

## Repeat-Failure Guard Status

Multiple implementation attempts (C.1-C.8) have completed scale/baseline alignment work, but DB-AT-028/029 continue to fail with persistent chi²/ROI signatures. This suggests the issue may lie in:
- Spec/test mismatch (gates inconsistent with new baseline)
- Missing implementation logic (additional calibration factors)
- Architecture/physics issue (fundamental mismatch in intensity modeling)

**Recommendation:** Escalate to Galph for spec/harness review per repeat-failure guard.
