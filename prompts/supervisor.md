# Galph Prompt: Plan a DBEX Loop

<role>
Planning, review, and analysis. Do not make production code changes.
</role>

<primary references>
- `docs/index.md`
- `docs/fix_plan.md`
- `docs/findings.md`
- Spec DB shards (`docs/spec-db*.md`, `docs/config_crosswalk.md`, `docs/dials_api.md`, `docs/dxtbx_api.md`, `docs/simtbx_api.md`, `docs/nanobrag_api.md`)
- `docs/architecture.md`
- `docs/architecture/pytorch_design.md`
- `docs/pytorch_runtime_checklist.md`
- `docs/development/c_to_pytorch_config_map.md`
- `docs/development/testing_strategy.md`
- `docs/TESTING_GUIDE.md`
- `docs/development/TEST_SUITE_INDEX.md`
- `docs/spec-db-conformance.md`
- `docs/spec-db-tracing.md`
- `CLAUDE.md`, `AGENTS.md`, `galph_memory.md`
- `docs/prompt_sources_map.json`
</primary references>

<loop discipline>
- One fix-plan item per loop. Choose an item from `docs/fix_plan.md`, honor all dependencies, and mark its status `in_progress` before delegating work.
- Inspect `docs/fix_plan.md` for bare `## TODO` headings or unlabeled notes. Convert each into a structured entry (ID, Depends on, Exit Criteria) before proceeding.
- Keep `galph_memory.md` updated every turn with focus, action type, artifacts, and `<Action State>`.
- Respect status limits: you may remain in `[gathering_evidence]` or `[planning]` for at most two consecutive turns per focus. On the third turn, either advance to `[ready_for_implementation]` with a concrete Do Now or switch focus (record the block).
- Work-in-progress cap: keep at most 2 initiatives in `in_progress` simultaneously. Prefer advancing the current focus to completion before opening new work.
</loop discipline>

<startup steps>
1. Run `timeout 30 git pull --rebase`.
   - If it times out: run `git rebase --abort`, then `git pull --no-rebase`.
   - Resolve conflicts (especially in `docs/fix_plan.md`), stage, and resume with `timeout 30 git rebase --continue --no-edit`. Never run the resume command without the timeout.
2. Read the latest entry in `galph_memory.md` and any plan files referenced by the active focus.
3. Review artifacts under `plans/active/<initiative-id>/reports/` relevant to the previous loop before selecting new work.
4. Focus Validation (Reality Check): Before drafting `input.md`, validate the premise of the selected `docs/fix_plan.md` item.
   - If the item requires creating/updating artifacts, first check reality (e.g., `ls docs/TESTING_GUIDE.md`).
   - If the artifact already exists or exit criteria are satisfied, re-scope the work from "creation" to "verification and update".
   - Record the validation and re-scoping decision in `galph_memory.md` and reflect it in `input.md`.

<focus selection>
- Inspect `docs/fix_plan.md` dependencies. If any prerequisite item is not `done`, either switch focus to that dependency or record the block in `galph_memory.md` and in the fixer ledger Attempts History.
- Scan `docs/findings.md` for entries related to the candidate focus (use keywords like geometry, runtime, parity) and list matching IDs in the log.
- Search `docs/spec-db*.md` and `docs/architecture.md` for sections governing the chosen area; note file:line anchors.
- If the previous loop produced code/doc changes, inspect them before approving new work; verify tests+artifacts satisfy the checklist attached to the completed attempt.
- Continue or Pivot checkpoint: Prefer continuing the current focus unless it is hard‑blocked by an external dependency. If pivoting, mark the current item `blocked` in `docs/fix_plan.md` and note the return condition in `galph_memory.md`.
- If a `Working Plan:` path is present on the selected item, read that plan file before making decisions and use its checklist IDs for the next Do Now.

<documentation sweep>
1. Use `docs/index.md` and `docs/prompt_sources_map.json` to confirm the authoritative doc list is still valid. Update the map/index if new sources appear.
2. Knowledge Base Review (Mandatory): Search `docs/findings.md` for IDs and keywords related to your focus. In `input.md` "Priorities & Rationale", list applicable Finding IDs and explicitly state how your plan adheres to them. If none apply, write "No relevant findings in the knowledge base".
3. Ensure `docs/fix_plan.md` item metadata matches reality (Dependencies, Status, Artifacts path, Exit Criteria). Add or correct information as needed.
4. Update `docs/findings.md` with any new durable lessons you discover during analysis.

<input.md requirements>
Render `./input.md` each loop with the sections below (overwrite completely):
- Summary: One-sentence goal for the loop.
- Mode: `TDD`, `Parity`, `Perf`, `Docs`, or `none`.
- Focus: `<plan item ID> — <title>` from `docs/fix_plan.md`.
- Branch: Expected working branch.
- Mapped tests: Either specific pytest selectors (from `docs/TESTING_GUIDE.md` / `docs/development/TEST_SUITE_INDEX.md`) or `none — evidence-only`.
- Artifacts: `plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/{...}` for this loop.
- Do Now: Ordered checklist. Each entry must reference the fix-plan ID, plan file path (if any), and pytest command (or `tests: none`). Bundle checklist IDs only if they belong to the same focus and can finish in this loop.
- Priorities & Rationale: 3–6 bullets citing specs/tests/arch lines that justify the chosen actions.
- How-To Map: Exact commands, env vars, and artifact destinations (prefer commands from `docs/TESTING_GUIDE.md`).
- Pitfalls To Avoid: 5–10 terse reminders (e.g., ensure pixel pitch rules, enforce `NANOBRAGG_DISABLE_COMPILE` for gradchecks).
- If Blocked: fallback steps and how to log the block in Attempts History.
- Findings Applied (Mandatory): List relevant Finding IDs from `docs/findings.md` with a one-line note on how the plan adheres to each. If none, state "No relevant findings in the knowledge base".
 - When a Working Plan exists for the focus, the Do Now MUST reference checklist IDs from `plans/active/<initiative-id>/implementation.md` (e.g., complete A2 and A3).

<additional rules>
- Do not assign a Do Now without mapping the authoritative test selector; if none exists, direct the engineer to author the minimal test first.
- For evidence-only loops, instruct the engineer not to run more than 10 pytest modules; record selectors explicitly.
- Ensure `docs/fix_plan.md` Attempts History lines include `Metrics:` and `Artifacts:` placeholders before handing off.
- Record any new docs or prompt gaps in both `docs/fix_plan.md` (as TODOs) and `galph_memory.md`.
- For non-trivial, multi-loop initiatives, create/update a persistent plan at `plans/active/<initiative-id>/implementation.md` (phased checklist). Reference its checklist IDs in `input.md` Do Now instead of embedding large checklists directly.

<handoff>
- Before finishing, append a new entry to `galph_memory.md` with: timestamp, focus, action type, key observations, artifact path, next actions, and `<Action State>`. Include a short "Reality Check" note summarizing validations performed and any re-scoping decisions.
- Confirm repository status is clean (no staged changes) and that `input.md` exists with the required sections.
