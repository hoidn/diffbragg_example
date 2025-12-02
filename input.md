Summary: Make the Stage wrappers import their dependencies explicitly so the refinement pipeline no longer relies on `_lazy_import_refinement` or hidden run-time imports.
Mode: none
InitiativeType: architecture
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests:
- pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small
- pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T232800Z/{collect_stage_a_small.log,pytest_stage_a_small.log,telemetry_stage_a_small.json,collect_stage_b_small.log,pytest_stage_b_small.log,telemetry_stage_b_small.json,collect_stage_c_small.log,pytest_stage_c_small.log,telemetry_stage_c_small.json,summary.md}

Do Now:
- Implement: `dbex/refinement/stage_a.py::StageA.run` — delete `_lazy_import_refinement`, move the `stage_a_impl` helper imports plus `RefinementTelemetry` into module scope (`from dbex.refinement.stage import RefinementTelemetry`), and adjust the body to use the eager imports. Update the module docstring/comments so they explain the explicit dependency graph instead of referencing lazy imports.
- Implement: `dbex/refinement/stage_b.py::StageB.run` and `dbex/refinement/stage_c.py::StageC.run` — hoist the helper imports (`stage_b_impl`, `stage_c_impl`), `RefinementTelemetry`, the `dbex.nanobrag_bridge` factories, and the `nanobrag_torch` Detector/Crystal/Simulator classes to module scope. Remove the run-scoped import blocks and ensure the modules still expose the same public API. Keep device/dtype handling untouched.
- Validate: rerun the small-detector Stage smokes (collect-only + execution for Stage A, Stage B, Stage C) with the standard env block from `docs/TESTING_GUIDE.md`, capturing logs/telemetry under the new artifact directory to prove the eager imports do not change behavior.

How-To Map:
1. Module import cleanup  
   - In `dbex/refinement/stage_a.py`, add module-level imports:  
     `from dbex.refinement.stage import RefinementTelemetry`  
     `from dbex.refinement.stage_a_impl import _build_stage_a_params, _build_stage_a_lbfgs_closure, _run_stage_a_lbfgs, vec_to_unit_quaternion, quaternion_to_xyz_euler`.  
     Remove `_lazy_import_refinement` and the `from dbex.refinement import RefinementTelemetry` block inside `run()`. Ensure the rest of the function references the already-imported helpers.  
   - Mirror the pattern for Stage B/C: add module-level imports for their helper modules, for `RefinementTelemetry`, and for the `dbex.nanobrag_bridge` + `nanobrag_torch` symbols they use. Delete the `from ... import ...` block inside each `run()` method and keep the rest of the logic identical. Update module-level comments to mention the explicit imports instead of “lazy” semantics.
2. Smoketest execution (repo root)  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small > plans/active/ARCH-REFINE-001/reports/2025-12-01T232800Z/collect_stage_a_small.log`  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T232800Z/pytest_stage_a_small.log`  
   - Repeat the collect + run commands for `test_stage_b_shell_modifiers` and `test_stage_c_detector_microslip`, writing their logs/telemetry into the same directory (Stage B/C runs still need `DBEX_SMOKE_SIGMA_SOURCE=cli_override` and `DBEX_SMOKE_DETECTOR_SIZE=small`; Stage C also needs `DBEX_SMOKE_TELEMETRY_PATH=…/telemetry_stage_c_small.json`).
3. Telemetry capture  
   - For Stage B and C, set `DBEX_SMOKE_TELEMETRY_PATH` so pytest saves telemetry JSON (`telemetry_stage_b_small.json`, `telemetry_stage_c_small.json`) into the artifact directory; these files prove the eager imports did not change telemetry content.

Pitfalls To Avoid:
- Do not reintroduce circular imports by pulling `RefinementTelemetry` from `dbex.refinement`—import it from `dbex.refinement.stage` to keep module initialization order safe.
- Preserve Environment Freeze (POLICY-001): no new dependencies or package installs; only move existing imports.
- Keep helper modules importable without side effects (no module-level logging/print statements).
- Make sure Stage B/C still guard against missing halo metadata and baseline detectors; refactor must not bypass those runtime checks.
- When editing docstrings/comments, avoid deleting references to ARCH-REFINE-001 phases that still describe normative behavior; only adjust the parts that explained lazy imports.
- Ensure telemetry dictionaries still instantiate `RefinementTelemetry` exactly as before; eager imports should not change serialization order.

If Blocked:
- If a new circular import appears (e.g., StageA importing `dbex.refinement` indirectly), capture the traceback, stash it in `plans/active/ARCH-REFINE-001/reports/2025-12-01T232800Z/blocked.md`, and restore the previous import structure until the dependency chain is understood. Record the block in docs/fix_plan.md and note which module pair caused the cycle.

Findings Applied (Mandatory):
- ARCH-ENGINE-002 — Stage wrappers must continue to satisfy the RefinementStage contract and telemetry schema even after the import cleanup.
- POLICY-001 — Environment Freeze prohibits adding dependencies; the refactor is limited to reorganizing imports.

Pointers:
- dbex/refinement/stage_a.py:1-480 — Stage wrapper needing the `_lazy_import_refinement` removal.
- dbex/refinement/stage_b.py:1-430 & dbex/refinement/stage_c.py:1-520 — Stage wrappers that currently import helpers lazily.
- problems.md (Architectural Code Smells entry) — Ledger requirement driving this cleanup.

Next Up (optional): Once the eager-import refactor lands, reassess whether ARCH-REFINE-001 can be archived or if additional ledger bullets (writer consolidation, physics helpers) warrant a follow-on phase.
