### Turn Summary
Implemented Stage B ROI mode that iterates `StageAContext.roi_entries` when warm cache + ROI mode are active, eliminating per-iteration whole-panel simulation overhead; mirrors Stage A sampling strategy.
Small-detector smoke PASSED with roi_mode="roi" and Stage B improvement 23.7%; full-detector smoke fails assertion (expects panel mode) because config.enable_stage_a_roi_mode defaults to True for both detector sizes.
Next: Adjust test config to set enable_stage_a_roi_mode=False for canonical full-detector runs, or realign test expectations to accept ROI mode when panel_slices>0.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T121804Z/ (pytest_stage_b_small.log, telemetry_stage_b_small.json)
