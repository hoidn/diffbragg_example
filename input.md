# Input for Ralph — Loop 2025-12-07T120500Z

## Summary
Teach `plan_inventory.py` to treat roll-up membership as real ledger coverage so the guard reports match reality, then rerun the inventory and refresh the fix plan appendix/attempts history with the new counts.

## Mode
none

## InitiativeType
housekeeping

## Focus
PORTFOLIO-STATUS — Plan/Fix-Plan synchronization & archive hygiene

## Branch
integration

## Mapped tests
pytest -q plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py

## Artifacts
plans/active/PORTFOLIO-STATUS/reports/2025-12-07T153000Z/

## Do Now
1. **Implement: plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py::apply_rollup_coverage**  
   - Extend `PlanEntry` with a `rollup_coverage` field (list) and add a helper that maps plan IDs → roll-up IDs when the roll-up itself is present in `docs/fix_plan.md`.  
   - Call the helper after building the inventory, then recompute `entry.bucket` so roll-up-covered plans land in a new `tracked_via_rollup` bucket, are omitted from `inventory_missing.md`, and appear in the console summary (print a "Covered via rollups" line).  
   - Ensure `inventory.json` serializes the new field and that `compute_bucket`/`write_missing_md` treat roll-up-covered plans as tracked even if their IDs never appear directly in the ledger.
2. **Implement: plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py::TestRollupCoverage**  
   - Update existing tests to match the new bucket behavior and add hermetic coverage for the helper (single/multi-roll-up membership, plans that should remain active_missing, etc.).  
   - Keep the suite tmp-path based; no repo data reads. Confirm the new bucket values (`tracked_via_rollup`) plus `inventory_missing.md` filtering are asserted.
3. **Rerun the guarded inventory + capture artifacts**  
   - Set `REPORT_TS=2025-12-07T153000Z`, run `plan_inventory.py --rollup-config … --out-dir plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/`, and confirm stdout shows `Covered via rollups: 32`, `active_missing` drops to only genuinely uncovered plans (likely 0), and `inventory_missing.md` lists just ARCH-REFRACTOR-001.  
   - Save the pytest log (`pytest_plan_inventory.log`) and a refreshed summary.md describing the roll-up coverage change, along with the regenerated `inventory.json` / `rollup_report.md` / `inventory_missing.md`.
4. **Docs + plan sync**  
   - Update `docs/fix_plan.md` (Tier 0 entry + Plan Directory Inventory appendix + Attempts History) with the new timestamp, bucket counts (explicitly call out the tracked_via_rollup split), and artifact pointer.  
   - Note the work in `plans/active/PORTFOLIO-STATUS/implementation.md` Phase D, marking D1–D3 complete once the rerun shows the expected counts.

## How-To Map
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
REPORT_TS=2025-12-07T153000Z

$EDITOR plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py
$EDITOR plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py

pytest -q plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py \
  | tee plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/pytest_plan_inventory.log

python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py \
  --plans-root plans/active \
  --fix-plan docs/fix_plan.md \
  --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json \
  --out-dir plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/

$EDITOR docs/fix_plan.md
$EDITOR plans/active/PORTFOLIO-STATUS/implementation.md
```

## Pitfalls To Avoid
- Do not treat a roll-up as coverage unless its ID already exists in `docs/fix_plan.md`; otherwise you could hide genuinely missing initiatives.
- Keep `inventory_missing.md` hermetic—no hand editing of results—and make sure the helper doesn’t mutate `entries` in place before JSON serialization.
- Preserve CLI defaults and guard behavior; any missing/invalid rollup config should still raise the same errors.
- Tests must stay tmp-path based; never read the real repo files from the unit tests.
- When updating docs, keep the Working Agreements command untouched and only adjust the appendix counts + Attempts History with the new timestamp/artifacts.
- Maintain ASCII and existing comment style inside the script.

## If Blocked
- If the helper cannot determine roll-up membership because the config or ledger is malformed, capture the failing plan IDs plus stack trace in `plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/rollup_coverage_fail.log`, leave docs unchanged, and summarize the failure in summary.md.  
- If pytest fails, preserve the log in the artifacts directory, revert any partial doc edits, and flag the failure (with selector + stack) in summary.md for supervisor triage.

## Findings Applied
No relevant findings in the knowledge base.

## Pointers
- `docs/fix_plan.md:27` — Tier 0 entry describing the Phase D goal and guard expectations.
- `plans/active/PORTFOLIO-STATUS/implementation.md:34` — Implementation plan (Phase D checklist) to update once changes land.
- `plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py:1` — Script to extend with roll-up coverage awareness.
- `plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py:1` — Hermetic pytest suite for the inventory script.

## Next Up (optional)
1. Once the roll-up aware counts are accurate, close PORTFOLIO-STATUS (mark initiative done) and archive its plan.
