### Turn Summary
Implemented apply_calibration_n_cells flag to gate N_cells for small-detector metadata fixtures while preserving full telemetry.
Both DB_AT_028 and DB_AT_029 now emit n_cells_applied=false and n_cells_suppression_reason in mapping_context JSON artifacts; test failures on chi²/ROI gates are acceptable per input.md.
Next: Monitor supervisor feedback on whether additional gate tuning or telemetry analysis is needed.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T220500Z/ (db_at_028/mapping_context_fixture.json, db_at_029/mapping_context_fixture.json)
