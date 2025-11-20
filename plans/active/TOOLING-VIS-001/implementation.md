# TOOLING-VIS-001 — Standardized Visual Diagnostics

## Initiative
- ID: TOOLING-VIS-001
- Title: Standardize Visual Diagnostics (Z-Scores & Triptychs)
- Status: pending

## Goals
- Implement the visual standards defined in `docs/spec-db-vis.md`.
- Replace ad-hoc plotting scripts with a reusable library `dbex.vis`.
- Ensure visual artifacts (PNGs) are generated automatically by the CLI for rapid verification.

## Exit Criteria
1. `dbex.vis` module exists and implements `plot_triptych` and `plot_z_scores` matching the Spec.
2. `dbex/look.py` is refactored to use `dbex.vis` (removing hardcoded layouts).
3. `refine_one.py` (CLI) generates a summary PNG report at the end of refinement.
4. Visuals correctly handle `(slow, fast)` coordinates and use diverging colormaps for residuals.

## Spec Alignment
- **Normative Spec:** `docs/spec-db-vis.md`
- **Key Clauses:**
    - Coordinate Systems: `(slow, fast)` origin top-left.
    - Triptych Layout: `[Data | Model | Residual]`.
    - Residual Definition: Z-score `(Data - Model) / sqrt(Variance)`.

## Phase A — Library Implementation
### Checklist
- [ ] A1: Create `dbex/vis/` package.
- [ ] A2: Implement `triptych.py`: Standard layout, shared colormaps.
- [ ] A3: Implement `residuals.py`: Z-score calculation (requires variance input).

## Phase B — Integration
### Checklist
- [ ] B1: Refactor `dbex/look.py` to consume `dbex.vis`.
- [ ] B2: Update `dbex/refine_one.py` to generate a static report on exit.

## Artifacts Index
- Reports root: `plans/active/TOOLING-VIS-001/reports/`
