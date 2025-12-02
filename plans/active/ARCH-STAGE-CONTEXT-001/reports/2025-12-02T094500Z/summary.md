### Turn Summary
Verified Stage B/C telemetry dataclasses landed (StageBTelemetryState/StageCTelemetryState) and updated the plan/fix plan with new smoketest logs.
Scoped Phase B.4 so the writer/engine consume StageArtifacts directly instead of rehydrating telemetry shims, keeping REFINE-FLOW-001 metrics intact.
Next: implement the new writer signature + engine plumbing and rerun Stage B/C smoketests plus the CLI diagnostics metadata test.
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T094500Z/ (pytest_stage_b_shell.log, pytest_stage_c_small.log, pytest_stage_c_full.log, pytest_stage_b_per_reflection.log)
