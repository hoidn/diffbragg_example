# Supervisor Handoff — TORCH-GEOMETRY-CONVERGENCE-001 Phase B2 Deep Diagnostic

## Summary
Diagnose catastrophic convergence failure via gradient/variance/forward-model telemetry to identify root cause (NaN/Inf, exploding magnitudes, variance instability).

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped Tests
tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — regression guard (cell+misset default path)

## Artifacts
plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/

## Do Now

**Checklist Items:** Phase B2 (Deep Diagnostic — Gradient Validation & Variance Analysis)

**Context:** Ralph's Phase B1 LBFGS validation (2025-11-22T183000Z) proved **Path B (Fix INCOMPLETE)** — B_ideal mismatch fix (commit e86fd4e) successfully resolved INITIALIZATION bug (zero-point chi²=989,811, step 0 chi²=1.13M, both healthy) but CONVERGENCE pathology persists unchanged (LBFGS steps 1-3: chi² 1.13M → 1.425B, CC 1.0 → -0.045). Failure signature is IDENTICAL to pre-fix PARITY-003 Phase C2 and optimizer-agnostic (reproduced with both Adam and LBFGS). **Root Cause Assessment:** Failure is NOT initialization (step 0 healthy), NOT optimizer choice (Adam+LBFGS both fail), so it MUST be a forward model/loss/gradient bug that manifests DURING OPTIMIZATION. Hypothesis verdicts: H1 (Adam hyperparameters) REJECTED, H2 (variance instability) PLAUSIBLE, H3 (gradient pathology) PLAUSIBLE, H4 (quaternion constraint) NOT TESTABLE with A_scale_only.

**Objective:** Execute Phase B2 deep diagnostic to identify SPECIFIC pathology: (a) NaN/Inf gradients, (b) exploding gradient magnitudes, (c) variance denominator instability, or (d) forward model numerical bug in updated-parameter path.

### Step 1: Implement Phase B2 Instrumentation

**Extend** `dbex/nanobrag_refinement.py` (Stage A LBFGS closure, U-matrix branch ~lines 968-1116) to capture comprehensive telemetry:

**1a. Gradient Telemetry** (before optimizer.step())
- Per-parameter gradient norms: `||∂L/∂q||`, `||∂L/∂log_scale||` (global L2 norms)
- Element-wise gradient stats: min/max/mean/std for `q_params.grad`, `log_scale.grad`
- NaN/Inf flags: `torch.isnan(grad).any()`, `torch.isinf(grad).any()` for each grad tensor
- Gradient sign consistency: count positive vs negative elements

**1b. Variance/Loss Telemetry** (after forward pass, before loss computation)
- I_model histogram: min/median/max/mean/std (on flattened valid pixels)
- V_denom = max(I_model + sigma_readout^2, sigma_floor^2): same histogram stats
- Clamp fraction: `(V_denom == sigma_floor^2).float().mean()` (fraction where sigma_floor dominates)
- Weighted residuals: `((I_target - I_model)^2 / V_denom)` histogram stats
- Loss components: total chi_squared, mean per-pixel chi_squared

**1c. Forward Model State** (after parameter update, before forward pass)
- log_scale value: current scalar
- q_params values: 4-element quaternion
- q_norm: `||q||` before normalization
- U_matrix checksum: `U_matrix.sum()` (simple hash to detect matrix changes)

