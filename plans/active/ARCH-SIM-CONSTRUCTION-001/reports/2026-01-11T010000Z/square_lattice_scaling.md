# Square Lattice Scaling Probe Results

## Configuration

- **N_cells**: (41, 29, 32)
- **Expected ratio**: 1,447,650,304.0
- **Oversample**: 1
- **Detector**: 1×1 pixels
- **Phi steps**: 1
- **Mosaic domains**: 1
- **Device**: cpu

## Intensities

- **Base** (N_cells=1,1,1): 7.024892e+00
- **Scaled** (N_cells=41,29,32): 1.016953e+10

## Scaling Analysis

- **Expected ratio** (Na·Nb·Nc)²: 1,447,650,304.0
- **Observed ratio**: 1,447,642,850.1
- **Relative error**: 0.00%
- **Deviation factor**: 0.999995x expected

## Phase C.31 Payload Analysis

### Base Case (N_cells=1,1,1)
- **F_cell**: 1.000000e+02
- **F_latt**: 1.000000e+00
- **intensity_pre_polar**: 7.024892e+06
- **min_abs_delta_h**: 3.051758e-05
- **min_abs_delta_k**: 0.000000e+00
- **min_abs_delta_l**: 0.000000e+00
- **steps_scalar**: 1.000000e+00

### Scaled Case (N_cells=41,29,32)
- **F_cell**: 1.000000e+02
- **F_latt**: 3.804790e+04
- **intensity_pre_polar**: 1.016953e+16
- **min_abs_delta_h**: 3.051758e-05
- **min_abs_delta_k**: 0.000000e+00
- **min_abs_delta_l**: 0.000000e+00
- **steps_scalar**: 1.000000e+00

### Traced Pixel HKL Tensor Stats (Phase C.35)

Per-subpixel HKL values captured via `_partiality_stats` for the single traced pixel:

| Axis | Min | Median | Max |
|------|-----|--------|-----|
| h | 200.000031 | 200.000031 | 200.000031 |
| k | 0.000000 | 0.000000 | 0.000000 |
| l | 0.000000 | 0.000000 | 0.000000 |
| h0 | 200 | 200 | 200 |
| k0 | 0 | 0 | 0 |
| l0 | 0 | 0 | 0 |

### HKL Projection Audit (Phase C.37)

Alternate HKL projection via dual-basis matrix solve (`torch.linalg.solve`) compared to production dot-product approach.

**Deltas**: production_HKL - dual_basis_HKL (signed offsets per subpixel)

| Axis | Min | Median | Max |
|------|-----|--------|-----|
| Δh | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 |
| Δk | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 |
| Δl | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 |

**Interpretation**: If the dual-basis solve produces HKL values that are closer to integers than the production dot-product approach, this suggests a bug in the HKL projection logic. If both approaches yield similar offsets from integers, the issue lies upstream (detector geometry or oversample grid construction).

### Derived Ratios

These ratios help bisect where the (Na·Nb·Nc)² scaling is lost:

- **F_latt_ratio**: 3.804790e+04
- **F_latt_ratio_expected**: 3.804800e+04
- **I_pre_polar_ratio**: 1.447643e+09
- **I_pre_polar_ratio_expected**: 1.447650e+09
- **base_I_pre_polar_over_F_total_sq**: 7.024892e+02
- **scaled_I_pre_polar_over_F_total_sq**: 7.024892e+02

## Phase C.34 Subpixel Coverage Analysis

This section quantifies how many subpixels hit the central sincg lobe (|Δ_{h,k,l}| < 1/N)
and what fraction of the total intensity they contribute.

- **Total subpixels sampled**: 1
- **Subpixels in central lobe**: 1 (100.00%)
- **Central lobe thresholds**:
  - |Δh| < 0.024390
  - |Δk| < 0.034483
  - |Δl| < 0.031250
- **Intensity share from central lobe**: 100.00%
- **Implied (Na·Nb·Nc)² ratio from coverage**: 1.447650e+09
  (Expected: 1,447,650,304.0)

**Diagnosis**: Central lobe coverage appears healthy.
The deficit must originate elsewhere (normalization, Lorentz, or polar ordering).

## Commentary

✅ The observed ratio is within 5% tolerance of the expected (Na·Nb·Nc)² scaling.
