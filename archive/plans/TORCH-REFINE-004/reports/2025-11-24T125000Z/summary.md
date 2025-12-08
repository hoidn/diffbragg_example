### Turn Summary
Completed Phase 6 planning analysis for per-reflection ASU mapping using cctbx.miller symmetry operations; parameter count estimates range 2K (P432) to 35K (P1 test fixture) with LBFGS < 10K gate and Adam ≥ 10K recommendation per spec-db-workflow.md:107.
ASU index computation pseudocode designed with halo voxel handling (map to index 0 fixed modifier=1.0) and cctbx unavailable fallback to shell mode per spec:60.
cctbx.miller API confirmed available (tested 2025-11-24T125000Z), P21 synthetic test validated symmetry folding, test fixture P1 ~35K parameters require Adam optimizer.
Next: Phase 6 implementation (extend compute_hkl_asu_map helper, add asu_modifiers parameter, dynamic optimizer selection LBFGS vs Adam).
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/ (phase_6_planning_analysis.md, asu_pseudocode.py, parameter_count_analysis.md, optimizer_decision.md, decision.json)
