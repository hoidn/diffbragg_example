# CLAUDE.md — Agent Operating Guide for DBEX

## Required Reading (in order)
1. `docs/index.md` — discover current specs, workflows, ledgers, and reports.
2. `docs/fix_plan.md` — select a single active item and honor dependencies before starting work.
3. `docs/findings.md` — review prior lessons, guardrails, and parity caveats.
4. Spec DB shards required for the chosen focus (`docs/spec-db*.md`, `docs/config_crosswalk.md`, `docs/dials_api.md`, `docs/dxtbx_api.md`, `docs/simtbx_api.md`, `docs/nanobrag_api.md`).
5. Architecture & runtime guidance: `docs/architecture.md`, `docs/pytorch_runtime_checklist.md`.
6. Testing references: `docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`, `docs/spec-db-conformance.md`.
7. Debugging & tracing: `docs/spec-db-tracing.md`.

## Environment Quick Reference (README.md)
- Initialize the toolchain via `source setup_env.sh` (automates README steps 1–3).
- The simtbx env must retain `torch==2.4.1+cu121` and `torchvision==0.19.1+cu121`; do **not** upgrade unless a plan explicitly directs it.
- Baseline DiffBragg run (README Step 7): `DIFFBRAGG_USE_CUDA=1 python -m dbex.refine_one -e refGeom.expt -r refGeom.refl -i 0 -o dbex_0000_0.h5 -m 747_mask.pkl -z scaled.mtz`.
- Full setup/benchmark details live in `README.md`; treat it as the authoritative walkthrough for environment resets.

## Loop Roles
- **Supervisor (Galph)** uses `prompts/supervisor.md` to plan each loop, update `galph_memory.md`, and emit `input.md` with a single focus.
- **Engineer (Ralph)** uses `prompts/main.md` (or `prompts/debug.md` for parity loops) to implement the Do Now checklist and update ledgers/artifacts.

## FSM Quick Reference
- States: `gathering_evidence`, `planning`, `ready_for_implementation`.
- Dwell rule: remain in `gathering_evidence` or `planning` at most two consecutive turns per focus; on the third turn, either move to `ready_for_implementation` with an executable Do Now or switch focus and record the block.
- Logging: supervisor appends `focus`, `state`, `dwell`, `artifacts`, and `next_action` to `galph_memory.md` at the end of every turn; engineer respects the current state and only executes code when `ready_for_implementation`.
- Reference: see `prompts/fsm_analysis.md` (states/transitions) and `prompts/supervisor.md` (enforcement and required logging).

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
- Respect AGENTS.md overrides in deeper directories (none beyond root today); this document serves as the root-level source.

---

## Repository-Scoped Rules (AGENTS.md)

### Scope & Precedence
- Applies to the entire `diffbragg_example/` tree.
- Future AGENTS.md files in subdirectories override these rules within their scope.
- Direct user/developer instructions supersede AGENTS.md.

### Coding & Documentation Conventions
- Follow the style already present in `dbex/` modules; prefer clear tensor operations and explicit parameter passing.
- Keep simulator/bridge logic aligned with Spec DB requirements (`docs/spec-db-*.md`). Cite the shard you implemented in commit messages when possible.
- Update documentation (`docs/`) when behavior, workflows, or commands change; maintain `docs/index.md` as the authoritative map.

### Testing Policy
- Primary framework: `pytest`.
- Author new tests in native pytest style (functions/fixtures). Do not mix with `unittest.TestCase` unless editing legacy code that already uses it.
- Respect selectors defined in `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md`. If a selector is missing, add a TODO plus rationale to `docs/fix_plan.md` before marking work complete.
- Gradient/torch tests must export `KMP_DUPLICATE_LIB_OK=TRUE`; gradient checks additionally require `NANOBRAGG_DISABLE_COMPILE=1`.

### Artifact & Ledger Policy
- Store loop artifacts under `plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/`.
- Reference artifact paths in `docs/fix_plan.md` Attempts History entries.
- Findings with lasting value belong in `docs/findings.md` (include `source:path:line`).

### External Tool Trees (read-only unless instructed)
- DIALS: `./dials/`
- dxtbx: `./dxtbx/`
- simtbx: `./cctbx_project/simtbx/`
