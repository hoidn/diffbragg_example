### Turn Summary
Reviewed Phase A3 forward model comparison confirming the 24.5% chi-squared gap is a pure geometry encoding artifact, not a simulator bug (both paths use nanobrag_torch).
Transitioned to Phase C1 Branch G to implement the minimal geometry fix: derive mapping-aligned B_ideal from MOSFLM A* matrix itself instead of dxtbx unit cell, eliminating the 1.4e-3 symmetric strain.
Next: Ralph extends `derive_robust_misset` with `use_mapping_b_ideal` flag, reruns parity probe and Phase 5 validation to confirm <1e-6 A* parity and stable Adam zero-point behavior.
Artifacts: plans/active/TORCH-REFINE-002E/reports/2025-11-22T100021Z/ (awaiting crystal_matrix_parity.json, stage_a_debug_phase5.json, pytest_stage_a_regression.log)
