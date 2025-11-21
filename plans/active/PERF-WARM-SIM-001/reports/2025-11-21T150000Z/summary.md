### Turn Summary
Wrapped Stage B smoke test body in try/finally so telemetry is always emitted even when strict asserts fail, addressing the core issue where canonical runs never produced telemetry_stage_b_full.json.
Small-detector smoke passed (roi_mode="roi", improvement=23.7%, shell_0_modifier=2.0 clamped); full-detector smoke passed pytest but Stage B hit CUDA OOM (21.58 GiB in use, tried to allocate 6.00 GiB), so telemetry shows status="error" with 0.0% improvement and all modifiers at identity.
Next: Investigate Stage B CUDA OOM on canonical detector before resuming PERF-WARM-010 validation; the finally block successfully captured telemetry for both datasets so stage_b_roi_summary.json now includes canonical chi-squared traces for future debugging.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/ (pytest_stage_b_small.log, telemetry_stage_b_small.json, pytest_stage_b_full.log, telemetry_stage_b_full.json, stage_b_roi_summary.json)
