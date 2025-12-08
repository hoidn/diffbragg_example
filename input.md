# Input for Ralph (Loop i=163)

## Summary
Execute SPEC-SQUARE-PARTIALITY-001 Phase C (Ledger Closure) — update fix_plan.md, ARCH-SIM-CONSTRUCTION-001 implementation.md, test registry docs, and verify initiative closure.

## BindingForRalph
- **ActionType:** implementation_ready
- **DecisionStatus:** patch_ready
- **InitiativeType:** spec+tests (spec_change + harness)

## SupervisorMode
Docs (non-binding — registry sync and ledger closure)

## Focus
SPEC-SQUARE-PARTIALITY-001 — SQUARE Lattice Spec & Test Alignment (Phase C)

## Branch
integration

## Mapped Tests
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/architecture/test_nanobrag_partiality.py` — capture collect-only log for registry sync
- (No pytest execution required — Phase C is docs-only registry sync)

## Artifacts
`plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T130000Z/`

## Findings Applied (Mandatory)
- **SIM-CONSTR-PARTIALITY-001** — Already marked "Resolved (physics clarified 2025-12-08; test updates in Phase B)" with correct linear scaling enforced. No further update needed (C4 satisfied).
- **PROBE-FREEZE-001** — Respected (no new plan-local scripts created).

## Pointers
- Plan: `plans/active/SPEC-SQUARE-PARTIALITY-001/implementation.md` — Phase C checklist
- Fix-plan row: `docs/fix_plan.md` Tier 1 — [SPEC-SQUARE-PARTIALITY-001] and [ARCH-SIM-CONSTRUCTION-001]
- Test registry: `docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`
- Finding: `docs/findings.md` line 168 — SIM-CONSTR-PARTIALITY-001 (already Resolved)

## ARCH Contracts (mandatory)
1. **ARCH-CONTRACT-TESTING-003**: Test registry synchronization — tests/architecture selectors must appear in TEST_SUITE_INDEX.md
   - Owner: `docs/development/TEST_SUITE_INDEX.md`
   - Classification: implementation work (registry sync pending for partiality test)

---

## Do Now

**Focus:** SPEC-SQUARE-PARTIALITY-001 Phase C (Ledger Closure)

### Implement: `docs/fix_plan.md` + `docs/development/TEST_SUITE_INDEX.md` + `docs/TESTING_GUIDE.md` + `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md`

Execute Phase C tasks (C1-C4) to close the initiative:

#### C1: Update `docs/fix_plan.md` (2 edits)
1. **Mark SPEC-SQUARE-PARTIALITY-001 as done:**
   - Find the [SPEC-SQUARE-PARTIALITY-001] row in Tier 1
   - Change status from `in_progress` to `done`
   - Update description: `Phase C complete (ledger closure 2025-12-08T130000Z)`
   - Add Attempts History entry for Phase C
2. **Update ARCH-SIM-CONSTRUCTION-001 status note:**
   - Add a note in the ARCH-SIM-CONSTRUCTION-001 description referencing that SQUARE scaling expectation mismatch has been resolved via SPEC-SQUARE-PARTIALITY-001
   - Keep status as `blocked_pending_environment` (remaining issues are DBEX-side, not SQUARE scaling)

#### C2: Update `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md`
- Near the top or in a prominent location, add a note:
  ```
  **SQUARE Lattice Resolved (2025-12-08):** The SQUARE lattice expectation mismatch (C.34-C.39 probes) has been resolved by SPEC-SQUARE-PARTIALITY-001. The correct physics is: peak height ∝ (Na·Nb·Nc)², integrated intensity ∝ Na·Nb·Nc. Tests now enforce linear scaling. See `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T110000Z/`. Future work should NOT reopen vendor edits for SQUARE scaling unless Spec-DB changes.
  ```

#### C3: Update test registry docs
1. **`docs/development/TEST_SUITE_INDEX.md`** — Add a row for the partiality test:
   ```markdown
   | SQUARE Lattice Partiality | `tests/architecture/test_nanobrag_partiality.py` | Active | `docs/spec-db-core.md:60-140`, `docs/findings.md::SIM-CONSTR-PARTIALITY-001` | Validates SQUARE lattice scaling: integrated intensity ∝ Na×Nb×Nc (linear, NOT squared). Uses 400×400 detector for full solid-angle integration per Phase B.6 investigation. 7% tolerance accommodates sinc² sidelobe oscillations. 2 tests (cpu/cuda). Runtime: ~12s. Environment: `KMP_DUPLICATE_LIB_OK=TRUE`. First added 2025-12-08 (SPEC-SQUARE-PARTIALITY-001). |
   ```
   (Insert in the appropriate location in the table, e.g., after the ARCH-GRADIENT-FLOW-001 row)

2. **`docs/TESTING_GUIDE.md`** — Add a brief entry in §2 (Quick Reference Commands) if not already present. Minimal addition:
   ```markdown
   | SQUARE Lattice Partiality | `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/architecture/test_nanobrag_partiality.py` | spec-db-core.md:60-140 |
   ```
   (If §2 doesn't have a table, add a brief subsection or append to existing architecture tests section)

#### C4: Verify finding closure (already done)
- **SIM-CONSTR-PARTIALITY-001** is already marked "Resolved" at line 168 of `docs/findings.md`
- No additional edit required — just confirm during review

#### C5: Update implementation.md
- Mark Phase C tasks (C1-C4) as complete in `plans/active/SPEC-SQUARE-PARTIALITY-001/implementation.md`

#### C6: Create summary.md
- Write `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T130000Z/summary.md` documenting:
  - Phase C completion
  - Links to all artifact locations
  - Initiative exit criteria status (all 4 should be met)

#### C7: Capture collect-only log
- Run: `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/architecture/test_nanobrag_partiality.py > plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T130000Z/collect_partiality.log 2>&1`

### Validation
After edits, verify:
1. `docs/fix_plan.md` shows SPEC-SQUARE-PARTIALITY-001 status=done
2. `docs/development/TEST_SUITE_INDEX.md` contains partiality test row
3. `plans/active/SPEC-SQUARE-PARTIALITY-001/implementation.md` shows all Phase C tasks checked
4. Collect-only log exists at artifacts path

---

## How-To Map

```bash
# Set environment
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md

