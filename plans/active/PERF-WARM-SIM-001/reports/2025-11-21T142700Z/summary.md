### Turn Summary
Traced the canonical Stage B failure to ROI-mode full validations that never touch the full detector and documented the fix-plan updates plus new finding PERF-WARM-009.
Captured evidence from plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/{pytest_stage_b_full.log,stage_b_roi_summary.json} showing shell_0_modifier pegged at 2.0 and wrote a ready-for-implementation Do Now forcing panel-scope validations while keeping ROI closures.
Next: add the panel-validation path in `dbex/nanobrag_refinement.py`, rerun the Stage B small/full smokes with telemetry, and refresh docs/findings once the ±1% gate passes.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/ (input.md)
