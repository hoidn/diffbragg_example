### Turn Summary
Implemented panel-mode validation flag for Stage A baseline/final/periodic evaluations so Stage A telemetry reports panel-level chi² matching Stage C's initial state (REFINE-007).
Added config fields stage_a_force_panel_validation and stage_a_panel_validation_roi_threshold (auto-enables when enable_stage_c or ROI count ≤32); plumbed through StageA.run() and compute_loss to skip ROI branch during validations while keeping ROI-mode closures for performance.
Test confirms Stage C telemetry gates now pass (chi² continuity within 5%), but reveals pre-existing Stage A zero-improvement blocker on small detector with 15% ROI sampling; requires supervisor decision on ROI mode strategy for small detectors.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T103325Z/ (pytest_stage_c_small_fix_v2.log, collect_stage_c_small_fix.log)
