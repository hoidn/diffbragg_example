# Stage A Mapping Alignment Diagnosis

**Generated:** 2025-11-24T213251Z
**Focus:** TOOLING-VIS-001 Phase D.A — Stage A vs Mapping Forward Model Parity
**Spec References:**
- `docs/spec-db-conformance.md:201-280` (DB-AT-027/028/029)
- `docs/spec-db-workflow.md:42-58` (Stage A mapping zero-point invariant)

## Summary

This diagnostic compares the **DB-AT-024 mapping baseline** (canonical `simulate_forward_once`) against the **Stage A refinement driver** to validate DB-AT-027/028/029 conformance on the `simple_cubic` fixture.

## Key Findings

### 1. DB-AT-027: Stage A Zero-Point Mapping Equivalence

**Goal:** Stage A zero-parameter forward model must match DB-AT-024 mapping forward model.

| Metric | Value | Spec Tolerance | Status |
|--------|-------|----------------|--------|
| **mean_abs_diff** (mapping vs Stage A before) | **77.43 ADU** | ≤ 1e-3 ADU | ❌ **FAIL** |
| **max_abs_diff** (mapping vs Stage A before) | **38,406.92 ADU** | ≤ 200 ADU | ❌ **FAIL** |

**Analysis:**
The Stage A "before" model (zero-parameter reconstruction) exhibits massive divergence from the mapping baseline, with a mean absolute difference of ~77 ADU and peak differences exceeding 38,000 ADU. This violates DB-AT-027 by **multiple orders of magnitude**.

**Likely Root Cause:**
The `bragg_before` reconstruction uses Stage A telemetry with initial parameters set, but the **scale ratio** between mapping and Stage A before is `7.11e-05`, indicating Stage A's initial forward model is effectively producing near-zero intensities. This suggests either:
1. Initial `log_scale` is not properly aligned with the mapping calibration (`spot_scale_override`),
2. Geometry parameterization (`U(0)`, `B(0)`) does not reproduce the mapping baseline,
3. Missing or incorrect application of `spot_scale_override` in the Stage A forward path.

### 2. DB-AT-028: Stage A Loss-Scale and Clamp Sanity

**Goal:** Stage A chi² values must remain in a physically reasonable regime.

| Metric | Value | Spec Tolerance | Status |
|--------|-------|----------------|--------|
| **chi2_per_pixel_initial** | **109,022.21** | ≤ 100 | ❌ **FAIL** |
| **chi2_per_pixel_final** | **23,541.64** | ≤ 100 | ❌ **FAIL** |
| **variance_floor_clamp_fraction** | 0.0 | < 0.5 | ✅ PASS |
| **chi2 improvement direction** | Initial > Final | Final ≤ Initial | ✅ PASS |

**Analysis:**
Both initial and final chi²-per-pixel are ~1000x larger than the spec tolerance of 100. The variance floor is not clamping pixels (clamp_fraction = 0.0), which is correct, but the chi² magnitude indicates the Stage A forward model is producing predictions that are wildly inconsistent with the experimental data even after refinement.

**Comparison to Mapping Baseline:**
- **Mapping chi²** (DB-AT-024): 989,811.51
- **Mapping chi²_per_pixel**: 989,811.51 / 13,084 = **75.64**
- **Stage A chi²_per_pixel_initial**: 109,022.21
- **Stage A chi²_per_pixel_final**: 23,541.64

The mapping baseline satisfies the chi²_per_pixel ≤ 100 tolerance, while Stage A does not, even after 30 LBFGS iterations.

### 3. DB-AT-029: Stage A Intensity and Structure Parity

**Goal:** Stage A predictions must have reasonable intensity scale and ROI structure.

#### Global Intensity Scale Ratios

| Metric | Value | Spec Tolerance | Status |
|--------|-------|----------------|--------|
| **scale_ratio_before** (mean_model_before / mean_data) | **7.11e-05** | [1e-2, 1e2] | ❌ **FAIL** |
| **scale_ratio_after** (mean_model_after / mean_data) | **1.92** | [1e-2, 1e2] | ✅ PASS |

**Analysis:**
The initial Stage A forward model produces intensities ~10,000x too small (scale_ratio_before = 7.11e-05), which is outside the spec band of [0.01, 100] by multiple orders of magnitude. After refinement, the scale_ratio_after recovers to 1.92, which is within the spec band and close to the mapping baseline scale hint of 62.66.

#### ROI Correlation Floor

| Metric | Value | Spec Tolerance | Status |
|--------|-------|----------------|--------|
| **median_cc_mapping** | **0.491** | ≥ 0.2 | ✅ PASS |
| **median_cc_stage_a_before** | **0.128** | ≥ 0.2 | ❌ **FAIL** |
| **median_cc_stage_a_after** | **0.128** | ≥ 0.2 | ❌ **FAIL** |
| **correlation collapse** (after - before) | **0.000** | ≥ -0.05 | ✅ PASS |

**Analysis:**
The mapping baseline achieves a median ROI correlation of 0.491, comfortably above the 0.2 floor. Stage A's median correlation (both before and after) is 0.128, which fails the 0.2 floor requirement. The **lack of improvement** in correlation (before ≈ after) indicates that the Stage A refinement is not meaningfully adjusting the structural alignment of the predicted ROIs with the experimental data, likely because the chi² optimization is dominated by the massive scale mismatch.

**Per-ROI Correlation Samples (first 6 ROIs):**

