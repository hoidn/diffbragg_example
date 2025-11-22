# Code Path Audit — Script _forward_once vs Production compute_loss

**Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
**Phase:** B5 (Fix Implementation)
**Date:** 2025-11-22T183012Z
**Purpose:** Side-by-side comparison of U-matrix reconstruction logic between script-level `_forward_once` and production `run_nanobrag_refinement`.

---

## Executive Summary

**ROOT CAUSE IDENTIFIED:** Script `_stage_a_forward` (called by `_forward_once`) sets `crystal_overrides["A_star"] = A_star_new` (line 437), but `create_crystal_config` **DOES NOT SUPPORT** the `A_star` key. Instead, when ANY `crystal_overrides` are provided, `create_crystal_config` sets `mosflm_a_star = None` (lines 575-579), which causes nanobrag_torch to recompute A* from cell parameters instead of using the quaternion-derived A*.

**CONSEQUENCE:** U @ B_ideal_cctbx ≠ A*_mosflm → catastrophic chi²=1.425B

**FIX:** Change script to use `mosflm_a_star`, `mosflm_b_star`, `mosflm_c_star` keys in `crystal_overrides` instead of unsupported `A_star` key.

---

## Audit Findings (A-D)

### A. B_ideal Derivation Source

**Production Path (CORRECT):**
- File: `dbex/nanobrag_refinement.py:784-799`
- Code:
  ```python
  # Line 784: Call derive_u_matrix_from_mosflm_a_star, capture BOTH U and B_ideal
  U_0, B_ideal_reciprocal_np = derive_u_matrix_from_mosflm_a_star(A_star_mosflm, cell_params)

  # Line 799: Convert B_ideal to torch tensor (uses MOSFLM-derived B_ideal)
  B_ideal_reciprocal_torch = torch.tensor(B_ideal_reciprocal_np, dtype=torch.float32, device=device)
  ```
- **Verdict:** ✅ CORRECT — Uses B_ideal from `derive_u_matrix_from_mosflm_a_star` (TorchCrystal computation)

**Script Path (CHECK):**
- File: `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:315-324`
- Code:
  ```python
  # Line 317: Call derive_u_matrix_from_mosflm_a_star, capture BOTH U and B_ideal
  U_matrix, B_ideal_reciprocal_np = derive_u_matrix_from_mosflm_a_star(A_star_mosflm, cell_params)

  # Line 324: Convert B_ideal to torch tensor (uses MOSFLM-derived B_ideal)
  B_ideal_reciprocal = torch.tensor(B_ideal_reciprocal_np, device=device, dtype=dtype)
  ```
- **Verdict:** ✅ CORRECT — Uses same B_ideal source as production (from TorchCrystal)

**Conclusion:** B_ideal source is CORRECT in both paths. Not the bug.

---

### B. Quaternion Normalization

**Production Path (CORRECT):**
- File: `dbex/nanobrag_refinement.py:973`
- Code:
  ```python
  q_norm = q_params / torch.norm(q_params)  # Enforce ||q|| = 1
  U = quaternion_to_matrix(q_norm)  # 3x3 rotation matrix
  ```
- **Verdict:** ✅ CORRECT — Normalizes quaternion before conversion

**Script Path (CHECK):**
- File: `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:432-434`
- Code:
  ```python
  # Line 432: Normalize quaternion to unit sphere
  q_norm = q_params / torch.norm(q_params)
  # Line 434: Convert to rotation matrix U ∈ SO(3)
  U_matrix = quaternion_to_matrix(q_norm)
  ```
- **Verdict:** ✅ CORRECT — Normalizes quaternion before conversion

**Conclusion:** Quaternion normalization is CORRECT in both paths. Not the bug.

---

### C. A* Reconstruction Formula

**Production Path (CORRECT):**
- File: `dbex/nanobrag_refinement.py:976`
- Code:
  ```python
  A_star_new = U @ B_ideal_reciprocal_torch  # Compute updated A*
  ```
- **Verdict:** ✅ CORRECT — Uses U @ B_ideal formula

**Script Path (CHECK):**
- File: `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:436`
- Code:
  ```python
  # Line 436: Reconstruct A* = U @ B_ideal_reciprocal
  A_star_new = U_matrix @ components.B_ideal_reciprocal
  ```
- **Verdict:** ✅ CORRECT — Uses same formula, same B_ideal source

**Conclusion:** A* reconstruction formula is CORRECT in both paths. Not the bug.

---

### D. Detector/Crystal/Simulator Instantiation — **BUG FOUND**

**Production Path (CORRECT):**
- File: `dbex/nanobrag_refinement.py:1009-1025`
- Code:
  ```python
  # Convert A* to numpy for crystal_overrides
  A_star_np = A_star_new.detach().cpu().numpy()
  mosflm_a_star_tuple = tuple(A_star_np[:, 0].tolist())
  mosflm_b_star_tuple = tuple(A_star_np[:, 1].tolist())
  mosflm_c_star_tuple = tuple(A_star_np[:, 2].tolist())

  crystal_overrides = {
      'cell_a': perturbed_cell_a,
      'cell_b': perturbed_cell_b,
      'cell_c': perturbed_cell_c,
      'cell_alpha': perturbed_alpha,
      'cell_beta': perturbed_beta,
      'cell_gamma': perturbed_gamma,
      'mosflm_a_star': mosflm_a_star_tuple,  # ← Uses MOSFLM keys
      'mosflm_b_star': mosflm_b_star_tuple,
      'mosflm_c_star': mosflm_c_star_tuple,
  }
  ```
