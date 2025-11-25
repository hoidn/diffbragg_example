### Turn Summary
Implemented refined HKL default logic across Stage A fixtures and mapping helpers so calibration presence automatically selects refined structure factors.
Both DB-AT-028/029 selectors now archive telemetry showing `hkl_source="refined"` and `hkl_path` pointing to `sp.proc/calibration/smoke_refined_structure_factors.mtz`; tests failed on chi²/pixel thresholds (expected) but telemetry capture succeeded.
Next: supervisor can proceed with physics investigation knowing HKL/calibration defaults are aligned across fixtures and probes.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T203500Z/ (pytest_db_at_028_029.log, mapping_context_fixture.json for both selectors)
