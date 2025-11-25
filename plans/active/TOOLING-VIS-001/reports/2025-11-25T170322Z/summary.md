### Turn Summary
Threaded apply_calibration_n_cells gate through RefinementConfig and all Stage A context builders; N_cells suppression now works correctly for small-detector metadata fixtures.
Discovered scale baseline bug: warmed simulators produce raw intensities without applying spot_scale_override, causing chi² to remain at 1.5e+05 even though log_scale_baseline derivation is correct.
Next: modify Stage A compute_loss to apply sqrt(spot_scale_override) multiplicatively to Bragg tensor when calibration_adjusted_for_n_cells flag is set.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/ (pytest_db_at_028_029.log, db_at_028/db_at_028_metrics.json)
