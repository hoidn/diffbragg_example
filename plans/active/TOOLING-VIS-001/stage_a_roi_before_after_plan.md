# TOOLING-VIS-001 — Session Plan: Stage A ROI Before/After Visualization

## Context
- Initiative: `TOOLING-VIS-001` — Standardize Visual Diagnostics (Z-Scores & Triptychs).
- Goal for this session: produce *spec-aligned*, reproducible ROI visualizations that show **experiment vs model before Stage A** and **experiment vs model after Stage A** on the canonical `refGeom` dataset.
- Constraint: respect the existing TOOLING-VIS-001 roadmap (library-first `dbex.vis`, no new ROI schema, CLI integration comes later).

## Scope for This Session
- Inputs: reuse the real Stage A pipeline (no synthetic shortcuts):
  - `DataLoad(refGeom.expt, refGeom.refl, scaled.mtz, 747_mask.pkl)`.
  - `prepare_refinement_inputs(...)` → `inputs.target`, `inputs.loss_mask`, `inputs.panel_slices`, `inputs.sigma_readout`.
  - `simulate_forward_once(...)` → `bragg_before` (zero-iteration model) on the canonical detector.
  - `run_nanobrag_refinement` with Stage A only → `bragg_after`.
- Outputs:
  - Per-ROI PNG triptychs that show:
    - **Before:** `Data | Model_before | Residual Z_before`.
    - **After:**  `Data | Model_after  | Residual Z_after`.
  - A small machine-readable summary (per-ROI metadata, pre/post CC, file paths) under the TOOLING-VIS-001 reports tree.

## Planned Work Items

1. **Clarify canonical Stage A ROI inputs**
   - Codify the “right” inputs for this visualization as:
     - `inputs` from `prepare_refinement_inputs` (using the same options as the Stage A smoke path).
     - `bragg_before` from `simulate_forward_once` (HKL grid from `build_structure_factor_grid`, canonical calibration, and the mapping configuration defined in the DB‑AT‑024/DB‑AT‑027 spec).
     - `bragg_after` from `run_nanobrag_refinement` with Stage A only (CPU, tricubic+halo enabled).
   - Treat this tuple `(inputs, bragg_before, bragg_after)` as the only sanctioned source for “before/after” Stage A ROI plots (no ad-hoc peak maps or standalone scripts).

2. **Add a Stage-A-aware ROI helper in `dbex.vis`**
   - New module, e.g. `dbex/vis/stage_a.py`, exposing a helper such as:
     - `emit_stage_a_roi_triptychs(inputs, bragg_before, bragg_after, out_dir, *, roi_indices=None, max_rois=16)`.
   - Responsibilities:
     - For each ROI index `i` (using `inputs.panel_slices[i]` and associated panel id):
       - Slice `(pid, y0:y1, x0:x1)` to obtain:
         - `data_roi`  = `inputs.target[pid, y, x]`.
         - `model_b0`  = `bragg_before[pid, y, x]`.
         - `model_b1`  = `bragg_after[pid, y, x]`.
         - `sigma_roi` = `inputs.sigma_readout[pid, y, x]` (or broadcast from scalar/panel if needed).
       - Compute variance and Z-score residuals using the same variance model as `dbex.physics.loss._compute_variance_weighted_loss` / `docs/spec-db-core.md`:
         - Treat `model_b*` as `I_model` (Bragg+background prediction) and `data_roi` as `I_obs` (background-subtracted target).
         - Use `sigma_readout` and `sigma_floor` exactly as defined in the spec (detached IRLS denominator with physical clamp) and form `z = (I_obs - I_model) / sqrt(variance)`.
       - Derive per-ROI statistics (e.g., CC before/after using background-aware `_roi_scale_and_corr` logic).
     - Use existing `dbex.vis.plot_triptych` / `plot_z_scores` as the only rendering primitives:
       - For each ROI, emit at least two triptychs into `out_dir`:
         - `roi_{i:03d}_before.png`: `Data | Model_before | Residual Z_before`.
         - `roi_{i:03d}_after.png`:  `Data | Model_after  | Residual Z_after`.
       - Optionally tag titles with HKL / CC if that metadata is cheaply available.
     - Return a list of structured records (e.g., dicts) capturing:
       - ROI index, `(panel_id, bbox)`.
       - Pre/post correlation and any other scalar metrics.
       - Paths to the generated PNGs.

3. **Introduce a reproducible Stage A driver under TOOLING-VIS-001**
   - Add a plan-local driver script, e.g.:
     - `plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs.py`.
   - Script behavior:
     - Load refGeom assets and sigma metadata via existing `dbex.data_load` / `prepare_refinement_inputs`:
       - `refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`, and external sigma manifest if required.
     - Call `simulate_forward_once` to obtain `bragg_before` on the canonical detector.
     - Run `run_nanobrag_refinement` with Stage A enabled, B/C disabled, to obtain `bragg_after` (matching smoke-test settings: CPU, `enable_hkl_interpolation=True`, halo grid).
     - Invoke `dbex.vis.stage_a.emit_stage_a_roi_triptychs(...)` with:
       - A deterministic ROI selection policy (e.g. first `N` ROIs, or top `N` by zero-iteration correlation once affordable).
       - Output directory like:
         - `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom/<timestamp>/`.
     - Write a small `summary.md` (and optionally JSON) in that directory containing:
       - Run metadata (timestamp, git SHA if available, config knobs).
       - ROI table: index, panel, bbox, CC_before, CC_after, PNG paths.

4. **Alignment with TOOLING-VIS-001 roadmap**
   - This session’s work is explicitly framed as:
     - Phase A extension: extending `dbex.vis` with Stage-A-specific ROI helpers that are built on top of `plot_triptych` / `plot_z_scores` and the variance model.
     - A limited Phase B slice: a plan-local driver script under `plans/active/TOOLING-VIS-001/bin/`, not a new public CLI or a parallel plotting stack.
   - Avoid:
     - New matplotlib layouts that bypass `dbex.vis`.
     - New “peak map” visual encodings that compress each ROI into a single detector-pixel and obscure ROI structure.
   - Longer-term integration (outside this session):
     - `dbex/look.py` and `dbex/refine_one.py` can later be refactored to call the `dbex.vis` helpers, reusing the same ROI triptych contract.
     - Smoke/parity tests may adopt these helpers for standardized refinement visuals once the library is stable.
