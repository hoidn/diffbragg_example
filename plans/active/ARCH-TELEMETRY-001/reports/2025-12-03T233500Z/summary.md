### Turn Summary
Captured the Stage C telemetry gaps (missing sample traces and variance-floor counters) and recorded the helper/wiring plan in docs/fix_plan.md plus the ARCH-TELEMETRY-001 implementation checklist.
Reserved plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T233500Z/ for the next loop and rewrote input.md so Ralph adds the Stage C collector helper, seeds a baseline sample when LBFGS never runs, and pipes the variance-floor stats into RefinementTelemetry before rerunning the parity smoketests.
Next: implement the collector helper + `_run_stage_c_lbfgs` wiring and run the Stage B guard, Stage B shell, and Stage C small-detector smokes to unblock REFINE-007/PHYSICS-LOSS-001.
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T233500Z/
