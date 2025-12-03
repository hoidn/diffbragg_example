# Ralph Findings - ARCH-SIM-CONSTRUCTION-001 Phase C.1 Corrective Fix

## Loop ID
2025-12-03T005008Z

## Task
Remove double sqrt multiplication at `dbex/refinement/reconstruction.py:238` per Galph's root cause diagnosis.

## Changes Made
- **File:** `dbex/refinement/reconstruction.py:238`
- **Change:** Removed explicit `* sqrt_spot_scale` multiplication
- **Before:** `bragg_scaled = bragg_panel * scale_factor * sqrt_spot_scale`
- **After:** `bragg_scaled = bragg_panel * scale_factor`

## Test Results
Both tests FAILED with **unexpected behavior** - output is now too small instead of correct:

### DB-AT-028 Metrics
- **chi²/pixel initial:** 1.084e+05 (FAIL - exceeds bound of 1e2, unchanged from prior loop)
- **bragg_before_mean:** 0.2394 (reasonable, matches Stage A baseline)
- **bragg_after_mean:** **1.0249e-05** (TOO SMALL - should be ~0.24 per diagnosis)
- **bragg_before / bragg_after ratio:** ~23,400

### Comparison with Prior Loop (2025-12-04T010500Z)
| Metric | Prior (with * sqrt_spot_scale) | Current (without) | Expected |
|--------|-------------------------------|-------------------|----------|
| bragg_after_mean | 5711.08 | 1.0249e-05 | ~0.24 |
| Error magnitude | 23,800× too large | 23,400× too small | Correct |

## Root Cause Analysis

### Mathematical Verification
From metrics:
- `spot_scale_override = 3.105e17`
- `sqrt(spot_scale) = 5.57e8`
- `log_scale_effective = 20.138`
- `scale_factor = exp(20.138) = 5.57e8`

**Key observation:** `scale_factor ≈ sqrt(spot_scale)` (both ≈ 5.57e8)

### Behavior Summary
1. **Prior loop:** `bragg_scaled = bragg_panel * scale_factor * sqrt_spot_scale = bragg_panel * (5.57e8)²` → 23,800× too large
2. **Current loop:** `bragg_scaled = bragg_panel * scale_factor = bragg_panel * 5.57e8` → Should be correct, but is 23,400× too small!

This suggests **simulator output (`bragg_panel`) is not raw ADU as expected**.

### Hypotheses

#### H1: Simulator applies inverse sqrt scaling
The simulator may be applying `1/sqrt(spot_scale)` internally when `spot_scale_override` is passed to the factory, resulting in:
- **Raw simulator physics:** Some base value `B`
- **Simulator output:** `bragg_panel = B / sqrt(spot_scale)`
- **After scale_factor:** `bragg_scaled = B / sqrt(spot_scale) * sqrt(spot_scale) = B` (correct)
- **But we observe:** Output is `B / (spot_scale)` somehow?

#### H2: Factory/simulator contract mismatch
The factory at line 200 receives `spot_scale_override`, and the comment says "Factory needs this to compute sqrt_scale". Perhaps:
- Factory computes `sqrt_scale` value
- Simulator applies `1/sqrt_scale` internally for some calibration reason
- Caller is expected to multiply by `sqrt_scale` externally (which is what the old code did with `* sqrt_spot_scale`)

This would explain:
- Old code: `bragg_panel * scale_factor * sqrt_spot_scale` where `bragg_panel` already has `1/sqrt_spot` applied, and `scale_factor ≈ sqrt_spot`, yielding `bragg_panel * sqrt_spot² = (raw/sqrt_spot) * sqrt_spot² = raw * sqrt_spot` (too large)
- New code: `bragg_panel * scale_factor = (raw/sqrt_spot) * sqrt_spot = raw` (should be correct!)

But measurements show new code is 23,400× too small, not correct!

#### H3: log_scale_baseline interpretation error
Perhaps `log_scale_baseline` does NOT equal `log(sqrt(spot_scale))` as Galph's diagnosis assumed. Need to verify what Stage A actually stores in telemetry for `log_scale_baseline`.

## Repeat-Failure Guard Triggered
Per `<ground_rules/>` repeat-failure guard:
- Same acceptance criterion (DB-AT-028 chi²/pixel) failed in consecutive loops (2025-12-04T010500Z, current)
- Failure signature changed (too large → too small) but criterion remains unmet
- Correctly implemented the requested fix per diagnosis, but outcome differs from prediction

**Recommendation:** Escalate to Galph for deeper inspection of:
1. Simulator/factory scaling contract
2. Stage A `log_scale_baseline` computation and storage
3. Possible fourth-root scaling (`(spot_scale)^0.25 ≈ 23,400`) source

## Artifacts
- `pytest_db_at_028_029_v3.log` - Test execution log
- `db_at_028_metrics.json` - Quantitative measurements
- `mapping_context_fixture.json` - Input diagnostics

## Status
**blocked — implementation correct per diagnosis but outcome contradicts prediction; needs supervisor re-analysis**
