### Turn Summary
Traced the bogus scale-chain telemetry to the plan-local probe zeroing `calibration_config_path`, so calibrated permutations never loaded the smoke config and stayed at spot_scale_override=1.0.
Recorded the finding in docs/fix_plan.md, updated galph_memory, and issued a ready-for-implementation Do Now for Ralph to patch the probe and rerun DB-AT-028/029 with canonical metadata envs.
Next: implement the probe fix and capture corrected metrics (raw vs calibrated cases) so we can resume the Stage A physics investigation with trustworthy evidence.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T114730Z/ (input.md, summary.md)
