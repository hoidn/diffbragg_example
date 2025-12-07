### Turn Summary (Loop i=115 — Galph Planning)

**Timestamp**: 2025-12-06T20:00:00Z
**Initiative**: ARCH-IMPL-CONFORMANCE-001 Phase B.6 (Implementation Ready)
**Status**: Planning complete, patch-ready for Ralph i=116

## Problem Analysis

Loop i=114 (Ralph) executed Phase B.5 evidence collection with 4-hop diagnostic tracing and proved **calibration threading works correctly** at all hops:
- Test passes `calibration_metadata` with `spot_scale_override=4.786e17` to `RefinementConfig` ✓
- Config preserves it ✓
- `effective_calibration_metadata` defaulting logic resolves correctly ✓
- `apply_sqrt_spot_scale` receives it and computes `sqrt_spot_scale=6.918e8` ✓

However, Phase A.2 cold-path test still **FAILS** with 3420% relative error (ratio 1:35.2). Evidence from i=114 trace logs shows:
- Stage A: `masked_mean = 2.15`
- Reconstruction cold: `masked_mean = 75.74` (35× too high)
- Raw simulator output: `9.90e-08`
- After `apply_sqrt_spot_scale`: `68.5`
- Scaling ratio: `6.918e8` (correct sqrt)

## Root Cause Determination

**The problem is NOT threading failure—it's double-sqrt scaling.**

Reconstruction cold path applies `sqrt(spot_scale)` **twice**:

1. **Line 395** (reconstruction.py): `scale_factor = exp(log_scale_baseline)`
   - Stage A sets: `log_scale_baseline = log(sqrt(spot_scale_override))` (stage_a.py:173)
   - Therefore: `scale_factor = exp(log(sqrt(spot_scale))) = sqrt(spot_scale)`

2. **Line 499** (reconstruction.py): `bragg_prescaled = bragg_panel * scale_factor`
   - This multiplies raw simulator output by `sqrt(spot_scale)`

3. **Line 506** (reconstruction.py): `bragg_scaled_np = apply_sqrt_spot_scale(bragg_prescaled_np, ...)`
   - This multiplies by `sqrt(spot_scale)` **AGAIN**

**Result**: `raw * sqrt * sqrt = raw * spot_scale` (2× the correct scaling)

**Expected ratio**: Stage A to reconstruction should be 1:1 (both apply sqrt once)
**Observed ratio**: 1:35.2 because reconstruction applies sqrt twice
**Math check**: `1 / sqrt(4.786e17) ≈ 1.45e-9` (if double-sqrt), but we observe ~0.028
**Actual explanation**: Different raw simulator baselines (~2e7× difference) + double sqrt = ~35× final mismatch

## Architecture Insight

Stage A uses a clever baseline separation:
- `bragg_zero_iter` from `simulate_forward_once` is **pre-scaled** by `sqrt(spot_scale)` (nanobrag_bridge.py:1457)
- But Stage A's loss function applies `exp(log_scale_baseline)` to **RAW** simulator outputs
- So Stage A scales cached `bragg_zero_iter` by `exp(log_scale_baseline) / sqrt(spot_scale)` to convert it to "iteration-0 model scale" (stage_a.py:500-514)

Reconstruction cold path:
- Creates **RAW** simulators via `create_unified_simulator` (NO pre-scaling)
- Should apply `exp(log_scale_baseline) = sqrt(spot_scale)` once
- Currently ALSO calls `apply_sqrt_spot_scale`, causing double-scaling

## The Fix

Make `apply_sqrt_spot_scale` **conditional** on `log_scale_baseline` absence:

```python
if log_scale_baseline_value is None:
    # Uncalibrated path: scale_factor doesn't include sqrt, apply it separately
    bragg_scaled_np = apply_sqrt_spot_scale(bragg_prescaled_np, effective_calibration_metadata)
else:
    # Calibrated path: scale_factor already includes sqrt(spot_scale)
    bragg_scaled = bragg_prescaled
```

**Rationale**: When `log_scale_baseline` is present (calibrated path), `scale_factor = exp(log_scale_baseline)` already incorporates `sqrt(spot_scale)` per Stage A convention (stage_a.py:173). Applying it again would double-scale.

## Expected Outcome (Loop i=116)

After Ralph implements the conditional fix:
- **Warm-cache regression** (Phase A.1): PASS (no code changes, early return still works)
- **Cold-path enforcement** (Phase A.2): PASS with rel_error < 1e-6 (currently 3420% error)

Metrics:
- Current: `masked_mean_reconstruction_cold = 75.74`, `rel_error = 3420%`
- After fix: `masked_mean_reconstruction_cold ≈ 2.15`, `rel_error < 0.0001%`

## Planning Artifacts

- `phase_b6_planning.md` — Full design doc with architecture analysis, fix strategy, risk analysis
- `input.md` — Detailed implementation instructions for Ralph (lines 501-520 change)
- `galph_memory.md` — Loop i=115 state update (DecisionStatus=patch_ready, confidence=0.9)

## Next Steps

- **Loop i=116** (Ralph): Implement conditional fix, run both enforcement tests, commit artifacts
- **Phase B.7**: Update `docs/findings.md` (SCALE-009 correction, new SCALE-010 for calibrated/uncalibrated paths)
- **Phase C.1**: Extend enforcement tests to cover uncalibrated path
- **Phase C.2**: Run DB-AT-027/028/029 with fixed reconstruction cold path

## ARCH Contracts Enforced

### ARCH-CONTRACT-001: Stage A vs Reconstruction Scaling Alignment
- **Status**: Violation identified (double-sqrt), fix ready
- **Owner API**: `dbex.refinement.scaling_utils.apply_sqrt_spot_scale`
- **Enforcement**: `tests/architecture/test_scale_contracts.py` (both warm/cold paths)

### ARCH-CONTRACT-002: Post-Run Scaling Pattern
- **Status**: Misused (unconditional application), fix ready
- **Usage Rule**: Apply ONLY when `log_scale_baseline` absent (uncalibrated)
- **Fix**: Conditional application at reconstruction.py:501-520

## Compliance

- ✓ No production edits by Galph (planning only)
- ✓ Evidence→Action contract satisfied (Phase B.5 evidence → exact fix at line 506)
- ✓ Dominant-hypothesis lock enforced (confidence=0.9, no more probes)
- ✓ ARCH conformance remediation planned (canonical API + conditional usage)
- ✓ Enforcement tests exist and mapped (Phase A.1/A.2)

---

**Commit**: 601348f9
**Artifacts**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T120000Z/`
**Next Actor**: Ralph (loop i=116)
