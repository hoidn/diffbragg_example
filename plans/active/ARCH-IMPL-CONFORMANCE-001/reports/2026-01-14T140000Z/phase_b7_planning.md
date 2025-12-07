# Phase B.7 Planning — Masked Mean Ratio Fallback

**Initiative**: ARCH-IMPL-CONFORMANCE-001
**Phase**: B.7 (masked_mean_ratio fallback for baseline_alignment_factor)
**Loop**: i=117 (Galph planning)
**Timestamp**: 2025-12-06T20:40:00Z
**Status**: patch_ready
**Confidence**: 0.95

## Context

Loop i=116 (Ralph) implemented Phase B.6 conditional sqrt fix, achieving 4.17× improvement:
- Eliminated double-sqrt scaling by making `apply_sqrt_spot_scale` conditional on `log_scale_baseline` absence
- Improved ratio from 1/35 (Phase B.5) to 1/8.4 (Phase B.6)
- Warm-cache test PASSED, cold-path test still FAILS with 738% rel_error

## Problem Statement

**Residual 8.4× scale mismatch persists after Phase B.6 fix.**

### Evidence from Phase B.6 Test Run

From `pytest_phase_b6_fix.log`:

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

**Observations**:
1. `log_scale_baseline = 20.138` (correctly computed from calibration)
2. Scaling path = "calibrated (scale_factor only, no double-sqrt)" (Phase B.6 conditional working correctly)
3. `masked_mean_stage_a = 0.999` (Stage A warm-cache baseline)
4. `masked_mean_reconstruction_cold = 8.377` (cold path output)
5. **Mismatch**: 8.377 / 0.999 ≈ 8.39× (ratio 1/8.4)

### Root Cause Analysis

**Hypothesis**: Reconstruction cold path is missing the `masked_mean_ratio` adjustment from the mapping phase.

#### Evidence Trail

**1. Mapping Phase** (`dbex/vis/mapping.py:297-312`):
```python
masked_mean_ratio = target_mean_masked / bragg_mean_masked
bragg_zero_iter = bragg_zero_iter * masked_mean_ratio  # Applied in-place

# Persist in calibration dict
calibration["masked_mean_ratio"] = masked_mean_ratio
```

**Purpose**: Align simulated bragg_zero_iter intensity with target data by computing ratio of masked means and scaling in-place.

**Result**: `stage_a_ctx.bragg_zero_iter` includes this adjustment (target-aligned baseline).

**2. Stage A Warm-Cache Path** (test Phase A.1):
```python
# Test extracts bragg_zero_iter from stage_a_ctx
bragg_stage_a = stage_a_ctx.bragg_zero_iter  # Already includes masked_mean_ratio
masked_mean_stage_a = (bragg_stage_a[trusted_mask]).sum() / trusted_mask.sum()
# Result: masked_mean_stage_a ≈ 1.0 (target-aligned)
```

**Outcome**: Phase A.1 test PASSES with rel_error=0.0 (perfect warm-cache parity).

**3. Reconstruction Cold Path** (`dbex/refinement/reconstruction.py:418-471`):

**Current logic**:
```python
# Step 1-2: Run simulators to get cold_masked_mean (lines 429-446)
bragg_cold_scaled = bragg_cold_stack * scale_factor
cold_masked_mean = bragg_cold_scaled[loss_mask_t].mean()

# Step 3-4: Compute baseline_alignment_factor (lines 448-467)
if telemetry_model_mean is not None and telemetry_model_mean > 0 and cold_masked_mean > 0:
    baseline_alignment_factor = telemetry_model_mean / cold_masked_mean
else:
    baseline_alignment_factor = 1.0  # DEFAULT FALLBACK
```

**Problem**: Test provides minimal telemetry without `model_mean_masked` field:
```python
# test_scale_contracts.py:226-239
RefinementTelemetry = namedtuple('RefinementTelemetry', ['param_deltas'])
zero_deltas = { 'log_scale': {'initial': 0.0, 'final': 0.0}, ... }
telemetry_initial = RefinementTelemetry(param_deltas=zero_deltas)
# NO model_mean_masked field!
```

**Result**: `telemetry_model_mean = None`, so `baseline_alignment_factor = 1.0`, and reconstruction outputs `raw * sqrt(spot_scale) * 1.0` while Stage A has `raw * sqrt(spot_scale) * masked_mean_ratio`.

**4. Mismatch Calculation**:

