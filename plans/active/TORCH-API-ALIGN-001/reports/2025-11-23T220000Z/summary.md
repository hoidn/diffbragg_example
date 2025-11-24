### Turn Summary
Completed Phase B2a planning for factory wiring to forward helpers (simulate_forward_once + simulate_forward_torch).
Analysis confirmed ~71 lines net reduction via factory integration, eliminating duplicated mask normalization, HKL attachment, and simulator instantiation across panel loops.
Authored comprehensive input.md with 9-step wiring protocol (factory calls replace lines 2056-2083, 2332-2356), 3 test validations (DB-AT-024 regression guard + Phase A2 factory tests), and 4-path decision tree.
Next: Ralph executes Phase B2a wiring; on PASS, proceed to Phase B2b (refine_one CLI + nanobrag_refinement panel loops wiring).
Artifacts: plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T220000Z/ (summary.md, input.md)
