# Findings Ledger Maintenance Cadence

This checklist guides quarterly maintenance of `docs/findings.md` to keep the knowledge base synchronized with implementation reality.

## When to Run

Run this cadence when any of:
- Quarterly portfolio review (align with Tier 0/1 roadmap reviews)
- After major initiative closures affecting ≥5 findings
- When >10 new findings are added/resolved in a month
- When supervisor notices doc drift (Active findings referencing deleted code, Resolved findings without pytest validation)

## Prerequisites

- [ ] `git pull --rebase` on `docs/findings.md`, `docs/fix_plan.md`, `docs/index.md`
- [ ] Create new report directory: `plans/active/FINDINGS-LEDGER-002/reports/<TIMESTAMP>/`
  - `<TIMESTAMP>` format: `YYYY-MM-DDTHHMMSSZ` (ISO 8601)

## Audit Steps

### Phase 1: Audit Active Findings

For each finding with `Status: Active` in `docs/findings.md`:

- [ ] **Verify path:line citations exist:**
  - Run `grep -n "<cited_function>" <cited_file>` for each citation in Summary column
  - If code moved/deleted: update citation or mark finding Resolved if constraint satisfied elsewhere

- [ ] **Check material changes:**
  - Run `git log -p --follow <cited_file> | grep -C 10 "<cited_function>"` since finding creation date
  - If behavior changed materially: update finding description or mark Resolved if constraint now satisfied

- [ ] **Update status if satisfied:**
  - If cited constraint is now enforced (pytest test exists, code pattern removed): change `Status: Active` → `Status: Resolved`, add closure note with commit SHA

- [ ] **Verify consumer links:**
  - Check if "**Consumers:** [INITIATIVE-ID]" metadata present in Summary column
  - If missing AND a fix-plan initiative now governs the finding: add consumer link
  - If no consumer exists: tag for Phase 3 (orphan handling)

- [ ] **Flag for Deferral:**
  - If finding is >6 months old, low-priority, and no consumer: mark for Deferral decision in Phase 3

### Phase 2: Audit Resolved Findings

For each finding with `Status: Resolved`:

- [ ] **Confirm validation:**
  - Check if resolution commit message cites a pytest selector
  - If pytest exists: run selector to confirm fix still holds
  - If pytest N/A: document why (e.g., doc-only fix, spec change)

- [ ] **Archive if stale:**
  - If Resolved >3 months ago AND no active cross-references from fix_plan.md: move to "Archived Findings" section in findings.md (or defer to fix_plan_archive.md)

### Phase 3: Handle Orphaned Findings

For Active findings without consumers (no "Consumers:" metadata or flagged in Phase 1):

- [ ] **Decision triage:**
  - **Create new initiative/roll-up:** If finding governs planned work not yet in fix_plan.md, create Tier 1–3 initiative and link it
  - **Mark Deferred:** If finding is valid but low-priority, change `Status: Deferred`, add rationale note
  - **Retire:** If finding is obsolete (code deleted, spec changed, constraint invalidated), move to Archived section with closure note

- [ ] **Document decisions:**
  - Capture triage rationale in `reports/<TIMESTAMP>/orphan_triage.md`

### Phase 4: Regenerate Artifacts

- [ ] **Inventory export:**
  - Option A (manual): Export findings table to CSV, save as `reports/<TIMESTAMP>/findings_inventory.csv`
  - Option B (scripted): Run `python plans/active/FINDINGS-LEDGER-002/bin/findings_inventory.py --out reports/<TIMESTAMP>/findings_inventory.json` (if script exists)

- [ ] **Write summary:**
  - Create `reports/<TIMESTAMP>/summary.md` with:
    - Total findings count
    - Status breakdown (Active / Resolved / Deferred / Archived)
    - Consumer coverage % (Active findings with "Consumers:" metadata)
    - Key decisions (findings retired, new initiatives created, deferrals)

### Phase 5: Commit and Update Ledger

- [ ] **Commit doc updates:**
  - Stage: `docs/findings.md`, `docs/fix_plan.md` (if new initiatives created), `docs/index.md` (if cadence rules updated)
  - Commit message: `[FINDINGS-LEDGER-002] Cadence run <TIMESTAMP> — <summary_line>`
  - Example: `[FINDINGS-LEDGER-002] Cadence run 2025-12-07T100000Z — 3 findings resolved, 2 deferred, 82% consumer coverage`

- [ ] **Update fix_plan.md Attempts History:**
  - Add entry to [FINDINGS-LEDGER-002] section:
    ```markdown
    * <TIMESTAMP> — Cadence run: <N> findings audited, <M> status changes, consumer coverage <X>%. Artifacts: plans/active/FINDINGS-LEDGER-002/reports/<TIMESTAMP>/
    ```

## Expected Artifacts

After completing all phases, the report directory should contain:

- `summary.md` — Stats and key decisions
- `findings_inventory.json` or `findings_inventory.csv` — Machine-readable inventory
- `orphan_triage.md` (if applicable) — Rationale for deferral/retire decisions
- `audit_notes.md` (if applicable) — Any manual judgment calls or blockers

## Exit Criteria

- [ ] All Active findings have valid `path:line` citations pointing to existing code/spec
- [ ] Resolved findings have validation notes (pytest selector or N/A documented)
- [ ] Orphaned findings (no consumers) have documented triage decision
- [ ] `findings_inventory.json` regenerated
- [ ] fix_plan.md Attempts History updated with artifact path
- [ ] Doc graph consistency verified (findings.md ↔ fix_plan.md ↔ index.md cross-refs valid)

## Maintenance Notes

- **Cadence owner:** Supervisor (Galph) delegates to Ralph for execution
- **Typical duration:** 1–2 loops (evidence gathering + doc edits)
- **Automation future:** Phase C.2 deferred — manual cadence sufficient for quarterly runs; revisit if findings volume exceeds 150 or cadence drops to monthly
