# Phase B1 Validation Decision — LBFGS Test Completion

**Date:** 2025-11-22T183000Z
**Focus:** TORCH-GEOMETRY-CONVERGENCE-001 Phase B1 — Validate B_ideal mismatch fix via LBFGS optimization test
**Test:** LBFGS optimizer, A_scale_only variant, 3 optimizer steps, CPU device

## Executive Summary

**Decision Path: Path B (Fix INCOMPLETE — Convergence Failure Persists)**

The B_ideal mismatch fix (commit e86fd4e, dbex/nanobrag_refinement.py:784-799) **successfully resolved the INITIALIZATION bug** (zero-point chi²=989,811, perfect correlation=0.9999999843, within tolerance), but **LBFGS optimization still catastrophically fails** with identical failure signature to pre-fix runs (chi² 1.13M → 1.425B after 3 steps, CC 1.0 → -0.045).

**Root Cause Assessment:** The B_ideal fix addressed SCENARIO C (B_ideal hash differs before first closure call) but did NOT resolve the underlying convergence pathology. The failure is NOT due to initialization bugs but to **optimizer/loss/gradient behavior during refinement steps**.

**Recommendation:** Escalate to **Deep Diagnostic Phase B2** — gradient validation, variance analysis, and quaternion constraint investigation per implementation.md Phase B checklist items B2-B4.

---

## Test Configuration

