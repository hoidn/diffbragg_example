### Turn Summary
Implemented Stage A log-scale baseline derivation from warmed simulators when calibration is adjusted for N_cells, achieving telemetry alignment with the mapping stack.
Fixed initial bug using global_scale_hint instead of masked target mean; corrected to compute log(target_mean_masked / model_mean_masked_stage_a) from actual simulator output.
Next: investigate remaining chi²/pixel and ROI correlation physics failures (likely ~1° U-matrix rotation geometry mismatch per prior diagnosis).
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/ (pytest_db_at_028_029.log, db_at_028/db_at_029_metrics.json)
