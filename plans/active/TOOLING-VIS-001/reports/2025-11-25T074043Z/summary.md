### Turn Summary
Implemented calibration_path persistence across mapping and Stage A diagnostic surfaces to enable audit trails for calibration configs.
Resolved missing calibration metadata tracking by extending emit_mapping_context_diagnostics, DB-AT-028/029 test metrics, and CPU/GPU probe scripts with calibration_path field extraction and persistence.
Next: implement Phase D.D zero-point probe to isolate calibration payload construction bugs causing chi²/pixel and ROI correlation failures.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T074043Z/ (smoke_calibration_manifest.json, mapping_cpu_gpu/mapping_forward_cpu_gpu.json, db_at_028/db_at_028_metrics.json, db_at_029/db_at_029_metrics.json)
