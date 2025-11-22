# Phase A0: Evidence Synthesis — Quaternion U-Matrix Convergence Failure

**Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
**Phase:** A0 (Evidence Collection & Synthesis)
**Date:** 2025-11-22
**Artifacts Source:** PARITY-003 Phase C2 (2025-11-22T130000Z)

## Executive Summary

Quaternion U-matrix parameterization achieves **perfect parity** (<1e-17 max_abs_diff) at zero deltas but **catastrophically fails** during Adam optimization: χ² explodes 1257× (1.13M → 1.43B) and median ROI CC collapses from 1.0 to -0.045 after 10 steps with LR=1e-4. This reproduces PARITY-002 failure exactly, proving the problem is **NOT file-specific** (canonical refGeom.expt, det(U)=1.0 per dxtbx audit). Root cause is a convergence pathology (optimizer/loss/gradient interaction), not geometry encoding.

---

## Failure Signature

### PARITY-003 Phase C2 Metrics (A_scale_only variant)

**Source:** `parity_003_phase_c2.json`, `parity_003_dof_results.json`

| Metric | Initial | Final (Step 10) | Change |
|--------|---------|-----------------|--------|
| Chi-squared | 1,133,421 | 1,425,250,048 | **+125,648%** (1257× explosion) |
| Median ROI CC | 0.9999999843 | -0.044678 | **Collapse to negative correlation** |
| Optimizer | Adam, LR=1e-4 | 10 steps | Scale DOF only |

**Failure Mode Classification:** `cc_collapse` (correlation coefficient catastrophic degradation)

**Convergence Success:** FALSE

---

## Known Constraints

### 1. Parity Status: PERFECT
- **Max absolute difference in A* elements:** 3.469e-18 (machine epsilon, essentially zero)
- **Conclusion:** Quaternion → matrix → A* reconstruction is numerically correct at zero deltas
- **Implication:** Failure is NOT a parity/encoding bug; geometry representation is valid

### 2. File Independence: CONFIRMED
- **Test asset:** Canonical `refGeom.expt` (repository standard, no file-specific anomalies)
- **det(U) per dxtbx audit (PARITY-003 Phase A1):** 1.0 (within machine precision 1e-16)
- **det(U) per MOSFLM reconstruction:** 1.000565 (0.06% offset due to nanobrag_torch/dxtbx parity artifact, NOT a convergence blocker)
- **Conclusion:** Failure reproduces with clean geometry; not tied to specific experiment file quirks

### 3. Determinant Analysis
- The 0.06% det(U) offset between nanobrag_torch MOSFLM path and dxtbx direct computation is a **parity artifact**, not a convergence blocker
- PARITY-003 Phase A proved det(U)=1.0 per dxtbx (the authoritative source)
- Perfect parity (<1e-17) at zero deltas confirms the quaternion normalization preserves SO(3) constraint correctly
- **Implication:** det(U)≠1 hypothesis is REJECTED; convergence failure has a different root cause

---

## Relevant Findings Cross-Reference

### REFINE-001: LBFGS Scale Warm-Start & NaN/Inf Guards
**Relevance to CONVERGENCE-001:** Medium

- **Summary:** Stage A LBFGS must warm-start `log_scale` from calibration hint (~e4) and bound it before `torch.exp(log_scale)` to prevent explosion (~1.5e39) and NaN/Inf gradient trips
- **Applicability:** A_scale_only variant trains **only** scale DOF; if quaternion U-matrix geometry introduces numerical instability in the forward model (affecting I_model variance), the variance-weighted loss denominator could amplify scale gradients similarly
- **Action:** Phase A telemetry MUST log `||∂L/∂log_scale||` alongside quaternion gradients to check if scale gradient explosion correlates with CC collapse

### PHYSICS-LOSS-002: Variance-Weighted Chi-Squared Sigma-Floor Guard
**Relevance to CONVERGENCE-001:** High

