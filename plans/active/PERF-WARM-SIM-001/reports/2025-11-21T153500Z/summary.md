### Turn Summary
Implemented CPU fallback for canonical Stage B smokes to eliminate CUDA OOM errors by routing panel-mode closures to CPU when stage_b_full_eval_on_cpu flag is active.
Both small-detector (ROI mode, warm cache, 23.7% improvement) and full-detector (panel mode, cold cache on CPU, 0% improvement with modifiers at identity) tests now pass.
Next: The OOM path is resolved; canonical Stage B telemetry can now be captured cleanly for future REFINE-008 analysis.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/ (pytest_stage_b_{small,full}.log, telemetry_stage_b_{small,full}.json, stage_b_roi_summary.json)
