# Phase A0: Evidence Synthesis — det(U)≠1 Investigation

**Initiative:** TORCH-GEOMETRY-PARITY-003
**Timestamp:** 2025-11-22T121500Z
**Phase:** A0 (Evidence Synthesis)

## Summary

Investigation into root cause of `det(U₀)=1.000557` discovered when deriving U-matrix from mapping MOSFLM A* via canonical relationship `U = A* @ inv(B_ideal)`. This 0.06% volume offset blocks Stage A convergence despite achieving perfect raw matrix parity.

## Evidence from PARITY-002 Attempts

### Phase C1: Raw U-Matrix Parity (2025-11-22T113409Z)

From `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/phase_c1_parity_failure_diagnosis.md`:

**Raw U-matrix extraction:**
- Derived `U₀ = mosflm_a_star @ np.linalg.inv(b_ideal_reciprocal)`
- Element-wise parity: `max_abs_diff = 3.5e-18` (essentially perfect, within floating-point roundoff)
- **Determinant:** `det(U₀) = 1.000557` (0.0557% deviation from unity)
- **Volume offset:** ~0.06% isotropic expansion

**Quaternion projection impact:**
- After `scipy.spatial.transform.Rotation.from_matrix(U₀)` → `.as_matrix()` (SO(3) projection):
  - Parity degraded to `max_abs_diff ≈ 4e-05` (quaternion variant)
  - Quaternion normalization discards the 0.06% volume scaling component
  - Projected quaternion achieves perfect orthonormality (`det=1.0` exactly)

### Phase C2/C3: Convergence Catastrophe (2025-11-22T120500Z)

From `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/phase_c2_c3_decision.json`:

**Zero-point validation (Phase C1):**
- Perfect correlation: `CC = 0.9999999843` (essentially 1.0)
- Chi-squared match: `chi²_rel_diff = -0.017%` (well within tolerance)
- Pixel-wise residuals: `max_abs_diff = 85.14 photons` (acceptable)

**Adam optimization failure (Phase C2/C3):**
- **A_scale_only variant:**
  - χ² increased 1257× (1.13M → 1.43B, drift = **+125687%**)
  - Median CC collapsed from 0.9999999843 to **-0.045** (negative correlation)
  - Conclusion: Catastrophic failure

- **D_full variant:**
  - χ² increased 1258× (1.13M → 1.43B, drift = **+125799%**)
  - Median CC collapsed to **-0.041**
  - Conclusion: Similar catastrophic failure

**Root Cause Hypothesis (from PARITY-002 decision):**
> "Quaternion normalization + scipy Rotation conversion creates pathological gradients; 0.06% volume scaling (det(U)≠1) may interact badly with refinement dynamics."

The SO(3) constraint (enforced via quaternion unit norm) is **incompatible** with the mapping geometry, which contains a small volume scaling component. Discarding this scaling at initialization creates a 4e-05 parity gap, and during optimization the gradients drive the solution toward configurations that minimize chi-squared *subject to the SO(3) constraint*, which diverges catastrophically from the physical crystal orientation.

## Key Question

**Why is det(U)≠1, and what does the 0.06% volume offset represent?**

Three hypotheses:

1. **H1: dxtbx A*/cell inconsistency (DXTBX-001 extension)**
   - `crystal.get_A()` may embed an isotropic scale factor not reflected in `crystal.get_unit_cell()` parameters
   - Possible calibration artifact from upstream MOSFLM/DIALS processing
   - Test via **Phase A1 audit:** Compare `det(A*)` vs `1/det(B_ideal)` where `B_ideal` is computed from dxtbx unit cell

2. **H2: Physical volume scaling**
   - Crystal underwent thermal expansion, pressure change, or radiation damage relative to reference cell
   - Small isotropic strain is physically real but not representable as pure rotation (U ∈ SO(3))
   - Test via **Phase A2 metadata review:** Check experiment JSON for environmental conditions, processing history

3. **H3: Numerical precision in B_ideal derivation**
   - `cctbx.uctbx.unit_cell(...).fractionalization_matrix()` roundtrip may introduce systematic errors
   - Test via **Phase A3 validation:** Roundtrip `cell → B_ideal → cell'` and measure error; compare against `crystal.get_B()` if available

## Escalation Context

This initiative was escalated from **TORCH-GEOMETRY-PARITY-002** after quaternion U-matrix parameterization (pure SO(3) approach) achieved perfect zero-point parity but catastrophically failed convergence tests. The 0.06% det offset is the critical blocker preventing Stage A refinement from converging on the mapping geometry.

## Next Actions (Phase A1-A4)

1. **A1: dxtbx A*/cell Audit** (PRIMARY) — Implement analysis script to extract A*, cell, compute B_ideal, validate decomposition identity `A* ≈ U @ B_ideal`, and check for dxtbx `get_B()` API
2. **A2: Metadata Review** — Inspect `sp.proc/refGeom.expt` for calibration flags, MOSFLM/DIALS parameters, environmental metadata
3. **A3: Numerical Precision Test** — Validate cctbx roundtrip stability and det(U) computation precision
4. **A4: Hypothesis Decision** — Synthesize evidence into root cause determination (H1, H2, H3, or combination) and recommend Phase B parameterization approach

---

**Artifacts Path:** `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/`
