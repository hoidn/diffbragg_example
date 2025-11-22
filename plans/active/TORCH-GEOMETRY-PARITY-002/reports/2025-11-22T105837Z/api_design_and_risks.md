# Phase A2/A3: API Design & Risk Analysis

**Initiative:** TORCH-GEOMETRY-PARITY-002
**Date:** 2025-11-22T105837Z
**Phase:** A2/A3 — Analysis & Design
**Tasks:** API design for U-matrix mode + risk mitigation strategies

## API Design (Minimal Changes)

### New Components

**1. Helper: `derive_u_matrix_from_mosflm_a_star`**
- **Location:** `dbex/nanobrag_bridge.py`
- **Signature:** `derive_u_matrix_from_mosflm_a_star(a_star: np.ndarray, cell: CellParams) -> np.ndarray[3,3]`
- **Purpose:** Extract U-matrix from mapping MOSFLM A* without SO(3) projection (preserves strain)
- **Implementation:**
  ```python
  B_ideal_reciprocal = compute_b_ideal_reciprocal(cell)  # existing helper
  U = a_star @ np.linalg.inv(B_ideal_reciprocal)  # No proper_rotation!
  return U  # 3x3, may have det(U) ≈ 1 ± ε (small strain)
  ```

**2. Helper: `matrix_to_quaternion` / `quaternion_to_matrix`**
- **Location:** `dbex/nanobrag_bridge.py`
- **Purpose:** Convert between 3×3 rotation matrices and unit quaternions
- **Implementation:** Wrap `scipy.spatial.transform.Rotation` with torch tensor conversions
- **Validation:** Roundtrip test `torch.allclose(quaternion_to_matrix(matrix_to_quaternion(U)), U, atol=1e-6)`

**3. Config Flag: `use_u_matrix_parameterization`**
- **Location:** `dbex/nanobrag_refinement.py` (or `dbex/config.py` if central config exists)
- **Type:** `bool`, default `False`
- **Plumbing:** CLI `--use-u-matrix` → `RefinementConfig.use_u_matrix_parameterization` → `build_mapping_stage_a_context`

**4. Extend `StageAContext`**
- **New field:** `q_params: Optional[torch.Tensor]` — trainable quaternion (4-DOF) when U-matrix mode is enabled
- **Initialization:** When `use_u_matrix_parameterization=True`, call `derive_u_matrix_from_mosflm_a_star`, convert to quaternion, store in context

**5. Branch `build_stage_a_lbfgs_closure`**
- **Current path:** cell+misset (orientation_vec, cell_logs, angle_raws) → unchanged, remains default
- **New U-matrix path:** `if config.use_u_matrix_parameterization: ...`
  - Normalize `q_params`: `q_norm = q_params / torch.norm(q_params)`
  - Convert to matrix: `U = quaternion_to_matrix(q_norm)`
  - Compute A*: `A_star_new = U @ B_ideal_reciprocal_torch`
  - Update `crystal_overrides['A_star']` with A_star_new
  - Forward, loss, backward, return loss

**6. Extend Parity Probe**
- **Script:** `plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py`
- **New flag:** `--use-u-matrix`
- **Action:** When enabled, initialize U-matrix from MOSFLM A* (no projection), run forward, compare A* parity
- **Output:** `max_abs_diff`, `quaternion_delta_norm` in JSON

### Zero-Point Initialization Contract

**Mapping MOSFLM A* → U₀ → q₀:**
1. Extract `U₀ = A*_mapping @ inv(B_ideal_reciprocal)` (no proper_rotation projection)
2. Convert to quaternion: `q₀ = Rotation.from_matrix(U₀).as_quat()`  (scipy convention: [x, y, z, w])
3. Initialize trainable: `q_params = torch.tensor(q₀, dtype=torch.float64, requires_grad=True)`

**Parity Expectation:**
At zero deltas (before any LBFGS updates), reconstructed A* from `quaternion_to_matrix(q₀ / ‖q₀‖) @ B_ideal_reciprocal` should match `A*_mapping` to <1e-6 (roundtrip precision in float64).

---

## Risk Analysis & Mitigation

### Risk 1: Quaternion Normalization Drift

**Description:** LBFGS updates may push `q_params` off the unit sphere faster than per-closure normalization can correct, leading to numerical instability or loss surface artifacts.

**Likelihood:** Low (LBFGS typically takes small steps in well-conditioned problems).

**Impact:** Medium (if drift >1e-2, gradients may become biased).

