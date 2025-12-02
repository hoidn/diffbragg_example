### Turn Summary
Stage B LBFGS closure now has the missing nonlocal guards and quiet telemetry so canonical runs capture best snapshots without UnboundLocalError noise.
run_nanobrag_refinement, the Stage C smoke, and the Stage C probe all pass the baseline detector to seed distance offsets and emit true initial/final telemetry; the helper now backfills distances via tanh⁻¹ when a baseline exists.
Strict Stage C and Stage B smokes on the full detector pass again, with telemetry showing detector_offset_reduction_min≈1.0, detector_offset_final_abs_max≈1.5e-8 mm, and shell modifiers still within ±1 %.
Next: feed the refreshed telemetry/metrics into PHYSICS-LOSS-001 and resume the variance-weighted loss gating using these canonical smokes as the guardrail.
Artifacts: plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/ (collect_stage_c_full.log, collect_stage_b_full.log, pytest_stage_c_full.log, pytest_stage_b_full.log, telemetry_full.json)

### Turn Summary
Documented the Stage B UnboundLocalError and bogus Stage C telemetry by replaying the canonical smoke logs and pegging REFINE-SMOKE-CANONICAL as the new block on PHYSICS-LOSS-001.
Refreshed docs/fix_plan.md and input.md so Ralph can add the missing `nonlocal` guards, plumb `baseline_detector`, and rerun the strict Stage B/C selectors with telemetry capture.
Next: implement the Stage B closure + Stage C telemetry fixes, then replay the full-detector smokes to produce clean logs + JSON evidence.
Artifacts: plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/ (input.md, summary.md)
