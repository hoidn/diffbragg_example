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

## Commentary

❌ **Contract violation detected**: The observed ratio deviates by 100.0% from expected.

The SQUARE lattice contract (docs/spec-db-core.md:60-140) requires weights ∝ (Na·Nb·Nc)².
This 0.000058x shortfall suggests a bug in the lattice weight computation.
