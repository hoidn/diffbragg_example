# Galph Root Cause Revised Analysis: ARCH-SIM-CONSTRUCTION-001 Phase C.1

**Date:** 2025-12-04T121500Z (Loop i=451)
**Initiative:** ARCH-SIM-CONSTRUCTION-001 (Simulator Construction Convention Alignment)
**Phase:** C.1 — Corrective analysis after unexpected outcome
**Status:** ROOT CAUSE REVISED — Original diagnosis was INCORRECT

## Executive Summary

**My previous diagnosis (2025-12-03T005008Z) was WRONG.** I incorrectly instructed Ralph to REMOVE the `* sqrt_spot_scale` multiplication, but this made the output 23,400× too small instead of fixing it.

**Correct root cause:** The reconstruction helper needs a DIFFERENT `sqrt_spot_scale` application pattern than I understood. The issue is more subtle than double multiplication.

## Evidence Review

### Ralph's Implementation Results

| Loop | Code at line 238 | bragg_after_mean | Status |
|------|------------------|------------------|--------|
| 2025-12-04T010500Z | `* scale_factor * sqrt_spot_scale` | 5711.08 | 23,800× too large |
| 2025-12-03T005008Z | `* scale_factor` (no sqrt) | 1.0249e-05 | 23,400× too small |
| Expected | ??? | ~0.24 | Correct |

### Key Measurements
```
bragg_before_mean (from simulate_forward_once) = 0.2394  ← CORRECT baseline
bragg_after_mean (target for reconstruction) ≈ 0.24      ← What we want
spot_scale_override = 3.105e17
sqrt(spot_scale) = 5.572e8
log_scale_baseline = 20.138
scale_factor = exp(20.138) = 5.572e8 = sqrt(spot_scale)
```

### Mathematical Relationships
```
With sqrt:     bragg_after = 5711 = bragg_no_sqrt * 5.572e8
Without sqrt:  bragg_after = 1.02e-05
Expected:      bragg_after ≈ 0.24

Ratio (with/without) = 5.572e8 = sqrt(spot_scale) ✓ (confirms sqrt multiplication effect)
```

## Root Cause Analysis — The Correct Understanding

### What `simulate_forward_once` Does

From `dbex/nanobrag_bridge.py:1428-1438`:
```python
panel_output = simulator.run()  # Raw simulator output
panel_output_scaled = panel_output_np * sqrt_scale_value  # Apply sqrt(spot_scale)
bragg[panel_id] = panel_output_scaled
```

**Result:** `bragg_before` includes `* sqrt_spot_scale` multiplication.

### What Stage A Does During Training

From `dbex/refinement/stage_a.py:435-457`:
```python
# Step 1: Run simulator and apply sqrt scaling for telemetry
bragg_stack = torch.stack([sim.run() for sim in simulators])
bragg_stack_scaled = bragg_stack * sqrt_spot_scale  # Line 443

# Step 2: Compute mean for baseline derivation
model_mean_masked = float(bragg_stack_scaled[loss_mask].mean())  # Line 446

# Step 3: Derive log_scale_baseline
log_scale_baseline = np.log(target_mean_masked / model_mean_masked)  # Line 457
```

**Key insight:**
```
model_mean_masked = mean(raw_simulator_output * sqrt_spot_scale)
log_scale_baseline = log(target_mean / model_mean_masked)
                    = log(target_mean / (raw_mean * sqrt_spot_scale))
```

Therefore:
```
exp(log_scale_baseline) = target_mean / (raw_mean * sqrt_spot_scale)
```

### What Stage A Does During Loss Computation

From `dbex/refinement/stage_a.py:1194-1202`:
```python
if log_scale_baseline_value is not None:
    log_scale_clamped = log_scale_baseline_value + torch.clamp(log_scale, ...)
else:
    log_scale_clamped = torch.clamp(log_scale, ...)

scale_factor = torch.exp(log_scale_clamped)
```

**In the loss function:**
```python
# Inside _compute_variance_weighted_loss (called by LBFGS closure):
model = bragg_raw * scale_factor  # Where bragg_raw is sim.run() output
```

So during optimization:
```
model = raw * exp(log_scale_baseline + delta)
      = raw * exp(log_scale_baseline) * exp(delta)
      = raw * (target_mean / (raw_mean * sqrt_spot_scale)) * exp(delta)
```

At delta=0 (the final telemetry state):
```
model = raw * (target_mean / (raw_mean * sqrt_spot_scale))
      = raw * target_mean / (raw_mean * sqrt_spot_scale)
```

**This does NOT match `bragg_before` which is `raw * sqrt_spot_scale`!**

### The Missing Piece

The disconnect is that:
1. `simulate_forward_once` applies `* sqrt_spot_scale` to match Stage A's **diagnostic telemetry** pattern (line 443)
2. But reconstruction should match Stage A's **loss computation** pattern, which uses `raw * scale_factor` WITHOUT the extra sqrt

However, the test expects `bragg_after ≈ bragg_before`, and `bragg_before` has the sqrt applied!

**This suggests the test itself might be checking the wrong thing**, OR reconstruction should indeed output the same as `simulate_forward_once`.