- **Verdict:** ✅ CORRECT — Uses `mosflm_a_star`, `mosflm_b_star`, `mosflm_c_star` keys, which `create_crystal_config` recognizes

**Script Path (BUG):**
- File: `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:437`
- Code:
  ```python
  # Line 418-425: Create crystal_overrides with cell parameters
  crystal_overrides = {
      "cell_a": perturbed_cell_a,
      "cell_b": perturbed_cell_b,
      "cell_c": perturbed_cell_c,
      "cell_alpha": perturbed_alpha,
      "cell_beta": perturbed_beta,
      "cell_gamma": perturbed_gamma,
  }

  # Line 428: Enter U-matrix branch
  if components.use_u_matrix:
      # ... (compute A_star_new = U_matrix @ components.B_ideal_reciprocal)

      # Line 437: ❌ BUG — Sets unsupported "A_star" key
      crystal_overrides["A_star"] = A_star_new
      misset_xyz_deg = None  # No misset override in U-matrix mode
  ```
- **Verdict:** ❌ **BUG FOUND** — Sets `crystal_overrides["A_star"]`, which `create_crystal_config` **DOES NOT SUPPORT**

**create_crystal_config behavior:**
- File: `dbex/nanobrag_bridge.py:569-579`
- Code:
  ```python
  # Line 569-574: When crystal_overrides is provided, skip A* injection
  if crystal_overrides is None:
      A_tuple = crystal.get_A()
      A = np.array(A_tuple).reshape(3, 3)
      mosflm_a_star = np.array(A[:, 0])
      mosflm_b_star = np.array(A[:, 1])
      mosflm_c_star = np.array(A[:, 2])
  else:
      # ❌ BUG TRIGGER: Sets mosflm_a_star = None when ANY overrides present
      # Let nanobrag_torch compute A* from overridden cell parameters
      mosflm_a_star = None
      mosflm_b_star = None
      mosflm_c_star = None
  ```
- **Consequence:** `crystal_overrides["A_star"]` is **IGNORED**, and nanobrag_torch computes A* from perturbed cell parameters (a, b, c, α, β, γ) instead of using quaternion-derived A*.
- **Result:** A*_computed_from_cell ≠ A*_from_quaternion → catastrophic chi²

---

## Fix Implementation

### Root Cause

Script sets `crystal_overrides["A_star"] = A_star_new`, but `create_crystal_config` **only recognizes** `mosflm_a_star`, `mosflm_b_star`, `mosflm_c_star` keys (per `dbex/nanobrag_bridge.py:603-605`).

### Solution

Change script to use the **same keys** as production code:

**File:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`
**Lines:** 428-438 (U-matrix branch)

**Before (BROKEN):**
```python
if components.use_u_matrix:
    # ... (compute A_star_new)
    crystal_overrides["A_star"] = A_star_new  # ❌ Unsupported key
    misset_xyz_deg = None
```

**After (FIXED):**
```python
if components.use_u_matrix:
    # ... (compute A_star_new)
    # Convert A* to numpy and extract columns as tuples (match production path)
    A_star_np = A_star_new.detach().cpu().numpy()
    crystal_overrides["mosflm_a_star"] = tuple(A_star_np[:, 0].tolist())
    crystal_overrides["mosflm_b_star"] = tuple(A_star_np[:, 1].tolist())
    crystal_overrides["mosflm_c_star"] = tuple(A_star_np[:, 2].tolist())
    misset_xyz_deg = None
```

### Validation

This fix ensures:
1. ✅ `create_crystal_config` receives `mosflm_a_star`, `mosflm_b_star`, `mosflm_c_star` keys (lines 603-605 in nanobrag_bridge.py)
2. ✅ nanobrag_torch uses quaternion-derived A* instead of recomputing from cell parameters
3. ✅ U @ B_ideal = A*_mosflm at initialization (chi² ~1.13M instead of 1.425B)

---

## Summary of Discrepancies

| Element | Production Path | Script Path | Discrepancy? |
|---------|----------------|-------------|--------------|
| **A. B_ideal source** | `derive_u_matrix_from_mosflm_a_star` return value | `derive_u_matrix_from_mosflm_a_star` return value | ✅ No |
| **B. Quaternion norm** | `q / torch.norm(q)` before conversion | `q / torch.norm(q)` before conversion | ✅ No |
| **C. A* formula** | `U @ B_ideal_reciprocal_torch` | `U @ B_ideal_reciprocal` | ✅ No |
| **D. Crystal config** | Sets `mosflm_a_star`, `mosflm_b_star`, `mosflm_c_star` | Sets unsupported `A_star` key | ❌ **BUG** |

**Fix Option:** Quick Patch (Option 1) — Only 1 isolated bug found (unsupported key).

---

## File References

- **Script (broken):** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:437`
- **Production (working):** `dbex/nanobrag_refinement.py:1009-1025`
- **Config function:** `dbex/nanobrag_bridge.py:514-620` (especially 569-579, 603-605)
- **Commit e86fd4e:** B_ideal bugfix (applied correctly in both paths)

---

**Next Actions:** Implement fix (change `A_star` to `mosflm_*_star` keys), run regression guard, execute 1-step diagnostic, validate chi² ~1.13M.
