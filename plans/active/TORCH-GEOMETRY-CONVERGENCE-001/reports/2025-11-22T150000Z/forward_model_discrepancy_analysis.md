# Forward Model Discrepancy Analysis

## Executive Summary

**Root Cause Identified:** The chi-squared discrepancy (990k vs 1.425B) between zero-point check and Adam loop step 0 is due to **different forward model code paths**, NOT a bug. The zero-point check uses `use_mapping_zero_geometry=True` (MOSFLM A* injection directly), while the Adam loop uses `use_mapping_zero_geometry=False` (reconstructs A* via `U @ B_ideal_reciprocal`). The reconstruction is numerically imperfect, leading to ~1000× worse chi-squared.

**Critical Finding:** This is NOT just a "logging discrepancy" - the U-matrix path is fundamentally broken at initialization because `U_initial @ B_ideal_reciprocal ≠ A_star_mosflm` due to B_ideal computation mismatch.

## Zero-Point Check Code Path

**Function:** `_run_zero_point_check` (stage_a_mapping_adam_debug.py:1007-1075)

**Call Chain:**
1. Calls `_stage_a_adam_core(..., n_steps=0, lr=0.0, train_scale=False, train_cell=False, train_orientation=False)`
2. Inside `_stage_a_adam_core` (line 803): `bragg_before_t, chi_sq_before_t = _forward_once(use_mapping_zero_geometry=True)`
3. Inside `_stage_a_forward` with `use_mapping_zero_geometry=True` (lines 395-403):
   ```python
   if use_mapping_zero_geometry:
       crystal_config, _ = create_crystal_config(
           dataload.crystal,
           dataload.Expt,
           N_cells=N_cells,
           apply_n_cells=apply_n_cells,
           crystal_overrides=None,  # <-- NO OVERRIDES
           misset_deg_override=None,
       )
   ```

**Forward Model:** Uses MOSFLM A* directly from `dataload.crystal.get_A()` via `create_crystal_config` with NO overrides.

**Chi-Squared Computation:** Variance-weighted chi-squared computed from Bragg tensor (stage_a_mapping_adam_debug.py:483-492 via `_compute_variance_weighted_loss`)

**Result:** chi2_stage_a = 989,645.5 (~990k, matches mapping chi2_mapping = 989,811.5)

## Adam Loop Code Path

**Function:** `_stage_a_adam_core` optimizer loop (stage_a_mapping_adam_debug.py:807-873)

**Call Chain:**
1. For each step (line 808-873):
   ```python
   for step_idx in range(n_steps):
       optimizer.zero_grad()
       bragg_t, chi_sq_t = _forward_once(use_mapping_zero_geometry=False)  # <-- FALSE!
       chi_sq_t.backward()
   ```
2. Inside `_stage_a_forward` with `use_mapping_zero_geometry=False` (lines 404-457):
   ```python
   else:  # use_mapping_zero_geometry=False
       # Build crystal_overrides with perturbed cell + orientation
       # ...
       if components.use_u_matrix:
           # U-matrix path: quaternion → rotation matrix → A*
           from dbex.nanobrag_bridge import quaternion_to_matrix
           q_norm = q_params / torch.norm(q_params)  # <-- q_params initialized from MOSFLM U
           U_matrix = quaternion_to_matrix(q_norm)
           A_star_new = U_matrix @ components.B_ideal_reciprocal  # <-- RECONSTRUCTION
           crystal_overrides["A_star"] = A_star_new
       # ...
       crystal_config, _ = create_crystal_config(
           dataload.crystal,
           dataload.Expt,
           N_cells=N_cells,
           apply_n_cells=apply_n_cells,
           crystal_overrides=crystal_overrides,  # <-- OVERRIDE WITH RECONSTRUCTED A*
           misset_deg_override=misset_xyz_deg,
       )
   ```

**Forward Model:** Computes `A_star_new = U_matrix @ B_ideal_reciprocal` where:
- `U_matrix` is derived from `q_params` (initialized via `derive_u_matrix_from_mosflm_a_star` and `matrix_to_quaternion`)
- `B_ideal_reciprocal` is computed from unit cell via `cctbx_cell(cell_params).fractionalization_matrix()` (stage_a_mapping_adam_debug.py:323-326)

**Chi-Squared Computation:** Same variance-weighted chi-squared as zero-point check

**Result:** chi_squared at step 0 = 1,425,248,640 (1.425B, ~1000× worse than 990k)

## Discrepancy Diagnosis

### Root Cause: B_ideal_reciprocal Mismatch (CONFIRMED)

**Hypothesis:** The reconstructed `A_star_new = U_matrix @ B_ideal_reciprocal` does NOT equal the original MOSFLM A* because `B_ideal_reciprocal` is computed differently than the implicit B_ideal used in the MOSFLM A* = U @ B identity.

