### Turn Summary
Focused on PERF-WARM-SIM-001 by tracing the Stage B ROI telemetry gap and updating the ledger/input so shell modifier deltas land in the smoke-test logs again.
Confirmed `_record_stage_telemetry` drops `telemetry.param_deltas` even though `dbex/nanobrag_refinement.py` populates them, and handed Ralph a Do Now to patch the writer, fix the ROI summary script, and rerun the small + full Stage B smokes with telemetry capture.
Next: implement the telemetry/logging updates, replay Stage B smokes, run the summary script, and refresh docs/findings + fix_plan with the new stage_b_roi_summary.json evidence.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/
