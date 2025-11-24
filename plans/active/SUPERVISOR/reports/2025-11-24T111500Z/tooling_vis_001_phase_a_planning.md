# TOOLING-VIS-001 Phase A Planning Analysis

**Date:** 2025-11-24T111500Z
**Planner:** Galph (Supervisor)
**Purpose:** Plan Phase A (Library Implementation) for TOOLING-VIS-001

## Current State

### Completed Work
- **Phase D Zero-Point Alignment** (2025-11-21T223420Z per fix_plan.md:206)
  - Implemented zero-point check in `stage_a_mapping_adam_debug.py`
  - Validation: `zero_point_ok=true`, `mean_abs_diff≈6e−5`, `|χ²_rel_diff|≈1.7e−4`
  - Geometry DoF experiments now gated on zero-point pass
  - Artifacts: `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam_debug/20251121T223420Z/`

### Dependencies Met
- **PHYSICS-LOSS-001** ✓ Done (variance-weighted loss telemetry stack operational)
- **ARCH-REFINE-FLOW-001** ✓ Done (protocol engine provides stable telemetry structure)

### Exit Criteria (from implementation.md & fix_plan.md:199-202)
1. `dbex.vis` module created implementing `spec-db-vis.md` standards (Z-scores, triptychs)
2. `dbex/look.py` refactored to use `dbex.vis` for rendering
3. CLI automatically generates a standard report (PNG/PDF) at end of refinement

## Phase A Scope Analysis

### Objectives (from implementation.md:75-80)
- **A1:** Create `dbex/vis/` package
- **A2:** Implement `triptych.py` — Standard layout, shared colormaps
- **A3:** Implement `residuals.py` — Z-score calculation (requires variance input)
- **A4:** Ensure `dbex.vis` can consume existing ROI artifacts

### Spec-DB-Vis Requirements (from docs/spec-db-vis.md)

**Coordinate Systems (§7-11, normative):**
- Images SHALL be displayed in `(slow, fast)` matrix coordinates
- Origin `(0, 0)` is top-left
- Fast axis horizontal (left→right), Slow axis vertical (top→bottom)

**ROI Triptych Layout (§14-24, normative):**
- Three panels: `[Observed Data | Model Prediction | Residual Z-Score]`
- Data/Model scaling: Shared colormap range `[0, max(data, model)]`
- Residuals: Z-score map `(Data - Model) / sqrt(Variance)`
- Colormaps:
  - Intensity: Perceptually uniform sequential (Viridis, Cividis)
  - Residuals: Diverging (Blue-White-Red or PiYG) centered at 0
- Annotation: Each ROI labeled with HKL index and correlation coefficient (CC)

**Mapping-Aligned Stage-A Visuals (§40-44, normative):**
- "Before" model SHALL be mapping-aligned Stage-A no-op Bragg tensor
- Must reproduce mapping `simulate_forward_once` within zero-point tolerance
- Plan-local refinement helpers MAY generate "after" panels on top of baseline

### Implementation Strategy

#### Module Structure
```
dbex/vis/
├── __init__.py         # Package init, exports plot_triptych, plot_z_scores
├── triptych.py         # ROI triptych rendering
├── residuals.py        # Z-score calculation per spec-db-vis.md
└── colormaps.py        # Standard colormaps (Viridis, diverging)
```

#### A1: Package Creation
- Create `dbex/vis/__init__.py` with docstring explaining purpose
- Define public API exports: `plot_triptych`, `compute_z_scores`
- **Estimated:** ~20 lines

#### A2: Triptych Implementation (`triptych.py`)
**Core Function:**
```python
def plot_triptych(
    data: np.ndarray,      # [slow, fast] observed
    model: np.ndarray,     # [slow, fast] prediction
    variance: np.ndarray,  # [slow, fast] variance map
    hkl: tuple = None,     # (h, k, l) Miller indices
    correlation: float = None,
    filename: str = None
) -> matplotlib.figure.Figure:
    """
    Render standard ROI triptych per spec-db-vis.md.

    Returns figure handle if filename=None, else saves PNG.
    """
```

