### Turn Summary
Extended compare_mapping_dataset_metrics.py with metadata_calibrated_drop_ncells case to isolate N_cells amplitude impact; propagated n_cells telemetry and masked/unmasked means into metrics.
Quantified N_cells suppression effect: bragg_mean collapses from 1.80 ADU (N_cells applied) to 0.00 ADU (N_cells suppressed) — 99.7% reduction confirming spot_scale_override alone cannot restore amplitudes without crystal volume scaling.
Next: supervisor to assess amplitude quantification; consider refitting spot_scale_override for small-detector calibration without N_cells if amplitude restoration needed for DB-AT-028/029.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T230500Z/ (mapping_dataset_metrics.json, probe.log, db_at_028/mapping_context_fixture.json, db_at_029/mapping_context_fixture.json, pytest_db_at_028_029.log)
