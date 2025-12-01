Summary: Consolidate RefinementTelemetry into the canonical refinement.stage module so the engine path, stage wrappers, and CLI writer all share one schema before Phase C IO cleanup.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small; pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata; pytest -vv tests/dbex/test_refinement_engine.py
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/
Do Now:
- Implement: dbex/nanobrag_refinement.py::RefinementTelemetry — delete the duplicate dataclass, import the canonical definition from `dbex.refinement.stage`, and keep the module returning `Dict[str, RefinementTelemetry]` for all code paths.
- Implement: dbex/refinement/stage_a.py::StageA.run — swap the lazy `dbex.nanobrag_refinement` import for `dbex.refinement.RefinementTelemetry`, update StageB.run, StageC.run, and `stage_c_impl._run_stage_c_lbfgs` to consume the canonical class, and ensure no wrapper imports the monolith solely for type construction.
- Implement: tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata — adjust the telemetry mocks (and any helper scripts) to reference `dbex.refinement.RefinementTelemetry` so `_write_torch_outputs` is exercised against the shared schema; touch `dbex/refine_one.py::_write_torch_outputs` only if it still instantiates the old class.
- Validate: `pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small > plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/collect_stage_bc_small.log`.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/telemetry_stage_bc_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/pytest_stage_bc_small.log`.
- Validate: `pytest --collect-only tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata > plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/collect_cli_torch_diag.log` followed by `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/pytest_cli_torch_diag.log`.
- Validate: `pytest --collect-only tests/dbex/test_refinement_engine.py > plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/collect_engine_contract.log` followed by `pytest -vv tests/dbex/test_refinement_engine.py | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/pytest_engine_contract.log`.
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` and `mkdir -p plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z` to pin artifact locations.
2. Update `dbex/nanobrag_refinement.py`: remove the local `RefinementTelemetry` dataclass, add `from dbex.refinement import RefinementTelemetry`, and ensure helper code paths that previously instantiated the local class now call the shared version without changing field defaults.
3. Touch Stage wrappers (`dbex/refinement/stage_a.py`, `dbex/refinement/stage_b.py`, `dbex/refinement/stage_c.py`) plus `dbex/refinement/stage_c_impl.py` so they import `RefinementTelemetry` from `dbex.refinement` at module scope instead of lazily importing the monolith.
4. Search for `from dbex.nanobrag_refinement import RefinementTelemetry` (tests/scripts) and update each site to the canonical import; keep mocks constructing real dataclass instances so `_write_torch_outputs` and engine tests exercise the single schema.
5. Log selector health with the collect-only commands above before executing each pytest run; stash all logs/telemetry JSON in the timestamped report directory.
6. After all tests pass, capture any additional telemetry (e.g., `telemetry_stage_bc_small.json`) required by docs/fix_plan.md references.
Pitfalls To Avoid:
- Do not edit ROI/sample logic or other refinement behavior—only update telemetry class imports.
- Preserve field defaults and ordering inside the canonical dataclass; avoid dropping optional fields used by `/torch_diagnostics` consumers.
- Stage wrappers must continue to avoid eager simulator imports; keep new imports lightweight and module-local when necessary.
- When cleaning up imports, do not break `RefinementEngine` circularity (avoid referencing stage modules from inside dataclass definitions).
- Maintain Environment Freeze: no package installs or dependency upgrades.
- Keep CLI tests hermetic; do not touch dataset assets listed in docs/data_dependency_manifest.md.
- Ensure smoke tests run with the provided env vars so telemetry paths are written under the correct artifacts directory.
If Blocked:
- Save the failing log (collect + pytest) under `plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/blocked.log`, note the failure signature (e.g., missing field or import loop) in docs/fix_plan.md Attempts History and galph_memory.md, then stop for supervisor guidance.
Findings Applied (Mandatory):
- DIAGNOSTICS-001 — `/torch_diagnostics` schema must remain stable; validate via CLI telemetry test.
- PHYSICS-LOSS-001 — Canonical chi-squared and sigma provenance fields live on RefinementTelemetry; consolidating the class keeps these metrics intact.
- ARCH-ENGINE-003 — Engine telemetry enrichment depends on a single dataclass, so stage wrappers must stop importing stale definitions.
Pointers:
- docs/spec-db-workflow.md:33 — Engine contract + telemetry invariants guiding the consolidation.
- docs/architecture/data_telemetry_flow.md:24 — `/torch_diagnostics` schema that the shared dataclass must represent.
- plans/active/ARCH-REFINE-001/implementation.md:200 — Phase C checklist for telemetry + IO cleanup.
Next Up (optional): Begin Phase C.2 by extracting the shared torch writer once the canonical telemetry definition is stable.
Doc Sync Plan (Conditional): none — no new selectors are added.
Mapped Tests Guardrail: The collect-only steps above must show ≥1 collected test per selector before running full pytest; if any selector collects 0, treat it as a block and capture evidence before proceeding.
