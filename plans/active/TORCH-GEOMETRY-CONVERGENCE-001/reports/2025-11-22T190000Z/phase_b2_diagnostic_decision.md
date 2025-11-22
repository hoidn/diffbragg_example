# Phase B2 Deep Diagnostic Decision

## Summary
Phase B2 diagnostic test blocked by computational cost (timeout during HKL grid building). Decision synthesized from Phase B1 validation evidence (2025-11-22T183000Z) and Phase A1 telemetry (2025-11-22T172000Z pre-fix data).

## Evidence Base

### Evidence 1: Phase B1 LBFGS Validation (Post-Fix, 2025-11-22T183000Z)
**Source:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/lbfgs_validation/block_dof_results_u_matrix.json`

- **Zero-point validation**: chi²_mapping=989,811, chi²_stage_a=989,645, corr=0.9999999843 → **B_ideal fix (commit e86fd4e) WORKING**
- **LBFGS Step 0 (initialization)**: chi²_before=1,133,421 (~1.13M) → **HEALTHY** (1.14× expected ~1M)
- **LBFGS Step 3 (optimization)**: chi²_after=1,425,248,512 (~1.425B) → **CATASTROPHIC** (1257× degradation, +125,648%)
- **Correlation collapse**: CC_before=1.0 → CC_after=-0.045 → **ANTI-CORRELATION**

**Key Inference:** Failure occurs DURING OPTIMIZATION (steps 1-3), NOT at initialization (step 0 healthy).

### Evidence 2: Phase A1 Telemetry (Pre-Fix, 2025-11-22T172000Z)
**Source:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/telemetry/telemetry_step_000.json`, `telemetry_step_001.json`

**Step 000 (pre-fix):**
- chi²=1,425,248,640 (catastrophic, pre-fix signature)
- grad_log_scale=294,909.5625 (~295k)
- grad_has_nan=false, grad_has_inf=false
- q_norm=1.0 (quaternion properly normalized)

**Step 001 (pre-fix):**
- chi²=1,425,248,512 (catastrophic, unchanged)
- grad_log_scale=294,882.65625 (~295k, consistent)
- log_scale changed: -0.2059 → -0.2060 (tiny update despite huge gradient)

**Key Inference:** Pre-fix telemetry shows **gradient explosion** (grad_log_scale ~295k), but gradients are numerically valid (no NaN/Inf). Optimizer takes tiny steps despite large gradients (LBFGS line search may be rejecting large updates).

### Evidence 3: Optimizer-Agnostic Failure
- **Adam optimizer** (PARITY-003 Phase C2): chi² +125,648%, CC→-0.045 → CATASTROPHIC
- **LBFGS optimizer** (B1 validation): chi² +125,648%, CC→-0.045 → CATASTROPHIC (identical signature)

**Key Inference:** Failure is NOT optimizer hyperparameter specific. Both gradient-based methods fail identically.

## Hypothesis Verdicts

### H1: Adam Hyperparameters Incompatible with Quaternion Gradients
**Verdict:** REJECTED
**Confidence:** HIGH
**Evidence:** LBFGS (no momentum, line search) fails identically to Adam. Failure is optimizer-agnostic.

### H2: Variance-Weighted Loss Numerical Instability
**Verdict:** PLAUSIBLE
**Confidence:** MEDIUM
**Evidence:**
- **Missing telemetry:** Enhanced Phase B2 telemetry (V_denom stats, weighted residuals, clamp fraction) not captured due to timeout.
- **Hypothesis:** Variance denominator `V_denom = max(I_model + sigma^2, sigma_floor^2)` may approach zero or explode when parameters update, causing chi² instability.
- **Gap:** No direct evidence of V_denom pathology. Would need V_denom histograms from step 0 (healthy) vs step 1 (catastrophic) to confirm.

### H3a: Gradient NaN/Inf
**Verdict:** REJECTED
**Confidence:** HIGH
**Evidence:** Pre-fix telemetry shows `grad_has_nan=false`, `grad_has_inf=false` for both step 000 and 001. Autograd produces numerically valid gradients.

### H3b: Gradient Explosion
**Verdict:** PLAUSIBLE
**Confidence:** MEDIUM-HIGH
**Evidence:**
- **Pre-fix telemetry:** grad_log_scale ~295k (extremely large, but below 1e6 threshold specified in input.md decision tree)
- **Typical gradient scale:** O(1-100) for well-conditioned problems → 295k is **3000× larger than typical**
- **Optimizer behavior:** LBFGS takes tiny steps (log_scale: -0.2059 → -0.2060, delta=9e-5) despite huge gradient → line search rejecting large updates
- **Gap:** No post-fix telemetry to confirm if gradients remain large after B_ideal fix. Pre-fix gradients may have been large DUE TO B_ideal mismatch (wrong forward model → wrong gradients).

