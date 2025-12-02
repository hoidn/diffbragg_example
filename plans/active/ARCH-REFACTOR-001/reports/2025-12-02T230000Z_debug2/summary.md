### Turn Summary
Implemented corrective fix for ARCH-REFACTOR-001 Phase D.3 Batch 2: replaced mapping_context.bragg_zero_iter with simulate_forward_once call using perturbed geometry (refinement starting point) per Galph's Do Now.
Tests still FAIL with identical signature (chi²=2.098e+05, correlation=-0.053); metrics reveal deeper bug: bragg_after is near-zero (7.59e-14 mean) when it should contain refined Bragg from engine._artifacts["stage_a"].bragg_full.
BLOCKED per repeat-failure guard — escalated to Galph as suspected implementation bug in artifact extraction or build_final_bragg_from_stage_a_telemetry; requires investigation outside bugfix initiative scope.
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T230000Z_debug2/ (pytest_parity_batch2_corrected.log, db_at_028_metrics.json, db_at_029_metrics.json)
