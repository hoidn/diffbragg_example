# Input for Ralph — Loop i=270

## Summary
Implement Phase A (Library Implementation) for TOOLING-VIS-001: Create `dbex.vis` module with triptych rendering and Z-score residuals per spec-db-vis.md standards.

## Mode
none

## Focus
TOOLING-VIS-001 — Standardize visual diagnostics library (Phase A: Library Implementation)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_vis_triptych.py::test_triptych_layout` — Validates 3-panel triptych structure, colormaps per spec
- `tests/dbex/test_vis_triptych.py::test_z_score_calculation` — Validates Z-score formula `(data-model)/sqrt(variance)` with known inputs
- `tests/dbex/test_vis_triptych.py::test_z_score_masking` — Validates masked pixels set to NaN

## Artifacts
`plans/active/TOOLING-VIS-001/reports/2025-11-24T111500Z/`

## Do Now

### Focus Item
**TOOLING-VIS-001 Phase A** — Implement core visualization library primitives per spec-db-vis.md

### Checklist IDs (from implementation.md:76-80)
- A1: Create `dbex/vis/` package
- A2: Implement `triptych.py` — Standard layout, shared colormaps
- A3: Implement `residuals.py` — Z-score calculation (requires variance input)
- (A4 deferred to Phase B: ROI artifact consumption adapters)

### Implementation Tasks

**Implement:**
1. `dbex/vis/__init__.py` — Package initialization (~20 lines)
   - Module docstring: "Visual diagnostics library implementing spec-db-vis.md standards"
   - Public API exports: `plot_triptych` (from triptych.py), `compute_z_scores` (from residuals.py)

2. `dbex/vis/triptych.py::plot_triptych` (~80 lines)
   - Function signature:
     ```python
     def plot_triptych(
         data: np.ndarray,      # [slow, fast] observed
         model: np.ndarray,     # [slow, fast] prediction
         variance: np.ndarray,  # [slow, fast] variance map
         hkl: tuple = None,     # (h, k, l) Miller indices (optional)
         correlation: float = None,  # ROI correlation coefficient (optional)
         filename: str = None   # Save PNG if provided, else return figure
     ) -> matplotlib.figure.Figure:
         """
         Render standard ROI triptych per spec-db-vis.md.

         Layout: [Observed Data | Model Prediction | Residual Z-Score]

         Colormaps (spec-db-vis.md §20-22):
         - Data/Model: 'viridis' (perceptually uniform), shared vmin=0, vmax=max(data, model)
         - Residuals: 'seismic' (diverging), centered at 0, vmin=-5, vmax=5

         Annotation: Super-title "HKL (h,k,l) | CC = {corr:.3f}" if hkl/correlation provided.

         Coordinate system (spec-db-vis.md §7-11):
         - (slow, fast) matrix coordinates
         - Origin (0,0) top-left
         - Fast axis horizontal, Slow axis vertical
         - Use origin='upper' in imshow
         """
     ```
   - Implementation:
     - `fig, axes = plt.subplots(1, 3, figsize=(12, 4))`
     - Panel 0: `axes[0].imshow(data, cmap='viridis', origin='upper', vmin=0, vmax=vmax_shared)`
     - Panel 1: `axes[1].imshow(model, cmap='viridis', origin='upper', vmin=0, vmax=vmax_shared)`
     - Panel 2: Z-scores via `compute_z_scores(data, model, variance)`, then `axes[2].imshow(z_scores, cmap='seismic', origin='upper', vmin=-5, vmax=5)`
     - Titles: "Data", "Model", "Residual Z-Score"
     - Super-title with HKL/CC if provided
     - If filename: `fig.savefig(filename, dpi=150, bbox_inches='tight')`, return None
     - Else: return fig

3. `dbex/vis/residuals.py::compute_z_scores` (~40 lines)
   - Function signature:
     ```python
     def compute_z_scores(
         data: np.ndarray,
         model: np.ndarray,
         variance: np.ndarray,
         mask: np.ndarray = None
     ) -> np.ndarray:
         """
         Compute residual Z-scores per spec-db-vis.md §19.

         Formula: Z = (Data - Model) / sqrt(Variance)

         Masked pixels (mask=False or mask=0) are set to NaN for visualization.

         Numerical stability: Add epsilon=1e-12 to denominator to prevent divide-by-zero.

         Returns:
             Z-score map with same shape as inputs. NaN where masked.
         """
     ```
   - Implementation:
     - `residuals = data - model`
     - `std_dev = np.sqrt(variance + 1e-12)  # Numerical stability`
     - `z_scores = residuals / std_dev`
     - If mask provided: `z_scores[~mask.astype(bool)] = np.nan`
     - Return z_scores

