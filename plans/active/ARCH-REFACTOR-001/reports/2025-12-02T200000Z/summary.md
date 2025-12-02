### Turn Summary
Extracted 7 cross-stage helpers from stage_a_impl.py to new stage_a_utils.py module (730 lines); updated imports across 5 files (stage_a, stage_b, stage_c, reconstruction, plus bugfix in stage_a.py).
All 4/4 validation selectors passed: Stage A expansion (7.42s, 58.2% improvement), Stage B guard (0.79s), Stage B shell (23.33s), Stage C microslip (6.95s).
Next: Phase C.8 — inline Stage-A-private helpers (_sync_stage_a_crystal, _build_stage_a_params, _run_stage_a_lbfgs) into StageA class.
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T200000Z/ (pytest_stage_a.log, pytest_stage_b_guard.log, pytest_stage_b_shell.log, pytest_stage_c.log)
