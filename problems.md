# Problems Ledger

This file is a lightweight, user-editable backlog for any issues that Galph (the supervisor) should consider during startup. Unlike `user_input.md`, these entries are advisory rather than imperative: Galph reads this file near the start of every loop, decides how to fold the items into `docs/fix_plan.md`, and then updates or removes entries as those problems are scheduled or resolved.

## How to use this file

- Add each problem as a checklist bullet under **Active Items**. Keep descriptions short but concrete.
- Optional sub-bullets can capture additional context, suggested solutions, or blocking dependencies.
- When Galph starts a loop, they will read every entry. If an item results in a plan or is otherwise addressed, Galph will edit the bullet with links/notes or remove it entirely.
- Mark items as completed (`[x]`) when the underlying issue is handled, preferably with a pointer to the fix-plan item, report, or commit that closed it.
- Feel free to leave this file empty; it exists only when you have additional guidance or ad-hoc requests that do not belong in `user_input.md`.

## Active Items

- [x] **Architectural Code Smells — overlapping legacy/new refinement paths** — Resolved via ARCH-REFINE-001 Phase F (2025-12-01T232800Z) by removing `_lazy_import_refinement`, hoisting Stage A/B/C helper imports to module scope, and documenting explicit dependencies so the RefinementEngine path no longer masks circular imports (see docs/fix_plan.md §2025-12-01T232800Z and telemetry in `plans/active/ARCH-REFINE-001/reports/2025-12-01T232800Z/`).

- [ ] _(Add new problems here. Galph will remove or rewrite entries as they are scheduled or resolved.)_
- [ ] **Stage contexts / engine artifact boundary (from 2025-12-01 design review)** — `ARCH-STAGE-CONTEXT-001` (docs/fix_plan.md) now tracks items 1, 2, 4, 7, and 8 from the review: helper data clumps, anemic Stage classes, mutable telemetry dicts, and engine branches that peek into stage-specific keys. Goal: add typed `RefinementSharedContext`/`StageArtifacts`, move LBFGS state into Stage classes, and let the engine/writer share artifacts without bespoke dict spelunking. Workflows: see `plans/active/ARCH-STAGE-CONTEXT-001/`.
- [ ] **Writer / bridge responsibility split** — Outstanding review items 3 and 5: `dbex/io/writer.py::write_torch_outputs` still runs Nelder–Mead to compute `opt_bragg_scale`, and `dbex/nanobrag_bridge.py` remains a “god object” that mixes data prep, calibration loading, simulator execution, and physics helpers. Need follow-up initiative to relocate scaling checks into analysis tooling and split bridge responsibilities across factories/physics modules.
- [ ] **Lazy imports / process noise** — Outstanding review items 6 and 9: several modules (`dbex/geometry/crystallography.py`, `dbex/physics/forward.py`, Stage helpers) still use pervasive lazy imports that hide dependencies, and code is saturated with historical ticket references. Requires a hygiene push once the architecture work above is stable.
