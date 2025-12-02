Summary: Surface the collector-emitted StageResult telemetry through the refinement pipeline and teach `dbex/io/writer.py` to consume it directly so Stage B/C observer data feeds /torch_diagnostics without legacy dict scraping.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-TELEMETRY-001 — Telemetry Observer Refactor
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T020000Z/
Do Now:
  - Implement: `dbex/refinement/stage.py::RefinementTelemetry` needs an optional field (e.g., `stage_result`) that can carry the collector-emitted StageResult from `dbex.refinement.interfaces`; ensure `to_dict()` skips this field so legacy serialization stays unchanged.
  - Implement: After `collector.finalize()` runs in each stage wrapper, persist the typed StageResult on the telemetry dataclass before building the `StageResult` container returned to the engine: add a finalize call + assignment in Stage A (`StageATelemetryCollector`, right after `_run_stage_a_lbfgs`), reuse the existing `stage_result` object in Stage B/C (`dbex/refinement/stage_b.py::_run_stage_b_lbfgs`, `dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs`) instead of dropping it after `to_legacy_dict()`.
  - Implement: Surface those typed results through the CLI path — after `run_nanobrag_refinement` completes, build `{label: telem.stage_result}` (skip None) and pass it to `dbex/io/writer.write_torch_outputs` via a new `stage_results` kwarg (default `None` for legacy callers). Update the writer signature and adjust call sites (`dbex/refine_one.py`, any tests/mocks) accordingly.
  - Implement: Refactor `dbex/io/writer.py` so it prefers the typed StageResult payload when provided (use its telemetry/perf counters for `/torch_diagnostics/stage_*` datasets, but keep `RefinementTelemetry` for static metadata such as optimizer/tolerance). Fall back to the existing dict-scraping logic when a stage lacks a typed result (e.g., mocks/tests).
  - Update tests/mocks that patch `write_torch_outputs` (CLI tests, telemetry metadata test) so they provide/expect `stage_results`. Capture pytest logs for each mapped selector under the artifacts directory listed above.
How-To Map:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T020000Z/pytest_cli_diag.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T020000Z/pytest_stage_b_guard.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T020000Z/pytest_stage_b_smoke.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T020000Z/pytest_stage_c_smoke.log
Pitfalls To Avoid:
  - Do not break `/torch_diagnostics` schema: new writer code must populate the same datasets/attrs even when using typed StageResult data.
  - `RefinementTelemetry.to_dict()` is consumed by other code paths; ensure adding `stage_result` (or similar) does not trigger dataclass recursion (skip it explicitly).
  - Stage A still enforces the canonical ROI/panel guards; keep the new finalize call outside autograd contexts so tensors are detached before StageResult construction.
  - Avoid widening the `run_nanobrag_refinement` return signature (too many call sites); keep new data flowed internally to `run_nanobrag_backend`/writer.
  - Environment Freeze: no new third-party deps; reuse existing collector/state helpers instead of importing new telemetry libraries.
If Blocked:
  - If Stage A finalize exposes a circular import, document the stack trace in `plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T020000Z/blocker.md`, revert the partial change, and fall back to wiring StageResult for Stage B/C only so writer work can proceed (note the missing Stage A payload in docs/fix_plan.md).
  - If the writer refactor breaks schema validation, capture the failing pytest logs under the artifacts directory and restore the previous dict path, then raise the issue in docs/fix_plan.md with the selector/failure signature so we can triage.
Findings Applied (Mandatory):
  - PHYSICS-LOSS-001 — Keep variance-weighted χ² / sigma-floor telemetry intact while moving data between collectors and writer.
  - PHYSICS-LOSS-003 — Stage A canonical snapshot/clamp provenance must still reach `/torch_diagnostics`.
  - DIAGNOSTICS-001 — `/torch_diagnostics` schema (attrs + ROI telemetry) must remain byte-for-byte compatible; new StageResult plumbing is an implementation detail only.
Pointers:
  - dbex/refinement/stage.py — `RefinementTelemetry` dataclass and StageResult container.
  - dbex/refinement/stage_a.py, dbex/refinement/stage_b.py, dbex/refinement/stage_c_impl.py — hook `collector.finalize()` results into telemetry before returning StageResult.
  - dbex/refine_one.py — pass the per-stage StageResult map to `write_torch_outputs`.
  - dbex/io/writer.py — extend signature + serialization logic to handle `stage_results`.
Next Up:
  - Phase C.3 (remove legacy telemetry dict shims) once the writer exclusively consumes typed StageResult data.
