# FINDINGS-LEDGER-002 Phase C Planning Notes
**Loop:** i=123 (Galph)
**Date:** 2025-12-07T100000Z
**Phase:** C — Cadence, Tooling, and Working Agreements
**DecisionStatus:** patch_ready

---

## Context

Phases A–B complete:
- **Phase A (2025-12-03T120250Z):** 100% path:line coverage achieved (86/86 findings). Ledger audit complete with inventory artifacts.
- **Phase B.1 (2025-12-07T060000Z):** Consumer mapping baseline established (9/74 Active findings, 12.2% coverage).
- **Phase B.2 (2025-12-07T080000Z):** Reciprocal cross-links delivered—78.4% consumer coverage (58/74 Active findings), 2 new initiatives created, 7 existing initiatives updated with "Governed by" lines.

**Remaining work:** Phase C — establish maintenance cadence and update doc graph guardrails.

---

## Phase C Breakdown

### C.1 — Cadence Definition (docs-only, this loop)

**Goal:** Author a quarterly maintenance checklist that supervisors can follow to keep `docs/findings.md` synchronized with implementation reality.

**Deliverable:** `plans/active/FINDINGS-LEDGER-002/cadence_checklist.md` template

**Contents:**
1. **When to run:** Quarterly, or when >10 findings are added/resolved in a span, or when a major initiative closes.
2. **Steps:**
   - Pull latest `docs/findings.md` + `docs/fix_plan.md`
   - For each Active finding:
     - Verify `path:line` citations still exist in codebase (grep each citation)
     - Check if cited code/spec changed materially since finding was authored
     - Update status to Resolved if implementation now satisfies the constraint
     - Add "Consumer" metadata if new initiatives now govern the finding
   - For each Resolved finding:
     - Confirm fix landed and pytest selector validates it (or document why pytest is N/A)
     - Move to archive section if >3 months old and no active references
   - For orphaned findings (no consumers after B.2):
     - Decide: (a) create new initiative/roll-up, (b) mark Deferred with rationale, or (c) retire if obsolete
   - Regenerate `findings_inventory.json` using Phase A audit script (or manual CSV export)
   - Commit all doc updates with artifact path in commit message
3. **Exit criteria:**
   - `findings_inventory.json` regenerated
   - Doc graph consistency verified (findings.md ↔ fix_plan.md ↔ index.md)
   - No stale "Active" findings older than 6 months without consumer or deferral note
4. **Artifact expectations:**
   - New timestamped report directory under `plans/active/FINDINGS-LEDGER-002/reports/<YYYY-MM-DDTHHMM00Z>/`
   - `summary.md` capturing stats (total findings, Active/Resolved/Deferred counts, consumer coverage %)
   - `findings_inventory.json` (machine-readable)
   - `audit_notes.md` (any manual decisions or deferrals)

**Template structure:**
```markdown
# Findings Ledger Maintenance Cadence

## When to Run
- Quarterly (align with Tier 0/1 portfolio reviews)
- After major initiative closures (≥5 findings impacted)
- When >10 new findings added in a month

## Checklist

### Pre-Run
- [ ] `git pull --rebase` on `docs/findings.md` and `docs/fix_plan.md`
- [ ] Create new report directory: `plans/active/FINDINGS-LEDGER-002/reports/<TIMESTAMP>/`

### Audit Active Findings
- [ ] For each Active finding:
  - [ ] Grep `path:line` citations to verify code still exists
  - [ ] Check if cited code changed materially (git log / blame)
  - [ ] Update status to Resolved if constraint now satisfied
  - [ ] Add "Consumer" metadata if new initiatives govern it
  - [ ] Flag for Deferral if obsolete or low-priority

### Audit Resolved Findings
- [ ] For each Resolved finding:
  - [ ] Confirm pytest selector validates fix (or N/A documented)
  - [ ] Move to archive if >3 months old and no active refs

### Handle Orphans
- [ ] For findings without consumers:
  - [ ] Decide: create new initiative, defer, or retire
  - [ ] Document decision in `audit_notes.md`

### Regenerate Artifacts
- [ ] Run `python plans/active/FINDINGS-LEDGER-002/bin/findings_inventory.py` (or manual export)
- [ ] Capture output to `findings_inventory.json`
- [ ] Write `summary.md` with coverage stats

### Commit
- [ ] Commit docs updates: `[FINDINGS-LEDGER-002] Cadence run <TIMESTAMP>`
- [ ] Update `docs/fix_plan.md` Attempts History with artifact path

## Expected Artifacts
- `summary.md` (stats)
- `findings_inventory.json` (machine-readable)
- `audit_notes.md` (manual decisions)
```

