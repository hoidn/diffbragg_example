# FINDINGS-LEDGER-002 Phase C — Cadence & Automation Planning

**Loop:** i=122
**Date:** 2025-12-07T062406Z
**Actor:** Galph (Supervisor / Planner)
**Phase:** C — Cadence, Tooling, and Working Agreements
**Status:** Planning

---

## Context

Phase A (ledger audit, 100% path:line coverage) and Phase B (cross-linking, 78.4% consumer coverage) are complete. Phase C must establish a recurring maintenance cadence so the findings ledger remains accurate and actionable as the codebase evolves.

**Prior Artifacts:**
- Phase A.2: `plans/active/FINDINGS-LEDGER-002/reports/2025-12-03T120250Z/` (audit report, inventory JSON/CSV)
- Phase B.1: `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T060000Z/` (consumer mapping)
- Phase B.2: `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T080000Z/` (reciprocal annotations, consumer_map_v2.json)

---

## Phase C Goals (from implementation.md:74-79)

1. **C1 — Cadence Definition:** Author a checklist (e.g., quarterly) covering rerun command, artifact expectations, and sign-off procedure. Reference it in `docs/index.md` + `docs/fix_plan.md`.

2. **C2 — Automation Hook (Optional/Tier-2):** If warranted, implement a small helper script under `plans/active/FINDINGS-LEDGER-002/bin/` that emits `findings_inventory.json` to reduce manual toil. Document usage + tests.

3. **C3 — Guardrail Update:** Update Working Agreements / plan inventory instructions so the cadence becomes part of the broader doc graph (similar to the plan inventory guard).

---

## Scope Analysis

### C1 — Cadence Definition

**Proposed Cadence:** Quarterly (every ~3 months or ~12 supervisor loops)

**Checklist Items:**
1. Re-audit `docs/findings.md`:
   - Verify all entries have `path:line` citations
   - Check status tags match reality (Active/Resolved/Deferred)
   - Flag stale or obsolete findings for retirement

2. Update consumer cross-links:
   - Review fix_plan.md for new initiatives
   - Add "Governed by" lines to new initiatives
   - Annotate new findings with "**Consumers:** [ID]." metadata

3. Generate inventory artifacts:
   - Run inventory script (if exists) or manual audit
   - Produce `findings_inventory.json` + `findings_audit.md`
   - Update coverage metrics in fix_plan.md Attempts History

4. Sign-off:
   - Record cadence run timestamp in galph_memory.md
   - Commit changes with standard FINDINGS-LEDGER-002 prefix

**Documentation Targets:**
- `docs/index.md` § Knowledge Base Ledger → Add "Maintenance Cadence" subsection
- `docs/fix_plan.md` § Working Agreements → Reference FINDINGS-LEDGER-002 cadence checklist

### C2 — Automation Hook

**Assessment:** Phase A.2 already produced semi-automated inventory via Python script (`plans/active/FINDINGS-LEDGER-002/reports/2025-12-03T120250Z/findings_inventory.py`). However, it was a one-off analysis script, not a reusable tool.

**Proposal:**
- Create `plans/active/FINDINGS-LEDGER-002/bin/findings_inventory.py` as a canonical reusable script
- Script should:
  - Parse `docs/findings.md` (markdown table format)
  - Validate each finding has ID, Status, path:line citation
  - Generate JSON inventory with coverage stats
  - Produce human-readable audit report
  - Exit non-zero if coverage drops below threshold (e.g., <70% path:line coverage)

**Benefits:**
- Reduces manual toil for quarterly cadence
- Provides machine-readable output for future automation (CI/CD hooks, plan inventory integration)
- Enables regression detection (coverage percentage trending)

**Testing Strategy:**
- Unit test: parse sample markdown table, verify JSON output schema
- Integration test: run against current `docs/findings.md`, expect 100% path:line coverage (86/86 findings per Phase A.2)
- Document usage in `plans/active/FINDINGS-LEDGER-002/bin/README.md`

