### Turn Summary
Implemented unified simulator factory `create_unified_simulator` in dbex/refinement/helpers.py with shape/dtype/device validation, mask normalization, and post-run sqrt_scale computation per SCALE-004.
Factory accepts DetectorConfig, CrystalConfig, BeamConfig, HKL tensors, and returns (simulator, mask, sqrt_scale, metadata) tuple eliminating duplication across 5+ wiring locations.
Compilation check PASSED, DB-AT-024 regression guard PASSED (zero-iteration forward model unchanged, no production path modifications).
Next: Phase B2 wiring (refactor simulate_forward_once + simulate_forward_torch to use factory, validate mapping parity with factory integration).
Artifacts: plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T210000Z/ (phase_b1_factory_implementation.md, pytest_db_at_024.log, phase_b1_decision.md)
