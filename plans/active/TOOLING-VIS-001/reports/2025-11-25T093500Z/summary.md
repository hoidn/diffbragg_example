### Turn Summary
Implemented dataset metrics comparison probe to quantify HKL/calibration effect on mapping forward; both metadata+scaled and metadata+refined produce identical negative ROI CC (-0.0399), confirming HKL swap alone does not fix structural mismatch.
Pathological spot_scale_override~3e+17 (factor 1e15 larger than typical O(1e2)) persists across both cases, pointing to deeper calibration bug in build_mapping_stage_a_context or upstream factory.
Next: audit build_mapping_stage_a_context (dbex/vis/mapping.py:95-239) and simulate_forward_once for spot_scale_override derivation, unit conversions, and flux*exposure product construction.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T093500Z/ (mapping_dataset_metrics.json, probe.log, db_at_028/, db_at_029/, pytest logs)
