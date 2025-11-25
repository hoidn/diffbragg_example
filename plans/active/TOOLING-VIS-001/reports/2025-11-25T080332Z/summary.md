### Turn Summary
Implemented DiffBragg-style nested config_torch schema in capture_smoke_calibration.py so Stage A calibration metadata loads correctly via nanobrag_bridge.load_calibration_metadata.
Regenerated smoke calibration config at sp.proc/calibration/config_torch_smoke.json; mapping probe now shows spot_scale_override≈3.1e+17 (not 1.0) and calibration_path resolves correctly, proving the schema fix works.
DB-AT-028/029 tests ran and persisted full metrics JSONs with calibration provenance; both selectors fail on physics (negative ROI CC, chi²/pixel ~1e5) as expected, not on calibration loading.
Next: isolate the physics gap between mapping forward model and Stage A _build_final_bragg_from_stage_a_telemetry per Phase D.D zero-point probe.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T080332Z/ (capture_smoke_calibration.log, smoke_calibration_manifest.json, mapping_cpu_gpu/mapping_forward_cpu_gpu.json, pytest_db_at_028_029.log, db_at_028/db_at_028_metrics.json, db_at_029/db_at_029_metrics.json)
