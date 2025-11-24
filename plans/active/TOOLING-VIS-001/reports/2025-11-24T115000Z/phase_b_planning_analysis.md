# TOOLING-VIS-001 Phase B Planning Analysis

**Date:** 2025-11-24T115000Z
**Agent:** Galph
**Loop:** i=271
**Focus:** TOOLING-VIS-001 Phase B Integration
**Action Type:** planning

## Context

Ralph successfully completed Phase A (commit fa4bed95, 2025-11-24T111500Z):
- ✓ Created `dbex.vis` package with minimal public API
- ✓ Implemented `plot_triptych(data, model, variance, hkl=None, correlation=None, filename=None)`
- ✓ Implemented `compute_z_scores(data, model, variance, mask=None)`
- ✓ All 3 unit tests PASSED (0.29s runtime)
- ✓ Spec alignment: spec-db-vis.md §7-11 (coordinates), §14-24 (triptych), §19 (Z-score), §20-22 (colormaps)

## Phase B Objective

Per implementation.md:82-86, Phase B consists of 2 tasks:
- **B1:** Refactor `dbex/look.py` to consume `dbex.vis.plot_triptych`
- **B2:** Update `dbex/refine_one.py` to generate a static report on exit

## Blocker Analysis: Variance Data Missing from HDF5

**Problem:** Current `dbex/look.py` reads HDF5 files (lines 52-77) but variance is NOT saved:
- ✓ Available: `data/roi%d`, `model/roi%d`, `bragg/roi%d`, `bg/roi%d`, `score`
- ❌ Missing: `variance/roi%d` (required by `plot_triptych` API)

**Root Cause:** `dbex/refine_one.py` HDF5 writing (lines 237-244, 647-654) does not save variance per-ROI.

**Variance Definition (spec-db-core.md §86-90):**
- Formula: `V = I_model + sigma_readout^2` (I_model = Bragg + background)
- Physical lower bound: `V = max(I_model + sigma_readout^2, sigma_floor^2)`
- `sigma_readout` from `--sigma-r` CLI flag or calibrated dark-RMS maps
- `sigma_floor` defaults to instrument readout noise (≥1 photon)

## Phase B.1: Add Variance to HDF5 Output

**Scope:** Extend `dbex/refine_one.py` to compute and save variance per-ROI.

### B.1 Implementation Tasks

1. **Legacy Backend (DiffBragg) — lines 200-244:**
   - Locate `model_subims` loop (line 240)
   - Compute variance per ROI: `variance_subims[i] = model_subims[i] + sigma_readout**2`
   - Extract `sigma_readout` from CLI args `--sigma-r` (already exists line ~159)
   - Apply `sigma_floor` clamp: `variance_subims[i] = np.maximum(variance_subims[i], sigma_floor**2)`
   - Add HDF5 dataset: `h.create_dataset("variance/roi%d" % i, data=variance_subims[i])`
   - Add scalar datasets: `h.create_dataset("sigma_readout", data=sigma_readout)`, `h.create_dataset("sigma_floor", data=sigma_floor)`

2. **Torch Backend (nanobrag) — lines 610-654:**
   - Same pattern as Legacy backend
   - Variance computation uses same formula: `variance_subims[i] = model_subims[i] + sigma_readout**2`
   - Apply same `sigma_floor` clamp
   - Add same HDF5 datasets

**Estimated Code:** ~30-40 lines total (both backends)

**Validation:** After implementation, verify HDF5 file contains:
- `variance/roi0`, `variance/roi1`, ... datasets (shape matches `data/roi%d`)
- `sigma_readout` scalar
- `sigma_floor` scalar

## Phase B.2: Refactor dbex/look.py

**Scope:** Replace current composite [Data|Model] rendering with `dbex.vis.plot_triptych` producing [Data|Model|Residuals] triptychs.

### Current Implementation Analysis (dbex/look.py)

- Lines 100-136: `_plot_page` method creates composite images `[Data | Black Line | Model]`
- Line 123: Uses 'cividis' colormap (spec wants 'viridis' for data/model)
- Lines 115-122: Custom vmin/vmax calculation (mean ± std, 3σ)
- Line 126: Title format: `ROI {i} | Score: {score*100:.1f}`

### B.2 Implementation Tasks