**1d. Emit JSON per optimizer step:**
```python
telemetry = {
    "step": i,
    "parameters": {
        "log_scale": log_scale.item(),
        "q_params": q_params.detach().cpu().tolist(),
        "q_norm": torch.norm(q_params).item(),
        "u_matrix_checksum": U_matrix.sum().item()
    },
    "gradients": {
        "log_scale": {
            "norm": torch.norm(log_scale.grad).item() if log_scale.grad is not None else None,
            "value": log_scale.grad.item() if log_scale.grad is not None else None,
            "has_nan": bool(torch.isnan(log_scale.grad).any()) if log_scale.grad is not None else None,
            "has_inf": bool(torch.isinf(log_scale.grad).any()) if log_scale.grad is not None else None
        },
        "q_params": {
            "norm": torch.norm(q_params.grad).item() if q_params.grad is not None else None,
            "min": q_params.grad.min().item() if q_params.grad is not None else None,
            "max": q_params.grad.max().item() if q_params.grad is not None else None,
            "has_nan": bool(torch.isnan(q_params.grad).any()) if q_params.grad is not None else None,
            "has_inf": bool(torch.isinf(q_params.grad).any()) if q_params.grad is not None else None
        }
    },
    "variance": {
        "i_model_min": I_model_valid.min().item(),
        "i_model_median": I_model_valid.median().item(),
        "i_model_max": I_model_valid.max().item(),
        "i_model_mean": I_model_valid.mean().item(),
        "v_denom_min": V_denom_valid.min().item(),
        "v_denom_median": V_denom_valid.median().item(),
        "v_denom_max": V_denom_valid.max().item(),
        "clamp_fraction": (V_denom_valid == sigma_floor**2).float().mean().item()
    },
    "loss": {
        "chi_squared": loss.item(),
        "mean_per_pixel_chi_squared": (weighted_residuals.sum() / valid_pixel_count).item()
    }
}
```

Write to: `{out_dir}/telemetry/telemetry_step_{i:03d}.json`

**Notes:**
- Only instrument the U-matrix branch (lines 968-1116, where `config.use_u_matrix_parameterization` is True)
- Do NOT instrument cell+misset default path (keep regression guard unaffected)
- Ensure telemetry writes happen AFTER loss.backward() so gradients are populated
- Use `.detach().cpu()` to avoid device/autograd issues

### Step 2: Run Phase B2 Diagnostic Test (2-step LBFGS)

**Rationale:** 2 steps (not 10) — we need step 0 (initialization check) + step 1 (first catastrophic failure). Estimated ~10 minutes CPU.

```bash
mkdir -p plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/diagnostic/

KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 timeout 1200 python \
  plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix --use-lbfgs --phases 5 --dof-variants A_scale_only \
  --optimizer-steps 2 --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/diagnostic/ \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/diagnostic_test.log
```

**Success Criteria:**
- Telemetry step_000.json and step_001.json exist
- Zero-point check shows chi² ≈ 989k (reconfirm B_ideal fix)
- Diagnostic captures first catastrophic step (step 1)

### Step 3: Extract Diagnostic Metrics

```bash
echo "=== Step 0 (Initialization) ===" | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/diagnostic_summary.txt

jq '{step, chi_squared: .loss.chi_squared, log_scale: .parameters.log_scale, q_norm: .parameters.q_norm, gradients: {log_scale_norm: .gradients.log_scale.norm, q_params_norm: .gradients.q_params.norm, has_nan: (.gradients.log_scale.has_nan or .gradients.q_params.has_nan), has_inf: (.gradients.log_scale.has_inf or .gradients.q_params.has_inf)}, variance: {i_model_median, clamp_fraction}}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/diagnostic/telemetry/telemetry_step_000.json \
  | tee -a plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/diagnostic_summary.txt

echo -e "\n=== Step 1 (First Catastrophic Failure) ===" | tee -a plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/diagnostic_summary.txt

jq '{step, chi_squared: .loss.chi_squared, log_scale: .parameters.log_scale, q_norm: .parameters.q_norm, gradients: {log_scale_norm: .gradients.log_scale.norm, q_params_norm: .gradients.q_params.norm, has_nan: (.gradients.log_scale.has_nan or .gradients.q_params.has_nan), has_inf: (.gradients.log_scale.has_inf or .gradients.q_params.has_inf)}, variance: {i_model_median, clamp_fraction}}' \
  plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/diagnostic/telemetry/telemetry_step_001.json \
  | tee -a plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/diagnostic_summary.txt
```

### Step 4: Finite-Difference Gradient Validation (Step 0 Only)

**Objective:** Validate autograd gradients vs finite-difference approximation to detect sign flips, magnitude mismatches, or NaN bugs.

