# Input

- Summary: Begin standardizing the visual diagnostics stack (`dbex.vis`) so smoke/parity runs share a common triptych/Z-score implementation.
- Mode: TDD
- Focus: TOOLING-VIS-001 — Standardize visual diagnostics library
- Branch: integration
- Mapped tests:
  * tests/dbex/test_vis_triptych_smoke.py::test_plot_triptych_smoke
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-21T180000Z/

## Do Now
- Focus Item: TOOLING-VIS-001
- Implement: `dbex/vis/__init__.py, dbex/vis/triptych.py::plot_triptych` — scaffold the `dbex.vis` package and a minimal `plot_triptych(data_roi, model_roi, residual_roi, out_path)` helper that renders a 3-panel triptych (Data | Model | Residual) using `(slow, fast)` indexing and saves a PNG; align layout with `docs/spec-db-vis.md` triptych clauses.
- Implement: `tests/dbex/test_vis_triptych_smoke.py::test_plot_triptych_smoke` — add a small smoke test that builds synthetic `[panel, slow, fast]` arrays, calls `plot_triptych` on a single ROI, and asserts the output PNG exists and has non-zero size.
- Test: `pytest -vv tests/dbex/test_vis_triptych_smoke.py::test_plot_triptych_smoke`

## How-To Map
1. Create the `dbex/vis/` package and an initial `triptych.py` module with a `plot_triptych(data_roi, model_roi, residual_roi, filename)` function that follows the triptych ordering and colormap guidance from `docs/spec-db-vis.md` (Data/Model in grayscale, Residual in diverging colormap).
2. In `tests/dbex/test_vis_triptych_smoke.py`, write a smoke test that constructs small synthetic `data`, `model`, and `residual` arrays (e.g., 1×16×16), calls `plot_triptych` to write to a temporary path, and asserts the file exists and is larger than a minimal byte threshold.
3. Run the mapped pytest node, capture logs under the Artifacts directory, and update `docs/fix_plan.md` Attempts History for TOOLING-VIS-001 with the artifact path and a brief summary of the new helper + test.

Pitfalls To Avoid:
- Do not introduce new plotting dependencies; reuse the existing matplotlib stack only.
- Keep the API surface minimal (one helper function) until later phases; avoid prematurely wiring `dbex.look` or the CLI.
- Ensure all plotting uses `(slow, fast)` ordering and does not transpose arrays implicitly.

If Blocked:
- If imports fail (e.g., missing matplotlib) or tests cannot run, record the minimal error signature in `docs/fix_plan.md` and treat TOOLING-VIS-001 as blocked rather than adding new dependencies.

Findings Applied (Mandatory):
- TOOLING-VIS-001 — Visual diagnostics should share a single triptych implementation and respect Spec DB visualization standards.

Pointers:
- docs/fix_plan.md — TOOLING-VIS-001 ledger row.
- plans/active/TOOLING-VIS-001/implementation.md — full visualization plan.
- docs/spec-db-vis.md — normative triptych/Z-score spec.

Next Up (optional):
- Once the basic triptych helper and smoke test land, extend `dbex/look.py` to call `dbex.vis.plot_triptych` for a single ROI page and add a CLI flag to write a static PNG report.

