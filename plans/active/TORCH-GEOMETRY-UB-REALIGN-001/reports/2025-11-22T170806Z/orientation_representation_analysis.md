# Orientation Representation Analysis

## Purpose
Compare three candidate representations for incremental orientation parameterization (ΔR) to select the optimal approach for TORCH-GEOMETRY-UB-REALIGN-001.

## Candidates

### Option 1: Quaternion-Based ΔR

**Representation:**
- 4-DOF unit quaternion `q_delta = [w, x, y, z]` with `||q_delta|| = 1`.
- Convert to rotation matrix: `ΔR = quaternion_to_matrix(q_delta / ||q_delta||)`.
- Apply: `U(params) = ΔR @ U₀`.

**Pros:**
- ✓ Aligns with spec normative clause "orientation (quaternion → XYZ)" (spec-db-workflow.md:36).
- ✓ No singularities (unlike Euler angles which suffer gimbal lock).
- ✓ Proven viable in CONVERGENCE-001 (chi² drift +0.0083%, CC≈1.0 over 10 steps with bypass fix).
- ✓ Compact 4-DOF representation for 3-DOF rotation (over-parameterized but well-conditioned).
- ✓ Smooth gradient flow on S³ manifold (with proper normalization).

**Cons:**
- ✗ Requires normalization constraint: `||q|| = 1` (either via explicit division or Riemannian optimizer).
- ✗ Code path divergence risk if parameter reconstruction differs from MOSFLM injection (mitigated by zero-check bypass per CONVERGENCE-001).
- ✗ Conversion to Euler XYZ needed for nanobrag_torch `misset_deg` injection (adds complexity).
- ✗ Optimizer may drift from unit sphere without periodic re-normalization (standard Adam doesn't respect manifold constraint).

**Spec Alignment:**
- **Spec-db-workflow.md:36:** "orientation (quaternion → XYZ)" — **Direct match** ✓
- **Spec-db-core.md:59:** "small rotation ΔR(params)" — **Satisfied** ✓
- **Spec-db-runtime.md:13:** Differentiability — **Satisfied** (quaternion ops are differentiable) ✓

**Implementation Complexity:**
- Medium (requires quaternion-to-matrix and quaternion-to-Euler conversion functions).
- Existing code in `dbex/nanobrag_bridge.py` uses scipy.spatial.transform.Rotation (proven in PARITY-002).

**Risk Assessment:**
- **Code path divergence:** Medium risk (CONVERGENCE-001 showed diagnostic script issue; mitigated by bypass pattern).
- **Gradient pathology:** Low risk (CONVERGENCE-001 proved stable convergence with bypass fix).
- **API mismatch:** Low risk (conversion to Euler XYZ is straightforward).

**Recommendation Score:** ★★★★☆ (4/5 — Best spec alignment, proven approach, minor complexity trade-off)

---

### Option 2: Euler Angle-Based ΔR

**Representation:**
- 3-DOF Euler angles `(δφ_x, δφ_y, δφ_z)` in radians.
- Convert to rotation matrix: `ΔR = R_z(δφ_z) @ R_y(δφ_y) @ R_x(δφ_x)` (ZYX extrinsic convention).
- Apply: `U(params) = ΔR @ U₀`.

**Pros:**
- ✓ Simpler implementation (no normalization constraint).
- ✓ Direct 3-DOF parameterization (minimal DOF for 3D rotation).
- ✓ Proven in GEOMETRY-002 finding (Euler inversion formula documented).
- ✓ Matches nanobrag_torch `misset_deg` API directly (XYZ extrinsic) — no conversion needed.
- ✓ No over-parameterization (exact 3 DOF).

**Cons:**
- ✗ Gimbal lock for large rotations (singularity at β = ±90°).
  - **Mitigation:** "Small rotation" assumption (spec-db-core.md:59) — refinement should stay near zero deltas, avoiding singularity.
- ✗ Does NOT align with spec normative clause "quaternion → XYZ" (spec-db-workflow.md:36).
  - **Interpretation issue:** Spec says "quaternion → XYZ" but may mean "use quaternions internally, convert to XYZ for API". Euler angles skip the quaternion step.
- ✗ Less smooth gradient flow near gimbal lock (gradient magnitudes become unbalanced).

**Spec Alignment:**
- **Spec-db-workflow.md:36:** "orientation (quaternion → XYZ)" — **Weak match** (uses XYZ directly, skips quaternion) ⚠️
- **Spec-db-core.md:59:** "small rotation ΔR(params)" — **Satisfied** ✓
- **Spec-db-runtime.md:13:** Differentiability — **Satisfied** (trigonometric ops are differentiable) ✓

**Implementation Complexity:**
- Low (Euler-to-matrix conversion is standard PyTorch ops).
- No external libraries needed.

**Risk Assessment:**
- **Gimbal lock:** Medium risk (mitigated by small-rotation assumption, but risk increases if refinement explores large deltas).
- **Spec non-compliance:** High risk (spec explicitly mentions quaternions; using Euler angles may violate normative clause).
- **API match:** Low risk (perfect match with nanobrag_torch `misset_deg`).

**Recommendation Score:** ★★★☆☆ (3/5 — Simpler but weaker spec alignment, gimbal lock risk)

---

### Option 3: Axis-Angle Representation

**Representation:**
- 3-DOF rotation vector `r = θ * n` where `n` is unit axis, `θ` is angle in radians.
- Convert to rotation matrix: `ΔR = rodrigues_formula(r)` or `axis_angle_to_matrix(r)`.
- Apply: `U(params) = ΔR @ U₀`.

**Pros:**
- ✓ Compact 3-DOF representation (minimal DOF).
- ✓ No gimbal lock (well-defined for all rotations).
- ✓ Well-suited for small rotations (r ≈ [ε_x, ε_y, ε_z] for small angles).
- ✓ Smooth gradient flow (no normalization constraint like quaternions, no singularity like Euler).

**Cons:**
- ✗ Does NOT align with spec normative clause "quaternion → XYZ" (spec-db-workflow.md:36).
- ✗ Less common in crystallography APIs (may not match nanobrag_torch conventions).
- ✗ Requires conversion to Euler XYZ for nanobrag_torch `misset_deg` injection (similar complexity to quaternion).
- ✗ No proven usage in DBEX codebase (unlike quaternions in PARITY-002 or Euler in GEOMETRY-002).

**Spec Alignment:**
- **Spec-db-workflow.md:36:** "orientation (quaternion → XYZ)" — **No match** ✗
- **Spec-db-core.md:59:** "small rotation ΔR(params)" — **Satisfied** ✓
- **Spec-db-runtime.md:13:** Differentiability — **Satisfied** (Rodrigues formula is differentiable) ✓

**Implementation Complexity:**
- Medium (Rodrigues formula + axis-angle-to-Euler conversion).
- Less mature tooling in PyTorch ecosystem compared to quaternions/Euler.

**Risk Assessment:**
- **Spec non-compliance:** High risk (spec explicitly mentions quaternions; axis-angle is not mentioned).
- **API mismatch:** Medium risk (requires conversion to Euler XYZ).
- **Novelty risk:** Medium risk (no prior usage in DBEX, untested in CONVERGENCE-001-like scenarios).

**Recommendation Score:** ★★☆☆☆ (2/5 — Elegant math but poor spec alignment and untested)

---

## Comparison Matrix

| Criterion | Quaternion | Euler | Axis-Angle |
|-----------|------------|-------|------------|
| **Spec alignment (spec-db-workflow.md:36)** | ✓ Direct match | ⚠️ Weak (XYZ only) | ✗ No match |
| **DOF efficiency** | 4 (over-parameterized) | 3 (minimal) | 3 (minimal) |
| **Singularities** | None | Gimbal lock (β=±90°) | None |
| **Gradient smoothness** | High (with normalization) | Medium (near gimbal) | High |
| **API compatibility (nanobrag_torch)** | Requires conversion | Direct match | Requires conversion |
| **DBEX precedent** | PARITY-002, CONVERGENCE-001 | GEOMETRY-002 | None |
| **Implementation complexity** | Medium | Low | Medium |
| **Risk level** | Low (proven) | Medium (gimbal lock) | High (untested) |

---

## Decision: Quaternion-Based ΔR (Option 1)

### Rationale

1. **Normative Spec Compliance:**
   - Spec-db-workflow.md:36 explicitly says "orientation (quaternion → XYZ)".
   - This is a **normative** requirement per spec structure.
   - Choosing quaternions ensures literal compliance.

2. **Proven Viability:**
   - CONVERGENCE-001 demonstrated that quaternion U-matrix achieves stable convergence (chi² drift +0.0083%, CC≈1.0) with bypass fix.
   - Code path divergence risk is known and mitigated.

3. **Robustness:**
   - No singularities (unlike Euler gimbal lock).
   - Smooth gradient flow on S³ manifold.

4. **Forward Compatibility:**
   - If nanobrag_torch ExperimentModel moves to quaternion-based parameterization in future, our design is already aligned.
   - Conversion to Euler XYZ is a compatibility layer, not a design limitation.

5. **Small-Rotation Regime:**
   - For refinement near mapping zero point, quaternion ≈ [1, ε_x, ε_y, ε_z] is numerically stable.
   - Over-parameterization (4 DOF for 3-DOF rotation) is not a practical issue; normalization is cheap.

### Implementation Notes

- **Normalization Strategy:** Use explicit division `q / ||q||` in forward pass (differentiable).
- **Optimizer:** Standard Adam with periodic re-normalization (every N steps) OR Riemannian optimizer (tangent space updates).
- **Conversion to Euler:** Use `scipy.spatial.transform.Rotation` or PyTorch geometric library (defer choice to Phase B).
- **Zero-Check Bypass:** Implement detection for all-zero deltas (atol=1e-9) in diagnostic tooling per CONVERGENCE-001 pattern.

### Rejected Alternatives

- **Euler angles:** Simpler but violates normative spec clause "quaternion → XYZ"; gimbal lock risk; lacks CONVERGENCE-001 validation.
- **Axis-angle:** Elegant but no spec alignment, no DBEX precedent, untested in refinement context.

---

## Next Steps (Phase B)

1. Implement `quaternion_to_matrix(q)` helper in `dbex/nanobrag_bridge.py` (or `dbex/geometry.py`).
2. Implement `quaternion_to_euler_xyz(q)` helper for nanobrag_torch `misset_deg` injection.
3. Add unit tests for:
   - Identity quaternion `[1,0,0,0]` → ΔR = I.
   - Orthogonality: `ΔR.T @ ΔR = I`.
   - Determinant: `det(ΔR) = 1`.
4. Wire into Stage A closure with zero-check bypass.

---

## References

- `docs/spec-db-workflow.md:36` — Normative "quaternion → XYZ" clause
- `docs/spec-db-core.md:59` — Incremental parameterization "small rotation ΔR(params)"
- `docs/findings.md:7` — GEOMETRY-002 (Euler inversion formula)
- `docs/findings.md:65` — CONVERGENCE-001 (quaternion convergence validation)
- `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T112058Z/phase_b_regression_bug_report.md` — Quaternion implementation details

---

**Recommendation: Use Quaternion-Based ΔR for TORCH-GEOMETRY-UB-REALIGN-001.**
