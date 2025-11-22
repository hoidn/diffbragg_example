# Phase A Review — Geometry Characterization Complete

**Date:** 2025-11-22T094500Z
**Initiative:** TORCH-REFINE-002E
**Phase:** A → B transition

## Summary

Phase A diagnostics (A0, A2) have definitively characterized the A* parity gap and ruled out the baseline cell mismatch hypothesis. We now have sufficient evidence to transition to Phase B (Gradient & Optimizer Diagnosis).

## Phase A Checklist Status

- [x] **A0: Probe extension** — Completed 2025-11-22T090505Z
  - Extended `probe_crystal_matrix_parity.py` with eigenvalue/SVD decomposition, symmetric/antisymmetric logm(U_error) splits, reciprocal-column norm/angle comparisons
  - **Key finding:** `log_u_symmetric_norm = 1.369e-3` (≈1000× larger than antisymmetric `1.37e-7`)
  - **Conclusion:** The 4e-5 A* gap is **dominated by symmetric strain**, not pure rotation
  - Artifacts: `plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/crystal_matrix_parity.json`

- [x] **A2: Baseline B_ideal variants** — Completed 2025-11-22T091200Z
  - Implemented `recover_cell_from_a_star()` using cctbx.uctbx to derive real-space cell params from MOSFLM A*
  - Extended `derive_robust_misset()` with `b_ideal_override` parameter
  - Compared two Path-B variants: (a) dxtbx unit-cell B_ideal, (b) MOSFLM A* recovered cell B_ideal
  - **Key finding:** Both variants show **identical** `log_u_symmetric_norm = 1.369e-3` (4 sig figs)
  - Recovered cell params match dxtbx to ~1e-6 Å and ~1e-5° (a=27.3642109 vs 27.3642101, α=88.672307° vs 88.672306°)
  - **Conclusion:** H2 (baseline cell mismatch) is **NOT** the root cause; the strain persists regardless of B_ideal source
  - Artifacts: `plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/crystal_matrix_parity.json`

- [ ] **A1: Multi-config sweep** — Deferred (low ROI given A0/A2 results)
  - Not required to proceed; strain is consistent across variants

- [ ] **A3: Mapping forward vs Stage-A configs** — Deferred pending Phase B results
  - May revisit if Phase B reveals unexpected gradient behavior

## Synthesis: What We Know

### Geometry Parity Gap (Confirmed)
- **Magnitude:** `max_abs_diff ≈ 4.02e-5` (A* matrices differ by ~40 ppm element-wise)
- **Character:** Dominated by **symmetric strain** (log_u_symmetric_norm ≈ 1.4e-3)
  - Pure rotation component negligible (log_u_antisymmetric_norm ≈ 1.4e-7)
  - Reciprocal column angle deviations: a* 0.051°, b* 0.017°, c* 0.049°
  - Singular-value ratios show ≈0.07% strain along principal axes
- **Source:** Intrinsic to mapping MOSFLM A* injection vs explicit cell parameterization
  - NOT due to baseline cell mismatch (H2 ruled out)
  - Likely a physics/convention gap in MOSFLM path or non-standard cell encoding

### Optimizer Behavior (From TOOLING-VIS-001)
All Adam DoF combinations degrade performance from the mapping zero point:
- **A_scale_only:** χ² 1.13M → 3.52M (+210%), CC 1.0 → 0.846 (LR=1e-4, 10 steps)
- **B_scale_plus_cell:** χ² 1.13M → 3.67M (+224%), CC 1.0 → 0.844
- **C_scale_plus_orientation:** χ² 1.13M → 1.44M (+27%), CC 1.0 → 0.890
- **D_full:** χ² 1.13M → 2.70M (+138%), CC 1.0 → 0.881

**Critical observation:** Even **scale-only** optimization degrades the fit, despite being the "simplest" DoF. This suggests:
1. Either the gradient ∂χ²/∂(log_scale) is non-zero and pointing the wrong direction at the zero point, OR
2. The learning rate (1e-4) and step count (10) are too aggressive for this landscape

## Open Questions for Phase B

1. **Is the gradient truly zero at the mapping zero point?**
   - If ∂χ²/∂θ ≠ 0 for any DoF at the zero point, that violates the mapping spec expectation
   - If ∂χ²/∂(log_scale) > 0, Adam legitimately walks away—but WHY is it positive?

2. **What is the actual scale optimum?**
   - Does a closed-form α* exist that minimizes χ² with geometry frozen?
   - How does α* compare to `global_scale_hint` and `exp(log_scale=0)`?

3. **Are outlier ROIs dominating the gradient?**
   - Could a small subset of ROIs with interpolation/clipping artifacts drive global CC degradation?

4. **Is the loss parity perfect?**
   - Do mapping diagnostics (`simulate_forward_once`) and Stage-A (`_compute_variance_weighted_loss`) compute **identical** χ² at the zero point?

## Transition to Phase B

**Recommendation:** Proceed to **Phase B1 (Local gradient probe)** to answer Q1 directly.

**Rationale:**
- Phase A has characterized the geometry gap (strain, not rotation; not fixable via B_ideal recovery)
- But geometry gap magnitude (~1e-3 strain, ~4e-5 A* element-wise) may or may not explain the optimizer divergence
- Before attempting geometry fixes (Branch G) or parameterization changes (Branch P), we need to know whether the gradients are zero/near-zero or systematically biased

**Next Artifact:** Phase B1 gradient probe results under `plans/active/TORCH-REFINE-002E/reports/<next_timestamp>/gradient_probe.json`

## Hypotheses Tracker

| ID | Hypothesis | Status | Evidence |
|----|-----------|---------|----------|
| H1 | Residual strain (not pure rotation) | **Confirmed** | A0: log_u_symmetric_norm ≈ 1.4e-3 >> log_u_antisymmetric_norm ≈ 1.4e-7 |
| H2 | Baseline cell mismatch | **Rejected** | A2: PathB_unitcell and PathB_recovered show identical strain (1.369e-3) |
| H3 | Scale zero-point mismatch | Pending | B1/B2 will test |
| H4 | Gradient dominated by outliers | Pending | B4 will test |
| H5 | Loss/variance subtlety | Pending | B5 will test |

## References
- Phase A0 artifacts: `plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/`
- Phase A2 artifacts: `plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/`
- Adam debug: `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam_debug/20251121T234215Z/block_dof_results.json`
- Spec: `docs/spec-db-workflow.md` §Stage A (mapping zero-point invariant)
- Finding: `docs/findings.md` GEOMETRY-003
