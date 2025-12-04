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
- **Scaled** (N_cells=41,29,32): 5.520524e+05

## Scaling Analysis

- **Expected ratio** (Na·Nb·Nc)²: 1,447,650,304.0
- **Observed ratio**: 84,612.7
- **Relative error**: 99.99%
- **Deviation factor**: 0.000058x expected

## Phase C.31 Payload Analysis

### Base Case (N_cells=1,1,1)
- **F_cell**: 1.000000e+02
- **F_latt**: 1.000000e+00
- **F_total_squared_pre_lorentz**: 1.000000e+04
- **intensity_pre_polar**: 6.524473e+06
- **min_abs_delta_h**: 0.000000e+00
- **min_abs_delta_k**: 5.384610e-02
- **min_abs_delta_l**: 5.384608e-02

### Scaled Case (N_cells=41,29,32)
- **F_cell**: 1.000000e+02
- **F_latt**: -3.807036e+00
- **F_total_squared_pre_lorentz**: 8.041411e+08
- **intensity_pre_polar**: 5.520532e+11
- **min_abs_delta_h**: 0.000000e+00
- **min_abs_delta_k**: 5.384610e-02
- **min_abs_delta_l**: 5.384608e-02

### Derived Ratios

These ratios help bisect where the (Na·Nb·Nc)² scaling is lost:

- **F_latt_ratio**: -3.807036e+00
- **F_latt_ratio_expected**: 3.804800e+04
- **F_total_sq_ratio**: 8.041411e+04
- **F_total_sq_ratio_expected**: 1.447650e+09
- **I_pre_polar_ratio**: 8.461268e+04
- **I_pre_polar_ratio_expected**: 1.447650e+09
- **base_I_pre_polar_over_F_total_sq**: 6.524473e+02
- **scaled_I_pre_polar_over_F_total_sq**: 3.808964e+06

## Phase C.32 Reference Analysis

High-precision NumPy float64 reference evaluator for `sin(NπΔ)/sin(πΔ)` compared against production `sincg` kernel.

### Per-Axis Error Statistics

| Axis | N | Production Median | Reference Median | Median Abs Err | Max Abs Err | Median Rel Err | Max Rel Err |
|------|---|-------------------|------------------|----------------|-------------|----------------|-------------|
| h | 41 | 4.099958e+01 | 4.099958e+01 | 9.121738e-07 | 1.778984e-06 | 0.0000% | 0.0000% |
| k | 29 | 1.119637e-01 | 1.119637e-01 | 3.100757e-08 | 2.359224e-07 | 0.0000% | 0.0000% |
| l | 32 | 5.053360e-01 | 5.053360e-01 | 3.815313e-08 | 1.826365e-07 | 0.0000% | 0.0000% |

### Worst-Case Samples (Max Absolute Error)

| Axis | Δ | Production | Reference | Abs Error | Rel Error |
|------|---|------------|-----------|-----------|------------|
| h | -0.000153 | 4.099736e+01 | 4.099736e+01 | 1.778984e-06 | 0.0000% |
| k | 0.053846 | -5.829110e+00 | -5.829110e+00 | 2.359224e-07 | 0.0000% |
| l | -0.053846 | -4.539858e+00 | -4.539859e+00 | 1.826365e-07 | 0.0000% |

### Near-Zero Δ Samples

| Axis | Δ | Production | Reference | Abs Error | Rel Error |
|------|---|------------|-----------|-----------|------------|
| h | 0.000000 | 4.100000e+01 | 4.100000e+01 | 0.000000e+00 | 0.0000% |

### Compounded F_latt Analysis

- **Reference median product** (F_latt_a × F_latt_b × F_latt_c): 2.319726e+00
- **Production F_latt**: -3.807036e+00
- **Expected** (Na·Nb·Nc): 3.804800e+04
- **Reference vs expected ratio**: 0.000061x
- **Production vs expected ratio**: -0.000100x
- **Production vs reference ratio**: -1.641158x

**Predicted intensity ratio using reference F_latt**: 5.381129e+00
(Expected (Na·Nb·Nc)² = 1,447,650,304.0)

## Commentary

❌ **Contract violation detected**: The observed ratio deviates by 100.0% from expected.

The SQUARE lattice contract (docs/spec-db-core.md:60-140) requires weights ∝ (Na·Nb·Nc)².
This 0.000058x shortfall suggests a bug in the lattice weight computation.
