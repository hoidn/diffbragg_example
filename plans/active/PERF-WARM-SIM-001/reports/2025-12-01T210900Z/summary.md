### Turn Summary
Diagnosed the repeat +0.067% Stage C chi² regression as Stage C clamping `log_scale` without Stage A’s calibrated baseline, so Stage C starts above Stage A even before detector offsets move.
Recorded evidence from telemetry_stage_c_full.json and the Stage A/Stage C code paths (dbex/refinement/stage_a_impl.py:1280-1296, stage_c.py + stage_c_impl) and logged REFINE-015 plus an updated fix_plan entry spelling out the baseline wiring work.
Rebuilt input.md/How-To Map with the new StageC.run/stage_c_impl changes and the small/full smoketest + summarizer commands under plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/.
Next: implement the baseline-aware clamp, rerun the Stage C smoketests (small/full), and archive telemetry + warm-cache summary to prove REFINE-007 is satisfied again.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/
