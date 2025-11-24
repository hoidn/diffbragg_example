### Turn Summary
Implemented calibration metadata threading through Stage A final Bragg reconstruction (_build_final_bragg_from_stage_a_telemetry) to forward beam flux/exposure/beamsize_mm/N_cells and log_scale_baseline into configs and telemetry.
DB-AT-027 still fails with large forward-model differences (mean_abs_diff=57.07 vs tolerance 1e-3) despite perfect chi² agreement; likely missing spot_scale_override application in Stage A simulators (direct instantiation vs create_unified_simulator factory in mapping path).
Next: add debug instrumentation comparing simulator.run() outputs before/after scaling in both paths, verify create_unified_simulator usage, check if spot_scale_override scaling needs to be applied in _build_stage_a_context.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T225908Z/ (db_at_027/db_at_027_metrics.json, pytest_db_at_027.log)