**Scriptization Policy Compliance:**
- Thin wrapper: delegates to stdlib markdown/JSON modules (no shadow pipelines)
- Lives under initiative `bin/` per ARCH-PROBE-FREEZE-001 precedent
- Growth cap: ~200-300 LOC expected (parsing + validation + JSON output)
- Not decision-carrying for acceptance tests (pure tooling/housekeeping)

### C3 — Guardrail Update

**Working Agreements Changes:**

1. Add to `docs/fix_plan.md` § Working Agreements (after line 11):
   ```markdown
   - **Findings Ledger Cadence:** Rerun FINDINGS-LEDGER-002 Phase C checklist quarterly (~12 supervisor loops).
     Execute: `python plans/active/FINDINGS-LEDGER-002/bin/findings_inventory.py --fix-plan docs/fix_plan.md --findings docs/findings.md --out-dir plans/active/FINDINGS-LEDGER-002/reports/<NEW_TIMESTAMP>/`
     Verify coverage ≥70% path:line citations, update consumer cross-links, commit with `[FINDINGS-LEDGER-002 CADENCE]` prefix.
   ```

2. Add to `docs/index.md` § Knowledge Base Ledger (after line 51):
   ```markdown
   ### Maintenance Cadence
   The findings ledger undergoes quarterly audits to ensure accuracy and actionability. Each cadence run:
   - Validates 100% of findings have path:line citations
   - Updates consumer cross-links with new initiatives
   - Retires obsolete findings to archive
   - Generates machine-readable inventory (JSON) + human audit report

   **Run Command:** See `docs/fix_plan.md` § Working Agreements for execution details.
   ```

**Plan Inventory Integration:**
- The existing plan inventory guard (`PORTFOLIO-STATUS`) already references findings.md implicitly (via roll-up initiative "Governed by" lines)
- No changes needed to `plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py` unless we want it to consume `findings_inventory.json` for coverage warnings

---

## Implementation Strategy

### Phase C.1 (Cadence Definition)

**Deliverables:**
1. `plans/active/FINDINGS-LEDGER-002/cadence_checklist.md` — Detailed quarterly checklist with rerun commands, artifact expectations, sign-off procedure
2. `docs/index.md` update — Add "Maintenance Cadence" subsection to § Knowledge Base Ledger
3. `docs/fix_plan.md` update — Add cadence reminder to § Working Agreements

**Validation:**
- Manual review: verify checklist completeness against Phase A/B artifacts
- Doc consistency: ensure index.md ↔ fix_plan.md ↔ cadence_checklist.md all reference each other

**Mapped Tests:** None (docs-only)

**Estimated Effort:** 1 planning loop (this loop: Galph drafts checklist, Ralph implements doc updates)

### Phase C.2 (Automation Hook)

**Deliverables:**
1. `plans/active/FINDINGS-LEDGER-002/bin/findings_inventory.py` — Reusable inventory script with JSON output
2. `plans/active/FINDINGS-LEDGER-002/bin/README.md` — Usage documentation with examples
3. `tests/findings/test_findings_inventory.py` — Unit + integration tests

**Validation:**
- Unit test: parse mock findings table → verify JSON schema
- Integration test: run against `docs/findings.md` → expect 100% path:line coverage (86/86)
- Regression guard: script exit non-zero if coverage <70%

**Mapped Tests:**
- `tests/findings/test_findings_inventory.py::test_parse_findings_table`
- `tests/findings/test_findings_inventory.py::test_inventory_integration`

**Estimated Effort:** 1-2 implementation loops (script authoring + tests)

**Deferral Option:** If automation is deemed low-priority, defer C.2 to a future cadence run and rely on manual audit for now. Document deferral rationale in Phase C summary.

### Phase C.3 (Guardrail Update)

**Deliverables:**
1. `docs/fix_plan.md` § Working Agreements update — Add cadence rerun command
2. `docs/index.md` § Knowledge Base Ledger update — Add "Maintenance Cadence" subsection

