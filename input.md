Summary: Wire Stage B/C telemetry to the observer collectors so StageBTelemetryCollector/StageCTelemetryCollector own all loss traces, variance stats, and validation payloads before writer/engine consume the typed StageResult outputs.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-TELEMETRY-001 — Telemetry Observer Refactor
Branch: integration
Mapped tests:
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T120000Z/
Do Now:
- Implement: dbex/refinement/telemetry_collectors.py::{StageBTelemetryCollector,StageCTelemetryCollector}; dbex/refinement/stage_b.py::{_build_lbfgs_closure,run}; dbex/refinement/stage_b_impl.py::_run_stage_b_lbfgs; dbex/refinement/stage_c.py::{_build_lbfgs_closure,run}; dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs so Stage B/C closures emit telemetry solely through the observer collectors (baseline, periodic, and final validations) and no longer mutate telemetry_state dicts.
- Validate: capture logs for the mapped pytest selectors and drop them into the artifact directory (separate log per selector).
How-To Map:
1. Expand `StageBTelemetryCollector` so `on_validation` and `finalize()` record tupled iteration entries, variance counters, baseline diagnostics, and best snapshots; update `StageCTelemetryCollector` to accept `panel_diag` payloads and track `(iteration, value)` tuples for chi²/masked MSE plus best-loss tuples.
2. Update `dbex/refinement/stage_b.py::_build_lbfgs_closure` to pass the collector everywhere we formerly appended to `telemetry_state` (per-iteration metrics, periodic validations, and panel/full validations). Route baseline validations from `_run_stage_b_lbfgs` through `collector.on_validation(scope='baseline', ...)` and ensure final validations and best snapshot restores go through the collector as well. Keep Stage B baseline parity guard writing to `StageBTelemetryState.stage_b_baseline_*` so diagnostics still surface in artifacts.
3. Modify `dbex/refinement/stage_b_impl.py::_run_stage_b_lbfgs` so baseline/final validations, best snapshot persistence, and restoration all use collector callbacks instead of direct list mutation. When collector is active, skip the legacy append paths entirely; the dataclass state should be driven only by collector callbacks.
4. Instantiate `StageCTelemetryCollector` inside `StageC.run`, pass it through `_build_stage_c_lbfgs_closure` and `_run_stage_c_lbfgs`, and convert the Stage C closure and helper so per-iteration traces, variance counters, baseline/final validations, and panel diagnostics are emitted via collector callbacks. Remove remaining direct `telemetry_state.*.append(...)` calls in Stage C helpers and rely on collector state for final telemetry serialization.
5. Rebuild telemetry/perf dictionaries from the collector state before returning `StageResult` for both stages (no dict fallback). Ensure variance-floor counts, ROI/panel mode labels, and Stage C canonical gates (REFINE-007/012) remain intact.
6. Run the Stage B baseline guard unit: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T120000Z/pytest_stage_b_guard.log`.
7. Run the Stage B smoke selector: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T120000Z/pytest_stage_b_smoke.log`.
8. Run the Stage C smoke selector: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T120000Z/pytest_stage_c_smoke.log`.
Pitfalls To Avoid:
- Do not mutate `telemetry_state` dict/list fields directly once the collectors own the state; use observer callbacks so ARCH-STAGE-CTX-001/002 stay satisfied.
- Preserve Stage B baseline parity guard outputs (`stage_b_baseline_rel_diff` et al.) when rerouting telemetry—collectors should expose setters so `_check_stage_b_baseline_parity` can still log diffs.
- Keep variance-floor counters and perf metrics detached from autograd and update them via metrics payloads (avoid `.item()` on tensors that still require grad inside closures).
- Ensure Stage C panel diagnostics continue to append when `DBEX_STAGE_C_CACHE_DEBUG_PATH` is set; collector payloads should include `panel_diag` so warm-cache traces remain intact.
- Maintain REFINE-007/012 gate math: Stage C final chi² comparisons must still use Stage A panel-mode telemetry and ROC gating should not regress when ROI closures are disabled.
- Environment freeze applies—no new dependencies and no edits outside the repo tree noted above.
- Warm cache contexts must stay device/dtype neutral (no `.cuda()` calls inside the new collector plumbing).
If Blocked:
- If the Stage B or Stage C smoke selector fails with a telemetry regression, capture the failing pytest log plus the updated telemetry JSON into the artifact directory, note the signature in docs/fix_plan.md Attempts History, and ping Galph before attempting additional implementation loops.
Findings Applied:
- PHYSICS-LOSS-001 — Stage telemetry must encode variance-weighted chi² / masked MSE consistently across stages.
- PHYSICS-LOSS-003 — Stage B/C telemetry needs the same chi² definition as Stage A so Stage C gates compare like-for-like values.
- REFINE-007 — Stage C detector improvement gate (≥80% offset reduction, ≤0.05% chi² regression) depends on accurate telemetry snapshots.
- REFINE-012 — Stage C must honor Stage A validation scope when deciding ROI vs panel evaluation, so collector payloads need to encode scope.
- ARCH-STAGE-CTX-001 — Typed contexts prohibit telemetry dict mutation; observer collectors enforce ownership of stateful traces.
- ARCH-STAGE-CTX-002 — Stage B baseline parity guard must succeed against the dataclass-backed telemetry channel.
Pointers:
- docs/fix_plan.md:82 (ARCH-TELEMETRY-001 ledger entry + Attempts History)
- plans/active/ARCH-TELEMETRY-001/implementation.md:1 (phase plan + checklist)
- docs/spec-db-workflow.md:62 (Stage pipeline + telemetry requirements)
- docs/spec-db-core.md:57 (variance-weighted loss definition)
- docs/TESTING_GUIDE.md:162 (Stage A/B/C smoke selector instructions)
Next Up: After Stage B/C collectors land, plan Phase C.2 to redirect writer to StageResult dataclasses before archiving this initiative.
