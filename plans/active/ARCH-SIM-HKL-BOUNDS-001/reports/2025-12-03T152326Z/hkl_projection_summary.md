# HKL Projection Inspection (ARCH-SIM-HKL-BOUNDS-001 Phase B.1)

**Dataset**: refGeom small-detector smoke fixture

**Beam center pixel**: (fast=515, slow=525)

## Structure Factor Grid Bounds

- h ∈ [-24, 24]
- k ∈ [-28, 28]
- l ∈ [-31, 30]

## Per-Pixel HKL Projections

| Label | Pixel (slow, fast) | HKL (fractional) | HKL (rounded) | In Bounds? |
|-------|-------------------|------------------|---------------|------------|
| direct_beam     | ( 525,  515) | (   0.03,    0.03,    0.04) | (   0,    0,    0) | ✓ |
| plus_slow       | ( 589,  515) | (   0.03,    0.03,    0.04) | (   0,    0,    0) | ✓ |
| minus_slow      | ( 461,  515) | (   0.02,    0.03,    0.04) | (   0,    0,    0) | ✓ |
| plus_fast       | ( 525,  579) | (   0.02,    0.03,    0.04) | (   0,    0,    0) | ✓ |
| minus_fast      | ( 525,  451) | (   0.03,    0.03,    0.03) | (   0,    0,    0) | ✓ |

## Phase B.1 Observations

1. **Direct-beam pixel HKL**: The pixel at the computed beam center yields HKL=(0, 0, 0), which should be ≈(0,0,0) per crystallographic conventions (zero scattering vector for direct beam).

2. **Grid center vs direct beam**: The loaded structure-factor grid is centered at (0.0, 0.0, -0.5). The direct-beam HKL is offset by (+0, +0, +0) from (0,0,0).

3. **Systematic offset hypothesis**: If all test pixels are consistently shifted by the same amount relative to the grid bounds, this suggests a reciprocal-space alignment bug in the crystal orientation or structure-factor grid indexing conventions.

4. **Next steps**: Cross-reference these per-pixel projections against the HKL stats from DIAG-NANOBRAGG-OVERSAMPLE-001 to confirm the offset pattern. If the direct-beam offset matches the 0% coverage ranges, the fix likely involves correcting the crystal rotation or grid indexing.

**Artifacts**: plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T152326Z
**CLI**: `NANOBRAGG_DISABLE_COMPILE=1 python /home/ollie/Documents/diffbragg_example_2/diffbragg_example/plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/inspect_hkl_projection.py --detector-size small --out-dir plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T152326Z`
