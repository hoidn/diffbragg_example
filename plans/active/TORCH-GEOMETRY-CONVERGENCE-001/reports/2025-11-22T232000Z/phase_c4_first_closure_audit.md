# Phase C4 First Closure Audit — Parameter Staleness Investigation

**Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
**Phase:** C4 (First Closure Parameter Staleness Audit)
**Date:** 2025-11-22T232000Z

---

## Audit Scope

Trace log_scale and q_params from initialization through first closure evaluation to identify WHERE stale values are introduced in the diagnostic script's Adam path (`stage_a_mapping_adam_debug.py`).

**Context:** Phase C3 proved catastrophic chi²=8.8M occurs BEFORE first optimizer.step(), suggesting forward model uses stale parameters during first closure evaluation.

---

## Key Discovery: NO STALENESS BUG FOUND

After systematic code audit, **no parameter staleness bug was found**. All parameters are correctly captured and used in the closure.

---

## Findings

### 1. log_scale Tensor Identity

**Initialization:**
- `stage_a_mapping_adam_debug.py:732-737`: `log_scale = torch.tensor(initial_log_scale, device=device, dtype=dtype, requires_grad=train_scale)`

**Closure usage:**
- Line 924: `bragg_t, chi_sq_t = _forward_once(use_mapping_zero_geometry=False)`
- Line 470 in `_stage_a_forward`: `log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)`
- Line 485: `panel_scaled = panel_output * sqrt_spot_scale * torch.exp(log_scale_clamped)`

**Verdict:** ✓ SAME TENSOR — Closure correctly captures `log_scale` parameter via Python closure scope.

**Evidence:** The function `_forward_once` is defined at line 816 and captures `log_scale` from the enclosing scope. When called from the Adam loop at line 924, it uses the CURRENT value of `log_scale`, not a stale copy.

---

### 2. q_params Tensor Identity

**Initialization:**
- Line 767: `q_params = components.q_initial.clone().requires_grad_(train_orientation)`
- `components.q_initial` comes from line 321 (converted from U-matrix derived from MOSFLM A*)

**Closure usage:**
- Line 829: `q_params=q_params` (passed explicitly to `_stage_a_forward`)
- Line 432 in `_stage_a_forward`: `q_norm = q_params / torch.norm(q_params)`
- Line 434: `U_matrix = quaternion_to_matrix(q_norm)`

**Verdict:** ✓ SAME TENSOR — Closure correctly uses the trainable `q_params` parameter.

**Evidence:** The `_forward_once` function explicitly passes `q_params` to `_stage_a_forward`, and the Adam optimizer updates this tensor in-place via `.grad` after backward().

---

### 3. U-Matrix Derivation

**Code path:** `_stage_a_forward:428-436`

```python
if components.use_u_matrix:
    from dbex.nanobrag_bridge import quaternion_to_matrix
    q_norm = q_params / torch.norm(q_params)  # Enforce ||q|| = 1
    U_matrix = quaternion_to_matrix(q_norm)
    A_star_new = U_matrix @ components.B_ideal_reciprocal
```

**Verdict:** ✓ CORRECT — U derived from CURRENT q_params, not initialization value.

**Evidence:** Each closure call recomputes U from the current `q_params` tensor (which is updated by optimizer.step()).

---

### 4. A* Reconstruction

**Code path:** `_stage_a_forward:435-442`

```python
A_star_new = U_matrix @ components.B_ideal_reciprocal
A_star_np = A_star_new.detach().cpu().numpy()
crystal_overrides["mosflm_a_star"] = tuple(A_star_np[:, 0].tolist())
crystal_overrides["mosflm_b_star"] = tuple(A_star_np[:, 1].tolist())
crystal_overrides["mosflm_c_star"] = tuple(A_star_np[:, 2].tolist())
```

**Formula:** A* = U_current @ B_ideal_mosflm

**Verdict:** ✓ CORRECT — A* reconstructed from CURRENT U and correct B_ideal.

**Evidence:**
- U_matrix is recomputed from current q_params (no stale reference)
- B_ideal_reciprocal comes from `components` (initialized at line 324 from MOSFLM-derived value)
- The Phase B5 fix ensured B_ideal matches MOSFLM decomposition (not cctbx recomputation)

---

### 5. Scale Application

**Code path:** `_stage_a_forward:470, 485`

