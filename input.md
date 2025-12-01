Summary: Scrub Stage A tooling/docs of the removed `use_engine_delegation` flag so probes/tests run on the default RefinementEngine path without TypeErrors.
Mode: Parity
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: pytest --collect-only tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity; pytest -vv tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity; pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry; pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T144500Z/
Do Now:
- Implement: dbex/tools/stage_a_adam.py::run_engine_zero_point_probe — drop the deprecated `use_engine_delegation` kwarg when calling `run_nanobrag_refinement`, guard against missing Stage A telemetry, and refresh the docstring/comments so zero-point probes explicitly describe the RefinementEngine-only flow.
- Implement: plans/active/TOOLING-VIS-001/bin/{compare_stage_a_mapping_parity.py::main, generate_stage_a_refgeom_roi_triptychs_adam.py::main, run_stage_a_engine_zero_point_probe.py::main} — update their helper calls/help text to match the new API (no `use_engine_delegation` flag) and ensure they keep forwarding calibration + baseline geometry inputs unchanged.
- Document: docs/architecture/live_backend.md; docs/architecture/data_telemetry_flow.md; docs/TESTING_GUIDE.md; docs/development/TEST_SUITE_INDEX.md — rewrite the affected sections/rows so they describe RefinementEngine as the sole execution path, remove wording that calls the contexts “planned,” and explain that the Stage A telemetry selector now validates the default engine route.
- Validate: capture the Stage A zero-point + telemetry selectors (collect-only first, then full run) with `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`, `DBAT027_ARTIFACT_DIR=plans/active/ARCH-REFINE-001/reports/2025-12-01T144500Z/db_at_027`, and `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` set for the smoke test; tee logs into the artifacts directory named in the mapped tests.
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` and `export DBAT027_ARTIFACT_DIR=plans/active/ARCH-REFINE-001/reports/2025-12-01T144500Z/db_at_027`; ensure `plans/active/ARCH-REFINE-001/reports/2025-12-01T144500Z/` exists for logs + doc diffs.
2. Update `dbex/tools/stage_a_adam.py::run_engine_zero_point_probe` to remove the stale kwarg, keep lazy imports, raise `RuntimeError` if `'A'` telemetry missing, and adjust docstrings/comments to describe engine-only execution.
3. Edit TOOLING-VIS-001 debug CLIs (`compare_stage_a_mapping_parity.py`, `generate_stage_a_refgeom_roi_triptychs_adam.py`, `run_stage_a_engine_zero_point_probe.py`) so every `run_nanobrag_refinement` call matches the new signature and the CLI usage text references RefinementEngine rather than `--use-engine-delegation`.
4. Refresh `docs/architecture/live_backend.md` + `docs/architecture/data_telemetry_flow.md` to say RefinementContext/JobContext are in production and the inline monolith is gone; update `docs/TESTING_GUIDE.md` §2 (engine telemetry row) and `docs/development/TEST_SUITE_INDEX.md` accordingly. Capture `git diff docs` output into `plans/active/ARCH-REFINE-001/reports/2025-12-01T144500Z/docs_diff.md`.
5. Run the mapped selectors in order, saving collect-only logs before each full pytest run. Ensure env vars (`KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`) are set for the smoke test; keep tee’d logs under the artifacts directory names listed in Do Now.
Pitfalls To Avoid:
- Do not reintroduce optional inline code paths or the removed `use_engine_delegation` kwarg; RefinementEngine must remain the only execution route (ARCH-ENGINE-003).
- Preserve lazy imports + device/dtype neutrality inside Stage A tooling while editing helper code; no eager torch allocations during module import.
- Keep canonical refGeom assets untouched; Stage A zero-point test depends on `sp.proc/refGeom*.{expt,refl}`, mask, HKL bundles per docs/data_dependency_manifest.md.
- When updating docs/tests, reference the new IDLs instead of duplicating API text; avoid paraphrasing spec equations.
- Maintain Environment Freeze (POLICY-001): no package installs or dataset regeneration—log blockers instead.
- Collect-only logs must be recorded before each pytest run to satisfy selector health tracking.
- Watch for cached artifacts under `plans/active/...`; do not overwrite prior evidence outside the new timestamped directory.
If Blocked:
- If Stage A zero-point probe fails due to missing assets or telemetry keys, capture the pytest log, save it under the artifacts directory, and record the failure signature + env vars in docs/fix_plan.md Attempts History and galph_memory.md before stopping.
- If docs/tests reveal additional references to `use_engine_delegation` you cannot safely remove, note the remaining files + rationale in docs/fix_plan.md and return the loop as blocked for supervisor triage.
Findings Applied (Mandatory):
- ARCH-ENGINE-003 — Engine telemetry enrichment must stay on the active code path; removing the flag ensures compliance.
- REFINE-010 — Stage A ROI/panel guardrails stay in effect when running zero-point probes; do not change ROI thresholds while editing tooling.
- PHYSICS-LOSS-001 — Variance-weighted loss math in probes/tests must remain untouched.
- POLICY-001 — Environment Freeze prohibits pip/conda installs or dataset regeneration.
Pointers:
- docs/TESTING_GUIDE.md:160 — Selector details + env vars for `test_stage_a_engine_delegation_telemetry`.
- docs/architecture/live_backend.md:20 — Current Torch backend description to update with engine-only notes.
- docs/architecture/data_telemetry_flow.md:5 — Pipeline description still mentioning “planned” contexts; align it with Phase B completion.
- docs/findings.md:75 — ARCH-ENGINE-003 guardrail on telemetry enrichment placement.
- docs/data_dependency_manifest.md:70 — Required assets for Stage A/DB-AT-027 probes.
Next Up (optional): After the flag cleanup, finish Phase D by capturing architecture_doc_update.md (D5) if capacity allows.
Doc Sync Plan (Conditional): Not applicable (no new selectors added).
Mapped Tests Guardrail: Store the `collect_db_at_027_zero_point.log` and `collect_stage_a_engine_telemetry.log` outputs before running the corresponding full pytest commands; if either selector reports 0 tests collected, stop immediately and diagnose before editing code further.
