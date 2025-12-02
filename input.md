Summary: Finish the Stage B/C telemetry collector migration by fixing the Stage B parity guard to talk only to `StageBTelemetryCollector`, deleting the lingering `telemetry_state` dict shims, and proving the Stage B guard plus the Stage B/C small-detector smokes stay green.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-TELEMETRY-001 — Telemetry Observer Refactor
Branch: integration
Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T190000Z/pytest_stage_b_guard.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T190000Z/pytest_stage_b_smoke.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T190000Z/pytest_stage_c_smoke.log
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T190000Z/
Do Now:
- Implement:
  * `dbex/refinement/stage_b_impl.py::_check_stage_b_baseline_parity` — replace the dict fallbacks with a collector branch so baseline rel/abs diffs and the JSON diff path are always recorded via `StageBTelemetryCollector.set_baseline_parity_metrics`, and clear the diff path through the helper when parity passes instead of trying to subscript the collector.
  * `dbex/refinement/stage_b_impl.py::{_build_stage_b_lbfgs_closure,_run_stage_b_lbfgs}` — drop the `isinstance(..., dict)` compatibility code, assume `telemetry_state` is a `StageBTelemetryState`, and rely on the collector-owned lists/counters (plus `StageResult.to_legacy_dict()`) for traces and parity metrics so no helper mutates `telemetry_state` directly.
  * `dbex/refinement/telemetry_collectors.py::StageBTelemetryCollector` — update `set_baseline_parity_metrics` to always propagate the diff path (set it to `None` when clearing) and add any convenience helpers the guard now relies on.
- Validate: run the mapped selectors above with the canonical env flags, capturing stdout/stderr via `tee` into the artifact directory. Stop immediately on the first failure and leave the log (plus any generated JSON diff) in place for supervisor triage.
How-To Map:
1. In `_check_stage_b_baseline_parity`, branch on `StageBTelemetryCollector` and `StageBTelemetryState` only, routing all metric updates through the collector helper and removing the `telemetry[...]` assignments. Preserve the JSON diff schema and warning text so REFINE-FLOW-001 assertions still match.
2. In `_build_stage_b_lbfgs_closure` and `_run_stage_b_lbfgs`, remove the dict-specific setup (e.g., `telemetry['loss_trace_sample_b']`), keep only the dataclass references, and let the collector maintain loss traces, perf counters, and parity metrics before you call `collector.finalize()`.
3. After the code edits, execute the Stage B guard, Stage B shell smoke, and Stage C detector microslip smoke with the commands above, ensuring each run tees its log into `plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T190000Z/`.
Pitfalls To Avoid:
- Do not reintroduce telemetry dict shims; collectors must be the sole writers per ARCH-STAGE-CTX-001/002.
- Keep the JSON diff structure and warning wording untouched so existing tests compare byte-for-byte artifacts.
- Stage C full-detector runs still fail under PERF-WARM-SIM-001; only run the small-detector selector listed unless instructed otherwise.
- Respect the Environment Freeze (no pip/conda installs); treat missing deps or new failures as blockers and document them.
- Capture pytest logs even on failure; do not delete artifacts that show the regression.
If Blocked:
- If any mapped selector fails due to telemetry/parity regressions, keep the failing log + JSON diff in the artifact directory, update docs/fix_plan.md Attempts History with the failure context, and stop instead of guessing at fixes.
Findings Applied:
- ARCH-STAGE-CTX-001 — Stage wrappers and telemetry must use typed contexts/collectors (docs/findings.md:83).
- ARCH-STAGE-CTX-002 — Stage B’s baseline guard has to interoperate with the typed telemetry state (docs/findings.md:84).
- PHYSICS-LOSS-001 / PHYSICS-LOSS-003 — All stages must report variance-weighted χ²/MSE consistently (docs/findings.md:35,37).
- REFINE-012 — Stage C validations must honor Stage A’s ROI vs panel scope decisions (docs/findings.md:73).
Pointers:
- docs/spec-db-workflow.md §7 & §Calibration (Stage B/C telemetry contract).
- dbex/refinement/stage_b_impl.py (parity guard + LBFGS helpers) and dbex/refinement/telemetry_collectors.py (Stage B/C collectors).
- docs/TESTING_GUIDE.md §2 (env knobs + log retention for the mapped selectors).
Next Up: Once the Stage B/C collector migration is stable, move on to Phase C.2 to teach `dbex/io/writer.py` to consume the `StageResult` telemetry directly.
Doc Sync Plan: none — selectors unchanged.
Mapped Tests Guardrail: Existing selectors already collect >0 tests; no new tests need to be authored before implementation.
Hard Gate: Treat any new Stage B baseline diff or Stage B/C smoke regression as a blocker; do not land telemetry changes without green runs and archived logs.
Normative Math/Physics: See docs/spec-db-core.md §Objective Function & Variance Model for the variance-weighted χ² definition the telemetry must continue to report.
