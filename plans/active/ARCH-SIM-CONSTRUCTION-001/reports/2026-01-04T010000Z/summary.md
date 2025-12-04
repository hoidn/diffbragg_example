# Phase C.32 Summary: sincg Reference Comparison

**Loop**: 2026-01-04T010000Z
**Focus**: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
**ActionType**: parity_localization
**DecisionStatus**: localized
**Finding**: SIM-CONSTR-PARTIALITY-001

## Objective

Compare nanobrag_torch's `sincg` kernel against a high-precision NumPy float64 reference evaluator to determine whether the observed (Na·Nb·Nc)² deficit (0.000058× ratio) originates inside the lattice kernel or in downstream aggregation.

## Implementation

Extended `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` with:

1. **High-precision reference evaluator** (`sincg_reference`):
   - NumPy float64 implementation of `sin(NπΔ)/sin(πΔ)`
   - Handles special cases: Δ≈0 returns N, Δ≈integer returns N·(-1)^(n(N-1))
   - Epsilon threshold: 1e-12 for float64 precision

2. **Per-axis error statistics**:
   - Captured delta_h/k/l and F_latt_a/b/c from partiality_stats
   - Computed absolute and relative errors for all samples
   - Recorded max/median errors and worst-case Δ locations
   - Identified near-zero Δ samples for verification

3. **Compounded F_latt analysis**:
   - Compared production F_latt product against reference median product
   - Computed ratios vs expected (Na·Nb·Nc)
   - Estimated expected intensity using reference values

## Key Findings

### 1. sincg Kernel is Correct

**Per-axis error statistics** (from `square_lattice_scaling.md:56-62`):

| Axis | N | Production Median | Reference Median | Median Abs Err | Max Abs Err | Median Rel Err | Max Rel Err |
|------|---|-------------------|------------------|----------------|-------------|----------------|-------------|
| h | 41 | 4.099958e+01 | 4.099958e+01 | 9.121738e-07 | 1.778984e-06 | 0.0000% | 0.0000% |
| k | 29 | 1.119637e-01 | 1.119637e-01 | 3.234918e-08 | 2.359224e-07 | 0.0000% | 0.0000% |
| l | 32 | 5.053360e-01 | 5.053360e-01 | 4.058422e-08 | 1.759031e-07 | 0.0000% | 0.0000% |

**Conclusion**: The production `sincg` implementation in `nanobrag_torch/utils/physics.py:33-111` matches the analytic reference to within **<1e-6 absolute error** and **<0.0001% relative error** across all axes. The kernel itself is not the source of the deficit.

### 2. Downstream Aggregation is Broken

**Compounded F_latt** (from `square_lattice_scaling.md:80-85`):

- **Reference median product** (F_latt_a × F_latt_b × F_latt_c): **2.319726e+00**
- **Production F_latt**: **-3.807035e+00** (WRONG SIGN + WRONG MAGNITUDE)
- **Expected** (Na·Nb·Nc): **3.804800e+04**
- **Reference vs expected ratio**: **0.000061×** (4 orders of magnitude too small)
- **Production vs reference ratio**: **-1.641157×** (wrong sign, inconsistent magnitude)

**Critical observation**:
- Per-axis `F_latt_a/b/c` values are correct individually (match reference)
- The **product F_latt = F_latt_a × F_latt_b × F_latt_c** is completely wrong
- The trace shows `F_latt = 38048` in the simulator (TRACE_PY line), but the extracted mean is **-3.807035**
- This suggests the **averaging or extraction logic** in the probe is capturing the wrong tensor slice or applying incorrect reduction

### 3. Suspected Root Cause

The issue is likely in **how F_latt is computed or averaged** during multi-sample runs:
- The trace for a single (phi=0, mosaic=0) sample shows `F_latt = 38048` ✓ (correct)
- But the partiality_stats extraction yields `F_latt mean = -3.807` ✗ (wrong)

This discrepancy suggests:
1. **Either**: The `_partiality_stats['f_latt']` capture in `simulator.py` is recording an intermediate value instead of the final product
2. **Or**: The probe's averaging (`pstats['f_latt'].mean()`) is collapsing across the wrong dimension

## Predicted Intensity Using Reference

If we use the **reference F_latt = 2.32** instead of production:
- **Predicted intensity ratio**: **5.381129e+00** (base: 6.52, scaled: ~35.1)
- **Expected ratio**: **(Na·Nb·Nc)² = 1,447,650,304**

The reference product is still 4 orders of magnitude too small (0.000061×), which means:
- **Both** production and reference suffer from the same ~10^4× deficit in the F_latt **product**
- But **per-axis** sincg values are correct

## Localized Divergence Point

**First divergence**: Between per-axis `F_latt_a/b/c` (correct) and the compounded `F_latt` product (wrong).

**Source trace anchors**:
- `nanobrag_torch/simulator.py:288-458` — SQUARE branch compute_physics_for_position
- `nanobrag_torch/utils/physics.py:33-111` — sincg kernel (validated correct)
- **Missing anchor**: Where `F_latt = F_latt_a * F_latt_b * F_latt_c` is computed/stored

## Next Step (Phase C.33)

**Escalate to `implementation_ready`** with concrete target:
1. **Locate** the line where `F_latt = F_latt_a * F_latt_b * F_latt_c` is computed in the SQUARE branch
2. **Verify** the multiplication is correct and not overwriting intermediate values
3. **Fix** the product computation or the partiality_stats capture logic
4. **Alternative hypothesis**: If the trace value (38048) is correct but the test still fails, the issue is in how F_latt is **aggregated across phi/mosaic samples** (averaging vs summing)

## Artifacts

- `square_lattice_scaling.json` — Full numeric results with reference analysis
- `square_lattice_scaling.md` — Per-axis error tables, worst-case samples, compounded analysis
- `square_lattice_probe.log` — Console trace showing F_latt=38048 in single-sample case
- `pytest_partiality.log` — Enforcement test failure (99.75% error, observed ratio ~3.5M vs expected ~1.4B)

## Status

**Decision**: The (Na·Nb·Nc)² deficit does **NOT** originate inside the `sincg` kernel. The kernel is correct to within numerical precision. The bug is in the **downstream aggregation** where `F_latt_a/b/c` are multiplied together OR in how the multi-sample average is computed.

**Recommendation**: Promote to Phase C.33 `implementation_ready` with ActionType=bugfix targeting the F_latt product computation in `simulator.py` SQUARE branch.