| ROI | cc_mapping | cc_stage_a_before | cc_stage_a_after |
|-----|------------|-------------------|------------------|
| 0   | 0.403      | 0.130             | 0.130            |
| 1   | 0.310      | 0.202             | 0.202            |
| 2   | 0.005      | 0.048             | 0.048            |
| 3   | 0.229      | 0.039             | 0.039            |
| 4   | 0.601      | 0.135             | 0.135            |
| 5   | 0.665      | 0.074             | 0.074            |

Most ROIs show a significant drop from mapping correlations to Stage A correlations, with essentially no change before/after Stage A refinement. This suggests the Stage A forward model is not correctly reproducing the mapping Bragg tensor at the zero point.

## Conformance Status Summary

| Test | Status | Primary Issue |
|------|--------|---------------|
| **DB-AT-027** (Zero-Point Equivalence) | ❌ **FAIL** | Mean/max abs diff mapping vs Stage A before ~1e3–1e5x spec tolerance |
| **DB-AT-028** (Loss-Scale Sanity) | ❌ **FAIL** | chi²_per_pixel ~1000x too large (initial and final) |
| **DB-AT-029** (Intensity/Structure Parity) | ❌ **FAIL** | scale_ratio_before ~10,000x too small; median_cc_stage_a < 0.2 floor |

## Detailed Metrics Reference

### Mapping Baseline (DB-AT-024)

```json
{
  "chi_squared": 989811.51,
  "sigma_floor_value": 1.0,
  "variance_floor_masked_pixels": 13084,
  "variance_floor_clamp_fraction": 0.0,
  "median_cc_mapping": 0.491,
  "spot_scale_override": 3.1847e+17,
  "global_scale_hint": 62.66
}
```

### Stage A Driver Metrics

```json
{
  "chi2_initial": 1426446592.0,
  "chi2_final": 308018848.0,
  "chi2_per_pixel_initial": 109022.21,
  "chi2_per_pixel_final": 23541.64,
  "variance_floor_clamp_fraction": 0.0,
  "mean_data": 63.03,
  "mean_model_before": 0.0045,
  "mean_model_after": 121.24,
  "scale_ratio_before": 7.11e-05,
  "scale_ratio_after": 1.92,
  "mean_abs_diff_mapping": 77.43,
  "max_abs_diff_mapping": 38406.92,
  "median_cc_mapping": 0.491,
  "median_cc_stage_a_before": 0.128,
  "median_cc_stage_a_after": 0.128
}
```

### Chi² Trace (Stage A LBFGS, 30 iterations)

```
Iteration 0: 1,426,446,592.0
Iteration 1: 1,425,177,600.0
Iteration 2:   170,089,392.0
Iteration 3:   308,018,848.0
```

**Observation:** Chi² drops by ~8x from iteration 0→2, then **increases** at iteration 3, suggesting a non-monotonic LBFGS step or possible line-search failure. This may indicate the loss surface is ill-conditioned due to the massive scale mismatch at the initial point.

## Recommended Next Steps (Phase D.B0)

1. **Zero-Point Probe (D.B0.1):** Implement a Stage A zero-parameter forward evaluation that explicitly reuses the mapping calibration (`spot_scale_override`, `beam_flux`, `beam_exposure`, `beamsize_mm`, `N_cells`) and the exact HKL grid from `build_mapping_stage_a_context`. Validate that `bragg_stagea_zero` matches `bragg_mapping` within DB-AT-027 tolerances (mean_abs_diff ≤ 1e-3, max_abs_diff ≤ 200).

2. **Calibration Plumbing (D.B0.2):** Audit the Stage A forward path in `_build_final_bragg_from_stage_a_telemetry` to ensure `spot_scale_override` is applied to the raw nanoBragg simulation output. Currently, the `scale_ratio_before = 7.11e-05` suggests the raw simulation is not being scaled by the calibration factor.

3. **Geometry Baseline Alignment (D.B0.3):** Confirm that `U(0) = U₀` and `B(0) = B₀` per `spec-db-workflow.md:45-46`. If Stage A uses a different parameterization (e.g., `crystal_overrides` instead of MOSFLM A* injection), ensure the baseline misset is correctly encoded such that zero deltas reproduce the mapping geometry.

4. **Scale Initialization (D.B0.4):** Investigate whether Stage A's initial `log_scale` parameter should be warm-started from the mapping `global_scale_hint` (62.66) rather than zero, to avoid the ~10,000x scale mismatch at the initial point.

5. **Rerun Diagnosis After Fixes:** Once D.B0 zero-point plumbing is complete, rerun this driver with the same 30-iteration LBFGS configuration and verify:
   - `mean_abs_diff_mapping ≤ 1e-3` (DB-AT-027)
   - `chi2_per_pixel_initial ≤ 100` (DB-AT-028)
   - `scale_ratio_before ∈ [1e-2, 1e2]` (DB-AT-029)
   - `median_cc_stage_a_before ≥ 0.2` (DB-AT-029)

## Artifacts

- **Mapping baseline metrics:** `plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/db_at_024/mapping_metrics.json`
- **Stage A driver metrics:** `plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/stage_a_refgeom_run/stage_a_mapping_gap_metrics.json`
- **Driver log:** `plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/stage_a_driver.log`
- **ROI triptychs:** `plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/stage_a_refgeom_run/roi_triptychs/`
- **Loss curve:** `plans/active/TOOLING-VIS-001/reports/2025-11-24T213251Z/stage_a_refgeom_run/stage_a_loss_curve.png`
