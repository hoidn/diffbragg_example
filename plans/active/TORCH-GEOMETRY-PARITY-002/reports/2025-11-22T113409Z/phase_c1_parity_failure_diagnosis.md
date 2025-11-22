# Phase C1 Parity Failure Diagnosis

## Summary

U-matrix parameterization achieves **perfect parity** (`max_abs_diff=3.469e-18`) when using the **raw U-matrix** without SO(3) projection. However, this U-matrix has `det(U)=1.000557`, which means it **is not a proper rotation**. Any SO(3) parameterization (quaternion, axis-angle, etc.) will project this onto the rotation manifold and lose the ~0.06% volume scaling, breaking parity.

## Evidence

From `crystal_matrix_parity.json`:

```json
{
  "path_B_u_matrix": {
    "max_abs_diff": 3.469447011705022e-18,  // PASS (<1e-6)
    "log_u_symmetric_norm": 3.542577570424972e-16  // No strain (machine precision)
  },
  "u_matrix_diagnostics": {
    "u_matrix_det": 1.0005572899796854,  // NOT in SO(3)!
    "quaternion_delta_norm": 1.4687683267295405e-16
  }
}
```

Comparison with other variants:
- PathB_unitcell, PathB_recovered, PathB_mapping_aligned: all show `log_u_symmetric_norm=1.369e-03` and `max_abs_diff~4e-05`
- PathB_u_matrix (raw): `log_u_symmetric_norm=3.5e-16`, `max_abs_diff=3.5e-18` (perfect!)

## Root Cause Analysis

1. **Mapping MOSFLM A* contains non-rotation components**: The dxtbx crystal geometry embeds a ~0.06% determinant offset relative to the ideal orthonormal+scaling factorization `A* = scale · R · B_ideal`.

2. **Quaternion projection loses this component**: `matrix_to_quaternion(U₀)` calls `scipy.spatial.transform.Rotation.from_matrix(U₀)`, which internally projects U₀ onto SO(3) via SVD: `U_rotation = U @ V.T` from `U = U S V.T`. This loses the `det(U)=1.000557` offset.

3. **Raw U-matrix preserves it**: Computing `A* = U₀ @ B_ideal` directly (without quaternion roundtrip) gives perfect reconstruction because `U₀ = A* @ inv(B_ideal)` is an exact matrix inverse identity.

## Implications for Phase C2/C3

**Blocking Issue**: We cannot proceed with Phase C2/C3 convergence tests using quaternion parameterization, because:

1. **Initialization will break parity**: Even if we initialize `q₀ = matrix_to_quaternion(U₀)`, the reconstructed `U_init = quaternion_to_matrix(q₀)` will have `det(U_init)=1.0` (proper rotation), not `1.000557`.

2. **Convergence tests will start with ~4e-05 parity error**: Same as the cell+misset variants, defeating the purpose of U-matrix parameterization.

3. **LBFGS/Adam updates will maintain SO(3)**: Normalization `q_norm = q / ||q||` keeps the quaternion on the unit sphere, which maps to SO(3) only.

## Decision Tree Branch

Per `input.md:125-129` abort trigger:

> **If C1 fails (`max_abs_diff ≥ 1e-6`):**
> 1. Capture exact parity metrics ✓ (done)
> 2. Diagnose: numerical precision? B_ideal mismatch? quaternion conversion roundtrip error? ✓ (quaternion SO(3) projection)
> 3. **BLOCK** before proceeding to C2/C3 ✓
> 4. Escalation path: TORCH-GEOMETRY-PARITY-003 (numerical precision limits) if root cause is fundamental

**Action**: BLOCK TORCH-GEOMETRY-PARITY-002 Phase C2/C3. The quaternion-based U-matrix parameterization cannot achieve <1e-6 parity at zero deltas because the mapping geometry is not in SO(3).

## Alternative Paths (for Escalation to GEOMETRY-PARITY-003)

1. **GL(3) parameterization**: Allow full 9-DOF A* refinement without SO(3) constraint. Risky (overfitting, non-physical), but preserves mapping geometry exactly.

2. **Hybrid cell+U parameterization**: Factor as `A* = U @ diag(scale_a, scale_b, scale_c) @ angles_matrix`, where U ∈ SO(3) and the diagonal absorbs the det offset. Requires careful gradient flow analysis.

3. **Accept ~4e-05 parity as "good enough"**: Quaternion parameterization gives the same parity as cell+misset (~4e-05), which may be acceptable if convergence improves. Test Phase C2/C3 anyway and compare χ² trajectories.

4. **Investigate MOSFLM A* source**: The `det(U)=1.000557` offset suggests the dxtbx crystal may have embedded a small isotropic scale factor or the unit cell parameters are slightly inconsistent with the reciprocal vectors. Audit `crystal.get_A()` and `crystal.get_unit_cell()` alignment per DXTBX-001.

## Recommendation

**Escalate to TORCH-GEOMETRY-PARITY-003** with focus on:
- Understanding why `det(U₀)=1.000557` (is this physical? calibration artifact? dxtbx bug?)
- Evaluating whether ~4e-05 parity is acceptable for Stage A convergence (run Phase C2/C3 with quaternion anyway as a sensitivity test)
- Designing a parameterization that preserves the mapping zero point without enforcing pure SO(3)

## Artifacts

- `crystal_matrix_parity.json` — Full parity metrics for all variants
- `probe_u_matrix_v4.log` — Console output showing C1 PASS (raw U) but det(U)≠1

## References

- TORCH-REFINE-002E Phase A0: Identified 1.37e-3 symmetric strain in cell+misset path
- GEOMETRY-003: B_ideal-based mapping misset decomposition
- input.md:114-136: Phase C1 execution plan and decision tree
