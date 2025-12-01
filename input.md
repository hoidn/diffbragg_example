Summary: Force Stage A baseline/final validations into panel mode whenever Stage B runs so REFINE-FLOW-001 parity holds for ROI-heavy configs, then prove the guard + smoke matrix still passes with the tighter threshold.
Mode: Parity
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T160850Z/telemetry_stage_bc_small.json pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small; pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T160850Z/
Do Now:
- Implement: dbex/refinement/stage_a.py::StageA.run — Treat `config.enable_stage_b` as a trigger for `force_panel_validation`, make sure the flag is preserved on `stage_a_context` / `_run_stage_a_lbfgs`, and document the REFINE-FLOW-001 rationale so Stage B always inherits a panel-level canonical baseline even when ROI thresholds would have left Stage A in ROI mode.
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers — Set `stage_a_panel_validation_roi_threshold=0` (and mention why in the docstring) so the small-detector run emulates the ROI-heavy detector; keep existing assertions and the `stage_b_baseline_diff_path is None` guard so the test now fails without the Stage B-aware toggle.
- Validate: (1) AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small > plans/active/ARCH-REFINE-001/reports/2025-12-01T160850Z/collect_stage_bc_small.log; (2) AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T160850Z/telemetry_stage_bc_small.json pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T160850Z/pytest_stage_bc_small.log; (3) AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload > plans/active/ARCH-REFINE-001/reports/2025-12-01T160850Z/pytest_stage_b_guard.log
How-To Map:
1. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small > plans/active/ARCH-REFINE-001/reports/2025-12-01T160850Z/collect_stage_bc_small.log
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T160850Z/telemetry_stage_bc_small.json pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T160850Z/pytest_stage_bc_small.log
3. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload > plans/active/ARCH-REFINE-001/reports/2025-12-01T160850Z/pytest_stage_b_guard.log
Pitfalls To Avoid:
- Do not relax the REFINE-FLOW-001 tolerance (1e-3 relative) or swallow the guard RuntimeError; we need loud failures with diff JSON on regressions.
- Keep Stage A ROI closures untouched—only baseline/final validations should flip to panel mode for Stage B; ROI sampling powers Stage A/B performance.
- Scope the `stage_a_panel_validation_roi_threshold=0` change to the smoketest; production defaults must remain 32 so refGeom_small still auto-switches without Stage B.
- Preserve Stage C warm-cache behavior and telemetry; the Stage B toggle must not regress detector microslip when Stage C is enabled.
- Do not assume `DBEX_SMOKE_TELEMETRY_PATH` exists—guard writes must continue to derive directories from the env var and survive cwd fallback.
- Avoid touching CLI flags or other config entry points; this fix belongs inside Stage A/Stage B plumbing only.
- Keep Environment Freeze intact (no package installs, no new datasets beyond docs/data_dependency_manifest.md).
If Blocked:
- If Stage B smoketest still fails because the guard fires, capture `stage_b_baseline_diff.json`, the pytest log, and telemetry JSON, note the relative diff in docs/fix_plan.md Attempts History, and halt further code churn until the canonical snapshot mismatch is understood.
Findings Applied (Mandatory):
- REFINE-FLOW-001 — Stage B initial chi² must match Stage A final within 0.1%; the new Stage A toggle enforces parity before the guard fires.
- REFINE-010 — Auto panel validations remain required for low-ROI or Stage C runs; extending the condition to Stage B follows the same precedent.
- PHYSICS-LOSS-001 — Baseline comparisons stay in variance-weighted chi² space; do not change loss definitions while wiring the toggle.
Pointers:
- dbex/refinement/stage_a.py:214 — Current `force_panel_validation` computation tied to Stage C + ROI threshold.
- tests/dbex/test_torch_refine_smoke.py:1258 — Stage B smoketest config where the tighter threshold should be injected.
- tests/dbex/test_stage_b_cpu_fallback.py:380 — Guard regression test exercising `stage_b_baseline_diff.json` schema.
- docs/spec-db-workflow.md:58 — Stage B modifier contract + baseline reuse expectations.
- docs/findings.md:71 — REFINE-FLOW-001 context and tolerance requirements.
Next Up (optional): Investigate Phase E.3 once Stage B parity is locked—thread the guard outcomes into CLI telemetry and re-enable the full-detector smoketest when CPU fallback is repaired.
