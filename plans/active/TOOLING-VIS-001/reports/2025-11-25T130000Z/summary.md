### Turn Summary
Implemented extended mapping diagnostics to capture masked/unmasked target/Bragg means, scale ratios, and global_scale_hint, enabling calibration mismatch diagnosis.
Probe revealed 3.2× global_scale_hint divergence between metadata_scaled and metadata_refined cases, with large masked vs unmasked gaps suggesting calibration metadata drives ROI anti-correlation.
Pytest DB-AT-028/029 both failed as expected with artifacts fully captured; fixture diagnostics show calibration_path=null and spot_scale_override=1.0, confirming smoke tests lack calibration metadata.
Next: investigate calibration env var plumbing to fixtures and patch if needed.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T130000Z/ (mapping_dataset_metrics.json, db_at_028/, db_at_029/, pytest logs)
