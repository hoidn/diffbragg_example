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

- **Base** (N_cells=1,1,1): 1.187207e+03
- **Scaled** (N_cells=41,29,32): 1.614788e+11

## Scaling Analysis

- **Expected ratio** (Na·Nb·Nc)²: 1,447,650,304.0
- **Observed ratio**: 136,015,748.6
- **Relative error**: 90.60%
- **Deviation factor**: 0.093956x expected

## Phase C.31 Payload Analysis

### Base Case (N_cells=1,1,1)
- **F_cell**: 1.000000e+02
- **F_latt**: 1.000000e+00
- **intensity_pre_polar**: 7.024892e+06
- **min_abs_delta_h**: 1.525879e-05
- **min_abs_delta_k**: 0.000000e+00
- **min_abs_delta_l**: 0.000000e+00
- **trace_subpixel_F_total_sq_sum**: 1.187207e+09
- **trace_subpixel_omega_last**: 9.999999e-07
- **trace_normalized_intensity**: 1.187207e+03
- **steps_scalar**: 1.000000e+00
- **omega_applied_post_sum**: 1.000000e+00
- **square_used_riemann_sum**: 1.000000e+00

### Scaled Case (N_cells=41,29,32)
- **F_cell**: 1.000000e+02
- **F_latt**: 4.206509e+03
- **intensity_pre_polar**: 9.554960e+14
- **min_abs_delta_h**: 1.525879e-05
- **min_abs_delta_k**: 0.000000e+00
- **min_abs_delta_l**: 0.000000e+00
- **trace_subpixel_F_total_sq_sum**: 1.614788e+17
- **trace_subpixel_omega_last**: 9.999999e-07
- **trace_normalized_intensity**: 1.614788e+11
- **steps_scalar**: 1.000000e+00
- **omega_applied_post_sum**: 1.000000e+00
- **square_used_riemann_sum**: 1.000000e+00

### Subpixel Offset Stats (Phase C.36)

Raw detector-plane slow/fast subpixel offsets (fractional pixel units) for the traced pixel:

| Axis | Min | Median | Max | Straddles Zero |
|------|-----|--------|-----|----------------|
| Slow | -0.461538 | 0.000000 | 0.461538 | ✓ |
| Fast | -0.461538 | 0.000000 | 0.461538 | ✓ |

**Interpretation**: For oversample=13, expected range is -6/13 = -0.461538 to +6/13 = +0.461538.
Both axes should straddle zero to ensure the sincg lobe center (Δ=0) is sampled.

### Traced Pixel HKL Tensor Stats (Phase C.35)

Per-subpixel HKL values captured via `_partiality_stats` for the single traced pixel:

| Axis | Min | Median | Max |
|------|-----|--------|-----|
| h | 200.000015 | 200.000031 | 200.000031 |
| k | -0.046154 | 0.000000 | 0.046154 |
| l | -0.046154 | 0.000000 | 0.046154 |
| h0 | 200 | 200 | 200 |
| k0 | -0 | 0 | -0 |
| l0 | 0 | 0 | 0 |

### HKL Projection Audit (Phase C.37)

Alternate HKL projection via dual-basis matrix solve (`torch.linalg.solve`) compared to production dot-product approach.

**Deltas**: production_HKL - dual_basis_HKL (signed offsets per subpixel)

| Axis | Min | Median | Max |
|------|-----|--------|-----|
| Δh | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 |
| Δk | -7.450581e-09 | 0.000000e+00 | 7.450581e-09 |
| Δl | -3.725290e-09 | 0.000000e+00 | 3.725290e-09 |

**Interpretation**: If the dual-basis solve produces HKL values that are closer to integers than the production dot-product approach, this suggests a bug in the HKL projection logic. If both approaches yield similar offsets from integers, the issue lies upstream (detector geometry or oversample grid construction).

### Oversample Accumulation Breakdown (Phase C.38/C.39)

Instrumentation to validate omega compensation fix for SQUARE lattices (C.39).

| Metric | Value |
|--------|-------|
| Raw subpixel sum (before omega) | 1.614788e+17 |
| Omega (last-value semantics) | 9.999999e-07 |
| **Omega application mode** | **✓ Applied once after sum (SQUARE integral)** |
| Normalized intensity (after omega) | 1.614788e+11 |
| Steps scalar (normalization divisor) | 1.000000e+00 |
| **Normalized / Raw sum ratio** | **0.000001** |

**Expected after C.39 fix**: For SQUARE lattices, omega should be applied once after summing subpixels (integral semantics). The Normalized/Raw ratio should be ≈1.0 (omega cancels out when comparing base vs scaled runs with same geometry).

### Derived Ratios

These ratios help bisect where the (Na·Nb·Nc)² scaling is lost:

- **F_latt_ratio**: 4.206509e+03
- **F_latt_ratio_expected**: 3.804800e+04
- **I_pre_polar_ratio**: 1.360158e+08
- **I_pre_polar_ratio_expected**: 1.447650e+09
- **base_I_pre_polar_over_F_total_sq**: 7.024892e+02
- **scaled_I_pre_polar_over_F_total_sq**: 5.399893e+03

## Phase C.34 Subpixel Coverage Analysis

This section quantifies how many subpixels hit the central sincg lobe (|Δ_{h,k,l}| < 1/N)
and what fraction of the total intensity they contribute.

- **Total subpixels sampled**: 169
- **Subpixels in central lobe**: 81 (47.93%)
- **Central lobe thresholds**:
  - |Δh| < 0.024390
  - |Δk| < 0.034483
  - |Δl| < 0.031250
- **Intensity share from central lobe**: 93.53%
- **Implied (Na·Nb·Nc)² ratio from coverage**: 1.354007e+09
  (Expected: 1,447,650,304.0)

**Diagnosis**: Central lobe coverage appears healthy.
The deficit must originate elsewhere (normalization, Lorentz, or polar ordering).

## Commentary

❌ **Contract violation detected**: The observed ratio deviates by 90.6% from expected.

The SQUARE lattice contract (docs/spec-db-core.md:60-140) requires weights ∝ (Na·Nb·Nc)².
This 0.093956x shortfall suggests a bug in the lattice weight computation.
