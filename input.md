# Input for Ralph — Loop 2025-12-05T150000Z

## Summary
Execute Phase B remediation for PORTFOLIO-STATUS: archive the ARCH-REFRACTOR-001 duplicate and create implementation.md stubs for the five directories that presently have no plan so future ledger entries have concrete anchors.

## Mode
Docs

## InitiativeType
housekeeping

## Focus
PORTFOLIO-STATUS — Plan/Fix-Plan synchronization & archive hygiene

## Branch
integration

## Mapped tests
none — docs-only

## Artifacts
plans/active/PORTFOLIO-STATUS/reports/2025-12-05T150000Z/

## Do Now

1. **Archive ARCH-REFRACTOR-001 duplicate**  
   - Move the contents of `plans/active/ARCH-REFRACTOR-001/` into `archive/plans/ARCH-REFRACTOR-001/` (preserve subdirectories/reports), then replace the active directory with a short `README.md` that points to `ARCH-REFACTOR-001` and notes the archive timestamp.  
   - Update `docs/fix_plan_archive.md` with a brief note linking to the archived path and referencing the PORTFOLIO-STATUS artifact directory.  
   - Record the move in `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T150000Z/archival_notes.md` (bullet list describing what moved and why).

2. **Author minimal implementation.md stubs for stub directories**  
   - For each of the following directories, add (or replace) `implementation.md` with the template header + two-sentence status summary so the ledger can reference a real plan: `plans/active/HARDEN-SUBMODULE-ROBUSTNESS/`, `plans/active/ORCH-CLAUDE-PATH-FIX-001/`, `plans/active/ORCH-CLI-FALLBACK-001/`, `plans/active/ORCH-ROBUST-001/`, `plans/active/SUPERVISOR/`.  
   - Each stub should include Goal/Non-Goal bullets and clearly state whether the initiative is pending or should be archived later; cite `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T150000Z/classification.md` so we know how it was categorized.  
   - Capture a short `stub_status.md` table under the artifact directory summarizing which plans received stubs and any follow-up needed.

3. **Update ledgers**  
   - In `docs/fix_plan_archive.md`, append a reference to the new archive move.  
   - In `docs/fix_plan.md` Attempts History for PORTFOLIO-STATUS, add a short note pointing to the archival/stub artifacts (this keeps the ledger synchronized with the on-disk changes).

## How-To Map
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
# 1. Archive duplicate plan
mkdir -p archive/plans/ARCH-REFRACTOR-001
rsync -a plans/active/ARCH-REFRACTOR-001/ archive/plans/ARCH-REFRACTOR-001/
rm -rf plans/active/ARCH-REFRACTOR-001
mkdir -p plans/active/ARCH-REFRACTOR-001
cat <<'MD' > plans/active/ARCH-REFRACTOR-001/README.md
# ARCH-REFRACTOR-001 (duplicate)
Archived on 2025-12-05T150000Z — see archive/plans/ARCH-REFRACTOR-001 for history.
Refer to ARCH-REFACTOR-001 for the active plan.
MD

# 2. Implementation stubs (repeat for each ID)
for id in HARDEN-SUBMODULE-ROBUSTNESS ORCH-CLAUDE-PATH-FIX-001 ORCH-CLI-FALLBACK-001 ORCH-ROBUST-001 SUPERVISOR; do
  cat plans/templates/implementation_plan.md > plans/active/$id/implementation.md
  printf '\n_Status:_ pending — stub created 2025-12-05T150000Z per PORTFOLIO-STATUS classification.\n' >> plans/active/$id/implementation.md
done

# 3. Capture notes
cat <<'MD' > plans/active/PORTFOLIO-STATUS/reports/2025-12-05T150000Z/archival_notes.md
- ARCH-REFRACTOR-001 moved under archive/plans/ARCH-REFRACTOR-001/ (duplicate of ARCH-REFACTOR-001)
MD
cat <<'MD' > plans/active/PORTFOLIO-STATUS/reports/2025-12-05T150000Z/stub_status.md
| Plan ID | Action |
| --- | --- |
| HARDEN-SUBMODULE-ROBUSTNESS | implementation.md stub added |
| ORCH-CLAUDE-PATH-FIX-001 | implementation.md stub added |
| ORCH-CLI-FALLBACK-001 | implementation.md stub added |
| ORCH-ROBUST-001 | implementation.md stub added |
| SUPERVISOR | implementation.md stub added |
MD
```

## Pitfalls To Avoid
- Keep archived content intact—use rsync/cp so historical reports remain untouched before removing the active directory.
- The README in `plans/active/ARCH-REFRACTOR-001/` should clearly state that the real plan is ARCH-REFACTOR-001; do not leave the directory empty.
- When creating implementation stubs, include enough context (goal + current status) to make future ledger work actionable—empty templates without notes do not satisfy the requirement.
- Do not touch production code or simulator trees; this loop is docs/plan maintenance only.
- Make sure both `docs/fix_plan.md` and `docs/fix_plan_archive.md` point at the new artifacts so future loops can trace the changes.

## If Blocked
- If any directory move fails (permissions, unexpected files), log the exact error in `archival_notes.md` and keep the directory unchanged; notify Galph before retrying.
- If a template copy overwrites valuable content, stop immediately, restore from `git`/backup, and record the incident in `stub_status.md`.

## Findings Applied
No relevant findings in the knowledge base.

## Pointers
- `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T150000Z/classification.md` — bucketed plan listing referenced above.
- `docs/fix_plan.md:320` — Plan Directory Inventory appendix that must reflect archive/stub work after edits.

## Next Up
1. After this remediation, continue Phase B by archiving or reviving any remaining stale directories (e.g., ORCH-* if they remain inactive).  
2. Begin wiring the new Tier 1 roll-up entries into concrete fix-plan rows with status metadata once the plan stubs exist.
