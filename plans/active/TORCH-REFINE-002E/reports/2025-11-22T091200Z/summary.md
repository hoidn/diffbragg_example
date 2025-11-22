### Turn Summary
Implemented Phase A2 baseline B_ideal variants to test whether recovering cell params from mapping's MOSFLM A* eliminates the 1e-3 symmetric strain observed in Phase A0.
Added recover_cell_from_a_star helper using cctbx.uctbx, extended derive_robust_misset with b_ideal_override parameter, and extended the probe to compare PathB_unitcell vs PathB_recovered variants; both show identical log_u_symmetric_norm=1.369e-3, ruling out H2 (baseline cell mismatch) as the root cause.
Next: pivot to Phase B (gradient/optimizer diagnosis) or Phase A3 (mapping forward vs Stage-A config comparison on single panel/HKL subset) to determine whether the strain gap blocks refinement or can be worked around via optimizer tuning.
Artifacts: plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/ (crystal_matrix_parity.json with path_B_unitcell, path_B_recovered, recovered_cell_params, dxtbx_cell_params fields)
