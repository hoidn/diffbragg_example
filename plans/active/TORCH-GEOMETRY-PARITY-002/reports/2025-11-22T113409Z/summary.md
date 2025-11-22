### Turn Summary
Implemented Phase C1 U-matrix parity probe extension with `--use-u-matrix` flag; raw U-matrix achieves perfect parity (3.5e-18) validating `A*=U@B_ideal` identity.
Critical blocker discovered: `det(U₀)=1.000557` means U is not in SO(3); quaternion parameterization enforces SO(3) projection (scipy Rotation.from_matrix), losing 0.06% volume offset and breaking parity during optimization.
Next: BLOCK C2/C3 per decision tree; escalate to TORCH-GEOMETRY-PARITY-003 to investigate det(U)≠1 root cause (dxtbx A*/cell inconsistency? physical volume scaling?) and evaluate hybrid parameterizations or accept ~4e-05 parity threshold.
Artifacts: plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/ (crystal_matrix_parity.json, phase_c1_parity_failure_diagnosis.md, probe_u_matrix_v4.log)
