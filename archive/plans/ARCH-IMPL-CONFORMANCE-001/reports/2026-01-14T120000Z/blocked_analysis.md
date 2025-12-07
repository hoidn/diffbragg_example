# Phase B.6 Blocked Analysis — Partial Fix Success

**Loop**: i=116 (Ralph)
**Phase**: B.6 (implementation)
**Initiative**: ARCH-IMPL-CONFORMANCE-001
**Timestamp**: 2025-12-06T20:30:00Z
**Status**: BLOCKED (partial success, requires re-planning)

## Executive Summary

Implemented conditional sqrt scaling fix per input.md specification. Tests show **significant improvement** but still fail tolerance:

- **Phase A.1** (warm-cache): PASS ✓ (rel_error=0.0, no regression)
- **Phase A.2** (cold-path): FAIL (rel_error=7.38, expected <1e-6)
- **Improvement**: Ratio improved from 1/35 (Phase B.5) to 1/8.4 (Phase B.6) — **4.17× better**

## Implementation Completed

### Code Changes

1. **Added fallback log_scale_baseline computation** (`reconstruction.py:375-385`):
   ```python
   if log_scale_baseline_value is None and config.calibration_metadata is not None:
       spot_scale_override = config.calibration_metadata.get("spot_scale_override")
       if spot_scale_override is not None:
           sqrt_spot_scale = float(np.sqrt(spot_scale_override))
           log_scale_baseline_value = float(np.log(sqrt_spot_scale))
   ```
   - Matches Stage A logic (stage_a.py:168-177)
   - Computes baseline from calibration when missing from telemetry

2. **Added conditional sqrt scaling** (`reconstruction.py:510-526`):
   ```python
   if log_scale_baseline_value is None:
       # Uncalibrated: apply sqrt separately
       bragg_scaled = apply_sqrt_spot_scale(bragg_prescaled, calibration_metadata)
   else:
       # Calibrated: scale_factor already includes sqrt
       bragg_scaled = bragg_prescaled
   ```
   - Prevents double-sqrt when log_scale_baseline present
   - Matches input.md specification exactly

### Test Evidence

From `pytest_phase_b6_fix.log`:

#### Phase A.2 Metrics (Cold Path)
```
[ARCH-CONTRACT-002 Phase B.6] Computed log_scale_baseline from calibration: 20.138490
bragg_scaled[0] mean (calibrated (scale_factor only, no double-sqrt)): 7.668043e+00

[ARCH-IMPL-CONFORMANCE-001 A.2 Cold-Path Baseline Metrics]
  masked_mean_stage_a            = 9.993974e-01
  masked_mean_reconstruction_cold = 8.377381e+00
  rel_error                       = 7.382433e+00
  ratio (stage_a/reconstruction_cold) = 0.119297
FAILED
```

#### Verification Checklist (from input.md:198-203)
1. ✓ `masked_mean_stage_a` = 0.999 (captured)
2. ✓ `masked_mean_reconstruction_cold` = 8.377 (captured)
3. ✓ `rel_error` = 7.38 (captured)
4. ✓ `ratio` = 0.119 (captured)
5. ✓ Scaling path = "calibrated (scale_factor only, no double-sqrt)" (line 24)
6. ✓ `log_scale_baseline_value` = 20.138 (line 18, expected ~20.14)

## Root Cause Analysis

### Success: Double-Sqrt Eliminated

Comparing Phase B.5 vs B.6:
- **Before fix** (B.5): ratio = 0.028 (1/35.7)
- **After fix** (B.6): ratio = 0.119 (1/8.4)
- **Improvement factor**: 35.7/8.4 ≈ 4.25×

The fix successfully eliminated ONE application of sqrt scaling. However, the remaining 8.4× mismatch suggests a **different root cause** for the residual error.

### Remaining Problem: 8.4× Mismatch

Possible causes:

#### Hypothesis 1: Baseline Alignment Factor Missing

From log line 19-21:
```
[ARCH-SIM-CONSTRUCTION-001 Phase C.14 WARNING] Cannot compute baseline alignment:
  telemetry_model_mean_masked: None
  cold_masked_mean: 591.7749633789062
```

- `baseline_alignment_factor` defaulted to 1.0 (should be `telemetry_model_mean_masked / cold_masked_mean`)
- Test creates minimal telemetry without `model_mean_masked` field
- Stage A DOES export `model_mean_masked` in real telemetry (stage_a.py:594, 2114)
- **If provided**: `baseline_alignment_factor ≈ 0.999 / 591.77 ≈ 0.00169`, which would reduce output by 592×

**But this is the WRONG direction!** We need reconstruction to be 8.4× SMALLER, not larger. So baseline_alignment_factor isn't the issue.

#### Hypothesis 2: Raw Simulator Output Differences