**Implementation Notes:**
- Use `matplotlib.pyplot.subplots(1, 3, figsize=(12, 4))`
- Panel 1: `imshow(data, cmap='viridis', vmin=0, vmax=max(data.max(), model.max()))`
- Panel 2: `imshow(model, cmap='viridis', vmin=0, vmax=same)`
- Panel 3: `imshow(z_scores, cmap='seismic', vmin=-5, vmax=5, center=0)`
- Titles: "Data", "Model", "Residual Z-Score"
- Super-title: f"HKL {hkl} | CC = {correlation:.3f}" if provided
- **Estimated:** ~80 lines (includes docstring, validation, colorbar handling)

#### A3: Residuals Implementation (`residuals.py`)
**Core Function:**
```python
def compute_z_scores(
    data: np.ndarray,
    model: np.ndarray,
    variance: np.ndarray,
    mask: np.ndarray = None
) -> np.ndarray:
    """
    Compute residual Z-scores per spec-db-vis.md.

    Z = (Data - Model) / sqrt(Variance)

    Returns Z-score map with same shape as inputs.
    Masked pixels set to NaN for plotting.
    """
    residuals = data - model
    std_dev = np.sqrt(variance)
    z_scores = residuals / (std_dev + 1e-12)  # Numerical stability

    if mask is not None:
        z_scores = z_scores * mask
        z_scores[~mask.astype(bool)] = np.nan

    return z_scores
```
- **Estimated:** ~40 lines (includes docstring, edge case handling)

#### A4: ROI Artifact Consumption
**Analysis:**
- Existing artifacts from `scripts/generate_simple_cubic_golden.py`:
  - ROI `.npz` bundles with keys: `data`, `model`, `background`, `bbox`, `hkl`
  - `index.json` metadata with ROI metrics
- PERF-WARM-SIM-001 telemetry: `[panel, slow, fast]` tensor conventions

**Adapter Function (optional helper):**
```python
def load_roi_from_npz(npz_path: str) -> dict:
    """
    Load ROI data from .npz bundle and return dict suitable for plot_triptych.

    Returns:
        {
            'data': np.ndarray,
            'model': np.ndarray,
            'variance': np.ndarray,  # computed from model + readout noise
            'hkl': tuple,
            'bbox': tuple,
            'correlation': float
        }
    """
```
- **Estimated:** ~60 lines (if implementing adapter; otherwise defer to Phase B integration)

**Decision:** Defer adapter to Phase B. Phase A focuses on core rendering primitives only.

### Validation Strategy

#### Unit Tests (`tests/dbex/test_vis_triptych.py`)
1. **Test triptych layout:**
   - Synthetic data `(10, 10)` arrays
   - Verify 3 subplots created
   - Verify colormaps match spec (viridis, seismic)
   - Verify shared vmin/vmax for data/model

2. **Test z-score calculation:**
   - Known inputs: `data=[5,5,5]`, `model=[3,3,3]`, `variance=[1,1,1]`
   - Expected: `z_scores=[2,2,2]`
   - Edge case: `variance=[0,0,0]` → numerical stability (no divide-by-zero)

3. **Test masking:**
   - Masked pixels set to NaN
   - Verify NaN pixels don't affect colormap range calculation

**Estimated test size:** ~120 lines (3 test functions, fixtures)

#### Integration Smoke Test
- Use golden ROI data from `tests/fixtures/golden_data/` (if available)
- Generate one triptych PNG artifact
- Visual inspection (manual, no automated check yet)
- **Defer** comprehensive integration to Phase B

### Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Variance map unavailable in existing artifacts | MEDIUM | Compute from model + readout noise (σ²_read=25 ADU² per spec-db-core.md) as temporary solution; Phase B will use canonical variance from RefinementTelemetry |
| Colormap choices don't render well | LOW | Use matplotlib defaults (viridis, seismic) per spec; user can override |
| HKL/CC metadata missing in some artifacts | LOW | Make hkl/correlation optional parameters; render without annotation if None |
| Z-score calculation numerically unstable | MEDIUM | Add epsilon (1e-12) to denominator; document in code comments |

### Estimated Effort

**Breakdown:**
- A1 (Package creation): 15 min
- A2 (Triptych implementation): 2.5 hours (code 1h, docstrings 0.5h, manual test 1h)
- A3 (Residuals implementation): 1 hour (code 30min, docstrings 15min, edge cases 15min)
- Unit tests: 2 hours (3 test functions, fixtures, validation)
- Integration smoke test: 1 hour (golden data loading, visual inspection)
- Documentation (module docstrings): Inline above

**Total:** ~6.5 hours

