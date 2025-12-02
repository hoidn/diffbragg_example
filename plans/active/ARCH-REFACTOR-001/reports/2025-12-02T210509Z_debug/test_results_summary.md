# Phase D.3 Telemetry Key Mapping Fix — Test Results Summary

## Fix Applied
Added telemetry key mapping in `dbex/refinement/engine.py::run()` (lines 192-206) to convert internal stage names ("stage_a", "stage_b", "stage_c") to legacy labels ("A", "B", "C") before returning telemetry dict.

## Test Results: 3/5 PASSED ✓

### Passing Tests (3/5)
1. **test_stage_a_expansion** - PASSED
   - Validates Stage A crystal/misset parameter recovery
   - Telemetry key "A" found correctly

2. **test_stage_b_shell_modifiers** - PASSED
   - Validates Stage B shell modifier mode
   - Telemetry keys "A" and "B" found correctly

3. **test_stage_c_detector_microslip** - PASSED
   - Validates Stage C detector offset refinement
   - Telemetry keys "A" and "C" found correctly

### Failing Tests (2/5) - Secondary Issues
The telemetry key mapping fix is working correctly (tests no longer fail on `assert 'A' in telemetry_dict`), but two tests expose **pre-existing issues** from Phase D.3 Batch 1 migration:

4. **test_stage_a_engine_delegation_telemetry** - FAILED
   - **Issue**: `telemetry.engine_protocol` is `None` (expected "stage_a")
   - **Root cause**: Phase E engine delegation fields not being populated by RefinementEngine.run()
   - **Note**: This is a **missing feature** issue, not a telemetry key issue
   - **Error**:
     ```
     AssertionError: Expected engine_protocol='stage_a', got None
     assert None == 'stage_a'
     ```

5. **test_stage_b_per_reflection_smoke** - FAILED
   - **Issue**: Stage A artifacts not present in `engine._artifacts` dict
   - **Root cause**: Stage A not storing artifacts when followed by Stage B
   - **Note**: This is an **artifacts storage** issue, not a telemetry key issue
   - **Error**:
     ```
     AssertionError: Stage A artifacts missing from engine artifacts
     assert 'stage_a' in {'stage_b': StageBArtifacts(...)}
     ```

## Primary Fix Status: ✅ SUCCESS

The telemetry key mapping fix **successfully resolved the primary blocker**:
- **Before fix**: 5/5 tests failed with `"Stage A telemetry missing"` or `"Engine delegation must return 'A' telemetry key"`
- **After fix**: 3/5 tests pass, telemetry keys "A"/"B"/"C" working correctly across all tests

The 2 remaining failures are **different bugs** that were masked by the key mismatch issue:
1. Missing Phase E `engine_protocol` / `stage_modes` field population
2. Stage A artifacts not being stored when Stage B follows

## Recommendation

The telemetry key mapping fix should be **committed** as it successfully addresses the stated root cause in input.md. The 2 remaining test failures should be tracked as **separate follow-up items** for Galph to triage (likely spec_change or harness initiatives to either fix the missing functionality or adjust test expectations).

## Metrics
- Files changed: 1 (`dbex/refinement/engine.py`)
- Lines added: +15 (telemetry key mapping logic + comments)
- Tests fixed: 3/5 (60% success rate on telemetry key issue)
- Tests still broken: 2/5 (secondary issues, different root causes)
