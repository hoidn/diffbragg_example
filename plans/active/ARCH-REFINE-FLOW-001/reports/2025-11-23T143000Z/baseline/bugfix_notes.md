# Stage C Baseline Bugfixes (Phase D0)

## Summary
Two blocking bugs discovered and fixed during Phase D0 baseline capture for Stage C detector offset refinement.

## Bug 1: UnboundLocalError for RefinementTelemetry

**Location:** `dbex/nanobrag_refinement.py:3170`
**Root Cause:** Redundant local import `from dbex.nanobrag_refinement import RefinementTelemetry` inside the `elif stage_a_b_mode:` block (engine delegation path) created a local binding that shadowed the module-level class definition. When the inline path (`else:` block at line 3182) tried to use `RefinementTelemetry` at line 3474, Python's scoping rules saw the name used in an assignment context within the function and treated it as an uninitialized local variable.

**Fix:** Removed the redundant import at line 3170. The `RefinementTelemetry` class is already defined at module level (line 392), so no import is needed.

**Patch:** `unbound_local_error_fix.patch`

## Bug 2: NameError for baseline_detector_distances

**Location:** `dbex/nanobrag_refinement.py:4267, 3874`
**Root Cause:** The variable `baseline_detector_distances` is computed inside the `_build_stage_a_params` helper function (line 863-871) but not returned in the helper's output dict. The inline Stage C code (lines 3874, 4267) references this variable for telemetry (to report initial detector offsets relative to nominal geometry), but it's not in scope.

**Fix:** Added `baseline_detector_distances` computation at the start of the Stage C inline block (line 3830-3834):
```python
baseline_detector_distances = None
if baseline_detector is not None:
    baseline_detector_distances = [
        baseline_detector[pid].get_directed_distance() for pid in range(n_panels)
    ]
```

**Patch:** `stage_c_bugfix.patch` (includes both fixes)

## Rationale
Per CLAUDE.md exception for local source bugfixes: both bugs blocked critical baseline capture (Phase D0) and were scoped to locally available source code under the workspace. Fixes are minimal, targeted, and preserve existing behavior (no API changes, no refactoring). Patches saved for reproducibility.

## Test Validation
- **Before fixes:** test_stage_c_detector_microslip[small] FAILED (UnboundLocalError → NameError)
- **After fixes:** test_stage_c_detector_microslip[small] PASSED (1 passed, 16.00s)
- **Rebuild:** No rebuild required (Python source changes only)

## Next Steps
- Run test_stage_c_detector_microslip[full] to complete Phase D0 baseline capture
- Document fixes in docs/findings.md if Stage C extraction proceeds (Phase D1+)
