# TORCH-REFINE-002 Blocker Summary

**Timestamp**: 2025-11-05T04:09Z
**Focus**: Stage A expansion — full crystal and orientation
**Status**: BLOCKED on HKL grid compatibility with perturbed geometry

## Problem Signature

When applying deterministic refGeom perturbation (cell stretch +1-2% + Z-axis rotation +1.5°), the **HKL grid lookup fails completely**:

```
[HKL stats] h=[-17,23] k=[-22,22] l=[0,14] hit_rate=0/6224001 (0.00%)
```

All simulator runs return zero Bragg intensity because computed Miller indices fall outside the HKL grid built from the **unperturbed** crystal.

## Root Cause

The `build_structure_factor_grid` helper (db ex/nanobrag_bridge.py:559-638) constructs the HKL grid using Miller indices from `refgeom_dataload.F.indices()`, which are indexed to the **original** crystal's reciprocal lattice.

When we perturb the crystal:
- Cell parameters change (a: +2%, b/c: +1%)
- Orientation rotates (+1.5° around Z via U matrix)
- **BUT**: The HKL grid remains tied to the original A* basis

The simulator computes new Miller indices for the perturbed crystal, which do not align with the original grid bounds, causing 100% miss rate.

## Attempted Mitigation (test_torch_refine_smoke.py:63-138)

Created `create_perturbed_geometry` helper applying:
- Cell perturbation: perturbed_uc via `uctbx.unit_cell(...)`
- Orientation perturbation: R_z(1.5°) × U via `scitbx.matrix.sqr`

The helper successfully creates a perturbed crystal, but the HKL grid remains incompatible.

## Resolution Paths

### Option A: Rebuild HKL grid for perturbed crystal (recommended for test robustness)
- After perturbing crystal, recompute structure factors from the same MTZ **but with the perturbed reciprocal lattice**
- This requires re-indexing MTZ reflections to the perturbed A* or accepting reduced coverage
- May need DIALS `dials.reindex` or manual Miller index recomputation

### Option B: Use smaller perturbations (≤0.1% cell, ≤0.5° rotation)
- Smaller perturbations might keep most Miller indices within the original HKL grid bounds
- Risk: insufficient miscalibration to clear the ≥5% improvement gate
- Empirical: must verify hit_rate > 90% after perturbation

### Option C: Synthetic dataset with known perturbation headroom
- Generate a fresh HKL grid + golden data pair from a "deliberately miscalibrated" base geometry
- Expensive: requires full DiffBragg capture workflow
- Deferred to upstream (NANOBRAG-GOLDEN-002 or similar)

### Option D (immediate workaround): Skip perturbation for now, accept lower gate
- Use unperturbed refGeom; accept ~0.15-0.23% improvement (per REFINE-002)
- Tag test with `@pytest.mark.xfail(reason="REFINE-004: dataset too calibrated, HKL rebuild TBD")`
- Focus this loop on **telemetry validation only**, defer ≥5% gate to follow-on with compatible dataset

## Implementation Status

### Completed (this loop):
- ✓ Telemetry: `misset_xyz_deg` with XYZ degrees, quaternion_norm
- ✓ Snapshots: `misset_xyz_deg` wired into `best_params_snapshot`
- ✓ Test assertions: orientation magnitude check (l.291-295)
- ✓ Perturbation helper: code exists, compiles, runs (but breaks HKL mapping)

### Blocked:
- ✗ ≥5% improvement threshold: cannot demonstrate with current perturbation + HKL grid mismatch
- ✗ Non-zero orientation delta telemetry validation: requires functional refinement run

## Recommendation for Next Loop

Execute **Option D** immediately to unblock telemetry validation:
1. Revert test to use unperturbed geometry (remove `create_perturbed_geometry` call)
2. Add `@pytest.mark.xfail` with blocker reference
3. Update assertions to validate **telemetry structure** (misset_xyz_deg keys present, quaternion_norm ~1.0) without requiring ≥5% gate
4. Run targeted pytest + full suite to verify no regressions
5. Document HKL grid rebuild requirement in `docs/fix_plan.md` REFINE-004 and spawn follow-on initiative

## Artifacts

- Blocker analysis: `plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/blocked.md` (this file)
- Failing pytest log: `plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/pytest_stage_a.log`
- Collection log: `plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/collect_stage_a.log`

## Dependencies for Unblock

- dxtbx/DIALS: Miller index reindexing API or workflow
- OR: Refined understanding of nanobrag_torch HKL interpolation tolerance (current: hard bounds check fails at 100%)

## Next Actions (for supervisor)

Decide between:
- A: Authorize HKL rebuild implementation (1-2 additional loops, blocking Stage A)
- D: Accept xfail + telemetry-only validation for this loop, defer full gate to future dataset

**Recommendation**: Option D (immediate telemetry closure) to avoid stalling Stage A indefinitely on dataset nuances.
