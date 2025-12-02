# Ralph Implementation Report — ARCH-REFACTOR-001 Phase D.3 Reconstruction Bugfix

**Loop:** 2025-12-02 (Ralph implementation of Galph diagnosis)
**Commit:** 6db57f45
**Status:** Fix implemented correctly per specification, but tests still FAIL — suspected additional bug

---

## Implementation Summary

Applied calibration baseline logic fix to `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` (lines 195-217) exactly as specified in input.md and matching the normative pattern from stage_a.py:1194-1202.

### Changes Made

**File:** `dbex/refinement/reconstruction.py`
**Lines:** 195-217 (replaced lines 192-193)

**Before:**
```python
log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
scale_factor = torch.exp(log_scale_clamped)
```

**After:**
```python
# Extract log_scale_baseline from Stage A telemetry
log_scale_baseline_value = param_deltas_a.get('log_scale_baseline', {}).get('final')

# Apply conditional clamp logic matching stage_a.py:1194-1202
max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
delta_bound = getattr(config, "log_scale_max_delta", 3.0) if log_scale_baseline_value is not None else max_delta_uncal

if log_scale_baseline_value is not None:
    # Calibrated path: baseline + delta
    log_scale_baseline_tensor = torch.tensor(log_scale_baseline_value, device=device, dtype=dtype)
    log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
    log_scale_clamped = log_scale_baseline_tensor + log_scale_delta_clamped
else:
    # Uncalibrated path: absolute clamp
    log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)

scale_factor = torch.exp(log_scale_clamped)
```

---

## Validation Results

### Test Execution
```bash
DBAT028_ARTIFACT_DIR=plans/.../at028 \
DBAT029_ARTIFACT_DIR=plans/.../at029 \
pytest -vv test_db_at_028_loss_scale_sanity test_db_at_029_structure_parity
```

**Result:** 2/2 FAILED (both tests)

### Failure Signatures
- **DB-AT-028:** `chi²/pixel initial 1.084e+05 exceeds 1e2 bound`
- **DB-AT-029:** `median ROI correlation before refinement -0.050 below 0.2 floor`

### Metrics Observed (from artifacts/at028/db_at_028_metrics.json)
```json
{
  "log_scale_baseline": 20.138489594990745,
  "log_scale_final": 5.549979675834038e-08,
  "log_scale_effective_final": 20.13848965049054,
  "bragg_before_mean": 0.23937484622001648,
  "bragg_after_mean": 1.0249042134091724e-05,  ← STILL TOO SMALL
  "chi2_per_pixel_initial": 108375.87037603179,
  "spot_scale_override": 3.105058665484234e+17
}
```

### Expected vs. Actual

**Expected (from diagnosis):**
- `bragg_after_mean` ≈ O(1) ≈ 0.1–10 (matching `bragg_before_mean = 0.24`)
- scale_factor = exp(20.14) ≈ 5.57e8

**Actual:**
- `bragg_after_mean` = 1.02e-05 (factor of ~23,400 too small)
- scale_factor = 5.57e8 ✓ (CORRECT — verified via debug output)

---

## Debug Investigation

Added temporary debug logging to verify fix execution:

```
DEBUG reconstruction.py: log_scale_baseline_value=20.138489594990745, log_scale=5.549979675834038e-08
DEBUG reconstruction.py: log_scale_clamped=20.13848876953125, scale_factor=557230080.0
DEBUG reconstruction.py: Panel 0: bragg_panel mean=1.839e-14, max=7.566e-13
DEBUG reconstruction.py: Panel 0: bragg_scaled mean=1.025e-05, max=4.216e-04
```

### Key Findings

1. **Baseline extraction:** ✓ CORRECT (`log_scale_baseline_value = 20.14`)
2. **Scale factor calculation:** ✓ CORRECT (`scale_factor = 5.57e8`)
3. **Simulator raw output:** ✗ TOO SMALL (`bragg_panel mean = 1.839e-14`)

**Analysis:**
- `bragg_panel` (simulator raw) = 1.839e-14
- `scale_factor` = 5.57e8
- `bragg_scaled` = 1.839e-14 × 5.57e8 = 1.025e-05 ✓ (arithmetic checks out)
- Expected `bragg_after` ≈ 0.24
- Implies `bragg_panel` should be ≈ 0.24 / 5.57e8 ≈ 4.3e-10 (not 1.8e-14)

**Missing factor:** ~4.3e-10 / 1.8e-14 ≈ 23,900 ≈ 10^4.38

This missing factor does NOT match `spot_scale_override = 3.1e17` or `sqrt(spot_scale_override) = 5.57e8`.

---

## Root Cause Hypothesis

The fix I implemented is **architecturally correct** and matches the normative pattern exactly. However, the simulator raw output is unexpectedly small, suggesting one of:

1. **Warm vs. Cold path mismatch:** Warm-path simulators (reused from Stage A) may have `spot_scale_override` baked in, while cold-path simulators (built fresh) do not. The reconstruction helper may be hitting the wrong path or mixing conventions.

2. **Double-counting or missing scale:** Either:
   - Stage A training applies spot_scale at simulator construction time, but reconstruction doesn't
   - OR: Stage A applies spot_scale post-run via `sqrt_scale`, but reconstruction doesn't

3. **Telemetry structure mismatch:** The `log_scale` value extracted from telemetry may be normalized differently than assumed (e.g., already includes some scaling that the reconstruction helper is missing).

4. **Simulator construction bug:** The unified factory `create_unified_simulator` may not be applying calibration metadata correctly when `spot_scale_override=None`.

---

## Spec Compliance

**Implementation matches specification:**
- ✓ Pattern matches stage_a.py:1194-1202 exactly
- ✓ Baseline extraction from telemetry correct
- ✓ Conditional clamp logic correct
- ✓ Device/dtype handling correct
- ✓ Config attribute defaults correct

**But result violates acceptance criteria:**
- ✗ DB-AT-028: chi²/pixel exceeds bound by 1000×
- ✗ DB-AT-029: ROI correlation below floor

---

## Escalation Rationale

Per Ralph ground rules:
- **Repeat-failure guard:** Same acceptance criterion failed 3+ loops with same signature
- **Implementation budget:** This is the 4th attempt at DB-AT-028/029
- **Initiative-type guard:** Fix is scoped as `bugfix`, but failure persists despite correct implementation

**Recommendation:**
1. Mark Phase D.3 `blocked — suspected additional bug beyond diagnosed issue`
2. Open new diagnostic initiative to investigate simulator construction and warm/cold path handling
3. Consider `architecture` initiative if the issue is systemic convention mismatch between training and reconstruction

---

## Artifacts

- Commit: 6db57f45
- Pytest logs: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/pytest_db_at_028_029.log`
- Metrics JSON: `.../at028/db_at_028_metrics.json`, `.../at029/db_at_029_metrics.json`
- This report: `ralph_findings.md`

---

## Next Actions (for Galph)

1. Review debug evidence showing simulator raw output is 1e4.4× too small
2. Investigate how Stage A builds simulators (with or without spot_scale_override baked in)
3. Compare warm-path vs cold-path simulator construction in reconstruction helper
4. Consider whether `create_unified_simulator(..., spot_scale_override=None, ...)` is correct or if it should pass `calibration_metadata['spot_scale_override']`
5. Decide whether to:
   - Open `architecture` initiative for reconstruction/training convention alignment
   - Open `harness` initiative if tests encode wrong expectations
   - Open `spec_change` initiative if calibration semantics need clarification

