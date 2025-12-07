# Input for Ralph — Loop i=123

## Summary
FINDINGS-LEDGER-002 Phase C (C.1 + C.3): Establish maintenance cadence checklist and update doc graph guardrails (docs-only).

## Metadata
- **Mode:** Docs
- **ActionType:** implementation_ready
- **DecisionStatus:** patch_ready
- **InitiativeType:** housekeeping/docs
- **Focus:** [FINDINGS-LEDGER-002] — Findings Ledger Upkeep & Knowledge Base Maintenance
- **Branch:** integration
- **Mapped tests:** none — docs-only (doc graph consistency validated by grep cross-references)
- **Artifacts:** `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T100000Z/`

## Findings Applied (Mandatory)
**No relevant findings** — this initiative IS the findings maintenance work.

## ARCH Contracts (mandatory)
**N/A** — documentation-only initiative, no production code changes.

## Do Now

**Context:**
Phase B complete (78.4% consumer coverage achieved 2025-12-07T080000Z). Phase C ready: establish quarterly maintenance cadence and embed it in doc graph guardrails. Planning notes at `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T100000Z/planning_notes.md`.

**Scope this loop:** C.1 (cadence checklist template) + C.3 (guardrail doc updates). **Defer C.2 (automation script)** to future loop.

---

**Implement Phase C.1 + C.3:**

### 1. Create Cadence Checklist Template

**File:** `plans/active/FINDINGS-LEDGER-002/cadence_checklist.md`

**Content template** (from planning_notes.md lines 49–147):

```markdown
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
```

---

### 2. Update `docs/index.md` (Knowledge Base Ledger section)

**Location:** `docs/index.md` line ~49–51 (§ Operational Ledgers → Knowledge Base Ledger)

**Current text (approximate):**
```markdown
### [Knowledge Base Ledger](findings.md)
Description: Persistent record of architectural findings, runtime guardrails, and parity lessons for the torch integration.
Keywords: findings, guardrails, lessons
Use this when: Planning a loop or checking prior art before touching simulator/bridge code.
```

**Add after "Use this when:" line:**
```markdown
The ledger is maintained quarterly via [FINDINGS-LEDGER-002] cadence checklist (`plans/active/FINDINGS-LEDGER-002/cadence_checklist.md`); rerun when >10 findings change in a month or after major initiative closures.
```

---

### 3. Update `docs/fix_plan.md` (Working Agreements)

**Location:** `docs/fix_plan.md` lines ~6–11 (§ Working Agreements)

**Current bullets include:**
- Continue logging every loop...
- Status values: ...
- Citation rule remains: ...
- **Plan Directory Inventory:** Rerun `plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py` ...

**Add new bullet after "Plan Directory Inventory" rule:**
```markdown
- **Findings Ledger Cadence:** Rerun [FINDINGS-LEDGER-002] maintenance quarterly or when >10 findings are added/resolved. Follow `plans/active/FINDINGS-LEDGER-002/cadence_checklist.md` and commit artifacts to timestamped reports directory. Cross-reference cadence schedule in `docs/index.md` § Knowledge Base Ledger.
```

---

### 4. Update `plans/active/FINDINGS-LEDGER-002/implementation.md`

**Mark Phase C progress:**

Find Phase C section (lines ~74–79), update status bullets:
- **C1 — Cadence Definition:** DONE (2025-12-07T100000Z) — `cadence_checklist.md` template authored, 5-phase checklist with quarterly schedule, orphan triage, and artifact expectations.
- **C2 — Automation Hook (Optional/Tier-2):** DEFERRED — manual quarterly cadence sufficient; revisit if findings volume >150 or cadence frequency increases to monthly.
- **C3 — Guardrail Update:** DONE (2025-12-07T100000Z) — `docs/index.md` § Knowledge Base Ledger and `docs/fix_plan.md` Working Agreements updated with cadence cross-references.

**Add completion note after C3:**
```markdown
**Phase C complete (2025-12-07T100000Z):** Cadence checklist template delivered, guardrails updated in index.md + fix_plan.md. Artifacts: `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T100000Z/`. C.2 automation deferred to future loop.
```

---

### 5. Write Summary Artifact

**File:** `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T100000Z/summary.md`

