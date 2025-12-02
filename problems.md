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
