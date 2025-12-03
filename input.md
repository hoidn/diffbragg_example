# Input for Ralph — Loop 2025-12-07T220000Z

## Summary
Add Tier‑4 ledger coverage for the remaining orchestration plans, drop the stray ARCH-REFRACTOR-001 stub, rerun the plan inventory so no active directories show up as “missing,” and capture the updated counts/artifacts in both the ledger and the implementation plan.

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
plans/active/PORTFOLIO-STATUS/reports/2025-12-07T220000Z/

## Do Now
1. **Implement: docs/fix_plan.md::Tier 4 — Orchestration & Agent Ops**  
   - After the existing Tier 3 blocks, add a `### Tier 4: Orchestration & Agent Ops` heading with entries for `HARDEN-SUBMODULE-ROBUSTNESS`, `ORCH-ROBUST-001`, `ORCH-CLAUDE-PATH-FIX-001`, `ORCH-CLI-FALLBACK-001`, and `SUPERVISOR`.  
   - For each entry include Dependencies (use CLAUDE.md / AGENTS.md + scripts/orchestration tooling), Status (`pending` or `in_progress` for ORCH-ROBUST work), Initiative Type (`architecture` for the orchestrator/tooling items, `docs` for SUPERVISOR), Exit Criteria (tie to `scripts/orchestration/README.md`, CLAUDE instructions, and required resiliency tests), Working Plan path, Spec References, and Attempts History referencing the existing reports/stubs (`plans/active/HARDEN-SUBMODULE-ROBUSTNESS/reports/2025-11-04T165400Z/…`, `plans/active/ORCH-ROBUST-001/reports/2025-11-05T050500Z/notes.md`, `plans/active/SUPERVISOR/reports/2025-11-24T153000Z/roadmap_assessment.md`, etc.).  
   - Make sure the new section mirrors the formatting of the Tier 1 roll-ups (bullets + Attempts History list) so plan_inventory can detect the IDs.
2. **Implement: docs/fix_plan.md::Plan Directory Inventory + Attempts History**  
   - After running the inventory (see step 5), update the appendix summary to the new counts (`Total plan directories: 55`, `Tracked in this ledger (direct): 28`, `Covered via roll-ups: 34`, `Active missing: 0`, `Missing implementation.md: 0`) and point the Artifacts/Latest Report bullets at `plans/active/PORTFOLIO-STATUS/reports/2025-12-07T220000Z/`.  
   - Refresh the Bucket Classification table so only the “tracked” and “tracked_via_rollup” buckets have members (no active_missing row).  
   - Append a new bullet under `[PORTFOLIO-STATUS] Attempts History` describing this ledger coverage pass and referencing the new artifact path. Keep Working Agreements untouched.
3. **Implement: plans/active/PORTFOLIO-STATUS/implementation.md::Phase wrap-up**  
   - Record that Phase D is complete and add a short Phase E note (“Ledger coverage + duplicate cleanup”) calling out (a) Tier 4 sections landed, (b) ARCH-REFRACTOR-001 duplicate removed, and (c) the 2025-12-07T220000Z inventory proving zero untracked plans.  
   - Update the Artifacts Index/Status line to reference the new reports directory and note that the initiative is ready for closure once Ralph confirms the counts.
4. **Implement: plans/active/ARCH-REFRACTOR-001/**  
   - Remove the duplicate stub directory (`rm -rf plans/active/ARCH-REFRACTOR-001`) now that the real plan lives at `plans/active/ARCH-REFACTOR-001/` and the archive already contains the history.  
   - Do not touch the archived copy under `archive/plans/ARCH-REFRACTOR-001/`. This step should leave no traces so the inventory no longer reports a missing implementation.md.
5. **Run: Regenerate the guarded inventory + artifacts**  
   - `python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py --plans-root plans/active --fix-plan docs/fix_plan.md --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json --out-dir plans/active/PORTFOLIO-STATUS/reports/2025-12-07T220000Z/`  
   - Verify stdout shows `Covered via rollups: 34`, `Active missing: 0`, `Missing implementation plans: 0`. Copy the resulting `inventory.json`, `inventory_missing.md` (should now be empty except for the table header), `rollup_report.md`, and the command log into the same reports directory.
6. **Validate**  
   - `pytest -q plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py` (capture the log under the new reports directory).  
   - Create/append `plans/active/PORTFOLIO-STATUS/reports/2025-12-07T220000Z/summary.md` with the final Turn Summary block after confirming the counts.

## How-To Map
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
REPORT_TS=2025-12-07T220000Z

rm -rf plans/active/ARCH-REFRACTOR-001

$EDITOR docs/fix_plan.md
$EDITOR plans/active/PORTFOLIO-STATUS/implementation.md

python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py \
  --plans-root plans/active \
  --fix-plan docs/fix_plan.md \
  --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json \
  --out-dir plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/ \
  | tee plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/plan_inventory.log

pytest -q plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py \
  | tee plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/pytest_plan_inventory.log

cp plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/summary.md{,.bak} 2>/dev/null || true
$EDITOR plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/summary.md
```

## Pitfalls To Avoid
- Do not delete `plans/active/ARCH-REFACTOR-001/`; only remove the duplicate “ARCH-REFRACTOR-001” stub. Double-check the path before running `rm -rf`.
- Keep the new Tier 4 entries consistent with existing ledger formatting (Dependencies/Status/Type/Exit Criteria/Working Plan/Spec References/Attempts History) so plan_inventory can parse them.
- When updating counts, use the numbers emitted by the fresh inventory run—hard-code only after verifying stdout/logs to prevent drift.
- Ensure `inventory_missing.md` reflects the new reality (no stray entries); do not hand-edit the file.
- Maintain ASCII text and wrap long markdown bullets as in the rest of the ledger; avoid introducing tabs or trailing whitespace.
- Remember to paste the same Turn Summary block into the new summary.md file once everything passes.

## If Blocked
- If the inventory script fails (e.g., unexpected bucket output), capture the full log in `plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/plan_inventory_fail.log`, leave docs untouched, and mark the run as blocked in summary.md so we can triage next loop.  
- If pytest hits a regression, save the failing log in the same reports directory, revert the doc edits that depended on the expected counts, and note the selector/failure text in summary.md for follow-up.

## Findings Applied
No relevant findings in the knowledge base.

## Pointers
- `docs/fix_plan.md` — add Tier 4 entries plus update the Plan Directory Inventory appendix and Attempts History.
- `plans/active/PORTFOLIO-STATUS/implementation.md` — Phase tracking for this housekeeping initiative.
- `plans/active/HARDEN-SUBMODULE-ROBUSTNESS/reports/2025-11-04T165400Z/orchestrator_tracked_outputs_prepull.patch` — Reference for the hardened submodule/tracked-output work.
- `plans/active/ORCH-ROBUST-001/reports/2025-11-05T050500Z/notes.md` — Evidence for the orchestration robustness initiative.
- `plans/active/SUPERVISOR/reports/2025-11-24T153000Z/roadmap_assessment.md` — Latest supervisor meta-analysis to cite.

## Next Up (optional)
1. Once the Tier 4 entries exist and the inventory is green, schedule whichever orchestration initiative (likely HARDEN-SUBMODULE-ROBUSTNESS) needs engineering attention first.
