# Input for Ralph — Loop 2025-12-06T094500Z

## Summary
Create the missing implementation stub for FINDINGS-LEDGER-002, wire it into the ledger, and rerun the guarded plan inventory so PORTFOLIO-STATUS Phase C can close with zero missing-plan directories.

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
plans/active/PORTFOLIO-STATUS/reports/2025-12-06T120000Z/

## Do Now
1. **Implement: plans/active/FINDINGS-LEDGER-002/implementation.md**  
   - Use `plans/templates/implementation_plan.md` as the skeleton. Summarize the purpose (knowledge-base ledger upkeep), note that the plan currently lacks Goals/Exit Criteria, and include placeholders for Phase breakdown + artifacts path. Cite `docs/fix_plan.md` Plan Inventory appendix so future loops know why this stub exists.  
   - Capture initial status (`pending`) and make it clear that this stub is for documentation/ledger hygiene; no production code scope.
2. **Update docs/fix_plan.md for FINDINGS-LEDGER-002**  
   - Under Tier 1 (Core Physics & Stability) add or refresh the bullet for `FINDINGS-LEDGER-002`, referencing the new implementation plan and its scope (knowledge base maintenance).  
   - In the Plan Directory Inventory appendix keep the new summary counts (56 total, active_missing 32, missing_plan 2) but note that FINDINGS-LEDGER-002 now has an implementation stub so the `missing_plan` bucket should drop back to 1 after rerunning the inventory.  
   - Append a PORTFOLIO-STATUS Attempts History entry describing the stub creation + guard rerun you are doing this loop.
3. **Rerun the guarded inventory + collect artifacts**  
   - Set `REPORT_TS=2025-12-06T120000Z` and run `plan_inventory.py` with the required `--rollup-config` flag, writing outputs into `plans/active/PORTFOLIO-STATUS/reports/$REPORT_TS/`.  
   - Verify `inventory.json` now reports 55 total plans with buckets `{tracked:22, active_missing:32, missing_plan:1}` (ARCH-REFRACTOR-001 is the lone missing-plan stub). Update the appendix summary with the new counts if they differ.  
   - Inspect `rollup_report.md` to confirm each roll-up still shows “Fix-Plan Coverage: ✓ Section exists.”
4. **Capture verification artifacts**  
   - Run `pytest -q plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py` after edits; save the log as `pytest_plan_inventory.log` under the new report directory.  
   - Write `summary.md` in the same directory noting the stub creation, ledger updates, inventory counts, and that the guard/test passed. This Turn Summary must mirror the supervisor’s block.

## How-To Map
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
REPORT_TS=2025-12-06T120000Z

# Create/Update files
$EDITOR plans/active/FINDINGS-LEDGER-002/implementation.md
$EDITOR docs/fix_plan.md

# Guarded inventory + tests
python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py \
  --plans-root plans/active \
  --fix-plan docs/fix_plan.md \
  --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json \
  --out-dir plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/

pytest -q plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py \
  | tee plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/pytest_plan_inventory.log
```

## Pitfalls To Avoid
- Do not skip `--rollup-config`; the script now errors when the guard file is missing or invalid.
- Keep the new stub minimal but structurally complete; don’t invent scope beyond knowledge-base ledger maintenance.
- When editing `docs/fix_plan.md`, append new entries instead of rewriting historical Attempts History rows.
- Ensure the Plan Directory Inventory appendix references the latest artifact path (`2025-12-06T120000Z`) after you rerun the inventory.
- Do not touch any simulator/runtime code—this loop is ledger/doc only.
- Make sure the pytest log and summary land in the new report directory so the automation guard has reproducible evidence.

## If Blocked
- If `plan_inventory.py` fails, capture the full traceback in `plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/plan_inventory_fail.log`, leave docs untouched, and note the failure + error string in `summary.md` so the supervisor can triage.
- If concurrent edits to `docs/fix_plan.md` cause conflicts, stash your appendix changes in `plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/pending_appendix.md`, resolve conflicts separately, and flag the block in the summary with the conflicted sections.

## Findings Applied
No relevant findings in the knowledge base.

## Pointers
- `docs/fix_plan.md:25` — Tier 0 entry + Tier 1 section where FINDINGS-LEDGER-002 must be referenced.
- `docs/fix_plan.md:554` — Plan Directory Inventory appendix (update counts + artifact path after rerun).
- `plans/templates/implementation_plan.md` — template for the new FINDINGS-LEDGER-002 stub.

## Next Up (optional)
1. Once the stub + ledger coverage land, consider marking PORTFOLIO-STATUS Phase C complete and planning the closure checklist.
2. With FINDINGS-LEDGER-002 tracked, reassess the largest active_missing bucket (e.g., DB-AT roll-up) for the next rotation.
