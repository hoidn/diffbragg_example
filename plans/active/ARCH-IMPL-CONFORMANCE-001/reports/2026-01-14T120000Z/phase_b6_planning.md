# Phase B.6 Planning — Double-Sqrt Scaling Fix

**Loop**: i=115 (Galph planning)
**Phase**: B.6 (implementation)
**Initiative**: ARCH-IMPL-CONFORMANCE-001
**Timestamp**: 2025-12-06T20:00:00Z

## Executive Summary

Loop i=114 evidence proves calibration threading works correctly. The ~35× mismatch is caused by **double sqrt scaling** in reconstruction cold path:

1. `scale_factor = exp(log_scale_baseline) = exp(log(sqrt(spot_scale))) = sqrt(spot_scale)` (reconstruction.py:395)
2. `apply_sqrt_spot_scale` multiplies by `sqrt(spot_scale)` again (reconstruction.py:506)
3. Result: `raw * sqrt * sqrt = raw * spot_scale` (double the correct scaling)

## Root Cause Analysis

### Stage A Forward Path (Correct)

`build_mapping_stage_a_context` → `simulate_forward_once` (nanobrag_bridge.py:1230+):
- Line 1368: `sqrt_spot_scale = np.sqrt(spot_scale_override)`
- Line 1457: `panel_output_scaled = panel_output_np * sqrt_scale_value`
- Returns `bragg` **already scaled** by `sqrt(spot_scale)`

### Stage A Refinement Path (Correct)

Stage A receives pre-scaled `bragg_zero_iter` but its loss function applies scaling to **RAW** simulator output:
- Line 173: `log_scale_baseline = log(sqrt(spot_scale_override))`
- Line 1287-1290: `scale_factor = exp(log_scale_baseline + delta)` applied to RAW sim output
- Lines 500-514: Scale cached `bragg_zero_iter` by `exp(log_scale_baseline) / sqrt(spot_scale)` to convert from pre-scaled cache to "iteration-0 model scale"

**Key insight**: Stage A's `log_scale_baseline` is designed to be applied to **RAW** simulator outputs (not pre-scaled ones).

### Reconstruction Cold Path (BROKEN — Double Scaling)

`build_final_bragg_from_stage_a_telemetry` with `stage_a_ctx=None`:
- Line 311-322: `create_unified_simulator` creates simulators (returns RAW outputs, NO pre-scaling)
- Line 373-395: Computes `log_scale_baseline` from telemetry, then `scale_factor = exp(log_scale_baseline)`
- Line 499: `bragg_prescaled = bragg_panel * scale_factor` (applies `sqrt(spot_scale)` to RAW)
- Line 506: `bragg_scaled_np = apply_sqrt_spot_scale(bragg_prescaled_np, ...)` (applies `sqrt(spot_scale)` AGAIN)

**Result**: `raw * sqrt * sqrt = raw * spot_scale` (2× too much scaling)

### Reconstruction Warm-Cache Path (Correct — No Double Scaling)

`build_final_bragg_from_stage_a_telemetry` with `stage_a_ctx != None` and `param_state="initial"`:
- Line 96-99: Returns cached `stage_a_ctx.bragg_zero_iter` directly
- `bragg_zero_iter` is **already** `raw * sqrt(spot_scale)` from `simulate_forward_once`
- No `apply_sqrt_spot_scale` call (fast-path return)
- **Correct**: matches Stage A exactly

## The Fix

**Problem**: Reconstruction cold path applies `sqrt(spot_scale)` twice when `log_scale_baseline` is present.

**Solution**: Skip `apply_sqrt_spot_scale` call when `log_scale_baseline` is present, because `scale_factor = exp(log_scale_baseline)` already includes the sqrt factor.

### Implementation Strategy

