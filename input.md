Summary: Restore Stage B shell telemetry by making `_check_stage_b_baseline_parity` and StageBTelemetryState dataclass-aware, then document the `stage_artifacts` writer API.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small
- tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T120500Z/

Do Now:
- FocusItem: ARCH-STAGE-CONTEXT-001 Phase B.4 follow-up — Stage B telemetry dataclass compatibility + IDL doc sync
- Implement: `dbex/refinement/context.py::StageBTelemetryState` — add optional REFINE-FLOW-001 fields (`stage_b_baseline_rel_diff`, `stage_b_baseline_abs_diff`, `stage_b_baseline_diff_path`) with `None` defaults so parity diagnostics live on the dataclass rather than ad-hoc dict keys.
- Implement: `dbex/refinement/stage_b_impl.py::_check_stage_b_baseline_parity` — detect dataclass vs dict telemetry. When handed StageBTelemetryState, update the new attributes via `setattr` (including diff-path bookkeeping) instead of subscripting. Preserve the legacy dict branch for `test_stage_b_cpu_fallback`.
- Implement: `dbex/refinement/stage_b.py::StageB.run` — after calling `_check_stage_b_baseline_parity`, attach the baseline diagnostics to the emitted `RefinementTelemetry` (so JSON telemetry and smoke fixtures still see those fields) while also passing them into `StageBArtifacts`.
- Implement: `docs/architecture/dbex/io/writer.idl.md` — refresh the API signature/usage notes to describe the `stage_artifacts` parameter that now feeds Stage B baseline metrics into `/torch_diagnostics`, keeping the schema reference in sync with the shipped code.
- Validate: run the mapped tests below, capturing logs into the new artifact directory.

How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T120500Z/pytest_stage_b_shell.log`
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T120500Z/pytest_stage_b_per_reflection.log` (failure signature should continue matching TORCH-REFINE-004; log the result).
3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T120500Z/pytest_cli_writer.log`

Pitfalls To Avoid:
- Do not mutate StageBTelemetryState via dict-style indexing; use attributes so future dataclass upgrades remain type-safe.
- Keep `/torch_diagnostics` attribute names byte-for-byte identical; only the source (artifacts vs telemetry) may change.
- Stage B per-reflection test still fails due to known gradient-flow issues; ensure the failure reason matches the archived TORCH-REFINE-004 logs.
- Environment Freeze still applies; no new dependencies or package edits.
- Avoid `.cpu()`/`.cuda()` churn inside the parity guard—device/dtype neutrality must hold.
- Do not drop Stage B baseline diagnostics from telemetry; smoke harnesses ingest them via `getattr`.
- Preserve StageBArtifacts schema; writers/tests already expect numpy shell metadata and parity floats.
- Capture all pytest logs in the artifact directory even when failures are expected.

If Blocked:
- If `_check_stage_b_baseline_parity` still explodes when run via the shell smoketest (or parity metrics disappear from telemetry/artifacts), stop, dump the traceback plus telemetry JSON into `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T120500Z/blocked.md`, and update docs/fix_plan.md with the blocker instead of attempting additional refactors.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage helpers/telemetry must use typed dataclasses instead of anonymous dicts.
- ARCH-STAGE-CTX-002 — Stage B baseline parity guard must support StageBTelemetryState to unblock REFINE-FLOW-001.
- REFINE-FLOW-001 — Stage B baseline diagnostics remain the authoritative parity gate; schema must continue surfacing those fields.

Pointers:
- dbex/refinement/context.py:624 — StageBTelemetryState definition.
- dbex/refinement/stage_b_impl.py:34 — `_check_stage_b_baseline_parity` dict-only mutation path.
- dbex/refinement/stage_b.py:780 — Stage B telemetry/artifact assembly that needs to propagate parity diagnostics.
- docs/architecture/dbex/io/writer.idl.md:1 — writer IDL contract awaiting signature update.
- docs/fix_plan.md:34 — fix-plan entry outlining initiative scope and exit criteria.

Next Up (optional):
- After Stage B telemetry compatibility lands, resume PERF-WARM-SIM-001 once Stage C ROI diagnostics can rely on clean artifacts.
