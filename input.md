# Input for Ralph — Loop i=185

## Summary
Complete FORWARD-EQUIV-COVERAGE-001 Phase C roll-up closure (docs/ledger updates only).

## Focus
**FORWARD-EQUIV-COVERAGE-001** — Forward Equivalence & Parity Harness Roll-up

## Branch
`integration`

## Mapped Tests
- Selector: `-k DB_AT_001` (already validated 15/15 PASS in i=184)
- Verification: `pytest --collect-only tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001` (evidence already captured)

## Artifacts
`plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T143000Z/`

---

## Do Now

**Focus Item:** FORWARD-EQUIV-COVERAGE-001 Phase C (Roll-up Closure)

### Implement: Phase C Tasks (Docs/Ledger Only)

**C1: Mark member plans done in implementation.md (verify — likely already done)**
- File: `plans/active/FORWARD-EQUIV-001/implementation.md` — confirm status header says complete/done
- File: `plans/active/FORWARD-EQUIV-002/implementation.md` — confirm status header says complete/done
- File: `plans/active/PARITY-HARNESS-002/implementation.md` — confirm status header says complete/done (Phase E closure done in i=184)

**C2: Update fix_plan.md status to done**
- File: `docs/fix_plan.md`
- Location: Line ~427-428 (FORWARD-EQUIV-COVERAGE-001 detailed section)
- Change: `Status: in_progress (Phase B complete; ready for Phase C roll-up closure)` → `Status: **done**`
- Also update: Line ~58-60 (Execution Roadmap entry for FORWARD-EQUIV-COVERAGE-001) to show `done`
- Add: Attempts History entry for Phase C (i=185)

**C3: Author closure_summary.md for roll-up**
- File: `plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T143000Z/closure_summary.md`
- Include:
  - Roll-up completion date/loop
  - Member plan status matrix (all 3 done)
  - Exit criteria validation (3/3 met)
  - Test evidence summary (15/15 PASS, correlation=0.988, localization=1.0)
  - Outstanding TODOs (simulator-dependent work documented in PARITY-HARNESS-002 closure)
  - Artifact index

**C4: Update implementation.md Phase C checkboxes**
- File: `plans/active/FORWARD-EQUIV-COVERAGE-001/implementation.md`
- Mark C1-C4 as [x]
- Update status header to `done`

### Validating Selector
- Verification only (tests already passed in i=184): `pytest --collect-only tests -k DB_AT_001`
- Evidence capture: `collect_db_at_001_final.log`

---

## How-To Map

```bash
# Artifacts directory
mkdir -p plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T143000Z/

# Verify member plans (read-only check)
# FORWARD-EQUIV-001, FORWARD-EQUIV-002, PARITY-HARNESS-002 — confirm completion status

# Update fix_plan.md
# - Line ~58: FORWARD-EQUIV-COVERAGE-001 → done
# - Line ~427: Status → done
# - Add Attempts History entry

# Author closure_summary.md
# See content template below

# Update implementation.md Phase C
# Mark checkboxes [x], update status header

# Capture collect-only evidence
pytest --collect-only tests -k DB_AT_001 > plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T143000Z/collect_db_at_001_final.log 2>&1
```

---

## Pitfalls To Avoid

1. **DO NOT** run full test suite — tests already validated in i=184 (15/15 PASS)
2. **DO NOT** modify any production code — this is docs/ledger closure only
3. **DO NOT** modify test files — already complete
4. **DO** use exact timestamps for artifacts path (2025-12-08T143000Z)
5. **DO** update both Execution Roadmap entry AND detailed section in fix_plan.md
6. **DO** include artifact pointers in Attempts History entry
7. **DO** respect findings CONFORMANCE-001, TESTING-003 (selector documentation accuracy)

---

## If Blocked

If any unexpected issue arises:
1. Document the issue in summary.md
2. Keep FORWARD-EQUIV-COVERAGE-001 status as `in_progress`
3. Note the block reason in galph_memory.md (via Galph next loop)

---

## Findings Applied (Mandatory)

| Finding ID | Adherence |
|------------|-----------|
| CONFORMANCE-001 | DB_AT_001 selector canonical commands documented |
| TESTING-003 | collect-only evidence captured, registry entries verified |
| PARITY-001 | Thresholds (correlation>=0.2, localization>=90%) documented and met |

---

## Pointers

| Document | Relevance |
|----------|-----------|
| `plans/active/FORWARD-EQUIV-COVERAGE-001/implementation.md` | Phase C checklist |
| `docs/fix_plan.md:425-445` | Detailed section + Attempts History |
| `docs/fix_plan.md:58-60` | Execution Roadmap entry |
| `plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T130000Z/summary.md` | Phase B evidence |
| `docs/spec-db-conformance.md:23-26` | DB-AT-001 thresholds |

---

## Next Up (Optional)

If Phase C completes early:
1. Portfolio review — identify next Tier 1 unblocked item
2. Candidates: TOOLING-VIS-001, TORCH-REFINE-CLEANUP-001, or blocked item review
