Summary: Wire Stage A telemetry through StageATelemetryCollector so observer callbacks own loss traces, perf counters, and sigma-floor stats before we touch Stage B/C.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-TELEMETRY-001 — Telemetry Observer Refactor
Branch: integration
Mapped tests:
- KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry
- KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=small pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-02T201500Z/

Do Now:
- Implement: dbex/refinement/stage_a.py::_build_lbfgs_closure — Add a StageATelemetryCollector parameter, pull the wrapped StageATelemetryState from `collector.state`, and replace the direct list/counter mutation with `collector.record_step` / `collector.on_step` for every closure evaluation plus `collector.record_validation` / `collector.on_validation` inside the periodic validation branch. Feed the metrics dict with chi², masked MSE, variance-floor clamp/mask counts, and forward-time samples so PHYSICS-LOSS telemetry stays intact.
- Implement: dbex/refinement/stage_a_impl.py::_run_stage_a_lbfgs and StageA.run — Instantiate a StageATelemetryCollector once the helper returns `telemetry_state`, pass it through `_build_lbfgs_closure` and `_run_stage_a_lbfgs`, use the collector to log the baseline, final, and fallback validations (scope="panel" when force_panel_validation else "roi"), and only provide `best_snapshot` payloads when the new chi² beats the current best. After LBFGS completes, call `collector.finalize()` for parity checks and continue building the RefinementTelemetry dict/StageResult exactly as before.
- Tests: Capture fresh evidence by running (1) the engine delegation telemetry selector and (2) the Stage A small-detector smoketest. Save both pytest logs under the artifacts directory (e.g., `pytest_stage_a_engine.log`, `pytest_stage_a_smoke_small.log`).

How-To Map:
1. Code: In `dbex/refinement/stage_a.py`, import `StageATelemetryCollector`, extend `_build_lbfgs_closure`’s signature to accept a `collector`, and route telemetry updates through it. Remove the direct `loss_trace_*`, `chi_squared_trace_*`, `perf_closure_evals`, `perf_validation_runs`, and `masked_mse_*` mutations inside both the closure and validation branches; instead, build a metrics dict (chi², masked MSE, variance-floor counts, forward_time_ms) and call `collector.record_step(...)`. For full validations, build a payload that carries `loss`, `masked_mse`, lifecycle checksums, panel diagnostics, and an optional `best_snapshot` before invoking `collector.record_validation(scope, chi2, ...)`. Keep StageAContext/panel diagnostics logic intact (panel_diag lists still extend via `collector.state.panel_loss_diag`).
2. Code: Thread the collector through `StageA.run` and `_run_stage_a_lbfgs` (dbex/refinement/stage_a_impl.py:1236). Update `_run_stage_a_lbfgs` to call `collector.record_validation` for the baseline, final, and exception paths (respecting ROI vs panel scope) and to rely on the collector’s state for traces/best tracking. After LBFGS, call `collector.finalize()` and optionally assert that `stage_result.to_legacy_dict()` matches the existing telemetry dict before returning the StageResult from `dbex.refinement.stage`. Make sure canonical baseline + perf_counters still use the same values currently written to `/torch_diagnostics`.
3. Tests/Artifacts: Run the two mapped selectors with the prescribed env vars, tee their logs into `plans/active/ARCH-TELEMETRY-001/reports/2025-12-02T201500Z/pytest_stage_a_engine.log` and `.../pytest_stage_a_smoke_small.log`, and double-check that telemetry diffs stay zero.

Pitfalls To Avoid:
- Do not double-increment closure/validation counters; only the collector should mutate those fields.
- Keep `iteration_count` updates consistent (increment once per closure after calling `collector.record_step`).
- Preserve every `/torch_diagnostics` key and StageResult field so downstream tests see identical payloads.
- Maintain ROI vs panel validation behavior (respect `force_panel_validation` for scope strings) and warm-cache panel diagnostics.
- Environment is frozen—no extra deps, no package installs.

If Blocked:
- If the collector path changes the serialized telemetry (diff in `/torch_diagnostics`), capture the before/after dicts plus pytest logs in the artifacts dir, update docs/fix_plan.md Attempts History with the diff summary, and pause implementation until we reconcile the schema.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage telemetry must flow through typed contexts/collectors.
- ARCH-STAGE-CTX-002 — Dict-style telemetry mutation already broke Stage B; avoid repeating it in Stage A.
- PHYSICS-LOSS-001 / PHYSICS-LOSS-003 — Chi² + masked-MSE traces and variance-floor stats must remain spec-compliant.

Pointers:
- dbex/refinement/stage_a.py:82 — `_build_lbfgs_closure` signature and telemetry mutation sites to refactor.
- dbex/refinement/stage_a_impl.py:1236 — `_run_stage_a_lbfgs` baseline/final validation logic.
- dbex/refinement/telemetry_collectors.py:25 — StageATelemetryCollector callbacks/finalize helpers.
- docs/spec-db-workflow.md:48-90 — Telemetry requirements and staging context for Stage A.

Next Up (optional): Stage B observer wiring (Phase C.1) once the Stage A collector path is green.