---

### C.2 — Automation Hook (DEFERRED to future loop)

**Rationale:** Phase A already delivered `findings_inventory.py` script skeleton (see `plans/active/FINDINGS-LEDGER-002/reports/2025-12-03T112709Z/`). Full automation (auto-grep citations, auto-status-update) requires more sophisticated parsing than warranted for quarterly manual cadence.

**Deferral:** Mark C.2 as "future enhancement" in implementation.md. Focus this loop on C.1 + C.3 (docs-only cadence definition).

---

### C.3 — Guardrail Updates (docs-only, this loop)

**Goal:** Embed the cadence into documented guardrails so future loops know when/how to rerun FINDINGS-LEDGER-002 maintenance.

**Targets:**

1. **`docs/index.md` § Knowledge Base Ledger section (line ~51):**
   - Add sentence after current description: "The ledger is maintained quarterly via [FINDINGS-LEDGER-002] cadence checklist (`plans/active/FINDINGS-LEDGER-002/cadence_checklist.md`); rerun when >10 findings change in a month or after major initiative closures."

2. **`docs/fix_plan.md` Working Agreements (line ~6):**
   - Add bullet under "Working Agreements" after Plan Directory Inventory rule:
     ```markdown
     - **Findings Ledger Cadence:** Rerun [FINDINGS-LEDGER-002] maintenance quarterly or when >10 findings are added/resolved. Follow `plans/active/FINDINGS-LEDGER-002/cadence_checklist.md` and commit artifacts to timestamped reports directory.
     ```

**Validation:** Grep both files after edits to confirm cross-references are correct.

---

## Loop Scope (C.1 + C.3 only)

**This loop implements:**
- C.1: Author `cadence_checklist.md` template (147–231 lines estimated based on template structure above)
- C.3: Update `docs/index.md` (1 sentence addition, ~line 51) and `docs/fix_plan.md` (1 bullet addition, ~line 11)
- Validation: Regenerate cross-reference matrix to confirm cadence_checklist path is discoverable

**Defer C.2 (automation)** to future loop when manual cadence proves insufficient or when plan inventory tooling expansion warrants it.

---

## Artifacts (This Loop)

**Created:**
- `plans/active/FINDINGS-LEDGER-002/cadence_checklist.md` (new file, template)
- `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T100000Z/planning_notes.md` (this file)
- `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T100000Z/summary.md` (Ralph to create after implementation)

**Updated:**
- `docs/index.md` (Knowledge Base Ledger section)
- `docs/fix_plan.md` (Working Agreements)
- `plans/active/FINDINGS-LEDGER-002/implementation.md` (mark C.1/C.3 done, C.2 deferred)

---

## Next Loop Actions

After C.1/C.3 complete:
1. Validate cadence checklist is reachable from `docs/index.md` cross-reference
2. Mark Phase C complete in implementation.md
3. Update fix_plan.md FINDINGS-LEDGER-002 Attempts History with Phase C completion timestamp + artifacts path
4. Consider initiative closure: all exit criteria satisfied (ledger integrity ✓, cross-linking ✓, cadence ✓, automation artifact ✓ via Phase A inventory)

---

## References
- `plans/active/FINDINGS-LEDGER-002/implementation.md` (Phase C exit criteria)
- `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T080000Z/summary.md` (Phase B.2 completion)
- `docs/index.md:51` (Knowledge Base Ledger section)
- `docs/fix_plan.md:11` (Working Agreements)