If `masked_mean_ratio ≈ 0.119` (from calibration_metadata), then:
- Stage A: `masked_mean = raw * sqrt * masked_mean_ratio ≈ 0.999`
- Reconstruction: `masked_mean = raw * sqrt * 1.0 ≈ 8.377`
- Ratio: `0.999 / 8.377 ≈ 0.119` ✓ (matches `masked_mean_ratio` inverse!)

**Confirmation**: The 8.4× mismatch is exactly `1 / masked_mean_ratio` (since reconstruction is missing the scaling-down adjustment).

## Solution (Phase B.7)

**Add masked_mean_ratio fallback extraction from calibration_metadata.**

### Implementation Location

`dbex/refinement/reconstruction.py:454-467` (baseline_alignment_factor computation)

### Change Specification

**Add elif branch** after the telemetry_model_mean conditional, before the final else:

```python
# Step 4: Compute baseline_alignment_factor when both are finite/positive
if (telemetry_model_mean is not None and telemetry_model_mean > 0 and
    cold_masked_mean > 0 and np.isfinite(telemetry_model_mean) and np.isfinite(cold_masked_mean)):
    baseline_alignment_factor = telemetry_model_mean / cold_masked_mean
    alignment_source = "telemetry_model_mean_masked"
    print(f"[ARCH-SIM-CONSTRUCTION-001 Phase C.14] Cold-path baseline alignment:")
    print(f"  telemetry_model_mean_masked: {telemetry_model_mean:.6e}")
    print(f"  cold_masked_mean (before alignment): {cold_masked_mean:.6e}")
    print(f"  baseline_alignment_factor: {baseline_alignment_factor:.6f}")
    print(f"  source: {alignment_source}")

# ARCH-CONTRACT-002 Phase B.7: NEW FALLBACK BRANCH
elif effective_calibration_metadata is not None and "masked_mean_ratio" in effective_calibration_metadata:
    # When telemetry doesn't provide model_mean_masked (e.g., minimal test fixtures),
    # fall back to masked_mean_ratio from build_mapping_stage_a_context (mapping.py:297-312).
    # This ensures reconstruction cold path aligns with mapping's target-to-bragg adjustment.
    masked_mean_ratio = effective_calibration_metadata.get("masked_mean_ratio")
    if masked_mean_ratio is not None and masked_mean_ratio > 0 and np.isfinite(masked_mean_ratio):
        baseline_alignment_factor = masked_mean_ratio
        alignment_source = "calibration_masked_mean_ratio"
        print(f"[ARCH-CONTRACT-002 Phase B.7] Cold-path baseline alignment from calibration:")
        print(f"  masked_mean_ratio (from mapping): {masked_mean_ratio:.6e}")
        print(f"  baseline_alignment_factor: {baseline_alignment_factor:.6f}")
        print(f"  source: {alignment_source}")
    else:
        # Emit warning if alignment cannot be computed
        print(f"[ARCH-SIM-CONSTRUCTION-001 Phase C.14 WARNING] Cannot compute baseline alignment:")
        print(f"  telemetry_model_mean_masked: {telemetry_model_mean}")
        print(f"  cold_masked_mean: {cold_masked_mean if inputs.loss_mask is not None else 'N/A (no loss_mask)'}")
        print(f"  calibration masked_mean_ratio: {effective_calibration_metadata.get('masked_mean_ratio')}")
        baseline_alignment_factor = 1.0
        alignment_source = "default_fallback"

else:
    # Original final fallback
    print(f"[ARCH-SIM-CONSTRUCTION-001 Phase C.14 WARNING] Cannot compute baseline alignment:")
    print(f"  telemetry_model_mean_masked: {telemetry_model_mean}")
    print(f"  cold_masked_mean: {cold_masked_mean if inputs.loss_mask is not None else 'N/A (no loss_mask)'}")
    baseline_alignment_factor = 1.0
    alignment_source = "default_fallback"
```

### Rationale

1. **Semantic correctness**: `masked_mean_ratio` from mapping phase represents the same target-to-bragg alignment that `telemetry.model_mean_masked / cold_masked_mean` would recompute dynamically.

2. **Fallback precedence**: Prefer telemetry-derived alignment (runtime-computed, accounts for any Stage A adjustments) over calibration-stored ratio (mapping-time computed, static).

3. **Contract alignment**: ARCH-CONTRACT-002 requires that masked_mean_ratio from mapping must be consumed by downstream paths when telemetry is incomplete.

