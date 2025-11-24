### Turn Summary
Investigated DB-AT-027 zero-point parity failure where Stage A engine delegation path was not applying `spot_scale_override` calibration correctly, causing Bragg frame mismatch (mean diff 57 ADU, max diff 13M).
Traced the flow: `calibration_metadata` with `spot_scale_override=3.18e17` flows correctly to `_build_stage_a_context` and telemetry writes `log_scale_baseline=log(sqrt(spot_scale))≈20.15`, but `_build_final_bragg_from_stage_a_telemetry` was defaulting to 0.0 when extracting from telemetry.
Implemented fix to compute `log_scale_baseline` from `config.calibration_metadata` directly in final Bragg reconstruction, but this caused regression (error increased to 3.2e10) suggesting double-scaling; root cause requires deeper investigation into whether simulators produce scaled vs unscaled Bragg and how closure applies scale in zero-iteration runs.
Next: revert debug changes, analyze simulator output characteristics, and determine correct scale application point in zero-iteration engine delegation path.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T231449Z/ (pytest_db_at_027_baseline.log, pytest_db_at_027.log, db_at_027/)
