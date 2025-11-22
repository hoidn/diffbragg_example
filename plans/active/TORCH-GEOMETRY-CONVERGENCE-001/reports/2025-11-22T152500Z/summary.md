### Turn Summary
Reviewed Ralph's Phase A forward model diagnostic confirming decisive root cause: B_ideal computation mismatch between TorchCrystal (in derive_u_matrix_from_mosflm_a_star) and cctbx (in script), causing U @ B_ideal reconstruction to fail at initialization (chi²=1.425B vs expected ~990k).
Authored comprehensive bugfix Do Now: refactor derive_u_matrix_from_mosflm_a_star to return both U and B_ideal from same TorchCrystal computation, update 2 call sites (stage_a_mapping_adam_debug.py + dbex/nanobrag_refinement.py), delete cctbx code to prevent future mismatch.
Next: Ralph implements bugfix, runs regression guard + Phase A2 validation rerun, synthesizes decision on whether initialization now correct (chi² step_0 ≈ 990k) and whether convergence succeeds or still fails.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/ (input.md with 10-step implementation protocol, decision tree templates)
