### Turn Summary
Centralized the variance-weighted loss helper so Stage A/B/C share one sigma-floor cache and emit canonical chi-squared + detector metadata in telemetry/HDF5.
Refreshed the Stage B/C full-detector smokes and CLI diagnostics metadata test to assert the new canonical telemetry; Stage B needed a rerun after the default timeout, Stage C logged the required ≥80% detector offset reduction.
Next: push the shared helper/telemetry into the DB-AT parity + Stage A regression selectors so mapping/gradcheck evidence reflects the aligned chi-squared schema.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/ (pytest_stage_b_full.log, pytest_stage_c_full.log, telemetry_stage_c.json)

### Turn Summary
Documented the REFINE-SMOKE-CANONICAL telemetry that restored Stage B/C full-detector smokes and unblocked PHYSICS-LOSS-001.
Updated docs/fix_plan.md and plans/active/PHYSICS-LOSS-001/implementation.md so Phase B is marked complete, added Phase D helper work, and rewrote input.md with the shared chi-squared Do Now.
Next: Ralph implements the shared variance helper + telemetry alignment and reruns the Stage B/C full-detector smokes plus CLI metadata test, capturing logs under this artifact set.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/ (input.md)
