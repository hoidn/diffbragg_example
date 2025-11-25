### Turn Summary
Framed the next increment to thread the apply_calibration_n_cells gate through the Stage A engine config/context so Stage A stops re-enabling DiffBragg N_cells when mapping suppressed them.
Captured Ralph’s latest telemetry (scale ratio fixed but chi² still huge) and updated docs/fix_plan.md plus galph_memory with the gating gap and new artifacts path.
Next: implement the config/context/CLI changes per input.md and rerun DB-AT-028/029 to record telemetry showing n_cells_applied=false.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T170322Z/ (input.md, pytest_db_at_028_029*.log)
