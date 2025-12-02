Summary: Move the Stage A/B final-Bragg reconstruction helpers into a shared refinement module, extend the stage artifacts to carry optional Bragg tensors, and retire the `run_nanobrag_refinement` fallback paths so artifact consumers no longer re-run the monolithic helpers.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T130500Z/

Do Now:
- FocusItem: ARCH-STAGE-CONTEXT-001 Phase D — Final Bragg Artifact Propagation
- Implement: create `dbex/refinement/reconstruction.py` that hosts the shared helper functions formerly defined in `dbex/nanobrag_refinement.py` (`_build_final_bragg_from_stage_a_telemetry` and `_build_final_bragg_from_stage_b_telemetry`). Preserve their signatures/behavior, keep the existing imports (`nanobrag_torch`, bridge helpers, `_clamp_log_cell_deltas`, `_retarget_stage_a_simulators`) inside the new module to avoid circular dependencies, and export them as `build_final_bragg_from_stage_a_telemetry` / `build_final_bragg_from_stage_b_telemetry` so both the stage wrappers and CLI path can import them without touching the monolith.
- Implement: `dbex/refinement/artifacts.py::{StageAArtifacts, StageBArtifacts}` — add optional `bragg_full` fields (default `None`) so Stage A/B can attach a final `[panel, slow, fast]` numpy tensor when they are the terminal stage. Update docstrings to make it clear the field is populated only when downstream stages are disabled.
- Implement: `dbex/refinement/stage_a.py::StageA.run` — after Stage A telemetry is assembled, detect `not self._config.enable_stage_b and not self._config.enable_stage_c`, call `build_final_bragg_from_stage_a_telemetry(...)` with the already-loaded detector/beam/crystal/refinement inputs + warm cache context, and stash the numpy stack inside `StageAArtifacts`. Leave the field `None` when Stage B/C are enabled to avoid redundant work. Ensure the helper import comes from the new reconstruction module and keep fallbacks for legacy contexts (e.g., when stage_a_ctx is absent).
- Implement: `dbex/refinement/stage_b.py::StageB.run` — similarly, when `not self._config.enable_stage_c`, run `build_final_bragg_from_stage_b_telemetry(...)` with the Stage A telemetry dict, freshly instantiated `RefinementTelemetry` for Stage B, the CPU-fallback context (`stage_b_eval_stage_a_ctx`), and the `use_stage_b_cpu_fallback` flag so the helper mirrors the existing CLI path. Attach the resulting numpy volume to the `StageBArtifacts` instance (both shell and per-reflection branches). Leave `bragg_full=None` for runs that continue into Stage C.
- Implement: `dbex/nanobrag_refinement.py::run_nanobrag_refinement` — drop the inlined helper definitions, import the new reconstruction module, and update the Stage-A-only and Stage-A→B branches so they first attempt to read `bragg_full` from the corresponding artifacts (`engine.artifacts['stage_a']` / `['stage_b']`) and only fall back to calling `build_final_bragg_from_stage_*_telemetry` when the artifacts were produced by older binaries. Keep the Stage C branch as-is (Stage C already emits its Bragg volume). While editing, remove the legacy helper definitions from this file to avoid duplicate implementations.
- Implement: update every consumer that previously imported `_build_final_bragg_from_stage_a_telemetry` (tests/dbex/test_stage_a_smoke_parity.py, dbex/tools/stage_a_adam.py, plans/active/TOOLING-VIS-001/bin/* parity scripts, etc.) so they import from `dbex.refinement.reconstruction` instead. Ensure no stale private import paths remain.
- Validate: run the mapped tests above, teeing each log into the new artifact directory (`pytest_stage_a_small.log`, `pytest_stage_b_shell.log`, `pytest_stage_b_per_reflection.log`). The per-reflection smoketest is still expected to fail with the TORCH-REFINE-004 gradient-flow signature; capture the output for traceability.

How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T130500Z/pytest_stage_a_small.log`
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T130500Z/pytest_stage_b_shell.log`
3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T130500Z/pytest_stage_b_per_reflection.log`

Pitfalls To Avoid:
- Keep the reconstruction helpers device/dtype neutral and avoid introducing new imports that would recreate the Stage A/B↔nanobrag_refinement circular dependency; the shared module must not import StageA/StageB classes.
- When populating `bragg_full`, ensure the numpy arrays stay CPU-resident (writer consumers expect cpu floats) and the Stage B CPU fallback continues to rebuild contexts on CPU instead of reusing CUDA tensors.
- StageAArtifacts/StageBArtifacts are read by existing code; adding fields must be backward-compatible (use defaults) and the `engine.artifacts` map may contain `None` for older runs—always guard attribute access.
- Do not regress Stage C behavior: its artifacts already include `bragg_full`, so avoid renaming fields or assuming Stage C runs when checking config flags.
- Update every helper import (tests/tools/plans) in the same change so the repository has a single authoritative reconstruction entry point; leaving split implementations will make future refactors brittle.
- Capture per-reflection failure logs; if the signature changes, document it in the artifact summary before proceeding.
- Maintain Environment Freeze: no new dependencies or build steps when creating the reconstruction module.
- Keep `StageB.run` parity guard telemetry/diagnostics intact; the new artifact field must not interfere with REFINE-FLOW-001 metrics.
- Preserve `docs/data_dependency_manifest.md` expectations for the smoke selectors (small-detector bundle, CLI sigma overrides) by exporting the documented env vars before each pytest command.
- When editing `run_nanobrag_refinement`, avoid altering the existing engine protocol/stage_modes telemetry enrichment; only the final-Bragg construction path should change.

If Blocked:
- If the new reconstruction module exposes a hidden dependency (e.g., missing bridge helper) or the stage artifacts cannot legally own the final Bragg tensor without duplicating large GPU buffers, stop, capture the traceback/note in `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T130500Z/blocked.md`, and update docs/fix_plan.md with the blocker details instead of forcing through an incomplete refactor. Note whether the block points to a required split with ARCH-ENGINE-ARTIFACTS-001.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage contexts + artifacts must replace the monolithic helper plumbing.
- ARCH-STAGE-CTX-002 — Stage B telemetry/guards must remain dataclass-safe while artifacts evolve.
- ARCH-ENGINE-002 — RefinementEngine consumers should rely on protocol artifacts rather than private caches; this change extends that guarantee to final Bragg tensors.

Pointers:
- dbex/nanobrag_refinement.py:700-1065 — engine branches currently rebuilding final Bragg tensors by calling the private helpers.
- dbex/refinement/stage_a.py:855-1270 — Telemetry + artifact assembly point that now needs to stash `bragg_full` when Stage A is terminal.
- dbex/refinement/stage_b.py:560-1005 — Stage B run path that will compute the final Bragg when Stage C is disabled.
- dbex/refinement/artifacts.py:11-105 — StageAArtifacts/StageBArtifacts definitions awaiting the new optional field.
- tests/dbex/test_stage_a_smoke_parity.py:15-181 — Example consumer whose import must be repointed to the new reconstruction module.

Next Up (optional):
- Once Stage A/B artifacts deliver Bragg tensors, ARCH-ENGINE-ARTIFACTS-001 can finish removing the remaining `run_nanobrag_refinement` special cases.
