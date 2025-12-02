### Turn Summary
Inlined 3 Stage-A-private helpers (_sync_stage_a_crystal, _build_stage_a_params, _run_stage_a_lbfgs) into StageA class, reducing stage_a_impl to 1 export.
Updated imports to fix StageAContext/StageATelemetryState sourcing; all 4 validation selectors (Stage A expansion/telemetry, Stage B guard/shell) passed without behavioral regression.
Next: Phase C.9 — migrate _compute_variance_weighted_loss to stage_a_utils.py and delete stage_a_impl.py entirely.
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-04T215000Z/ (pytest_stage_a_expansion.log, pytest_stage_a_telemetry.log, pytest_stage_b_guard.log, pytest_stage_b_shell.log)
