Summary:
- Wire Stage B and Stage C through the new telemetry observer path so LBFGS closures and validation hooks emit metrics via `StageBTelemetryCollector`/`StageCTelemetryCollector` without mutating telemetry dicts.

Mode: Parity

InitiativeType: architecture

Focus: ARCH-TELEMETRY-001 — Telemetry Observer Refactor

Branch: integration

Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload

Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T070500Z/

Do Now:
- Implement: `dbex/refinement/stage_b.py::{_build_lbfgs_closure,run}`, `dbex/refinement/stage_b_impl.py::_run_stage_b_lbfgs`, `dbex/refinement/stage_c.py::{_build_lbfgs_closure,run}`, `dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs`, and `dbex/refinement/telemetry_collectors.py::{StageBTelemetryCollector,StageCTelemetryCollector}` so Stage B/C LBFGS closures and baseline/final validation hooks accept collector instances, call `collector.on_step` / `collector.on_validation`, and stop mutating telemetry dataclass lists directly while preserving the existing StageBArtifacts/StageCArtifacts and telemetry outputs (variance-floor counters, panel diagnostics, baseline parity metrics).
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T070500Z/pytest_stage_b_shell_small.log`
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T070500Z/pytest_stage_c_small.log`
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T070500Z/pytest_stage_b_guard.log`

How-To Map:
1. `mkdir -p plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T070500Z`
2. Update `dbex/refinement/stage_b.py:83` so `_build_lbfgs_closure` takes an optional `StageBTelemetryCollector`, swaps the manual `loss_trace_sample_b` / variance-floor / perf counter mutations for `collector.on_step(...)`, and records periodic validations via `collector.on_validation(...)` with the best snapshot payload. Thread the collector through `StageB.run` and `_run_stage_b_lbfgs` so baseline/final/default validations also use the observer path (fall back to the current list mutation only if no collector is provided for backward compatibility).
3. Apply the same observer plumbing to Stage C: update `dbex/refinement/stage_c.py:87` and `dbex/refinement/stage_c_impl.py:477` so detector-offset closures call `StageCTelemetryCollector` for every iteration and for baseline/final validations, keeping panel diagnostics (`panel_loss_diag`) and warm-cache counters unchanged.
4. Extend `dbex/refinement/telemetry_collectors.py:356` and `:423` as needed so the Stage B/C collectors expose the same convenience helpers as Stage A (accepting forward-time + variance-floor deltas in metrics) and continue to return StageResult objects that carry `stage_b_baseline_*` / panel diagnostic fields for writer consumers.
5. Re-read Stage B baseline guard helper (`dbex/refinement/stage_b_impl.py:55-210`) after the refactor to ensure it still populates `StageBTelemetryState.stage_b_baseline_rel_diff` etc. without relying on dict subscripts.
6. Run the staged pytest selectors above with `DBEX_SMOKE_TELEMETRY_PATH` pointed at the artifacts directory when you need telemetry JSON (`export DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T070500Z/telemetry_stage_bc_small.json` before the smoke bundle) so we capture before/after chi² traces.
7. Inspect the resulting `/torch_diagnostics` payloads (Stage B/C telemetry JSON and StageBArtifacts) to confirm that `stage_b_baseline_rel_diff`, variance-floor stats, warm-cache counters, and panel diagnostics are unchanged; drop a short note in `plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T070500Z/summary.md` summarizing parity evidence.

Pitfalls To Avoid:
- Do not regress the REFINE-FLOW-001 parity guard: keep `stage_b_baseline_rel_diff`, `stage_b_baseline_abs_diff`, and `stage_b_baseline_diff_path` populated and ensure the RuntimeError path still raises with the same message/signature.
- Preserve variance-floor accounting by feeding per-step clamp/masked-pixel deltas to the collector; skipping those metrics will break PHYSICS-LOSS telemetry downstream.
- Keep StageC panel diagnostics optional and gated by `DBEX_STAGE_C_PANEL_DIAG_DIR`; the collector needs to append to `panel_loss_diag` only when the shim requests it.
- Avoid touching StageArtifacts serialization or writer plumbing in this loop—the observer wiring must be transparent to `RefinementEngine` consumers.
- Maintain `torch.no_grad()` boundaries around validation calls; introducing graph-tracked tensors into collector payloads will break LBFGS backward passes.

If Blocked:
- If LBFGS closures start throwing due to missing metrics (e.g., collector state is None), capture the stack trace in `plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T070500Z/blocker.log`, revert the minimal hunks necessary to restore Stage B/C execution, and note the failing hook in docs/fix_plan.md so we can revisit the collector injection.
- If smoketests fail with the known Stage B per-reflection gradient-flow issue, confirm the failure signature matches the existing TORCH-REFINE-004 finding, attach the pytest log under this loop’s artifacts, and pause until we open the dedicated initiative; do not loosen the smoketest gates.
- Should the baseline guard unit test start failing because telemetry fields are missing, record the new telemetry dict in the artifact directory and fall back to the previous dict-based mutation so we have a working state before retrying the observer path.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage helpers must rely on typed contexts/telemetry objects; observer wiring enforces it.
- ARCH-STAGE-CTX-002 — Stage B baseline parity guard must work with dataclasses (no dict mutation).
- PHYSICS-LOSS-001/003 — Maintain variance-weighted chi² / masked-MSE telemetry per spec-db-core.md.
- REFINE-007 / REFINE-012 — Stage C validations must keep the canonical panel-mode chi² and offset gates intact.

Pointers:
- dbex/refinement/stage_b.py:83 — Stage B closure builder (per-iteration telemetry hooks live here).
- dbex/refinement/stage_b_impl.py:839 — `_run_stage_b_lbfgs` baseline/final validation logic that must call the collector.
- dbex/refinement/stage_c.py:87 and dbex/refinement/stage_c_impl.py:477 — Stage C closure + LBFGS runner where observer plumbing needs to be added.
- dbex/refinement/telemetry_collectors.py:356 & 423 — Stage B/C collectors (extend callbacks/helpers so they match Stage A parity).
- docs/TESTING_GUIDE.md:162 — Reference for the Stage A/B/C smoketest commands/env flags you must reuse when running the mapped selectors.

Next Up (optional):
- If the observer path lands cleanly this loop, follow up by simplifying `RefinementEngine` telemetry plumbing so writer/engine consume the typed `StageResult` objects directly (Phase C.2).