4. `tests/dbex/test_vis_triptych.py` (~120 lines, 3 test functions)

   **Test 1: test_triptych_layout**
   - Synthetic inputs: `data = np.ones((10,10)) * 5`, `model = np.ones((10,10)) * 3`, `variance = np.ones((10,10))`
   - Call: `fig = plot_triptych(data, model, variance, hkl=(1,2,3), correlation=0.95)`
   - Assertions:
     - `assert len(fig.axes) == 3` (3 panels)
     - Check colormaps: `assert fig.axes[0].images[0].get_cmap().name == 'viridis'`
     - Check super-title contains "HKL (1, 2, 3)" and "CC = 0.950"
     - Check origin: `assert fig.axes[0].images[0].origin == 'upper'`
   - Cleanup: `plt.close(fig)`

   **Test 2: test_z_score_calculation**
   - Known inputs: `data = np.array([[5,5],[5,5]])`, `model = np.array([[3,3],[3,3]])`, `variance = np.array([[1,1],[1,1]])`
   - Call: `z_scores = compute_z_scores(data, model, variance)`
   - Expected: `z_scores ≈ [[2,2],[2,2]]` (residual=2, std_dev=1, z=2)
   - Assertion: `np.testing.assert_allclose(z_scores, 2.0, rtol=1e-5)`
   - Edge case: `variance = np.array([[0,0],[0,0]])` → no divide-by-zero error (epsilon handling)

   **Test 3: test_z_score_masking**
   - Inputs: `data = np.ones((5,5)) * 10`, `model = np.ones((5,5)) * 8`, `variance = np.ones((5,5)) * 4`
   - Mask: `mask = np.ones((5,5))`, then `mask[2,2] = 0` (center pixel masked)
   - Call: `z_scores = compute_z_scores(data, model, variance, mask=mask)`
   - Assertions:
     - `assert np.isnan(z_scores[2,2])` (masked pixel is NaN)
     - `assert not np.isnan(z_scores[0,0])` (unmasked pixel is valid)
     - `assert np.abs(z_scores[0,0] - 1.0) < 1e-5` (residual=2, std=2, z=1)

### Validating Pytest Node
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_vis_triptych.py
```

**Expected outcome:** 3/3 tests PASS

### Decision Paths
- **Path A (All tests PASS):** Phase A COMPLETE, commit artifacts, update implementation.md checklist A1+A2+A3 as done, proceed to Phase B planning next loop
- **Path B (Variance computation issue):** Document blocker, defer A3 residuals, keep A1+A2 only, investigate variance source next loop
- **Path C (Test failures due to test logic):** Debug test assertions, iterate on test code, stay in Phase A
- **Path D (Import error matplotlib/numpy):** Record error in fix_plan.md per Environment Freeze, mark TOOLING-VIS-001 blocked, switch focus

## How-To Map

### Environment
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export PYTHONPATH=.
```

### Implementation Sequence (9 steps)

**Step 1:** Read planning analysis
```bash
cat plans/active/SUPERVISOR/reports/2025-11-24T111500Z/tooling_vis_001_phase_a_planning.md
```

