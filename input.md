Summary: Route Stage artifacts through the writer so Stage-specific metadata no longer depends on telemetry shims and the HDF5 schema stays canonical.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
- tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T110000Z/

Do Now:
- FocusItem: ARCH-STAGE-CONTEXT-001 Phase B.4 — Writer/engine artifact plumbing
- Implement: `dbex/io/writer.py::write_torch_outputs` — add an optional `stage_artifacts: Optional[Dict[str, Any]]` parameter (documented in the module docstring and `docs/architecture/dbex/io/writer.idl.md`). When serializing `stage_B` diagnostics, pull `stage_b_baseline_rel_diff`, `stage_b_baseline_abs_diff`, and `stage_b_baseline_diff_path` directly from a `StageBArtifacts` payload when present, falling back to telemetry fields only for backward compatibility. Ensure the `/torch_diagnostics` layout and attribute names remain byte-for-byte identical (DIAGNOSTICS-001, REFINE-FLOW-001) and keep ROI score/Nelder-Mead behavior unchanged.
- Implement: `dbex/refine_one.py::run_nanobrag_backend` (and any helper that calls `write_torch_outputs`) — pass `engine.artifacts` to the writer so Stage-specific metadata is available without telemetry shims. Update the CLI tests that patch `write_torch_outputs` (all `@patch('dbex.io.writer.write_torch_outputs')` occurrences in `tests/dbex/test_refine_one_cli.py`) to expect the new keyword argument and to assert that Stage B baseline metrics remain intact.
- Implement: `dbex/refinement/engine.py::run` — remove the temporary `excluded_fields` filter and the Stage B attribute rebinding block that copied artifact fields back onto telemetry. After this change, `RefinementTelemetry` instances remain clean and Stage-specific metadata is provided exclusively through artifacts/writer.
- Validate: run the mapped smoketests (Stage B shell expected PASS, Stage B per-reflection expected failure, Stage C small PASS, Stage C full reproduces PERF-WARM-SIM-001 signature) plus `pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`. Capture logs, CLI output, and any telemetry JSON under the new artifact directory.

How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T110000Z/pytest_stage_b_shell.log`
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T110000Z/pytest_stage_b_per_reflection.log` (failure expected; ensure signature matches TORCH-REFINE-004 notes).
3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_STAGE_C_PANEL_DIAG_DIR=plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T110000Z/panel_diag_small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T110000Z/pytest_stage_c_small.log`
4. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_STAGE_C_PANEL_DIAG_DIR=plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T110000Z/panel_diag_full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T110000Z/pytest_stage_c_full.log` (PERF-WARM-SIM-001 failure expected; capture telemetry JSON for PERF initiative).
5. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T110000Z/pytest_cli_writer.log`

Pitfalls To Avoid:
- Do not change `/torch_diagnostics` dataset/attribute names; only the data source should move from telemetry to artifacts.
- Maintain REFINE-FLOW-001 semantics: Stage B baseline metrics must still be emitted (even if sourced from StageBArtifacts) and guard tests expect identical tolerances.
- Keep `RefinementTelemetry` cleanly typed; avoid reintroducing dict mutations when removing the shim.
- Update `docs/architecture/dbex/io/writer.idl.md` if the public signature changes, and keep doc comments in sync.
- Ensure writer callers (CLI tests, smoke harnesses) provide the new argument; missing kwargs will break existing patches.
- Do not delete the Stage B per-reflection smoke even though it fails — capture the failure log for TORCH-REFINE-004 cross-reference.
- Preserve device/dtype neutrality when touching engine or writer; no new `.cuda()` calls.
- Avoid modifying the problem-space configuration (Environment Freeze) while rearranging writer plumbing.
- Keep Stage C ROI diagnostics hook wired to the new telemetry dataclass (panel diag paths must still resolve).
- Remember that Stage C full-detector run is expected to fail due to PERF-WARM-SIM-001; treat any new failure signature as a regression.

If Blocked:
- If the new writer signature breaks third-party tooling or the CLI patch cannot pass artifacts through, stop, capture the traceback plus your current diff in `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T110000Z/blocked.md`, and flag the Do Now as blocked in docs/fix_plan.md (include the error and missing dependency). Do not ship a partial refactor—telemetry + HDF5 schema must remain coherent.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage contexts and telemetry must use typed dataclasses instead of dict shims.
- ARCH-ENGINE-002 — Engine/writer boundaries must rely on Stage artifacts rather than private caches.
- REFINE-FLOW-001 — Stage B baseline parity metrics must remain traceable.
- PHYSICS-LOSS-001/002 — Dual loss traces and variance-floor telemetry cannot regress while plumbing changes land.

Pointers:
- dbex/io/writer.py:41 — current writer signature and serialization logic.
- dbex/refine_one.py:601 — writer call site receiving telemetry and bragg outputs.
- dbex/refinement/engine.py:140 — telemetry aggregation + Stage B shim to remove.
- docs/architecture/dbex/io/writer.idl.md:28 — canonical API contract to update alongside the code.
- tests/dbex/test_refine_one_cli.py:110-900 — writer patches and CLI regression coverage affected by the signature change.

Next Up (optional):
- Once StageArtifacts feed the writer, Phase C can focus on moving the remaining ROI-scale helpers out of the writer.