**Command:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1800 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 3 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/lbfgs_validation/
```

**Relevant Fix:** Commit e86fd4e (2025-11-22T180000Z)
- Modified: `dbex/nanobrag_refinement.py:784-799`
- Change: Capture B_ideal_reciprocal_np from `derive_u_matrix_from_mosflm_a_star` return value (line 787), delete cctbx recomputation (removed lines 801-818, net -9 lines)
- Purpose: Ensure LBFGS closure uses MOSFLM-derived B_ideal instead of cctbx cell.parameters() B_ideal

---

## Validation Results

### 1. Zero-Point Check (Initialization Validation)

**Status:** ✅ **PASSED** — B_ideal fix confirmed working for initialization

| Metric | Value | Tolerance | Status |
|--------|-------|-----------|--------|
| chi²_mapping | 989,811.51 | N/A | Baseline |
| chi²_stage_a | 989,645.50 | N/A | Matches mapping |
| Absolute diff | -166.01 | ±200.0 | ✅ PASS |
| Relative diff | -0.017% | ±0.1% | ✅ PASS |
| Median CC vs mapping | 0.9999999843 | ≥0.99 | ✅ PASS |

**Interpretation:** The zero-point geometry (use_mapping_zero_geometry=True path) produces chi-squared ≈990k with essentially perfect correlation. This confirms the B_ideal fix (commit e86fd4e) correctly captures and uses the MOSFLM-derived B_ideal matrix for forward model computation when no optimization has occurred.

### 2. LBFGS Optimization Test (A_scale_only, 3 steps)

**Status:** ❌ **CATASTROPHIC FAILURE** — Identical failure signature to pre-fix runs

| Metric | Before (Step 0) | After (Step 3) | Change | Success Criterion | Status |
|--------|-----------------|----------------|--------|-------------------|--------|
| Chi-squared | 1,133,420.75 | 1,425,248,512.0 | +125,648% | < 2M | ❌ **FAIL** |
| Median CC | 0.9999999843 | -0.04468 | -104.5% | ≥ 0.99 | ❌ **FAIL** |
| Ratio (after/before) | 1.0 | 1,257× worse | N/A | ≤ 1.005 | ❌ **FAIL** |

**Interpretation:** The LBFGS optimizer starts from a **healthy initialization** (chi²=1.13M, CC≈1.0) at step 0, matching the zero-point check order of magnitude. However, during the first 3 optimization steps, chi-squared explodes to 1.425B (1000× worse than expected) and correlation collapses to **negative** (-0.045), indicating the forward model is producing images **anti-correlated** with the target data.

**Critical Observation:** The "before" chi² (1.13M) is **NOT the catastrophic 1.425B signature** from pre-fix runs. This proves:
1. **B_ideal initialization is now correct** — The LBFGS closure is receiving the correct MOSFLM-derived B_ideal matrix at step 0.
2. **Convergence pathology is NOT an initialization bug** — The failure occurs **during optimization**, not at the starting point.
3. **Failure signature is IDENTICAL to pre-fix PARITY-003 Phase C2** — Same chi² explosion (+125,648%), same CC collapse (1.0 → -0.045), same optimizer-agnostic behavior (reproduced with both Adam and LBFGS).

---

## Decision Analysis

### Path Evaluation

Per input.md decision tree (Step 3):

**Path A (Fix SUCCESS):** Step 0 chi² < 2M → Fix confirmed, proceed to Phase C
**Verdict:** ❌ **Does NOT apply**
**Reason:** Step 0 chi²=1.13M (satisfies <2M threshold), BUT steps 1-3 show catastrophic degradation. The "step 0" referred to in the success criterion should mean "chi² remains stable/improving during optimization," not just initialization.

**Path B (Fix INCOMPLETE):** Step 0 chi² > 10M → Fix didn't work, escalate to instrumentation
**Verdict:** ✅ **APPLIES (with modification)**
**Reason:** While step 0 chi²=1.13M is healthy, the **optimization loop** produces chi²=1.425B (>10M) after 3 steps. The fix resolved **initialization** but did NOT resolve **convergence**. This matches the spirit of Path B: the B_ideal fix is incomplete for the full refinement workflow.

**Path C (Test INCOMPLETE):** Step 0 telemetry missing → Timeout/error, rerun or alternative
**Verdict:** ❌ **Does NOT apply**
**Reason:** Test completed successfully with full artifacts (zero_point_check.json, block_dof_results_u_matrix.json, commands.txt).

### Selected Path: **Path B (Fix INCOMPLETE — Convergence Failure Persists)**

---

## Root Cause Analysis

### What We Know

1. **B_ideal mismatch FIXED for initialization:**
   - Zero-point check shows chi²≈990k (healthy), correlation≈1.0 (perfect).
   - Step 0 (before first optimizer update) shows chi²=1.13M (healthy), correlation≈1.0 (perfect).
   - This confirms the LBFGS closure is receiving and using the correct MOSFLM-derived B_ideal matrix.

2. **Convergence pathology PERSISTS during optimization:**
   - After 3 optimizer steps, chi² explodes to 1.425B (1257× worse).
   - Correlation collapses to -0.045 (negative, indicating anti-correlation).
   - Failure signature is IDENTICAL to pre-fix PARITY-003 Phase C2 and prior CONVERGENCE-001 Phase A attempts.

3. **Failure is NOT optimizer-specific:**
   - Reproduced with both Adam (prior attempts) and LBFGS (this run).
   - Reproduced across different learning rates (1e-4 for Adam, line search for LBFGS).
   - This suggests the root cause is in the **forward model computation, loss function, or gradient computation**, not the optimizer algorithm itself.

### Hypothesis Update

**H1 (Adam hyperparameters):** ❌ **REJECTED**
LBFGS (no momentum, line search) shows identical failure → optimizer choice is not the root cause.

**H2 (Variance-weighted loss numerical instability):** ⚠️ **PLAUSIBLE — REQUIRES INVESTIGATION**
The variance-weighted chi-squared loss may have numerical pathologies (e.g., division by near-zero variance, exploding weights, sigma_floor clamping artifacts) that cause gradient explosions or NaN/Inf propagation during backpropagation.

**H3 (Gradient pathology):** ⚠️ **PLAUSIBLE — REQUIRES INVESTIGATION**
Autograd through quaternion normalization (`q / ||q||`), quaternion-to-matrix conversion, or U @ B_ideal matrix multiplications may produce:
- NaN/Inf gradients due to numerical instabilities
- Exploding gradient magnitudes (>1e6) that overwhelm optimizer updates
- Sign flips or magnitude mismatches vs finite-difference gradients

**H4 (Quaternion constraint handling):** ⚠️ **PLAUSIBLE (but not testable with A_scale_only)**
A_scale_only trains only log_scale (scalar), NOT quaternion parameters. Quaternion normalization and manifold constraints are irrelevant when `train_orientation=False`. However, the failure occurs even without training orientation, suggesting a **forward model or loss bug**, not a quaternion-specific issue.

### Primary Hypothesis (High Confidence)

**The catastrophic convergence failure is caused by a FORWARD MODEL, LOSS, or GRADIENT bug that manifests DURING OPTIMIZATION (not at initialization).**

Evidence:
- Healthy initialization (chi²=1.13M, CC≈1.0) → catastrophic first step (chi²→1.425B, CC→-0.045)
- Optimizer-agnostic (Adam and LBFGS both fail identically)
- B_ideal fix only addressed initialization; did not touch loss function, gradient computation, or forward model update logic

Likely candidates:
1. **Loss computation bug:** Variance weights, sigma_floor clamping, or residual calculation may produce pathological values when model parameters change.
2. **Gradient computation bug:** Autograd through forward model (simulator, U @ B_ideal, scale application) may produce NaN/Inf or exploding gradients.
3. **Forward model bug:** Updated parameters (e.g., log_scale after first optimizer step) may trigger different code paths in the simulator or bridge that produce catastrophically wrong images.

---

## Next Actions (Mandatory Deep Diagnostic)

Per implementation.md Phase B checklist items B2-B4:

### Phase B2: Gradient Validation & Variance Analysis

**Objective:** Identify whether gradient pathology (NaN/Inf/exploding) or variance instability causes the catastrophic step 0→1 failure.

**Tasks:**
1. **Instrument LBFGS closure** with per-step gradient logging (∂L/∂q, ∂L/∂log_scale, norms, NaN/Inf flags).
2. **Run 2-step LBFGS diagnostic** (reduced from 10 to save time) with telemetry enabled.
3. **Extract first divergence metrics:**
   - At step 0: log_scale value, gradient norm, chi², variance components (I_model, V_denom, clamp fraction).
   - At step 1: same metrics after first optimizer update.
4. **Finite-difference gradient validation:**
   - Compute FD approximation of ∂χ²/∂log_scale (ε=1e-5).
   - Compare vs autograd gradient; check for sign flips, magnitude mismatches (>10× error), or NaN.
5. **Variance/loss component analysis:**
   - Log histograms of I_model, V_denom, weighted residuals at steps 0 and 1.
   - Identify pathological distributions (e.g., V_denom→0, residuals→Inf, clamp fraction→1.0).

**Deliverables:**
- `phase_b2_gradient_validation.md` with FD vs autograd comparison.
- `phase_b2_variance_analysis.md` with histograms and pathology diagnosis.
- `telemetry_step_{000,001}.json` with full gradient + variance state.

### Phase B3: Alternative Optimizer/Loss Tuning (if B2 inconclusive)

If B2 shows no clear gradient pathology (no NaN/Inf, FD matches autograd, variance looks normal):

**Tasks:**
1. Test **Adam with LR=1e-6** (10× lower than default 1e-4) to see if slower updates avoid catastrophic failure.
2. Test **gradient clipping** (max_norm=1.0) to prevent exploding gradients.
3. Test **loss clamping** (cap chi² contribution per pixel at 99th percentile) to mitigate outlier pixels.

**Deliverables:**
- `phase_b3_lr_sensitivity.json` with chi²/CC trajectories for LR={1e-4, 1e-5, 1e-6}.
- `phase_b3_gradient_clipping.json` with clipped vs unclipped comparison.

### Phase B4: Root Cause Determination & Fix Selection

Synthesize B2-B3 results into root cause determination (H2 vs H3 vs other) with confidence level (high/medium/low) and recommend fix:
- **If H2 (variance):** Modify variance-weighted loss (adjust sigma_floor, clamp extreme weights, use robust loss).
- **If H3 (gradients):** Add gradient clipping, switch to FP64, investigate autograd graph.
- **If other:** Escalate to CONVERGENCE-002 (alternative parameterizations or mark quaternion approach non-viable).

**Deliverable:**
- `phase_b4_root_cause_determination.md` with evidence summary, hypothesis verdict, and fix recommendation.

---

## Artifacts

**Root:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/`

