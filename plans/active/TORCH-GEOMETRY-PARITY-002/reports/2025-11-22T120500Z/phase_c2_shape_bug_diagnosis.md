# Phase C2 B_ideal_reciprocal Shape Bug Diagnosis

## Summary

Ralph's Phase C2 execution (2025-11-22T114945Z) failed with `RuntimeError: size mismatch, got input (3), mat (3x3), vec (9)` when attempting to compute `A_star_new = U_matrix @ components.B_ideal_reciprocal` at line 434 of `stage_a_mapping_adam_debug.py`.

## Root Cause

In `_build_stage_a_components` (line 323-326):

```python
B_ideal = np.array(
    cctbx_cell(cell_params).fractionalization_matrix(), dtype=np.float64
).T  # cctbx gives row-major, we need column-major
B_ideal_reciprocal = torch.tensor(B_ideal, device=device, dtype=dtype)
```

**Bug:** `cctbx_cell(...).fractionalization_matrix()` returns a **9-element flat array** (row-major), NOT a 3×3 matrix. The `.T` transpose operation does nothing because the array is already 1-dimensional (shape `(9,)`).

**Evidence (diagnostic run):**
```
B_ideal shape: (9,)
B_ideal:
 [ 1.73064276e-02  9.99187064e-03 -2.66652841e-18  0.00000000e+00
  1.99837413e-02 -3.21363070e-18  0.00000000e+00  0.00000000e+00
  6.66564460e-03]
```

When this flat (9,) tensor is stored in `components.B_ideal_reciprocal` and later used in the matmul `U_matrix @ components.B_ideal_reciprocal` (line 434), PyTorch sees:
- `U_matrix`: shape (3, 3)
- `components.B_ideal_reciprocal`: shape (9,)

PyTorch matmul tries to interpret the (9,) vector as a batch of 3 vectors of size 3 each, causing the "size mismatch" error.

## Fix

Reshape the flat array to (3, 3) **before** transposing:

```python
B_ideal = np.array(
    cctbx_cell(cell_params).fractionalization_matrix(), dtype=np.float64
).reshape(3, 3).T  # Reshape THEN transpose
```

This ensures `B_ideal` is a proper 3×3 matrix in column-major form (matching the transpose from row-major cctbx convention to column-major PyTorch convention).

## Validation

After fix, `B_ideal` shape should be `(3, 3)`:
```python
B_ideal shape: (3, 3)
B_ideal:
 [[ 1.73064276e-02  0.00000000e+00  0.00000000e+00]
  [ 9.99187064e-03  1.99837413e-02  0.00000000e+00]
  [-2.66652841e-18 -3.21363070e-18  6.66564460e-03]]
```

Then `B_ideal_reciprocal = torch.tensor(B_ideal, ...)` will preserve the (3, 3) shape, and `U_matrix @ B_ideal_reciprocal` will correctly compute the 3×3 matrix product.

## Impact

This is a **blocking bug** for Phase C2/C3 convergence tests. Ralph could not execute the A_scale_only/D_full Adam optimization because the forward pass crashed on the first step.

Ralph **did** successfully run a zero-point check (Phase 0) with U-matrix mode, producing `zero_point_check.json` showing:
- `corr_median_vs_mapping`: 0.9999999843 (perfect)
- `chi2_rel_diff`: -0.017% (within tolerance)
- `zero_point_ok`: true

This confirms the U-matrix parameterization logic is correct when initialized at zero deltas; the bug only manifests when `q_params` is perturbed during optimization and `B_ideal_reciprocal` is accessed for A* reconstruction.

## Remediation

1. Apply the reshape fix to line 323-325 in `stage_a_mapping_adam_debug.py`
2. Re-run Phase C2/C3 convergence test per input.md:46-55
3. Verify `block_dof_results_u_matrix.json` is written successfully
4. Proceed with decision synthesis per input.md:63-92

## References

- Error log: `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T114945Z/stage_a_debug_u_matrix.log:28`
- Zero-point validation: `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T114945Z/zero_point_check.json`
- Code location: `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:323-326`
- Spec reference: `docs/spec-db-core.md` §Geometry Mapping (B-matrix conventions)
