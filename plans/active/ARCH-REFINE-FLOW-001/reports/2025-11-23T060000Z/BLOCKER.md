# BLOCKER: Regression Guard Failure

**Loop:** i=194 (ralph)
**Date:** 2025-11-23T060000Z
**Initiative:** ARCH-REFINE-FLOW-001 Phase B1a-loop3

## Status

Refactoring INCOMPLETE due to runtime error in regression guard test.

## Error

```
status='error', message="'NoneType' object has no attribute 'zero_grad'"
```

Test: `test_stage_a_expansion`
Notice: `closure_evals': 0` - optimizer.step() failed immediately before calling closure

## Root Cause Hypothesis

The `params` list passed to LBFGS optimizer contains None values for optional parameterization modes (U-matrix, incremental UB). When the optimizer tries to call `zero_grad()` on None, it fails.

## Work Completed

1. ✓ Helper 3 extracted (`_run_stage_a_lbfgs`, lines 1729-1884)
2. ✓ Main function refactored to call all three helpers (lines 1970-2029)
3. ✓ Compilation passes
4. ✗ Regression guard FAILS with NoneType error

## Files Modified

- dbex/nanobrag_refinement.py

## Next Steps (for next loop)

1. Debug which parameter in `params` list is None
2. Fix parameter passing to ensure all values are valid tensors
3. Rerun regression guard until PASS
4. Complete telemetry comparison
5. Commit with full B1a completion message

## Artifacts

- pytest log: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060000Z/pytest_stage_a_expansion.log
- helper3 extraction summary: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060000Z/helper3_extraction_summary.md
- refactoring summary: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060000Z/refactoring_summary.md
