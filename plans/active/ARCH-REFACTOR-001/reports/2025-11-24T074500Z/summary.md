### Turn Summary
Extracted derive_u_matrix_from_mosflm_a_star and _compute_variance_weighted_loss to new leaf-node modules dbex.geometry.crystallography and dbex.physics.loss.
All validation passed: 6 Phase 0 tests (geometry + physics) and 2 regression guards (Stage A smoke + DB-AT-024 mapping) confirmed no behavioral changes from pure code movement.
Phase A complete; next action is Phase B planning (telemetry standardization with RefinementTelemetry to_dict and HDF5 serialization).
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/ (pytest_geometry_new.log, pytest_physics_new.log, regression_stage_a.log, regression_db_at_024.log, phase_a_decision.md, mapping_metrics.json)
