# Square Lattice Scaling Probe Results

## Configuration

- **N_cells**: (41, 29, 32)
- **Expected ratio**: 1,447,650,304.0
- **Oversample**: 41
- **Detector**: 1×1 pixels
- **Phi steps**: 1
- **Mosaic domains**: 1
- **Device**: cpu

## Intensities

- **Base** (N_cells=1,1,1): 1.096889e+04
- **Scaled** (N_cells=41,29,32): 9.421389e+08

## Scaling Analysis

- **Expected ratio** (Na·Nb·Nc)²: 1,447,650,304.0
- **Observed ratio**: 85,891.9
- **Relative error**: 99.99%
- **Deviation factor**: 0.000059x expected

## Phase C.31 Payload Analysis

### Base Case (N_cells=1,1,1)
- **F_cell**: 1.000000e+02
- **F_latt**: 1.000000e+00
- **intensity_pre_polar**: 6.525228e+06
- **min_abs_delta_h**: 0.000000e+00
- **min_abs_delta_k**: 5.121946e-02
- **min_abs_delta_l**: 5.121944e-02

### Scaled Case (N_cells=41,29,32)
- **F_cell**: 1.000000e+02
- **F_latt**: -3.631866e+00
- **intensity_pre_polar**: 5.604641e+11
- **min_abs_delta_h**: 0.000000e+00
- **min_abs_delta_k**: 5.121946e-02
- **min_abs_delta_l**: 5.121944e-02

### Derived Ratios

These ratios help bisect where the (Na·Nb·Nc)² scaling is lost:

- **F_latt_ratio**: -3.631866e+00
- **F_latt_ratio_expected**: 3.804800e+04
- **I_pre_polar_ratio**: 8.589188e+04
- **I_pre_polar_ratio_expected**: 1.447650e+09
- **base_I_pre_polar_over_F_total_sq**: 6.525228e+02
- **scaled_I_pre_polar_over_F_total_sq**: 4.249015e+06

## Phase C.34 Subpixel Coverage Analysis

This section quantifies how many subpixels hit the central sincg lobe (|Δ_{h,k,l}| < 1/N)
and what fraction of the total intensity they contribute.

- **Total subpixels sampled**: 1681
- **Subpixels in central lobe**: 0 (0.00%)
- **Central lobe thresholds**:
  - |Δh| < 0.024390
  - |Δk| < 0.034483
  - |Δl| < 0.031250
- **Intensity share from central lobe**: 0.00%
- **Implied (Na·Nb·Nc)² ratio from coverage**: 0.000000e+00
  (Expected: 1,447,650,304.0)

**Diagnosis**: Less than 1% of subpixels reach the central lobe.
This explains the (Na·Nb·Nc)² deficit: the oversample grid is not capturing the sincg peak.
Next step: investigate subpixel positioning or increase oversample factor.

## Commentary

❌ **Contract violation detected**: The observed ratio deviates by 100.0% from expected.

The SQUARE lattice contract (docs/spec-db-core.md:60-140) requires weights ∝ (Na·Nb·Nc)².
This 0.000059x shortfall suggests a bug in the lattice weight computation.