**Validation:**
- Doc consistency guard: verify both files reference FINDINGS-LEDGER-002 cadence
- Manual review: ensure rerun command is copy-pasteable and correct

**Mapped Tests:** None (docs-only)

**Estimated Effort:** Same loop as C.1 (parallel doc updates)

---

## Risks & Mitigations

1. **Risk:** Automation script becomes a shadow pipeline (duplicates plan inventory logic)
   - **Mitigation:** Keep script focused on findings.md parsing only; do not replicate plan inventory rollup logic. If integration needed, have plan_inventory.py consume findings_inventory.json as input.

2. **Risk:** Cadence checklist becomes stale as codebase evolves
   - **Mitigation:** Include "Review and update this checklist" as step 0 of the cadence run; treat checklist as living document.

3. **Risk:** Quarterly cadence is too infrequent (findings drift out of sync)
   - **Mitigation:** Monitor coverage percentage trend over 2-3 cadence runs; adjust to monthly if coverage drops consistently.

4. **Risk:** Automation script fails on malformed markdown (e.g., pipe characters in Summary column)
   - **Mitigation:** Robust parsing with explicit error messages; fallback to manual audit if script fails; validate against current findings.md structure during Phase C.2 testing.

---

## Exit Criteria Alignment

| Exit Criterion (from implementation.md:24-29) | Phase C Deliverables |
|-----------------------------------------------|---------------------|
| Cadence & Guardrails: `docs/index.md` and `docs/fix_plan.md` describe maintenance cadence | C.1 + C.3: checklist + doc updates |
| Cadence checklist stored under initiative reports or bin/ | C.1: cadence_checklist.md |
| Automation Artifact: Machine-readable inventory lives in reports directory | C.2: findings_inventory.py generates JSON |
| Rerun command documented | C.3: fix_plan.md § Working Agreements includes copy-pasteable command |

---

## Proposed Do Now (for Ralph, next loop)

**Mode:** Docs
**ActionType:** planning → implementation_ready (C.1 + C.3 docs-only; C.2 optional/deferred)
**DecisionStatus:** patch_ready (exact doc sections known)

**Implement:**
1. **C.1 + C.3 (Priority 1 — Docs-only, no automation):**
   - Create `plans/active/FINDINGS-LEDGER-002/cadence_checklist.md` with quarterly checklist (template below)
   - Update `docs/index.md` § Knowledge Base Ledger: add "Maintenance Cadence" subsection after line 51
   - Update `docs/fix_plan.md` § Working Agreements: add cadence rerun command after line 11
   - Validate doc consistency: all 3 files cross-reference each other

2. **C.2 (Priority 2 — Automation, deferred to future loop if time-constrained):**
   - Create `plans/active/FINDINGS-LEDGER-002/bin/findings_inventory.py` (parsing + JSON output)
   - Create `plans/active/FINDINGS-LEDGER-002/bin/README.md` (usage docs)
   - Create `tests/findings/test_findings_inventory.py` (unit + integration tests)
   - Validate: script runs against `docs/findings.md` → produces JSON with 100% path:line coverage (86/86)

**Mapped Tests:**
- None (C.1 + C.3 docs-only)
- `tests/findings/test_findings_inventory.py` (C.2 automation, if implemented)

**Artifacts:** `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T062406Z/`

**Forbidden This Loop:** No production code changes (docs/tooling only per housekeeping initiative type)

---

## Cadence Checklist Template (for C.1 deliverable)

