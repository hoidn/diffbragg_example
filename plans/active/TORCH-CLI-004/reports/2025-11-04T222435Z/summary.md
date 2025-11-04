# TORCH-CLI-004 Implementation Summary

## Problem Statement

**SPEC Reference:** `docs/spec-db-tracing.md:22` — "Telemetry payload SHALL be produced by the same code paths used in production (no re-derived physics)."

The `_write_torch_outputs` function (dbex/refine_one.py:364-450) failed when mocked ROI scores returned `MagicMock` objects instead of floats, causing:
1. `TypeError: '>=' not supported between instances of 'MagicMock' and 'float'` at line 449
2. `np.mean(scores)` producing NaN when scores contained non-numeric objects

This violated the requirement for stable, numeric diagnostics and blocked test execution.

## ADR Alignment

**DIAGNOSTICS-001** (`docs/findings.md:18-23`): Maintain `/torch_diagnostics` metadata contract while adjusting score coercion.

**SCALE-003** (`docs/findings.md:45-50`): Preserve refined/raw HKL telemetry attributes when editing diagnostics.

## Search Summary

1. Identified score collection at `dbex/refine_one.py:414-424` where `CHECKER.score()` returns are appended without coercion
2. Located aggregation logic at `dbex/refine_one.py:448-449` performing comparisons and mean/std calculations
3. Confirmed test harness at `tests/dbex/test_refine_one_cli.py:500-583` uses mocks that expose the fragility
4. No prior coercion guards existed in the codebase for ROI scores

## Implementation Changes

### 1. Score Coercion (dbex/refine_one.py:414-424)

```python
# Before:
score = CHECKER.score(dat_im, mod_im)
print("roi=%d : score= %.1f" % (i_sb, score*100))
scores.append(score)

# After:
score = CHECKER.score(dat_im, mod_im)
# TORCH-CLI-004: Coerce score to float to guard against mocks/non-scalars
score_float = float(score)
print("roi=%d : score= %.1f" % (i_sb, score_float*100))
scores.append(score_float)
```

### 2. Empty Collection Guard (dbex/refine_one.py:448-456)

```python
# Before:
print("Average score:", 100*np.mean(scores), "+-", 100*np.std(scores))
print("Fraction of spots well modeled= %.1f%%" % (100*sum([s >= 0.5 for s in scores])/len(scores), ))

# After:
# TORCH-CLI-004: Guard against empty scores collection
if len(scores) > 0:
    print("Average score:", 100*np.mean(scores), "+-", 100*np.std(scores))
    print("Fraction of spots well modeled= %.1f%%" % (100*sum([s >= 0.5 for s in scores])/len(scores), ))
else:
    print("Average score: N/A (no ROIs processed)")
    print("Fraction of spots well modeled= N/A (no ROIs processed)")
```

### 3. Test Assertions (tests/dbex/test_refine_one_cli.py:584-591)

Added numeric validation for score dataset:
```python
# TORCH-CLI-004: Verify score dataset contains numeric values (not Mock objects)
assert 'score' in h
scores_ds = h['score'][:]
assert len(scores_ds) == 1
assert isinstance(scores_ds[0], (int, float, np.number))
# Score should be numeric and finite (coercion guards against Mock objects)
assert np.isfinite(scores_ds[0])
assert 0.0 <= scores_ds[0] <= 1.0
```

## Test Results

### Targeted Tests

**Collect-only:**
```
pytest --collect-only tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
collected 1 item
```

**Execution:**
```
pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1
PASSED [100%]
1 passed in 0.92s
```

### Full Test Suite

```
pytest -v tests/
67 passed, 2 failed, 3 skipped in 350.96s
```

**Pre-existing failures** (unchanged from MAP-SCALE-005):
- `test_db_at_010_gradcheck_crystal_cell_a`
- `test_db_at_010_gradcheck`

## Metrics

- **Code changes:** 2 files modified (dbex/refine_one.py, tests/dbex/test_refine_one_cli.py)
- **Lines added/modified:** 11 lines
- **Test coverage:** 1 new assertion block (numeric score validation)
- **Regression status:** No new failures; test_torch_diagnostics_metadata now passes

## Artifacts

All artifacts stored in `plans/active/TORCH-CLI-004/reports/2025-11-04T222435Z/`:
- `collect_torch_diag.log` — Collection evidence (1 test)
- `pytest_torch_diag.log` — Targeted test execution (PASSED)
- `pytest_full_suite.log` — Full suite results (67 passed)
- `summary.md` — This document

## Next Actions

1. Mark TORCH-CLI-004 as `done` in `docs/fix_plan.md`
2. No new findings warranted (existing DIAGNOSTICS-001 and SCALE-003 remain applicable)
3. Consider archiving TORCH-CLI-004 artifacts during next housekeeping sweep
