# B_ideal Fix Implementation

## Root Cause (Confirmed via Code Audit)

**File:** `dbex/nanobrag_refinement.py`
**Lines:** 784-818 (prior to fix)

The LBFGS closure was recomputing B_ideal from cctbx cell parameters instead of using the MOSFLM-derived B_ideal from initialization:

```python
# BUGGY CODE (lines 784-818):
U_0, _ = derive_u_matrix_from_mosflm_a_star(A_star_np, cell_params)  # B_ideal DISCARDED
# ...
# Recompute B_ideal from cctbx cell (WRONG):
cfg_b_ideal = TorchCrystalConfig(
    cell_a=a, cell_b=b, cell_c=c,
    cell_alpha=alpha, cell_beta=beta, cell_gamma=gamma,
    misset_deg=(0.0, 0.0, 0.0),
    mosflm_a_star=None,  # ← NOT USING MOSFLM A*
)
crystal_nb_b_ideal = TorchCrystal(cfg_b_ideal, device=device, dtype=dtype)
geom = crystal_nb_b_ideal.compute_cell_tensors()  # ← Recomputes B_ideal from cctbx cell
# ...
B_ideal_reciprocal_torch = torch.stack([a_star_nb, b_star_nb, c_star_nb], dim=1)
```

**Problem:**
- `derive_u_matrix_from_mosflm_a_star` returns `(U, B_ideal)` where B_ideal is derived from MOSFLM A* via TorchCrystal
- This B_ideal was DISCARDED (assigned to `_`)
- A NEW B_ideal was recomputed from cctbx `cell.parameters()` → TorchCrystal → `compute_cell_tensors()`
- cctbx B_ideal ≠ MOSFLM B_ideal (numerical difference due to different computation paths)
- Result: `U @ B_ideal_cctbx ≠ A*_MOSFLM` → catastrophic chi²=1.425B

## Fix Applied

**File:** `dbex/nanobrag_refinement.py`
**Lines:** 784-799 (after fix)

```python
# FIXED CODE:
U_0, B_ideal_reciprocal_np = derive_u_matrix_from_mosflm_a_star(A_star_np, cell_params)  # KEEP B_ideal

# Convert to quaternion
q_0 = matrix_to_quaternion(torch.tensor(U_0, dtype=torch.float64))

# Initialize trainable quaternion params
q_params = q_0.clone().to(device=device, dtype=dtype).requires_grad_(True)

# Use the MOSFLM-derived B_ideal (ensures U @ B_ideal == A*_MOSFLM at initialization)
B_ideal_reciprocal_torch = torch.tensor(B_ideal_reciprocal_np, device=device, dtype=dtype)
```

**Changes:**
1. Capture both `U_0` AND `B_ideal_reciprocal_np` from `derive_u_matrix_from_mosflm_a_star` (line 787)
2. Delete the cctbx TorchCrystal recomputation code (removed lines 798-818 of buggy version)
3. Directly convert `B_ideal_reciprocal_np` to torch tensor (line 799)

**Lines Deleted:** 13 lines (cctbx TorchCrystal creation + compute_cell_tensors + stack)
**Lines Added:** 4 lines (comments documenting the fix)
**Net change:** -9 lines

## Consistency with stage_a_mapping_adam_debug.py

The fix makes `dbex/nanobrag_refinement.py` consistent with `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`:

```python
# stage_a_mapping_adam_debug.py (lines 315-324):
U_matrix, B_ideal_reciprocal_np = derive_u_matrix_from_mosflm_a_star(A_star_mosflm, cell_params)
q_initial_np = matrix_to_quaternion(torch.tensor(U_matrix, dtype=torch.float64))
q_initial = torch.tensor(q_initial_np, device=device, dtype=dtype)
B_ideal_reciprocal = torch.tensor(B_ideal_reciprocal_np, device=device, dtype=dtype)
```

Both paths now use the SAME B_ideal source: MOSFLM A* → `derive_u_matrix_from_mosflm_a_star` → TorchCrystal → `compute_cell_tensors()`.

## Expected Impact

### Zero-Point Check (Unchanged)
- Uses `use_mapping_zero_geometry=True` → provides MOSFLM A* directly via `mosflm_a_star/b_star/c_star` tuples
- Bypasses U @ B_ideal reconstruction entirely
- Chi² ≈ 989k (should remain unchanged)

### LBFGS Optimization Loop (Fixed)
- Before fix: `U @ B_ideal_cctbx` produced chi²=1.425B (catastrophic)
- After fix: `U @ B_ideal_MOSFLM` should produce chi²~1M (healthy, matching zero-point magnitude)
- Expected improvement: **1000× reduction** in chi² at step 0 (1.425B → ~1M)

### Convergence Behavior
- If chi² step 0 is healthy (~1M), LBFGS should converge normally
- Expect median ROI CC ≥ 0.99 after 10 steps (per exit criteria)
- Expect stable or improving chi² trajectory

## Validation Plan

### Step 7: Rerun Test B1 (10-step LBFGS)
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 2400 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 10 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/revalidation/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/revalidation/stage_a_lbfgs_fixed.log
```

### Success Criteria
1. Zero-point check: chi²=989k ± 1% (unchanged)
2. **LBFGS step 0: chi² < 2M** (target ~1M, MUST be <2M to confirm fix)
3. LBFGS convergence: median CC ≥ 0.99 after 10 steps
4. No NaN/Inf gradients

### Failure Scenarios
- **Chi² step 0 still catastrophic (>2M):** Fix incomplete, B_ideal mismatch persists (check if fix was applied correctly)
- **Chi² step 0 healthy (~1M) but convergence fails:** Different issue (optimizer hyperparameters, variance stability, quaternion constraint)
- **Zero-point check fails:** Regression introduced (revert fix and investigate)

## Regression Guard

### Step 9: Run Smoke Test
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/pytest_stage_a_regression.log 2>&1
```

**Expected:** PASSED (cell+misset default path unaffected by U-matrix fix)

**Note:** The fix is scoped to `config.use_u_matrix_parameterization=True` path only. Default path (cell+misset) does not use B_ideal_reciprocal_torch, so no regression risk.

## Confidence Level
**HIGH** - The bug is explicit (discarding B_ideal, recomputing from different source). The fix is minimal (use returned value instead of recomputing). No side effects expected (scoped to U-matrix path only).