```markdown
# FINDINGS-LEDGER-002 Quarterly Cadence Checklist

**Run Frequency:** Every ~12 supervisor loops (~3 months)
**Responsible:** Galph (Supervisor)
**Artifacts Root:** `plans/active/FINDINGS-LEDGER-002/reports/<TIMESTAMP>/`

---

## Pre-Run

- [ ] Check last cadence run timestamp in `galph_memory.md` or `docs/fix_plan.md` Attempts History
- [ ] Verify ≥12 loops have elapsed since last run (or ~3 months calendar time)
- [ ] Review this checklist for updates (treat as living document)

## Execution

### Step 1: Audit findings.md

- [ ] Read `docs/findings.md` in full
- [ ] For each finding entry:
  - [ ] Verify `path:line` citation exists (at least one code/spec reference)
  - [ ] Check Status tag matches reality (Active / Resolved / Deferred / Retracted)
  - [ ] Flag stale findings (no consumer, referenced code deleted, spec changed)
- [ ] Record audit results in `<TIMESTAMP>/findings_audit.md`

### Step 2: Update consumer cross-links

- [ ] Read `docs/fix_plan.md` Tier 0-4 initiatives
- [ ] For new initiatives created since last cadence:
  - [ ] Add "Governed by" lines citing relevant findings
  - [ ] Update findings.md Summary column with "**Consumers:** [INITIATIVE-ID]." metadata
- [ ] Regenerate `consumer_map.json` (or run automation script if available)
- [ ] Calculate coverage percentage: `findings_with_consumers / total_active_findings`

### Step 3: Generate artifacts

- [ ] Option A (Automation): Run `python plans/active/FINDINGS-LEDGER-002/bin/findings_inventory.py --fix-plan docs/fix_plan.md --findings docs/findings.md --out-dir plans/active/FINDINGS-LEDGER-002/reports/<TIMESTAMP>/`
- [ ] Option B (Manual): Create `findings_inventory.json` manually from audit notes
- [ ] Verify JSON schema matches Phase B.2 format (phase, timestamp, total_active_findings, coverage_percentage, initiatives, notes)
- [ ] Write `<TIMESTAMP>/summary.md` with coverage stats and notable changes since last run

### Step 4: Archive obsolete findings

- [ ] For findings flagged as stale:
  - [ ] Validate with pytest (if applicable): confirm referenced code/test is truly obsolete
  - [ ] Move to "Archived" section in `docs/findings.md` OR delete if redundant
  - [ ] Document rationale in `<TIMESTAMP>/findings_audit.md`
- [ ] Update `docs/fix_plan_archive.md` if archiving findings that govern completed initiatives

### Step 5: Doc graph sync

- [ ] Update `docs/fix_plan.md` Attempts History for FINDINGS-LEDGER-002:
  - [ ] Add new attempt entry with cadence run timestamp
  - [ ] Record coverage percentage and artifact path
  - [ ] Note any new initiatives created or findings archived
- [ ] Verify `docs/index.md` § Knowledge Base Ledger references this cadence
- [ ] Commit changes with `[FINDINGS-LEDGER-002 CADENCE] <summary>` prefix

## Post-Run

- [ ] Record cadence run timestamp in `galph_memory.md` focus field
- [ ] Schedule next cadence run (~12 loops / ~3 months from now)
- [ ] If coverage dropped below 70%, open issue for next cadence to investigate

---

## Notes

- **Coverage Target:** Maintain ≥70% consumer coverage (findings with at least one initiative consumer)
- **Trend Monitoring:** Track coverage percentage over time; adjust cadence frequency if drift accelerates
- **Tool Maturity:** This checklist assumes automation script exists (Phase C.2); if not, rely on manual audit (Steps 1-3 Option B)
```

---

## Next Action

Galph issues Do Now to Ralph: implement Phase C.1 + C.3 (docs-only cadence definition + guardrail updates). Defer Phase C.2 (automation script) to a future loop if Ralph signals time constraints or prefers to validate cadence checklist manually first.

**Expected Outcome:** FINDINGS-LEDGER-002 Phase C.1 + C.3 complete, cadence checklist documented, quarterly maintenance guardrails established in doc graph.

---

**Artifacts:** This planning note + cadence_checklist.md template ready for Ralph to commit under `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T062406Z/`
