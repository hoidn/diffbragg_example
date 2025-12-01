### Turn Summary
Captured new Stage A/C telemetry on the rebuilt refGeom_small dataset (ROI sampling still flatlines at 0.00% improvement while panel validation drops 57.4%) and added ROI/panel knobs to the probe script.
Diagnosed the blocker: ROI-mode validations only see four ROIs even at 100% sampling, so Stage C’s Stage A gate never sees progress; forcing panel validation aligns the metrics (Stage A final=1.59e8, Stage C initial=1.59e8).
Next: teach Stage A to switch baseline/final validations to panel mode whenever Stage C runs or ROI count ≤32, then rerun the Stage B/C smokes.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T103325Z/ (stage_c_stage_a_probe_cli*.{json,log}, stage_c_stage_a_probe_cli_panel.{json,log}, refGeom_small_crop_report.json)
