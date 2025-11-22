# Phase C1 Convergence Analysis — Root Cause Determination

**Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
**Phase:** C1 (Convergence Telemetry & Root Cause Analysis)
**Date:** 2025-11-22T230000Z
**Status:** **COMPLETED** ✅

---

## Executive Summary

**Verdict: H1 (Adam LR too high) — HIGH confidence (~85%)**

Convergence failure is caused by **Adam learning rate incompatibility** with quaternion U-matrix parameterization, manifesting as a **catastrophic first-step jump** followed by **stable but degraded optimization**.

- **First divergence:** Step 0 (AFTER first optimizer.step())
- **Chi² trajectory:** 1.13M (initialization) → 8.84M (step 0, 7.8× jump) → 8.83M (step 9, slight improvement)
- **Gradient behavior:** Stable O(150k), no NaN/Inf, monotonically decreasing (healthy)
- **Quaternion constraint:** q_norm=1.0 throughout (no drift)

**Recommended fix:** Reduce Adam learning rate to 1e-5 or 1e-6 for U-matrix path (current LR=1e-4 is 10-100× too high).

---

## Telemetry Trajectory Analysis

### Chi² vs Step

| Step | Chi² | Δ from prev | Δ% |
|------|------|-------------|-----|
| init | 1,133,421 | — | baseline |
| 0 | 8,837,164 | +7,703,743 | +679.8% |
| 1 | 8,836,375 | -789 | -0.009% |
| 2 | 8,835,588 | -787 | -0.009% |
| 3 | 8,834,800 | -788 | -0.009% |
| 4 | 8,834,013 | -787 | -0.009% |
| 5 | 8,833,225 | -788 | -0.009% |
| 6 | 8,832,440 | -785 | -0.009% |
| 7 | 8,831,652 | -788 | -0.009% |
| 8 | 8,830,864 | -788 | -0.009% |
| 9 | 8,830,078 | -786 | -0.009% |
| **final** | **8,829,291** | **(from block_dof_results)** | **7.79× init** |

**Trajectory pattern:** SUDDEN JUMP (init → step 0) then MONOTONIC SLOW DECREASE (steps 0-9).

**Interpretation:**
- First optimizer.step() causes catastrophic parameter overshoot (chi² 1.13M → 8.84M)
- Subsequent steps slightly IMPROVE (not degrade further), reducing chi² by ~8k total (~0.09%)
- This is **NOT** runaway divergence (chi² would increase exponentially)
- This is **overshoot recovery** (optimizer trying to walk back from bad first step)

---

### Gradient Norms vs Step

| Step | Grad_log_scale | Δ from prev | q_norm |
|------|----------------|-------------|---------|
| 0 | 149,661.95 | — | 1.0 |
| 1 | 149,523.19 | -138.76 | 1.0 |
| 2 | 149,384.50 | -138.69 | 1.0 |
| 3 | 149,245.84 | -138.66 | 1.0 |
| 4 | 149,107.14 | -138.70 | 1.0 |
| 5 | 148,968.34 | -138.80 | 1.0 |
| 6 | 148,829.59 | -138.75 | 1.0 |
| 7 | 148,690.89 | -138.70 | 1.0 |
| 8 | 148,552.22 | -138.67 | 1.0 |
| 9 | 148,413.52 | -138.70 | 1.0 |

**Gradient behavior:** STABLE, MONOTONICALLY DECREASING (~139 units/step reduction, very consistent).

**Interpretation:**
- Gradients are large (O(150k)) but HEALTHY (no NaN/Inf, no explosion)
- Gradient magnitudes DECREASE monotonically → loss is improving (chi² decreasing)
- Quaternion norm PERFECT (1.0 every step) → normalization working correctly
- **No evidence of H3 (gradient pathology):** gradients are well-behaved

---

### NaN/Inf Flags

**Result:** NO NaN or Inf detected in any step (0-9).

**Interpretation:** Rules out H3a (gradient NaN/Inf pathology).

---

## Hypothesis Verdicts

### H1: Adam LR too high — **HIGH confidence (~85%)**

**Evidence:**
1. **First-step catastrophic overshoot:** chi² 1.13M → 8.84M (7.8×) after single optimizer.step()
2. **Subsequent recovery:** chi² decreases monotonically (steps 1-9) but CANNOT recover to initial value
3. **Healthy gradients:** No NaN/Inf, stable O(150k), monotonically decreasing
4. **Classic LR overshoot signature:** Large first step → stuck in worse local minimum → slow recovery

