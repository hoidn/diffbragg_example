Summary: Rebuild `_build_final_bragg_from_stage_a_telemetry` so Stage A telemetry can hydrate a valid `CrystalConfig` and unblock the RefinementContext Stage B.1 smoke regressions.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/
Do Now:
- Implement: dbex/nanobrag_refinement.py::_build_final_bragg_from_stage_a_telemetry — clamp the Stage A log cell/angle telemetry deltas, convert them to `crystal_overrides` + `misset_deg_override`, and call `create_crystal_config` with those overrides so both the warm-cache retargeter and the cold Simulator path receive the same `CrystalConfig` object that Stage B already uses.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_a_expansion or test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/pytest_stage_smokes_small.log
How-To Map:
1. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_a_expansion or test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small > plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/collect_stage_smokes_small.log
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/pytest_stage_a_small.log
3. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/pytest_stage_b_small.log
4. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/pytest_stage_c_small.log
Pitfalls To Avoid:
- Do not change `create_crystal_config` signature; Stage B already depends on the current override API.
- Preserve the warm-cache path by passing the new `CrystalConfig` into `_retarget_stage_a_simulators` exactly as Stage B does.
- Keep Stage A ROI auto-panel behavior (REFINE-010) intact: the reconstruction helper must not reintroduce ROI-only validations.
- Respect Environment Freeze (no new deps, no torch upgrades); only touch the existing Python sources.
- Maintain telemetry schema (`stage_type`, `engine_protocol`, `stage_modes`) so ARCH-ENGINE-003 stays satisfied.
- Leave Stage B/C reconstruction math as-is—only Stage A’s helper needs the override plumbing.
- Always set `DBEX_SMOKE_SIGMA_SOURCE=cli_override`/`DBEX_SMOKE_DETECTOR_SIZE=small`; the guards in `tests/conftest.py` will abort otherwise.
If Blocked:
- Capture the failing stack trace + pytest log under the artifacts directory, add an Attempts History note in docs/fix_plan.md describing the exact exception, and mark ARCH-REFINE-001 `blocked` in galph_memory until the telemetry mismatch is understood.
Findings Applied (Mandatory):
- REFINE-010 — Stage A panel-mode telemetry must remain in sync with Stage C gates, so the reconstruction helper must keep the panel path enabled when Stage C is active.
- GEOMETRY-003 — Orientation deltas are always relative to the baseline misset; ensure the baseline misset tensor is added before calling `create_crystal_config`.
- GRADIENT-004 — Warm-cache retargeting must keep tensors attached; avoid `.item()` / `.cpu()` when constructing the refined `CrystalConfig`.
Pointers:
- docs/fix_plan.md (ARCH-REFINE-001 Phase B.1 entry) — scope + acceptance criteria for this handoff.
- plans/active/ARCH-REFINE-001/implementation.md §Phase B — checklists for RefinementContext + reconstruction tasks.
- docs/spec-db-workflow.md §7 & §Optimization Strategy — normative definitions for Stage A/B/C parameterization and ROI policies.
- docs/TESTING_GUIDE.md §1.1–§2 — required env vars and telemetry expectations for Stage smokes.
Next Up (optional): If Stage A reconstruction passes quickly, move to Phase B.2 (JobContext wiring) per plans/active/ARCH-REFINE-001/implementation.md.
