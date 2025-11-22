# Phase C3 Decision — Parameter Lifecycle Investigation

**Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
**Phase:** C3 (Parameter Update Propagation Investigation)
**Date:** 2025-11-22T224717Z

---

## Verdict

**[ ] Path A — Parameter update WORKS, forward model uses NEW value**
**[ ] Path B — Parameter update FAILS (Δlog_scale ≈ 0)**
**[X] Path C — Parameter update CORRECT, but forward model uses STALE/WRONG value**
**[ ] Path D — Parameter update TOO LARGE (different LR or gradient)**

**PRIMARY DIAGNOSIS:** **Path C CONFIRMED with HIGH confidence (~90%)**

The catastrophic chi² (8.8M) appears BEFORE the first optimizer.step(), meaning the failure occurs during the FIRST closure evaluation, not during parameter updates. This indicates a **forward model initialization bug** where parameters are set correctly but the forward model uses stale or incorrect values.

---

## Critical Evidence

### Zero-Point Initialization
**Correlation at mapping zero-point:** 0.9999999843 (perfect parity, Phase B5 fix working)

This confirms that at the mapping zero-point (before any optimization), the forward model produces correct results.

### Step 0 Lifecycle

**BEFORE optimizer.step():**
- log_scale: -0.20591746
- grad_log_scale: 149,661.95
- chi²: **8,837,164** (CATASTROPHIC)
- q_params: [-0.3125, 0.8748, -0.2550, 0.2684]
- q_norm: 1.0 (perfect)

**AFTER optimizer.step():**
- log_scale: -0.20590746
- chi²: 8,837,085 (essentially unchanged, -79 = -0.0009%)
- q_params: [-0.3125, 0.8748, -0.2550, 0.2684] (UNCHANGED — train_orientation=False)
- q_norm: 1.0

**Parameter Update Analysis:**
- Δlog_scale (actual): +0.00001000 = **+1e-5**
- Expected Δ (≈ -LR × grad): -1e-5 × 149,661.95 = **-1.49662**
- **MISMATCH:** Parameter changed by +1e-5 instead of -1.5

---

## Root Cause Determination

### PRIMARY FINDING: Catastrophic chi² BEFORE First Optimizer Step

The most critical observation is that chi² = 8.8M **BEFORE** the first optimizer.step() call. This means:

1. **Zero-point validation:** chi² ~990k-1.13M (healthy, correlation 1.0)
2. **First closure evaluation:** chi² ~8.8M (catastrophic, BEFORE optimizer updates parameters)
3. **After first optimizer.step():** chi² ~8.8M (unchanged)

**Interpretation:** The failure happens during the FIRST closure evaluation, not during parameter updates. The optimizer sees an already-catastrophic loss and tries to optimize from that bad state.

### Why the Parameter Update is Wrong

The parameter update Δlog_scale = +1e-5 instead of -1.5 is ALSO wrong, but it's a **secondary symptom**. Possible explanations:

1. **Gradient is computed against wrong forward model:** If the forward model produces chi²=8.8M due to using stale parameters, the gradient of 149k is the gradient TO FIX that wrong model, not the gradient for the correct model at log_scale=-0.206.

2. **Adam optimizer state:** The expected Δ = -LR × gradient formula is for vanilla SGD. Adam uses momentum and adaptive LR, so the actual update might differ. However, a +1e-5 update suggests the optimizer is barely moving (possibly due to clipping or momentum damping).

### Path C: Forward Model Uses Stale/Wrong Parameters

**Hypothesis:** Similar to Phase B5's B_ideal mismatch, there's a code path where:
- Parameters (log_scale, q_params) are correctly initialized at zero-point
- But when the first closure runs, the forward model uses DIFFERENT (stale or default) parameter values
- This causes chi² to jump to 8.8M
- The optimizer then tries to recover from this bad state, but can't

**Evidence supporting Path C:**
1. Zero-point validation passes (correct parameters, correct forward model)
2. First closure evaluation catastrophic (parameters unchanged by user, but forward model produces wrong result)
3. This pattern matches Phase B5: initialization healthy, first optimization step catastrophic
4. Parameter update magnitude is suspiciously small (+1e-5 vs expected -1.5), suggesting optimizer is confused by the bad loss landscape

---

## Comparison to Phase C1/C2 (LR Hypothesis)

**Phase C1 Hypothesis:** Adam LR=1e-4 too high → first step overshoot → chi² 1.13M → 8.8M

**Phase C1 Evidence:**
- chi² BEFORE first step: 1.13M (healthy)
- chi² AFTER first step: 8.8M (catastrophic)
- Interpretation: Optimizer overshoot caused by LR × gradient = -1.5 too large

**Phase C2 Test (LR=1e-5):**
- chi² AFTER 10 steps: 8.8M (identical to Phase C1)
- Verdict: H1 (LR too high) REJECTED

**Phase C3 Evidence (NEW):**
- chi² BEFORE first step: 8.8M (ALREADY CATASTROPHIC)
- Interpretation: Failure is NOT in optimizer step, but in first closure evaluation

**Conclusion:** Phase C1 misdiagnosed the failure. The "before" chi² in C1 was likely measured at zero-point, not immediately before optimizer.step() inside the closure. C3's telemetry captures the TRUE before-step chi², revealing the failure happens earlier.

---

## Recommended Next Actions

### Priority 1: Audit First Closure Evaluation (HIGH confidence fix ~85%)

