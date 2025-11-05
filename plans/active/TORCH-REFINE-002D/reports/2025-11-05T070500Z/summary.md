# TORCH-REFINE-002D Implementation Loop — 2025-11-05T070500Z

## Problem Statement

Per input.md Do Now, plumb the deterministic Stage A misset (U_delta from refGeom→perturbed) into the refinement loop so the smoke test can exercise the perturbation while staying on nearest-neighbor HKL (no tricubic, no grid rebuild). Implements:

> **SPEC (docs/spec-db-workflow.md:30-78):**
> "Stage A SHALL optimize crystal unit cell (a/b/c logs, alpha/beta/gamma bounded), orientation (quaternion→XYZ misset_deg), and global scale using LBFGS with closure recomputing full loss."

> "Orientation refinement uses misset_deg (XYZ extrinsic Euler angles, degrees) applied after MOSFLM A* injection per DiffBragg semantics."

## ADR Alignment

- **REFINE-005** (docs/findings.md:18): Stage A SHALL disable interpolation (`crystal.interpolate=False`) to use nearest-neighbor |F| lookup, avoiding tricubic halo requirements and gradient issues with fractional HKL indices.
- **GRADIENT-001** (docs/findings.md:35): Production refinement must preserve autograd by accepting tensor-valued overrides without `.item()` detaching; misset plumbing uses torch.tensor on device/dtype to maintain differentiability.
- **REFINE-003** (docs/findings.md:36): Orientation refinement via misset_deg_override avoids A* reconstruction conflicts by adding baseline + optimization deltas directly to the misset field.
- **GEOMETRY-002** (docs/findings.md:6): XYZ Euler extraction from U_delta uses analytic formulas (`phi_y=-asin(R[2,0])`, `phi_x=atan2(R[2,1],R[2,2])`, `phi_z=atan2(R[1,0],R[0,0])`) to prevent rotation matrix drift.

## Search Summary

Existing implementations reviewed:
- `dbex/nanobrag_refinement.py:172-700` — `run_nanobrag_refinement` LBFGS closure; confirmed no baseline_crystal parameter or U_delta extraction present (file:172)
- `tests/dbex/test_torch_refine_smoke.py:63-140` — `create_perturbed_geometry` helper applies deterministic cell stretch (+2/+1/+1%) and Z-rotation (+1.5°), but smoke test (lines 191-340) does not pass baseline crystal (file:63)
- `dbex/nanobrag_refinement.py:333-358,581-598` — Orientation plumbing converts orientation_vec → quaternion → XYZ Euler and passes to `create_crystal_config(misset_deg_override=...)`, but baseline misset was never added (file:333)
- `dbex/nanobrag_refinement.py:363-366,603-606` — TODO comments to disable interpolation were present but not implemented (file:363)
- `dbex/nanobrag_refinement.py:669-683` — Telemetry hardcoded `'initial': [0.0, 0.0, 0.0]`, missing baseline misset capture (file:679)

No duplication detected; this loop extends existing orientation path without replacing prior work.

## Changes

**1. U_delta extraction (dbex/nanobrag_refinement.py:172-258)**
- Added `baseline_crystal` optional parameter to `run_nanobrag_refinement` docstring (lines 197-200)
- Extracted U matrices from baseline and perturbed crystals via scitbx `sqr` API (lines 234-242)
- Computed U_delta = U_perturbed @ U_baseline^{-1} and converted to numpy array (lines 242-245)
- Applied GEOMETRY-002 formulas to extract XYZ Euler angles from U_delta matrix (lines 247-254)
- Created `baseline_misset_deg_tensor` on refinement device/dtype (line 258)

**2. Misset plumbing in LBFGS closure (dbex/nanobrag_refinement.py:381-410)**
- Added baseline_misset_deg_tensor to misset_xyz_deg after quaternion→Euler conversion (lines 381-385)
- Disabled tricubic interpolation by setting `crystal_model.interpolate = False` (lines 407-410)
- Comment references REFINE-005 and input.md rationale (lines 408-409)

**3. Misset plumbing in final render (dbex/nanobrag_refinement.py:587-614)**
- Added baseline_misset_deg_tensor to misset_xyz_deg in final render path (lines 587-589)
- Disabled tricubic interpolation identically to closure (lines 608-611)

**4. Telemetry capture (dbex/nanobrag_refinement.py:677-691)**
- Computed final total misset as baseline + optimization delta (line 679)
- Captured initial_misset from baseline_misset_deg_tensor when provided, else [0,0,0] (lines 680,683)
- Updated param_deltas['misset_xyz_deg'] with initial, final (total), delta (optimization only), and quaternion_norm (lines 686-691)

**5. Test update (tests/dbex/test_torch_refine_smoke.py:227-248,272,284-331)**
- Created perturbed geometry via `create_perturbed_geometry` helper (lines 230-236)
- Passed baseline_crystal parameter to `run_nanobrag_refinement` (line 247)
- Added assertion for 'initial' field in misset_xyz telemetry (line 272)
- Added deterministic misset assertions: Z-component ~1.5° (±0.2°), X/Y near zero (lines 284-297)
- Updated xfail rationale to reflect TORCH-REFINE-002D progress and NN HKL orientation gradient limitation (lines 312-331)

## Test Results

**Targeted selector (tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion):**
- `pytest --collect-only`: 1 test collected
- `pytest -v --maxfail=1`: XFAIL in 19.98s
- Telemetry validated: initial=[0.0, 0.0, 1.5] degrees (Z-component matches perturbation helper)
- HKL hit rate: 98.07% (6103634/6224001), stable across LBFGS iterations
- Improvement: 0.22% (below ≥5% gate, xfail triggered as expected per updated rationale)

**Full test suite:**
- `pytest -v tests/`: 69 passed, 3 skipped, 1 xfailed, 0 failed in 639.11s (10:39)
- No regressions introduced

## Artifacts

- `collect_stage_a.log` — Collection output (1 test)
- `pytest_stage_a.log` — Targeted test run (XFAIL in 19.98s)
- `pytest_full_suite.log` — Full suite (69 passed, 3 skipped, 1 xfailed)

## Ledger Updates

- `docs/fix_plan.md:73` — Added 2025-11-05T070500Z attempt with implementation details, metrics, and Next Actions
- No findings.md update required (REFINE-003/004/005 remain valid; no new guardrails)

## Next Steps

1. **Immediate (this initiative):** Mark TORCH-REFINE-002D exit criteria 1+3 satisfied (telemetry plumbing complete, ≥95% hit rate achieved, Attempts History updated); criterion 2 (≥5% gate) remains blocked by negligible orientation gradient with NN lookup.
2. **Follow-on (Option A):** Spawn HKL grid rebuild initiative to reindex structure factors against perturbed A*, enabling larger perturbation or restoring tricubic interpolation with halo.
3. **Alternative (Option B):** Explore larger perturbation amplitude (e.g., +3-5% cell stretch, +3-5° rotation) to assess orientation gradient headroom without grid rebuild.
4. **Documentation closure:** If closing TORCH-REFINE-002D, update docs/spec-db-conformance.md DB-AT-025 to note Stage A interpolate=False policy and REFINE-005 mitigation status.
