# Implementation Plan: FORWARD-EQUIV-COVERAGE-001

## Initiative
- ID: FORWARD-EQUIV-COVERAGE-001
- Title: Forward Equivalence & Parity Harness Roll-up
- Status: in_progress (Phase A.5 complete, GAP-1 fixed 2025-12-08T120000Z; Phase B complete 2025-12-08T130000Z)

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
| PARITY-HARNESS-002 | Phases A-E complete | `implementation.md` all [x], closure_summary.md authored |

## Phase A — Member Plan Reality Check

### Checklist
- [x] A1: Run DB_AT_001 tests and verify all pass. Command: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 --smoke-detector-size=full`. Capture logs. **DONE (2025-12-08T110000Z)**: 12/15 pass, 3 fail due to PARITY-001 bug.
- [x] A2: Verify member plan checklists match implementation reality. Cross-reference test files with plan phases. **DONE**: All 3 member plans verified.
- [x] A3: Identify any gaps between claimed completion and actual state. Document discrepancies. **DONE**: GAP-1 (PARITY-001 bug: compute_z_scores() signature mismatch), GAP-2 (PARITY-HARNESS-002 E1-E3 pending).
- [x] A4: Author summary.md with member plan status matrix and gap analysis. **DONE**: `reports/2025-12-08T110000Z/summary.md`

### Exit Criteria for Phase A
- 3 DB_AT_001 test files verified (pass/fail with metrics)
- Member plan checklist status validated
- Gap analysis complete
- Summary.md authored

## Phase B — Closure Validation (Complete — 2025-12-08T130000Z)

### Checklist
- [x] B1: Complete PARITY-HARNESS-002 Phase E closure tasks (E1 audit, E2 ledger closure, E3 archive readiness). **DONE**: 15/15 tests PASS, closure_summary.md authored at `plans/active/PARITY-HARNESS-002/reports/2025-12-08T130000Z/closing/closure_summary.md`
- [x] B2: Verify docs/TESTING_GUIDE.md with DB_AT_001 selector documentation. **DONE**: Both forward equiv (1 test) and parity harness (14 tests) entries accurate in section 2
- [x] B3: Verify docs/development/TEST_SUITE_INDEX.md with unified forward-equiv entries. **DONE**: Entries present and accurate (line ~195-197)
- [x] B4: Refresh docs/fix_plan.md with closure metrics. **DONE**: Attempts History updated with Phase B completion (i=184)

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
