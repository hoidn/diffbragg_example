# Input for Ralph (Loop i=182)

## Summary
Execute FORWARD-EQUIV-COVERAGE-001 Phase A: Reality check member plans (FORWARD-EQUIV-001, FORWARD-EQUIV-002, PARITY-HARNESS-002) and validate DB_AT_001 tests.

## BindingForRalph
- **ActionType:** evidence_collection
- **DecisionStatus:** exploring
- **InitiativeType:** roll-up reality check

## SupervisorMode
Evidence Collection (first Phase A for roll-up)

## Focus
FORWARD-EQUIV-COVERAGE-001 — Forward Equivalence & Parity Harness — Phase A

## Branch
integration

## Mapped Tests
- `tests/dbex/test_db_at_001_parity.py` (DB_AT_001)
- `tests/dbex/test_forward_equivalence_complete.py`
- `tests/dbex/test_forward_equivalence.py`

## Artifacts
`plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T110000Z/`

## Findings Applied (Mandatory)
- **PROBE-FREEZE-001**: No new persistent scripts
  - Adherence: Evidence collection only, use inline python -c for probe work
- **TESTING-003**: Use canonical selectors from TESTING_GUIDE.md
  - Adherence: Use DB_AT_001 selector per docs/TESTING_GUIDE.md
- **DIAGNOSTICS-001**: Artifact directory structure
  - Adherence: Store artifacts under `reports/2025-12-08T110000Z/`

## Pointers
- Roll-up implementation.md: `plans/active/FORWARD-EQUIV-COVERAGE-001/implementation.md` (Phase A checklist)
- Member plans:
  - `plans/active/FORWARD-EQUIV-001/implementation.md` (Phases A-C complete)
  - `plans/active/FORWARD-EQUIV-002/implementation.md` (All phases complete)
  - `plans/active/PARITY-HARNESS-002/implementation.md` (Phases A-D complete, E pending)
- Spec refs:
  - `docs/forward_equivalence.md` (harness requirements)
  - `docs/spec-db-conformance.md` DB-AT-001 acceptance criteria
- Test files:
  - `tests/dbex/test_db_at_001_parity.py`
  - `tests/dbex/test_forward_equivalence_complete.py`
  - `tests/dbex/test_forward_equivalence.py`

---

## ARCH Contracts (mandatory)
- **Environment Freeze**: No package installs
  - Owner: CLAUDE.md
  - Classification: Evidence collection only
- **Test Registry Sync**: Update TESTING_GUIDE.md if tests fail/change
  - Owner: TESTING-003
  - Classification: Document status

---

## Do Now

**Focus:** FORWARD-EQUIV-COVERAGE-001 Phase A (Member Plan Reality Check)

**Implement:** Evidence collection — run tests, verify checklists, identify gaps

**Validating Pytest Selector:** `pytest -v tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence_complete.py tests/dbex/test_forward_equivalence.py -k DB_AT_001`

### Background
- Dependency satisfied: NANOBRAG-GOLDEN-001 done
- Member plan analysis from implementation.md review:
  - **FORWARD-EQUIV-001**: Phases A-C complete (D1-D3 optional/deferred)
  - **FORWARD-EQUIV-002**: All phases complete
  - **PARITY-HARNESS-002**: Phases A-D complete, E1-E3 pending
- Roll-up likely ready for closure but needs validation

### Phase A Tasks

#### A1 — Run DB_AT_001 Tests
Execute test suite with artifact capture:
```bash
cd /home/ollie/Documents/diffbragg_example
export ART=plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T110000Z
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence_complete.py tests/dbex/test_forward_equivalence.py -k DB_AT_001 2>&1 | tee $ART/pytest_db_at_001.log
```
Record: pass/fail status, test count, runtime, any errors

#### A2 — Verify Member Plan Checklists
Cross-reference each member plan's implementation.md against test files:

| Member Plan | Claimed Status | Verify |
|-------------|----------------|--------|
| FORWARD-EQUIV-001 | A-C complete | `test_forward_equivalence_complete.py` exists |
| FORWARD-EQUIV-002 | All complete | `test_db_at_001_parity.py` exists with canonical fixtures |
| PARITY-HARNESS-002 | A-D complete | Parity harness utilities in tests/fixtures/parity_loader.py |

Tasks:
- Verify test files exist and reference golden data
- Confirm DB-AT-001 thresholds (correlation >= 0.2, localization >= 0.90) are enforced
- Check that manifest.json checksum validation is present

#### A3 — Identify Gaps
Document any discrepancies between claimed completion and reality:
- Missing test coverage
- Stale documentation references
- Pending items that should be resolved before closure

Focus areas:
- PARITY-HARNESS-002 Phase E (E1-E3) — closure validation unchecked
- Optional items in FORWARD-EQUIV-001 Phase D — assess if needed

#### A4 — Author Summary
Create `$ART/summary.md` with:
1. Member plan status matrix (verified)
2. Test results summary
3. Gap analysis
4. Recommendation: proceed to Phase B closure OR address gaps first

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example
export ART=plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T110000Z

# A1: Run DB_AT_001 tests
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence_complete.py tests/dbex/test_forward_equivalence.py -k DB_AT_001 2>&1 | tee $ART/pytest_db_at_001.log

# A1: Capture collect-only evidence
pytest --collect-only tests/dbex/ -k "DB_AT_001 or forward_equiv" 2>&1 | tee $ART/collect_db_at_001.log

# A2: Read member plan implementation.md files (already analyzed by Galph)
# Verify test file existence:
ls -la tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence*.py
ls -la tests/fixtures/parity_loader.py 2>/dev/null || echo "No parity_loader.py"

# A3: Check golden data manifest
ls -la tests/fixtures/golden_data/simple_cubic/

# A4: Write summary to $ART/summary.md via Write tool
```

---

## Forbidden This Loop
- **No production code changes** — Evidence collection only
- **No package installs** — Environment Freeze
- **No new persistent scripts** — PROBE-FREEZE-001

## Pitfalls To Avoid
1. **Don't skip test execution** — We need fresh validation even though member plans claim completion
2. **Check for golden data** — `tests/fixtures/golden_data/simple_cubic/` must exist for tests to pass
3. **Note any xfail markers** — Some tests may have conditional xfail; document current status
4. **Use KMP_DUPLICATE_LIB_OK=TRUE** — Required for torch tests
5. **Document test metrics** — Record correlation/localization values from output if available

## If Blocked
If tests fail or golden data is missing:
1. Document the specific failure/missing resource
2. Check if NANOBRAG-GOLDEN-001 artifacts exist at expected locations
3. Record block reason in summary.md
4. Recommend remediation in gap analysis

---

## Exit Criteria Validation (Phase A)

| Criterion | Expected | Validation |
|-----------|----------|------------|
| A1 Tests run | Pass/fail captured | pytest_db_at_001.log |
| A2 Checklists verified | 3/3 member plans | Summary matrix |
| A3 Gaps identified | Document or "none" | Gap analysis section |
| A4 Summary authored | Exists | summary.md |

---

## Output Artifacts Expected

1. `$ART/pytest_db_at_001.log` — Test execution output
2. `$ART/collect_db_at_001.log` — Test collection evidence
3. `$ART/summary.md` — Phase A analysis with:
   - Member plan status matrix
   - Test results summary (count, pass/fail, metrics)
   - Gap analysis
   - Recommendation for Phase B

---

## Next Up (optional)
If Phase A shows all member plans complete with passing tests:
- Proceed to Phase B (Closure Validation) which includes completing PARITY-HARNESS-002 E1-E3