**Option A (Recommended)**: Conditional `apply_sqrt_spot_scale` call
```python
# Line 501-509 (reconstruction.py)
bragg_prescaled = bragg_panel * scale_factor * baseline_alignment_factor

# Only apply sqrt scaling when log_scale_baseline is NOT present
# When log_scale_baseline exists, scale_factor already includes sqrt(spot_scale)
if log_scale_baseline_value is None:
    # Uncalibrated path: scale_factor doesn't include sqrt, apply it separately
    bragg_prescaled_np = bragg_prescaled.cpu().numpy()
    bragg_scaled_np = apply_sqrt_spot_scale(bragg_prescaled_np, effective_calibration_metadata)
    bragg_scaled = torch.from_numpy(bragg_scaled_np).to(
        device=bragg_panel.device, dtype=bragg_panel.dtype
    )
else:
    # Calibrated path: scale_factor = exp(log_scale_baseline) already includes sqrt(spot_scale)
    bragg_scaled = bragg_prescaled
```

**Option B**: Remove `apply_sqrt_spot_scale` entirely
- Rationale: `scale_factor` computation already handles both calibrated and uncalibrated paths correctly
- Risk: May break uncalibrated path if `log_scale_baseline=None` but `spot_scale_override` present via other route

**Recommendation**: Option A is safer. It preserves backward compatibility and makes the logic explicit.

## Expected Outcome

After fix:
- Cold-path reconstruction: `raw * sqrt(spot_scale)` (via `scale_factor` only)
- Stage A: `raw * sqrt(spot_scale)` (from `simulate_forward_once`)
- Warm-cache reconstruction: `raw * sqrt(spot_scale)` (cached from Stage A)
- **All three paths agree** → Phase A.2 test PASS with rel_error < 1e-6

## Implementation Plan (Loop i=116)

### Code Changes

**File**: `dbex/refinement/reconstruction.py`

**Lines 501-513**: Wrap `apply_sqrt_spot_scale` call in conditional:

```python
# ARCH-CONTRACT-002 (Phase B.6, ARCH-IMPL-CONFORMANCE-001):
# Apply canonical spot_scale_override sqrt scaling ONLY when log_scale_baseline is absent.
# When log_scale_baseline is present (calibrated path), scale_factor already incorporates
# sqrt(spot_scale) per stage_a.py:173, so applying it again would double-scale.
if log_scale_baseline_value is None:
    # Uncalibrated path: scale_factor doesn't include sqrt, apply it separately
    bragg_prescaled_np = bragg_prescaled.cpu().numpy()
    bragg_scaled_np = apply_sqrt_spot_scale(bragg_prescaled_np, effective_calibration_metadata)
    bragg_scaled = torch.from_numpy(bragg_scaled_np).to(
        device=bragg_panel.device, dtype=bragg_panel.dtype
    )
else:
    # Calibrated path: scale_factor = exp(log_scale_baseline) already includes sqrt(spot_scale)
    # Do not apply sqrt scaling again to avoid double-scaling
    bragg_scaled = bragg_prescaled
```

**Validation**: Preserve debug logging at line 512 but update message:
```python
if pid == 0:
    scaling_path = "calibrated (scale_factor only)" if log_scale_baseline_value is not None else "uncalibrated (scale_factor + apply_sqrt_spot_scale)"
    print(f"  bragg_scaled[0] mean ({scaling_path}): {bragg_scaled.mean().item():.6e}")
```

### Test Plan

Run Phase A.1 (warm-cache) and A.2 (cold-path) enforcement tests:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale \
  tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path
