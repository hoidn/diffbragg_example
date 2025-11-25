### Turn Summary
N_cells suppression restored positive ROI correlations but left Stage A ~1.5×10^5 off-scale (see plans/active/TOOLING-VIS-001/reports/2025-11-25T230500Z/mapping_dataset_metrics/mapping_dataset_metrics.json), so we planned to auto-adjust spot_scale when `apply_calibration_n_cells=False`.
We will update dbex/vis/mapping.py::build_mapping_stage_a_context to detect huge `target_bragg_mean_ratio`, re-run simulate_forward_once with `spot_scale_override *= (target/bragg)^2`, and surface the adjustment in diagnostics so downstream probes/tests can verify the correction.
Next: implement the scale-adjustment hook, rerun the dataset probe, and capture DB-AT-028/029 logs under the new report directory.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/ (input.md)
