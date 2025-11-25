### Turn Summary
Implemented calibration-variant probe in compare_mapping_dataset_metrics.py to isolate which DiffBragg calibration fields flip Stage-A ROI correlations negative.
Evidence captured: N_cells removal restores positive median ROI CC (+0.047) from negative baseline (-0.053); spot_scale=1 alone keeps CC negative but zeroes Bragg intensities.
Next: analyze why N_cells presence causes negative correlations and plan Stage A calibration bugfix (either sanitize capture output or adjust simulate_forward_once scaling).
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T133505Z/mapping_dataset_metrics/ (mapping_dataset_metrics.json, 4×16 ROI PNG/NPZ bundles, calibration_variants/*.json), db_at_028/db_at_029/ (mapping_context_fixture.json, roi_correlation_diagnostics.json, pytest logs)