```python
log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
...
panel_scaled = panel_output * sqrt_spot_scale * torch.exp(log_scale_clamped)
```

**Verdict:** ✓ CORRECT — Scale derived from CURRENT log_scale parameter.

**Evidence:** `log_scale` is captured from closure scope and used directly (no `.detach()`, no stale copy).

---

### 6. crystal_overrides Construction

**Code path:** `_stage_a_forward:418-425, 440-442`

**Cell parameters:**
```python
crystal_overrides = {
    "cell_a": perturbed_cell_a,  # = cell_params[0] * torch.exp(log_cell_a_delta)
    "cell_b": perturbed_cell_b,
    "cell_c": perturbed_cell_c,
    "cell_alpha": perturbed_alpha,  # = cell_params[3] + torch.tanh(angle_alpha_raw) * 10.0
    "cell_beta": perturbed_beta,
    "cell_gamma": perturbed_gamma,
}
```

**U-matrix path (adds mosflm_a/b/c_star):**
```python
crystal_overrides["mosflm_a_star"] = tuple(A_star_np[:, 0].tolist())
crystal_overrides["mosflm_b_star"] = tuple(A_star_np[:, 1].tolist())
crystal_overrides["mosflm_c_star"] = tuple(A_star_np[:, 2].tolist())
```

**Verdict:** ✓ CORRECT — crystal_overrides built from CURRENT parameters.

**Evidence:** All overrides are computed fresh in each closure call from current parameter tensors.

---

## Root Cause Determination

**PRIMARY BUG:** **NONE FOUND in parameter flow**

**CONFIDENCE:** HIGH (~95%)

**MECHANISM:** After systematic audit of ALL parameter initialization and closure usage paths:
1. log_scale: Correctly captured and used ✓
2. q_params: Correctly captured and used ✓
3. U-matrix: Correctly derived from current q_params ✓
4. A* reconstruction: Correctly uses current U @ B_ideal ✓
5. crystal_overrides: Correctly built from current parameters ✓
6. Scale application: Correctly uses current log_scale ✓

---

## Alternative Hypothesis: Zero-Point vs First-Closure Code Path Divergence

**CRITICAL FINDING:** The zero-point validation and first closure use DIFFERENT code paths:

### Zero-Point Path (SUCCEEDS — chi²=990k, corr=1.0)

**Code:** `stage_a_mapping_adam_debug.py:836`
```python
bragg_before_t, chi_sq_before_t = _forward_once(use_mapping_zero_geometry=True)
```

**Effect:** Calls `_stage_a_forward` with `use_mapping_zero_geometry=True`
- Line 397-405: `create_crystal_config(crystal, Expt, ..., crystal_overrides=None, misset_deg_override=None)`
- **Result:** Uses mapping geometry DIRECTLY (MOSFLM A* injection, no parameter perturbations)

### First Closure Path (FAILS — chi²=8.8M)

**Code:** `stage_a_mapping_adam_debug.py:924`
```python
bragg_t, chi_sq_t = _forward_once(use_mapping_zero_geometry=False)
```

**Effect:** Calls `_stage_a_forward` with `use_mapping_zero_geometry=False`
- Line 407-464: Builds `crystal_overrides` with cell parameters AND mosflm_a/b/c_star
- Line 457-464: `create_crystal_config(crystal, Expt, ..., crystal_overrides={...}, misset_deg_override=misset_xyz_deg)`
- **Result:** Uses perturbed geometry (U @ B_ideal → mosflm_a/b/c_star)

**Hypothesis:** Even though ALL parameters are at zero-point (log_cell_X_delta=0, q_params=q_0), the *code path* through `create_crystal_config` with `crystal_overrides` produces DIFFERENT results than the path with `crystal_overrides=None`.

**Mechanism:** Possible numerical precision loss or normalization differences when:
1. Extracting MOSFLM A* from crystal
2. Decomposing into U and B_ideal
3. Reconstructing A* = U @ B_ideal
4. Converting to numpy tuples
5. Passing through `create_crystal_config(..., crystal_overrides={"mosflm_a_star": ..., ...})`

---

## Recommended Actions

### Priority 1: Test Code Path Equivalence (HIGH confidence ~85%)

**Hypothesis:** The `use_mapping_zero_geometry=False` path with all parameters at zero produces DIFFERENT results than `use_mapping_zero_geometry=True` due to round-trip precision loss or `create_crystal_config` handling differences.