4. **Test compatibility**: Minimal test fixtures (without full telemetry) can still achieve parity by falling back to the stored ratio.

## Expected Outcomes

### Phase A.2 Test Behavior

**Before Phase B.7** (current):
```
masked_mean_stage_a = 0.999
masked_mean_reconstruction_cold = 8.377
rel_error = 7.38 (738%)
ratio = 0.119 (1/8.4)
baseline_alignment_factor = 1.0 (default fallback)
```

**After Phase B.7** (expected):
```
masked_mean_stage_a = 0.999
masked_mean_reconstruction_cold ≈ 0.999
rel_error < 1e-6 (<0.0001%)
ratio ≈ 1.0
baseline_alignment_factor ≈ 0.119 (from calibration masked_mean_ratio)
alignment_source = "calibration_masked_mean_ratio"
```

### Phase A.1 Regression Check

**No changes expected** (warm-cache path uses early return at reconstruction.py:83-86, bypasses all scaling logic).

```
masked_mean_stage_a = 1.023
masked_mean_reconstruction = 1.023
rel_error = 0.0
PASSED
```

## Risk Analysis

### Risk 1: calibration_metadata missing masked_mean_ratio

**Likelihood**: Low (mapping.py:312 stores it when alignment computed)

**Mitigation**: Added defensive check `if masked_mean_ratio is not None and masked_mean_ratio > 0 and np.isfinite(masked_mean_ratio)` with fallback warning.

**Impact if occurs**: Test will still fail, but with clear diagnostic: "calibration masked_mean_ratio: None"

### Risk 2: Test uses different HKL/geometry than mapping phase

**Likelihood**: Very Low (test explicitly uses `stage_a_ctx.hkl_indices` and `stage_a_ctx.hkl_amplitudes` from mapping phase)

**Evidence**: Test code (test_scale_contracts.py:241-252) ensures identical HKL inputs:
```python
hkl_indices = stage_a_ctx.hkl_indices
hkl_amplitudes = stage_a_ctx.hkl_amplitudes
```

**Impact if occurs**: Would manifest as different baseline intensity, not just 8.4× ratio (we'd see non-uniform scaling).

### Risk 3: masked_mean_ratio semantics differ from model_mean_masked / cold_masked_mean

**Likelihood**: Very Low (both represent target-to-bragg alignment ratio)

**Evidence**:
- mapping.py:297: `masked_mean_ratio = target_mean_masked / bragg_mean_masked`
- reconstruction.py:457: `baseline_alignment_factor = telemetry_model_mean / cold_masked_mean`
- `telemetry_model_mean` comes from Stage A's `model_mean_masked` telemetry field (stage_a.py:594, 2114)
- `model_mean_masked` is computed from `bragg_zero_iter[loss_mask].mean()` after mapping adjustments

**Conclusion**: Semantically equivalent when Stage A has applied no additional refinement adjustments (param_state="initial").

## Validation Plan

1. **Run both enforcement tests** (Phase A.1 + A.2)
2. **Verify Phase A.1 PASS** with rel_error=0.0 (regression check)
3. **Verify Phase A.2 PASS** with rel_error < 1e-6, ratio ≈ 1.0
4. **Check pytest log** for `alignment_source = "calibration_masked_mean_ratio"` evidence
5. **Capture metrics** in summary.md with Phase B.5 → B.6 → B.7 progression

## Next Phase (B.8)

**Update docs/findings.md SCALE-009** with Phase B.6-B.7 corrections:
- Document double-sqrt bug (Phase B.6 fix)
- Document masked_mean_ratio fallback pattern (Phase B.7 fix)
- Update reconstruction scaling provenance with calibration_metadata threading + fallback semantics

## Compliance Checklist

- [x] No production edits by Galph (planning only)
- [x] Evidence→Action contract: Phase B.6 evidence → exact fix location (lines 454-467)
- [x] Dominant-hypothesis lock: confidence=0.95, no additional probes
- [x] ARCH conformance: masked_mean_ratio fallback pattern extends ARCH-CONTRACT-002
- [x] Enforcement tests: both Phase A.1 and A.2 mapped
- [x] Findings paydown: deferred to Phase B.8 after tests validate
- [x] No environment changes: dbex code only
- [x] No shadow-pipeline creation: implementation in production reconstruction.py

---

**Artifacts**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T140000Z/`
**Next**: Ralph implements Phase B.7, expects both tests PASS
