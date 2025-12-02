### Turn Summary
Scoped Phase D.2 CLI refactor: migrate refine_one.py from run_nanobrag_refinement facade to direct RefinementEngine instantiation using the 5-step pattern (import updates → build RefinementContext → instantiate stages → run engine → extract artifacts).
Serviced problems.md ledger directive "PRIORITIZE ARCH-REFACTOR-001 ASAP" with comprehensive planning notes documenting implementation strategy, validation plan (2 CLI selectors), and risks/mitigations per CLI blueprint reference.
Next: Ralph implements Phase D.2 via explicit line-by-line Do Now (refactor lines 505-595, validate with test_torch_diagnostics_metadata + test_nanobrag_backend_runs_simulator).
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220000Z/ (planning_notes.md, summary.md)
