### Turn Summary
Implemented sigma-source aware cases in the mapping dataset probe to toggle between metadata sigma tiles and CLI default_sigma override; all 4 cases executed successfully with ROI artifacts emitted.
Critical finding: metadata and CLI cases produce identical ROI correlations (raw=0.047, calibrated=-0.044), ruling out sigma tiles as the root cause of anti-correlation.
Next: investigate HKL/calibration alignment (verify refined_structure_factors.mtz + config_torch_smoke.json are synchronized) or explore whether spot_scale_override=3.1e17 is inverting structure.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T200500Z/ (mapping_dataset_metrics/mapping_dataset_metrics.json with 4 cases, db_at_028/, db_at_029/, pytest logs)
