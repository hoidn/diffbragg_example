# Phase B1a-loop3 Bugfix Summary

**Loop:** i=194 (Ralph)
**Date:** 2025-11-23T060500Z
**Initiative:** ARCH-REFINE-FLOW-001 Phase B1a-loop3 Bugfix
**Mode:** Implementation (straightforward bugfix)

## Problem Statement

Fixed params dict bug causing `'NoneType' object has no attribute 'zero_grad'` error in Phase B1a-loop3 regression guard test. The extraction of three Stage A helpers was successful, but the refactored code failed at runtime because the closure couldn't access the optimizer and params objects.

## Root Cause

The closure function (line 1562 in `_build_stage_a_lbfgs_closure`) tried to retrieve the optimizer from `param_values`:

```python
optimizer = param_values.get('optimizer')
```

However, the optimizer was only stored at the top level of `helper1_result` dict (line 1007), NOT in the `param_values` dict. Similarly, `params` was at the top level (line 1004) but not in `param_values`, causing `param_values.get('params', [])` at line 1073 to return an empty list.

When `optimizer.zero_grad()` (line 1563) was called on None, Python raised `AttributeError: 'NoneType' object has no attribute 'zero_grad'`.

## Fix Applied

Added TWO entries to the `param_values` dict in `_build_stage_a_params` helper (dbex/nanobrag_refinement.py:943-966):

1. Line 953: `'params': params,`  # List of Parameter objects for optimizer
2. Line 954: `'optimizer': optimizer,`  # LBFGS optimizer for closure

This ensures the closure can retrieve both the params list and the optimizer object from the `param_values` dict that it receives as a parameter.

## Verification

**Regression Guard:** test_stage_a_expansion PASSED (12.39s)
- Environment: DBEX_SMOKE_DETECTOR_SIZE=small, KMP_DUPLICATE_LIB_OK=TRUE, NANOBRAGG_DISABLE_COMPILE=1
- Selector: `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Result: 1 passed, 5 warnings

**Compilation:** PASSED (exit code 0)
- Module import: `python -c "import dbex.nanobrag_refinement"`

## Code Changes

**File:** dbex/nanobrag_refinement.py
**Lines modified:** 953-954 (2 lines added to param_values dict)

```diff
    param_values = {
        'initial_log_scale': initial_log_scale,
        'log_scale': log_scale,
        ...
        'orientation_vec': orientation_vec,
+       'params': params,  # List of Parameter objects for optimizer
+       'optimizer': optimizer,  # LBFGS optimizer for closure
        'q_params': q_params,
        ...
    }
```

## Phase B1a Completion Status

✓ **COMPLETE** — All 3 helpers extracted, main function refactored, regression guard PASSES

**Extraction Summary:**
- Helper 1 (`_build_stage_a_params`): ~328 lines (loop i=192)
- Helper 2 (`_build_stage_a_lbfgs_closure`): ~717 lines with TWO nested functions (loop i=193)
- Helper 3 (`_run_stage_a_lbfgs`): ~156 lines (loop i=194)
- Main function (`run_nanobrag_refinement`): Reduced by 692 lines

**All 3 parameterization modes preserved:**
- Default: cell + misset (8 DOF)
- U-matrix: cell + misset + quaternion (9 DOF)
- Incremental UB: log_scale + quaternion delta + cell deltas (10 DOF)

## Artifacts

- pytest_stage_a_expansion.log (regression guard test output)
- summary.md (this file)

## Next Actions

Phase B1b: Wrap extracted helpers in StageA.run() class method

### Turn Summary
Fixed params dict bug with two-line change adding params and optimizer to param_values dict.
Regression guard test_stage_a_expansion now PASSES (12.39s).
Phase B1a extraction COMPLETE: 3 helpers extracted, main function reduced by 692 lines, all parameterization modes intact.
Next: Phase B1b will wrap the extracted helpers in a StageA wrapper class.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060500Z/pytest_stage_a_expansion.log