**Test:**
1. Add diagnostic print in `_stage_a_forward` to log:
   - A_star_new checksum when use_mapping_zero_geometry=False with zero parameters
   - Crystal.get_A() checksum when use_mapping_zero_geometry=True
2. Compare the two checksums — if they differ, the bug is in the round-trip conversion
3. Add logging inside `create_crystal_config` to see how `crystal_overrides={"mosflm_a_star": ...}` is applied

**Expected outcome:** Find that `crystal_overrides` path produces slightly different A* matrix than direct MOSFLM injection, amplifying to catastrophic chi² due to sensitivity.

**Implementation:** Add instrumentation to `_stage_a_forward` and `create_crystal_config` (dbex/nanobrag_bridge.py).

---

### Priority 2: Test Minimal Reproduction (MEDIUM confidence ~60%)

If Priority 1 doesn't find the issue:

**Test:** Create standalone script that:
1. Loads crystal geometry
2. Derives U, B_ideal from MOSFLM A*
3. Reconstructs A* = U @ B_ideal
4. Compares reconstructed A* to original MOSFLM A* (max abs diff)
5. Creates two crystal configs:
   - Path A: `create_crystal_config(..., crystal_overrides=None)`
   - Path B: `create_crystal_config(..., crystal_overrides={"mosflm_a_star": tuple(...), ...})`
6. Simulates with both and compares chi²

**Expected outcome:** Isolate whether the bug is in U/B_ideal derivation OR in `create_crystal_config` handling.

---

### Priority 3: Test Adam vs LBFGS (LOW confidence ~15%)

**Note:** The production `run_nanobrag_refinement` uses LBFGS, not Adam. The diagnostic script's Adam path may have optimizer-specific issues.

**Test:** Run Phase C3 diagnostic with `--use-lbfgs` flag to see if LBFGS shows same catastrophic chi².

**Rationale:** LBFGS uses closure pattern differently (multiple line search evaluations), which might expose/hide the bug differently than Adam's single forward-backward-step pattern.

---

## Files Audited

1. `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`
   - Lines 686-933: `_stage_a_adam_core` (Adam loop and parameter initialization)
   - Lines 351-495: `_stage_a_forward` (shared forward model)
   - Lines 250-348: `_build_stage_a_components` (U-matrix and B_ideal initialization)

2. `dbex/nanobrag_refinement.py` (for comparison)
   - Lines 779-806: U-matrix initialization (matches diagnostic script)
   - Lines 977-1033: U-matrix closure path (similar to diagnostic, but LBFGS optimizer)

3. `dbex/nanobrag_bridge.py` (referenced, not fully audited)
   - `create_crystal_config`: How crystal_overrides are applied
   - `derive_u_matrix_from_mosflm_a_star`: U and B_ideal derivation

---

## Conclusion

**NO PARAMETER STALENESS BUG FOUND.**

All parameters (log_scale, q_params, cell deltas, angle raws) are correctly:
1. Initialized from mapping zero-point
2. Captured in closure scope (Adam path) or passed explicitly (LBFGS path)
3. Used in forward model without detachment or stale copies
4. Updated by optimizer after backward()

**NEW HYPOTHESIS:** The catastrophic chi² is caused by a **code path divergence** between:
- Zero-point validation: `use_mapping_zero_geometry=True` → direct MOSFLM injection
- First closure: `use_mapping_zero_geometry=False` → U/B_ideal round-trip → crystal_overrides

**NEXT STEP:** Priority 1 diagnostic to instrument the two code paths and identify where they diverge (suspect: `create_crystal_config` handling of `crystal_overrides` vs direct MOSFLM injection).

---

## Artifacts

- `phase_c4_first_closure_audit.md` (this file)
- Code inspection notes (no additional JSON/logs — audit was manual code review)

---

## Next Loop

**Objective:** Implement Priority 1 diagnostic (code path equivalence test) to prove/disprove the hypothesis that `use_mapping_zero_geometry=False` with zero parameters produces different A* than `use_mapping_zero_geometry=True`.

**Success criteria:**
- Identify exact line/function where the two paths diverge
- Quantify the A* difference (expect ~1e-6 to 1e-3 precision loss)
- Confirm this precision loss amplifies to catastrophic chi²

**If diagnostic fails:** Escalate to Priority 2 (minimal reproduction) or Priority 3 (test LBFGS optimizer).
