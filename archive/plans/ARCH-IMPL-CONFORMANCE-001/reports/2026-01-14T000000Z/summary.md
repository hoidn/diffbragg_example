# Loop i=111: Phase B.1-B.2 Implementation

## Turn Summary

Shipped canonical scaling utility apply_sqrt_spot_scale() with 11/11 unit tests passing. Threaded calibration_metadata parameter to reconstruction cold path for explicit calibration control. Warm-cache regression test passed; cold-path baseline remains failing as expected pending Phase B.3-B.4 refactor. Next: refactor stage_a.py:442-443 to use canonical API.

Artifacts: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/pytest_phase_b1_unit.log, pytest_phase_a1_regression.log

---

## Test Results

Unit tests: 11/11 PASSED (tests/dbex/refinement/test_scaling_utils.py, 2.05s)
Warm-cache regression: PASSED (test_stage_a_vs_reconstruction_scale, 9.54s)  
Cold-path baseline: Expected FAIL (deferred to Phase B.3-B.4)

## Files Changed

Created:
- dbex/refinement/scaling_utils.py (112 lines) - canonical apply_sqrt_spot_scale API
- tests/dbex/refinement/test_scaling_utils.py (134 lines) - 11 unit tests
- tests/dbex/refinement/__init__.py (1 line)

Modified:
- dbex/refinement/reconstruction.py - added calibration_metadata parameter, threaded to cold-path

Total: +254 lines, -2 lines (4 files)

## Next Steps

Phase B.3: Refactor stage_a.py:442-443 to use canonical apply_sqrt_spot_scale()
Phase B.4: Refactor reconstruction.py:203-208 to use canonical API  
Expected outcome: cold-path baseline test passes (rel_error <1%, currently ~64.7%)