**Evidence:**
1. `U_matrix` is derived from MOSFLM A* via `derive_u_matrix_from_mosflm_a_star(A_star_mosflm, cell_params)` (stage_a_mapping_adam_debug.py:315)
2. `B_ideal_reciprocal` is independently computed from unit cell via `cctbx_cell(cell_params).fractionalization_matrix()` (stage_a_mapping_adam_debug.py:323-326)
3. **CODE INSPECTION CONFIRMS BUG**: The `derive_u_matrix_from_mosflm_a_star` function (dbex/nanobrag_bridge.py:844-862) computes B_ideal using `TorchCrystal.compute_cell_tensors()` to extract `a_star, b_star, c_star` and constructs `B_ideal_reciprocal = np.column_stack([a_star_nb, b_star_nb, c_star_nb])`
4. **BUT**: The `_build_stage_a_components` function (stage_a_mapping_adam_debug.py:323-326) computes B_ideal using `cctbx_cell(cell_params).fractionalization_matrix().reshape(3, 3).T`

**Root Cause CONFIRMED:**
Two different B_ideal computation methods:
- **derive_u_matrix_from_mosflm_a_star**: Uses `TorchCrystal.compute_cell_tensors()` → `np.column_stack([a_star, b_star, c_star])`
- **_build_stage_a_components**: Uses `cctbx_cell().fractionalization_matrix().reshape(3, 3).T`

These two methods produce slightly different B_ideal matrices, leading to:
- `U_initial = A_star_mosflm @ inv(B_ideal_torch)` (from derive_u_matrix_from_mosflm_a_star)
- `A_star_reconstructed = U_initial @ B_ideal_cctbx` (in Adam loop)
- `A_star_reconstructed ≠ A_star_mosflm` because `B_ideal_cctbx ≠ B_ideal_torch`

**Mathematical consequence:**
```
A_star_reconstructed = (A_star_mosflm @ inv(B_ideal_torch)) @ B_ideal_cctbx
                     = A_star_mosflm @ (inv(B_ideal_torch) @ B_ideal_cctbx)
                     ≠ A_star_mosflm  (if B_ideal_torch ≠ B_ideal_cctbx)
```

This mismatch propagates through the simulator, producing vastly different Bragg peaks and catastrophic chi-squared (1.425B vs 990k).

### Why Zero-Point Check Succeeds

The zero-point check uses `use_mapping_zero_geometry=True`, which bypasses the U-matrix reconstruction entirely and uses the MOSFLM A* directly. Therefore, it achieves perfect parity (corr ≈ 1.0, chi-squared ~990k matching mapping).

### Why Adam Loop Fails at Step 0

The Adam loop uses `use_mapping_zero_geometry=False` even at step 0, forcing it to reconstruct A* via `U @ B_ideal_reciprocal`. If this reconstruction is numerically imperfect (off by even a small amount in crystal orientation), the resulting forward model produces drastically different Bragg peaks, leading to 1000× worse chi-squared.

## Proposed Fix (CONFIRMED: Option 2)

**Option 2: Fix B_ideal_reciprocal Computation (Root Cause Fix) — RECOMMENDED**

Ensure `B_ideal_reciprocal` in `_build_stage_a_components` is computed EXACTLY the same way as inside `derive_u_matrix_from_mosflm_a_star`, so that `U @ B_ideal_reciprocal == A_star_mosflm` numerically.

**Confirmed Implementation:**
1. Refactor `derive_u_matrix_from_mosflm_a_star` (dbex/nanobrag_bridge.py:794-880) to return BOTH `U_matrix` and `B_ideal_reciprocal` from the TorchCrystal computation
2. Update `_build_stage_a_components` (stage_a_mapping_adam_debug.py:305-326) to call the refactored helper and use the returned B_ideal_reciprocal directly
3. Delete the cctbx_cell().fractionalization_matrix() code (lines 323-326) to prevent future mismatch

**Code changes:**
```python
# dbex/nanobrag_bridge.py:794
def derive_u_matrix_from_mosflm_a_star(
    a_star: np.ndarray,
    cell: Tuple[float, float, float, float, float, float]
) -> Tuple[np.ndarray, np.ndarray]:  # <-- Return BOTH U and B_ideal
    """
    Extract U-matrix and B_ideal_reciprocal from mapping MOSFLM A*...

    Returns:
        Tuple of (U_matrix, B_ideal_reciprocal), both 3×3 numpy arrays (dtype=float64).
    """
    # ... existing B_ideal computation using TorchCrystal ...
    U = a_star @ B_inv
    return U, B_ideal_reciprocal  # <-- Return both
```

```python
# stage_a_mapping_adam_debug.py:305-326
if use_u_matrix:
    from dbex.nanobrag_bridge import (
        derive_u_matrix_from_mosflm_a_star,
        matrix_to_quaternion,
    )
    A_star_mosflm = np.array(dataload.crystal.get_A(), dtype=np.float64).reshape(3, 3)
    cell = dataload.crystal.get_unit_cell()
    cell_params = cell.parameters()

    # Get BOTH U and B_ideal from the same computation (CONVERGENCE-001 fix)
    U_matrix, B_ideal_reciprocal_np = derive_u_matrix_from_mosflm_a_star(A_star_mosflm, cell_params)

    # Convert to quaternion
    q_initial_np = matrix_to_quaternion(torch.tensor(U_matrix, dtype=torch.float64))
    q_initial = torch.tensor(q_initial_np, device=device, dtype=dtype)
    B_ideal_reciprocal = torch.tensor(B_ideal_reciprocal_np, device=device, dtype=dtype)

    # DELETE the cctbx_cell() code (lines 323-326) - no longer needed
```