## Hypothesis: Reconstruction Should Match `simulate_forward_once`, Not Loss

If reconstruction is meant to produce a "final forward model" for visualization/analysis (not for loss computation), then it should match `simulate_forward_once`:

```python
bragg_output = raw * sqrt_spot_scale
```

But we're using:
```python
bragg_scaled = raw * scale_factor
where scale_factor = exp(log_scale_baseline) = target_mean / (raw_mean * sqrt_spot_scale)
```

To get `bragg_output = raw * sqrt_spot_scale`, we need:
```python
scale_factor_adjusted = scale_factor * sqrt_spot_scale
                      = (target_mean / (raw_mean * sqrt_spot_scale)) * sqrt_spot_scale
                      = target_mean / raw_mean
```

But that's not what we have!

## The Actual Problem

Looking at the numbers:
```
bragg_before (simulate_forward_once) = 0.2394
bragg_after (current, no sqrt) = 1.02e-05

bragg_before / bragg_after = 0.2394 / 1.02e-05 = 23,470 ≈ sqrt(spot_scale) / raw_normalization
```

This suggests that `scale_factor` is MISSING a factor!

Let me check: if `scale_factor = exp(log_scale_baseline)` and the raw simulator output needs to be multiplied by `sqrt_spot_scale` to match `simulate_forward_once`, then:

```
bragg_reconstruction = raw * scale_factor
                     = raw * exp(log_scale_baseline)
                     = raw * (target_mean / (raw_mean * sqrt_spot_scale))

bragg_simulate_forward_once = raw * sqrt_spot_scale

Ratio = (raw * sqrt_spot_scale) / (raw * target_mean / (raw_mean * sqrt_spot_scale))
      = (raw * sqrt_spot_scale) * (raw_mean * sqrt_spot_scale) / target_mean
      = raw * raw_mean * (sqrt_spot_scale)² / target_mean
```

This doesn't simplify nicely unless `raw ≈ raw_mean` and `target_mean ≈ raw_mean * (sqrt_spot_scale)²`, which seems off.

## Resolution

**I need to ADD BACK the `* sqrt_spot_scale` multiplication** that I told Ralph to remove. But FIRST I need to understand why the original code with `* sqrt_spot_scale` produced outputs 23,800× too large.

The answer must be that **`scale_factor` already includes sqrt_spot_scale somehow**, creating the double application.

Let me verify: if `log_scale_baseline ≈ 20.138` and `exp(20.138) = 5.572e8 = sqrt(3.105e17)`, then yes, `scale_factor = sqrt(spot_scale)`.

So the original code was:
```python
bragg_scaled = raw * sqrt(spot_scale) * sqrt(spot_scale) = raw * spot_scale
```

And `simulate_forward_once` gives:
```python
bragg_before = raw * sqrt(spot_scale)
```

So to match, we need:
```python
bragg_after = raw * sqrt(spot_scale)
```

Which means we need to **DIVIDE** `scale_factor` by `sqrt(spot_scale)` or use a different scale!

## Final Diagnosis

**The bug is NOT in reconstruction.py**. The bug is in how `log_scale_baseline` is being interpreted!

When `log_scale_baseline` is derived as `log(target_mean / model_mean_masked)` where `model_mean_masked` already includes `* sqrt_spot_scale`, the baseline is:

```
log_scale_baseline = log(target / (raw * sqrt_spot_scale))
```

But in the loss function, we apply:
```
model = raw * exp(log_scale_baseline)
      = raw * target / (raw * sqrt_spot_scale)
      = target / sqrt_spot_scale  # When raw ≈ raw_baseline
```

This is WRONG for reconstruction! We want:
```
bragg_final = raw * sqrt_spot_scale  # Match simulate_forward_once
```

So we need:
```python
scale_factor_correct = exp(log_scale_baseline) * (sqrt_spot_scale)²
                     = exp(log_scale_baseline) * spot_scale
```

Wait, that's even worse!

## The Real Issue

I think the problem is simpler: **we're using the wrong simulator output or the wrong `log_scale` value**.

The `log_scale` telemetry parameter represents a DELTA from baseline when calibrated. At the final state, `log_scale ≈ 0` (optimized), so:
```
scale_factor = exp(log_scale_baseline + 0) = exp(log_scale_baseline)
```

If `log_scale_baseline = 20.138 = log(sqrt(spot_scale))`, then:
```
scale_factor = sqrt(spot_scale)
bragg_scaled = raw * sqrt(spot_scale)  # WITHOUT extra multiplication
```

This should match `simulate_forward_once`!

But measurements show `bragg_scaled = 1.02e-05` when we use just `scale_factor`, which is 23,400× too small.

This means **the raw simulator output is NOT the same between training and reconstruction**, OR the scale_factor calculation is wrong.

## Next Steps

Ralph should:
1. Add debug instrumentation to print:
   - `bragg_panel.mean()` (raw simulator output)
   - `scale_factor` value
   - `log_scale_baseline` value
   - `log_scale` (delta) value
2. Compare these to Stage A's values at the same crystal/beam/detector configuration
3. Identify where the 23,400× discrepancy originates

**Status:** blocked — need empirical data to diagnose scale_factor vs simulator output mismatch
