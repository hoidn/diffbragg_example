### Turn Summary
Migrated test_stage_a_smoke_parity.py fixture from run_nanobrag_refinement facade to direct RefinementEngine usage; both DB-AT tests now run but fail on pre-existing physics regression (chi²/pixel and ROI correlation out of bounds).
Fixed two critical pre-existing bugs blocking test execution: (1) added missing config_factories import in nanobrag_bridge.py (ARCH-BRIDGE-RESP-001 Phase C.6 regression), (2) corrected test fixture's invalid build_final_bragg_from_stage_a_telemetry calls (param_state parameter never existed).
Next: Debug physics regression (suspected issue with mapping_context.bragg_zero_iter vs actual initial-state Bragg) OR proceed to D.3 Batch 3 (stage_a_adam.py migration) if regression is tolerated.
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z/ (pytest_parity_batch2.log, import_verification.txt, migration_status.txt, artifacts_028/, artifacts_029/)
