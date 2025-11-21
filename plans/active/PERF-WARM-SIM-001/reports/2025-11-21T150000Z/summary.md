### Turn Summary
Documented that Stage B telemetry never writes when the REFINE-008 gate fires and logged the PERF-WARM-SIM-001 attempt in docs/fix_plan.md.
Rewrote input.md so Ralph moves `_record_stage_telemetry` ahead of the strict asserts, reruns the Stage B smokes (small passing, full failing but emitting telemetry), and regenerates stage_b_roi_summary.json under 2025-11-21T150000Z/.
Next: implement the telemetry ordering fix, capture both telemetry files, and analyze the canonical chi-squared traces for the shell_0 clamp root cause.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/
