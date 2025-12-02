# Problems Ledger

This file is a lightweight, user-editable backlog for any issues that Galph (the supervisor) should consider during startup. Unlike `user_input.md`, these entries are advisory rather than imperative: Galph reads this file near the start of every loop, decides how to fold the items into `docs/fix_plan.md`, and then updates or removes entries as those problems are scheduled or resolved.

## How to use this file

- Add each problem as a checklist bullet under **Active Items**. Keep descriptions short but concrete.
- Optional sub-bullets can capture additional context, suggested solutions, or blocking dependencies.
- When Galph starts a loop, they will read every entry. If an item results in a plan or is otherwise addressed, Galph will edit the bullet with links/notes or remove it entirely.
- Mark items as completed (`[x]`) when the underlying issue is handled, preferably with a pointer to the fix-plan item, report, or commit that closed it.
- Feel free to leave this file empty; it exists only when you have additional guidance or ad-hoc requests that do not belong in `user_input.md`.

## Active Items

- [ ] **Architectural Code Smells — overlapping legacy/new refinement paths**
  - *A. “Lava Flow” migration state:* `dbex/nanobrag_refinement.py` still owns monolithic orchestration (stage_a_only_mode / stage_a_b_mode / else) while the new `refinement/engine.py` + stage modules exist. Legacy code imports helpers from the new stage implementations, so neither path can be removed independently.
    - Violations: Open/Closed Principle (new stages require touching the orchestrator); tangled dependency graph prevents deleting legacy modules.
  - *B. Circular dependencies & lazy imports:* `_lazy_import_refinement()` in `dbex/refinement/stage_a.py`, TYPE_CHECKING hacks in `dbex/refinement/helpers.py`, and lazy imports in `dbex/refinement/stage_c.py` show pervasive circular-dependency mitigation. Hides the real dependency graph and causes late ImportErrors.
  - *C. “Test-only” logic shipped in prod:* `dbex/physics/forward.py::simulate_forward_torch` is labeled TEST-ONLY yet coexists with production closures, implying duplicate implementations that can drift.
  - *Design pattern violations:* dictionaries impersonate typed objects (`_build_stage_a_params`), long parameter lists (14–17 args) in `_build_stage_a_lbfgs_closure` / `_run_stage_c_lbfgs`, and “god functions” inside `_impl` modules that wrap hundreds of lines/closures, making telemetry or memory debugging painful.
  - *Implementation smells:*
    - Hardcoded physics constants (`max_angle_delta = 10.0`, `max_orientation_deg = 3.0`) buried in `stage_a_impl.py` instead of `RefinementConfig`.
    - I/O modules doing optimization (`dbex/io/writer.py::write_torch_outputs` launches Nelder–Mead scoring).
    - Mutable default state hacks (`telemetry_step_counter = [0]`) and broad exception swallowing in `dbex/vis/mapping.py`.
  - *Performance smells:* repeated `.item()` syncs inside loops (`stage_a_impl.py`) and re-instantiating heavy tensors/configs inside Stage C fallback loops.
  - *Recommendations:* consolidate physics/loss paths, enforce `RefinementContext` as the hand-off object, convert stages into classes (stateful telemetry), move Nelder–Mead scoring into refinement/physics modules, and centralize hardcoded constraints in `RefinementConfig`.
  - 2025-12-01: Scheduled Stage wrapper import cleanup under ARCH-REFINE-001 Phase F to remove `_lazy_import_refinement` and lazy `run()` imports (see docs/fix_plan.md entry at 2025-12-01T232800Z).

- [ ] _(Add new problems here. Galph will remove or rewrite entries as they are scheduled or resolved.)_
