Summary: Thread the CLI-built HKL halo + ASU metadata into RefinementContext so Stage B/C consume the same tensors without recomputing, then prove Stage B/C smokes still pass on the small-detector bundle.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T123044Z/
Do Now:
- Implement: dbex/refinement/context.py::build_refinement_context — copy `asu_map`/`hkl_indices_grid`/halo mask from the CLI JobContext into the RefinementContext, teach StageB.run/_build_stage_b_params (and the Stage C warm-cache retargeters) to consume those tensors before falling back to cctbx, and create docs/architecture/dbex/refinement/context.idl.md describing the new context fields.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T123044Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small (repeat for Stage C with its telemetry path) and store logs under the artifacts directory.
How-To Map:
1. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small > plans/active/ARCH-REFINE-001/reports/2025-12-01T123044Z/collect_stage_bc_small.log
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T123044Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T123044Z/pytest_stage_b_small.log
3. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T123044Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T123044Z/pytest_stage_c_small.log
Pitfalls To Avoid:
- Keep device/dtype neutrality when threading `asu_map`; do not `.to("cuda")` inside builders—Stages manage device placement.
- Do not import cctbx in module scope; keep lazy imports/Fallbacks per Environment Freeze.
- Preserve Stage B per-reflection fallback logic: use the context `asu_map` when available but leave compute_hkl_asu_map as a fallback path with clear warnings.
- Avoid touching simulator factory helpers; Stage closures still instantiate `nanobrag_torch.Simulator` directly (ARCH-FACTORY-001).
- When updating Stage C warm-cache hooks, never detach detector offsets (GRADIENT-004) or nullify the Stage A ROI auto-panel telemetry (REFINE-010).
If Blocked:
- Capture the failing selector output under the artifacts directory (e.g., `blocked_stage_b.log`), cite the selector + error in docs/fix_plan.md Attempts History, and log the same signature in galph_memory before requesting rescope instructions.
Findings Applied (Mandatory):
- REFINE-005 — Stage B requires haloed HKL grids with tricubic interpolation; ensure the context builder enforces `hkl_metadata['has_halo']` before allowing Stage B/C to run.
- REFINE-010 — Stage A/C telemetry coupling depends on panel-mode validation; keep the ROI auto-panel fallback intact while threading new metadata.
- GRADIENT-004 — Warm-cache retargeting must keep detector offsets as tensors; the Stage C updates here must preserve autograd links when reusing context metadata.
Pointers:
- docs/fix_plan.md:330 — Phase B.2 completion notes and new Phase B.3 scope.
- plans/active/ARCH-REFINE-001/implementation.md:108 — Phase B checklist describing the shared HKL context requirement.
- docs/data_dependency_manifest.md:52 — refGeom_small assets and overrides used by the mapped smoke selectors.
Next Up (optional): Phase B.4 — wire the simulator factory for forward-only helpers once the shared context metadata has been stabilized.