# Capture collect-only for registry sync
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/architecture/test_nanobrag_partiality.py > plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T130000Z/collect_partiality.log 2>&1

# Verify test collection (should show 2 tests)
cat plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T130000Z/collect_partiality.log | tail -5
```

## Pitfalls To Avoid
1. **Do not change test logic** — Phase C is docs-only; the partiality test already works per Phase B.7
2. **Do not create new plan-local scripts** — PROBE-FREEZE-001 applies
3. **Do not unblock ARCH-SIM-CONSTRUCTION-001** — it remains blocked for other reasons (DBEX layer issues); only add the SQUARE scaling resolution note
4. **Preserve existing fix_plan.md structure** — edit in place, don't reformat entire sections
5. **Match TEST_SUITE_INDEX.md format** — follow existing row structure exactly

## Forbidden This Loop
- No new probes
- No test logic changes
- No production code changes
- Do not mark ARCH-SIM-CONSTRUCTION-001 as done or unblocked

## If Blocked
If any registry file is unexpectedly missing or corrupt:
- Record the blocker in summary.md
- Skip that specific sync task
- Complete other Phase C tasks
- Mark SPEC-SQUARE-PARTIALITY-001 as `done_with_caveat` noting the blocked doc sync

---

## Exit Criteria Check (for summary.md)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Spec text explicitly states peak vs integrated SQUARE scaling | ✅ Phase A (SIM-CONSTR-PARTIALITY-001 updated 2025-12-08) |
| 2 | test_nanobrag_partiality.py enforces linear scaling, passes | ✅ Phase B.7 (2/2 PASS, 400×400 detector, 7% tolerance) |
| 3 | ARCH-SIM-CONSTRUCTION-001 ledger/impl updated re SQUARE resolution | 🔲 Phase C.1, C.2 |
| 4 | Test registry synchronized (TESTING_GUIDE.md, TEST_SUITE_INDEX.md) | 🔲 Phase C.3 |
