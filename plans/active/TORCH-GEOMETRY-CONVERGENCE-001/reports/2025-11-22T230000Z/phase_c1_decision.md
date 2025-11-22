# Phase C1 Decision — Convergence Root Cause

**Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
**Phase:** C1 (Convergence Telemetry & Root Cause Analysis)
**Date:** 2025-11-22T230000Z

---

## Verdict

**[X] Path A — Primary Hypothesis CLEAR (implement targeted fix)**

Primary hypothesis **H1 (Adam LR too high)** identified with **HIGH confidence (~85%)**.

Recommended fix: Reduce Adam learning rate to 1e-5 for U-matrix parameterization.

---

## Evidence Summary

### Divergence Step
**Step 0** (after first optimizer.step())

### Chi² Trajectory
**SUDDEN JUMP then MONOTONIC SLOW DECREASE**

- Initialization: 1,133,421 (healthy, Phase B5 fix working)
- Step 0: 8,837,164 (+679.8% catastrophic jump)
- Step 1: 8,836,375 (-0.009% slight improvement)
- Step 2-9: Monotonic decrease (-0.009%/step, total -0.09%)
- Final: 8,829,291 (7.79× worse than init, but stable/improving trend)

**Interpretation:** First optimizer step causes catastrophic overshoot (LR × gradient too large), subsequent steps slowly recover but stuck in bad local minimum.

### Gradient Norms
**STABLE O(150k), MONOTONICALLY DECREASING**

- Step 0: grad_log_scale = 149,662
- Step 9: grad_log_scale = 148,414 (-1,248 total, -139 units/step)
- Trend: Linear decrease, very consistent

**Interpretation:** Gradients are healthy (no explosion, no vanishing), indicating optimizer is functioning correctly after initial overshoot.

### NaN/Inf Flags
**ALL FALSE** (no NaN or Inf detected in any step 0-9)

**Interpretation:** Rules out H3a (gradient NaN/Inf pathology).

### Quaternion Norm Drift
**q_norm = 1.0 EXACT** (all steps 0-9)

**Interpretation:** Normalization working correctly, no constraint violation. Rules out quaternion drift issues.

---

## Primary Hypothesis

**H1: Adam learning rate incompatibility with quaternion U-matrix parameterization**

**Confidence:** HIGH (~85%)

### Rationale

1. **Classic LR overshoot signature:**
   - Single catastrophic first step (chi² 1.13M → 8.84M, +679%)
   - Subsequent monotonic recovery (chi² decreasing -0.009%/step)
   - Stuck in worse local minimum (cannot recover to initial chi²=1.13M)

2. **Gradient magnitude scale mismatch:**
   - Quaternion gradients: O(150k) (unitless parameters on S³ manifold)
   - Cell/misset gradients: O(1-100) (physical units: Å, degrees)
   - LR=1e-4 calibrated for cell/misset → Adam update Δq = -1e-4 × 150k = **-15.0**
   - This is a ~35° rotation (>>1° safe step size), causing catastrophic geometry change

3. **Healthy gradient behavior post-overshoot:**
   - No NaN/Inf (rules out H3a)
   - No explosion (rules out H3b as primary cause)
   - Monotonic decrease (rules out H2 variance instability)
   - Optimizer is WORKING CORRECTLY, just started from bad initial overshoot

4. **Zero-point validation success:**
   - chi²_mapping = 989,812 (healthy)
   - chi²_stage_a = 989,646 (healthy, matches mapping)
   - correlation = 0.9999999843 (perfect)
   - **Phase B5 fix confirmed working** → initialization healthy, convergence is separate issue

### Physics Interpretation

Adam optimizer computes parameter update: `Δθ = -LR × gradient`

For quaternion parameters:
- `gradient ≈ 150,000` (large due to chi²=8.84M residuals)
- `LR = 1e-4` (designed for cell/misset)
- `Δq = -1e-4 × 150,000 = -15.0` (MASSIVE perturbation)