**Content:**
```markdown
# FINDINGS-LEDGER-002 Phase C Summary

**Loop:** i=123
**Date:** 2025-12-07T100000Z
**Actor:** Ralph (Implementation Engineer)
**Phase:** C.1 + C.3 — Cadence & Guardrails
**Status:** ✅ COMPLETE (C.2 deferred)

---

## Deliverables

### 1. Cadence Checklist Template

**File:** `plans/active/FINDINGS-LEDGER-002/cadence_checklist.md` (new file, 147–231 lines)

**Structure:**
- 5-phase audit workflow (Active findings → Resolved findings → Orphans → Artifacts → Commit)
- Quarterly schedule + event-based triggers (>10 findings changed, major initiative closures)
- Orphan triage decision tree (create initiative, defer, retire)
- Expected artifacts: summary.md, findings_inventory.json, orphan_triage.md

**Integration:** Cross-referenced from `docs/index.md` § Knowledge Base Ledger and `docs/fix_plan.md` Working Agreements.

### 2. Guardrail Updates

**`docs/index.md` (line ~51):**
- Added cadence maintenance sentence with cross-reference to checklist path

**`docs/fix_plan.md` (Working Agreements, line ~12):**
- Added "Findings Ledger Cadence" bullet with quarterly schedule, triggers, and cross-reference

**Validation:** Grep confirmed both files reference `cadence_checklist.md` path correctly.

### 3. Implementation Plan Status

**`plans/active/FINDINGS-LEDGER-002/implementation.md` updated:**
- Phase C.1: DONE (cadence definition)
- Phase C.2: DEFERRED (automation hook — manual cadence sufficient)
- Phase C.3: DONE (guardrail updates)
- Phase C completion note added with artifact path

---

## Exit Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Cadence checklist authored | ✅ DONE | `cadence_checklist.md` template with 5-phase workflow |
| Quarterly schedule defined | ✅ DONE | "When to Run" section specifies quarterly + event-based triggers |
| Guardrails updated | ✅ DONE | `docs/index.md` + `docs/fix_plan.md` cross-reference cadence checklist |
| Checklist reachable from docs | ✅ DONE | Grep validation confirms cross-refs in index.md + fix_plan.md |
| Automation hook (optional) | ⏸️ DEFERRED | C.2 deferred to future loop (manual cadence sufficient) |

---

## Metrics

- **Files created:** 1 (`cadence_checklist.md`)
- **Files updated:** 3 (`docs/index.md`, `docs/fix_plan.md`, `implementation.md`)
- **Checklist phases:** 5 (Active audit, Resolved audit, Orphan triage, Artifacts, Commit)
- **Cadence frequency:** Quarterly (or >10 findings changed, or major initiative closure)
- **Automation deferral:** C.2 deferred — revisit if findings volume >150 or cadence goes monthly

---

## Phase C Lessons

1. **Quarterly cadence balances rigor with toil:** Manual 5-phase audit is tractable for ~75 findings quarterly; automation (C.2) can wait until findings volume exceeds 150 or cadence frequency increases.

2. **Event-based triggers reduce staleness risk:** Triggers for ">10 findings changed" and "major initiative closures" ensure ledger stays synchronized even if quarterly schedule slips.

3. **Orphan triage decision tree reduces ambiguity:** Explicit options (create initiative, defer, retire) with documented rationale prevent "forever Active" findings from accumulating.

4. **Cross-reference enforcement via doc graph:** Adding cadence to both `docs/index.md` (discovery) and `docs/fix_plan.md` (working agreements) ensures supervisors see the maintenance workflow during planning loops.

---

## Next Step

**Initiative closure evaluation:**
All FINDINGS-LEDGER-002 exit criteria satisfied:
1. ✅ Ledger integrity (Phase A: 100% path:line coverage)
2. ✅ Cross-linking (Phase B: 78.4% consumer coverage)
3. ✅ Cadence & guardrails (Phase C.1/C.3: checklist + doc updates)
4. ✅ Automation artifact (Phase A: findings_inventory.json)

**Action:** Next loop, mark FINDINGS-LEDGER-002 as **done**, update fix_plan.md status, and archive implementation plan.

---

**Artifacts:** `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T100000Z/` (planning_notes.md, summary.md, cadence_checklist.md cross-ref validation)
```

---

### 6. Validation

- [ ] Grep `cadence_checklist.md` in `docs/index.md` and `docs/fix_plan.md` to confirm cross-references exist
- [ ] Verify `cadence_checklist.md` file is readable and formatted correctly
- [ ] Confirm implementation.md Phase C section shows C.1/C.3 DONE, C.2 DEFERRED

---

**Commit hygiene:**
- Write Phase C summary to `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T100000Z/summary.md`
- Update `docs/fix_plan.md` [FINDINGS-LEDGER-002] Attempts History with Phase C completion timestamp + artifact path
- Commit message: `[FINDINGS-LEDGER-002] Phase C (C.1+C.3) — Cadence checklist + guardrails`

---

## Forbidden This Loop

- No production code edits (`dbex/`, `src/`, `tests/` source modules)
- No environment modifications
- No pytest runs (validation is doc-graph cross-reference check only)
- Do NOT implement C.2 (automation script) — deferred to future loop

## How-To Map

**N/A** — documentation edits only, no test runs.

**Validation commands:**
```bash
# Verify cross-references exist
grep -n "cadence_checklist.md" docs/index.md
grep -n "cadence_checklist.md" docs/fix_plan.md

# Verify cadence checklist is readable
cat plans/active/FINDINGS-LEDGER-002/cadence_checklist.md | head -20
```

## Pitfalls To Avoid

1. **Type discipline:** This is housekeeping/docs work (no spec_change, no architecture code changes, no C.2 automation this loop).
2. **Doc consistency:** Update docs/index.md + docs/fix_plan.md + implementation.md in the same loop to keep doc graph synchronized.
3. **Scope creep:** Do NOT implement C.2 automation — defer it explicitly in implementation.md.
4. **Cross-ref accuracy:** Ensure both index.md and fix_plan.md reference the exact same path: `plans/active/FINDINGS-LEDGER-002/cadence_checklist.md`.
5. **Checklist completeness:** Template must include all 5 phases (Active audit, Resolved audit, Orphan triage, Artifacts, Commit) with concrete steps, not just placeholders.
6. **Markdown formatting:** Preserve checklist checkbox syntax (`- [ ]`) and nested structure for readability.

## If Blocked

- If cadence_checklist.md template structure unclear, use planning_notes.md lines 49–147 verbatim as starting point.
- If doc cross-reference lines drift during editing, use section headers (e.g., "### [Knowledge Base Ledger]", "## Working Agreements") to locate insertion points instead of line numbers.
- If grep validation fails, manually verify cross-refs exist by reading both files.
- Record any blockers in `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T100000Z/blockers.md` and mark Phase C.1/C.3 as in_progress (not done).

## Doc Sync Plan

**N/A** — no test additions or renames this loop.