1. **Update HDF5 loading (lines 49-77):**
   - Add variance loading: `'variance': [h["variance"]["roi%d" % i][()] for i in range(len(scores))]`
   - Add scalars: `'sigma_readout': h["sigma_readout"][()]`, `'sigma_floor': h["sigma_floor"][()]`

2. **Refactor plotting method (lines 79-147):**
   - Remove composite image creation (lines 104-109)
   - Remove manual vmin/vmax calculation (lines 115-122)
   - Replace `ax.imshow(composite_im, ...)` (line 123) with:
     ```python
     fig_roi = dbex.vis.plot_triptych(
         data=self.data['data'][i],
         model=self.data['model'][i],
         variance=self.data['variance'][i],
         hkl=None,  # No HKL data in HDF5 currently
         correlation=self.data['scores'][i],
         filename=None  # Return figure for embedding
     )
     ```
   - Extract axes from `fig_roi` and embed in grid layout
   - **Challenge:** `plot_triptych` returns a figure with 3 axes; need to extract and re-embed in paginated grid

3. **Alternate Approach (Simpler):**
   - Instead of refactoring `_plot_page` grid layout, use `plot_triptych` with `filename` parameter for static reports (Phase B.3)
   - Keep interactive viewer with composite images for now (defer full refactor to future phase)
   - **Rationale:** `plot_triptych` is designed for single-ROI standalone figures, not grid layouts

**Recommendation:** Defer B.2 full refactor until Phase C; focus Phase B on:
- **B.1:** Add variance to HDF5 (blocker for any triptych usage)
- **B.2-lite:** Add command-line flag to `dbex/look.py` to generate static triptych PNGs for selected ROIs (proof-of-concept)
- **B.3:** Auto-generate summary report in `dbex/refine_one.py` using triptychs

## Revised Phase B Scope (Lite Integration)

### B.1: Add Variance to HDF5 (REQUIRED)
- Extend `dbex/refine_one.py` to compute and save variance per-ROI
- Add `sigma_readout` and `sigma_floor` scalars
- **Validation:** h5py inspection, verify datasets exist

### B.2-lite: Proof-of-Concept Static Triptych Export
- Add `--export-triptychs <output_dir>` flag to `dbex/look.py`
- When flag present, generate PNG triptychs for all ROIs using `dbex.vis.plot_triptych`
- Skip interactive viewer when export mode enabled
- **Validation:** Confirm PNG files match spec (3 panels, viridis/seismic, Z-scores visible)

### B.3: Auto-Generate Summary Report (deferred to Phase B.3-lite)
- Defer to separate subtask after B.1+B.2-lite validated

## Implementation Plan: Phase B.1 + B.2-lite

### Step 1: Variance HDF5 Extension (B.1)
**Files:** `dbex/refine_one.py`
**Lines Modified:** ~237-244 (Legacy), ~647-654 (Torch)
**Code Added:** ~30-40 lines

**Checklist:**
1. Extract `sigma_readout` from CLI args (already available via `--sigma-r`)
2. Set `sigma_floor = 1.0` (spec default, or make configurable via CLI)
3. Legacy backend: compute variance loop after line 240
4. Torch backend: compute variance loop after line 650
5. Both backends: add 3 HDF5 datasets (`variance/roi%d`, `sigma_readout`, `sigma_floor`)
6. Validation: Run `dbex.refine_one` and inspect HDF5 with h5py

### Step 2: Static Triptych Export (B.2-lite)
**Files:** `dbex/look.py`
**Lines Modified:** ~49-77 (load variance), ~168-177 (main), ~79-147 (export logic)
**Code Added:** ~40-50 lines

**Checklist:**
1. Update `_load_data` to read variance datasets
2. Add argparse `--export-triptychs` flag
3. Add export method: loop over ROIs, call `plot_triptych(..., filename=f"{output_dir}/roi_{i}.png")`
4. Skip interactive viewer if export mode enabled
5. Validation: Run `python -m dbex.look <hdf5> --export-triptychs <dir>`, verify PNGs

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `sigma_readout` not available in all code paths | LOW | MEDIUM | CLI validation: require `--sigma-r` or abort |
| Variance computation overflow/underflow | LOW | LOW | Use `np.maximum` for clamp, verify dtypes |
| `plot_triptych` slow for large ROI counts | LOW | LOW | Export is one-time operation, not interactive |
| HDF5 backward compatibility break | MEDIUM | LOW | Variance datasets are additive; old readers ignore |