**Mitigation:**
1. **Monitor ‖q‖ in telemetry:** Log `quaternion_norm = torch.norm(q_params).item()` every closure call.
2. **Alert threshold:** If `|‖q‖ - 1.0| > 1e-3` for >5 consecutive iterations, warn and switch to projected gradient descent.
3. **Fallback:** Reparameterize as stereographic projection (3-param, enforces ‖q‖=1 implicitly).

### Risk 2: Roundtrip Numerical Precision

**Description:** Converting U-matrix → quaternion → U-matrix may introduce >1e-6 error, failing the parity test even at zero deltas.

**Likelihood:** Very low (scipy `Rotation` is numerically robust, float64 provides ~15 decimal digits).

**Impact:** High (would block exit criterion #1).

**Mitigation:**
1. **Use float64 for initialization:** `torch.tensor(q₀, dtype=torch.float64)`
2. **Validation test:** Add roundtrip gradcheck in Phase B7 (`test_quaternion_roundtrip` with synthetic U-matrices).
3. **If precision issue arises:** Switch to `torch.float64` for the entire Stage A closure (currently float32), or use higher-precision quaternion conversion library.

### Risk 3: Ill-Conditioning with Cell/Angle DoFs

**Description:** If U-matrix, cell_logs, and angle_raws are all trainable simultaneously, the loss surface may become ill-conditioned (redundant DoFs → flat directions → slow convergence).

**Likelihood:** Medium (cell and U-matrix both parameterize A*, so they are coupled).

**Impact:** Medium (convergence may stall, but not fail catastrophically).

**Mitigation:**
1. **Phase C validation:** Test three DoF combos:
   - `U_scale_only` (U-matrix + log_scale, freeze cell/angles)
   - `U_full` (U-matrix + log_scale + cell_logs + angle_raws)
   - If `U_full` shows ill-conditioning (e.g., >2× slower convergence than `U_scale_only`), document in findings and recommend freezing cell/angles at mapping values.
2. **Hessian conditioning check (optional):** If needed, compute condition number of the Hessian approximation during LBFGS; if κ(H) > 1e6, add L2 regularization to quaternion updates.

### Risk 4: Interaction with Existing Cell+Misset Users

**Description:** Adding U-matrix mode may accidentally break the default cell+misset path (regressions in GEOMETRY-003 baseline misset behavior).

**Likelihood:** Low (branching with `if use_u_matrix_parameterization` keeps paths separate).

**Impact:** High (would break existing Stage A smokes).

**Mitigation:**
1. **Regression guard (Phase C4):** Run `test_stage_a_expansion` with U-matrix mode **OFF** (default) to ensure no regressions.
2. **Separate test (Phase C4):** Add `test_stage_a_u_matrix_parity` selector that explicitly enables `--use-u-matrix` flag.
3. **Code review:** Ensure no shared state between cell+misset and U-matrix paths (e.g., `StageAContext.q_params` is `None` when U-matrix mode is disabled).

### Risk 5: Scale-Only Variant Still Degrades

**Description:** If the 1.37e-3 strain is not the only blocker, U-matrix parameterization may still fail to achieve stable convergence (e.g., if there's a deeper simulator parity bug or loss function artifact).

**Likelihood:** Low (Phase A3 ruled out simulator bugs; Phase B1 ruled out loss artifacts).

**Impact:** High (would require escalation to TORCH-REFINE-003 or TORCH-SIMULATOR-PARITY-001).

**Mitigation:**
1. **Decision tree in Phase C2:** If `A_scale_only` (U-matrix + scale) still degrades:
   - Diagnose: Re-run Phase B1 gradient probe with U-matrix mode to check if gradients are now small (<1e4) at zero.
   - If gradients still large: Escalate to new initiative (U-matrix didn't fix the geometry gap → deeper issue).
   - If gradients small but convergence fails: Pivot to optimizer sensitivity (LR sweep, Phase B3 from TORCH-REFINE-002E).
2. **Abort trigger (from implementation.md):** If quaternion parameterization shows >1e-6 A* parity gap after Phase B, escalate to TORCH-GEOMETRY-PARITY-003 (numerical precision limits or MOSFLM A* injection bugs).

---

## Summary

**API changes:** Minimal (5 new helpers, 1 config flag, branch in closure).
**Backward compatibility:** Preserved (default path unchanged).
**Risks:** Mitigated via telemetry, validation tests, and decision trees.
**Next step:** Transition to Phase B (Implementation) with ready-for-implementation Do Now.

## Checklist Status

- [x] **A0:** Evidence synthesis — root cause confirmed
- [x] **A1:** SO(3) survey — quaternion recommended
- [x] **A2:** API design — documented above
- [x] **A3:** Risk analysis — 5 risks identified with mitigation strategies

**Phase A complete. Ready for Phase B implementation.**
