Summary: Teach `dbex/io/writer.py` to consume the typed StageResult telemetry/perf-counters that now reach it so `/torch_diagnostics` stays spec-compliant without scraping legacy dicts.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-TELEMETRY-001 — Telemetry Observer Refactor
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T050000Z/
Do Now:
  - dbex/io/writer.py — Rework the per-stage serialization loop (lines 202‑360) so it prefers `stage_results` when present. Add a helper that ingests a `StageResult` (telemetry + perf counters) and returns the same payloads we currently emit (loss/chi² traces, best tuples, variance counters, perf stats). Use that typed payload for `stage_*` groups and the single-stage top-level mirror, while still reading static metadata (optimizer, ROI counts, param_deltas, status/message) from `RefinementTelemetry`. Fall back to the existing `stage_telem.to_dict()` path when a stage lacks a typed result (mocks/tests) so schema stays byte-for-byte compatible.
  - Keep Stage B baseline attrs wired: when artifacts exist use them, else pull the legacy values from either the typed payload or the `RefinementTelemetry` fallback. Ensure perf counters recorded in StageResult now drive the JSON blobs we write (no stale copies from the dict shim).
  - Re-run the Stage B guard, Stage B shell smoke, and Stage C microslip selectors plus the CLI metadata test with logs under the new artifacts directory (Stage C coverage was skipped last loop, so capture `pytest_stage_c_smoke.log` this time).
How-To Map:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T050000Z/pytest_cli_diag.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T050000Z/pytest_stage_b_guard.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T050000Z/pytest_stage_b_smoke.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T050000Z/pytest_stage_c_smoke.log
Pitfalls To Avoid:
  - StageResult payloads carry tensors detached by the collectors; never mutate them inside writer. Convert to numpy/scalars before writing datasets to keep HDF5 schema identical.
  - Maintain the legacy fallback path for tests/mocks that still pass `stage_results=None`; do not drop `RefinementTelemetry.to_dict()` until C3.2 lands.
  - Preserve Stage B baseline attrs and Stage A top-level mirrors exactly—schema drift fails DIAGNOSTICS-001.
  - Writer is hot code; avoid importing heavy modules at top level and respect Environment Freeze (stdlib only).
  - Run Stage C microslip even if known flaky: we need a fresh log to show the StageResult → writer path works for all stages.
If Blocked:
  - If StageResult lacks a field you need (e.g., certain diagnostics), document the gap in `plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T050000Z/blocker.md`, leave the legacy dict path intact, and push the missing-field analysis into docs/fix_plan.md so we can size a follow-up.
  - If `/torch_diagnostics` diffs fail schema assertions, revert the writer change, attach the failing pytest log in the artifacts directory, and note the failure signature plus suspected field in docs/fix_plan.md before stopping.
Findings Applied (Mandatory):
  - PHYSICS-LOSS-001 — Stage A/B/C loss/chi² traces must remain variance-weighted with sigma-floor provenance when StageResult drives serialization.
  - PHYSICS-LOSS-003 — Stage A canonical snapshot/clamp telemetry still needs to reach `/torch_diagnostics` even after switching writers.
  - DIAGNOSTICS-001 — `/torch_diagnostics` schema (attrs/datasets/JSON) is normative; treat StageResult usage as an implementation detail only.
Pointers:
  - dbex/io/writer.py:202 — current per-stage serialization loops that still call `stage_telem.to_dict()`.
  - dbex/refine_one.py:561 — StageResult map forwarded to `write_torch_outputs`.
  - plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T020000Z/pytest_stage_b_smoke_retry.log — proof that current StageResult plumbing keeps Stage B smokes green; replicate coverage plus Stage C.
Next Up:
  - Phase C.3.2 — remove the `legacy_telemetry_dict` plumbing inside Stage A/B/C once the writer path is StageResult-first.
