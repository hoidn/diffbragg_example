# Input for Ralph — Loop 2025-12-08T150000Z

## Summary
Mark PORTFOLIO-STATUS as complete by updating the Tier 0 ledger entry and implementation plan header to `done`, citing the 2025-12-07T220000Z artifacts so the initiative can close cleanly.

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
plans/active/PORTFOLIO-STATUS/reports/2025-12-08T150000Z/

## Do Now
1. **Implement: docs/fix_plan.md::Tier 0 entry + Attempts History**  
   - Change the Tier 0 bullet for PORTFOLIO-STATUS from “in_progress (Phase D)” to `done`, summarize that Phases A–E satisfied the guardrails, and point at `plans/active/PORTFOLIO-STATUS/reports/2025-12-07T220000Z/` for the final inventory.  
   - Append a final Attempts History row (dated with your loop) that notes closure, references the same artifact path, and states that future reruns follow the Working Agreements guardrail command.
2. **Implement: plans/active/PORTFOLIO-STATUS/implementation.md::Header + closure summary**  
   - Flip the `Status:` field from `in_progress` to `done`.  
   - Add a short closure paragraph under the Phase E section (or a new “Closure” subheading) describing that Tier 4 ledger coverage and the 2025-12-07T220000Z inventory satisfied Exit Criteria 1–4, with an explicit link to the reports directory.
3. **Implement: docs/fix_plan.md::Plan Directory Inventory appendix**  
   - Leave the guard command as-is but note that the “Latest Report” and “Artifacts” entries already point at 2025-12-07T220000Z; simply confirm they remain accurate after your edits and adjust wording if needed to reflect the initiative being complete.
4. **Record Turn Summary**  
   - Once the docs edits are staged, add a new `summary.md` under `plans/active/PORTFOLIO-STATUS/reports/2025-12-08T150000Z/` (or update it) with the canonical Turn Summary for this loop.

## How-To Map
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
REPORT_TS=2025-12-08T150000Z

$EDITOR docs/fix_plan.md
$EDITOR plans/active/PORTFOLIO-STATUS/implementation.md

mkdir -p plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}
$EDITOR plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/summary.md
```

## Pitfalls To Avoid
- Do not touch `plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py`; we are only updating documentation/ledger state.
- Keep the Tier 0 entry wording concise but explicit about the final artifact path and which phases closed the initiative.
- Ensure the new Attempts History entry references the same artifact directory so audits follow a single breadcrumb.
- Maintain ASCII text and wrap bullets to match existing markdown style.
- Leave the Working Agreements guardrail command intact so future reruns still cite the canonical CLI.

## If Blocked
- If you discover the inventory counts have changed since 2025-12-07, stop editing the ledger, rerun the guard command into a new timestamped directory, and capture the discrepancy in `plans/active/PORTFOLIO-STATUS/reports/${REPORT_TS}/summary.md` so we can triage before marking the initiative done.

## Findings Applied
No relevant findings in the knowledge base.

## Pointers
- `docs/fix_plan.md:27` — Tier 0 entry and Attempts History block to update.
- `plans/active/PORTFOLIO-STATUS/implementation.md:1` — Status header and Phase sections.
- `plans/active/PORTFOLIO-STATUS/reports/2025-12-07T220000Z/summary.md` — Final Phase E evidence to cite.

## Next Up (optional)
1. If extra time remains, draft the scoping notes for FINDINGS-LEDGER-002 so the knowledge-base upkeep plan has real Goals/Exit Criteria.
