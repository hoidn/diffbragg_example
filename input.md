# Input for Ralph — Loop 2025-12-03T121328Z

## Summary
Move the ARCH-LAZY-IMPORTS-001 and ARCH-TELEMETRY-001 plan directories out of `plans/active/`, update every ledger/problems reference to the new archive paths, rerun the plan-inventory guard, and refresh the Plan Directory Inventory appendix so PORTFOLIO-STATUS Phase F can close.

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
plans/active/PORTFOLIO-STATUS/reports/2025-12-03T131500Z/

## Do Now
1. **Implement: archive/plans/ARCH-LAZY-IMPORTS-001::migration**  
   - `git mv plans/active/ARCH-LAZY-IMPORTS-001 archive/plans/ARCH-LAZY-IMPORTS-001` to preserve history.  
   - Repeat for `ARCH-TELEMETRY-001`.  
   - After the move, run `rg -n "plans/active/ARCH-LAZY-IMPORTS-001"` and `rg -n "plans/active/ARCH-TELEMETRY-001"` to confirm only historic files still mention the old path.
2. **Implement: docs/fix_plan.md::Tier0 + Plan Directory Inventory sections**  
   - Update the Tier 0 bullets (lines 24-33) so Working Plan pointers and artifact citations reference `archive/plans/<ID>/...`.  
   - Update the `Working Plan:` stanza under `### [ARCH-LAZY-IMPORTS-001]` and `### [ARCH-TELEMETRY-001]` plus any Attempts History bullets that still cite `plans/active/...`.  
   - Refresh the Plan Directory Inventory appendix with the new guard timestamp and bucket counts produced by the script (expect Total≈53, Tracked direct≈26, Covered via rollups=34, Active missing=0, Missing plan=0).
3. **Implement: problems.md::Active Items**  
   - Edit the stale-plan directive so it references the new archive paths and notes that Phase F moved the closed plans under `archive/plans/`.  
   - Leave the entry unchecked until all archived initiatives are relocated, but cite `plans/active/PORTFOLIO-STATUS/reports/2025-12-03T131500Z/` so the ledger stays current.
4. **Run: plan inventory guard + pytest**  
   - Re-run `plan_inventory.py` with the rollup config and capture `inventory.json`, `inventory_missing.md`, `rollup_report.md`, and the command log under the artifacts directory for this loop.  
   - Execute `pytest -vv plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py` (log ⇒ `pytest_plan_inventory.log` in the artifacts directory) to prove the guard still passes after the directory moves.  
   - Update `docs/fix_plan.md` Attempts History (PORTFOLIO-STATUS section) with a new bullet summarizing the archival move + guard rerun referencing the new artifact path.

## How-To Map
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export REPORT_TS=2025-12-03T131500Z
mkdir -p plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}

# 1) Move the stale plan directories into archive/plans/
git mv plans/active/ARCH-LAZY-IMPORTS-001 archive/plans/ARCH-LAZY-IMPORTS-001
git mv plans/active/ARCH-TELEMETRY-001 archive/plans/ARCH-TELEMETRY-001

# 2) Update ledger/problems references (edit docs/fix_plan.md + problems.md)
rg -n "plans/active/ARCH-LAZY-IMPORTS-001" docs fix_plan.md problems.md
rg -n "plans/active/ARCH-TELEMETRY-001" docs fix_plan.md problems.md
$EDITOR docs/fix_plan.md
$EDITOR problems.md

# 3) Rerun the guard with rollup validation and log outputs
env REPORT_TS=${REPORT_TS} \
  python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py \
    --plans-root plans/active \
    --fix-plan docs/fix_plan.md \
    --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json \
    --out-dir plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/ \
  | tee plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/plan_inventory.log

# 4) Validate tests for the guard
env REPORT_TS=${REPORT_TS} \
  pytest -vv plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py \
  | tee plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/pytest_plan_inventory.log
```
- After editing `docs/fix_plan.md`, ensure both the Tier 0 section and the Appendix reference `archive/plans/<ID>/...` and the new artifact timestamp.
- Keep all new artifacts (`inventory.json`, `inventory_missing.md`, `rollup_report.md`, `plan_inventory.log`, `pytest_plan_inventory.log`) under `plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/`.

## Pitfalls To Avoid
- Do **not** copy/delete directories manually—use `git mv` so history remains intact.
- Only the two archived initiatives move this loop; leave active plans under `plans/active/` untouched until explicitly scheduled.
- Update every live reference (`docs/fix_plan.md`, `problems.md`, Working Plan pointers, Attempts History) or the inventory script will still treat them as active.
- Always invoke `plan_inventory.py` with `--rollup-config`; a missing rollup report invalidates the guard.
- The Plan Directory Inventory appendix must mirror the counts emitted by the new `inventory.json`; double-check the numbers before saving.
- Do not edit historical artifacts under `archive/plans/<ID>/reports/`; only paths and metadata change.
- Capture logs for both the guard run and pytest so Phase F has auditable evidence.
- Keep changes ASCII-only and avoid touching production code; this is a docs-only initiative.

## If Blocked
If `plan_inventory.py` or the pytest guard fails after the move, stop immediately, capture the failing command output in `plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/failure.log`, and leave the moved directories under `archive/plans/`. Update `docs/fix_plan.md` (PORTFOLIO-STATUS entry) and `galph_memory.md` to mark the initiative blocked with the error signature instead of moving additional plans.

## Findings Applied
No relevant findings in the knowledge base.

## Pointers
- `plans/active/PORTFOLIO-STATUS/implementation.md:95` — Phase F checklist and status notes.
- `docs/fix_plan.md:9` — Plan inventory Working Agreement + guard command.
- `docs/fix_plan.md:24` — Tier 0 entries referencing ARCH-LAZY-IMPORTS-001 / ARCH-TELEMETRY-001.
- `problems.md:1` — Problems ledger item requesting stale-plan cleanup.
- `plans/active/PORTFOLIO-STATUS/reports/2025-12-03T114311Z/summary.md:1` — Previous guard run for comparison.

## Next Up (optional)
If time remains after moving the first two archived directories, start enumerating the next batch of `plans/active/` entries that are already marked `done/archived` (e.g., ARCH-BRIDGE-RESP-001, ARCH-REFINE-001) so the follow-up loop can continue Phase F without another audit pass.