## Estimated Effort

- **B.1 (Variance HDF5):** 1.5 hours (30min code + 30min validation + 30min edge cases)
- **B.2-lite (Static Export):** 1.5 hours (40min code + 30min validation + 20min docs)
- **Total:** 3 hours (single loop feasible)

## Exit Criteria (Phase B Revised)

1. ✅ `dbex/refine_one.py` saves variance/sigma_readout/sigma_floor to HDF5 — **Phase B.1**
2. ✅ `dbex/look.py` can export static triptych PNGs via --export-triptychs flag — **Phase B.2-lite**
3. ❌ Interactive viewer uses triptych layout — **Deferred to Phase C**
4. ❌ CLI auto-generates summary report — **Deferred to Phase B.3**

## Validation Protocol

1. **Compilation Check:**
   - `python -c "from dbex.refine_one import main; from dbex.look import HDF5Viewer"`

2. **HDF5 Variance Validation:**
   - Run: `python -m dbex.refine_one -e <expt> -r <refl> -i 0 -o test_out.h5 ...`
   - Inspect: `python -c "import h5py; h = h5py.File('test_out.h5'); print(list(h.keys())); print(list(h['variance'].keys())); print(h['sigma_readout'][()], h['sigma_floor'][()])"`
   - Expected: `variance/roi0`, `variance/roi1`, ... exist; scalars present

3. **Triptych Export Validation:**
   - Run: `python -m dbex.look test_out.h5 --export-triptychs triptychs_out/`
   - Inspect: `ls triptychs_out/ | wc -l` (should match ROI count)
   - Visual: Open PNG, verify 3 panels (Data|Model|Residuals), colormaps correct, Z-scores visible

4. **Regression Guard (optional):**
   - Run existing smoke tests without `--export-triptychs` flag
   - Verify HDF5 files backward compatible (old code can still read)

## Decision Tree

**Path A (All Validations PASS):**
- Phase B.1+B.2-lite COMPLETE
- Commit changes with message: "TOOLING-VIS-001 Phase B: Variance HDF5 + static triptych export — tests: manual validation"
- Return to Galph for Phase B.3 planning (auto-generate summary report) OR Phase C planning (interactive viewer refactor)

**Path B (Variance HDF5 FAIL):**
- Debug `sigma_readout` extraction, clamp logic, or HDF5 writing
- Verify both legacy and torch backends produce correct datasets
- Re-run validation protocol

**Path C (Triptych Export FAIL):**
- Debug `plot_triptych` integration, filename handling, or output_dir creation
- Check for import errors or API mismatches
- Re-run validation protocol

**Path D (Compilation FAIL):**
- Fix import errors, circular dependencies, or missing dbex.vis API
- Verify Phase A deliverables are present and correct

## Findings Applied

- **POLICY-001:** Environment Freeze (code-only changes, no package installs)
- **PHYSICS-LOSS-001:** Variance formula `V = I_model + sigma_readout^2` per spec-db-core.md §86-90
- **ARCH-ENGINE-002:** Lazy imports if needed (not expected for this scope)
- **spec-db-vis.md §19:** Z-score definition `(Data - Model) / sqrt(Variance)`
- **spec-db-core.md §86-90:** Variance clamp `max(V, sigma_floor^2)`

## Confidence

**HIGH (~90%)** based on:
1. Clear scope (variance HDF5 + static export, no complex refactor)
2. Phase A API proven stable (3/3 tests PASSED)
3. Variance computation straightforward (spec formula, no physics edge cases)
4. HDF5 extension is additive (backward compatible)
5. Single-loop delivery feasible (~3 hours estimated)

## Next Actions

Ralph executes Phase B.1+B.2-lite implementation:
1. Read this planning analysis
2. Implement B.1 (variance HDF5 extension in both backends)
3. Implement B.2-lite (static triptych export flag)
4. Run validation protocol (3 steps)
5. Decision synthesis (Path A/B/C/D)
6. Write summary.md with Turn Summary
7. Commit and push

**Expected Outcome:** Path A (all validations PASS → Phase B.1+B.2-lite COMPLETE)
