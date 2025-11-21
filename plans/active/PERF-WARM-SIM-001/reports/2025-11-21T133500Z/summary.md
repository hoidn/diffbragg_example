### Turn Summary
Tightened Stage B/C perf telemetry so the warm cache path fails fast whenever perf counters drift and logged the canonical full-detector smokes.
Replayed the warm-vs-cold benchmark to record the 14.77s vs 169.12s delta and documented metrics/fixes in findings plus the fix plan.
Next: chase Stage B ROI-aware sampling so shell modifiers can operate on ROIs without regressing the perf invariants.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133500Z/ (pytest_stage_bc_full.log, benchmark_summary.json)

### Turn Summary
Directed Ralph to harden Stage B/C perf telemetry by adding perf-counter asserts in the smoke tests so the warm cache contract fails fast when Stage A context stops flowing through.
Captured the command plan for rerunning the Stage B/C smokes with `DBEX_SMOKE_DETECTOR_SIZE=full` and for rerunning the warm-vs-cold benchmark so we can publish the canonical ROI vs panel deltas in findings/fix_plan.
Next: implement the test edits, run the canonical smokes plus the benchmark, and land the resulting telemetry/log updates in docs/findings.md and docs/fix_plan.md.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133500Z/ (input.md, summary.md)