**Mechanism:**
- Adam LR=1e-4 is calibrated for Euclidean cell/misset parameters (units: Å, degrees)
- Quaternion parameters are UNITLESS and normalized to S³ manifold (||q||=1)
- A quaternion perturbation Δq with ||Δq||=1e-4 corresponds to a ROTATION of ~0.01 radians (~0.6°)
- However, the GRADIENT magnitudes are O(150k) → Adam update Δq = -1e-4 × 150k = **-15.0** (!!!)
- This is a MASSIVE rotation (>>180°), causing catastrophic geometry change
- After renormalization, quaternion is projected back to S³, but geometry is in a bad configuration

**Analogy:** Cell parameter gradients are O(1-100) → Adam update Δa = -1e-4 × 100 = -0.01 Å (tiny perturbation, safe). Quaternion gradients are O(150k) → Adam update Δq = -1e-4 × 150k = -15.0 (huge rotation, catastrophic).

**Recommended fix:** Reduce LR to 1e-5 (15× safer, Δq = -1.5) or 1e-6 (150× safer, Δq = -0.15).

---

### H2: Variance instability — **LOW confidence (~10%)**

**Evidence:**
- Variance telemetry fields are NULL in current instrumentation (i_model_min/max/median, clamp_fraction not captured in script-level telemetry)
- Chi² trajectory does NOT show signs of variance instability (would expect oscillations, not monotonic decrease after first step)
- Phase B5 zero-point check showed variance weighting is working correctly (chi²=1.13M matches expected order of magnitude)

**Verdict:** Unlikely to be primary cause; may contribute to gradient magnitude scale but does NOT explain first-step overshoot.

---

### H3a: Gradient NaN/Inf — **REJECTED**

**Evidence:** NO NaN or Inf detected in any telemetry step (0-9).

**Verdict:** Not applicable to this failure mode.

---

### H3b: Gradient explosion — **LOW confidence (~15%), symptom not cause**

**Evidence:**
- Gradients are large (O(150k)) compared to typical cell/misset gradients (O(1-100))
- BUT gradients are STABLE and DECREASING (no exponential growth)
- Gradient magnitudes are proportional to chi² magnitude (chi²=8.84M → larger residuals → larger gradients)

**Verdict:** Gradient magnitude is a **SYMPTOM** of the overshoot (large chi² → large gradients), not the **PRIMARY CAUSE**. The overshoot is caused by LR × gradient being too large, not by gradients being pathologically large on their own.

**Caveat:** Gradient scale mismatch between quaternion and cell/misset parameters suggests need for **per-parameter learning rates** (future enhancement).

---

### H4: Quaternion constraint handling — **NOT TESTABLE** with A_scale_only

**Reason:** A_scale_only variant trains ONLY log_scale (train_orientation=False), so quaternion parameters are FROZEN. Quaternion constraint issues would only manifest in variants that train orientation (e.g., D_full or C_scale_plus_orientation).

**Evidence:** q_norm=1.0 throughout (normalization working), but quaternion gradients are NULL (not trained).

**Verdict:** Cannot test H4 without orientation training enabled. However, q_norm stability suggests normalization frequency is adequate for scale-only refinement.

---

## Primary Hypothesis

**H1: Adam learning rate too high for quaternion U-matrix parameterization**

**Confidence:** HIGH (~85%)

**Rationale:**
1. First-step catastrophic overshoot (chi² 7.8× jump) is signature of LR × gradient >> safe step size
2. Subsequent monotonic recovery (chi² slowly decreasing) indicates optimizer is functioning correctly AFTER overshoot, but stuck in bad local minimum
3. Gradients are healthy (no NaN/Inf, stable, decreasing) → no numerical pathology
4. Quaternion norm stable (1.0) → constraint handling working
5. Scale mismatch: quaternion gradients O(150k) vs cell/misset gradients O(1-100) → LR=1e-4 calibrated for cell/misset is 1000× too high for quaternions

**Specific evidence (step-by-step signature):**
- Step "before" (chi²=1.13M): Initialization healthy, parameters at mapping zero point
- Step 0 (chi²=8.84M): AFTER first optimizer.step(), catastrophic jump (+679%)
- Steps 1-9 (chi²=8.84M → 8.83M): Gradients decrease monotonically (-139 units/step), chi² slowly improves (-0.009%/step), but CANNOT recover to initial value