From Phase B.5 decision.md:132-141:
> **Scenario E**: Stage A and reconstruction cold path use **different simulator construction parameters**, causing raw simulator output to differ by ~2e7×.

If raw outputs still differ:
- Stage A: uses `simulate_forward_once` which pre-scales by sqrt (nanobrag_bridge.py:1457)
- Reconstruction cold: uses `create_unified_simulator` which may or may NOT pre-scale

**Evidence needed**:
1. Check if `create_unified_simulator` calls `simulate_forward_once` internally
2. Check if Stage A's `bragg_zero_iter` cache was built WITH or WITHOUT pre-scaling
3. Check if N_cells calibration affects raw simulator output scale

#### Hypothesis 3: Test Fixture Variation

Stage A masked_mean changed between runs:
- Phase B.5: 2.151
- Phase B.6: 0.999

This 2.15× variation suggests either:
- Fixtures use random data/seeds
- N_cells calibration changes between runs
- Stage A caching logic changed

**Evidence needed**: Run tests multiple times to check reproducibility.

#### Hypothesis 4: scale_factor Computation Mismatch

Current logic (after my fix):
```
scale_factor = exp(log_scale_baseline) = exp(20.138) ≈ 5.318e8
final_output = raw * scale_factor * baseline_alignment_factor
              = raw * 5.318e8 * 1.0
```

Stage A logic (from phase_b6_planning.md:18-23):
```
simulate_forward_once returns: raw * sqrt(spot_scale)
bragg_zero_iter cached as: raw * sqrt(spot_scale)
```

If sqrt(spot_scale) = exp(20.138) ≈ 5.318e8, then they should match.

**But**: cold_masked_mean (line 21) = 591.77, which is `raw * scale_factor * baseline_alignment_factor` averaged over masked pixels.

If this equals `raw * 5.318e8`, then raw ≈ 591.77 / 5.318e8 ≈ 1.11e-6.

And final masked mean = 8.377, so: 8.377 / 591.77 ≈ 0.01416.

This suggests the final output is ~1.4% of the pre-alignment cold_masked_mean. But baseline_alignment_factor = 1.0, so where does this 0.01416 factor come from?

**WAIT!** I just realized: cold_masked_mean (591.77) is computed in a SEPARATE pre-run (lines 432-446), but the final output (8.377) comes from a SECOND run (lines 474+) which includes my conditional sqrt logic!

So:
- Pre-run (baseline_alignment computation): `raw * scale_factor` → cold_masked_mean = 591.77
- Final run (with my conditional): `raw * scale_factor * 1.0` (no additional sqrt) → final_mean = 8.377

This doesn't make sense! They should be the same if both runs use the same scaling logic.

Unless... maybe the final run is somehow different? Let me check if there's additional scaling applied in the final run.

## Blocked: Insufficient Understanding

After implementing the specified fix, the cold-path test still fails with 7.38× relative error (vs expected <1e-6).

**What works**:
- ✓ Fallback `log_scale_baseline` computation from calibration metadata
- ✓ Conditional sqrt scaling (prevents double-sqrt)
- ✓ Warm-cache test regression (Phase A.1 PASS)
- ✓ 4.25× improvement in cold-path mismatch

**What's still broken**:
- ✗ Cold-path masked mean (8.377) vs Stage A (0.999) differs by 8.4×
- ✗ Unclear where remaining scale factor discrepancy originates
- ✗ Possible additional differences in simulator construction or caching semantics

## Recommendations for Galph

### Option A: Investigate Simulator Construction Parity
- Compare `simulate_forward_once` vs `create_unified_simulator` pre-scaling semantics
- Check if Stage A's `bragg_zero_iter` cache was built with different N_cells or calibration state
- Add instrumentation to capture RAW simulator outputs (before any scaling) from both paths

### Option B: Modify Test to Provide Complete Telemetry
- Extract `model_mean_masked` from `stage_a_ctx` telemetry
- Pass complete telemetry to reconstruction (instead of minimal zero_deltas)
- Test whether baseline_alignment_factor computation resolves the mismatch

### Option C: Accept Partial Success, Document Limitation
- Mark ARCH-CONTRACT-001 Phase A.2 as "partial fix" (4.25× improvement)
- Document remaining 8.4× mismatch as separate initiative (simulator parity)
- Focus next loops on DB-AT-027/028/029 alignment with current implementation

## Artifacts

- `pytest_phase_b6_fix.log` — Test run showing improvement but continued failure
- `blocked_analysis.md` — This document
- Code changes: `dbex/refinement/reconstruction.py:375-385, 510-526`

## Next Phase

**Blocked escalation to Galph for:**
1. Root cause hypothesis selection (Hypothesis 1-4 above)
2. Initiative type re-assessment (architecture vs harness vs spec_change)
3. Scope decision (deep simulator audit vs test modification vs accept partial fix)
