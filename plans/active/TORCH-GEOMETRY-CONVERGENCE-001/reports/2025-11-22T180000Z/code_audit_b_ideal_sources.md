# Code Audit: B_ideal Computation Sources

## Executive Summary
Found **TWO DIFFERENT B_ideal computation paths** in the codebase:
1. **Initialization path** (stage_a_mapping_adam_debug.py:317): Uses `derive_u_matrix_from_mosflm_a_star` → TorchCrystal → returns `(U, B_ideal_reciprocal_np)`
2. **LBFGS closure path** (dbex/nanobrag_refinement.py:814): Creates NEW TorchCrystal → computes B_ideal from CURRENT cell parameters

**ROOT CAUSE CONFIRMED:** The closure re-computes B_ideal from perturbed cell parameters (lines 973-981) instead of using the fixed B_ideal from initialization. This causes A* = U @ B_ideal reconstruction to diverge from A*_MOSFLM.

## Search Results

### fractionalization_matrix Usage
File: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/grep_fractionalization_matrix.txt`

```
plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:327:        # Prior bug: cctbx fractionalization_matrix() produced different B_ideal than TorchCrystal,
```

**Analysis:** Comment only - no active use. Prior cctbx code was deleted (bugfix 826f4c9).

### compute_cell_tensors Usage
File: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/grep_compute_cell_tensors.txt`

```
dbex/nanobrag_refinement.py:814:        geom = crystal_nb_b_ideal.compute_cell_tensors()
dbex/nanobrag_bridge.py:725:        3. Extract B_ideal from nanobrag_torch's compute_cell_tensors()
dbex/nanobrag_bridge.py:782:        geom = crystal_nb.compute_cell_tensors()
dbex/nanobrag_bridge.py:865:        geom = crystal_nb.compute_cell_tensors()
dbex/nanobrag_bridge.py:1023:            compute_cell_tensors() defines B_ideal. When None, a temporary
dbex/nanobrag_bridge.py:1085:        geom = crystal_nb.compute_cell_tensors()
dbex/nanobrag_bridge.py:1108:        geom = crystal_nb.compute_cell_tensors()
```

**CRITICAL FINDING:** `dbex/nanobrag_refinement.py:814` is **INSIDE the LBFGS closure's compute_loss function** (specifically in the U-matrix path, lines 985-1001).

### B_ideal_reciprocal Assignments
File: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/grep_b_ideal_assignments.txt`

```
plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:304:    B_ideal_reciprocal = None
plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:324:        B_ideal_reciprocal = torch.tensor(B_ideal_reciprocal_np, device=device, dtype=dtype)
plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:347:        B_ideal_reciprocal=B_ideal_reciprocal,
```

**Analysis:** B_ideal_reciprocal is assigned ONCE at initialization (line 324), then passed to StageAContext (line 347). It is **never reassigned** in the script.

## Code Path Analysis

### Path 1: Zero-Point Check (uses_mapping_zero_geometry=True)
**File:** plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py
**Lines:** 310-328

```python
# Extract MOSFLM A* from crystal
A_star_mosflm = np.array(dataload.crystal.get_A(), dtype=np.float64).reshape(3, 3)
cell = dataload.crystal.get_unit_cell()
cell_params = cell.parameters()  # (a, b, c, alpha, beta, gamma)

# Derive U-matrix and B_ideal from MOSFLM A*
U_matrix, B_ideal_reciprocal_np = derive_u_matrix_from_mosflm_a_star(A_star_mosflm, cell_params)

# Convert B_ideal to torch tensor
B_ideal_reciprocal = torch.tensor(B_ideal_reciprocal_np, device=device, dtype=dtype)
```

**Key:** B_ideal is derived from TorchCrystal inside `derive_u_matrix_from_mosflm_a_star`, which uses the MOSFLM cell parameters.

### Path 2: LBFGS Optimization Loop (uses_mapping_zero_geometry=False)
**File:** dbex/nanobrag_refinement.py
**Lines:** 973-1001 (inside `compute_loss` function, which is called by LBFGS closure)

```python
# Compute perturbed cell parameters (refinement DOFs)
perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)
perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

# U-matrix path (line 985-1001):
if config.use_u_matrix_parameterization:
    q_norm = q_params / torch.norm(q_params)
    U = quaternion_to_matrix(q_norm)
    A_star_new = U @ B_ideal_reciprocal_torch  # ← Uses B_ideal_reciprocal_torch from closure scope
