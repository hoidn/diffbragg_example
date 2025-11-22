# Phase A0: Evidence Synthesis

**Initiative:** TORCH-GEOMETRY-PARITY-002
**Date:** 2025-11-22T105837Z
**Phase:** A0 — Analysis & Design
**Task:** Evidence synthesis confirming root cause is cell+misset decomposition, not simulator/loss bugs

## Executive Summary

The 1.37e-3 symmetric strain blocking Stage A refinement convergence originates from the GEOMETRY-003 cell+misset decomposition that projects the mapping MOSFLM A* matrix onto SO(3), discarding the non-rotational strain component. This geometric encoding gap—not simulator parity bugs or loss function subtleties—creates a 24.5% χ² penalty at zero deltas and causes all DoF variants (including scale-only) to degrade instead of converge. Direct U-matrix parameterization (quaternion or SO(3) Lie algebra) is required to preserve the mapping geometry exactly.

## Causal Chain

### Root Cause
**GEOMETRY-003 decomposition cannot express mapping MOSFLM A* strain**

The current Stage A parameterization encodes crystal orientation as:
- `orientation_vec`: 3-DOF XYZ Euler angles (rotation only, SO(3))
- `cell_logs`: 3-DOF (log a, log b, log c)
- `angle_raws`: 3-DOF (bounded α, β, γ)

Baseline misset is derived via:
```
U_baseline = proper_rotation(A*_mapping · B_ideal^{-1})
```

This `proper_rotation()` projection discards any symmetric (strain) component in the U-matrix, enforcing U ∈ SO(3). When MOSFLM A* embeds a small strain (e.g., from imperfect crystal lattice or non-standard cell encoding), the projection creates a fundamentally different crystal orientation at zero deltas.

### Evidence Chain (TORCH-REFINE-002E Phases A→B→C)

**Phase A0 (Geometry Characterization):**
- Artifacts: `plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/crystal_matrix_parity.json`
- Key Results:
  - `log_u_symmetric_norm = 1.37e-3` (symmetric strain component)
  - `log_u_antisymmetric_norm = 1.37e-7` (rotation error, ~1000× smaller)
  - Reciprocal-column angle deviations ≤0.051° (a*=0.051°, b*=0.017°, c*=0.049°)
  - Singular-value ratios show ≈0.07% strain along principal axes
- **First Divergence:** The 4e-5 A* element-wise gap is **dominated by symmetric strain**, not pure rotational misalignment (antisymmetric component is negligible).

**Phase A2 (Baseline B_ideal Variants):**
- Artifacts: `plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/crystal_matrix_parity.json`
- Hypothesis H2: Baseline cell mismatch (dxtbx unit cell vs MOSFLM A* recovered cell) causes strain.
- Key Results:
  - `PathB_unitcell.log_u_symmetric_norm = 1.369e-3`
  - `PathB_recovered.log_u_symmetric_norm = 1.369e-3` (identical to 4 sig figs)
  - Recovered cell params match dxtbx cell to ~1e-6 Å and ~1e-5°
- **Conclusion:** H2 rejected — both B_ideal variants exhibit the same 1e-3 symmetric strain. The strain persists regardless of B_ideal source, proving it originates from the mapping MOSFLM A* matrix itself, not the baseline cell derivation.

**Phase B1 (Local Gradient Probe):**
- Artifacts: `plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/gradient_probe.json`
- Hypothesis H3/H4/H5: Gradients are zero at mapping zero, or optimizer artifacts cause degradation.
- Key Results:
  - χ² at zero deltas (explicit parameterization) = 2.979e6
  - **Gradients are LARGE and NON-ZERO:**
    - ∂χ²/∂(log_scale) = 4.28e5
    - ∂χ²/∂(cell_logs) magnitude = 9.82e7 (max_abs 9.79e7)
    - ∂χ²/∂(angle_raws) magnitude = 1.55e8 (max_abs 1.14e8)
    - ∂χ²/∂(orientation_vec) magnitude = 2.88e8 (max_abs 2.16e8)
- **First Divergence:** The mapping "zero point" is **far from a chi-squared local minimum** under explicit cell+misset encoding. Adam legitimately walks away because zero deltas do NOT reproduce the mapping geometry — the explicit parameterization starts at a physically different configuration (χ²_explicit ≈ 2.98e6 vs χ²_mapping ≈ 1.13e6).

**Phase A3 (Forward Model Comparison):**
- Artifacts: `plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/forward_model_comparison.json`
- Hypothesis: χ² gap originates from simulator parity bugs (interpolation, spot shape, HKL grid differences).
- Key Results:
  - χ²_mapping = 2.394e6 (MOSFLM A* injection, nanobrag_torch simulator)
  - χ²_stage_a_zero = 2.980e6 (explicit cell+misset at zero deltas, same simulator)
  - |Δχ²| = 5.856e5 (24.5% relative difference)
  - Conclusion: **differs_numerically** (NOT a simulator bug)
- **First Divergence:** Both paths use the same nanobrag_torch simulator and HKL grid; the 24.5% χ² gap arises purely from **geometry encoding differences**. The GEOMETRY-003 baseline misset + dxtbx unit cell at zero deltas produces a different effective crystal orientation than the mapping MOSFLM A* injection.

