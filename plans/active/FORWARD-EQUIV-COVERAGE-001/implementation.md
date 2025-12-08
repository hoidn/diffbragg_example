# Implementation Plan: FORWARD-EQUIV-COVERAGE-001

## Initiative
- ID: FORWARD-EQUIV-COVERAGE-001
- Title: Forward Equivalence & Parity Harness Roll-up
- Status: in_progress (Phase A: Member Plan Reality Check)

## Goals
- Consolidate forward equivalence and parity harness infrastructure
- Ensure DB-AT-001 selector is stable and documented
- Verify all member plans are complete and properly tracked

## Exit Criteria
1. Parity thresholds documented: median ROI correlation >= 0.2, localization >= 90% per `docs/spec-db-conformance.md` DB-AT-001
2. Forward equivalence harness traces artifact requirements per `docs/forward_equivalence.md`
3. Ties to NANOBRAG-GOLDEN-001 dataset refreshes documented

## Member Plans
| Plan ID | Status | Evidence |
|---------|--------|----------|
| FORWARD-EQUIV-001 | Phases A-C complete (D1-D3 optional) | `implementation.md` all [x] for A-C |
| FORWARD-EQUIV-002 | All phases complete | `implementation.md` all [x] |
| PARITY-HARNESS-002 | Phases A-D complete, E pending | `implementation.md` E1-E3 unchecked |

## Phase A — Member Plan Reality Check

### Checklist
- [ ] A1: Run DB_AT_001 tests and verify all pass. Command: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001`. Capture logs.
- [ ] A2: Verify member plan checklists match implementation reality. Cross-reference test files with plan phases.
- [ ] A3: Identify any gaps between claimed completion and actual state. Document discrepancies.
- [ ] A4: Author summary.md with member plan status matrix and gap analysis.

### Exit Criteria for Phase A
- 3 DB_AT_001 test files verified (pass/fail with metrics)
- Member plan checklist status validated
- Gap analysis complete
- Summary.md authored

## Phase B — Closure Validation (if Phase A shows readiness)

### Checklist
- [ ] B1: Complete PARITY-HARNESS-002 Phase E closure tasks (E1 audit, E2 ledger closure, E3 archive readiness)
- [ ] B2: Update docs/TESTING_GUIDE.md with DB_AT_001 selector consolidation
- [ ] B3: Update docs/development/TEST_SUITE_INDEX.md with unified forward-equiv entries
- [ ] B4: Refresh docs/fix_plan.md with closure metrics

## Phase C — Roll-up Closure

### Checklist
- [ ] C1: Mark all member plans as done in their implementation.md
- [ ] C2: Update fix_plan.md status to done
- [ ] C3: Author closure_summary.md
- [ ] C4: Capture collect-only logs for all DB_AT_001 selectors

## Spec References
- `docs/forward_equivalence.md`
- `docs/spec-db-conformance.md` DB-AT-001
- `docs/TESTING_GUIDE.md` section 2

## Artifacts Index
- Reports root: `plans/active/FORWARD-EQUIV-COVERAGE-001/reports/`
