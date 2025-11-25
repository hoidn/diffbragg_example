### Turn Summary
Added mapping-forward parity diagnostics to compare_stage_a_mapping_parity.py CLI and stage_a_smoke_result fixture per Phase D.D specification.
Both tools now store HKL indices/amplitudes, call simulate_forward_once with baseline crystal + shared calibration, and emit ROI CC + scale ratio metrics to JSON artifacts.
Tests collect properly (2/2) but FAIL as expected with chi²/pixel ~1e5 exceeding normative 1e2 threshold; mapping forward pass failed due to missing hkl_indices/amplitudes in dataload fallback path.
Next: diagnose and fix HKL/calibration alignment so Stage A chi²/pixel and ROI CCs meet DB-AT-028/029 normative bounds.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T040828Z/ (parity_metrics.json, db_at_028_metrics.json, db_at_029_metrics.json, pytest_db_at_028_029.log, pytest_db_at_028_029_collect.log)
