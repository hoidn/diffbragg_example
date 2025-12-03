# Input for Ralph — Loop 2025-12-05T235500Z

## Summary
Finalize PORTFOLIO-STATUS Phase B3 by syncing `docs/fix_plan.md` and the implementation plan with the 2025-12-05 inventory run, then capture a fresh artifact/summary so Phase C (automation guard + exit) can start cleanly.

## Mode
Docs

## InitiativeType
housekeeping

## Focus
PORTFOLIO-STATUS — Plan/Fix-Plan synchronization & archive hygiene

## Branch
integration

## Mapped tests
pytest -q plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py

## Artifacts
plans/active/PORTFOLIO-STATUS/reports/2025-12-05T235500Z/

## Do Now

1. **Regenerate the inventory + roll-up artifacts for tracking**  
   - Set `REPORT_TS=2025-12-05T235500Z` (keep this literal so the ledger references stay deterministic).  
   - Run `python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py --plans-root plans/active --fix-plan docs/fix_plan.md --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json --out-dir plans/active/PORTFOLIO-STATUS/reports/$REPORT_TS/`.  
   - Verify the new `rollup_report.md` shows every roll-up with “Fix-Plan Coverage: ✓ Section exists” and that `inventory.json` still reports 55 total plans with buckets `{tracked:21, active_missing:33, missing_plan:1}`. Leave the generated `inventory_missing.md`/`notes.md` alongside it.

2. **Update `docs/fix_plan.md` with Phase B3 completion + updated appendix**  
   - In the Tier 0 entry (see `docs/fix_plan.md:25`), replace the “Phase B3 in progress” text with a summary of the completed roll-up automation (artifact `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T210000Z/`) and spell out the Phase C focus (embedding automation guard + prepping exit criteria).  
   - In the Plan Directory Inventory appendix (starts near `docs/fix_plan.md:560`):
     * Change “Latest Report” to `2025-12-05T235500Z` and point “Artifacts”/“Roll-up Report” at the new directory.  
     * Update the Summary bullets to the current counts (55 total, 21 tracked ≈38%, 33 active_missing ≈60%, 1 missing_plan ≈2%) and call out that active_missing+missing_plan = 34 untracked initiatives.  
     * Refresh the bucket table text and ensure the automation guard command still shows the `--rollup-config` flag.  
   - Append a Attempts History entry under `### [PORTFOLIO-STATUS] Attempts History` describing the 2025-12-05T210000Z run (script/test outputs + doc edits) and reference the new artifact path plus the pytest log you’ll capture this loop.

3. **Align the implementation plan with the ledger**  
   - Edit `plans/active/PORTFOLIO-STATUS/implementation.md` so Phase B3 explicitly notes the 2025-12-05 roll-up automation + test run (retain prior timestamps for history), and add a short Phase C paragraph that lists the remaining guard-rail work (Working Agreements update + plan-archive hygiene).  
   - Mention the new artifact directory in the Phase B3 notes so future loops can trace the evidence without cross-checking older runs.

4. **Capture the loop summary + verification**  
   - Add `summary.md` under `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T235500Z/` describing the doc updates, refreshed counts, pytest selector result, and next Phase C steps (this will mirror the Turn Summary).  
   - Run `pytest -q plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py` after editing to prove the script/test harness stayed green; stash the log in the same report directory.

## How-To Map
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
REPORT_TS=2025-12-05T235500Z

python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py \
  --plans-root plans/active \
  --fix-plan docs/fix_plan.md \
  --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json \
  --out-dir plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/

pytest -q plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py \
  | tee plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/pytest_plan_inventory.log
```

## Pitfalls To Avoid
- Pull counts straight from the freshly generated `inventory.json`; do not hand-edit numbers or forget the single `missing_plan` bucket.
- Keep Tier 0 prose scoped to PORTFOLIO-STATUS; do not reword statuses for other initiatives.
- When editing the appendix, avoid reflowing archived Attempts History—append instead of rewriting prior bullets.
- Do not delete or rename existing report directories; just add the new timestamped set.
- Ensure the pytest log and summary live under the new report directory so automation can reference them later.
- Keep changes limited to docs/plan directories; no simulator or CLI code should be touched during this loop.

## If Blocked
- If `plan_inventory.py` fails, leave docs untouched, capture `plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/plan_inventory_fail.log` with the full traceback, and note the failure plus observed error string in `summary.md`.
- If concurrent edits to `docs/fix_plan.md` conflict, park your updated appendix text in `plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/pending_appendix.md`, resolve the conflict separately, and flag the block in the summary so the supervisor can requeue the doc merge.

## Findings Applied
No relevant findings in the knowledge base for this scope.

## Pointers
- `docs/fix_plan.md:25` — Tier 0 entry for PORTFOLIO-STATUS (needs status/attempts refresh).
- `docs/fix_plan.md:560` — Plan Directory Inventory appendix to update with the new inventory run.
- `plans/active/PORTFOLIO-STATUS/implementation.md:1` — Phase breakdown requiring Phase B3/Phase C alignment.

## Next Up (optional)
1. After Phase C guardrails land, consider marking PORTFOLIO-STATUS ready for closure or hand the refreshed ledger to ARCH-REFACTOR-001 to unblock Phase D.3.
2. Revisit DB-AT roll-up sections to start filling in member-plan status rows once the appendix is stable.
