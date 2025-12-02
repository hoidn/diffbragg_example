Summary: Hoist the remaining Stage A/C lazy imports to module scope and prove the refactor keeps the small-detector Stage A/B/C smokes green.
Mode: none
InitiativeType: architecture
Focus: ARCH-LAZY-IMPORTS-001 — Lazy imports / process-noise hygiene
Branch: integration
Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-03T223500Z/pytest_stage_a_expansion.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry | tee plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-03T223500Z/pytest_stage_a_engine_telemetry.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-03T223500Z/pytest_stage_c_smoke.log
Artifacts: plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-03T223500Z/
Do Now:
- Implement: dbex/refinement/stage_a_impl.py::_build_stage_a_context & _compute_panel_loss plus the Stage A diagnostics footer, and dbex/refinement/stage_c_impl.py::_retarget_stage_a_detectors & _run_stage_c_lbfgs. Hoist the shared dependencies (`create_detector_config/create_beam_config/create_crystal_config`, `Detector/Crystal/Simulator`, `json`, `Path`, `warnings`) to module scope with a short ARCH-ENGINE-002 comment, then delete the per-call `import` statements so the hot loops stop hiding dependencies. Ensure the panel-diagnostics writers in both stages use the new module-scope imports and keep the environment guards intact.
- Tests: run the three mapped selectors with the canonical env flags above; stop on the first failure, keep the log, and add a short note to docs/fix_plan.md before escalating.
- Artifacts: tee the pytest output into `pytest_stage_a_expansion.log`, `pytest_stage_a_engine_telemetry.log`, and `pytest_stage_c_smoke.log` under the artifacts directory, and leave any supporting `rg`/diff output in the same folder if you capture it.
How-To Map:
1. Stage A imports — add module-scope imports for `json`, `Path`, `Detector`, `Crystal`, `Simulator`, and the config factories near the top of `dbex/refinement/stage_a_impl.py`, keeping `compute_baseline_misset_deg` sourced from `dbex.nanobrag_bridge`. Remove the inline `from ... import ...` blocks inside `_build_stage_a_context` and `_compute_panel_loss`, and update the Stage A diagnostics writer at the end of `_run_stage_a_lbfgs` to use the shared `Path/json` objects instead of re-importing them. Run `rg -n "^\s+import" dbex/refinement/stage_a_impl.py` to confirm no inline imports remain.
2. Stage C imports — add `import warnings` beside the existing module-scope imports in `dbex/refinement/stage_c_impl.py`, drop the inline `import warnings` in `_retarget_stage_a_detectors`, and delete the `import os/json/Path` block in `_run_stage_c_lbfgs` so the diagnostics writer reuses the existing module-level imports. Keep the PERF-WARM-016 debug guard path untouched aside from borrowing the shared `warnings` object.
3. Validation — with code staged, run the three pytest commands listed above (set `DBEX_SMOKE_DETECTOR_SIZE=small` for all of them) and tee each run into the artifacts directory. Leave the repo clean when done.
Pitfalls To Avoid:
- Do not reintroduce lazy imports elsewhere—ARCH-ENGINE-002 requires module-scope dependency declarations so import errors surface early.
- Keep Environment Freeze intact: no package installs or torch upgrades while editing hot loops.
- Preserve PERF-WARM-016 hooks: debug snapshots must remain optional and tolerant of filesystem failures.
- Leave Stage A/B/C telemetry untouched aside from import cleanup; collector ownership now lives under ARCH-TELEMETRY-001, so avoid dict shims.
- Respect the existing env guards (`DBEX_STAGE_A/C_PANEL_DIAG_DIR`); never write panel diagnostics when the env var is unset.
If Blocked:
- Capture the failing selector log plus a short summary (what failed, which env flags) in `plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-03T223500Z/`, update docs/fix_plan.md Attempts History with the failure signature, and halt so the supervisor can reassess scope.
Findings Applied (Mandatory):
- ARCH-ENGINE-002 — Stage helper modules must expose dependencies at module scope; this refactor enforces that policy.
- RUNTIME-001 — Keep `NANOBRAGG_DISABLE_COMPILE=1` when running parity smokes so torch.compile does not interfere with gradient paths.
Pointers:
- docs/fix_plan.md:161 — latest planning entry describing the Stage A/C lazy-import cleanup scope.
- plans/active/ARCH-LAZY-IMPORTS-001/implementation.md:61 — Phase B.3 checklist + validation targets for this focus.
- docs/TESTING_GUIDE.md:162 — canonical Stage A/B/C smoketest commands and env requirements.
Next Up: Phase C process-noise cleanup (docstring/spec citation sweep + hygiene selector) once Stage A/C imports are eager.
Doc Sync Plan: none — mapped selectors already live in TESTING_GUIDE.md/TEST_SUITE_INDEX.
Mapped Tests Guardrail: Existing selectors collect >0 tests; no new authoring needed before implementation.
Hard Gate: Do not land if any mapped selector regresses; this initiative only moves when Stage A/B/C smokes are green with artifacts captured.
Normative Math/Physics: See docs/spec-db-workflow.md §§30-65 and docs/spec-db-core.md §§57-90 for the stage contracts and variance-weighted χ² definitions that must remain unchanged.
