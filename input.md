# Input for Ralph (Loop i=183)

## Summary
Fix compute_z_scores() signature mismatch in parity_loader.py:604-607 to unblock FORWARD-EQUIV-COVERAGE-001 closure.

## BindingForRalph
- **ActionType:** debug→implementation_ready
- **DecisionStatus:** patch_ready
- **InitiativeType:** bug fix (signature mismatch)

## SupervisorMode
Debug → Implementation (bug fix)

## Focus
FORWARD-EQUIV-COVERAGE-001 — Forward Equivalence & Parity Harness — Phase A.5 (GAP-1 fix)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_db_at_001_parity.py` (DB_AT_001 selector)
- `tests/dbex/test_forward_equivalence_complete.py`
- `tests/dbex/test_forward_equivalence.py`

## Artifacts
`plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T120000Z/`

## Findings Applied (Mandatory)
- **TESTING-003**: Use canonical selectors from TESTING_GUIDE.md
  - Adherence: Use DB_AT_001 selector for validation
- **DIAGNOSTICS-001**: Artifact directory structure
  - Adherence: Store artifacts under `reports/2025-12-08T120000Z/`

## Pointers
- Bug location: `tests/fixtures/parity_loader.py:604-607`
- Target signature: `dbex/vis/residuals.py:12-18`
- Spec reference: `docs/spec-db-core.md` (variance = model + sigma_readout²)
- Phase A summary (prior loop): `plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T110000Z/summary.md`

---

## ARCH Contracts (mandatory)
- **Environment Freeze**: No package installs
  - Owner: CLAUDE.md
  - Classification: Bug fix only
- **Test Registry Sync**: Update if test selector changes
  - Owner: TESTING-003
  - Classification: No selector changes expected

---

## Do Now

**Focus:** FORWARD-EQUIV-COVERAGE-001 Phase A.5 (GAP-1 fix)

**Implement:** `tests/fixtures/parity_loader.py::write_parity_artifacts` — fix compute_z_scores() call

**Validating Pytest Selector:** `pytest -v tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence_complete.py tests/dbex/test_forward_equivalence.py -k DB_AT_001`

### Background

Phase A reality check (i=182) identified GAP-1:
- **Bug**: `parity_loader.py:604-607` calls `compute_z_scores(target, predicted)` with 2 args
- **Target signature** (`residuals.py:12-18`): `compute_z_scores(data, model, variance, mask=None, sigma_floor=None)`
- **Missing**: Required `variance` positional argument

Per `docs/spec-db-core.md`, variance is computed as:
```
variance = model + sigma_readout²
```
where `sigma_readout = 5 ADU` (standard detector readout noise).

### Phase A.5 Tasks

#### A5.1 — Fix parity_loader.py:604-607

Current code (lines 602-607):
```python
        # Standardized residual triptych for quick visual inspection.
        # Use a simple Z-score style residual consistent with dbex.vis helpers.
        z_scores = compute_z_scores(
            target,
            predicted,
        )
```

Required fix:
```python
        # Standardized residual triptych for quick visual inspection.
        # Use a simple Z-score style residual consistent with dbex.vis helpers.
        # Per spec-db-core.md: variance = model + sigma_readout² where sigma_readout=5 ADU
        sigma_readout = 5.0
        variance = predicted + sigma_readout ** 2
        z_scores = compute_z_scores(
            target,
            predicted,
            variance,
        )
```

**Note**: `predicted` is the model array, so `variance = predicted + sigma_readout**2` per spec.

#### A5.2 — Run DB_AT_001 Tests

Execute test suite with artifact capture:
```bash
cd /home/ollie/Documents/diffbragg_example
export ART=plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T120000Z
mkdir -p $ART
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence_complete.py tests/dbex/test_forward_equivalence.py -k DB_AT_001 2>&1 | tee $ART/pytest_db_at_001_fixed.log
```

**Expected**: 15/15 PASS (previously 12/15 with 3 failing on compute_z_scores)

#### A5.3 — Update Summary

Append to or create `$ART/summary.md` documenting:
1. Fix applied (file:line, before/after)
2. Test results (15/15 PASS expected)
3. GAP-1 status: RESOLVED

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example
export ART=plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T120000Z
mkdir -p $ART

# A5.1: Fix is applied via Edit tool (see Do Now)

# A5.2: Run tests after fix
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py tests/dbex/test_forward_equivalence_complete.py tests/dbex/test_forward_equivalence.py -k DB_AT_001 2>&1 | tee $ART/pytest_db_at_001_fixed.log

# A5.3: Write summary via Write tool
```

---

## Forbidden This Loop
- **No package installs** — Environment Freeze
- **No new test files** — Fix existing code only
- **No changes to residuals.py** — Callers must adapt to signature

## Pitfalls To Avoid
1. **Use `predicted` for variance base** — `predicted` IS the model; `variance = predicted + sigma_readout²`
2. **sigma_readout = 5.0 ADU** — Standard detector readout noise per spec-db-core.md
3. **Do not modify compute_z_scores signature** — Fix the caller, not the callee
4. **Check test count** — Should be 15 total tests, expecting 15 PASS

## If Blocked
If tests still fail after fix:
1. Document the exact error
2. Check if any OTHER callers of compute_z_scores have the same issue
3. Record in summary.md and request further investigation

---

## Exit Criteria Validation (Phase A.5)

| Criterion | Expected | Validation |
|-----------|----------|------------|
| A5.1 Fix applied | parity_loader.py:604-607 updated | Edit tool success |
| A5.2 Tests pass | 15/15 PASS | pytest_db_at_001_fixed.log |
| A5.3 Summary updated | GAP-1 resolved | summary.md |

---

## Output Artifacts Expected

1. `$ART/pytest_db_at_001_fixed.log` — Test execution output showing 15/15 PASS
2. `$ART/summary.md` — Phase A.5 fix summary

---

## Next Up (optional)
If 15/15 tests pass after fix:
- Proceed to Phase B (Closure Validation) to complete PARITY-HARNESS-002 E1-E3
