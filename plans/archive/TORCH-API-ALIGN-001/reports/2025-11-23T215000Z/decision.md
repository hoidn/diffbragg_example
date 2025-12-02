# TORCH-API-ALIGN-001 Phase B3 Evidence Gathering — Decision

**Loop:** Ralph 2025-11-23T215000Z
**Focus:** TORCH-API-ALIGN-001 Phase B3 Tolerance Analysis
**Date:** 2025-11-23

## Executive Summary

**Verdict:** Path C — Significant implementation bug detected (max abs diff > 1e-03).

**Evidence:** Tolerance sweep experiment reveals:
- **max_abs_diff = 5.03e-03** (beyond numerical budget by 50x)
- **MSE = 2.41e-11** (excellent! 99.99% of pixels match within floating-point precision)
- **Only 1 outlier pixel** out of 1,048,576 total pixels (0.000095%)
- **Outlier persists** across ALL tested tolerances (1e-06 to 1e-03)

**Conclusion:** This is NOT a tolerance calibration issue. The single-pixel outlier with magnitude 5.03e-03 indicates a **localized implementation bug**, likely in:
1. ExperimentModel boundary condition handling (edge pixel?)
2. HKL grid lookup edge case
3. Coordinate transform singularity

**Phase B3 Status:** **BLOCKED** — suspected bug in ExperimentModel or adapter

## Detailed Analysis

### Tolerance Sweep Results

From `tolerance_sweep.json`:

| Tolerance | Outlier Count | Outlier Fraction | Pass/Fail |
|-----------|---------------|------------------|-----------|
| 1e-06     | 1             | 0.000095%        | FAIL      |
| 5e-06     | 1             | 0.000095%        | FAIL      |
| 1e-05     | 1             | 0.000095%        | FAIL      |
| 5e-05     | 1             | 0.000095%        | FAIL      |
| 1e-04     | 1             | 0.000095%        | FAIL      |
| 5e-04     | 1             | 0.000095%        | FAIL      |
| 1e-03     | 1             | 0.000095%        | FAIL      |

**Key Observation:** The outlier count remains **exactly 1 pixel** across all tolerances, indicating:
- NOT a statistical/numerical noise issue (would affect multiple pixels)
- NOT a systematic error (MSE is excellent at 2.41e-11)
- LIKELY a single-pixel bug (boundary condition, edge case, or coordinate singularity)

### Configuration Instrumentation

```
Detector config: beam_center_mm=(s=90.230167, f=88.574191), distance_mm=231.276455
Detector pixels: spixels=1024, fpixels=1024, pixel_size_mm=1.720000e-01
Crystal a*: [-0.02757067 -0.02869191 -0.01245197]
Crystal b*: [-0.00416187  0.02966329 -0.01563749]
Crystal c*: [ 0.02523375 -0.00187283 -0.01747896]
HKL grid shape: torch.Size([49, 57, 63]), dtype=torch.float32, device=cpu
HKL non-zero count: 69614
Image non-zero pixels: factory=1045385, adapter=1045385
```

**No obvious misconfiguration** — both paths produce identical non-zero pixel counts, indicating the issue is NOT in:
- Detector geometry mapping
- Crystal lattice orientation
- HKL grid construction
- Device/dtype handling

### Numerical Budget Evaluation

Per `input.md` hypothesis:
- **Forward pass numerical budget:** ≈1e-04 cumulative error (coordinate transforms + tricubic interpolation + pixel accumulation)
- **Observed max abs diff:** 5.03e-03 (50x beyond budget!)
- **Observed MSE:** 2.41e-11 (well within budget, 99.99% pixel parity)

**This confirms a localized bug, NOT a tolerance calibration issue.**

## Path C: Next Actions (Implementation Bug Investigation)

Per `input.md` Path C guidance:

### Immediate Next Steps

1. **Identify the outlier pixel location**
   - Run diff heatmap visualization to locate the (s, f) coordinate of the 5.03e-03 outlier
   - Check if outlier is at detector boundary (s=0, s=1023, f=0, f=1023)
   - Check if outlier is at beam center or special geometry position

2. **Full instrumentation comparison**
   - Add detailed tracing to both `create_unified_simulator` and `simulate_via_experiment_model`
   - Capture intermediate values:
     - A* matrices (should be identical)
     - Scattering vectors for outlier pixel
     - HKL lookups for outlier pixel
     - Reciprocal space coordinates
   - Document first divergence point

3. **Hypothesis ranking**
   - **H1 (LIKELY):** ExperimentModel boundary condition bug at detector edge
   - **H2 (POSSIBLE):** HKL grid interpolation edge case (tricubic boundary behavior)
   - **H3 (POSSIBLE):** Coordinate transform singularity (beam center or origin)
   - **H4 (UNLIKELY):** Random seed/numerical instability (MSE is too good)

4. **Escalation criteria**
   - If outlier is reproducible across multiple fixtures → file nanobrag_torch maintainer issue
   - If outlier is detector-edge specific → propose boundary guard in ExperimentModel
   - If outlier is beam-center specific → propose coordinate singularity handling

### Artifacts to Produce (Next Loop)

- `blocker_implementation_bug.md` — suspected bug location and evidence
- `diff_heatmap.png` — visual localization of outlier pixel
- `instrumentation_comparison.md` — factory vs adapter intermediate value comparison
- `outlier_trace.json` — detailed trace for the single outlier pixel

### No Regression Guards (Evidence-Only Loop)

Per `input.md`, **NO regression guards** should run in this loop (evidence-gathering only, no production changes).

## Decision Rationale

### Why NOT Path A (Tolerance Adjustment)?

Path A criteria: `max_abs_diff ≤ 1e-04`
**Observed:** `max_abs_diff = 5.03e-03` (50x beyond threshold)
**Verdict:** REJECTED — tolerance adjustment cannot fix a 5 milli-unit outlier

### Why NOT Path B (Marginal Parity)?

Path B criteria: `1e-04 < max_abs_diff ≤ 1e-03`
**Observed:** `max_abs_diff = 5.03e-03` (beyond marginal range)
**Verdict:** REJECTED — not marginal, clearly beyond budget

### Why Path C (Implementation Bug)?

Path C criteria: `max_abs_diff > 1e-03`
**Observed:** `max_abs_diff = 5.03e-03` ✓
**Supporting evidence:**
- Only 1 outlier pixel (not systematic)
- MSE excellent (not numerical drift)
- Outlier persists across all tolerances (not statistical)
- 50x beyond numerical budget (not rounding)

**Verdict:** ACCEPTED — this is a localized implementation bug

## Findings

**ARCH-FACTORY-003 (NEW):** ExperimentModel parity blocker — single-pixel outlier (5.03e-03) detected in Phase B3 tolerance sweep, indicating localized implementation bug (NOT tolerance calibration issue). Evidence: only 1 pixel out of 1M affected, MSE=2.41e-11 excellent, outlier persists across 1e-06 to 1e-03 tolerances. Hypothesis: ExperimentModel boundary condition bug or HKL grid interpolation edge case. Next: diff heatmap + full instrumentation comparison.

## References

- Tolerance sweep results: `tolerance_sweep.json`
- Test log: `pytest_experiment_parity_instrumented.log`
- Hypothesis source: `input.md` (Ralph's Phase B3 specification)
- Numerical budget analysis: `input.md` Context section (forward pass ≈1e-04 cumulative error)
