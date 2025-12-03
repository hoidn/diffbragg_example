# Input for Ralph — Loop 2025-12-08T190000Z

## Summary
Close PORTFOLIO-STATUS by marking the Tier 0 ledger/plan/problems ledger as done and capturing a fresh plan-inventory guard run so the final artifacts reflect the 100% coverage snapshot from 2025-12-07T220000Z.

## Mode
Docs

## InitiativeType
housekeeping

## Focus
PORTFOLIO-STATUS — Plan/Fix-Plan synchronization & archive hygiene

## Branch
integration

## Mapped tests
pytest -vv plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py

## Artifacts
plans/active/PORTFOLIO-STATUS/reports/2025-12-08T190000Z/

## Do Now
1. **Implement: docs/fix_plan.md::Tier 0 entry + Plan Directory Inventory**  
   - Change the PORTFOLIO-STATUS Tier 0 bullet from “in_progress (Phase F …)” to **done**, summarizing that Phases A–F completed and citing the final inventory at `plans/active/PORTFOLIO-STATUS/reports/2025-12-07T220000Z/`.  
   - Refresh the Attempts History with a new 2025-12-08T190000Z line describing this closure loop and pointing at the new artifact path below.  
   - Update the “Plan Directory Inventory” appendix header so “Latest Report” references 2025-12-07T220000Z (or the new run you capture in step 3), and rewrite the Summary/Bucket sections with the canonical counts (Total=55, Tracked=28, Covered via rollups=34, Active missing=0, Missing plan=0). Keep the guard command block unchanged aside from the timestamp.  
   - Ensure Working Agreements still emphasize the `--rollup-config` flag.
2. **Implement: plans/active/PORTFOLIO-STATUS/implementation.md::Status + Closure**  
   - Set `Status:` to `done` in the header.  
   - Fold the Closure narrative (the paragraph that starts “All Exit Criteria satisfied…”) into the “Phase F” section and cite the same final artifact path so the plan matches the ledger text.  
   - Remove any lingering “Phase F in progress” language so the plan header, phase breakdown, and closure section align.
3. **Implement: problems.md::Active Items**  
   - Edit the free-form directive under “ATTN NEW PROBLEMS” so it records that the stale-plan inventory/archival drive is resolved via PORTFOLIO-STATUS (refer to docs/fix_plan.md Tier 0 entry).  
   - If you prefer, convert that note into a checked `[x]` bullet linking to the fix-plan line so the ledger now has a historical pointer and the “Active Items” list goes back to empty.
4. **Run + capture guard artifacts**  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py --plans-root plans/active --fix-plan docs/fix_plan.md --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json --out-dir plans/active/PORTFOLIO-STATUS/reports/2025-12-08T190000Z/ | tee plans/active/PORTFOLIO-STATUS/reports/2025-12-08T190000Z/plan_inventory.log`  
   - Copy the generated `inventory.json`, `inventory_missing.md`, and `rollup_report.md` into that directory.  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py | tee plans/active/PORTFOLIO-STATUS/reports/2025-12-08T190000Z/pytest_plan_inventory.log`  
   - Drop a short `summary.md` noting that the guard/tests were re-run post-closure.

## How-To Map
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export REPORT_TS=2025-12-08T190000Z
mkdir -p plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}

$EDITOR docs/fix_plan.md
$EDITOR plans/active/PORTFOLIO-STATUS/implementation.md
$EDITOR problems.md

python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py \
  --plans-root plans/active \
  --fix-plan docs/fix_plan.md \
  --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json \
  --out-dir plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/ \
  | tee plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/plan_inventory.log

pytest -vv plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py \
  | tee plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/pytest_plan_inventory.log
```

## Pitfalls To Avoid
- Keep scope limited to docs/plan/problems; do **not** touch production src modules.  
- When editing markdown tables or bullet lists, preserve spacing so rendered layout stays intact.  
- Do not hardcode new plan counts manually—pull them from the freshly generated `inventory.json`.  
- Ensure the guard command includes `--rollup-config`; the automation now fails fast if it’s omitted.  
- Capture every log/artifact (inventory + pytest) under `plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/` so the ledger can cite them.  
- Leave historical Attempts History entries untouched—only append the new closure note.  
- If adjusting `problems.md`, make sure no duplicate unchecked entries remain for the same topic.

## If Blocked
- If the guard script or pytest fails, stop, save the console output to `plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/failure.log`, and record the blocker in both `docs/fix_plan.md` Attempts History and `plans/active/PORTFOLIO-STATUS/implementation.md`.  
- If doc edits uncover merge conflicts (e.g., someone else already edited Tier 0), keep the files unmerged and log the conflict in `galph_memory.md`; do not guess at the intended content.

## Findings Applied
No relevant findings in the knowledge base (grep for “PORTFOLIO-STATUS” returned no matches in docs/findings.md).

## Pointers
- `docs/fix_plan.md:21` — Tier 0 entry + Attempts History that must be updated.  
- `docs/fix_plan.md:640` — Plan Directory Inventory appendix requiring the new counts.  
- `plans/active/PORTFOLIO-STATUS/implementation.md:1` — Plan header/Phase F text to align.  
- `plans/active/PORTFOLIO-STATUS/reports/2025-12-07T220000Z/summary.md` — Final inventory evidence you’re referencing.  
- `problems.md:34` — Directive describing the stale-plan inventory work you’re closing.

## Next Up (optional)
If you finish early, prep the archive move for `plans/active/ARCH-REFINE-001` so the stale plan directories list keeps shrinking.
