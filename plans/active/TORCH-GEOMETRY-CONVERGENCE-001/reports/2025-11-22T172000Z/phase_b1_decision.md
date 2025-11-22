# Phase B1 LBFGS Test Decision

## Test Configuration
- Optimizer: torch.optim.LBFGS(lr=1.0, max_iter=20, line_search_fn='strong_wolfe')
- Parameters: q_params (quaternion), log_scale (train_orientation=False for A_scale_only)
- Variant: A_scale_only (scale-only refinement, orientation fixed)
- Steps requested: 10 optimizer.step() calls
- Execution: Foreground, timeout=1200s
- Result: **TIMEOUT** (exit code 143, test did not complete within 20 minutes)

## Zero-Point Validation (Pre-Optimization)
- Chi² mapping path: **989,811.5**
- Chi² stage_a (U-matrix): **989,645.5**
- Relative difference: **-0.017%** (well within 0.1% tolerance)
- Correlation median: **0.9999999843**
- Verdict: **PASSED** ✓

Zero-point validation confirms that `derive_u_matrix_from_mosflm_a_star` bugfix (commit 826f4c9) works correctly when `use_mapping_zero_geometry=True` (direct MOSFLM A* usage, bypassing U @ B_ideal reconstruction).

## Telemetry Step 000 (First LBFGS Step)
- Chi²: **1,425,248,640** (1.425 billion)
- log_scale gradient: **294,909.5625** (~295k)
- q_params gradients: null (expected, train_orientation=False)
- Verdict: **CATASTROPHIC FAILURE** ✗

This chi²=1.425B matches **EXACTLY** the Phase A pre-bugfix signature (before commit 826f4c9), indicating that the LBFGS optimization loop is using a DIFFERENT code path that still computes B_ideal incorrectly (likely via cctbx fractionalization_matrix instead of MOSFLM-derived B_ideal).

## Telemetry Step 001 (Second LBFGS Step)
Test timed out before completing step 1 fully. Only step_001.json file exists but may be incomplete.

## Convergence Metrics (Incomplete - Test Timed Out)
- Test ran for 1200s (20 minutes) before timeout
- Completed: ~2 optimizer steps (telemetry_step_000.json, telemetry_step_001.json)
- Expected: 10 optimizer steps
- Missing artifacts: block_dof_results.json (final convergence summary)

**Timeout Analysis:**
- Log shows repetitive HKL grid builds (LBFGS backtracking line search evaluates closure many times per step)
- 2 steps in 1200s → ~600s per step → 10 steps would require ~6000s (100 minutes)
- LBFGS on CPU is prohibitively slow for this problem

## Decision Path

### Path A: LBFGS Convergence SUCCESS
**Criteria:** Chi² step 000 ~1M (not 1.4B) AND median_cc_after ≥ 0.99 AND chi2_ratio ≤ 1.005

**Verdict:** **NOT SELECTED** - Chi² step 000 is catastrophic (1.425B), not healthy (~1M)

### Path B: LBFGS Convergence FAILURE (Chi² Step 000 Catastrophic)
**Criteria:** Chi² step 000 ~1.4B (matches pre-bugfix signature)

**Verdict:** **SELECTED** ✓

**Evidence:**
1. Zero-point check PASSED (chi²=989k) → bugfix works in that code path
2. LBFGS step 0 FAILED (chi²=1.425B) → bugfix does NOT work in optimization loop code path
3. Chi²=1.425B is the EXACT pre-bugfix signature from Phase A
4. Massive log_scale gradient (295k) confirms parameters are catastrophically far from optimum
5. Telemetry path duplication bug FIXED (paths are clean), so this is NOT a data corruption issue

**Root Cause (High Confidence):**
The `derive_u_matrix_from_mosflm_a_star` bugfix returns `(U_matrix, B_ideal_reciprocal)` correctly, but somewhere in the LBFGS optimization loop, `components.B_ideal_reciprocal` is either:
- Being overwritten/mutated with the wrong value (cctbx fractionalization_matrix)
- Not being used at all (different code path computes B_ideal separately)
- Experiencing tensor aliasing or device/dtype mismatch causing reversion

**Recommended Actions (Priority Order):**
1. **Deep Diagnostic (Mandatory):** Instrument LBFGS closure with B_ideal checksum logging to identify WHERE and WHEN B_ideal diverges from the correct MOSFLM-derived value
2. **Code Audit:** Search for ALL uses of `fractionalization_matrix` in `stage_a_mapping_adam_debug.py` and `dbex/nanobrag_refinement.py` to find alternate B_ideal computation paths
3. **Tensor Lifecycle Audit:** Verify `components.B_ideal_reciprocal` is immutable (cloned/detached) and not subject to mutation during optimization
4. **Device/Dtype Consistency Check:** Ensure U_matrix and B_ideal_reciprocal are on same device and dtype before matmul in closure

### Path C: LBFGS Convergence PARTIAL
**Criteria:** Chi² step 000 OK (~1M) BUT median_cc_after < 0.99 OR chi2_ratio > 1.005

**Verdict:** **NOT SELECTED** - Chi² step 000 is catastrophic, not just suboptimal

## Selected Path
**Path B: LBFGS Convergence FAILURE (B_ideal Mismatch in Optimization Loop)**

## Confidence Level
**High**

## Rationale
1. **Reproducibility:** Chi²=1.425B signature appeared in BOTH the original attempt (2025-11-22T165000Z) and this rerun (2025-11-22T172000Z), with telemetry path fix applied. This rules out data corruption or path duplication as the cause.

2. **Specificity:** The chi² value is EXACTLY 1.425 billion in both runs, matching the pre-bugfix signature from Phase A. This is too specific to be coincidental - it indicates the SAME underlying B_ideal matrix is being used (cctbx fractionalization_matrix).

3. **Code Path Divergence:** Zero-point check uses `use_mapping_zero_geometry=True` → PASSED. LBFGS optimization uses `use_mapping_zero_geometry=False` → FAILED. This confirms the bugfix is incomplete - it works in one code path but not the other.

4. **Gradient Magnitude:** log_scale gradient of 295k is consistent with catastrophic B_ideal mismatch (scale factor trying to compensate for 1000x error in predicted intensities).

## Next Loop Focus
**CONVERGENCE-001 Phase B Deep Diagnostic:** Instrument LBFGS closure to identify B_ideal mismatch root cause

**Deliverables:**
1. Add B_ideal checksum/hash logging to LBFGS closure (entry and during A* reconstruction)
2. Add device/dtype logging for U_matrix and B_ideal_reciprocal
3. Run 2-step LBFGS diagnostic variant (reduced from 10 steps to save time)
4. Capture B_ideal lifecycle: creation → components assignment → closure entry → A* reconstruction
5. Identify EXACT point where B_ideal diverges from MOSFLM-derived value
6. Document root cause in `phase_b1_diagnostic_results.md`
7. Implement fix (likely: ensure components.B_ideal_reciprocal is immutable clone, not reference)

**Estimated Time:** 1-2 loops (diagnostic run + fix implementation)

**Exit Criteria:**
- B_ideal checksum in closure matches MOSFLM-derived value from `derive_u_matrix_from_mosflm_a_star`
- Chi² step 0 drops from 1.425B → ~1M (same as zero-point check)
- LBFGS convergence metrics show healthy behavior (chi² stable or improving)
