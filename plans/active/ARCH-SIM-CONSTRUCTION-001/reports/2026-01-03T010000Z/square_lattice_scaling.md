# Square Lattice Scaling Probe Results

## Configuration

- **N_cells**: (41, 29, 32)
- **Expected ratio**: 1,447,650,304.0
- **Oversample**: 13
- **Detector**: 1×1 pixels
- **Phi steps**: 1
- **Mosaic domains**: 1
- **Device**: cpu

## Intensities

- **Base** (N_cells=1,1,1): 6.524461e+00
- **Scaled** (N_cells=41,29,32): 5.520526e+05

## Scaling Analysis

- **Expected ratio** (Na·Nb·Nc)²: 1,447,650,304.0
- **Observed ratio**: 84,612.8
- **Relative error**: 99.99%
- **Deviation factor**: 0.000058x expected

## Phase C.31 Payload Analysis

### Base Case (N_cells=1,1,1)
- **F_cell**: 1.000000e+02
- **F_latt**: 1.000000e+00
- **F_total_squared_pre_lorentz**: 1.000000e+04
- **intensity_pre_polar**: 6.524473e+06

### Scaled Case (N_cells=41,29,32)
- **F_cell**: 1.000000e+02
- **F_latt**: -3.807035e+00
- **F_total_squared_pre_lorentz**: 8.041414e+08
- **intensity_pre_polar**: 5.520534e+11

### Derived Ratios

These ratios help bisect where the (Na·Nb·Nc)² scaling is lost:

- **F_latt_ratio**: -3.807035e+00
- **F_latt_ratio_expected**: 3.804800e+04
- **F_total_sq_ratio**: 8.041414e+04
- **F_total_sq_ratio_expected**: 1.447650e+09
- **I_pre_polar_ratio**: 8.461272e+04
- **I_pre_polar_ratio_expected**: 1.447650e+09
- **base_I_pre_polar_over_F_total_sq**: 6.524473e+02
- **scaled_I_pre_polar_over_F_total_sq**: 3.808968e+06

## Commentary

❌ **Contract violation detected**: The observed ratio deviates by 100.0% from expected.

The SQUARE lattice contract (docs/spec-db-core.md:60-140) requires weights ∝ (Na·Nb·Nc)².
This 0.000058x shortfall suggests a bug in the lattice weight computation.