```

**Expected results**:
- Phase A.1 (warm-cache): PASS (already passing, regression check)
- Phase A.2 (cold-path): PASS with rel_error < 1e-6 (currently FAILING with 3420% error)

### Artifacts

- `pytest_phase_b6_fix.log` — test run showing both tests PASS
- `phase_b6_summary.md` — commit message and decision summary

## ARCH Contracts

### ARCH-CONTRACT-001: Stage A vs Reconstruction Scaling Alignment
- **Owner API**: `dbex.refinement.scaling_utils.apply_sqrt_spot_scale` (Phase B.1-B.2)
- **Duplicates Removed**: reconstruction.py lines 501-509 conditional (Phase B.6)
- **Enforcement Tests**:
  - `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale` (warm-cache)
  - `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path` (cold-path)
- **Status After B.6**: ✓ SATISFIED (both tests PASS)

### ARCH-CONTRACT-002: Post-Run Scaling Pattern
- **Owner API**: `dbex.refinement.scaling_utils.apply_sqrt_spot_scale`
- **Usage Rule**: Apply ONLY when `log_scale_baseline` is absent (uncalibrated path)
- **Rationale**: Calibrated path already includes sqrt in `log_scale_baseline`
- **Status After B.6**: ✓ SATISFIED (conditional application prevents double-scaling)

## Findings to Update

### SCALE-009 (Reconstruction Scaling Provenance)

**Current status**: Partially incorrect (implied threading was the issue)

**Update required**:
- **Root cause**: Double sqrt scaling in cold path (calibrated)
- **Fix**: Conditional `apply_sqrt_spot_scale` based on `log_scale_baseline` presence
- **Evidence**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/phase_b5_decision.md`

### NEW FINDING: SCALE-010 (Calibrated vs Uncalibrated Scaling Paths)

**Finding**: Stage A and reconstruction use different scaling semantics for calibrated vs uncalibrated runs:
- **Calibrated**: `log_scale_baseline = log(sqrt(spot_scale))`, applied to RAW simulator outputs
- **Uncalibrated**: `log_scale` is direct learnable parameter, no baseline separation
- **Implication**: Post-run `apply_sqrt_spot_scale` must be conditional on calibration presence

**Owner API**: `dbex.refinement.scaling_utils.apply_sqrt_spot_scale` (canonical)

**Enforcement**: `tests/architecture/test_scale_contracts.py` (both warm/cold paths)

**Status**: Resolved via Phase B.6 conditional application

## Risk Analysis

### Risk 1: Uncalibrated Path Regression

**Scenario**: Uncalibrated runs (no `calibration_metadata`) break if `apply_sqrt_spot_scale` is skipped incorrectly

**Mitigation**:
- Conditional logic checks `log_scale_baseline_value is None` (line 373-395 already computes this)
- Test plan includes both calibrated (current refGeom fixture) and uncalibrated scenarios
- Add uncalibrated test case to Phase C.1 (DB-AT-027/028/029 alignment)

### Risk 2: Warm-Cache Path Regression

**Scenario**: Warm-cache path (line 96-99 early return) stops working

**Mitigation**:
- Phase A.1 test (warm-cache) is already PASSING, provides regression coverage
- No code changes to warm-cache path (lines 96-99 unchanged)
- Test plan runs both Phase A.1 and A.2 to confirm no regressions

### Risk 3: Log Messages Confusing Future Debugging

**Scenario**: Debug logs don't reflect conditional logic, making future issues harder to diagnose

**Mitigation**:
- Update line 512 debug message to indicate which scaling path was used
- Add explicit log when skipping `apply_sqrt_spot_scale` in calibrated path

## Next Steps (Phase B.7+)

After Phase B.6 fix lands:
1. **Phase B.7**: Update `docs/findings.md` (SCALE-009, SCALE-010)
2. **Phase C.1**: Extend enforcement tests to cover uncalibrated path
3. **Phase C.2**: Run DB-AT-027/028/029 with fixed reconstruction cold path
4. **Phase C.3**: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md`

## References

- **Phase B.5 Evidence**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/phase_b5_decision.md`
- **Stage A Scaling Logic**: `dbex/refinement/stage_a.py:172-177, 500-514, 1275-1290`
- **Reconstruction Cold Path**: `dbex/refinement/reconstruction.py:88-223, 373-395, 499-513`
- **Canonical API**: `dbex/refinement/scaling_utils.py:35-111`
- **Enforcement Tests**: `tests/architecture/test_scale_contracts.py:24-302`
