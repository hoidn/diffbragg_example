Summary:
- Split `RefinementInputs` + config builders out of `dbex/nanobrag_bridge.py` into purpose-built `dbex/refinement/inputs.py` and `dbex/refinement/config_factories.py`, rewire the core modules/docs to those new homes, and keep the bridge module as thin orchestration glue.

Mode: none

InitiativeType: architecture

Focus: ARCH-BRIDGE-RESP-001 — Writer / bridge responsibility split

Branch: integration

Mapped tests:
- tests/dbex/test_nanobrag_bridge.py
- tests/dbex/test_nanobrag_bridge_configs.py
- tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator
- tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_applies_calibration
- tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
- tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion

Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T020500Z/

Do Now:
- Implement: dbex/refinement/inputs.py::{RefinementInputs,prepare_refinement_inputs} — move the dataclass + builder logic out of `dbex/nanobrag_bridge.py` unchanged (sigma broadcast, sentinel guards, ADU↔photon policy), export them from the new module, and update `dbex/physics/forward.py`, `dbex/refine_one.py`, `dbex/data_load.py`, and `dbex/vis/mapping.py` to import from the new path. Keep `dbex.nanobrag_bridge` importing and re-exporting these names (with a `# TODO(ARCH-BRIDGE-RESP-001)` deprecation note) so tests that still import from the bridge keep working this loop.
- Implement: dbex/refinement/config_factories.py::{create_detector_config,create_beam_config,create_crystal_config} — transplant the detector/beam/crystal hydration helpers verbatim (square-pixel guard, DIALS Euler extraction, trusted-mask torch tensors, ROI cropping, distance override tensors, calibration metadata) and switch every `dbex/*` caller (stage modules, CLI, reconstruction, nanobrag_refinement, forward helper, tools) to import from the new module instead of `dbex.nanobrag_bridge`. Leave a compatibility re-export in `dbex.nanobrag_bridge` so downstream tests/scripts can be updated incrementally, and add a brief module docstring stating the bridge now delegates to refinement-level helpers.
- Update docs: refresh `docs/data_dependency_manifest.md` (inputs + config sections should point to the new modules), `docs/architecture/live_backend.md` (pipeline bullets referencing `prepare_refinement_inputs`/factory helpers), and `docs/architecture/dbex/io/writer.idl.md` (note that `RefinementInputs` now lives under `dbex/refinement/inputs`). Capture a short `bridge_split_summary.md` in the artifacts directory describing the before/after responsibility map and note the temporary re-export layer.

How-To Map:
1. `mkdir -p dbex/refinement && touch dbex/refinement/__init__.py` if the package file does not exist. Create `dbex/refinement/inputs.py` by moving the dataclass/function block from `dbex/nanobrag_bridge.py` wholesale; keep numpy/scipy imports identical so behavior stays byte-for-byte. Update `dbex/nanobrag_bridge.py` to `from dbex.refinement.inputs import RefinementInputs, prepare_refinement_inputs` and set `__all__` accordingly with a deprecation comment.
2. Create `dbex/refinement/config_factories.py` with the existing detector/beam/crystal helpers plus any supporting constant imports (torch, numpy, scitbx). Import this module everywhere inside `dbex/` that previously reached into the bridge (stage_a/b/c modules, `nanobrag_refinement.py`, `reconstruction.py`, CLI, physics forward helper, stage_a_adam, etc.). Leave re-exports in `dbex.nanobrag_bridge` (`create_detector_config = config_factories.create_detector_config`, etc.) so external scripts/tests continue to resolve the old names.
3. Adjust tooling/tests that live inside the repo (e.g., `scripts/generate_simple_cubic_golden.py`, plan-local probes) only if they import from `dbex.` modules; third-party consumers can rely on the re-exports. Run `python -m compileall dbex/refinement` or simply `python -m compileall dbex` if you want to sanity-check import errors before pytest.
4. Update docs: edit `docs/data_dependency_manifest.md` to mention `dbex/refinement/inputs.py` as the owner of RefinementInputs and `dbex/refinement/config_factories.py` as the detector/beam/crystal mapping surface; tweak `docs/architecture/live_backend.md` bullet lists and `docs/architecture/dbex/io/writer.idl.md` tables to cite the new module paths. Add a short `bridge_split_summary.md` (bullet list of what moved + re-export note) under the artifacts directory.
5. Validate the mapped selectors with authoritative env flags, capturing logs under the artifact path:
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_nanobrag_bridge.py | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T020500Z/pytest_bridge.log`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_nanobrag_bridge_configs.py | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T020500Z/pytest_bridge_configs.log`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator ::test_nanobrag_backend_applies_calibration ::test_torch_diagnostics_metadata | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T020500Z/pytest_cli.log`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=cli_override KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T020500Z/pytest_stage_a_smoke.log`

Pitfalls To Avoid:
- Do not change the semantics of `prepare_refinement_inputs` (sentinel guard, ROI slicing, sigma broadcasting); aim for a pure move so Stage A/B/C telemetry stays identical.
- Preserve torch tensor coercion for trusted masks and the ROI cropping logic when moving `create_detector_config`; any regression here would violate GEOMETRY-001/002 and CLI-001.
- Watch for circular imports when stages pull from the new module. Keep helpers import-only (no torch device instantiation at module scope) and, if needed, move heavy imports inside functions.
- Maintain the temporary re-export layer in `dbex.nanobrag_bridge` until the test-suite is updated; removing it prematurely will break dozens of selectors.
- Update `__all__`/module docstrings to prevent lint warnings, but avoid editing unrelated code paths (Stage B/C logic) this loop.

If Blocked:
- If creating `dbex/refinement/config_factories.py` introduces an import cycle (e.g., stage modules importing each other), capture the traceback plus which modules participate, add a `blockers.md` note under the artifact path with the stack trace + proposed mitigation, and update `docs/fix_plan.md` + `galph_memory.md` with the block description. Do not hack around the cycle by inlining logic back into the bridge; escalate instead.

Findings Applied (Mandatory):
- GEOMETRY-001 / GEOMETRY-002 / GEOMETRY-003 — detector/beam/crystal mapping must continue to match the DIALS conventions documented in `docs/config_crosswalk.md`; the new factories must enforce the same guards.
- CONFIG-001 — keep `[panel, slow, fast]` array ordering, mask polarity, and ADU↔photon policies intact when relocating helpers.
- DIAGNOSTICS-001 & PHYSICS-LOSS-001/002/003 — reader/writer telemetry requires the same variance-weighted loss inputs; moving the builders must not change sigma provenance or loss-mask semantics.

Pointers:
- docs/spec-db-workflow.md:16-45 — canonical mask/prep and calibration policy that `prepare_refinement_inputs` enforces.
- docs/config_crosswalk.md:17-95 — mapping rules for detector/beam/crystal factories that must carry over to the new module.
- docs/data_dependency_manifest.md:120-190 — current ROI helper descriptions that need to be updated to mention the new modules.
- plans/active/ARCH-BRIDGE-RESP-001/implementation.md:80-96 — Phase C checklist describing the new module boundaries and artifacts expectations.
- docs/fix_plan.md:116-124 — attempts history showing why the bridge split is required and which selectors guard it.

Next Up (optional):
- Once the factories live under `dbex/refinement/`, schedule a follow-up to remove the compatibility re-exports and update the remaining tests/scripts to import from the new modules directly.