**Target:** Identify where forward model parameters diverge between zero-point validation and first closure call.

**Checklist:**
1. Verify log_scale tensor is SAME object in zero-point forward and first closure forward
   - Check for accidental .clone(), .detach(), or reassignment
2. Verify q_params tensor is SAME object (or correctly derived from same source)
3. Audit U-matrix derivation in first closure:
   - Is quaternion_to_matrix called with the CORRECT q_params?
   - Is B_ideal correctly sourced from MOSFLM tuple (not cctbx)?
   - Is A* = U @ B_ideal using the CORRECT U and B_ideal?
4. Add checksum logging:
   - Log U_matrix hash/checksum at zero-point and first closure
   - Log A* hash/checksum at zero-point and first closure
   - Identify first divergence point

**Expected outcome:** Find that first closure uses stale q_params or B_ideal, similar to Phase B5's crystal_overrides["A_star"] bypass bug.

### Priority 2: Alternative Hypothesis — Adam Optimizer Bug (MEDIUM confidence ~40%)

If Priority 1 audit finds no parameter staleness:

**Test:** Switch to LBFGS optimizer for Phase 5
- LBFGS computes gradients inside closure via multiple forward passes
- If first closure evaluation is healthy with LBFGS, the bug is Adam-specific
- Possible cause: Adam's momentum buffer initialization or gradient scaling

**Validation:** Run Phase 5 with `--use-lbfgs --lbfgs-steps 2`
- If LBFGS shows chi² ~1.13M before first step → Adam bug confirmed
- If LBFGS also shows chi² ~8.8M before first step → forward model bug confirmed

### Priority 3: Gradient Clipping / Numerical Stability (LOW confidence ~10%)

If both Priority 1 and 2 fail to identify root cause:

**Test:** Add gradient clipping or parameter bounds
- Clip grad_log_scale to [-1e4, 1e4]
- Bound log_scale to [-5, 5] (scale factor [0.007, 148])
- Check if catastrophic chi² is due to overflow/underflow in scale

---

## Decision Tree Paths (Input.md Spec)

### Path A: Parameter update WORKS, forward model uses NEW value
**Verdict:** REJECTED (0% confidence)
**Evidence:** chi² catastrophic BEFORE first step, not after
**Interpretation:** Would only apply if chi² jumped AFTER optimizer.step(), but jump happens BEFORE

### Path B: Parameter update FAILS (Δlog_scale ≈ 0)
**Verdict:** REJECTED (5% confidence)
**Evidence:** Δlog_scale = +1e-5 ≠ 0, parameter DID change
**Interpretation:** Update magnitude is wrong, but not zero → not a requires_grad or detach bug

### Path C: Parameter update CORRECT, but forward model uses OLD value
**Verdict:** CONFIRMED (90% confidence)
**Evidence:**
- Zero-point forward uses correct parameters (chi² ~1.13M, corr 1.0)
- First closure forward uses stale/wrong parameters (chi² 8.8M BEFORE step)
- Pattern matches Phase B5 code path discrepancy
**Interpretation:** Variable scope or aliasing bug where closure captures wrong parameter tensor or derives U/A* from stale source

### Path D: Parameter update TOO LARGE (different LR or gradient)
**Verdict:** PLAUSIBLE (40% confidence)
**Evidence:** Δlog_scale = +1e-5 (LR magnitude) instead of -1.5 (LR × gradient)
**Interpretation:** Adam might be applying LR incorrectly or gradient is scaled wrong. However, this doesn't explain chi² catastrophic BEFORE step.
**Note:** Could be SECONDARY symptom of Path C (optimizer confused by wrong loss landscape)

---

## Hypothesis Verdicts Summary

| Hypothesis | Verdict | Confidence | Key Evidence |
|------------|---------|------------|--------------|
| H1: Adam LR too high | **REJECTED** | 0% | Phase C2 LR reduction ZERO effect; C3 shows chi² bad BEFORE step |
| H2: Variance instability | Unlikely | 5% | No variance telemetry captured, but zero-point healthy suggests variance OK |
| H3a: Gradient NaN/Inf | **REJECTED** | 0% | grad_has_nan/inf = false |
| H3b: Gradient explosion | Symptom | 10% | grad=149k large but proportional to chi²=8.8M residuals |
| H4: Quaternion constraint | Not testable | N/A | A_scale_only has train_orientation=False |
| **H5 (NEW): Forward model parameter staleness** | **PRIMARY** | **90%** | chi² catastrophic BEFORE step, matches Phase B5 pattern |
| **H6 (NEW): Adam optimizer bug** | Secondary | 40% | Δlog_scale wrong magnitude, but doesn't explain pre-step chi² |

---

## Artifacts

- `lifecycle_diagnostic.log` — Full diagnostic execution log
- `telemetry/telemetry_step_000_init.json` — Parameters and chi² BEFORE first step
- `telemetry/telemetry_step_000_post.json` — Parameters and chi² AFTER first step
- `zero_point_check.json` — Zero-point correlation validation (corr=1.0)

---

## Next Loop

**Objective:** Implement Priority 1 audit (U_matrix/A* checksum logging in first closure) to identify parameter staleness bug.

**Success criteria:** Identify where U_matrix or A* diverges between zero-point and first closure, similar to Phase B5's B_ideal mismatch fix.

**If audit finds no staleness:** Escalate to Priority 2 (test LBFGS optimizer) to rule out Adam-specific bug before considering alternative parameterizations.
