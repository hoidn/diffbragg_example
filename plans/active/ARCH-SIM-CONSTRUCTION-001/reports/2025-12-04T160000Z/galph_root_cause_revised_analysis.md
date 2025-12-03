# ARCH-SIM-CONSTRUCTION-001 — Root Cause Analysis (Revised 2025-12-04T160000Z)

## Executive Summary

After three implementation attempts and empirical debug instrumentation, the root cause is now clear:

**Stage A's `log_scale_baseline` is computed from simulator outputs that were ALREADY scaled by `sqrt(spot_scale)`.** This means `exp(log_scale_baseline)` embeds a **division by `sqrt(spot_scale)`**, not a multiplication.

Therefore, reconstruction must **multiply by `sqrt(spot_scale)`** to cancel this embedded division and produce the correct absolute intensity.

However, empirical measurements show that doing so produces outputs ~23,900× too LARGE, not too small. This indicates a **fourth-root** error, suggesting **double application** of the sqrt factor.

## Empirical Evidence (Loop i=451, 2025-12-04T121500Z)

From `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T121500Z/debug_output.txt`:

```
log_scale_baseline_value: 20.138489595
scale_factor (after exp): 557230080.0 = 5.57e8
sqrt_spot_scale: 557230532.6778347 = 5.57e8
spot_scale_override: 3.105058665484234e+17

bragg_panel[0] mean (raw sim output): 1.839284e-14
bragg_scaled[0] mean (after scale_factor): 1.024905e-05
bragg_full mean (final output): 1.024904e-05
```

**Test Assertions:**
- Expected: `bragg_after_mean ≈ 0.24`
- Observed: `1.025e-05`
- **Missing factor: `0.24 / 1.025e-05 ≈ 23,400 ≈ sqrt(5.57e8)`**

**Current code** (reconstruction.py:252):
```python
bragg_scaled = bragg_panel * scale_factor  # No sqrt multiplication
```

## Stage A Baseline Derivation (Two Paths)

### Path 1: Initial Guess (stage_a.py:164-174)

```python
# Priority 2: Standard calibration path
if log_scale_baseline is None and config.calibration_metadata is not None:
    spot_scale_override = config.calibration_metadata.get("spot_scale_override")
    if spot_scale_override is not None:
        sqrt_spot_scale = float(np.sqrt(spot_scale_override))
        log_scale_baseline = float(np.log(sqrt_spot_scale))  # = log(5.57e8) ≈ 20.14
```

**Result:** `log_scale_baseline = log(sqrt(spot_scale))` → `exp(baseline) = sqrt(spot_scale)`

### Path 2: Refined from Simulator Output (stage_a.py:431-467)

```python
# Compute target mean from MASKED pixels
target_mean_masked = target_t[loss_mask_t].mean()

# Build zero-iteration Bragg stack from warmed simulators
bragg_samples = [simulator.run() for simulator in stage_a_ctx.simulators]
bragg_stack = torch.stack(bragg_samples, dim=0)

# Apply spot_scale_override per SCALE-002 (sqrt factor)
sqrt_spot_scale = float(np.sqrt(spot_scale_override))
bragg_stack_scaled = bragg_stack * sqrt_spot_scale  # ← MULTIPLY by sqrt

# Compute masked mean from SCALED output
model_mean_masked = bragg_stack_scaled[loss_mask_t].mean()  # = bragg_raw_mean * sqrt(spot_scale)

# Compute log_scale_baseline from ratio
log_scale_baseline = float(np.log(target_mean_masked / model_mean_masked))
                    = log(target_mean / (bragg_raw_mean * sqrt(spot_scale)))
```

**Result:**
```
exp(log_scale_baseline) = target_mean / (bragg_raw_mean * sqrt(spot_scale))
```

**This embeds a DIVISION by `sqrt(spot_scale)`, not a multiplication!**

## Stage A Loss Application (stage_a.py:1186-1303)

```python
# Clamp log_scale and apply baseline
log_scale_baseline_value = param_values.get('log_scale_baseline')  # From refined path above
log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
log_scale_clamped = log_scale_baseline_value + log_scale_delta_clamped

# Inside ROI loop:
bragg_patch = simulator.run()
bragg_scaled = bragg_patch * torch.exp(log_scale_clamped)
             = bragg_patch * exp(log_scale_baseline + delta)
             = bragg_patch * (target_mean / (bragg_raw_mean * sqrt(spot_scale))) * exp(delta)
```

If `bragg_patch ≈ bragg_raw_mean` (same simulator state), this simplifies to:
```
bragg_scaled ≈ target_mean / sqrt(spot_scale) * exp(delta)
```

For `delta ≈ 0` (converged refinement):
```
bragg_scaled ≈ target_mean / sqrt(spot_scale)
```

**Stage A's output intensity is DIVIDED by `sqrt(spot_scale)`, not multiplied!**

## Reconstruction Scaling (reconstruction.py:235-252)

**Current code:**
```python
scale_factor = torch.exp(log_scale_clamped)  # = exp(20.138 + delta) ≈ 5.57e8

for pid, sim in zip(sampled_panel_ids, simulators):
    bragg_panel = sim.run()  # Raw output: 1.839e-14
    bragg_scaled = bragg_panel * scale_factor  # = 1.839e-14 * 5.57e8 = 1.025e-05
```

**Observed:** `bragg_scaled = 1.025e-05`

**Expected:** `bragg_scaled ≈ 0.24`

**Missing factor:** `0.24 / 1.025e-05 ≈ 23,400 ≈ sqrt(spot_scale)`

