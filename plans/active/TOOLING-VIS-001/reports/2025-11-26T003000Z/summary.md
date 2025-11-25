### Turn Summary
Implemented mapping-aware log-scale baseline override to prevent double-application when mapping adjusts spot_scale_override for N_cells suppression.
Added Priority 4 baseline selection using global_scale_hint when calibration_adjusted_for_n_cells=True; extended RefinementTelemetry (both definitions) with log_scale_baseline_source and spot_scale_override_adjustment_factor fields.
Next: investigate why telemetry fields remain null in artifacts (calibration adjustment flag may not be set for small-detector case or ratio check not triggered).
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T003000Z/ (pytest_db_at_028_029_retry.log, db_at_028/db_at_028_metrics.json)