- **Summary:** Variance-weighted chi-squared must enforce `V = max(I_model + sigma_readout^2, sigma_floor^2)` to prevent infinite weights; without the floor, Stage B gradients hit NaN/Inf on GPU
- **Applicability:** **Directly relevant**—quaternion U-matrix may produce forward model outputs (I_model) with different variance structure than cell+misset path. If I_model values approach zero or exhibit pathological distributions, the variance denominator could collapse → extreme weights → gradient explosion
- **Action:** Phase A telemetry MUST capture variance component histograms (I_model, V_denom, clamp fraction) per step and check for:
  - V_denom approaching zero (would cause `(residual)^2 / V_denom → inf`)
  - Clamp fraction near 1.0 (would indicate sigma_floor dominates, possibly masking numerical issues)
  - I_model distribution anomalies (negative values, NaN, extreme outliers)

### GRADIENT-001: Autograd Graph Preservation & Crystal Overrides
**Relevance to CONVERGENCE-001:** Medium

- **Summary:** Production refinement must avoid `.item()`/`.numpy()` on differentiable tensors; use `crystal_overrides` dict to preserve autograd graphs. When overrides are provided, `create_crystal_config` must NOT inject `mosflm_a/b/c_star` from base crystal, else gradients are blocked
- **Applicability:** Quaternion U-matrix path bypasses cell+misset parameterization and directly injects A* via `mosflm_a/b/c_star` overrides (or equivalent). If autograd graph is broken during quaternion normalization (`q / ||q||`) or `quaternion_to_matrix` conversion (scipy.spatial.transform.Rotation), gradients would be corrupted
- **Action:** Phase A telemetry MUST validate gradients are non-NaN and finite at every step. Consider finite-difference gradient check at step 0 to verify autograd correctness

---

## Hypothesis Space

Based on PARITY-003 escalation decision and implementation.md diagnostic protocol, four primary hypotheses for convergence failure:

### H1: Adam Hyperparameters Incompatible with Quaternion Gradients
- **Mechanism:** Quaternion gradients live on S³ unit sphere tangent space; Euclidean Adam momentum may violate ||q||=1 constraint between normalization steps, causing drift off-manifold
- **Evidence Gap:** No per-step quaternion norm (||q||) or gradient norm (||∂L/∂q||) data from PARITY-003 Phase C2
- **Test:** Phase A1 telemetry captures `||q||` and `||∂L/∂q||` per step; Phase B tests LBFGS (no momentum), lower LR (1e-5, 1e-6), gradient clipping

### H2: Variance-Weighted Loss Instability with Quaternion U-Matrix
- **Mechanism:** Quaternion parameterization may produce I_model distributions that interact poorly with variance denominator (V_denom approaching zero, sigma_floor clamping, outlier pixels driving loss)
- **Evidence Gap:** No variance component histograms or clamp fraction data from PARITY-003 Phase C2
- **Test:** Phase A1 telemetry captures I_model, V_denom, clamp fraction, weighted residual histograms per step; check for pathological distributions at first divergence

### H3: Gradient Pathology (NaN/Inf/Exploding Magnitudes)
- **Mechanism:** Quaternion normalization `q / ||q||` may produce numerical instabilities if ||q|| approaches zero during backprop; `quaternion_to_matrix` matrix operations may amplify errors
- **Evidence Gap:** No gradient norm or NaN/inf checks from PARITY-003 Phase C2
- **Test:** Phase A1 telemetry logs gradient norms (global + per-DOF), checks for NaN/inf every step; Phase A finite-difference validation at step 0 to verify autograd correctness

### H4: Quaternion Constraint Handling (Normalization Frequency)
- **Mechanism:** Current implementation normalizes quaternion once per forward pass; if Adam updates violate ||q||=1 between normalizations, gradients may point off-manifold (Riemannian optimization needed)
- **Evidence Gap:** No ||q|| tracking or normalization event logging from PARITY-003 Phase C2
- **Test:** Phase A1 telemetry logs ||q|| before/after normalization; compare gradient magnitudes pre/post normalization; Phase B tests Riemannian Adam or more frequent normalization

---

## Recommended Next Steps

### Phase A1: Instrumentation (Immediate)
Extend `build_stage_a_lbfgs_closure` (U-matrix branch, dbex/nanobrag_refinement.py:~950-1150) with per-step telemetry:

