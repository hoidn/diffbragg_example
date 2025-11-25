### Turn Summary
Implemented refined HKL persistence in capture_smoke_calibration.py and wired Stage A fixtures to default to the refined MTZ when calibration config exists.
The key issue was that MTZ column labels differed between refined (F columns) and raw (I columns) files, plus telemetry extraction needed to handle nested hkl_telemetry diagnostics.
Next: re-evaluate ROI diagnostics/DB-AT tolerances now that refined HKL ingestion is working.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T160500Z/ (smoke_calibration_manifest.json, mapping_cpu_gpu_refined/mapping_forward_cpu_gpu.json, db_at_028/mapping_context_fixture.json, db_at_029/mapping_context_fixture.json)
