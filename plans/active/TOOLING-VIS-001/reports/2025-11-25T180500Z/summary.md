### Turn Summary
Implemented canonical geometry + sigma_map alignment in the mapping dataset comparison probe; both cases now use refGeom_small.expt (not swapping to idx-0000_sigma_metadata.expt) and pass sigma_map through DataLoad args.
DB-AT-028/029 selectors ran with canonical metadata env and captured full telemetry (chi²=2.1e5/pixel, ROI CC=-0.051) confirming the known calibration gap; artifacts archived under 2025-11-25T180500Z.
Next: supervisor should review the captured metrics to determine if the chi²/ROI failures indicate a deeper implementation defect requiring callchain analysis or if relaxing acceptance gates is appropriate.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T180500Z/ (mapping_dataset_metrics.json, pytest_db_at_028_029.log, db_at_028/029 metrics)
