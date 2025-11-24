# TOOLING-VIS-001 — Standardized Visual Diagnostics

## Initiative
- ID: TOOLING-VIS-001
- Title: Standardize Visual Diagnostics (Z-Scores & Triptychs)
- Status: substantial_progress (2025-11-24T123051Z — Phases A+B complete, 3.5/5 exit criteria satisfied, Phase C deferred)

## Goals
- Implement the visual standards defined in `docs/spec-db-vis.md`.
- Replace ad-hoc plotting scripts with a reusable library `dbex.vis`.
- Ensure visual artifacts (PNGs) are generated automatically by the CLI.

## Exit Criteria
1. `dbex.vis` module exists and implements `plot_triptych` and `plot_z_scores`. — ✓ COMPLETE (Phase A, 2025-11-24T111500Z: 3/3 tests PASSED)
2. `dbex/look.py` refactored to use `dbex.vis`. — ✓ PARTIAL (Phase B.2-lite static export complete 2025-11-24T115000Z; interactive viewer refactor deferred Phase C)
3. `refine_one.py` generates a summary PNG report automatically. — ✓ COMPLETE (Phase B.2, 2025-11-24T120000Z: --report-dir flag)
4. Visuals respect `(slow, fast)` coordinates and Z-score definitions. — ✓ COMPLETE (Phase A validated in tests)
5. Test harnesses (smoke/parity) use `dbex.vis` for artifact generation. — ❌ DEFERRED (Phase C: LOW priority, no blocking dependencies)

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
- [x] A1: Create `dbex/vis/` package. ✓ COMPLETE (2025-11-24T111500Z)
- [x] A2: Implement `triptych.py`: Standard layout, shared colormaps. ✓ COMPLETE (2025-11-24T111500Z)
- [x] A3: Implement `residuals.py`: Z-score calculation (requires variance input). ✓ COMPLETE (2025-11-24T111500Z)
 - [ ] A4: Ensure `dbex.vis` can consume existing ROI triptych artifacts and metrics (from `scripts/generate_simple_cubic_golden.py` and PERF-WARM-SIM-001 Stage A telemetry) as first-class inputs, rather than defining a new ROI schema. If those artifacts are missing required fields, extend that pipeline/contract in its home initiative and then adapt `dbex.vis` to the updated schema. (DEFERRED to Phase B integration)

## Phase B — Integration
### Checklist
- [x] B1: Variance HDF5 extension in both backends (dbex/refine_one.py). ✓ COMPLETE (2025-11-24T115000Z)
  - Formula: V = max(I_model + sigma_readout^2, sigma_floor^2) per spec-db-core.md §86-90
  - HDF5 datasets: variance/roi%d, sigma_readout, sigma_floor
  - Both Legacy (lines 236-263) and Torch (lines 665-689) backends
- [x] B2-lite: Static export flag in `dbex/look.py`. ✓ COMPLETE (2025-11-24T115000Z)
  - CLI flag: --export-triptychs <dir>
  - Integration: lines 67-74 (_load_data variance read), 170-189 (export_triptychs method), 199-204 (CLI arg)
  - Interactive viewer refactor DEFERRED to Phase C
- [x] B2: Auto-generate triptych report in `dbex/refine_one.py`. ✓ COMPLETE (2025-11-24T120000Z, commit 08b89b4e)
  - CLI flag: --report-dir <path>
  - Helper function: _generate_triptych_report (lines 891-955, 64 lines)
  - Integration: Legacy backend 278-279, Torch backend 600-601

## Phase C — Test Infrastructure Unification (DEFERRED)
**Status:** Deferred (2025-11-24T123051Z — LOW priority enhancement, no blocking dependencies)

**Deferral Rationale:**
- Test infrastructure refactor is consistency/DX improvement, not functional gap
- Current test infrastructure works correctly
- No blocking dependencies from other initiatives
- Substantial user-facing value already delivered (Phases A+B complete)
- Estimated effort ~4-6 loops for LOW incremental value

**Return Conditions:**
- Ad-hoc plotting scripts in test harnesses become unmaintainable
- Interactive viewer refactor requested by user for specific workflow
- Phase C becomes blocker for another initiative (unlikely based on current roadmap)

### Checklist
- [ ] C1: Refactor `tests/dbex/test_nanobrag_smoke.py` to use `dbex.vis.save_triptych`. — DEFERRED
- [ ] C2: Update parity harness (tests/fixtures/parity_loader.py) to use `dbex.vis`. — DEFERRED
- [ ] C3: Refactor `dbex/look.py` interactive matplotlib viewer to use `dbex.vis.plot_triptych` for grid layout. — DEFERRED (Phase B.2-lite static export sufficient for user needs)

## Stage A Mapping Helpers (Plan-Local)

