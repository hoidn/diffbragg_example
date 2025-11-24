# TOOLING-VIS-001 Phase A — Library Implementation Complete

**Date:** 2025-11-24T111500Z
**Agent:** Ralph
**Loop:** i=270
**Status:** Phase A COMPLETE (Path A)

## Problem Statement

**Quoted SPEC lines (spec-db-vis.md):**
- §7-11 (Coordinate Systems): "Images SHALL be displayed in `(slow, fast)` matrix coordinates. Origin `(0, 0)` is top-left. Fast axis is horizontal (left→right). Slow axis is vertical (top→bottom)."
- §16-24 (ROI Triptych Layout): "Layout: Three panels horizontally `[Observed Data | Model Prediction | Residual Z-Score]`. ... Data/Model: Shared colormap range `[0, max(data, model)]`. ... Residuals: Z-score map `(Data - Model) / sqrt(Variance)`. Colormaps: Intensity: Perceptually uniform sequential (e.g., Viridis, Cividis). Residuals: Diverging (e.g., Blue-White-Red or PiYG) centered at 0."
- §19 (Residual Definition): "Z = (Data - Model) / sqrt(Variance)"

**Relevant ADR (docs/architecture.md):**
No ADR directly applies. Phase A implements pure visualization primitives per spec-db-vis.md normative standards. Future integration (Phase B) will align with existing ADRs for CLI/HDF5 output.

## Implementation Summary

### Search Summary
Searched existing `dbex/vis/` directory:
- Found prior implementation with incompatible API (existing `plot_triptych` took pre-computed residuals; spec requires variance input and internal Z-score computation)
- Decision: Replace with spec-compliant implementation per input.md authoritative command

### Changes Made

**Files Created/Modified:**
1. `dbex/vis/__init__.py` (20 lines) — Package initialization with minimal public API exports
2. `dbex/vis/residuals.py` (81 lines) — `compute_z_scores(data, model, variance, mask=None)` implementing Z-score formula with epsilon stability and NaN masking
3. `dbex/vis/triptych.py` (129 lines) — `plot_triptych(data, model, variance, hkl=None, correlation=None, filename=None)` implementing 3-panel layout with viridis/seismic colormaps per spec
4. `tests/dbex/test_vis_triptych.py` (142 lines, 3 tests) — Unit tests validating layout, Z-score calculation, and masking per input.md spec

**Total Code:** ~370 lines (implementation + tests)

### Key Implementation Decisions

1. **Colormap choice:** Used 'viridis' (data/model) and 'seismic' (residuals) per spec-db-vis.md §20-22
2. **Coordinate system:** Enforced `origin='upper'` in all `imshow` calls per §7-11
3. **Numerical stability:** Added epsilon=1e-12 to variance sqrt to prevent divide-by-zero
4. **Masking behavior:** Masked pixels set to `np.nan` (not 0) for proper matplotlib rendering
5. **HKL/CC annotation:** Optional parameters; super-title format: "HKL (h, k, l) | CC = {corr:.3f}"

## Test Results

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_vis_triptych.py
```

**Results:** 3/3 tests PASSED (0.29s runtime)

### Test 1: test_triptych_layout
- Validated 3-panel structure
- Confirmed colormaps: viridis (data/model), seismic (residuals)
- Verified origin='upper' for all panels
- Checked super-title contains "HKL (1, 2, 3)" and "CC = 0.950"
- **Status:** PASS

### Test 2: test_z_score_calculation
- Known inputs: data=[5,5], model=[3,3], variance=[1,1]
- Expected: z_scores=[2,2] (residual=2, std=1, z=2)
- Edge case: variance=[0,0] → no divide-by-zero error (epsilon handling)
- **Status:** PASS (np.testing.assert_allclose with rtol=1e-5)

### Test 3: test_z_score_masking
- Inputs: data=10, model=8, variance=4
- Mask: center pixel (2,2) masked → NaN
- Unmasked pixels: z=(10-8)/sqrt(4) = 1.0
- **Status:** PASS (masked pixel is NaN, unmasked=1.0 ±1e-5)

### Collection Verification
```bash
pytest --collect-only tests/dbex/test_vis_triptych.py
```
**Result:** collected 3 items (test_triptych_layout, test_z_score_calculation, test_z_score_masking)

## Documentation Updates

1. `plans/active/TOOLING-VIS-001/implementation.md` — Checklist A1/A2/A3 marked complete, A4 deferred to Phase B
2. `docs/fix_plan.md` — Attempts History updated (2025-11-24T111500Z entry added)

## Exit Criteria Status

**From fix_plan.md:199-202:**
1. ✅ `dbex.vis` module created implementing `spec-db-vis.md` standards (Z-scores, triptychs) — **SATISFIED** (Phase A complete)
2. ❌ `dbex/look.py` refactored to use `dbex.vis` for rendering — **PENDING** (Phase B)
3. ❌ CLI automatically generates a standard report (PNG/PDF) at end of refinement — **PENDING** (Future phase)

**Phase A Status:** COMPLETE (3/3 checklist items done)

## Artifacts
- Pytest log: `plans/active/TOOLING-VIS-001/reports/2025-11-24T111500Z/pytest.log`
- This summary: `plans/active/TOOLING-VIS-001/reports/2025-11-24T111500Z/summary.md`

## Next Most Important Item

**Phase B Integration** (from implementation.md:82-86):
- B1: Refactor `dbex/look.py` to consume `dbex.vis.plot_triptych`
- B2: Update `dbex/refine_one.py` to generate static report on exit

This will address Exit Criterion #2 and move towards automated visual diagnostics in the CLI.

---

### Turn Summary
Implemented Phase A core library primitives for TOOLING-VIS-001 per spec-db-vis.md standards.
All 3 unit tests PASS (triptych layout with viridis/seismic colormaps verified, Z-score formula validated with known inputs residual=2 std=1 z=2, masking behavior confirmed with NaN for masked pixels).
Next: Phase B integration (refactor dbex/look.py to use new dbex.vis API, then extend CLI to auto-generate PNG reports).
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T111500Z/ (pytest.log, summary.md)
