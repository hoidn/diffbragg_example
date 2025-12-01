### Turn Summary
Diagnosed Stage C telemetry from 2025-12-01T183500Z showing detector offsets stuck at ±0.25 mm because `_apply_baseline_detector_prior()` still runs after LBFGS and the new rehydration reloads stale tensors.
Recorded the baseline-prior ordering fix in docs/fix_plan.md and input.md so Ralph can move the prior call ahead of the optimizer and rerun the Stage C smoketest pair under the 2025-12-01T190945Z artifact path.
Next: implement the `_run_stage_c_lbfgs` prior reorder and rerun the small/full detector microslip selectors plus the warm-cache summarizer.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T190945Z/