```

**BUT WHERE DOES B_ideal_reciprocal_torch COME FROM?**

Looking at lines 794-818 (before the closure definition):

```python
# Line 794: Initialize B_ideal_reciprocal_torch for U-matrix path
if config.use_u_matrix_parameterization:
    # Compute B_ideal from baseline cell (no perturbations)
    # ISSUE: This uses cctbx cell.parameters(), NOT MOSFLM-derived B_ideal!
    cell = crystal.get_unit_cell()
    a, b, c, alpha, beta, gamma = cell.parameters()

    # Create TorchCrystal with baseline cell
    cfg_b_ideal = CrystalConfig(
        cell_a=a, cell_b=b, cell_c=c,
        cell_alpha=alpha, cell_beta=beta, cell_gamma=gamma,
        misset_deg=(0.0, 0.0, 0.0),
        mosflm_a_star=None,  # ← NOT USING MOSFLM A*
        mosflm_b_star=None,
        mosflm_c_star=None,
    )
    crystal_nb_b_ideal = TorchCrystal(cfg_b_ideal, device=device, dtype=dtype)
    geom = crystal_nb_b_ideal.compute_cell_tensors()  # ← Line 814: Recomputes B_ideal
    a_star_nb = geom["a_star"].reshape(3)
    b_star_nb = geom["b_star"].reshape(3)
    c_star_nb = geom["c_star"].reshape(3)
    B_ideal_reciprocal_torch = torch.stack([a_star_nb, b_star_nb, c_star_nb], dim=1)
```

**ROOT CAUSE:**
- The **LBFGS closure** creates a NEW TorchCrystal (line 813) using `crystal.get_unit_cell().parameters()` (cctbx cell)
- This computes B_ideal via `compute_cell_tensors()` from the **cctbx cell**, NOT from MOSFLM A*
- The **initialization path** (stage_a_mapping_adam_debug.py) computes B_ideal from MOSFLM A* via `derive_u_matrix_from_mosflm_a_star`
- These two B_ideal matrices are DIFFERENT, causing U @ B_ideal ≠ A*_MOSFLM

## Why Zero-Point Check Passes
Zero-point check uses `use_mapping_zero_geometry=True`, which **bypasses the U @ B_ideal reconstruction entirely**:
- It directly provides MOSFLM A* to the crystal config via `mosflm_a_star/b_star/c_star` tuples (lines 1009-1018)
- No U @ B_ideal matmul occurs → B_ideal mismatch is invisible
- Chi² = 989k (healthy)

## Why LBFGS Optimization Fails
LBFGS optimization uses the U-matrix path (line 985-1001):
- Computes `A_star_new = U @ B_ideal_reciprocal_torch` (line 1001)
- `B_ideal_reciprocal_torch` comes from cctbx cell (line 814), NOT MOSFLM
- Even with correct U from quaternion, U @ B_ideal_cctbx ≠ A*_MOSFLM
- Chi² = 1.425B (catastrophic)

## Fix Required
**Option 1: Pass MOSFLM-derived B_ideal from stage_a_mapping_adam_debug.py to dbex/nanobrag_refinement.py**
- Add `B_ideal_reciprocal_override` parameter to `build_stage_a_lbfgs_closure`
- Use this override instead of recomputing from cctbx cell
- Ensure consistency: B_ideal_reciprocal_torch = B_ideal_reciprocal_override (from MOSFLM)

**Option 2: Use MOSFLM A* in the TorchCrystal config (line 809-812)**
- Instead of `mosflm_a_star=None`, pass the MOSFLM A* columns
- Extract B_ideal from TorchCrystal's internal state (if it stores it separately from A*)

**Recommended: Option 1** (simpler, explicit, matches bugfix 826f4c9 design)

## Validation
After fix:
1. B_ideal hash at initialization (stage_a_mapping_adam_debug.py:324) should MATCH B_ideal hash in closure (dbex/nanobrag_refinement.py:818)
2. Zero-point check: chi² should remain ~989k (unchanged)
3. LBFGS step 0: chi² should drop from 1.425B → ~1M (1000× improvement)

## File Pointers
- Initialization: `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:304-347`
- Closure B_ideal recomputation: `dbex/nanobrag_refinement.py:794-818`
- Closure U @ B_ideal matmul: `dbex/nanobrag_refinement.py:1001`
- Zero-point bypass: `dbex/nanobrag_refinement.py:1009-1018`

## Confidence Level
**HIGH** - Code paths and data flow are explicit. The divergence point (line 814 recomputation vs line 324 MOSFLM-derived) is unambiguous.
