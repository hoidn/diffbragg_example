# Phase A1: SO(3) Parameterization Survey

**Initiative:** TORCH-GEOMETRY-PARITY-002
**Date:** 2025-11-22T105837Z
**Phase:** A1 — Analysis & Design
**Task:** Survey SO(3) representations and recommend one for U-matrix parameterization

## Candidates

### 1. Quaternion (4-param, unit norm)

**Description:** Represent rotation as unit quaternion q = [w, x, y, z] with ‖q‖ = 1.

**Pros:**
- No gimbal lock (global parameterization)
- Smooth gradient flow everywhere
- Straightforward constraint: normalize every iteration
- PyTorch3D/scipy provide `matrix_to_quaternion` and `quaternion_to_matrix`
- Double coverage (q and -q represent same rotation) easily handled

**Cons:**
- 4 parameters for 3-DOF object (redundant, but constraint is simple)
- Normalization drift during LBFGS updates (mitigated by per-closure normalization)

**Gradient Quality:** Excellent — smooth everywhere, no singularities.

**PyTorch Ops:** Available via `scipy.spatial.transform.Rotation` + torch conversion, or PyTorch3D.

**Recommendation:** **Preferred** for numerical stability and gradient quality.

---

### 2. Axis-Angle (3-param)

**Description:** Represent rotation as axis vector n (unit length) and angle θ: rotation = exp(θ * n̂).

**Pros:**
- Compact (3 parameters exactly for 3-DOF)
- Geometric intuition (axis + magnitude)

**Cons:**
- **Gimbal lock near θ=π:** Axis direction becomes ambiguous at ±180°
- **Singularity near θ=0:** Axis undefined for identity rotation
- Normalization required for axis (unit length constraint)
- More complex to convert to/from matrices

**Gradient Quality:** Poor near θ=0 and θ=π (singularities).

**PyTorch Ops:** Manual implementation of Rodrigues' formula.

**Recommendation:** **Not recommended** due to singularities blocking convergence near identity and ±π.

---

### 3. Lie Algebra so(3) Exponential Map (3-param)

**Description:** Represent rotation as ω ∈ ℝ³ (rotation vector), rotation = exp(ω̂) where ω̂ is the skew-symmetric matrix.

**Pros:**
- Compact (3 parameters for 3-DOF)
- Local chart around identity (good for small perturbations)
- Smooth gradients in the local neighborhood

**Cons:**
- **Local chart only:** For large rotations (‖ω‖ > π), wrapping/ambiguity issues
- **Singularities at ‖ω‖ = 2πk:** Exponential map is not one-to-one globally
- Matrix exponential `exp(ω̂)` requires Rodrigues or series expansion (more compute)

**Gradient Quality:** Good locally, poor globally (wrapping artifacts).

**PyTorch Ops:** Manual Rodrigues formula or scipy conversions.

**Recommendation:** **Not recommended** for global optimization (LBFGS may take large steps outside the local chart).

---

## Recommendation: Quaternion (4-param)

**Rationale:**
1. **No singularities:** Smooth everywhere, no gimbal lock or wrapping issues.
2. **Simple constraint:** Normalize quaternion every closure call (`q_norm = q / torch.norm(q)`).
3. **Gradient quality:** Excellent — LBFGS can take large steps without hitting singularities.
4. **Proven tooling:** scipy `Rotation.from_matrix` / `as_quat` + torch tensor conversions are robust.
5. **Numerical stability:** Double precision (float64) for initialization ensures roundtrip error < 1e-8.

**Implementation sketch:**
```python
# Initialization (from mapping MOSFLM A*)
U_0 = A_star_mapping @ np.linalg.inv(B_ideal_reciprocal)  # 3x3, no projection
q_0 = Rotation.from_matrix(U_0).as_quat()  # [x, y, z, w] scipy convention
q_params = torch.tensor(q_0, dtype=torch.float64, requires_grad=True)

# LBFGS closure
def closure():
    q_norm = q_params / torch.norm(q_params)  # Enforce ‖q‖=1
    U = quaternion_to_matrix(q_norm)  # 3x3 rotation matrix
    A_star_new = U @ B_ideal_reciprocal_torch  # Update crystal A*
    # ... forward pass, loss, backward ...
    return loss
```

## Alternatives (Future Work)

If quaternion normalization drift becomes a problem (e.g., LBFGS takes huge steps and ‖q‖ drifts >1e-2 per iteration):
1. Switch to **projected gradient descent** (project onto unit sphere after each step).
2. Reparameterize as **stereographic projection** (3-param local chart, smooth near identity).
3. Use **constrained optimizer** (scipy L-BFGS-B with ‖q‖=1 constraint).

For now, per-closure normalization is sufficient and matches the REFINE-001 pattern (scale warm-start + log-space bounds).

## Next Steps

- [x] **A1:** SO(3) survey — quaternion recommended
- [ ] **A2:** API design (minimal code changes for quaternion path)
- [ ] **A3:** Risk analysis (normalization drift, numerical precision)