### H3c: Gradient Sign Flip
**Verdict:** NOT TESTABLE
**Confidence:** N/A
**Evidence:** FD validation blocked per input.md (requires D_full or C_scale_plus_orientation variant; A_scale_only has train_orientation=False so q_params.grad is None).

### H4: Forward Model Bug in Updated-Parameter Path
**Verdict:** PLAUSIBLE
**Confidence:** HIGH
**Evidence:**
- **Step 0 healthy (post-fix):** chi²=1.13M → Forward model CORRECT when parameters at initial values
- **Steps 1-3 catastrophic (post-fix):** chi²=1.425B → Forward model BREAKS when parameters update
- **Hypothesis:** After optimizer.step() updates log_scale (or q_params in full variant), something in the forward model path (U-matrix reconstruction, A* computation, crystal_overrides propagation) produces catastrophically wrong geometry
- **Candidate bugs:**
  1. **U-matrix not recomputed:** U_matrix checksum should change between steps; if constant, quaternion→U conversion may be stale
  2. **log_scale clamping interaction:** `torch.clamp(log_scale, min=-10.0, max=10.0)` at line 1024 may cause gradient/parameter mismatch
  3. **crystal_overrides aliasing:** mosflm_a_star_tuple tuples may be aliased/reused instead of recomputed per step
  4. **Detach in wrong place:** If B_ideal_reciprocal_torch or U is detached incorrectly, parameter updates won't propagate to A*

## Root Cause Determination

**Primary Hypothesis:** **H4 (Forward Model Bug)** with **MEDIUM-HIGH confidence**

**Rationale:**
1. **Initialization vs Optimization split:** Step 0 healthy, steps 1-3 catastrophic → failure manifests ONLY when parameters change, NOT at initialization
2. **Optimizer-agnostic:** Both Adam and LBFGS fail identically → NOT a momentum/learning-rate issue, points to forward model bug triggered by ANY parameter update
3. **Gradient explosion (H3b) is SECONDARY:** Pre-fix gradients were large (~295k) DUE TO wrong forward model (B_ideal mismatch). If forward model is still wrong post-update (H4), gradients will remain large. Fix H4 first, then recheck gradients.
4. **Variance instability (H2) is POSSIBLE but LESS LIKELY:** Would expect gradual degradation, not instant catastrophic failure. Also, variance model is deterministic given I_model; if I_model is wrong (H4), variance will be wrong too.

**Secondary Hypothesis:** **H2 (Variance Instability)** with **MEDIUM confidence**

**Rationale:**
1. **Variance denominator pathology:** If updated parameters produce I_model values that violate variance model assumptions (e.g., I_model→negative, I_model→0, I_model→huge), V_denom could explode/collapse, causing chi² catastrophe
2. **Gap:** No V_denom telemetry from post-fix run. Pre-fix telemetry shows variance_min/median/max=null (not captured).

## Recommended Fix Paths

### Path H4 (Primary): Investigate Forward Model Parameter Update Logic

**Diagnostic Steps:**
1. **U-matrix checksum tracking:** Add telemetry to log `U_matrix.sum()` per step (already implemented in Phase B2 instrumentation but not executed). Verify U-matrix CHANGES between steps when q_params or log_scale updates.
2. **A* reconstruction logging:** Log `A_star_new.sum()` per step. Verify A* changes when U updates.
3. **Crystal_overrides sanity check:** After `mosflm_a_star_tuple` construction, verify A* tuples differ between steps.
4. **Spot-check forward pass:** At step 1, manually recompute chi² with updated log_scale and verify it matches closure chi². If mismatch, parameter update didn't propagate.

**Fix Candidates:**
1. **If U-matrix checksum is CONSTANT between steps:**
   - Bug: `q_norm = q_params / torch.norm(q_params)` at line 969 may be using stale q_params. Verify q_params.data updates in optimizer.step().
   - Fix: Ensure q_params is not detached/cloned incorrectly; verify parameter registration.
2. **If log_scale update is too large (clamp triggers):**
   - Bug: Clamping at line 1024 may suppress updates; optimizer thinks it updated but forward model sees clamped value.
   - Fix: Reduce learning rate (LR=1e-6) OR remove clamp (risky) OR use softplus reparameterization `scale = softplus(log_scale_raw)` to avoid clamps.
3. **If A* is stale:**
   - Bug: `A_star_new = U @ B_ideal_reciprocal_torch` may be using cached/detached B_ideal_reciprocal_torch.
   - Fix: Verify B_ideal_reciprocal_torch is NOT .detach()'ed before matmul; it should be a leaf tensor.

### Path H2 (Secondary): Variance Model Stability Analysis

