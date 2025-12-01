Summary: Restore Stage A telemetry baselines so Stage B/C smokes see real Δχ² traces and Stage C can seed its canonical snapshot from Stage A’s final chi-squared.
Mode: Parity
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T095317Z/
Do Now:
- Implement: dbex/refinement/stage_a_impl.py::_run_stage_a_lbfgs (plus the closure helper) — capture a full-loss/chi-squared evaluation before LBFGS runs so `loss_trace_full`, `chi_squared_trace_full`, and `best_loss_full` always include the Stage A baseline; make sure the final evaluation is appended even when early-stop or zero-iteration exits occur, and propagate that canonical snapshot back to `telemetry_state` so downstream stages never see empty traces.
- Implement: dbex/refinement/stage_c.py::StageC.run (and dbex/refinement/engine.py::RefinementEngine.run) — assert that Stage A telemetry handed to Stage C contains a baseline and final entry, raise a clear error when it does not, and set Stage C’s `canonical_chi_squared`/`chi_squared_trace_full[0]` directly from Stage A’s final chi-squared before running `_run_stage_c_lbfgs`, keeping telemetry parity with the inline path.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T095317Z/telemetry_stage_bc_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T095317Z/pytest_stage_bc_small.log
How-To Map:
1. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T095317Z/collect_stage_bc_small.log
2. In `dbex/refinement/stage_a_impl.py::_run_stage_a_lbfgs`, run `compute_loss(full_stage_a_indices, is_full=True)` once before `optimizer.step(closure)` to append the Stage A baseline into `loss_trace_full`, `chi_squared_trace_full`, and `masked_mse_trace_full`, and guard against empty traces by appending the final evaluation again when the optimizer exits without hitting another validation point; update the `canonical_baseline`/`best_loss_full` bookkeeping so downstream stages inherit that snapshot.
3. In `dbex/refinement/stage_c.py::StageC.run` (and the engine telemetry pass-through), check that `stage_a_telemetry` contains at least two full-trace entries; if not, raise `RuntimeError` instructing callers to repair Stage A telemetry; otherwise copy Stage A’s final chi-squared into `telemetry_c.canonical_chi_squared` and enforce equality (±1e-3) before running `_run_stage_c_lbfgs` so Stage C’s initial chi-squared matches Stage A’s final result.
4. Re-run the Stage B + Stage C smoke selector command above with `DBEX_SMOKE_TELEMETRY_PATH` pointed at the new artifacts directory; archive the pytest log plus the telemetry JSON under `plans/active/ARCH-REFINE-001/reports/2025-12-01T095317Z/`.
Pitfalls To Avoid:
- Do not relax REFINE-007/REFINE-007-EXT acceptance gates; the fix must restore real Stage A improvements instead of downgrading the checks.
- Keep PERF-WARM-011 CPU fallback logic intact when touching Stage A traces (ROI vs panel distinctions cannot regress).
- Maintain PHYSICS-LOSS-001/002 telemetry fields; every change should continue emitting chi-squared + masked-MSE traces and variance-floor stats.
- Preserve existing `RefinementTelemetry` schema (engine_protocol, stage_modes) when adding new guards; no renaming or key churn.
- Avoid device/dtype hardcoding in the new baseline evaluation (respect config.device and dtype throughout the extra compute_loss pass).
- Do not suppress exceptions silently; if Stage A telemetry is still empty after the patch, raises must point at the exact selector and command to reproduce.
- Stay within Environment Freeze (POLICY-001); no dataset copies or package installs to work around the missing refGeom_small bundle.
- When writing new telemetry evaluations, reuse the existing `perf_validation_runs` counters so perf evidence stays accurate.
If Blocked:
- Capture the failing pytest log under `plans/active/ARCH-REFINE-001/reports/2025-12-01T095317Z/blocked_stage_bc.log`, note the selector + env vars in `docs/fix_plan.md` Attempts History, and log the same synopsis in `galph_memory.md` before marking the item blocked.
Findings Applied (Mandatory):
- REFINE-FLOW-001 — Stage A→B/C parameter reconstruction must see identical chi-squared baselines between stages.
- REFINE-007 / REFINE-007-EXT — Stage C detector offsets are validated via telemetry; gates remain active.
- ARCH-ENGINE-003 — Engine protocol/mode enrichment must persist through the telemetry changes.
- PHYSICS-LOSS-001/002 — Dual loss metrics and variance-floor statistics are required for every stage.
- PERF-WARM-011 — Stage A ROI/panel mode telemetry drives CPU fallback decisions; do not regress it.
Pointers:
- dbex/refinement/stage_a_impl.py:1682 — periodic validation currently starts after the first LBFGS iteration.
- dbex/refinement/stage_a_impl.py:1738 — `_run_stage_a_lbfgs` is where we can inject the pre-optimization evaluation and final fallback.
- dbex/refinement/stage_c.py:150 — Stage C currently trusts Stage A telemetry without guarding for empty traces.
- docs/spec-db-workflow.md:33 — engine contract that requires Stage C initial chi-squared to equal Stage A final.
Next Up (optional):
1. After telemetry baselines are fixed, resume Phase B (RefinementContext/JobContext) so Stage wrappers stop passing loose dicts.
2. Follow up on RefinementConfig attribute drift (missing telemetry_output_dir/log_cell_max_delta guards) noted in Phase A.3 once Stage C smokes stabilize.
