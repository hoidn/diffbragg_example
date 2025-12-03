# Input for Ralph — Loop 2025-12-05T183000Z

## Summary
Land PORTFOLIO-STATUS Phase B3 by extending the plan inventory tooling with roll-up awareness and updating `docs/fix_plan.md` so the DB-AT/MAP-SCALE/TORCH-* suites have first-class ledger sections backed by automated reports.

## Mode
none

## InitiativeType
housekeeping

## Focus
PORTFOLIO-STATUS — Plan/Fix-Plan synchronization & archive hygiene

## Branch
integration

## Mapped tests
`pytest -q plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py`

## Artifacts
plans/active/PORTFOLIO-STATUS/reports/2025-12-05T210000Z/

## Do Now

1. **Enhance `plan_inventory.py` with roll-up + bucket outputs**  
   - Add `--rollup-config plans/active/PORTFOLIO-STATUS/rollups.json` so the script can look up member plan directories for each roll-up ID (definitions live in that JSON file; update it if additional IDs appear).  
   - For every plan entry, emit a `bucket` field in `inventory.json` (`active_missing`, `archive_ready`, `missing_plan`) using the same rules recorded in `reports/2025-12-05T150000Z/classification.md`.  
   - When `--rollup-config` is present, produce a companion `rollup_report.md` inside the `--out-dir` summarizing each roll-up (ID, member plans, last-report span, whether `docs/fix_plan.md` already has a `### [ID]` section).  
   - Create a pytest module under `plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py` that builds a temporary mini tree (a few fake plan directories + JSON config) and asserts that the new bucket logic and roll-up report text match expectations. Tests should be hermetic (tmp_path fixtures, no reliance on repo data).

2. **Author the roll-up sections in `docs/fix_plan.md`**  
   - For each ID listed in `reports/2025-12-05T183000Z/ledger_rollup_plan.md` (DB-AT-SUITE-CARE-001, MAP-SCALE-SYNC-001, PHYSICS-LOSS-001, TORCH-GEOMETRY-SYNC-001, TORCH-REFINE-CLEANUP-001, TORCH-CLI-BRIDGE-ROLLUP-001, FORWARD-EQUIV-COVERAGE-001, TOOLING-VIS-001, DOCS-ROADMAP-001, RUNTIME-VEC-001, REPORT-NANOBRAG-STATUS-001, NANOBRAG-GOLDEN-001, ARCH-SPLIT-001):  
     • Add a dedicated `### [ROLLUP-ID]` subsection under “Active / Pending Initiatives” stating dependencies, initiative type/tier, working plan pointers (list the member directories), exit criteria tied to the cited spec doc(s), and an Attempts History bullet linking back to `reports/2025-12-05T150000Z/classification.md`.  
     • Update the meta bullets near the top (Tier 1 list) only if titles/wording need alignment; avoid duplicating text.  
     • Refresh the Plan Directory Inventory appendix so it references both `reports/2025-12-05T150000Z/` and the new roll-up report, and note that `plan_inventory.py` now requires the roll-up config when rerun.

3. **Regenerate the automation artifacts**  
   - After the code + doc edits, run `python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py --plans-root plans/active --fix-plan docs/fix_plan.md --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json --out-dir plans/active/PORTFOLIO-STATUS/reports/2025-12-05T210000Z/` so the new inventory, missing summary, and roll-up report reflect the ledger changes.  
   - Capture `rollup_report.md`, the refreshed `inventory.json`, and a short `notes.md` describing any follow-up gaps (e.g., if specific plan directories still need archival review).

## How-To Map
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
# 1. Run the new pytest coverage for plan_inventory.py (after adding tests)
pytest -q plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py

# 2. Regenerate inventory + roll-up artifacts after the doc/script edits
python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py \
  --plans-root plans/active \
  --fix-plan docs/fix_plan.md \
  --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json \
  --out-dir plans/active/PORTFOLIO-STATUS/reports/2025-12-05T210000Z/
```

## Pitfalls To Avoid
- Keep `plans/active/PORTFOLIO-STATUS/rollups.json` in sync with the ledger; if you rename an ID, update both the JSON and every fix-plan heading atomically.
- The script must remain idempotent and safe to rerun—do not embed timestamps in its outputs beyond the directory name the caller provides.
- Each new fix-plan subsection should cite the relevant spec doc (see the roll-up plan table) and clearly list the plan directories covered; avoid vague text like “covers DB-AT items.”
- Respect FINDING TESTING-003: whenever you mention a selector or test module, ensure the referenced pytest node actually collects (rerun `pytest --collect-only` locally if unsure) and link to the latest artifact under the member plan.
- Tests for the script should not mutate the real `plans/active/` tree—use temporary directories and clean up after the run.

## If Blocked
- If `plan_inventory.py` cannot parse `docs/fix_plan.md` after your edits, capture the stack trace in `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T210000Z/plan_inventory_fail.log`, leave the doc intact, and note the issue in `notes.md` so we can triage before the next loop.
- If adding roll-up sections would cause merge conflicts with concurrent ledger edits, stop, stash your changes in the artifact directory (e.g., `draft_rollup_sections.md`), and ping Galph—do not overwrite other initiatives’ Attempts History.

## Findings Applied
- **TESTING-003** — Selector entries in docs/tests must stay synchronized with real pytest collection; when adding DB-AT roll-up content ensure each selector reference points to an exercised test with a fresh artifact.
- **MANIFEST-001** — Automation artifacts (inventory/roll-up reports) must reference on-disk files; the new script output and roll-up config should error when member plan directories are missing so manifests never point to stale paths.

## Pointers
- `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T183000Z/ledger_rollup_plan.md` — table detailing each roll-up’s members, spec references, and script/test requirements.
- `plans/active/PORTFOLIO-STATUS/implementation.md:34-55` — updated Phase B description calling for the roll-up automation.
- `docs/fix_plan.md:20-120` — Tier 1 roadmap entries that now need full subsections plus appendix updates once the roll-up sections exist.

## Next Up (optional)
1. After the roll-up sections land, start Phase C by embedding the new automation guard (plan inventory rerun instructions) directly into `docs/fix_plan.md` Working Agreements.  
2. Once the ledger is synchronized, revisit ARCH-SIM-CONSTRUCTION-001 to unblock ARCH-REFACTOR-001 Phase D.3 using the refreshed acceptance-suite metadata.