**Step 2:** Create package directory
```bash
mkdir -p dbex/vis
touch dbex/vis/__init__.py
```

**Step 3:** Implement `dbex/vis/__init__.py` (~20 lines)
- Module docstring
- Import and export: `from .triptych import plot_triptych`
- Import and export: `from .residuals import compute_z_scores`

**Step 4:** Implement `dbex/vis/residuals.py::compute_z_scores` (~40 lines)
- Copy function signature from Do Now section above
- Implement formula: `(data - model) / sqrt(variance + eps)`
- Handle masking: NaN for masked pixels
- Comprehensive docstring with spec reference

**Step 5:** Implement `dbex/vis/triptych.py::plot_triptych` (~80 lines)
- Copy function signature from Do Now section above
- 3-panel subplot layout
- Colormaps per spec: viridis (data/model), seismic (residuals)
- Call `compute_z_scores()` for Panel 2
- HKL/CC annotation in super-title if provided
- Comprehensive docstring with spec references

**Step 6:** Create test file `tests/dbex/test_vis_triptych.py` (~120 lines)
- Import: `import numpy as np`, `import pytest`, `import matplotlib.pyplot as plt`, `from dbex.vis import plot_triptych, compute_z_scores`
- Implement 3 test functions as specified in Do Now section

**Step 7:** Run tests
```bash
cd /home/ollie/Documents/diffbragg_example
pytest -vv tests/dbex/test_vis_triptych.py
```

**Step 8:** Decision synthesis
- Create `plans/active/TOOLING-VIS-001/reports/2025-11-24T111500Z/decision.json`
- Choose outcome: `all_tests_pass` (Path A), `variance_blocker` (Path B), `test_failure` (Path C), `import_error` (Path D)
- Document metrics: test count, runtime, any blockers

**Step 9:** Update artifacts and commit
- Update `plans/active/TOOLING-VIS-001/implementation.md` checklist: A1/A2/A3 status
- Write `plans/active/TOOLING-VIS-001/reports/2025-11-24T111500Z/summary.md` with Turn Summary
- Stage files: `git add dbex/vis/ tests/dbex/test_vis_triptych.py plans/active/TOOLING-VIS-001/`
- Commit: `git commit -m "TOOLING-VIS-001 Phase A: dbex.vis library (triptych + residuals) — tests: run"`
- Push: `git push`

### ROI Coverage (Thresholds)
- None for Phase A (pure library implementation, no ROI-specific validation yet)
- Integration with ROI artifacts deferred to Phase B

## Pitfalls To Avoid

1. **Coordinate system confusion:** MUST use `origin='upper'` in imshow per spec-db-vis.md (top-left origin, not bottom-left)
2. **Colormap diverging center:** For residuals, use `vmin=-5, vmax=5` to center seismic colormap at 0 (white=zero residual)
3. **Shared data/model vmax:** Data and Model panels MUST have identical vmin/vmax for fair comparison (`vmax = max(data.max(), model.max())`)
4. **Z-score numerical stability:** Add epsilon to variance denominator to prevent divide-by-zero
5. **Masked pixels:** Set to NaN (not 0) so they render as transparent/white in imshow
6. **Module imports:** Do NOT create circular imports (residuals.py imports nothing from triptych.py or vice versa; both are leaf modules)
7. **Test cleanup:** MUST call `plt.close(fig)` after every test to prevent matplotlib memory leaks
8. **Figure return:** If `filename` provided, save PNG and return None; else return figure handle for interactive use
9. **Spec citations:** Include spec-db-vis.md section references in docstrings for traceability
10. **Protected Assets:** Do NOT modify `dbex/look.py` or `dbex/refine_one.py` in Phase A; defer to Phase B integration

**Environment:**
- Assume matplotlib and numpy available per Environment Freeze policy
- If import fails, record error and mark blocked per Path D

