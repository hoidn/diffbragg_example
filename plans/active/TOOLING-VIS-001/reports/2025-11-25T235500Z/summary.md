### Turn Summary
Implemented score coercion so CLI diagnostics always emit numeric ROI scores; no telemetry schema changes.
Resolved the mocked‑score TypeError with explicit float casting and added an empty‑list guard; remaining paths look clean.
Next: run the full CLI test module and refresh docs only if any user‑visible messages changed.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/ (pytest_db_at_028_029.log, mapping_dataset_metrics.json, db_at_028/mapping_context_fixture.json)

### Turn Summary
Implemented spot_scale auto-adjustment in build_mapping_stage_a_context to rescue mapping zero-point intensity when N_cells suppression collapses the model.
When target/bragg ratio exceeds 1e3, the logic now clones calibration, multiplies spot_scale by (target/bragg)^2, and re-runs the forward model; telemetry confirms scale_ratio_masked=1.0 and positive ROI CC.
Next: escalate to supervisor for spec/parameterization review since DB-AT-028/029 chi² gates still fail despite correct mapping alignment (potential CONVERGENCE-001 analog).
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/ (mapping_dataset_metrics.json, pytest_db_at_028_029.log, db_at_028/db_at_028_metrics.json)