- Mapping context: `dbex.vis.mapping.build_mapping_stage_a_context` constructs a
  `MappingStageAContext` from canonical refGeom assets using `simulate_forward_once`
  and DB-AT-024 calibration/MTZ preferences (refined structure factors when present).
- Vis-only refinement (scale-only): `dbex.vis.mapping.refine_on_mapping_model` runs
  a scale-only Adam optimization on top of the mapping Bragg stack using the
  variance-weighted chi-squared loss (sigma_floor clamp, detached denominator).
- Full Stage-A refinement (experimental): plan-local helpers MAY wrap
  `nanobrag_torch.models.experiment.ExperimentModel(param_init="stage_a")` so
  that Stage-A DOFs (cell logs/angles, misset, and optional detector/beam
  deltas) are exposed as learnable tensors. Any such usage MUST:
  - Reuse the mapping HKL grid and calibration path established by
    `simulate_forward_once` (refined MTZ + config_torch.json).
  - Preserve the variance-weighted loss semantics from
    `docs/spec-db-core.md` and `docs/spec-db-workflow.md`.
  - Be treated as plan-local tooling only; canonical Stage A remains
    `run_nanobrag_refinement` and the Stage-smoke selectors documented in
    `docs/TESTING_GUIDE.md`.
- Drivers:
  - `plans/active/TOOLING-VIS-001/bin/generate_zero_iter_refined_roi_triptychs.py` —
    zero-iteration triptychs (mapping-only).
  - `plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs.py` —
    mapping-based before/after ROI triptychs (scale-only refinement).
  - `plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs_adam.py` —
    experimental full Stage-A Adam refinement on top of the mapping context,
    used for visualization only. This helper is explicitly **non-mapping-aligned**
    with respect to the zero-point invariant and MUST NOT be used as the
    canonical "before" reference for TOOLING-VIS-001 visuals or as a DB-AT
    selector; prefer the mapping context + scale-only refinement for
    spec-aligned paths.
  - `plans/active/TOOLING-VIS-001/bin/probe_mapping_stage_a_context_metrics.py` —
    DB-AT-024-aligned probe for mapping context correlation/localization metrics.
  - `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` —
    plan-local Stage A mapping debug driver implementing the forward-model
    equality, loss-alignment, single-step Adam, and block-wise DoF probes with
    JSON artifacts under `reports/stage_a_refgeom_adam_debug/<timestamp>/`.
  - Phase D zero-point alignment (this plan) extends `stage_a_mapping_adam_debug`
    with a no-op Stage-A probe (`zero_point_check.json`) that compares the
    helper’s zero-parameter forward model against `bragg_zero_iter` and records
    `zero_point_ok`. Geometry experiments (single-step Adam and block-wise
    DoF sweeps) are automatically skipped unless this flag is true, enforcing
    the Mapping-Aligned Stage‑A Initialization invariant from
    `docs/spec-db-conformance.md` and `docs/spec-db-workflow.md`.

## Artifacts Index
- Reports root: `plans/active/TOOLING-VIS-001/reports/`

## Phase D — Stage A Mapping Alignment & Debugging

### Objectives
- Align the Stage A engine forward model with the DB-AT-024 mapping model at the zero point (shared geometry, HKL grid, and calibration).
- Ensure Stage A ROI/full-frame visuals used by TOOLING-VIS-001 are physically meaningful (correct intensity scale, visible Bragg spots).
- Lock this behavior in with DB-AT-027/028/029 acceptance tests so similar regressions are caught automatically.

