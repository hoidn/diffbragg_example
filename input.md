Summary: Finish Phase C.1 by moving Stage B/C telemetry fully onto the observer collectors so StageResult payloads are emitted from `StageBTelemetryCollector`/`StageCTelemetryCollector` instead of mutating dict shims, then prove parity with the Stage B guard + Stage B/C smokes.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-TELEMETRY-001 — Telemetry Observer Refactor
Branch: integration
Mapped tests:
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T150000Z/
Do Now:
- Implement: 
  * `dbex/refinement/telemetry_collectors.py::{StageBTelemetryCollector,StageCTelemetryCollector}` — extend `on_validation`/`finalize()` so each collector records baseline/periodic/final validations, variance-floor counters, stage-specific diagnostics (Stage B baseline parity diffs, Stage C panel traces), and exposes a helper (`to_legacy_dict()` or reuse `StageResult.to_legacy_dict()`) that Stage B/C can feed into `RefinementTelemetry`.
  * `dbex/refinement/stage_b.py::{_build_lbfgs_closure,run}`, `dbex/refinement/stage_b_impl.py::_run_stage_b_lbfgs` — remove the `telemetry_state` dict/list mutation branches, route baseline validations and final restorations through `collector.on_validation(scope=...)`, plumb `StageBTelemetryCollector` into `_run_stage_b_lbfgs`, and build the returned `StageResult` by calling `collector.finalize()` instead of hand-assembling traces/perf counters.
  * `dbex/refinement/stage_c.py::{_build_lbfgs_closure,run}`, `dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs` — same conversion for Stage C: collectors must own per-iteration traces, baseline/periodic/final validations, panel diagnostics, and the final telemetry dict; ensure REFINE-012 scope (`validation_scope="panel"` vs `"roi"`) and warm-cache traces survive.
- Validate: capture the logs for all mapped selectors under the artifact directory (one `.log` per selector) and confirm `/torch_diagnostics` still lists Stage B/C chi² + masked MSE traces.
How-To Map:
1. Update `StageBTelemetryCollector` so `on_validation` accepts a `scope` for `"baseline"`, `"panel"`, `"roi"`, and `"final"`; stash tuples `(iteration, value)` and checksum payloads, expose setters for Stage B baseline parity fields, and have `finalize()` return a `StageResult(stage="B", telemetry=StageBTelemetry(...), perf_counters=...)`. Mirror the structure for `StageCTelemetryCollector`, including optional `panel_diag` aggregation and validation-scope tagging for REFINE-012.
2. In `StageB._build_lbfgs_closure`, delete the `if collector is None` branches. Use `collector.record_step()`/`collector.on_validation()` everywhere we previously appended to the `loss_trace_*`/`chi_squared_trace_*` lists, and ensure periodic validations capture the current iteration index plus a snapshot of either `log_modifiers` or `shell_modifier_raw`. Baseline validations (prior to the LBFGS step) should now be emitted in `_run_stage_b_lbfgs` via `collector.on_validation(scope="baseline", ...)`.
3. Rework `_run_stage_b_lbfgs` to rely on the collector for baseline/periodic/final traces and best-snapshot capture: call `collector.on_validation(scope="final", ...)` right after the final full-eval, drop the legacy list-append blocks, and treat the collector’s wrapped `StageBTelemetryState` as the only source of truth when restoring best snapshots. Keep `_check_stage_b_baseline_parity` writing diff fields onto the dataclass so the collector can surface them.
4. Have `StageB.run` call `collector.finalize()` once LBFGS returns, convert the typed StageResult to a legacy dict via `to_legacy_dict()`, and use that dict when constructing the `RefinementTelemetry`/`StageBArtifacts` pair returned to the engine. This is where you reattach shell metadata, Stage B mode, and final Bragg artifacts (if Stage C is disabled).
5. Apply the same pattern to Stage C: `_build_stage_c_lbfgs_closure` shouldn’t mutate `telemetry_state` lists, `_run_stage_c_lbfgs` must emit baseline and final validations via the collector (scope hints `"baseline"`, `"panel"`, `"final"`), and `StageC.run` should build its output telemetry dict from `collector.finalize()` before instantiating `StageCArtifacts`. Make sure panel diagnostics gathered when `DBEX_STAGE_C_CACHE_DEBUG_PATH` is set are added to the payload the collector sees.
6. Run the Stage B guard and both smokes, saving logs as you go:
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T150000Z/pytest_stage_b_guard.log`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T150000Z/pytest_stage_b_smoke.log`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T150000Z/pytest_stage_c_smoke.log`
Pitfalls To Avoid:
- Do not manipulate `telemetry_state` lists/dicts directly; the collectors must be the only writers (ARCH-STAGE-CTX-001/002).
- Keep Stage B baseline parity guard functional: update the dataclass fields the guard expects so diagnostics still show up in artifacts.
- Preserve variance-floor counters and perf traces; emit `variance_floor_*` deltas via the metrics dict rather than calling `.item()` on tensors that still require grad.
- Stage C panel diagnostics and validation scope are part of REFINE-012; make sure `panel_diag` data and the `validation_scope` string surface in collector payloads and final telemetry.
- No environment changes; use existing torch/scipy deps only. Any missing import is a blocker to log in docs/fix_plan.md.
- Warm-cache paths must stay device-neutral: do not introduce `.cuda()` or `.cpu()` churn inside the collectors.
- Capture logs for every mapped selector; if a selector fails, keep the log + telemetry snapshot in the artifact directory and stop.
If Blocked:
- If any mapped selector fails because telemetry no longer matches expectations, archive the failing log(s) plus the offending `/torch_diagnostics` JSON in the artifact directory, note the signature in docs/fix_plan.md Attempts History, and stop so Galph can reassess before more code churn.
Findings Applied:
- PHYSICS-LOSS-001 — Stage telemetry must encode the variance-weighted chi²/ masked-MSE pair for every stage.
- PHYSICS-LOSS-003 — Stage B/C need Stage A-equivalent chi² semantics so Stage C gates compare apples to apples.
- REFINE-007 — Stage C detector improvement gate relies on accurate Stage A vs Stage C chi² snapshots.
- REFINE-012 — Stage C must honor Stage A’s validation scope when deciding ROI vs panel gradients.
- ARCH-STAGE-CTX-001 / ARCH-STAGE-CTX-002 — Typed contexts own telemetry; baseline parity diagnostics can’t mutate dict shims.
Pointers:
- plans/active/ARCH-TELEMETRY-001/implementation.md:86 (Phase C checklist for collector wiring).
- docs/fix_plan.md:410 (Attempts history + artifact path for this loop).
- docs/spec-db-workflow.md:60 (Stage telemetry + observer contract requirements).
- docs/spec-db-core.md:57 (variance-weighted loss mandate feeding telemetry).
- docs/TESTING_GUIDE.md:160 (Stage B/C smoke selectors + env knobs).
Next Up: Once Stage B/C emit typed StageResults, Phase C.2 will move the writer over to those dataclasses so `/torch_diagnostics` no longer pulls from legacy dicts.
