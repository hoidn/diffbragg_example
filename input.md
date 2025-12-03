# Input for Ralph — Loop 2025-12-03T095530Z

## Summary
Finish PORTFOLIO-STATUS Phase B3 by wiring the 13 roll-up initiatives into `docs/fix_plan.md`, updating the plan notes, and regenerating the inventory artifacts with the roll-up config.

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
plans/active/PORTFOLIO-STATUS/reports/2025-12-03T120000Z/

## Do Now

1. **Add the 13 roll-up subsections to `docs/fix_plan.md`**  
   - For each ID in `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T183000Z/ledger_rollup_plan.md` (`DB-AT-SUITE-CARE-001`, `MAP-SCALE-SYNC-001`, `PHYSICS-LOSS-001`, `TORCH-GEOMETRY-SYNC-001`, `TORCH-REFINE-CLEANUP-001`, `TORCH-CLI-BRIDGE-ROLLUP-001`, `FORWARD-EQUIV-COVERAGE-001`, `TOOLING-VIS-001`, `DOCS-ROADMAP-001`, `RUNTIME-VEC-001`, `REPORT-NANOBRAG-STATUS-001`, `NANOBRAG-GOLDEN-001`, `ARCH-SPLIT-001`):
     - Insert a `### [ROLLUP-ID]` section under the Active/Pending portion describing initiative type, tier, dependencies (cite the spec shards listed in the roll-up plan), and the exact member plan directories (use `plans/active/PORTFOLIO-STATUS/rollups.json`).
     - Spell out exit criteria tied to those specs/tests (e.g., DB-AT chi²/pixel ≤ 1e2 per `docs/spec-db-conformance.md`, MAP-SCALE calibration precedence per `docs/spec-db-workflow.md`, TORCH-REFINE Stage B ASU guardrails per `docs/spec-db-workflow.md` §Stage B, TOOLING-VIS residual Z-score bounds per `docs/spec-db-vis.md`).
     - Add an Attempts History bullet pointing at `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T150000Z/classification.md` and the freshest member-plan report for that roll-up when available.
     - Keep the Tier 1 bullet list aligned with the new sections and refresh the Plan Directory Inventory appendix so it references both the roll-up plan and the enforced `--rollup-config` automation guard.

2. **Sync the plan narrative with the ledger work**  
   - Update `plans/active/PORTFOLIO-STATUS/implementation.md` Phase B3 notes to mark the roll-up sections as complete (leave the script/test status callouts intact for history) and mention the new artifact timestamp `2025-12-03T120000Z`.

3. **Regenerate the inventory + roll-up artifacts**  
   - Run `python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py --plans-root plans/active --fix-plan docs/fix_plan.md --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json --out-dir plans/active/PORTFOLIO-STATUS/reports/2025-12-03T120000Z/`.
   - Ensure the new `rollup_report.md` shows “Fix-Plan Coverage: ✓ Section exists” for all 13 roll-ups and capture residual TODOs (if any) in `notes.md` inside the same directory.

## How-To Map
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md

python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py \
  --plans-root plans/active \
  --fix-plan docs/fix_plan.md \
  --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json \
  --out-dir plans/active/PORTFOLIO-STATUS/reports/2025-12-03T120000Z/
```

## Pitfalls To Avoid
- Keep roll-up headings synchronized with `rollups.json`; update both files if an ID changes.
- Cite the exact spec clauses from the roll-up plan rather than inventing new prose; DB-AT entries must point to `docs/spec-db-conformance.md`, MAP-SCALE to `docs/spec-db-workflow.md`, etc.
- Do not duplicate member-plan Attempts History; link to the classification artifact and the latest member report instead.
- Ensure each roll-up section lists member plan directories and current status so automation outputs stay meaningful.
- Always pass `--rollup-config` when running `plan_inventory.py`; the regenerated `rollup_report.md` is the validation that the ledger edits took effect.
- Keep doc edits focused—avoid reflowing unrelated sections or altering prior history entries.

## If Blocked
- If concurrent ledger edits conflict with your changes, stash the drafted sections as `plans/active/PORTFOLIO-STATUS/reports/2025-12-03T120000Z/draft_rollup_sections.md` and stop before touching `docs/fix_plan.md`.
- If `plan_inventory.py` fails post-edit, capture the traceback in `plans/active/PORTFOLIO-STATUS/reports/2025-12-03T120000Z/plan_inventory_fail.log`, leave the docs unchanged, and note the issue in `notes.md` for next loop triage.

## Findings Applied
- **TESTING-003** — DB-AT roll-up text must reference real pytest selectors with existing artifacts.
- **MANIFEST-001** — Automation outputs must point to on-disk files; rerun plan_inventory.py so the new roll-up report validates coverage.

## Pointers
- `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T183000Z/ledger_rollup_plan.md` — authoritative roll-up table.
- `plans/active/PORTFOLIO-STATUS/rollups.json` — definitive member list for each roll-up ID.
- `docs/fix_plan.md` (Tier 1 + appendix) — edit location for the new sections.
- `plans/active/PORTFOLIO-STATUS/implementation.md:41-53` — Phase B3 description with new status notes.

## Next Up (optional)
1. After the roll-up sections exist, move into Phase C by surfacing the automation guard inside `docs/fix_plan.md` Working Agreements.
2. Revisit ARCH-SIM-CONSTRUCTION-001 to unblock ARCH-REFACTOR-001 once the revamped ledger stabilizes.
