### Turn Summary
Set up the next ARCH-TELEMETRY-001 loop to move Stage A off raw telemetry_state mutation and fully onto StageATelemetryCollector callbacks.
Captured the precise `_build_lbfgs_closure`, `_run_stage_a_lbfgs`, and StageA.run deltas so chi²/masked-MSE/variance stats flow through the observer while the RefinementTelemetry payload stays byte-identical.
Documented the Stage A engine telemetry selector plus the small-detector smoketest with artifact paths so Ralph can prove the collector wiring keeps `/torch_diagnostics` stable.
Next: implement the collector wiring and rerun those selectors to confirm no telemetry diffs remain.
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-02T201500Z/
