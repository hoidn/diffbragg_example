# Input for Ralph — Loop 2025-12-03T122513Z

## Summary
Archive the completed ARCH-BRIDGE-RESP-001 plan directory (plus the stray ARCH-TELEMETRY-001 stub), update every living doc reference to the new archive path, and rerun the plan-inventory guard/tests so PORTFOLIO-STATUS Phase F can progress.

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
plans/active/PORTFOLIO-STATUS/reports/2025-12-03T140000Z/

## Do Now
1. **Implement: archive/plans/ARCH-BRIDGE-RESP-001::migration**  
   - `git mv plans/active/ARCH-BRIDGE-RESP-001 archive/plans/ARCH-BRIDGE-RESP-001` so every tracked file moves under the archive tree.  
   - Remove the now-stale stub directory for ARCH-TELEMETRY-001 (`rm -rf plans/active/ARCH-TELEMETRY-001`) so the inventory script no longer reports a missing implementation.  
   - `rg -n "plans/active/ARCH-(BRIDGE-RESP|TELEMETRY)-001" docs` (and `plans`) to confirm only historical logs mention the old paths.
2. **Implement: docs/fix_plan.md::Tier0 & Plan Directory Inventory**  
   - Update the Tier 0 entry + Attempts History bullets so ARCH-BRIDGE-RESP-001 points at `archive/plans/ARCH-BRIDGE-RESP-001/...`.  
   - Add a new Attempts History line for this Phase F loop citing the 2025-12-03T140000Z artifacts.  
   - Refresh the “Plan Directory Inventory” appendix with the new guard timestamp, artifact path, and bucket counts from the latest `inventory.json` (ensure Total/Tracked/Roll-up/Active missing/Missing plan match the script output).  
   - Drop any lingering references to the deleted ARCH-TELEMETRY-001 stub.
3. **Implement: docs/fix_plan_archive_2025-12-02.md + allied docs**  
   - Replace every `plans/active/ARCH-BRIDGE-RESP-001/...` reference in `docs/fix_plan_archive_2025-12-02.md`, `docs/data_dependency_manifest.md:173`, `docs/architecture/dbex/io/writer.idl.md:144`, `docs/TESTING_GUIDE.md:139/163`, and `docs/development/TEST_SUITE_INDEX.md:13/23` with the `archive/plans/ARCH-BRIDGE-RESP-001/...` equivalents so future readers land in the archive tree.  
   - Double-check markdown tables still align after the edits.
4. **Implement: problems.md & plans/active/PORTFOLIO-STATUS/implementation.md**  
   - Amend the problems-ledger entry about stale plan directories to note that ARCH-BRIDGE-RESP-001 was moved on this loop (keep the box unchecked and list the next targets, e.g., ARCH-REFINE-001).  
   - Update the Phase F section in `plans/active/PORTFOLIO-STATUS/implementation.md` to log this archival move, referencing the new artifact path.
5. **Run: plan_inventory guard + pytest**  
   - `export REPORT_TS=2025-12-03T140000Z; mkdir -p plans/active/PORTFOLIO-STATUS/reports/$REPORT_TS`  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py --plans-root plans/active --fix-plan docs/fix_plan.md --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json --out-dir plans/active/PORTFOLIO-STATUS/reports/$REPORT_TS/ | tee plans/active/PORTFOLIO-STATUS/reports/$REPORT_TS/plan_inventory.log`  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py | tee plans/active/PORTFOLIO-STATUS/reports/$REPORT_TS/pytest_plan_inventory.log`  
   - Drop the resulting `inventory.json`, `inventory_missing.md`, and `rollup_report.md` alongside the logs in the artifacts directory.

## How-To Map
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export REPORT_TS=2025-12-03T140000Z
mkdir -p plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}

git mv plans/active/ARCH-BRIDGE-RESP-001 archive/plans/ARCH-BRIDGE-RESP-001
rm -rf plans/active/ARCH-TELEMETRY-001
rg -n "plans/active/ARCH-BRIDGE-RESP-001" docs || true
rg -n "plans/active/ARCH-TELEMETRY-001" docs || true

$EDITOR docs/fix_plan.md
$EDITOR docs/fix_plan_archive_2025-12-02.md
$EDITOR docs/data_dependency_manifest.md
$EDITOR docs/architecture/dbex/io/writer.idl.md
$EDITOR docs/TESTING_GUIDE.md
$EDITOR docs/development/TEST_SUITE_INDEX.md
$EDITOR problems.md
$EDITOR plans/active/PORTFOLIO-STATUS/implementation.md

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
- Do not edit archived report contents; only relocate the directory via `git mv`.
- Keep git history intact—no `cp` or manual copy/paste.
- Limit `rg`/replacement scopes to docs and plans so build logs remain untouched.
- When updating markdown tables, preserve the pipe alignment (watch for tabs vs spaces).
- Re-run the inventory guard *after* all moves so counts reflect the new tree.
- Ensure no lingering `plans/active/ARCH-BRIDGE-RESP-001` strings survive outside historical logs before wrapping up.
- Capture every log (`plan_inventory.log`, `pytest_plan_inventory.log`, inventory outputs) under the designated artifacts directory.
- Do not delete other directories under `plans/active/`—only the specific stub called out above.
- Leave `problems.md` entry unchecked; just append the new status note.
- Remember to regenerate `docs/fix_plan.md` Plan Directory Inventory numbers from the new `inventory.json` (do not reuse the prior counts).

## If Blocked
- If `plan_inventory.py` or the pytest guard fails, stop immediately, save the failing command output to `plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/failure.log`, and note the error in `docs/fix_plan.md` Attempts History + `plans/active/PORTFOLIO-STATUS/implementation.md`.  
- If the `git mv` collides with existing archive content, capture the exact error, leave the tree untouched, and record the blocker in `problems.md` + `docs/fix_plan.md` (Phase F entry) instead of attempting partial moves.

## Findings Applied
No relevant findings in the knowledge base.

## Pointers
- `docs/fix_plan.md:24` — Tier 0 entry describing Phase F scope.
- `plans/active/PORTFOLIO-STATUS/implementation.md:95` — Phase F checklist/notes.
- `problems.md:1` — Stale-plan directive that this work services.
- `docs/fix_plan_archive_2025-12-02.md:53` — ARCH-BRIDGE-RESP-001 archive log that needs updated paths.
- `plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py:1` — Guard script referenced in this loop.

## Next Up (optional)
- Continue Phase F by archiving `plans/active/ARCH-REFINE-001` once this loop lands cleanly.
