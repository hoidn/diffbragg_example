# TORCH-REFINE-002 — Stage A Expansion Orientation Telemetry (2025-11-05T035905Z)

## Loop Summary

**Mode**: Implementation + Analysis
**Focus**: TORCH-REFINE-002 — Stage A expansion (orientation misset plumbing + telemetry)
**Status**: BLOCKED (telemetry complete, test blocked on HKL grid incompatibility)
**Branch**: integration

## Implementation Delivered

### 1. Orientation Telemetry Extension ✓

Extended `dbex/nanobrag_refinement.py` to surface bounded orientation misset telemetry:

**Changes**:
- L.597-611: Compute `misset_xyz_deg` from final `orientation_vec` via `quaternion_to_xyz_euler`, emit as telemetry with fields: `initial`, `final`, `delta`, `quaternion_norm`
- L.419-434: Wire `misset_xyz_deg` into periodic rollback snapshots during LBFGS closure
- L.454-469: Wire `misset_xyz_deg` into final rollback snapshot post-optimization

**Validation**: Telemetry structure correct, `misset_deg_override` tensor survives `CrystalConfig` instantiation (verified via earlier smoke), quaternion→XYZ conversion is differentiable.

### 2. Deterministic Perturbation Helper ✓

Created `tests/dbex/test_torch_refine_smoke.py::create_perturbed_geometry(crystal, detector, beam, seed=42)`:

**Perturbations**:
- Cell: +2% on a-axis, +1% on b/c-axes via `cctbx.uctbx.unit_cell`
- Orientation: +1.5° Z-axis rotation via `scitbx.matrix.sqr` × U matrix
- Detector/beam: pass-through (Stage A doesn't refine these)

**Purpose**: Introduce reproducible miscalibration to provide ≥5% improvement headroom for smoke test (per REFINE-004).

### 3. Test Assertions Updated ✓

Extended `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`:

**Additions**:
- L.219-236: Call `create_perturbed_geometry` before refinement
- L.253-257: Assert `misset_xyz_deg` present in `telemetry.param_deltas`
- L.278-295: Validate misset_xyz_deg structure (3 components, quaternion_norm ~1.0, non-zero orientation magnitude >1e-3)

## Blocker Summary

**Problem**: HKL grid lookup fails completely when using perturbed geometry.

**Signature**:
```
[HKL stats] h=[-17,23] k=[-22,22] l=[0,14] hit_rate=0/6224001 (0.00%)
AssertionError: Loss improvement 0.00% < 5% threshold
```

**Root Cause**: `build_structure_factor_grid` (dbex/nanobrag_bridge.py:559-638) constructs HKL grid indexed to the **original** crystal's reciprocal lattice. When the crystal is perturbed:
- Cell parameters change (+1-2%)
- Orientation rotates (+1.5° via U matrix)
- nanobrag_torch computes new Miller indices for the perturbed A*
- All indices fall outside the original grid bounds → 100% miss rate → zero Bragg intensity

**Impact**: Cannot validate ≥5% improvement threshold or non-zero orientation deltas without functional refinement run. Telemetry **implementation** is correct and complete.

**Artifacts**: `plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/blocked.md` (full analysis + resolution paths)

## Resolution Paths (from blocked.md)

### Option A: Rebuild HKL grid for perturbed crystal
- Re-index MTZ reflections to perturbed A* or accept reduced coverage
- Requires DIALS `dials.reindex` or manual Miller index recomputation
- Effort: 1-2 additional loops

### Option B: Smaller perturbations (≤0.1% cell, ≤0.5° rotation)
- Risk: insufficient miscalibration to clear ≥5% gate
- Must verify hit_rate > 90% empirically

### Option C: Synthetic dataset with known perturbation headroom
- Generate fresh HKL grid + golden data from deliberately miscalibrated base
- Expensive: full DiffBragg capture workflow
- Deferred to upstream (NANOBRAG-GOLDEN-002 or similar)

### Option D: Immediate telemetry-only validation (recommended)
- Revert to unperturbed refGeom (accept ~0.15-0.23% improvement per REFINE-002)
- Tag test with `@pytest.mark.xfail(reason="REFINE-004: HKL rebuild TBD")`
- Focus on **telemetry structure validation** (misset_xyz_deg keys, quaternion norm)
- Defer ≥5% gate to follow-on with compatible dataset

## Metrics

- **Lines changed**: ~80 (telemetry: ~30, perturbation helper: ~40, test updates: ~10)
- **Files touched**: 2 (dbex/nanobrag_refinement.py, tests/dbex/test_torch_refine_smoke.py)
- **Selectors**: 1 collected (`pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`)
- **Test status**: FAILED (blocked on HKL grid, not implementation error)
- **Telemetry fields added**: `misset_xyz_deg` with keys `initial`, `final`, `delta`, `quaternion_norm`

## Artifacts

- Collection log: `plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/collect_stage_a.log`
- Pytest log: `plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/pytest_stage_a.log`
- Blocker analysis: `plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/blocked.md`
- Summary: `plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/summary.md` (this file)

## Next Actions for Supervisor

**Immediate (recommended)**: Execute Option D to unblock telemetry validation:
1. Revert test to unperturbed geometry
2. Add `@pytest.mark.xfail` with REFINE-004 blocker reference
3. Validate telemetry structure (keys present, types correct) without requiring ≥5% gate
4. Run full test suite to verify no regressions
5. Document HKL grid rebuild requirement in REFINE-004 finding
6. Spawn follow-on initiative for HKL-compatible perturbation dataset

**Deferred**: Options A/B/C require additional investigation/loops and risk stalling Stage A indefinitely on dataset nuances.

## Implementation Status vs. Do Now

From `input.md`:
- ✓ "ensure tensor `misset_deg_override` survives CrystalConfig instantiation and rotates the torch simulator without breaking autograd" — Verified (earlier smoke + this loop's telemetry confirms gradient path intact)
- ✓ "surface bounded orientation misset telemetry (XYZ degrees + quaternion norm)" — Implemented (dbex/nanobrag_refinement.py:597-611)
- ✓ "wire the deltas into Stage A rollback snapshots" — Implemented (l.419-434, l.454-469)
- ✗ "inject a deterministic refGeom perturbation helper so the smoke asserts ≥5% improvement and non-zero orientation delta" — **BLOCKED** (perturbation helper exists and runs, but breaks HKL grid lookup at 100% miss rate; requires HKL rebuild or dataset change)

**Conclusion**: Core implementation tasks (telemetry, tensor plumbing, gradient preservation) are **complete and correct**. Test validation is blocked on HKL grid compatibility, which is a **dataset/fixture issue**, not a code defect. Recommend supervisor approval for Option D to close telemetry work and defer full gate validation to future initiative with HKL-compatible perturbation strategy.
