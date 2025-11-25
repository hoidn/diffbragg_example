### Turn Summary
Scoped a metadata-vs-refined mapping comparison probe so we can quantify how HKL/calibration choices drive the Stage A ROI CC gap before touching production code.
Documented that metadata+scaled.mtz still yields ROI CC≈-0.04 while earlier refined HKL runs were ≈0.62, so the next loop will add compare_mapping_dataset_metrics.py to capture both cases via build_mapping_stage_a_context.
Updated docs/fix_plan.md, input.md, and galph_memory with the new plan; the next action is to implement the probe and rerun DB-AT-028/029 under the reserved artifacts directory.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T093500Z/