**Create script:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/bin/validate_gradients_fd.py`

**Pseudocode:**
```python
# Load step_000 telemetry to get parameter values at step 0
# Reconstruct forward pass: create simulator, compute loss with those parameters
# Compute autograd gradient: loss.backward()
# For log_scale:
#   - Compute FD gradient: (loss(log_scale + ε) - loss(log_scale - ε)) / (2ε), ε=1e-5
#   - Compare: ratio = autograd_grad / fd_grad, sign_match = sign(autograd) == sign(fd)
# Emit fd_validation.json with {parameter, autograd_grad, fd_grad, ratio, sign_match}
```

**Run:**
```bash
python plans/active/TORCH-GEOMETRY-CONVERGENCE-001/bin/validate_gradients_fd.py \
  --telemetry-step plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/diagnostic/telemetry/telemetry_step_000.json \
  --out-file plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/fd_validation.json
```

**Expected Output:**
- If autograd correct: ratio ≈ 1.0 (within 5%), sign_match=true
- If autograd wrong: ratio ≫ 1.0 or ≪ 1.0, or sign_match=false, or NaN

### Step 5: Synthesize Phase B2 Decision

Use Write tool to create `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/phase_b2_diagnostic_decision.md`

**Decision Paths:**

**Path H2 (Variance Instability):** If step_001 shows:
- clamp_fraction → 1.0 (sigma_floor dominates most pixels), OR
- v_denom_min → 0 (near-zero denominators), OR
- i_model values go negative/extreme
→ **Verdict:** Variance-weighted loss is numerically unstable with updated parameters
→ **Fix:** Adjust sigma_floor (increase from current value), add loss clamping (cap max chi² contribution per pixel), or switch to robust loss (Huber, etc.)

**Path H3a (Gradient NaN/Inf):** If step_000 or step_001 shows:
- has_nan=true OR has_inf=true in gradients
→ **Verdict:** Autograd produces NaN/Inf during backprop through forward model
→ **Fix:** Add gradient clipping (max_norm=1.0), switch to FP64 precision, investigate specific autograd operations (quaternion normalization, U @ B_ideal matmul)

**Path H3b (Gradient Explosion):** If step_000 shows:
- log_scale gradient norm > 1e6 (exploding), OR
- FD validation shows ratio > 10 (autograd overstates gradient by 10×)
→ **Verdict:** Gradients are numerically correct but catastrophically large
→ **Fix:** Gradient clipping (max_norm=1.0), lower learning rate (1e-6), or parameter reparameterization

**Path H3c (Gradient Sign Flip):** If FD validation shows:
- sign_match=false (autograd and FD have opposite signs)
→ **Verdict:** Autograd gradient direction is wrong (loss increases when it should decrease)
→ **Fix:** Investigate autograd graph for incorrect operations (missing .detach(), wrong loss formula)

**Path H4 (Forward Model Bug):** If step_000 gradients look healthy (no NaN/Inf, reasonable magnitudes, FD matches) BUT step_001 chi² explodes:
- Compare step_000 parameters vs step_001 parameters (did log_scale change by huge amount?)
- Check u_matrix_checksum change (did U matrix update correctly?)
→ **Verdict:** Updated parameters (after optimizer.step()) produce catastrophically wrong forward model
→ **Fix:** Investigate parameter update logic (log_scale clamping, quaternion renormalization, U-matrix reconstruction)

**Document must include:**
- Root cause hypothesis (H2, H3a, H3b, H3c, or H4) with HIGH/MEDIUM/LOW confidence
- Evidence summary (telemetry metrics, FD validation results)
- Recommended fix with implementation steps
- Next phase (B3: implement fix and validate, or escalate to alternative parameterization)

### Step 6: Update Implementation Plan

Edit `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md` Phase B checklist line B2:
- Mark `[x]` with diagnostic verdict summary
- Add pointer to phase_b2_diagnostic_decision.md

### Step 7: Regression Guard

```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  -v --tb=short \
  2>&1 | tee plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/pytest_regression.log
