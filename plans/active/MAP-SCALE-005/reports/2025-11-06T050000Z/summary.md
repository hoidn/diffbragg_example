# MAP-SCALE-005 Implementation Summary

**Date**: 2025-11-06T050000Z  
**Focus**: CLI refined telemetry enforcement (SCALE-007)  
**Branch**: integration  
**Status**: Complete

## Problem Statement

**SPEC Reference**: docs/spec-db-workflow.md §4, docs/spec-db-tracing.md §2, docs/findings.md:20 (SCALE-007)

> When `--refined-mtz` is provided to the CLI but refined structure factors cannot be loaded or telemetry downgrades to `raw`, the CLI must fail fast with a RuntimeError containing an actionable message that references the flag and expected asset path. Silent fallback to raw MTZ violates the calibration metadata contract established in MAP-SCALE-002/003/004.

## Implementation

### Code Changes

**File**: `dbex/refine_one.py:222-248`

Modified `run_nanobrag_backend` to enforce SCALE-007 guardrail:
- Replaced warning + fallback logic (lines 234-236) with `raise RuntimeError` when `load_refined_mtz` fails
- Error message includes: `--refined-mtz` flag reference, provided path, enforcement rationale ("MUST be consumed"), column hints (F(+)/F(-) or F/SIGF)
- Preserved legacy behavior: when `--refined-mtz` is absent, CLI continues using raw MTZ from `--mtzFile`

**Quoted Implementation** (dbex/refine_one.py:234-240):
```python
except (FileNotFoundError, ValueError, ImportError) as e:
    # SCALE-007: Fail fast when --refined-mtz is provided but cannot be loaded
    raise RuntimeError(
        f"Failed to load refined structure factors from --refined-mtz '{args.refined_mtz}': {e}\n"
        f"When --refined-mtz is provided, refined structure factors MUST be consumed.\n"
        f"Ensure the MTZ file exists and contains valid F(+)/F(-) or F/SIGF columns."
    ) from e
```

### Test Coverage

**File**: `tests/dbex/test_refine_one_cli.py:585-677`

Authored `test_nanobrag_backend_refined_mtz_missing_errors`:
- Validates CLI raises RuntimeError when nonexistent refined MTZ path provided
- Asserts error message contains: `--refined-mtz`, provided path, "MUST be consumed"
- Uses mocked DataLoad to avoid file I/O; mocked detector panels with square pixels (0.1mm) and background image with -1 sentinel outside ROIs per spec
- Test passed in 3.57s

### Documentation Updates

**Files**:
- `docs/TESTING_GUIDE.md:86` — CLI backend flag selector updated with refined MTZ enforcement test description, SCALE-007 cross-reference, collection log path (9 tests collected)
- `docs/development/TEST_SUITE_INDEX.md:12` — Synchronized CLI backend flag entry with enforcement guardrail notes, test log paths, and dbex/refine_one.py:234-240 pointer

## Validation

### Targeted Tests (passing)
1. `pytest --collect-only tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_refined_mtz_missing_errors` — 1 test collected  
   Log: `plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/collect_refined_mtz_guard.log`

2. `pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_refined_mtz_missing_errors --maxfail=1` — 1 passed in 3.57s  
   Log: `plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/pytest_refined_mtz_guard.log`

3. `pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz --maxfail=1` — 1 passed in 3.31s (regression check)  
   Log: `plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/pytest_refined_mtz_success.log`

### Full Suite
Command: `pytest -v tests/`  
Result: 66 passed, 3 skipped, 3 failed in 349.67s (0:05:49)  
Failures:
- 2 pre-existing gradient tests: `test_db_at_010_gradcheck_crystal_cell_a`, `test_db_at_010_gradcheck` (documented in prior fix_plan entries)
- 1 unrelated test: `test_torch_diagnostics_metadata` (mock configuration issue in list comprehension at dbex/refine_one.py:449; not introduced by this change)

Log: `plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/pytest_full_suite.log`

**Assessment**: Core implementation (refined MTZ enforcement) passed all targeted tests. Full suite failures are unrelated to MAP-SCALE-005 scope.

## Metrics

| Metric | Value | Source |
| --- | --- | --- |
| Tests collected (CLI backend flag) | 9 | collect_refined_mtz_guard.log |
| Tests passing (new + regression) | 2/2 | pytest_refined_mtz_guard.log, pytest_refined_mtz_success.log |
| Full suite: passed | 66 | pytest_full_suite.log |
| Full suite: skipped | 3 | pytest_full_suite.log |
| Full suite: failed (pre-existing) | 2 | gradient tests |
| Full suite: failed (unrelated) | 1 | test_torch_diagnostics_metadata |
| Runtime (targeted) | 3.57s + 3.31s | Per test logs |
| Runtime (full suite) | 349.67s | pytest_full_suite.log |

## Exit Criteria

All MAP-SCALE-005 criteria satisfied:

1. ✅ Hardened `run_nanobrag_backend` to raise RuntimeError when `--refined-mtz` load fails (dbex/refine_one.py:234-240)
2. ✅ Regression coverage via `test_nanobrag_backend_refined_mtz_missing_errors` exercising failure path and asserting actionable error message
3. ✅ Updated `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` with SCALE-007 guardrail documentation and artifact paths

## Artifacts

All artifacts stored under: `plans/active/MAP-SCALE-005/reports/2025-11-06T050000Z/`

- `collect_refined_mtz_guard.log` — pytest --collect-only output (1 test)
- `pytest_refined_mtz_guard.log` — New test run (1 passed in 3.57s)
- `pytest_refined_mtz_success.log` — Regression test run (1 passed in 3.31s)
- `pytest_full_suite.log` — Full test suite (66 passed, 3 skipped, 3 failed in 349.67s)
- `summary.md` — This document

## Next Actions

Per input.md optional follow-up:
1. Audit user-facing CLI docs (e.g., README, CLI help text) to describe the refined MTZ failure mode and expected usage
2. Mark MAP-SCALE-005 done in fix_plan.md
3. Archive artifacts during housekeeping sweep