**Single Loop Feasibility:** BORDERLINE
- If golden data available and no blockers → YES (1 loop)
- If variance computation requires investigation → NO (2 loops: Phase A2+A3 loop 1, tests loop 2)

### Decision Tree

**Path A (Ideal):** Golden data available, variance computable from model
- Implementation: A1+A2+A3 (~3.5h)
- Tests: 3 unit tests (~2h)
- Smoke test: 1 triptych PNG (~1h)
- **Outcome:** Phase A COMPLETE, commit artifacts, proceed to Phase B planning

**Path B (Variance Blocker):** Variance map not straightforward to compute
- Implementation: A1+A2 only (~2.5h)
- Tests: Triptych layout tests only (~1.5h)
- Document A3 variance blocker in planning artifact
- **Outcome:** Phase A PARTIAL, mark variance as dependency issue, investigate in next loop

**Path C (Test Failure):** Core logic correct but tests fail
- Debug test logic (~1-2h)
- Re-run validation
- **Outcome:** Iterate on tests, stay in Phase A

**Path D (Import/Environment Error):** Missing matplotlib or numpy
- Record error in fix_plan.md per Environment Freeze policy
- **Outcome:** Mark TOOLING-VIS-001 blocked, switch focus

### Confidence Assessment

**MEDIUM-HIGH (~75%)**

**Positive Factors:**
- Clear spec (spec-db-vis.md is detailed and normative)
- Matplotlib/numpy standard tooling (high confidence available)
- Prototype reference code in implementation.md:32-72
- Unit test scope well-defined

**Risk Factors:**
- Variance map computation may require investigation (MEDIUM risk)
- Golden data availability unknown (need to check `tests/fixtures/golden_data/`)
- 6.5 hour estimate is borderline for single loop

**Recommendation:** Proceed with Phase A implementation, target Path A (full implementation), but prepare for Path B (defer A3 if variance blocker).

## Production Code Requirements

Per galph_prompt §loop_discipline:
> Next turn must hand off a Do Now with at least one *production code* task (`<file>::<function>`) and a validating pytest node

**Phase A Production Code:**
1. `dbex/vis/__init__.py` — Package creation
2. `dbex/vis/triptych.py::plot_triptych` — Core triptych function (~80 lines)
3. `dbex/vis/residuals.py::compute_z_scores` — Z-score calculation (~40 lines)
4. `tests/dbex/test_vis_triptych.py` — Unit tests (3 test functions, ~120 lines)

**Validating Pytest Node:**
```bash
pytest -vv tests/dbex/test_vis_triptych.py
```

**Exit Criterion Mapping:**
- This loop advances Exit Criterion #1 ("`dbex.vis` module created implementing spec-db-vis.md standards")
- Phase B will address Exit Criterion #2 ("`dbex/look.py` refactored")
- Future phase addresses Exit Criterion #3 ("CLI auto-generates report")

## Findings Applied

- **CLAUDE.md** (Incremental progress) ✓ — Phase A isolated library implementation
- **POLICY-001** (Environment Freeze) ✓ — Matplotlib/numpy assumed available
- **spec-db-vis.md** (Normative visual standards) ✓ — Z-scores, triptych layout, colormaps
- **PHYSICS-LOSS-001** (Variance-weighted loss) ✓ — Variance map convention established
- **galph_prompt §loop_discipline** (Implementation floor) ✓ — Production code tasks specified

## Next Actions for Ralph (input.md)

1. Read this planning analysis
2. Check `tests/fixtures/golden_data/` for ROI .npz bundles (variance availability)
3. Implement A1: Create `dbex/vis/__init__.py` (~20 lines)
4. Implement A2: Create `dbex/vis/triptych.py::plot_triptych` (~80 lines)
5. Implement A3: Create `dbex/vis/residuals.py::compute_z_scores` (~40 lines)
6. Implement unit tests: `tests/dbex/test_vis_triptych.py` (3 functions, ~120 lines)
7. Run pytest: `pytest -vv tests/dbex/test_vis_triptych.py`
8. Decision synthesis (4-path template)
9. Commit artifacts with message "TOOLING-VIS-001 Phase A: dbex.vis library (triptych + residuals) — tests: run"

## Artifacts
- This analysis: `plans/active/SUPERVISOR/reports/2025-11-24T111500Z/tooling_vis_001_phase_a_planning.md`
- Next: `input.md` with detailed Phase A implementation tasks