## The Paradox

Based on the math above, reconstruction should MULTIPLY by `sqrt(spot_scale)` to cancel the division embedded in `log_scale_baseline`:

```
bragg_final = bragg_raw * exp(log_scale_baseline) * sqrt(spot_scale)
            = bragg_raw * (target_mean / (bragg_raw_mean * sqrt(spot_scale))) * sqrt(spot_scale)
            = bragg_raw * target_mean / bragg_raw_mean
            ≈ target_mean  (if bragg_raw ≈ bragg_raw_mean)
```

**This suggests the fix is:**
```python
bragg_scaled = bragg_panel * scale_factor * sqrt_spot_scale
```

**But** when Ralph tried this (commit acea29ef, 2025-12-04T010500Z), the output was **too LARGE** by ~23,900×:
- Observed: `bragg_after_mean = 5711`
- Expected: `0.24`
- Ratio: `5711 / 0.24 ≈ 23,800 ≈ sqrt(spot_scale)`

This is a **fourth-root error**: `(spot_scale)^(1/4)`, indicating DOUBLE application of the sqrt factor.

## Hypothesis: Simulator Output Already Scaled

The only way to reconcile the math is if the **raw simulator output** (1.839e-14) is ALREADY incorporating some scaling factor.

Let me check what the "unscaled" simulator output should be by working backwards from the expected result:

**From the double-sqrt experiment (commit acea29ef):**
```
bragg_final = bragg_raw * scale_factor * sqrt_spot_scale
5711 = 1.839e-14 * 5.57e8 * 5.57e8
5711 ≈ 1.839e-14 * 3.1e17  ✓ (matches)
```

**Expected result:**
```
bragg_expected = 0.24
```

**Implied "correct" raw simulator output:**
```
bragg_raw_correct = bragg_expected / (scale_factor * sqrt_spot_scale)
                  = 0.24 / (5.57e8 * 5.57e8)
                  = 0.24 / 3.1e17
                  = 7.7e-19
```

**But we observe:** `bragg_raw = 1.839e-14`

**Ratio:** `1.839e-14 / 7.7e-19 ≈ 23,900 ≈ sqrt(spot_scale)`

**This means the simulator is ALREADY applying `sqrt(spot_scale)` internally, despite the factory contract saying it should be applied post-run!**

OR: The baseline derivation is WRONG and should NOT include the sqrt division.

## Revised Hypothesis: Baseline Derivation Mismatch

Let me re-examine the baseline derivation. Stage A computes (lines 442-457):

```python
bragg_stack_scaled = bragg_stack * sqrt_spot_scale  # Multiply raw output by sqrt
model_mean_masked = bragg_stack_scaled[mask].mean()  # Mean of SCALED output
log_scale_baseline = log(target_mean / model_mean_masked)
```

If the **raw** simulator output (before sqrt multiplication) has mean `M_raw`, then:
```
model_mean_masked = M_raw * sqrt(spot_scale)
log_scale_baseline = log(target_mean / (M_raw * sqrt(spot_scale)))
```

So:
```
exp(log_scale_baseline) = target_mean / (M_raw * sqrt(spot_scale))
```

Then in the loss (stage_a.py:1303):
```
bragg_scaled = bragg_patch * exp(log_scale_baseline)
             = bragg_patch * (target_mean / (M_raw * sqrt(spot_scale)))
```

If `bragg_patch ≈ M_raw`:
```
bragg_scaled ≈ target_mean / sqrt(spot_scale)
```

**So Stage A's LOSS output is `target_mean / sqrt(spot_scale)`, which should match `bragg_expected = 0.24`.**

This means:
```
target_mean = 0.24 * sqrt(spot_scale) = 0.24 * 5.57e8 ≈ 1.3e8 ADU
```

That's a HUGE intensity for a diffraction image! Typical pixel values are 10-1000 ADU, not 10^8.

**Wait—I think I'm confusing panel-mean vs ROI-mean or total vs per-pixel intensity.**

Let me check what "bragg_after_mean" actually measures in the test assertions...

## Key Insight: What Does "bragg_after_mean" Measure?

I need to check the test code to see what `bragg_after_mean` represents. It's likely a PER-PIXEL mean over the full detector panel, not a sum or ROI-only mean.

But without access to the test fixture data or Stage A training run outputs, I can't verify this empirically in this loop.

## Conclusion: Stuck on Baseline Semantics

The issue is that I don't have enough information to determine whether:

**Option A:** The baseline correctly embeds `1/sqrt(spot_scale)`, and reconstruction should multiply by `sqrt(spot_scale)` but the simulator is producing intrinsically low output for an unknown reason.

**Option B:** The baseline derivation is WRONG and should not include the sqrt scaling at all, meaning `log_scale_baseline` should just be `log(target_mean / M_raw)` without the sqrt division.

**Option C:** There's a discrepancy between how Stage A builds simulators (warm cache retargeting) vs how reconstruction builds them (cold factory path), and they're applying different internal scalings.

## Next Action: Compare Stage A vs Reconstruction Simulator Outputs

The most direct way to resolve this is to:

1. Run Stage A's baseline derivation code (lines 435-457) and capture:
   - `M_raw` = mean of `bragg_stack` BEFORE sqrt multiplication
   - `model_mean_masked` = mean AFTER sqrt multiplication
   - `log_scale_baseline` = the derived value

2. Run reconstruction's cold simulator path and capture the raw output

3. Compare: Are they the same? If not, why?

This requires a **debug probe** that runs both paths side-by-side with the same inputs.