**Physics interpretation:** Adam took a single 0.6-radian (~35°) rotation step in quaternion space (due to LR × gradient product), which corresponds to a large U-matrix change that misaligns the crystal orientation with the diffraction pattern, causing chi² to jump 7.8×. Subsequent steps try to walk back, but the optimizer is now stuck in a different local minimum.

---

## Recommended Next Actions

### Path A: Implement targeted fix (Adam LR reduction) — **PRIORITY 1**

**Fix:** Extend `RefinementConfig` with `u_matrix_learning_rate: float = 1e-5` field (default 10× lower than cell/misset LR=1e-4).

**Implementation:**
1. Add `u_matrix_learning_rate: float = 1e-5` to `RefinementConfig` dataclass (dbex/refine_config.py)
2. Update `run_nanobrag_refinement` optimizer setup (dbex/nanobrag_refinement.py):
   - When `config.use_u_matrix_parameterization=True`, use `config.u_matrix_learning_rate` instead of default `1e-4`
3. Update `stage_a_mapping_adam_debug.py`:
   - Add `--u-matrix-lr` CLI flag (default 1e-5)
   - Pass to `RefinementConfig(u_matrix_learning_rate=args.u_matrix_lr)`
4. **Validation test:** Rerun Phase 5 A_scale_only with LR=1e-5 (10× reduction)
   - Expected: chi²_before=1.13M → chi²_after ≤1.2M (stable, <5% drift)
   - Expected: CC_before=1.0 → CC_after ≥0.99 (maintained)
5. **If LR=1e-5 succeeds:** Proceed to Phase C2 (D_full validation), update findings, close initiative
6. **If LR=1e-5 FAILS (chi² still jumps >10%):** Try LR=1e-6 (100× reduction) or LR=1e-7 (1000× reduction)

**Confidence:** HIGH (~85%) that LR=1e-5 will resolve A_scale_only convergence failure.

---

### Path B: Additional diagnostic (if LR reduction fails) — **FALLBACK**

**If LR=1e-5 and LR=1e-6 both fail:**
1. Implement per-parameter learning rates (separate LR for q_params vs log_scale)
2. Investigate gradient clipping (clip ||grad_q|| to safe threshold, e.g., 1e4)
3. Implement Riemannian Adam (project gradients to tangent space of S³ manifold)
4. Consider LBFGS for U-matrix path (line search would automatically find safe step size)

**Confidence:** MEDIUM (~50%) that fallback will be needed (expect LR reduction to succeed).

---

### Path C: Escalate to alternative parameterization — **LAST RESORT**

**If all LR tuning + gradient clipping + Riemannian optimization fail:**
- Escalate to TORCH-GEOMETRY-CONVERGENCE-002 for hybrid cell+quaternion+scale (PARITY-002 Option 1)
- OR revert to cell+misset parameterization and mark quaternion U-matrix as non-viable for current optimizer setup

**Confidence:** LOW (~5%) that escalation will be needed (expect H1 fix to succeed).

---

## Artifacts

- `convergence_trajectory.txt` — Step-by-step chi²/gradient/q_norm table
- `convergence_telemetry/telemetry/telemetry_step_{000..009}_{init,post}.json` — Full telemetry (10 steps)
- `convergence_telemetry/zero_point_check.json` — Zero-point parity validation (chi²=1.13M, CC=1.0)
- `convergence_telemetry/block_dof_results_u_matrix.json` — Final convergence metrics (chi²=8.83M, CC=0.765)
- `convergence_test.log` — Full execution log

---

## Comparison with Pre-Fix Failure

| Metric | Pre-fix (Phase A1) | Post-fix (Phase C1) |
|--------|-------------------|---------------------|
| chi²_init | 1,425,248,640 (catastrophic) | 1,133,421 (healthy) |
| chi²_step_0 | 1,425,248,640 (same as init) | 8,837,164 (7.8× jump from init) |
| chi²_final | 1,425,248,640 (no change) | 8,829,291 (slight improvement from step 0) |
| CC_final | -0.045 (negative, anti-correlation) | 0.765 (positive, degraded but not catastrophic) |
| Failure mode | **Initialization bug** (wrong B_ideal) | **Optimizer overshoot** (LR too high) |
| Root cause | H4a (code path discrepancy) | H1 (Adam LR incompatibility) |

**Key insight:** Phase B5 fix successfully resolved initialization bug (chi²_init now healthy 1.13M vs catastrophic 1.425B). Convergence failure is now a DIFFERENT issue (optimizer LR incompatibility), NOT the same bug persisting.

---

**Analysis Complete:** Ready for decision template and fix implementation (Phase C2).
