### Turn Summary
Reopened ARCH-SIM-CONSTRUCTION-001 after closing the DIAG and ARCH-SIM-HKL-BOUNDS initiatives and updated docs/fix_plan.md plus the implementation plan to focus on the remaining intensity gap.
Scoped Phase C.5 as an evidence loop that extends compare_simulator_outputs.py so it logs calibration inputs and raw/scaled means for Stage A, reconstruction, and simulate_forward_once under the 2025-12-09T210000Z artifacts directory.
Handed Ralph a refreshed input.md with the probe run + DB-AT-028/029 commands so we capture the fresh intensity metrics and the current failure signature without touching the frozen nanobrag_torch environment.
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/ (simulator_intensity_metrics.json, pytest_db_at_028_029.log)
