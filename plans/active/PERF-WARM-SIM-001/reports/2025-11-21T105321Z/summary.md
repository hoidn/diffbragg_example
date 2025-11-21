### Turn Summary
Warm Stage B/C reuse Stage A detector configs/masks and expose the cache/ROI perf counters in telemetry so Stage C matches the Stage A baseline.
Stage C ROI logic now falls back to panel loops when slices are missing and restores the best chi-squared snapshot before we record telemetry, keeping loss traces monotonic.
Next: replay the full-detector smokes/benchmark once the warm cache stabilizes to publish the ROI vs panel perf delta.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T105321Z/ (pytest_stage_bc_small.log, telemetry_stage_bc_small.json)

### Turn Summary
Scoped the next PERF-WARM-SIM-001 increment so Stage B/C reuse StageAContext and emit perf counters, updating docs/fix_plan.md plus input.md with the ready-for-implementation brief.
Documented that Stage B/C still rebuild detectors per closure and mapped the fix to the canonical Stage B/C smoke selectors so Ralph can validate the warm cache.
Next: implement the Stage B/C warm-cache reuse and rerun the Stage B/C smokes while capturing telemetry/logs under the new artifact directory.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T105321Z/ (input.md, fix_plan.md)
