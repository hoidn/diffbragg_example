# Ralph Loop Summary: ARCH-SIM-CONSTRUCTION-001 Phase C.1 Verification

**Status:** BLOCKED — Double multiplication confirmed, requires supervisor analysis
**Initiative Type:** architecture
**Tests:** DB-AT-028 FAILED (chi²=1.084e+05), DB-AT-029 not run

## Problem

input.md requested applying `* sqrt_spot_scale` multiplication at reconstruction.py:239. However:

1. Code ALREADY has this multiplication (commit acea29ef, 2025-12-02 16:31:53)
2. Empirical test confirms Ralph's theoretical prediction: **double multiplication**
3. This violates repeat-failure guard — same fix requested after prior attempt

## Empirical Evidence

Test run with current code (multiplication present):

```
bragg_before_mean  = 0.239      ← CORRECT (uses simulate_forward_once, no sqrt)
bragg_after_mean   = 5711.08    ← WRONG (uses reconstruction helper, applies sqrt)
chi²/pixel initial = 1.084e+05  ← vs ≤ 100 spec
spot_scale_override = 3.105e17
log_scale_baseline = 20.138 = log(sqrt(3.105e17))
```

**Analysis:**
- `scale_factor = exp(log_scale_baseline + delta) = exp(20.138 + 0) ≈ 5.572e8 = sqrt(spot_scale)` ✓
- Current code: `bragg_scaled = bragg_panel * scale_factor * sqrt_spot_scale`
  → Applies sqrt TWICE: `bragg * sqrt(spot) * sqrt(spot) = bragg * spot`
- Ratio: `5711 / 0.239 = 23,895 ≈ (spot_scale)^(1/4)` confirms fourth-root error

## Root Cause

**Architectural mismatch in SCALE-009 interpretation:**

Stage A uses:
1. **Loss computation:** `bragg * exp(log_scale_baseline + delta)` where `log_scale_baseline = log(sqrt(spot_scale))`
   → Already includes ONE sqrt application
2. **Diagnostics only:** `bragg * sqrt(spot_scale)` for masked-mean telemetry (NOT used in loss!)

Reconstruction helper incorrectly mixes these:
- Applies `exp(log_scale_baseline)` (includes sqrt) AND
- Multiplies by `sqrt_spot_scale` again (double application)

**Correct pattern** (matching `simulate_forward_once` and Stage A loss):
```python
bragg_scaled = bragg_panel * scale_factor  # NO additional sqrt multiplication
```

## Actions Taken This Loop

1. Synced repo, verified current code state (multiplication present)
2. Ran empirical validation test with artifact directories configured
3. Extracted metrics confirming double multiplication (bragg_after=5711 vs expected ~0.24)
4. Documented architecture tension and root cause analysis

## Blocked Reason

Per repeat-failure guard (ralph_prompt §ground_rules):
> If the same acceptance criterion failed in the prior loop with essentially the same log/telemetry signature...halt immediately.

**Cannot proceed** with more implementation attempts without supervisor analysis of:
1. SCALE-009 finding interpretation (post-run sqrt application semantics)
2. log_scale_baseline derivation contract (whether it already embeds sqrt)
3. Reconstruction helper vs Stage A loss computation alignment

## Recommended Next Actions (for Galph)

1. **Remove `* sqrt_spot_scale` from reconstruction.py:238**
   → Restores correct pattern: `bragg_scaled = bragg_panel * scale_factor`
2. **Update SCALE-009 finding** in docs/findings.md to clarify:
   - log_scale_baseline = log(sqrt(spot_scale)) for calibrated runs
   - sqrt multiplication is embedded in exp(log_scale_baseline), NOT applied post-run
   - Post-run sqrt only for diagnostics (masked-mean telemetry), not loss/artifacts
3. **Re-run DB-AT-028/029** to confirm fix resolves chi²/bragg_after issues

## Artifacts

- Test log: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T010500Z_ralph_verification/pytest_full.log`
- Metrics: `.../db_at_028/db_at_028_metrics.json`
- Analysis: `.../analysis.md`, `.../summary.md`