## If Blocked
- Record specific error message in `plans/active/TOOLING-VIS-001/reports/2025-11-24T111500Z/block_analysis.md`
- Update `docs/fix_plan.md` TOOLING-VIS-001 status to `blocked` with error signature
- Append to `galph_memory.md` with focus, dwell, artifacts path, blocker description
- Do NOT attempt workarounds or environment changes per POLICY-001

## Findings Applied

**Mandatory — Supervisor verified these are relevant to Phase A:**

- **spec-db-vis.md §7-11** (Coordinate Systems): Origin (0,0) top-left, fast=horizontal, slow=vertical, use origin='upper' in imshow
- **spec-db-vis.md §16-23** (ROI Triptych Layout): 3 panels, Data/Model shared colormap viridis, Residuals diverging seismic, HKL/CC annotation
- **spec-db-vis.md §19** (Residual Definition): Z = (Data - Model) / sqrt(Variance)
- **PHYSICS-LOSS-001** (Variance-weighted loss): Variance map convention `σ² = model + σ²_readout` (readout noise σ²_read=25 ADU² per spec-db-core.md §Variance Model)
- **POLICY-001** (Environment Freeze): Do NOT install packages; if matplotlib/numpy missing, record blocker
- **CLAUDE.md §Code Quality** (Every commit must compile, pass tests): Run pytest validation before committing

No relevant findings in knowledge base beyond those above.

## Pointers

### Specs
- **spec-db-vis.md:1-49** — Full visual diagnostics specification (coordinate systems, triptych layout, Z-scores, file formats)
- **spec-db-core.md §Variance Model** — Variance formula `σ² = model + σ²_readout` (σ_read=5 ADU readout noise)

### Architecture
- **implementation.md:75-80** — Phase A checklist (A1: package, A2: triptych, A3: residuals, A4: adapters deferred)
- **implementation.md:32-72** — Reference prototype code (ROI scaling, triptych plotting logic)

### Testing
- **TESTING_GUIDE.md** — Canonical pytest commands and environment flags
- **fix_plan.md:199-202** — TOOLING-VIS-001 exit criteria (3 total, Phase A addresses #1 partial: library creation)

### Fix Plan
- **fix_plan.md:194-207** — TOOLING-VIS-001 ledger entry (status, dependencies, attempts history)

### Planning
- **plans/active/SUPERVISOR/reports/2025-11-24T111500Z/tooling_vis_001_phase_a_planning.md** — Comprehensive 6.5-hour effort estimate, risk analysis, 4-path decision tree

## Next Up
If Ralph finishes Phase A early (Path A outcome):
1. **Option 1 (preferred):** Return to supervisor for Phase B planning (dbex/look.py refactor to use dbex.vis)
2. **Option 2 (if time remains):** Author smoke test that generates one PNG triptych from synthetic data for visual inspection

## Doc Sync Plan
Not required for Phase A (internal library implementation, no user-facing tests or selectors yet).

## Mapped Tests Guardrail
- At least one mapped selector WILL collect: `tests/dbex/test_vis_triptych.py` is NEW, created in Step 6
- After creation, verify with:
  ```bash
  pytest --collect-only tests/dbex/test_vis_triptych.py
  ```
  Expected: "collected 3 items"

## Normative Math/Physics
**Z-Score Residual Formula (spec-db-vis.md §19):**
```
Z = (Data - Model) / sqrt(Variance)
```
Where:
- Data = Observed intensity (ADU)
- Model = Predicted intensity (Bragg + background, ADU)
- Variance = σ² = Model + σ²_readout (per spec-db-core.md Variance Model)
- σ_readout = 5 ADU readout noise → σ²_readout = 25 ADU²

See `docs/spec-db-core.md §Variance Model` for full derivation and rationale.

**Implementation Note:** For Phase A, variance is passed as input parameter. Phase B integration will extract variance from RefinementTelemetry or compute from model + readout noise constant.
