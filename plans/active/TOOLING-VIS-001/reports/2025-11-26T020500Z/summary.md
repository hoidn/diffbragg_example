### Turn Summary
Unified calibration_adjusted_for_n_cells detection in _build_stage_a_params; both engine and inline paths now thread log_scale_baseline_source and spot_scale_override_adjustment_factor into RefinementTelemetry.
DB-AT-029 telemetry verified: log_scale_baseline_source="mapping_global_scale_hint" and spot_scale_override_adjustment_factor match mapping diagnostics (23025916217.587364); test failures (chi² and scale_ratio divergence) expected and deferred.
Next: Supervisor reviews telemetry evidence; if amplitude quantification or implementation defect suspected, pursue callchain analysis or N_cells suppression refinement.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T020500Z/ (pytest_db_at_028_029.log, db_at_029_metrics.json, mapping_context_fixture.json)
