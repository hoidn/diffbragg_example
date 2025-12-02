Summary: Ensure Stage C telemetry always emits sample traces and variance-floor counters so REFINE-007/PHYSICS-LOSS-001 gates read meaningful data before rerunning the parity smoketests.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-TELEMETRY-001 — Telemetry Observer Refactor
Branch: integration
Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T233500Z/pytest_stage_b_guard.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T233500Z/pytest_stage_b_smoke.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T233500Z/pytest_stage_c_smoke.log
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T233500Z/
Do Now:
- Implement: dbex/refinement/telemetry_collectors.py::StageCTelemetryCollector (add a helper that can seed a baseline sample in the wrapped StageCTelemetryState without bumping closure evals) and dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs (invoke the helper whenever `loss_trace_sample` stayed empty, keep baseline chi²/MSE handy, and wire `variance_floor_{masked,clamped}_pixels` from the finalized collector into the RefinementTelemetry constructor so the PHYSICS-LOSS counters reach `/torch_diagnostics`). Keep the changes scoped to Stage C; Stage A/B telemetry should not be touched this loop.
- Tests: run the three selectors above with the canonical env flags and tee the logs into the new artifacts directory; stop on the first failure, capture the log, and note the failure signature in docs/fix_plan.md if anything regresses.
How-To Map:
1. Telemetry collector helper — in `StageCTelemetryCollector`, add a method such as `ensure_sample_trace(*, loss, metrics)` that appends to `loss_trace_sample`, `chi_squared_trace_sample`, and `masked_mse_trace_sample` only when they are empty. This method must not touch `perf_closure_evals` so we can seed a baseline sample without fabricating closure counts; reuse the iteration stored in `_state.iteration_count[0]` only to keep chi²/MSE arrays aligned.
2. `_run_stage_c_lbfgs` wiring — cache the baseline chi²/MSE computed before `stage_c_optimizer.step(closure_stage_c)` and call the new helper immediately after the fallback guard (or just before finalizing) whenever `telemetry_state.loss_trace_sample` is still empty. After `collector.finalize()` unwrap `variance_floor_{masked,clamped}_pixels` along with the existing traces and pass those integers into the `RefinementTelemetry` constructor so `/torch_diagnostics` reports clamp counts again. Keep the existing improvement gate (`stage_c_min_loss_improvement`) and best-snapshot logic untouched.
3. Validation — rerun the Stage B parity guard, Stage B shell smoke, and Stage C small-detector smoke with the env block above and tee the logs into `pytest_stage_b_guard.log`, `pytest_stage_b_smoke.log`, and `pytest_stage_c_smoke.log` under the new artifacts path.
Pitfalls To Avoid:
- Do not modify Stage A/B telemetry or the writer in this loop; ARCH-TELEMETRY-001 Phase C is scoped to Stage C until the collector path is stable.
- Keep the Environment Freeze intact—no package installs, torch upgrades, or cudatoolkit changes.
- Preserve REFINE-007/011/012 semantics: Stage C validations still force panel mode when Stage A telemetry says so, and ROI/panel scopes must be recorded accurately in telemetry.
- Never edit the LBFGS improvement gates; only seed telemetry for observability.
- Avoid mutating `telemetry_state` directly; go through the collector helper so StageResult serialization stays consistent.
- Make sure the synthetic sample does not increment `perf_closure_evals`; tests inspect that counter when diagnosing early stops.
- Capture artifacts even on failure; the supervisor plan requires the log files in the new report directory.
- Keep the canonical env variables (KMP_DUPLICATE_LIB_OK, NANOBRAGG_DISABLE_COMPILE, DBEX_SMOKE_DETECTOR_SIZE) on every pytest run so perf/telemetry deltas stay apples-to-apples.
If Blocked:
- If any selector fails, stop immediately, tee the failing log into the artifacts directory, annotate docs/fix_plan.md with the failure signature plus env knobs, and ping Galph before attempting ad-hoc fixes—the observer migration is the only allowed code touch this loop.
Findings Applied (Mandatory):
- PHYSICS-LOSS-001 (docs/findings.md:35) — Stage C telemetry must report variance-weighted chi²/variance floor stats so parity gates stay meaningful.
- REFINE-007 (docs/findings.md:60) — Stage C detector smokes rely on telemetry to prove ≥80% offset reduction with ≤0.05% χ² regression.
- REFINE-012 (docs/findings.md:73) — When Stage A forces panel validations, Stage C closures/telemetry must run in panel mode as well; keep the ROI/panel markers accurate.
Pointers:
- docs/fix_plan.md:108 — latest attempt entry detailing the Stage C sample-trace + variance telemetry work scope.
- plans/active/ARCH-TELEMETRY-001/implementation.md:93 — Phase C checklist bullets describing the baseline sample helper + variance-floor wiring deliverable.
- docs/spec-db-core.md:106 — normative variance-weighted chi² definition that telemetry must reflect.
- docs/spec-db-workflow.md:81 — Stage C detector stage contract (panel vs ROI behavior, optimizer expectations).
Next Up: Once Stage C telemetry matches spec, Phase C.2 can move on to the writer/StageResult plumbing.
Doc Sync Plan: none — no new selectors or registry changes required once tests stay green.
Mapped Tests Guardrail: Existing selectors already collect (>0); no new authoring needed before implementation.
Hard Gate: Do not land if any mapped selector fails or if Stage C telemetry still lacks sample traces/variance stats; rerun until both criteria are satisfied.
Normative Math/Physics: Follow docs/spec-db-core.md §Objective Function (line 106) for variance-weighted chi² and docs/spec-db-workflow.md §Stage C (line 81) for detector refinement semantics; the telemetry fix must not alter the underlying optimization math.
