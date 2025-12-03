# Roll-up Section Gaps — 2025-12-03T095530Z

## Observed State
- `docs/fix_plan.md` currently references the 13 roll-up IDs only in Tier 1 bullet points and the Plan Directory Inventory appendix (lines 25-40 and 343-370).
- No dedicated `### [ROLLUP-ID]` subsections exist under “Active / Pending Initiatives”; `rg "### \[DB-AT-SUITE-CARE-001\] docs/fix_plan.md` returns no matches.
- As a result, the 34 plan directories that rely on these roll-ups still lack individual ledger entries describing scope, dependencies, or exit criteria.

## Required Actions (Phase B3 scope from `ledger_rollup_plan.md`)
1. For each roll-up ID listed in `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T183000Z/ledger_rollup_plan.md`, add a `### [ID]` section under the Active/Pending portion of `docs/fix_plan.md`.
2. Each section must include:
   - Initiative type + tier and dependency notes citing the relevant spec shards (see the roll-up plan table).
   - Member plan directories (use `rollups.json` for definitive membership).
   - Exit criteria that echo the acceptance gates already defined in the individual plan directories/tests.
   - An Attempts History bullet referencing the Phase B classification artifact or the latest member-plan reports.
3. Update `plans/active/PORTFOLIO-STATUS/implementation.md` Phase B3 notes after the sections land so future loops know the ledger portion is satisfied.

## Validation Hooks
- After editing `docs/fix_plan.md`, rerun `plan_inventory.py --rollup-config ...` to confirm the roll-up report now sees fix-plan coverage (`Fix-Plan Coverage: ✓`).
- Record the regenerated artifacts under `plans/active/PORTFOLIO-STATUS/reports/<new timestamp>/`.
