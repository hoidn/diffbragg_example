### Turn Summary
Implemented scale-chain probe capturing apples-to-apples HKL/calibration permutations (scaled_raw, scaled_calibrated, refined_calibrated) to isolate where metadata smoke mapping collapses.
Critical finding: calibration config NOT loading (all three cases identical with spot_scale_override=1.0), confirming build_mapping_stage_a_context bug in dataload.args.calibration_config_path plumbing.
Next: debug dbex/vis/mapping.py calibration loader (lines 179-189) to find why load_calibration_metadata silently fails and rerun probe once fixed.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T170500Z/ (scale_chain_probe/scale_chain_metrics.json, db_at_028/, db_at_029/, pytest logs)
