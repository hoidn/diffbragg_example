### Turn Summary
Implemented Stage A panel validation toggle so Stage B enablement forces panel-mode baseline/final validations, ensuring REFINE-FLOW-001 parity (Stage B initial chi² matches Stage A final within 0.1%) holds for ROI-heavy configs.
Resolved the core issue by adding `config.enable_stage_b` to the `force_panel_validation` condition in stage_a.py and updating test_stage_b_shell_modifiers to set `stage_a_panel_validation_roi_threshold=0`, proving the toggle works independently of ROI count thresholds.
Next: Phase E.2 complete; REFINE-FLOW-001 parity now guaranteed for Stage B enablement; ready to proceed with remaining ARCH-REFINE-001 phases or pivot to supervisor-prioritized focus.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T160850Z/ (collect_stage_bc_small.log, pytest_stage_bc_small.log, telemetry_stage_bc_small.json)
