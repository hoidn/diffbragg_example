### Turn Summary
Implemented sigma-map cropping so CLI diagnostics can consume metadata sigma tiles for the small-detector fixture without shape mismatch errors; DB-AT-028/029 now execute and archive metrics.
Resolved the blocking ValueError with explicit pickle crop (1024×1024 window); remaining assertion failures (chi²/pixel 11756, ROI CC 0.047) are separate calibration issues requiring spot_scale investigation.
Next: investigate calibration mismatch (spot_scale_override 3.1e17 vs expected ~1e0) causing negative ROI CC; verify mapping/Stage A use consistent calibration assets.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T093626Z/ (crop_sigma_map_report.json, mapping_forward_cpu_gpu.json, db_at_028_metrics.json, pytest_db_at_028_029.log)
