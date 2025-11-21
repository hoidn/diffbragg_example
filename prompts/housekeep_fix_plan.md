# Prompt: Fix Plan Housekeeping

Use this prompt when the fix plan ledger (`docs/fix_plan.md`) has become unwieldy or stale. The goal is to reduce noise while preserving all actionable initiatives and historical context as required by the supervisor rules.

## Scope
- Keep **all active and pending initiatives** (sections under `## Active Initiatives`) intact, including their exit criteria and Attempts History.
- Move legacy/done initiatives and long-form attempts to `docs/fix_plan_archive.md` (create if missing) instead of deleting them.
- Update the "Last Updated" timestamp and ensure every surviving initiative cites the latest artifact path.

## Procedure
1. **Snapshot the current ledger:**
   - `cp docs/fix_plan.md docs/fix_plan_archive.md` (append or merge if the archive already exists).
2. **Edit `docs/fix_plan.md`:**
   - Remove/trim only the sections for completed or archived initiatives that are no longer relevant to current loops.
   - Ensure active/pending initiatives retain full detail (Working Plan, Attempts History, artifact paths).
   - Update the "Last Updated" date and add a note pointing to the archive for historical entries.
3. **Verify references:**
   - Check that each remaining initiative points to an existing plan (`plans/active/<id>/implementation.md`) and that artifact paths are valid.
4. **Commit with context:**
   - Reference the housekeeping goal in the commit message (e.g., `docs: housekeep fix plan ledger`).

## Tips
- When in doubt, preserve more detail—never drop active work.
- Mention in the updated ledger that older attempts live in `docs/fix_plan_archive.md` so future readers know where to find history.
- If multiple initiatives are blocked by the same dependency, summarize that once to avoid repetition.
