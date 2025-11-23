# Phase C0 Baseline Summary

## Test Result
**PASS** ✓

## Initial Blocker
NameError at `dbex/nanobrag_refinement.py:2657`: `canonical_roi_count` not defined in `run_nanobrag_refinement` scope.

## Targeted Bugfix Applied
**Policy**: Environment Freeze exception for locally available source code blocking critical path (per CLAUDE.md)

**Root Cause**: Variable `canonical_roi_count` defined in helper function `_build_stage_a_params` (line 873) but referenced in main function `run_nanobrag_refinement` where it's out of scope.

**Fix**: Replaced `canonical_roi_count` with `canonical_baseline["roi_count"]` (which IS in scope via `stage_a_context`) at three locations:
- Line 2657: `stage_b_total_work_items` initialization
- Line 3078: `stage_b_roi_count_total` telemetry
- Line 3079: `stage_b_roi_count_sampled` telemetry

**Patch**: `canonical_roi_count_scope_fix.patch`

## Test Details
- **Selector**: `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
- **Detector**: small
- **Exit code**: 0 (PASS)
- **Runtime**: ~14.77s
- **Environment**: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`

## Stage B Baseline Status
Test passed successfully after bugfix. Stage B inline code (pre-extraction) is now executable for small-detector smoke tests.

**Note**: Test is a smoke test that validates Stage B executes without error. Detailed telemetry extraction (chi-squared improvement, shell modifier values, ROI counts) would require test modifications to emit structured output, which is out of scope for baseline artifact collection.

## Artifacts
- `pytest_collect_stage_b.log` — Collection verification (1 test collected ✓)
- `pytest_stage_b_small.log` — Initial test failure with NameError traceback
- `pytest_stage_b_small_fixed.log` — Test PASS after bugfix
- `canonical_roi_count_scope_fix.patch` — Git diff of the fix
- `blocker.md` — Root cause analysis and fix documentation
- `summary.md` — This file

## File Sizes
```bash
$ ls -lh plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline/
```
- pytest_collect_stage_b.log: ~1KB
- pytest_stage_b_small.log: ~86KB (failure)
- pytest_stage_b_small_fixed.log: ~86KB (pass)
- canonical_roi_count_scope_fix.patch: ~1KB
- blocker.md: ~3KB
- summary.md: this file

## Next Steps
1. Update `docs/findings.md` with bugfix lesson (REFINE-009 or similar)
2. Mark Phase C0 COMPLETE in `plans/active/ARCH-REFINE-FLOW-001/implementation.md:180`
3. Commit baseline artifacts + bugfix
4. Galph plans Phase C1a-loop1 (extract `_build_stage_b_params` helper)

---
Created: 2025-11-23T061726Z
Test passed: 2025-11-23T061726Z (after bugfix)