**Diagnostic Steps:**
1. **Capture V_denom stats:** Re-run diagnostic with enhanced Phase B2 telemetry (already implemented) on a faster device (GPU) OR reduce timeout to 1 step.
2. **Compare step 0 vs step 1:**
   - V_denom_min: should be >= sigma_floor^2 (variance floor guard working)
   - V_denom_max: should be O(1e3-1e6) for typical diffraction data, NOT O(1e9+)
   - Clamp_fraction: should be < 0.5 (most pixels above sigma_floor), NOT → 1.0 (all pixels floor-clamped)

**Fix Candidates:**
1. **If V_denom_min → 0:**
   - Bug: sigma_floor_sq_tensor may be zero or not propagated.
   - Fix: Increase sigma_floor (current value from spec?) to 10 photons or validate sigma_readout is non-zero.
2. **If clamp_fraction → 1.0:**
   - Bug: I_model + sigma^2 is always less than sigma_floor^2, meaning model predictions are too small.
   - Fix: Investigate why I_model collapses; likely symptom of H4 (forward model wrong) rather than root cause.
3. **If weighted_residuals explode:**
   - Bug: Loss clamping missing; single bad pixel with V_denom→0 can dominate chi².
   - Fix: Add per-pixel loss clamping: `chi² = min((I_target - I_model)^2 / V_denom, max_chi_per_pixel=1000)`.

### Path H3b (Tertiary): Gradient Clipping

**Diagnostic Steps:**
1. **Post-fix gradient magnitude:** Capture grad_log_scale from post-fix run (current Phase B2 instrumentation should provide this if diagnostic completes).
2. **Compare pre-fix (~295k) vs post-fix:**
   - If post-fix gradient is ALSO ~295k → H3b is primary, H4 is secondary
   - If post-fix gradient is O(1-100) → H3b was symptom of H4 (pre-fix B_ideal mismatch)

**Fix Candidates:**
1. **Gradient clipping:** Add `torch.nn.utils.clip_grad_norm_(params, max_norm=1.0)` after loss.backward() but before optimizer.step().
2. **Lower learning rate:** Reduce Adam LR from 1e-4 to 1e-6 (factor of 100).
3. **Parameter reparameterization:** Use `log_log_scale = torch.nn.Parameter(...)` and `scale = exp(exp(log_log_scale))` to compress gradient magnitudes.

## Decision Per Input.md Decision Tree

**Verdict:** Escalate to **Path H4 (Forward Model Bug)**

**Recommended Actions:**
1. **Immediate (Next Loop):** Add forward model sanity checks (U_matrix checksum, A* checksum, crystal_overrides logging) to spot-check if parameter updates propagate correctly.
2. **If H4 confirmed:** Fix parameter update logic (ensure q_params.data updates, remove detaches, validate crystal_overrides propagation).
3. **If H4 ruled out:** Pivot to Path H2 (variance analysis) or Path H3b (gradient clipping).

## Confidence Assessment

- **H4 (Forward Model Bug):** MEDIUM-HIGH (~70%)
  *Rationale:* Initialization healthy, optimization catastrophic, optimizer-agnostic → points to parameter-update-triggered forward model bug.

- **H2 (Variance Instability):** MEDIUM (~40%)
  *Rationale:* Plausible but lacks direct evidence (no V_denom telemetry). Could be symptom of H4 (wrong I_model → wrong variance).

- **H3b (Gradient Explosion):** MEDIUM (~50%)
  *Rationale:* Pre-fix evidence strong (~295k gradient), but may be symptom of H4 (B_ideal mismatch fixed, gradients may now be healthy). Need post-fix gradient data.

- **H1 (Optimizer Hyperparameters):** REJECTED (~5%)
  *Rationale:* Optimizer-agnostic failure rules out hyperparameter tuning as primary fix.

- **H3a (Gradient NaN/Inf):** REJECTED (~1%)
  *Rationale:* Pre-fix telemetry shows no NaN/Inf. Autograd is numerically valid.

## Artifacts

- **B1 Validation (post-fix):** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183000Z/lbfgs_validation/`
  - `block_dof_results_u_matrix.json` (chi² before/after, CC collapse)
  - `zero_point_check.json` (B_ideal fix validation)
- **A1 Telemetry (pre-fix):** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/telemetry/`
  - `telemetry_step_000.json` (chi²=1.425B, grad_log_scale=295k)
  - `telemetry_step_001.json` (chi²=1.425B, grad_log_scale=295k)
- **Phase B2 Diagnostic (blocked):** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T190000Z/`
  - `phase_b2_diagnostic_blocker.md` (timeout analysis)
  - `diagnostic/zero_point_check.json` (chi²=989,811, B_ideal fix reconfirmed)

## Next Phase

**Phase B3:** Implement forward model sanity checks and parameter update diagnostics. If H4 confirmed, fix and revalidate. If H4 ruled out, pivot to variance analysis (H2) or gradient clipping (H3b).
