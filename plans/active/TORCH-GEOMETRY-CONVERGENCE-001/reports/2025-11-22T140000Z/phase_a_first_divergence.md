# Phase A First Divergence Analysis

## Executive Summary

Telemetry analysis reveals **catastrophic failure at step 0** (before any optimizer updates), indicating the problem is NOT optimizer-related but rather a **forward model or initialization bug**. The quaternion U-matrix path produces chi-squared 1.425B at zero parameters, which is ~1000× worse than expected (~1.13M from PARITY-003 zero-point validation).

## Telemetry Summary (9 steps captured, step 000-008)

### Step 0 (Initial State, Before First Optimizer Update)
- **Parameters:**
  - `q_params`: `[-0.3125, 0.8748, -0.2550, 0.2684]` (unit norm 1.0)
  - `log_scale`: `-0.2059`
- **Loss:**
  - `chi_squared`: **1,425,248,640** (1.425B)
  - Expected: ~1.13M (from PARITY-003 Phase C2 zero-point check)
  - **Deviation: +125,948% (1000× worse)**
- **Gradients:**
  - `grad_q_norm`: **null** (expected - A_scale_only has `train_orientation=False`)
  - `grad_log_scale`: **294,909.56** (massive!)
- **Variance Components:** All null (simplified telemetry in script, not available)

### Step 8 (Final Captured Step)
- **Parameters:**
  - `q_params`: **unchanged** `[-0.3125, 0.8748, -0.2550, 0.2684]` (frozen, train_orientation=False)
  - `log_scale`: `-0.2067` (tiny delta -0.0008 from step 0)
- **Loss:**
  - `chi_squared`: **1,425,249,792** (1.425B, +1152 from step 0 = +0.00008%)
- **Gradients:**
  - `grad_log_scale`: **294,672.91** (still massive, barely changed)

### Progression Analysis
- **Chi-squared trajectory:** 1.425B → 1.425B (flat, variations < 0.0001%)
- **log_scale gradient trajectory:** ~295k → ~295k (consistent, massive)
- **q_params:** Completely frozen (expected for A_scale_only)
- **log_scale parameter:** Tiny movements (-0.2059 → -0.2067, delta -0.0008)

## First Divergence Point

**Step Index:** **0** (catastrophic failure **before** any optimizer updates)

**Primary Failure Mode:** `forward_model_pathology` (NOT optimizer/gradient pathology)

### Evidence
1. **Chi-squared is 1000× worse than expected at initialization** (1.425B vs 1.13M), before Adam has taken a single step
2. **log_scale gradient is massive** (~295k) at step 0, indicating the loss surface is pathological even at the starting point
3. **Optimizer makes essentially no progress** (chi-squared changes < 0.0001%, log_scale changes -0.0008)
4. **Gradients are clean** (no NaN/Inf flags set)

## Root Cause Hypothesis Classification

### H1 (Adam Hyperparameters) — **REJECTED**
- Problem manifests **at step 0 before optimizer runs**
- Gradient magnitude (~295k) is extreme, but optimizer makes no progress regardless of LR
- **Not an optimizer tuning issue**

### H2 (Variance-Weighted Loss Numerical Instability) — **PLAUSIBLE**
- Massive log_scale gradient suggests variance denominator may be pathological
- Need variance component telemetry (masked_mse, clamp_fraction, i_model stats) to confirm
- **Requires deeper instrumentation** in `dbex/nanobrag_refinement.py` closure

### H3 (Gradient Pathology) — **PARTIALLY SUPPORTED**
- **Gradients are NOT NaN/inf** (grad_has_nan=false, grad_has_inf=false)
- **Gradients are NOT exploding during backprop** (values ~295k are large but stable)
- **Forward model is wrong** (chi-squared 1.425B at zero params suggests A* computation bug or geometry mismatch)
- **Gradient direction may be correct but starting point is wrong**

