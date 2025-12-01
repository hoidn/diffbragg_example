# Stage C best-snapshot persistence bug (PERF-WARM-SIM-001 Phase D.4)

## Observation
`test_stage_c_detector_microslip` still fails REFINE-007 after ROI closure restoration: both detector sizes show ~+0.067% chi² regression even though detector offsets shrink by 99.99999% and Stage C telemetry now reports `roi_mode`/`validation_scope` correctly (`telemetry_stage_c_full.json`, 2025-12-01T174500Z artifacts).

## Root Cause
While inspecting `dbex/refinement/stage_c_impl.py` we noticed that the LBFGS closure reassigns `best_loss_full_c`, `chi_squared_best_c`, `masked_mse_best_c`, and `best_params_snapshot_c` but never writes the new tuples back into `telemetry_state`:

- `_build_stage_c_lbfgs` sets `chi_squared_best_c = telemetry_state['chi_squared_best_c']` (line ~349) and later `chi_squared_best_c = (...)` inside `closure_stage_c` (lines 618-625) without mutating `telemetry_state`.
- `_run_stage_c_lbfgs` again reads `telemetry_state['chi_squared_best_c']` (line ~686), so it still sees the `(inf, -1)` default, skips the snapshot restore, and appends the degraded final iterate (`chi_squared_trace_full[-1] = 2.1085e+08`) to telemetry even though the first panel-mode validation (iteration 0) matched Stage A (2.1071e+08) — see `telemetry_stage_c_full.json` loss trace.
- The same omission affects `best_params_snapshot_c`, so the optimizer never reloads the optimal `distance_offset_raw` before generating the Stage C `bragg_full` tensor.

## Impact
Stage C always reports the last LBFGS iterate, not the best validation. When panel-mode validations are stricter, the final iterate often regresses compared to Stage A even though earlier snapshots were equal/lower. This explains the reproducible +0.067% regression.

## Fix Outline
Persist best-snapshot tuples back into `telemetry_state` inside `_build_stage_c_lbfgs` and `_run_stage_c_lbfgs`, then reload that snapshot before the final chi² logging/regeneration. Once Stage C telemetry reflects the best validation, REFINE-007 should pass without adjusting tolerances.
