# Phase C.7 Implementation Summary — Scale-Factor Telemetry Instrumentation

**Date:** 2025-12-12T180000Z  
**Initiative:** ARCH-SIM-CONSTRUCTION-001 (Simulator Construction Convention Alignment)  
**Phase:** C.7 (Scale-factor telemetry capture)  
**Status:** Telemetry instrumentation complete; scale inflation confirmed

## Objective

Instrument Stage A and reconstruction helpers to capture and persist the exact scale-factor values used during the final forward pass, enabling direct comparison and diagnosis of the log_scale delta inflation observed in prior loops.

## Changes Made

### 1. Stage A Telemetry (stage_a.py:1856-1890)

Added `param_deltas['log_scale_effective']` dictionary capturing:
- `log_scale_clamped`: Final effective log-scale (baseline + clamped_delta)
- `log_scale_delta_clamped`: Clamped delta value
- `delta_bound`: Upper/lower clamp threshold (config.log_scale_max_delta)
- `scale_factor`: `exp(log_scale_clamped)` — the authoritative scale multiplier

Logic replicates compute_loss clamp computation (lines 1195-1203) to ensure telemetry captures the exact values used during the final validation run.

### 2. Reconstruction Consumer (reconstruction.py:269-322)

Updated `build_final_bragg_from_stage_a_telemetry` to:
- Prefer recorded `log_scale_effective['scale_factor']` from Stage A telemetry when available
- Fall back to legacy baseline+delta computation when telemetry missing
- Emit diagnostic prints showing recorded vs recomputed values
- Warn when recomputation disagrees with recorded value (rel_diff > 1e-6)

### 3. Probe Script (probe_stage_a_scale_alignment.py:278-288)

Added `log_scale_effective_telemetry_structure` example to JSON output showing expected telemetry schema (note: probe doesn't run refinement, so no actual values captured).

## Test Results

### Scale Probe
- Successfully ran without errors
- Artifacts: `scale_probe/stage_a_scale_alignment.json`, `scale_probe_summary.md`
- Mapping path statistics captured; reconstruction path skipped (requires full refinement)

### DB-AT-028/029
- **Tests still FAIL** with same signature: chi²=2.098e+05 (vs ≤1e2 bound)
- **BUT**: New telemetry confirms the root cause hypothesis

#### Key Diagnostic Output (from reconstruction DEBUG):
```
[ARCH-SIM-CONSTRUCTION-001 Phase C.7] Using recorded scale_factor from Stage A telemetry:
  scale_factor (recorded): 1.389551e+10
  log_scale_effective (recorded): 23.354832
  log_scale_baseline: 20.354832
  log_scale_delta_clamped (recorded): 3.0
  sqrt_spot_scale: 691817229.1071362
  spot_scale_override: 4.786110784894759e+17
  bragg_panel[0] mean (raw sim output): 1.865559e-09
  bragg_scaled[0] mean (after scale_factor): 2.592290e+01
  bragg_full mean (final output): 2.592289e+01
```

## Root Cause Confirmation

The telemetry **definitively proves** that Stage A is using an inflated log_scale during refinement:

1. **Expected scale_factor**: `exp(20.354832) ≈ 6.92e+08` (matches sqrt(spot_scale))
2. **Actual scale_factor**: `1.39e+10 = exp(23.354832)` — **20× too large**
3. **Delta maxed out**: `log_scale_delta_clamped = 3.0` (hit upper clamp bound)
4. **Result**: `bragg_scaled = 25.92 ADU` vs expected `~1.84 ADU` (14× discrepancy)

Reconstruction is correctly using the recorded inflated scale_factor from Stage A, proving the inflation happens during Stage A's LBFGS optimization, not in reconstruction's post-processing.

## Exit Criteria Status

- ✅ **Criterion #1** (raw parity): SATISFIED — simulators produce identical raw outputs (1.0 ratio)
- ❌ **Criterion #2** (chi²≤1e2): FAIL — blocked by scale inflation (chi²=2.098e+05)
- ❌ **Criterion #3** (ROI corr≥0.2): FAIL — blocked by scale inflation (corr=-0.053)

## Metrics Summary

| Metric | Value | Expected | Status |
|--------|-------|----------|--------|
| scale_factor (recorded) | 1.39e+10 | 6.92e+08 | ⚠️ 20× inflated |
| log_scale_delta_clamped | 3.0 | ≈0.0 | ⚠️ maxed out |
| bragg_after_mean | 25.92 ADU | ~1.84 ADU | ⚠️ 14× too high |
| chi²/pixel initial | 2.098e+05 | ≤1e2 | ❌ FAIL |
| raw_parity (stage_a vs recon) | 1.000 | 1.0 ±1% | ✅ PASS |

## Artifacts

- `scale_probe/`: Probe script output (mapping context, calibration metadata)
- `db_at_028/db_at_028_metrics.json`: Full test metrics including telemetry
- `db_at_029/db_at_029_metrics.json`: Full test metrics including telemetry
- `pytest_db_at_028_029.log`: Full test output with diagnostic prints

## Next Actions

**For Supervisor (Galph):**

The telemetry instrumentation is complete and has successfully captured authoritative evidence of the scale inflation. The next step is NOT another implementation attempt, but rather a decision on how to address the root cause:

### Option A: Investigate log_scale baseline derivation
- Analyze why mapping's zero-iteration forward produces baseline that Stage A's optimizer rejects
- Check if target_mean_masked/model_mean_masked ratio used for baseline includes bias
- Consider whether log_scale should be initialized closer to zero for calibrated runs

### Option B: Widen delta_bound temporarily
- Set `config.log_scale_max_delta = 10.0` temporarily to let optimizer explore further
- If chi² improves, confirms delta clamp is overly restrictive
- Then investigate why optimizer needs such a large delta

### Option C: Spec-change initiative
- If this behavior is expected under current variance model (sigma_floor, variance weighting)
- Open dedicated spec-change initiative to revisit log_scale parameterization
- Document whether delta=+3.0 represents a real signal or optimizer pathology

### Recommended: Option A + diagnostic run with widened bound
1. First: Analyze target_mean_masked, model_mean_masked telemetry to understand baseline derivation
2. Then: Run one diagnostic loop with `log_scale_max_delta=10.0` to see final delta value
3. Use evidence from both to decide whether to adjust baseline computation or escalate to spec-change

**Do NOT attempt more reconstruction changes** — the issue is in Stage A's optimization landscape, not in reconstruction's scale application logic.
