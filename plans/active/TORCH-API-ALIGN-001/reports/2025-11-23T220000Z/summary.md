### Turn Summary
Wired simulate_forward_once + simulate_forward_torch to use create_unified_simulator factory, eliminating 56 lines of duplicated simulator instantiation logic across panel loops.
Factory integration centralizes mask normalization, HKL attachment, and sqrt_scale computation; both helpers now call factory and apply post-run scaling consistently.
DB-AT-024 regression guard PASSED (mapping parity unchanged), Phase A2 factory tests had xfail markers removed successfully (stub tests remain intentionally skipped).
Next: Phase B2b wiring (refine_one CLI path + nanobrag_refinement panel loops to factory, validate smoke tests).
Artifacts: plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T220000Z/ (phase_b2a_decision.md, pytest_db_at_024.log, pytest_factory_tests.log)
