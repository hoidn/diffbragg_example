# Debug Analysis: Phase C.1 Missing sqrt_spot_scale Application

**Date:** 2025-12-04T010500Z
**Focus:** ARCH-SIM-CONSTRUCTION-001 Phase C.1
**Issue:** DB-AT-028/029 still FAIL after Ralph's implementation

## Problem Statement

Ralph's commit a00d42c7 implemented beam calibration threading and extracted `sqrt_spot_scale` correctly (reconstruction.py:152), but tests still FAIL with identical signatures:
- DB-AT-028: chi²/pixel initial 1.084e+05 (vs ≤1e2 spec)
- DB-AT-029: ROI correlation before -0.050 (vs ≥0.2 floor)

## Root Cause

**Ralph calculated `sqrt_spot_scale` but never applied it to the simulator output.**

### Evidence

**Current Code (reconstruction.py:238-240):**
```python
bragg_panel = sim.run()
bragg_scaled = bragg_panel * scale_factor  # Missing sqrt_spot_scale multiplication!
bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
```

**Correct Pattern (stage_a.py:442-443):**
```python
sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override > 0 else 1.0
bragg_stack_scaled = bragg_stack * sqrt_spot_scale  # Explicit multiplication
```

### Metrics Confirmation

From `db_at_028_metrics.json`:
- `bragg_after_mean = 5711.08` (expected ~0.24)
- `spot_scale_override = 3.105e17`
- `sqrt_spot_scale = sqrt(3.105e17) ≈ 5.57e8`
- Missing multiplication factor: `5711 / 0.24 ≈ 23,800` ≈ `sqrt(spot_scale_override)` ✓

This confirms Ralph's code applies `exp(log_scale_baseline)` correctly but omits the **additional** `sqrt_spot_scale` post-run multiplication that Stage A performs.

## Fix Required

**File:** `dbex/refinement/reconstruction.py`

**Line 239 must change from:**
```python
bragg_scaled = bragg_panel * scale_factor
```

**To:**
```python
bragg_scaled = bragg_panel * scale_factor * sqrt_spot_scale
```

**Rationale:** Stage A applies sqrt(spot_scale_override) as an **explicit post-run multiplication** separate from the exp(log_scale_baseline) scaling. The baseline is used for the learnable delta parameter, while the sqrt multiplication is applied to the raw simulator output to match mapping conventions (SCALE-009, TOOLING-VIS-001 Phase D.E).

## Next Step

Issue corrective Do Now directing Ralph to:
1. Apply `* sqrt_spot_scale` multiplication at reconstruction.py:239
2. Re-run DB-AT-028/029 validation
3. Confirm `bragg_after_mean ≈ 0.24` and tests PASS
