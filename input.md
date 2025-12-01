Summary: Relocate Stage A contexts/helpers out of `dbex.nanobrag_refinement` so the RefinementEngine path owns its closure without monolith imports.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small, tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry --smoke-detector-size=small, tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/
Do Now:
- Implement: dbex/refinement/stage_a.py::StageA.run — move `_build_stage_a_params/_build_stage_a_lbfgs_closure/_run_stage_a_lbfgs`, `StageAROIEntry`, `StageAContext`, and the quaternion helpers into a new `dbex/refinement/stage_a_impl.py` (or equivalent) so this class depends only on refinement modules while preserving telemetry fields, warm-cache plumbing, and device/dtype neutrality.
- Implement: dbex/nanobrag_refinement.py::_build_stage_a_params — replace the in-file helper/dataclass definitions with imports from the new refinement module (and update `dbex/tools/stage_a_adam.py` accordingly) so the inline path and engine share a single implementation source.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/pytest_stage_a_engine.log
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/pytest_stage_b_small.log
How-To Map:
1. mkdir -p plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/pytest_stage_a_helpers_collect.log
3. Run both Stage A selectors per the Validate step and archive `pytest_stage_a_engine.log` to the artifacts directory.
4. Export DBEX_SMOKE_TELEMETRY_PATH as shown in the Validate command, rerun the Stage B selector, and capture both the pytest log and telemetry JSON in the artifacts directory for perf regressions.
5. Summarize the helper relocations plus test outcomes in plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/summary.md (include pointers to modified modules and telemetry files).
Pitfalls To Avoid:
- Do not create new circular imports; the helper module must stay free of `dbex.refinement.stage_a` or CLI-facing modules.
- Preserve StageAContext warm/cold semantics (PERF-WARM-001); cloning contexts for CPU fallback must still work for Stage B ROI reuse.
- Keep telemetry schemas identical (PHYSICS-LOSS-001/003): `stage_type`, `mode`, variance-floor stats, and sigma provenance must survive the move.
- Update every existing consumer of `vec_to_unit_quaternion`/`quaternion_to_xyz_euler` (including `dbex/tools/stage_a_adam.py`) so no module silently re-imports from the monolith.
- Avoid touching nanobrag_torch or installing packages (Environment Freeze / POLICY-001).
- Maintain dtype/device neutrality inside helpers; no `.cuda()` assumptions when moving tensors.
- Ensure inline reconstruction paths (`_build_final_bragg_from_stage_a_telemetry`) continue importing the relocated helpers so engine vs inline parity stays intact (REFINE-FLOW-001).
If Blocked:
- If helper extraction exposes missing upstream modules or cyclic imports you cannot break cleanly, capture the stack trace plus partial diffs under the artifacts directory, mark ARCH-REFINE-001 `blocked` in docs/fix_plan.md with the error signature, and log the issue in galph_memory before pausing.
Findings Applied (Mandatory):
- PHYSICS-LOSS-001 — Stage telemetry must keep chi-squared/masked-MSE dual metrics and sigma provenance when helpers move.
- PERF-WARM-001 — StageAContext cache semantics cannot regress while relocating dataclasses.
- REFINE-FLOW-001 — Engine delegation must keep Stage B initial chi² aligned with Stage A, so helper dedupe must not change parameter reconstruction.
- POLICY-001 — No environment/package changes while refactoring helpers.
Pointers:
- plans/active/ARCH-REFINE-001/implementation.md:1 — Phase A checklist calling for Stage extraction and context consolidation.
- dbex/nanobrag_refinement.py:584 — Current StageAContext/dataclass and helper definitions slated for relocation.
- dbex/refinement/stage_a.py:31 — StageA class still importing helper functions from the monolith.
- docs/spec-db-workflow.md:49 — Engine contract + Stage definitions governing how Stage modules must behave.
- docs/TESTING_GUIDE.md:31 — Stage smoke env requirements and guards applied to the mapped selectors.
Next Up (optional):
- After the helpers live under refinement/, plan the follow-up loop to delete the inline Stage A branch and run Stage C via `RefinementEngine([StageA(), StageB(), StageC])`.