### H4 (Quaternion Constraint Handling) — **NOT TESTABLE with A_scale_only**
- `q_params` is frozen (train_orientation=False), so quaternion normalization/constraint issues cannot be diagnosed with this variant
- **Need C_scale_plus_orientation or D_full telemetry** to test quaternion gradient flow

## Comparison with PARITY-003 Zero-Point Validation

PARITY-003 Phase C2 "zero_point_check" (plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/zero_point_check.json) reported:
- `corr_median_vs_mapping`: **0.9999999843** (essentially perfect parity)
- `max_abs_diff`: **85.14 photons** (acceptable forward model error)
- **Implied chi-squared:** ~1.13M (from PARITY-002 A_scale_only Phase 5 before optimization)

**Current telemetry (same code path, same U-matrix mode):**
- `chi_squared`: **1.425B** (1000× worse)
- **Discrepancy:** +1.424B difference at initialization

### Hypothesis: Different Test Contexts

**Possible explanations:**
1. **Different experiment files**: PARITY-003 used canonical `refGeom.expt`; this test may be using a different file with different cell/det parameters
2. **Different forward model parameters**: ROI sampling, N_cells, spot_scale, or other simulator settings may differ between zero-point check and Adam debug script
3. **Different chi-squared computation**: Zero-point check may use full-image chi-squared while Adam loop uses ROI-sampled chi-squared
4. **B_ideal_reciprocal mismatch**: Possible shape bug or computation error in quaternion path's B_ideal initialization (similar to PARITY-002 Phase C2 bugfix at line 325 `.reshape(3,3)`)

## Recommended Next Actions

### Immediate (Phase A4-A6)
1. **Compare zero-point check vs Adam initialization**:
   - Read `zero_point_check.json` from this run (plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/)
   - Verify chi-squared at zero params matches PARITY-003 expectations (~1.13M)
   - If mismatch, diagnose difference in forward model setup between zero-point check and Adam loop

2. **Inspect forward model at step 0**:
   - Add logging to `_stage_a_forward` to capture A_star, U_matrix, B_ideal_reciprocal shapes/values
   - Verify quaternion → U → A* computation is correct at initialization
   - Check if B_ideal_reciprocal has same shape bug (flat array vs 3×3 matrix)

3. **Capture full variance telemetry**:
   - Instrument `dbex/nanobrag_refinement.py` closure (not script) to get masked_mse, clamp_fraction, i_model stats
   - Determine if variance-weighted loss denominator is causing pathological gradients

4. **Test with D_full variant**:
   - Rerun with `--dof-variants D_full` to enable quaternion gradients (train_orientation=True)
   - Verify quaternion gradient norms, check for NaN/Inf, test H4 quaternion constraint hypothesis

### Escalation (if Phase A4-A6 confirms forward model bug)
- If chi-squared mismatch is due to B_ideal computation or quaternion_to_matrix bug:
  → Fix implementation bug and rerun Phase A2 validation
- If chi-squared mismatch is due to fundamental geometry incompatibility:
  → Escalate to TORCH-GEOMETRY-CONVERGENCE-002 (re-examine A* = U @ B_ideal identity and quaternion parameterization assumptions)

## Findings Update (Pending Phase A4-A6 Completion)

**Preliminary CONVERGENCE-002 Finding:**
> **CONVERGENCE-002 (Quaternion U-Matrix Forward Model Pathology):** Quaternion U-matrix parameterization produces chi-squared 1.425B at zero parameters (1000× worse than expected ~1.13M), indicating forward model or initialization bug. Massive log_scale gradient (~295k) at step 0 suggests variance-weighted loss denominator pathology or A* computation error. Optimizer makes no progress (chi-squared drift < 0.0001%) despite clean gradients (no NaN/Inf). First divergence at step 0 (before optimizer runs) rules out optimizer hyperparameter issues (H1) and points to forward model geometry mismatch (H3) or variance numerical instability (H2). Root cause investigation requires variance telemetry instrumentation in closure and comparison with zero-point check forward model setup.

**Status:** Preliminary diagnosis pending Phase A4-A6 evidence (variance telemetry, zero-point check comparison, B_ideal shape validation).
