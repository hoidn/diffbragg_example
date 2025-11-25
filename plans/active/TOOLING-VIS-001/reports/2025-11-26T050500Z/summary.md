### Turn Summary
Implemented zero-iteration masked-mean baseline computation in _build_stage_a_params; extracted and persisted target_mean_masked, model_mean_masked, log_scale_baseline_source, and spot_scale_override_adjustment_factor in RefinementTelemetry.
DB-AT-028/029 tests collected (2/2) and executed; both FAILED with known chi²/pixel violations (2.097e+05 vs 1e2 spec), but telemetry fields correctly populated and scale_ratio parity achieved (within 0.01% tolerance).
Next: investigate model_mean_masked=1.67e-8 (pathologically low zero-iteration Bragg intensity) to address chi²/pixel gate failures; likely requires calibration plumbing debug in simulate_forward_once or Stage A context builder.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/ (pytest_db_at_028_029.log, db_at_028_metrics.json, db_at_029_metrics.json)