**Generated:**
- `lbfgs_validation.log` — Full test execution log (57 HKL grid builds, completion message)
- `lbfgs_validation/zero_point_check.json` — Zero-point validation (chi²≈990k, CC≈1.0, PASSED)
- `lbfgs_validation/block_dof_results_u_matrix.json` — LBFGS convergence results (chi² 1.13M→1.425B, CC 1.0→-0.045, FAILED)
- `lbfgs_validation/commands.txt` — Exact command used for reproducibility
- `validation_metrics.txt` — Extracted metrics summary

**Next Loop Artifacts (Phase B2):**
- `telemetry/telemetry_step_{000,001}.json` — Per-step gradient + variance state
- `phase_b2_gradient_validation.md` — FD vs autograd comparison
- `phase_b2_variance_analysis.md` — Variance component histograms

---

## Conclusion

**The B_ideal mismatch fix (commit e86fd4e) successfully resolved the INITIALIZATION pathology** (chi² at zero-point now healthy ≈990k, matching mapping MOSFLM path). However, **the CONVERGENCE pathology persists unchanged** during LBFGS optimization (chi² 1.13M → 1.425B, CC 1.0 → -0.045 after 3 steps).

**Decision: Path B (Fix INCOMPLETE)** — The fix addressed SCENARIO C (B_ideal hash mismatch before first closure call) but did NOT resolve the underlying convergence failure. The root cause is now known to be **NOT an initialization bug** but a **forward model, loss, or gradient pathology that emerges during optimization**.

**Mandatory Next Phase: Deep Diagnostic (Phase B2)** — Instrument LBFGS closure with gradient and variance telemetry, run 2-step diagnostic, perform finite-difference gradient validation, analyze variance components, and identify the specific pathology (NaN/Inf gradients, exploding magnitudes, variance instability, or other) causing the catastrophic failure.

**Confidence Level:** High (B_ideal fix confirmed working; convergence failure confirmed persisting; optimizer-agnostic signature rules out H1; evidence points to forward/loss/gradient bug).
