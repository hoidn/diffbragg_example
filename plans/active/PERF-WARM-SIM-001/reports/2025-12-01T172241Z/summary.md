### Turn Summary
Inspected Stage C ROI/panel plumbing plus the smoketest and verified canonical runs now evaluate every closure in panel mode, so the recurring +0.067% chi² regression is not coming from a stray ROI path.
Traced the lack of evidence to `_record_stage_telemetry` running after the REFINE-007 assert, which means the failing full-detector run never emits telemetry JSON and we cannot justify any gate change.
Next loop will move the telemetry write ahead of the strict gate, rerun both detector sizes with the new logging, and feed the outputs through `summarize_stage_c_warm_cache.py` under the precreated 2025-12-01T173200Z report dir.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T172241Z/ (stage_c_panel_inspection.md)
