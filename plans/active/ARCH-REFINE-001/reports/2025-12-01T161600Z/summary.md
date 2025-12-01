### Turn Summary
Factored the REFINE-FLOW-001 baseline parity guard into `_check_stage_b_baseline_parity` helper in `dbex/refinement/stage_b_impl.py` so the guard logic can be unit-tested without constructing optimizers; updated `_run_stage_b_lbfgs` to call the helper; rewrote `test_stage_b_baseline_guard_diff_payload` to drive the helper directly with mocked loss functions testing both failure (>0.1% drift → RuntimeError + JSON) and passing (<0.1% → None path) cases.
All validation passed: guard test PASSED (0.76s), Stage B/C small smokes PASSED (27.63s, 2/2 tests green), telemetry schema preserved.
Next: Continue ARCH-REFINE-001 modularization by creating RefinementContext/JobContext dataclasses to replace ad-hoc dict plumbing.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T161600Z/ (collect_stage_b_guard.log, pytest_stage_b_guard.log, collect_stage_bc_small.log, pytest_stage_bc_small.log, telemetry_stage_bc_small.json)
