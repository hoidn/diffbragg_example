### Turn Summary
Re-confirmed Stage C warm-cache evidence gaps: tests/dbex/test_torch_refine_smoke.py:583-854 asserts the perf counters but never logs them, and no telemetry_stage_c_*.json exist under plans/active/PERF-WARM-SIM-001/reports/.
Updated docs/fix_plan.md + input.md with a ready-for-implementation handoff covering the Stage C log print, new summarize_stage_c_roi.py (mirroring summarize_stage_b_roi.py:1), the small/full telemetry reruns rooted at 2025-11-21T172334Z, and the docs/TESTING_GUIDE.md refresh.
Next: Ralph implements the logging + summarizer, runs both Stage C selectors with telemetry capture, generates stage_c_roi_summary.json, and syncs the docs/fix_plan entries with the new evidence.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T172334Z/ (summary.md)