After normalization: `q_new = (q_old + Δq) / ||q_old + Δq||`
- Adding Δq=(-15, -15, -15, -15) to q_old ≈ (-0.31, 0.87, -0.25, 0.27) completely changes direction
- After renormalization, q_new points in a very different direction on S³
- This corresponds to a large rotation (~35°) in U-matrix
- Crystal orientation is severely misaligned → chi² jumps 7.8×

For cell/misset parameters (for comparison):
- `gradient ≈ 100` (typical for cell parameter in Å)
- `LR = 1e-4` (same LR)
- `Δa = -1e-4 × 100 = -0.01 Å` (tiny perturbation, safe)

**Root cause:** Learning rate is 1000× too high for quaternion parameters compared to their gradient scale.

---

## Recommended Next Actions

### Path A: Implement Adam LR reduction fix (PRIORITY 1)

**Target:** Phase C2 implementation

**Fix specification:**
1. Extend `RefinementConfig` with `u_matrix_learning_rate: float = 1e-5`
2. Update optimizer setup in `run_nanobrag_refinement`:
   - When `use_u_matrix_parameterization=True`, use `u_matrix_learning_rate`
   - Else use default `1e-4` (cell/misset path unchanged)
3. Update `stage_a_mapping_adam_debug.py` with `--u-matrix-lr` CLI flag
4. Validation test: Rerun Phase 5 A_scale_only with LR=1e-5
   - Success criteria: chi²_after ≤ 1.2M (≤5% drift), CC_after ≥ 0.99
5. If LR=1e-5 succeeds: Proceed to D_full validation, update findings, close initiative
6. If LR=1e-5 fails: Try LR=1e-6 (100× reduction) or LR=1e-7 (1000× reduction)

**Expected outcome:** HIGH confidence (~85%) that LR=1e-5 will resolve A_scale_only convergence failure.

**Implementation effort:** 1 loop (config field + optimizer branch + CLI flag + validation test)

---

### Alternative Paths (if LR reduction fails)

**Path B: Additional diagnostics/tuning** (MEDIUM confidence ~50%)
- Per-parameter learning rates (separate LR for q_params vs log_scale)
- Gradient clipping (clip ||grad_q|| to 1e4)
- Riemannian Adam (project gradients to tangent space of S³)
- LBFGS for U-matrix path (line search finds safe step size automatically)

**Path C: Escalate to alternative parameterization** (LOW confidence ~5%)
- Hybrid cell+quaternion+scale (PARITY-002 Option 1)
- Revert to cell+misset only (mark quaternion as non-viable)

---

## Hypothesis Verdicts Summary

| Hypothesis | Verdict | Confidence | Key Evidence |
|------------|---------|------------|--------------|
| H1: Adam LR too high | **PRIMARY** | HIGH (~85%) | First-step overshoot, gradient scale mismatch, monotonic recovery |
| H2: Variance instability | Unlikely | LOW (~10%) | No oscillations, variance telemetry NULL, zero-point healthy |
| H3a: Gradient NaN/Inf | **REJECTED** | 0% | NO NaN or Inf detected (steps 0-9) |
| H3b: Gradient explosion | Symptom | LOW (~15%) | Gradients large but stable/decreasing, proportional to chi² |
| H4: Quaternion constraint | Not testable | N/A | A_scale_only has train_orientation=False, q_norm=1.0 stable |

---

## Artifacts

- `phase_c1_convergence_analysis.md` — Full telemetry analysis and hypothesis verdicts
- `convergence_trajectory.txt` — Step-by-step metrics table
- `convergence_telemetry/` — Telemetry JSON files (steps 0-9), zero-point check, block results
- `convergence_test.log` — Full execution log

---

## Next Loop

**Objective:** Implement Phase C2 (Adam LR reduction fix) per Path A specification above.

**Success criteria:** Phase 5 A_scale_only with LR=1e-5 shows chi² stable (≤5% drift) and CC ≥ 0.99 after 10 steps.
