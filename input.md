Summary: Fix the new Stage B final-Bragg plumbing so the reconstruction helper receives the shell metadata from the artifacts, and relax the Stage A smoke gate so small, well-initialized runs stop failing on a 2e‑7 log-scale delta.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T141500Z/

Do Now:
- FocusItem: ARCH-STAGE-CONTEXT-001 Phase D — Final Bragg Artifact Propagation cleanup
- Implement: dbex/refinement/stage_b.py::StageB.run — before calling `build_final_bragg_from_stage_b_telemetry`, build a reconstruction payload that merges the existing telemetry dict with the shell metadata and stage mode from `StageBArtifacts`, and attach the resulting `bragg_full` numpy volume back onto the artifact so the Stage A→B branch in `run_nanobrag_refinement` no longer falls back to the helper. Keep the payload compact (numpy arrays, no GPU tensors) and retain the per-reflection branch semantics.
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — update Acceptance 5 so it asserts that at least one Stage A degree of freedom moved (max absolute delta across log_scale, log_cell deltas, angle deltas, or misset components) exceeds 1e‑6 instead of hard-coding the log-scale delta. This preserves the “Stage A is not a no-op” guarantee without failing when only geometry parameters move.
- Validate: Re-run the mapped Stage B shell smoketest and Stage A expansion smoketest with the canonical env vars, teeing logs into the new artifact folder (`pytest_stage_b_shell.log`, `pytest_stage_a_small.log`). Capture the Stage B per-reflection smoketest output only if it changes; its known TORCH-REFINE-004 failure signature may remain unchanged.

How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T141500Z/pytest_stage_b_shell.log`
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T141500Z/pytest_stage_a_small.log`

Pitfalls To Avoid:
- Do not call the reconstruction helper with GPU tensors or omit the shell metadata; the helper expects CPU-resident numpy arrays so the writer path stays deterministic.
- Keep StageBArtifacts backward-compatible: the new bragg payload must default to `None` and the shell metadata fields must stay available for the writer and fallback code.
- Preserve REFINE-FLOW-001 telemetry (baseline parity diagnostics) when mutating StageBArtifacts, and avoid touching the per-reflection fast path beyond the reconstruction payload.
- When computing the Stage A max-delta check, use the existing `param_deltas` dict rather than recomputing tensors so the smoke test stays hermetic and doesn’t depend on device state.
- Leave the Stage B per-reflection smoketest guard in place (documented expected failure) and record any signature changes in the artifact summary if they occur.
- Reuse the canonical env vars from docs/TESTING_GUIDE.md (KMP_DUPLICATE_LIB_OK, NANOBRAGG_DISABLE_COMPILE, DBEX_SMOKE_* overrides) so the small-detector fixtures pull the intended HKL/calibration bundle.
- Avoid rearranging Stage B warm-cache logic or CPU fallback semantics; only the reconstruction payload should change, not the optimization path.

If Blocked: Capture the traceback (e.g., if shell metadata is missing from artifacts) plus a short root-cause note in `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T141500Z/blocked.md`, update `docs/fix_plan.md` Attempts History with the blocker, and page Galph if the reconstruction helper needs a signature change that spills into ARCH-ENGINE-ARTIFACTS-001.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage wrappers must own their contexts/artifacts; feeding shell metadata through StageBArtifacts instead of dict hacks keeps this promise.
- ARCH-STAGE-CTX-002 — Stage B telemetry guards remain dataclass-safe; the reconstruction fix must not reintroduce dict mutation.
- REFINE-FLOW-001 — Stage B baseline parity relies on Stage A canonical telemetry; ensure the reconstruction payload retains the same provenance.

Pointers:
- dbex/refinement/stage_b.py:560-1030 — Stage B artifact assembly and new reconstruction call site.
- dbex/refinement/reconstruction.py:250-410 — Helper expecting shell metadata; use these arguments as the contract.
- tests/dbex/test_torch_refine_smoke.py:450-560 & 1240-1395 — Stage A expansion acceptance criteria and Stage B shell smoketest harness that must be updated/verified.

Next Up (optional):
- If time allows after the smoketests pass, rerun the Stage B per-reflection smoketest to confirm its known TORCH-REFINE-004 failure signature is unchanged and archive the log beside the other artifacts.