### Context Priming (read before edits)
- `docs/spec-db-conformance.md` — DB-AT-024 (mapping consistency), DB-AT-027/028/029 (Stage A parity, loss-scale, and structure).
- `docs/spec-db-core.md` — Variance model, sigma_floor semantics, masking.
- `docs/spec-db-workflow.md` — Stage A staging, mapping zero-point invariant.
- `tests/dbex/test_mapping_consistency.py` — DB-AT-024 implementation and metrics.
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` — canonical Stage A smoke behavior.
- `dbex.vis.mapping` / `dbex.tools.stage_a_adam` — mapping-based Stage A context and Adam debug helpers.

### Phase D.A — Reproduce & Quantify Stage A vs Mapping

**Checklist**
- [ ] D.A0: Run `tests/dbex/test_mapping_consistency.py::test_db_at_024_mapping_consistency` and record mapping χ², clamp_fraction, median ROI CC, and scale ratios from `mapping_metrics.json` under `plans/active/TOOLING-VIS-001/reports/<timestamp>/mapping_metrics_snapshot.json`.
- [ ] D.A1: Using the canonical Stage A refGeom driver (`plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs_adam.py`) or a small probe script, capture Stage A telemetry (χ² trace, variance_floor_*), `bragg_before`, and `bragg_after` on the simple_cubic fixture.
- [ ] D.A2: Compute and record:
  - `chi2_stagea_per_pixel = chi2_final / variance_floor_masked_pixels`,
  - ROI CCs vs data for mapping vs Stage A (before/after),
  - global intensity scale ratios `mean(bragg_before[loss_mask]) / mean(target[loss_mask])`.
- [ ] D.A3: Summarize findings in `plans/active/TOOLING-VIS-001/reports/<timestamp>/stage_a_mapping_diagnosis.md` and cite this artifact in `docs/fix_plan.md` under `[TOOLING-VIS-001]`.

### Phase D.B — Zero-Point Forward-Model Parity (DB-AT-027)

**Checklist**
- [ ] D.B0: Extend or mirror `dbex.tools.stage_a_adam.run_zero_point_check` with an engine-delegation probe that uses `run_nanobrag_refinement` (Stage A only, `max_iter=0`) and `_build_final_bragg_from_stage_a_telemetry` on the simple_cubic mapping context.
- [ ] D.B1: Ensure the probe reuses:
  - `MappingStageAContext.inputs`, `bragg_zero_iter`, `sigma_floor_value`,
  - refined HKL indices/amplitudes and calibration dict (spot_scale_override, flux, exposure, beamsize_mm, N_cells).
- [ ] D.B2: Compute:
  - `max_abs_diff` and `mean_abs_diff` between `bragg_stagea_zero` (engine) and `bragg_mapping`,
  - Stage A variance-weighted χ² on the mapping stack using the canonical PHYSICS-LOSS variance model.
- [ ] D.B3: Add a DB-AT-027 selector (e.g. `tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity`) that asserts the agreed tolerances and references the corresponding section in `docs/spec-db-conformance.md`.

### Phase D.C — Calibration Plumbing into Stage A Engine

**Checklist**
- [ ] D.C0: Design a minimal calibration payload for Stage A (spot_scale_override, beam_flux, beam_exposure, beamsize_mm, N_cells) and decide how it is threaded (e.g. via mapping context or an explicit CalibrationContext argument to `run_nanobrag_refinement` / StageA).
- [ ] D.C1: Plumb calibration into Stage A:
  - Build BeamConfig with flux/exposure/beamsize overrides when calibration is provided (matching `simulate_forward_once`),
  - Build CrystalConfig with N_cells and `apply_n_cells=True` when provided,
  - Ensure any use of the unified simulator factory (`create_unified_simulator`) receives `spot_scale_override` so the same `sqrt_spot_scale` as mapping is applied.
- [ ] D.C2: Treat Stage A log scale as a calibrated delta, not the entire scale:
  - Use the mapping-calibrated scale as the baseline,
  - Restrict Stage A’s learnable log-scale to a modest log band (e.g. ±3) around this baseline so it fine-tunes instead of compensating for missing calibration.
- [ ] D.C3: Re-run the DB-AT-027 probe on the engine path and update `docs/spec-db-conformance.md` / `docs/TESTING_GUIDE.md` once zero-point parity is achieved.

### Phase D.D — Visualization Parity & Loss-Scale Sanity (DB-AT-028/029)

**Checklist**
- [ ] D.D0: Audit and update `_build_final_bragg_from_stage_a_telemetry` so it:
  - Reuses the same HKL grid, interpolation mode, calibration, and (when applicable) baseline misset/UB state as the Stage A closure,
  - Produces `bragg_before`/`bragg_after` frames that match the calibrated engine forward passes up to numerical tolerances.
- [ ] D.D1: Implement DB-AT-028 in code:
  - Extend `test_stage_a_expansion` or add a dedicated DB-AT-028 test to assert χ²-per-pixel bounds and `variance_floor_clamp_fraction` sanity based on Stage A telemetry for the refGeom smoke fixtures.
- [ ] D.D2: Implement DB-AT-029:
  - Reconstruct Stage A initial/final Bragg frames via `_build_final_bragg_from_stage_a_telemetry`,
  - Compute per-ROI CCs vs data and global scale ratios using the canonical parity harness,
  - Assert the ROI correlation floor and scale band from `docs/spec-db-conformance.md` (DB-AT-029).
- [ ] D.D3: Refresh `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` with DB-AT-027/028/029 selectors, and record a telemetry snapshot for these tests under `plans/active/TOOLING-VIS-001/reports/<timestamp>/`.

### Phase D Risks & Notes
- Risk: Tightening DB-AT-027/028/029 too aggressively may initially fail on existing fixtures; mitigated by calibrating thresholds from current mapping/Stage A runs and tightening only after parity is proven.
- Risk: Calibration plumbing into Stage A may interact with UB parameterization and Stage B; mitigated by keeping changes scoped to Stage A engine-only mode and re-running the existing Stage A/B/C smokes.
- Note: All work must honor POLICY-001 (Environment Freeze) and reuse existing nanobrag_torch + dbex factories; no new dependencies.
