### Turn Summary
Serviced problems.md ledger directive "PRIORITIZE ARCH-REFACTOR-001 ASAP" by planning Phase C.5: Stage B LBFGS inlining + HKL utilities extraction.
Phase C.4 complete (commit cd855064): Stage B requires strict `RefinementContext` inputs and owns its parameter builder (322 lines inlined); both tests PASSED.
Phase C.5 scopes: create `dbex/refinement/hkl_utils.py` (ASU/shell utilities), inline `_run_stage_b_lbfgs` and `_check_stage_b_baseline_parity` into StageB class (~347 lines total), update all imports (StageB, nanobrag_refinement, tests), validate via guard + shell smokes.
Next: Ralph implements C.5 (7 concrete tasks in input.md), then C.6 deletes stage_b_impl.py, then C.7-C.9 repeat for Stage A.
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T184846Z/ (planning_notes.md, this summary)
