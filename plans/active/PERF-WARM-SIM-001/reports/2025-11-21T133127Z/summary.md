### Turn Summary
Implemented ROI-mode toggle for canonical Stage B smokes so full-detector runs disable Stage A ROI sampling and restore ±1% REFINE-008 shell-modifier gates while small-detector runs continue using ROI mode.
Both test variants now pass: small shows roi_mode="roi" with 23.7% improvement (shell_0 at clamp), canonical shows roi_mode="panel" with 0% improvement and all modifiers at identity.
Fixed telemetry reporting bug where roi_count_total was set to n_panels=1 instead of canonical ROI count (92) when in panel mode.
Next: initiative exit criteria satisfied; canonical gates restored and telemetry captures ROI vs panel execution correctly.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/ (pytest_stage_b_small.log, pytest_stage_b_full.log, telemetry_stage_b_small.json, telemetry_stage_b_full.json, stage_b_roi_summary.json)