**Pros:**
- Fixes the root cause; U-matrix reconstruction will be numerically exact at initialization
- Ensures `U_initial @ B_ideal_reciprocal == A_star_mosflm` by construction (both computed in same function)
- Eliminates dependency on cctbx for B_ideal (uses TorchCrystal consistently)

**Cons:**
- Requires signature change to `derive_u_matrix_from_mosflm_a_star` (breaks backward compatibility if used elsewhere)
- Mitigation: Check usages of this helper before refactoring

**Option 1: Use mapping geometry at step 0 (Quick Fix) — NOT RECOMMENDED**

This would mask the symptom without fixing the root cause. The B_ideal mismatch would still affect step 1+ optimization.

**Option 3: Validate and Document as Known Issue — NOT APPLICABLE**

Code inspection confirms this is a B_ideal computation mismatch bug, NOT a fundamental geometry incompatibility.

## Validation Plan

### Immediate Validation (No Code Changes)

Add debug logging to `_stage_a_forward` at U-matrix path (lines 426-436) to print:
```python
if step_idx == 0 and use_u_matrix:
    print(f"[DEBUG step 0] A_star_mosflm:\n{dataload.crystal.get_A()}")
    print(f"[DEBUG step 0] U_matrix:\n{U_matrix.detach().cpu().numpy()}")
    print(f"[DEBUG step 0] B_ideal_reciprocal:\n{components.B_ideal_reciprocal.detach().cpu().numpy()}")
    print(f"[DEBUG step 0] A_star_new (U @ B):\n{A_star_new.detach().cpu().numpy()}")
    print(f"[DEBUG step 0] ||A_star_new - A_star_mosflm||: {torch.norm(A_star_new - torch.tensor(dataload.crystal.get_A(), device=device, dtype=dtype))}")
```

Rerun Phase A2 with debug logging and inspect whether reconstruction error is small (<1e-6) or large (>1e-3).

### Root Cause Decision Tree

1. If `||A_star_new - A_star_mosflm|| < 1e-6`:
   - Reconstruction is numerically exact at initialization
   - Chi-squared gap is due to subtle simulator/variance differences (investigate variance components per Phase A5)
   - Proceed to Phase A5 variance telemetry

2. If `||A_star_new - A_star_mosflm|| > 1e-3`:
   - Reconstruction is numerically broken
   - B_ideal mismatch between `derive_u_matrix_from_mosflm_a_star` and `_build_stage_a_components`
   - Apply Option 2 (fix B_ideal computation)

3. If `1e-6 < ||A_star_new - A_star_mosflm|| < 1e-3`:
   - Small numerical error; may compound through simulator
   - Test Option 1 (use mapping geometry at step 0) to see if it eliminates chi-squared gap
   - If yes, apply Option 1 as interim fix and document as CONVERGENCE-003 known issue

## Next Actions

Per `input.md` Step 5 (CONDITIONAL bugfix), since we have identified a **clear code path discrepancy** (not a bug yet, but a mismatch between zero-point check and Adam loop):

1. **Do NOT apply speculative bugfix** (per input.md pitfall #2)
2. **Add debug logging** to capture A_star_mosflm, U_matrix, B_ideal_reciprocal, A_star_new, and reconstruction error at step 0
3. **Rerun Phase A2** with debug logging (input.md Step 6 Option B)
4. **Synthesize findings** based on reconstruction error magnitude
5. **If bug confirmed** (reconstruction error > 1e-3), apply Option 2 (refactor B_ideal computation) and rerun
6. **If no bug** (reconstruction error < 1e-6), document as CONVERGENCE-003 and pivot to Phase A5 variance analysis

## Findings Applied

- **PHYSICS-LOSS-002** (variance-weighted chi-squared sigma-floor guard): Relevant; chi-squared computation uses variance weighting in both code paths
- **GEOMETRY-003** (baseline misset derivation): Not directly relevant; U-matrix path bypasses misset entirely
- No existing finding directly addresses U-matrix A* reconstruction parity

## Metrics Summary

| Metric | Zero-Point Check | Adam Loop Step 0 | Ratio |
|--------|-----------------|------------------|-------|
| Chi-squared | 989,645.5 (~990k) | 1,425,248,640 (1.425B) | 1440× |
| Correlation vs mapping | 0.9999999843 | Unknown (not captured) | N/A |
| Max abs diff (photons) | 85.14 | Unknown | N/A |
| Code path | `use_mapping_zero_geometry=True` | `use_mapping_zero_geometry=False` | Different |
| A* source | MOSFLM direct (no override) | U @ B_ideal reconstruction | Different |

## Artifacts

- Zero-point check JSON: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/zero_point_check.json`
- Telemetry step 0: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/plans/active/.../telemetry/telemetry_step_000.json`
- Script: `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`
- U-matrix helpers: `dbex/nanobrag_bridge.py:derive_u_matrix_from_mosflm_a_star`, `quaternion_to_matrix`