```

Verify cell+misset default path (no --use-u-matrix) still passes.

### Step 8: Write Summary

Create `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/summary.md` with Turn Summary format (3-5 sentences):
- Diagnostic test execution (2 steps, telemetry captured)
- Root cause verdict (H2/H3a/H3b/H3c/H4 with confidence)
- Recommended fix
- Next step (Phase B3 fix implementation or escalation)
- Artifacts pointer

### Step 9: Commit and Push

```bash
git add -A
git commit -m "TORCH-GEOMETRY-CONVERGENCE-001 Phase B2 diagnostic: [H2/H3/H4 verdict] - [brief finding] (tests: test_stage_a_expansion)"
git push
```

## How-To Map

See Do Now steps above for exact commands and implementation guidance.

**Key Implementation Notes:**

**Telemetry Placement:** Insert telemetry capture AFTER `loss.backward()` call (so gradients are populated) but BEFORE `optimizer.step()` (so parameters haven't changed yet). Typical structure:
```python
for i in range(num_steps):
    def closure():
        optimizer.zero_grad()
        # Forward pass → loss
        loss.backward()
        return loss

    # LBFGS calls closure() internally during line search
    optimizer.step(closure)

    # AFTER optimizer.step(), capture telemetry with CURRENT parameters + gradients from LAST closure call
    # (Note: gradients may be stale after optimizer.step(); best to capture INSIDE closure before return)
```

**Better approach:** Capture telemetry INSIDE closure (after loss.backward(), before return loss) so gradients are fresh.

**FD Validation Script:** Can be a standalone script that reconstructs the forward pass from telemetry parameters, or integrated into the closure as a one-time check at step 0.

## Pitfalls To Avoid

1. **Capturing telemetry BEFORE loss.backward()** — Gradients will be None
2. **Telemetry on cell+misset path** — Only instrument U-matrix branch to avoid regression guard pollution
3. **Expecting quaternion gradients with A_scale_only** — train_orientation=False, so q_params.grad is None. FD validation must focus on log_scale gradient only.
4. **Confusing step 0 initialization vs step 1 catastrophic failure** — Step 0 should show healthy chi² ~1.13M (matching B1 validation "before" metric), step 1 should show catastrophic chi² ~1.4B
5. **Not checking u_matrix_checksum** — If U matrix doesn't change between steps 0→1 despite optimizer.step(), quaternion update may be broken
6. **Premature fix implementation** — Diagnostic + decision ONLY this loop. Fix implementation is Phase B3 (next loop).

## If Blocked

**If telemetry step_000.json is missing:**
- Check log for errors during closure execution
- Verify telemetry_dir path construction (no double-prepending like B1 diagnostic)
- Run with --device cpu (no CUDA sync issues)

**If FD validation script too complex:**
- Skip FD validation for this loop; rely on NaN/Inf/magnitude analysis from telemetry
- Document as "FD validation deferred pending simpler harness"

**If diagnostic test times out before 2 steps:**
- Reduce to 1 step (step 0 only) and analyze initialization telemetry
- Compare step_000 telemetry to step_001 from B1 validation run (reuse artifacts)

## Findings Applied

- **REFINE-001** (LBFGS scale warm-start, NaN/Inf guards) — Check if log_scale gradient triggers NaN guard
- **PHYSICS-LOSS-002** (variance-weighted loss sigma-floor guard) — Analyze clamp_fraction and V_denom stability
- **GRADIENT-001** (autograd graph preservation) — Verify no .item()/.numpy() in forward model path

## Pointers

- **Prior Validation:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/phase_b1_validation_decision.md (Path B verdict, convergence FAILED)
- **Implementation Plan:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md (Phase B checklist)
- **Production Code (Closure):** dbex/nanobrag_refinement.py:968-1116 (Stage A U-matrix branch)
- **Test Script:** plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py
- **Telemetry Examples:** plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/telemetry/ (prior instrumentation, less comprehensive)

## Next Up

If Ralph finishes Phase B2 early and decision is clear:
- Can proceed to Phase B3 (implement fix) in same loop
- Otherwise, wait for supervisor review before fix implementation
