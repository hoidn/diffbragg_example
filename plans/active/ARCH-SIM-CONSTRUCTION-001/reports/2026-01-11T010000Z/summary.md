# Phase C.38 — Oversample accumulation instrumentation (2026-01-11T010000Z)

## Implementation Summary

Instrumented the oversample accumulation path in `nanobrag_torch.simulator.Simulator.run` (lines 1340-1382) to capture:
1. Raw per-subpixel sum (`trace_subpixel_F_total_sq_sum`) before omega application
2. Omega scalar applied (`trace_subpixel_omega_last` for last-value semantics or `trace_subpixel_omega_mean` for per-subpixel mode)
3. Final normalized intensity (`trace_normalized_intensity`) after omega but before division by steps

Extended `probe_square_lattice_scaling.py` (lines 286-302 payload extraction, 451-473 console output, 838-865 markdown report) to ingest these stats and compute the ratio between raw sum and normalized intensity.

## Key Findings

### Oversample=13 (1×1 detector)
- Raw subpixel sum (before omega): **1.614788e+17**
- Omega (last-value semantics): **9.999992e-07**
- Normalized intensity (after omega): **1.614787e+11**
- Steps scalar: **1.0**
- **Normalized / Raw sum ratio: 0.000001 (1e-6)**

This proves that omega is correctly applied (raw sum × omega ≈ normalized intensity), but the final output is **missing a compensating factor** that should restore the integral semantics for SQUARE lattices.

### Oversample=1 (1×1 detector)
- **Observed ratio: 1,447,642,850.1 vs expected 1,447,650,304.0 (0.00% error)**
- Confirms the simulator obeys `(Na·Nb·Nc)²` when no subpixel averaging occurs

### Architecture Test (10×10 detector, oversample=13)
- **Expected ratio: 1,447,650,304.0**
- **Observed ratio: 590,383,479.7**
- **Relative error: 59.22%** (tolerance: 1%)
- Test FAILED

## Root Cause Localization

The instrumentation definitively locates the ≈0.094× (for 1×1 detector) to 0.41× (for 10×10 detector) deficit at the **omega application stage** in the oversample>1 branch:

1. The raw per-subpixel sum before omega is correct (matches expected physics)
2. Omega is correctly computed and applied (1e-6 for 100mm distance, 0.1mm pixel)
3. But for SQUARE lattices, the code should **not apply omega per-subpixel** OR should compensate by multiplying back by `oversample²` after summing

The current code path (simulator.py:1333-1365) applies omega via **last-value semantics** when `oversample_omega=False` (line 1362), meaning:
```python
accumulated_intensity = torch.sum(intensity_all, dim=2)  # sum raw subpixels
accumulated_intensity = accumulated_intensity * last_omega  # apply omega ONCE
```

However, `intensity_all` at line 1334 is cloned from `subpixel_physics_intensity_all`, which has **NOT** had omega applied yet. So the omega factor of 1e-6 reduces the accumulated sum by that factor, but there's no subsequent correction for SQUARE lattices.

## Next Action

The fix requires one of:
1. **Option A (preferred)**: Skip omega application entirely in the oversample>1 branch when `shape=SQUARE` and apply it only once at the end (matching the oversample=1 path)
2. **Option B**: Apply omega per-subpixel but compensate by multiplying by `oversample²` for SQUARE lattices after the sum
3. **Option C**: Move the omega application outside the subpixel loop so it's applied once per pixel regardless of oversample

Recommend Option A to maintain symmetry with the oversample=1 path and avoid introducing new SQUARE-specific branches.

## Artifacts
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/square_lattice_probe_os13.log`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/square_lattice_probe_os1.log`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/square_lattice_scaling.json`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/square_lattice_scaling.md`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/pytest_partiality.log`

### Turn Summary
Shipped C.38 instrumentation capturing raw subpixel sum, omega scalar, and normalized intensity for oversample accumulation path. Probe results prove omega application reduces intensity by 1e-6 (correct solid angle factor) but SQUARE lattices lack compensating restoration of integral semantics. Test suite still fails (59% error on 10×10 detector) awaiting production fix. Next: implement Option A to skip per-subpixel omega for SQUARE shape.

Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/ (square_lattice_probe_os13.log, square_lattice_scaling.json/md, pytest_partiality.log)
