### Turn Summary
Fixed the scale-chain probe to plumb calibration_config_path correctly for calibrated permutations, enabling trustworthy telemetry capture.
Resolved the bug where calibrated cases always reported spot_scale_override=1.0 by accepting and passing calibration_path through compute_case_metrics().
Next: rerun the full geometry/scale analysis now that probe telemetry is reliable, or proceed with DB-AT-028/029 physics investigation.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T114730Z/ (scale_chain_probe/scale_chain_metrics.json, db_at_028/db_at_028_metrics.json, db_at_029/db_at_029_metrics.json, pytest logs)
