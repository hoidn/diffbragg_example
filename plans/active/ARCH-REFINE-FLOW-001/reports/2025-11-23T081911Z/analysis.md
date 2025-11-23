# Phase C2 Chi² Offset Root Cause Analysis (Loop i=209)

## Problem Statement

**Test Failure:** Engine delegation path has 9.3% chi-squared offset between Stage A final (7.053e+08) and Stage B initial (7.709e+08). Tolerance: 0.1%.

**Attempts So Far:**
1. Loop i=206: Fixed asdict() conversion bug at line 3089-3090 - offset persisted
2. Loop i=207-208: Added `baseline_crystal` parameter to `_build_final_bragg_from_stage_b_telemetry` helper - offset persisted

## Key Insights from Code Analysis

### 1. The Helper Ralph Fixed is NOT Used for Initial Chi²

The `_build_final_bragg_from_stage_b_telemetry` helper (lines 2713-2916) is called AFTER Stage B optimization completes to regenerate the final Bragg pattern. It is NOT involved in computing the **initial** chi² that causes the test to fail.

The initial chi² comes from `_run_stage_b_lbfgs` calling `compute_loss_stage_b` at iteration 0 (line 2635).

### 2. The Closure Already Handles Baseline Misset Correctly

Looking at `_build_stage_b_lbfgs_closure` (lines 2273-2593), the `compute_loss_stage_b` function correctly adds baseline + delta misset:

**Warm cache path (lines 2414-2416):**
```python
misset_override = misset_eval
if baseline_misset_eval is not None:
    misset_override = baseline_misset_eval + misset_eval
```

**Cold path (lines 2496-2498):**
```python
misset_override = misset_eval
if baseline_misset_eval is not None:
    misset_override = baseline_misset_eval + misset_eval
```

So the baseline_misset handling in the closure is **already correct**.

### 3. StageB.run() Parameter Extraction Looks Correct

StageB.run() (lines 140-199):
- Line 151: Extracts `misset_xyz_deg_delta_final` from `stage_a_telemetry['param_deltas']['misset_xyz_deg']['delta']` ✓ CORRECT (delta only)
- Line 176: Creates tensor from delta ✓ CORRECT
- Lines 178-183: Computes `baseline_misset_deg_tensor` separately ✓ CORRECT
- Line 288: Passes `baseline_misset_deg_tensor` to closure ✓ CORRECT

### 4. StageA Telemetry Structure is Correct

StageA.run() (lines 287-293) stores:
- `'initial'`: baseline_misset (or [0,0,0])
- `'final'`: baseline + delta (total misset)
- `'delta'`: delta only (perturbation)

This structure is correct for the incremental approach.

## Hypothesis: The Real Bug

Given that:
1. The closure handles baseline_misset correctly
2. StageB extracts parameters correctly
3. The telemetry structure is correct

**The bug must be in one of these locations:**

### H1: Cell Parameter Reconstruction Mismatch

StageB.run() lines 166-173 reconstructs cell parameters:
```python
cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta)
cell_b_tensor = cell_params[1] * torch.exp(log_cell_b_delta)
cell_c_tensor = cell_params[2] * torch.exp(log_cell_c_delta)
cell_alpha_tensor = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
cell_beta_tensor = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
cell_gamma_tensor = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta
```

**Potential issue:** This uses the SAME `crystal` object to extract `cell_params`, but Stage A's final cell is NOT the same as the baseline cell. The `log_cell_*_delta` values are deltas from the BASELINE, so we should be using `cell_params[0] * torch.exp(log_cell_a_delta)` starting from the **baseline** crystal params, not the potentially perturbed `crystal` params.

### H2: Scale Parameter Mismatch

StageB passes `log_scale` (Stage A's final optimized scale) to the closure at line 225. This gets used in the Bragg scaling at line 2457:
```python
bragg_scaled = bragg_patch * torch.exp(log_scale_clamped)
```

But we need to verify this is the SAME scale that was used in Stage A's final validation.

### H3: HKL Grid or Shell Indices Mismatch

Stage B initializes shell_modifier_raw to zeros (which becomes 1.0 after softplus), so the HKL grid should be unchanged. But we need to verify that the HKL grid passed to StageB is exactly the same grid used in Stage A's final validation.

### H4: Device/Dtype Mismatch

PERF-WARM-011/012 has CPU fallback logic for canonical detector runs. Maybe the initial chi² is computed on a different device than Stage A's final validation?

## Recommended Diagnostic Steps

1. **Signature fix:** Remove erroneous `=None` defaults from `_build_final_bragg_from_stage_b_telemetry` (lines 2720-2726)

2. **Telemetry injection:** Add detailed logging to capture:
   - Stage A final chi² computation parameters (cell, misset, log_scale, device)
   - Stage B initial chi² computation parameters (same values)
   - Diff of all parameters between A final and B initial

3. **Hypothesis testing:**
   - H1: Check if `crystal.get_unit_cell().parameters()` in StageB.run() line 163 returns baseline or perturbed values
   - H2: Verify log_scale matches between Stage A final and Stage B initial
   - H3: Verify HKL grid integrity
   - H4: Check device routing (CPU vs CUDA)

4. **Controlled reproduction:**
   - Extract exact parameters from Stage A final validation
   - Manually call compute_loss_stage_b with those parameters
   - Verify chi² matches Stage A final

## Next Actions

Create a diagnostic script that captures full parameter state at the boundary between Stage A and Stage B, then compares the two chi² computations step by step.
