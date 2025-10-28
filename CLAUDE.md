# CLAUDE.md — Agent Operating Guide for DBEX

## Required Reading (in order)
1. `docs/index.md` — discover current specs, workflows, ledgers, and reports.
2. `docs/fix_plan.md` — select a single active item and honor dependencies before starting work.
3. `docs/findings.md` — review prior lessons, guardrails, and parity caveats.
4. Spec DB shards required for the chosen focus (`docs/spec-db*.md`, `docs/config_crosswalk.md`, `docs/dials_api.md`, `docs/dxtbx_api.md`, `docs/simtbx_api.md`, `docs/nanobrag_api.md`).
5. Architecture & runtime guidance: `docs/architecture.md`, `docs/pytorch_runtime_checklist.md`.
6. Testing references: `docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`, `docs/spec-db-conformance.md`.
7. Debugging & tracing: `docs/spec-db-tracing.md`.

## Loop Roles
- **Supervisor (Galph)** uses `prompts/supervisor.md` to plan each loop, update `galph_memory.md`, and emit `input.md` with a single focus.
- **Engineer (Ralph)** uses `prompts/main.md` (or `prompts/debug.md` for parity loops) to implement the Do Now checklist and update ledgers/artifacts.

## Core Rules
- One fix-plan item per loop; mark status → `in_progress` at start, append Attempts History with `Metrics:` & `Artifacts:` lines at end.
- Artifact policy: write outputs to `plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/`; include logs/metrics summaries.
- Always run `git pull --rebase` with a 30s timeout before selecting work; abort/retry per prompt instructions if conflicts occur.
- Tests run via `pytest` only. Respect selectors in `docs/TESTING_GUIDE.md`; if a required selector is missing, author it or record a TODO in the ledger before proceeding.
- Prefer editable install (`pip install -e .`) and avoid modifying `sys.path` in code or tests.
- For debugging/parity, follow `prompts/debug.md`: capture first divergence, metrics (correlation, MSE, RMSE, max|Δ|, sum ratio), and diff heatmaps.
- Update `docs/findings.md` when you learn a durable lesson not already recorded.
- Keep `docs/index.md` in sync with new ledgers/docs so prompts remain discoverable.

## Safety & External Trees
- External tool mirrors: `dials/`, `dxtbx/`, `cctbx_project/simtbx/`. Treat them as read-only unless the plan explicitly targets them.
- Do not commit runtime artifacts or large binaries; ensure `.gitignore` covers scratch data.
- Respect AGENTS.md overrides for any subdirectory you modify (none beyond root today).

