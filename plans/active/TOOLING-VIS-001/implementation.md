# TOOLING-VIS-001 — Standardized Visual Diagnostics

## Initiative
- ID: TOOLING-VIS-001
- Title: Standardize Visual Diagnostics (Z-Scores & Triptychs)
- Status: pending

## Goals
- Implement the visual standards defined in `docs/spec-db-vis.md`.
- Replace ad-hoc plotting scripts with a reusable library `dbex.vis`.
- Ensure visual artifacts (PNGs) are generated automatically by the CLI.

## Exit Criteria
1. `dbex.vis` module exists and implements `plot_triptych` and `plot_z_scores`.
2. `dbex/look.py` refactored to use `dbex.vis`.
3. `refine_one.py` generates a summary PNG report automatically.
4. Visuals respect `(slow, fast)` coordinates and Z-score definitions.
5. Test harnesses (smoke/parity) use `dbex.vis` for artifact generation.

## Spec Alignment
- **Normative Spec:** `docs/spec-db-vis.md`
- **Key Clauses:** Coordinate Systems, Triptych Layout, Residual Definition.

## Context Priming (read before edits)
- `scripts/generate_simple_cubic_golden.py` ROI triptych pipeline (`compute_roi_metrics`, ROI `.npz` bundles, and `index.json` metadata).
- PERF-WARM-SIM-001 Stage A ROI telemetry (`roi_count_*`, `cache_mode`, `roi_mode`, `forward_time_ms`) and `[panel, slow, fast]` tensor conventions.

## Reference Implementation (Prototype)
*Use this logic as the seed for `dbex/vis/triptych.py`. Do not copy-paste monolithic scripts; extract the plotting functions.*

```python
def _roi_scale_and_corr(data_roi, bg_roi, bragg_roi):
    """Closed-form scale and correlation for a single ROI."""
    y = data_roi - bg_roi
    x = bragg_roi
    num = np.sum(x * y)
    den = np.sum(x * x)
    s = float(num / den) if den > 1e-12 else 0.0
    if s < 0: s = 0.0
    model = bg_roi + s * bragg_roi
    
    # Correlation
    y0 = data_roi - np.mean(data_roi)
    m0 = model - np.mean(model)
    denom = (np.linalg.norm(y0) * np.linalg.norm(m0))
    corr = float(np.sum(y0 * m0) / denom) if denom > 1e-12 else 0.0
    return s, corr, model

def plot_roi_grid(rois, data_stack, model_stack, bg_stack, filename):
    """
    rois: list of (pid, x0, x1, y0, y1)
    data_stack, model_stack: [panel, slow, fast] arrays
    """
    rows = len(rois)
    fig, axes = plt.subplots(rows, 3, figsize=(10, 3 * rows), constrained_layout=True)
    
    for r, (pid, x0, x1, y0, y1) in enumerate(rois):
        # Slice: [pid, y0:y1, x0:x1] (Slow, Fast)
        data = data_stack[pid, y0:y1, x0:x1]
        model = model_stack[pid, y0:y1, x0:x1]
        bg = bg_stack[pid, y0:y1, x0:x1]
        
        # Calculate residuals (Z-score logic goes here per spec)
        resid = data - model 
        
        # Plot Data | Model | Residual
        axes[r, 0].imshow(data, cmap="gray", origin="upper")
        axes[r, 1].imshow(model, cmap="gray", origin="upper")
        axes[r, 2].imshow(resid, cmap="seismic", origin="upper")
        
    fig.savefig(filename)
    plt.close(fig)
```

## Phase A — Library Implementation
### Checklist
- [ ] A1: Create `dbex/vis/` package.
- [ ] A2: Implement `triptych.py`: Standard layout, shared colormaps.
- [ ] A3: Implement `residuals.py`: Z-score calculation (requires variance input).
 - [ ] A4: Ensure `dbex.vis` can consume existing ROI triptych artifacts and metrics (from `scripts/generate_simple_cubic_golden.py` and PERF-WARM-SIM-001 Stage A telemetry) as first-class inputs, rather than defining a new ROI schema. If those artifacts are missing required fields, extend that pipeline/contract in its home initiative and then adapt `dbex.vis` to the updated schema.

## Phase B — Integration
### Checklist
- [ ] B1: Refactor `dbex/look.py` to consume `dbex.vis`.
- [ ] B2: Update `dbex/refine_one.py` to generate a static report on exit.

## Phase C — Test Infrastructure Unification
### Checklist
- [ ] C1: Refactor `tests/dbex/test_nanobrag_smoke.py` to use `dbex.vis.save_triptych`.
- [ ] C2: Update parity harness (tests/fixtures/parity_loader.py) to use `dbex.vis`.

## Stage A Mapping Helpers (Plan-Local)

- Mapping context: `dbex.vis.mapping.build_mapping_stage_a_context` constructs a
  `MappingStageAContext` from canonical refGeom assets using `simulate_forward_once`
  and DB-AT-024 calibration/MTZ preferences (refined structure factors when present).
- Vis-only refinement: `dbex.vis.mapping.refine_on_mapping_model` runs a
  scale-only Adam optimization on top of the mapping Bragg stack using the
  variance-weighted chi-squared loss (sigma_floor clamp, detached denominator).
- Drivers:
  - `plans/active/TOOLING-VIS-001/bin/generate_zero_iter_refined_roi_triptychs.py` —
    zero-iteration triptychs (mapping-only).
  - `plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs.py` —
    mapping-based before/after ROI triptychs (scale-only refinement).
  - `plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs_adam.py` —
    mapping-based Adam scale-only refinement with loss trace and aggregate grids.
  - `plans/active/TOOLING-VIS-001/bin/probe_mapping_stage_a_context_metrics.py` —
    DB-AT-024-aligned probe for mapping context correlation/localization metrics.

## Artifacts Index
- Reports root: `plans/active/TOOLING-VIS-001/reports/`