**Parameters to log:**
- `q_params` (4-element quaternion tensor)
- `log_scale` (scalar)
- `||q||` (quaternion norm, should stay ≈1.0 if constraint is maintained)

**Gradients to log:**
- `||∂L/∂q||` (L2 norm of quaternion gradient vector)
- `||∂L/∂log_scale||` (absolute value, scalar gradient)
- Element-wise max/min gradients for quaternion (identify if specific components explode)
- NaN/inf flags (boolean checks)

**Loss components to log:**
- Total chi-squared (variance-weighted)
- Variance components:
  - `I_model` histogram (min/median/max/std)
  - `V_denom = max(I_model + sigma_readout^2, sigma_floor^2)` histogram
  - Clamp fraction (fraction of pixels where sigma_floor dominates)
- Weighted residuals `(I_target - I_model)^2 / V_denom` histogram

**Forward metrics (optional, if low overhead):**
- Median ROI CC (if available without full ROI scoring)

**Emission format:** JSON per step to `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/<timestamp>/telemetry_step_{0..9}.json`

**Constraints:**
- Observation only (no mutation of production logic)
- Run on CPU (--device cpu) to avoid CUDA sync overhead
- JSON only (no visualization overhead)

### Phase A2: Execute Instrumented Run
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --phases 5 --dof-variants A_scale_only \
  --adam-steps 10 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/<timestamp>/
```

### Phase A3: First Divergence Analysis
Identify first step where:
- χ² increases >10% from initial, OR
- CC drops <0.95, OR
- Gradients explode (norm >1e10) or vanish (norm <1e-10), OR
- NaN/inf appears in loss or gradients

Document parameter/gradient state at first divergence in `phase_a_first_divergence.md`

### Phase A4: Finite-Difference Gradient Validation (if needed)
At first-divergence step (or step 0 if immediate failure):
- Compute FD approximation of `∂χ²/∂q` using small perturbations (ε=1e-5)
- Compare FD vs autograd gradients; check for sign flips, magnitude mismatches, NaN
- Document in `phase_a_gradient_validation.md`

### Phase A5: Variance/Loss Component Analysis
At first-divergence step:
- Analyze variance tensor breakdown histograms
- Check for pathological distributions (V_denom→0, residuals→inf, I_model anomalies)
- Document in `phase_a_variance_analysis.md`

### Phase A6: Hypothesis Decision
Synthesize A1-A5 results → root cause determination (H1/H2/H3/H4 or combination) → recommend Phase B test

---

## Evidence Gaps Requiring Phase A Data

| Hypothesis | Missing Data from PARITY-003 | Phase A Telemetry to Capture |
|------------|------------------------------|------------------------------|
| H1 (Adam hyperparameters) | Quaternion norm drift, gradient norms | `||q||` per step, `||∂L/∂q||`, momentum accumulation effects |
| H2 (Variance-weighted loss) | I_model distribution, V_denom, clamp fraction | Variance component histograms, clamp fraction, weighted residual distributions |
| H3 (Gradient pathology) | Gradient NaN/inf checks, gradient magnitudes | Global + per-DOF gradient norms, NaN/inf flags, element-wise extrema |
| H4 (Constraint handling) | Quaternion norm before/after normalization, normalization event timing | `||q||` before/after each forward pass, normalization frequency |

---

## Artifacts

- **PARITY-003 Decision:** `parity_003_decision.json`
- **Phase C2 Convergence Verification:** `parity_003_phase_c2.json`
- **DOF Results (U-matrix):** `parity_003_dof_results.json`
- **This Document:** `phase_a0_evidence_synthesis.md`

---

## Conclusion

PARITY-003 proved quaternion U-matrix parameterization is **geometrically correct** (perfect parity) but **optimizer-incompatible** (catastrophic convergence failure). Phase A instrumentation is the critical next step to diagnose whether the root cause is:
1. Optimizer hyperparameters (H1)
2. Loss numerical stability (H2)
3. Gradient corruption (H3)
4. Quaternion constraint handling (H4)

Without per-step telemetry (parameter trajectories, gradient norms, loss components, variance distributions), we cannot distinguish among these hypotheses. Phase A1-A6 will provide the evidence needed to select a targeted fix in Phase B.
