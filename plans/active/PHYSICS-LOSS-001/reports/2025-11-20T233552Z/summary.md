### Turn Summary
Implemented variance-weighted chi-squared loss and dual-metric telemetry (chi_squared + masked_mse) for Stage B/C refinement loops, completing PHYSICS-LOSS-001 checklist items B2b, B2c, and B3.
Fixed Stage C loss computation bug (incorrect normalization), extended RefinementTelemetry dataclass with six new fields, updated all three stages to track both metrics in parallel, and persisted them to HDF5 via updated _write_torch_outputs function.
CLI diagnostics unit test PASSED; Stage B/C smoke tests running in background to validate full integration (expected runtime ~5 minutes each).
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T233552Z/ (pytest_cli_diag.log PASSED, pytest_stage_b.log + pytest_stage_c.log pending completion)