**Phase C1 (Decisive Validation):**
- Artifacts: `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/{decision.json,block_dof_results.json}`
- Decision criterion: If Phase 5 shows stable/improving convergence, accept the documented residual; otherwise escalate.
- Key Results (Phase 5 reduced scope, A_scale_only + D_full):
  - **A_scale_only:** χ² degraded 1.13M → 3.52M (3.10× worse), CC dropped 1.0 → 0.846 (stable convergence = FALSE)
  - **D_full:** χ² degraded 1.13M → 1.94M (1.71× worse), CC dropped 1.0 → 0.895 (monotonic improvement = FALSE)
- **First Divergence:** Both scale-only and full-DoF variants degrade from the mapping zero point, confirming the geometry gap blocks **all refinement paths** including the minimal scale-only variant.

### Why Not Simulator Parity or Loss Function?

1. **Simulator:** Phase A3 proves both mapping and explicit paths use nanobrag_torch with identical HKL grids, interpolation settings, and spot shape models. The 24.5% χ² gap exists purely at the geometry encoding level before any simulator differences could manifest.

2. **Loss Function:** Both paths use the same variance-weighted chi-squared loss (`Σ((I_model - I_obs)^2 / V)` per PHYSICS-LOSS-001). The denominator is detached and sigma-floored identically. Phase B1 gradients confirm the loss surface is smooth and differentiable — no NaN/Inf, no outlier dominance, no clamping artifacts.

3. **Optimizer:** Phase 4 single-step Adam and Phase 5 multi-step convergence both show degradation across all DoF variants. The gradients are massive (≈1e8) and point away from zero, proving Adam is following the loss surface correctly — the starting point is simply the wrong geometry.

## Root Cause Confirmation

**The 1.37e-3 symmetric strain cannot be expressed by the current Stage-A parameterization.**

- `orientation_vec` encodes rotation only (3-DOF SO(3) via XYZ Euler angles)
- `cell_logs` and `angle_raws` parameterize the unit cell (a, b, c, α, β, γ)
- When MOSFLM A* contains a small non-rotational strain (e.g., lattice imperfection, non-standard cell convention), the GEOMETRY-003 decomposition `U = proper_rotation(A* · B_ideal^{-1})` **projects away the strain**, leaving only the rotation component.
- At zero deltas, the explicit parameterization reconstructs: `A* = U_baseline @ B_ideal_reciprocal`, which differs from `A*_mapping` by the discarded strain tensor.
- Result: **24.5% χ² penalty at zero deltas**, massive gradients (≈2.88e8), and convergence failure for all DoF variants.

## Solution Requirements

**Direct U-matrix parameterization (TORCH-GEOMETRY-PARITY-002)**

To preserve the mapping geometry exactly:
1. **Parameterize U-matrix directly:** Use quaternion (4-param, ‖q‖=1) or SO(3) Lie algebra (3-param, exponential map) instead of XYZ Euler angles.
2. **Initialize from mapping A*:** At zero deltas, `U₀ = A*_mapping · B_ideal^{-1}` (no proper_rotation projection) → convert to quaternion q₀.
3. **Apply deltas in SO(3):** LBFGS updates quaternion q, normalized every iteration, converted to rotation matrix U, then `A* = U @ B_ideal_reciprocal`.
4. **Expected outcome:** `max_abs_diff(A*, A*_mapping) < 1e-6` at zero deltas, stable/improving convergence for scale-only and full-DoF variants.

### Why Quaternion?

| Representation | Params | Constraints | Singularities | Gradient Quality | PyTorch Ops |
|---|---|---|---|---|---|
| XYZ Euler | 3 | None | Gimbal lock near ±90° | Poor near singularities | Manual |
| Axis-angle | 3 | None | Gimbal lock near θ=π | Poor near θ=0, π | Manual |
| Quaternion | 4 | ‖q‖=1 | None (global) | Smooth | scipy + torch conversion |
| Lie algebra so(3) | 3 | None | Local chart only | Smooth (local) | Manual exponential map |

**Recommendation:** Quaternion (4-param) for numerical stability, no gimbal lock, and straightforward normalization constraint.

## Artifacts Cross-Reference

- **Phase A0 strain decomposition:** `plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/crystal_matrix_parity.json`
- **Phase A2 B_ideal variants:** `plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/crystal_matrix_parity.json`
- **Phase B1 gradient probe:** `plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/gradient_probe.json`
- **Phase A3 forward comparison:** `plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/forward_model_comparison.json`
- **Phase C1 final validation:** `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/{decision.json,block_dof_results.json}`
- **Escalation decision:** `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/decision.json`

## Next Steps (Phase A Checklist)

- [x] **A0:** Evidence synthesis — root cause confirmed (this document)
- [ ] **A1:** SO(3) parameterization survey (quaternion vs axis-angle vs Lie algebra)
- [ ] **A2:** API design (minimal changes to Stage A code)
- [ ] **A3:** Risk analysis (quaternion drift, numerical precision, ill-conditioning)

Once Phase A completes, transition to Phase B (Implementation) with quaternion-based U-matrix direct parameterization.
