# Input for Ralph: FORWARD-EQUIV-COVERAGE-001 Phase B (Closure Validation)

## Summary
Complete PARITY-HARNESS-002 Phase E closure tasks and FORWARD-EQUIV-COVERAGE-001 Phase B, then prepare roll-up for closure in Phase C.

## Focus
`FORWARD-EQUIV-COVERAGE-001` — Forward Equivalence & Parity Harness Roll-up

## Branch
`integration`

## Mapped Tests
- Primary: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001`
- Collect-only: `pytest --collect-only tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence_complete.py`

## Artifacts
`plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T130000Z/`

---

## Do Now

**Focus Item:** FORWARD-EQUIV-COVERAGE-001 Phase B

**Implement:** PARITY-HARNESS-002 Phase E closure (E1-E3) + FORWARD-EQUIV-COVERAGE-001 B1-B4

### Phase B Tasks (FORWARD-EQUIV-COVERAGE-001)

**B1: Complete PARITY-HARNESS-002 Phase E closure tasks**
- [ ] E1 — Exit criteria audit: Re-run the authoritative selector to confirm 15/15 PASS:
  ```bash
  KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T130000Z/pytest_db_at_001_closure.log
  ```
- [ ] E2 — Ledger closure: Update `plans/active/PARITY-HARNESS-002/implementation.md` to mark E1-E3 as complete with `[x]`
- [ ] E3 — Archive readiness: Author `plans/active/PARITY-HARNESS-002/reports/2025-12-08T130000Z/closing/closure_summary.md` with:
  - Outstanding simulator-dependent TODOs (Phase C was synthetic-only; real nanobrag_torch pending)
  - Reference to CONFORMANCE-001, TESTING-003, PARITY-001 findings

**B2: Update docs/TESTING_GUIDE.md**
- Verify DB_AT_001 selector documentation in section 2 is accurate for the current 15-test suite
- Add collect-only artifact reference if missing

**B3: Update docs/development/TEST_SUITE_INDEX.md**
- Verify unified forward-equiv entries exist for DB_AT_001 selector
- Confirm row counts match collected tests (15)

**B4: Refresh docs/fix_plan.md**
- Update FORWARD-EQUIV-COVERAGE-001 detailed section status from `pending` to `in_progress (Phase B complete)`
- Add Attempts History entry for Phase B completion with artifact path

### Capture collect-only evidence:
```bash
pytest --collect-only tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence_complete.py -q 2>&1 | tee plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T130000Z/collect_db_at_001_closure.log
```

---

## How-To Map

1. Run authoritative pytest selector (expects 15/15 PASS)
2. Capture collect-only evidence
3. Update PARITY-HARNESS-002 implementation.md Phase E checkboxes
4. Create PARITY-HARNESS-002 closing directory and author closure_summary.md
5. Verify TESTING_GUIDE.md section 2 and TEST_SUITE_INDEX.md have accurate DB_AT_001 entries
6. Update fix_plan.md FORWARD-EQUIV-COVERAGE-001 status + Attempts History
7. Author summary.md for this loop

---

## Pitfalls To Avoid

1. **Do NOT modify production code** — this is docs/ledger-only closure
2. **Do NOT skip collect-only capture** — required by TESTING-003
3. **Do NOT mark roll-up as done yet** — Phase C will close the roll-up
4. **Do NOT install packages** — Environment Freeze in effect
5. **Preserve exact test selectors** — use `-k DB_AT_001` not broader patterns
6. **Archive logs under correct timestamp** — `2025-12-08T130000Z`
7. **Cross-reference findings** — CONFORMANCE-001, TESTING-003, PARITY-001 must appear in closure docs

---

## If Blocked

If pytest fails with unexpected errors:
1. Capture full traceback to artifact directory
2. Document failure signature in summary.md
3. Mark Phase B blocked in implementation.md
4. Do NOT attempt code fixes — report block to Galph

---

## Findings Applied

- **CONFORMANCE-001**: DB-AT parity profiles define canonical pytest selectors (`-k DB_AT_0XX`) and `KMP_DUPLICATE_LIB_OK=TRUE` — ADHERED (selector and env var specified)
- **TESTING-003**: Selector status transitions require `pytest --collect-only` evidence — ADHERED (collect-only capture in How-To Map)
- **PARITY-001**: Parity thresholds (correlation >= 0.2, localization >= 90%) — REFERENCED in closure docs

---

## Pointers

- PARITY-HARNESS-002 implementation: `plans/active/PARITY-HARNESS-002/implementation.md:24-28` (Phase E checklist)
- FORWARD-EQUIV-COVERAGE-001 implementation: `plans/active/FORWARD-EQUIV-COVERAGE-001/implementation.md:39-46` (Phase B checklist)
- DB_AT_001 spec: `docs/spec-db-conformance.md:23-26`
- Forward equivalence: `docs/forward_equivalence.md`
- Test registry: `docs/development/TEST_SUITE_INDEX.md`
- Testing guide: `docs/TESTING_GUIDE.md:56-90`
- fix_plan detailed section: `docs/fix_plan.md:425-444`

---

## Next Up (optional)

If Phase B completes early:
- Phase C: Roll-up closure (mark member plans done, update fix_plan.md status to done, author closure_summary.md)
