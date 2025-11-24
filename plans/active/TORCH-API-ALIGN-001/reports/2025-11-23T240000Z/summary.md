### Turn Summary
Wired refine_one CLI forward simulation panel loop to use create_unified_simulator factory, eliminating 23 lines of duplicated simulator instantiation logic.
Factory integration centralizes model instantiation, HKL attachment, and sqrt_scale computation while preserving config creation for downstream Stage A refinement.
DB-AT-024 regression guard PASSED (mapping parity unchanged), Stage A expansion smoke test PASSED (refine_one CLI unaffected).
Next: Phase B2b(ii) wiring (nanobrag_refinement Stage B/C panel loops to factory, validate Stage B/C smokes).
Artifacts: plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T240000Z/ (phase_b2b_i_decision.md, pytest_db_at_024.log, pytest_stage_a_expansion.log)
