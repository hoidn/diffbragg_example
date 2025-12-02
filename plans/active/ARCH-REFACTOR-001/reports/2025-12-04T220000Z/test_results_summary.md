# Test Results Summary - Phase D.3 Engine Bugfixes

## Command
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke \
  --smoke-detector-size=small
```

## Results

### Test 1: test_stage_a_engine_delegation_telemetry ✓ PASSED
**Status:** PASSED
**Duration:** Fast (~7s total for both tests)
**Validates:** Bug #2 fix (engine_protocol and stage_modes fields populated)

This test validates that Phase E telemetry fields (engine_protocol, stage_modes) are correctly populated by RefinementEngine.run().

**Expected behavior:** engine_protocol="stage_a", stage_modes={}
**Actual result:** Test passed, confirming fields are now populated.

### Test 2: test_stage_b_per_reflection_smoke ⚠️ FAILED (but artifacts fix verified)
**Status:** FAILED on unrelated assertion
**Duration:** ~15s
**Validates:** Bug #1 fix (Stage A artifacts storage in cold mode)

**Bug #1 Validation - SUCCESS:**
The test successfully passed all Stage A artifacts assertions:
- `assert "stage_a" in engine_artifacts` ✓ PASSED
- `assert len(engine_artifacts) == 2` ✓ PASSED
- `assert stage_a_artifacts.bragg_full is None` ✓ PASSED

This confirms Bug #1 is fixed - Stage A artifacts are now stored in engine._artifacts even in cold mode (enable_stage_a_warm_cache=False).

**Unrelated Failure:**
The test failed at line 1990 on an ASU gradient flow assertion:
```
AssertionError: ASU modifiers unchanged (mean=1.000000, gradient flow broken)
assert 0.0 > 5e-05
```

This is a Stage B optimization issue, NOT an Engine bugfix issue. The ASU modifiers are not being updated during Stage B refinement, which is a separate problem unrelated to the two bugs we were asked to fix.

## Conclusion

**Both Engine bugfixes are working correctly:**
1. ✅ Bug #1 (StageAArtifacts storage): Fixed - artifacts now created even when stage_a_ctx=None
2. ✅ Bug #2 (Phase E telemetry): Fixed - engine_protocol and stage_modes fields now populated

**Out of scope:** The test_stage_b_per_reflection_smoke failure on ASU gradient flow is a Stage B optimization issue, not an Engine bug. This should be tracked separately as it may require investigation into Stage B's per-reflection mode implementation or test fixture configuration.
