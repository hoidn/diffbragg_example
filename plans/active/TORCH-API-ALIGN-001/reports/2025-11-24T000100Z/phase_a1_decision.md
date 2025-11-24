# Phase A1 Decision — DIALS Mapping Parity Test COMPLETE

**Timestamp:** 2025-11-24T000100Z
**Focus:** TORCH-API-ALIGN-001 Phase A1 (DIALS Mapping Parity Test Implementation)
**Status:** Path A (PASS) → Phase A1 COMPLETE
**Confidence:** HIGH (~95%)

## Test Outcome

**Result:** PASS (1 test collected, 1 passed)

**Test selector:** `tests/dbex/test_bridge_mapping.py::test_dials_mapping_parity`

**Runtime:** 0.82s (mock panel/beam fixture, extremely fast)

## Metrics

### Beam-Center Swap Validation
- **Expected:** `beam_center_s = 5.0`, `beam_center_f = 5.0` (DIALS swap convention)
- **Actual:** `beam_center_s = 5.000000`, `beam_center_f = 5.000000`
- **Delta:** < 1e-6 (assertion tolerance met)
- **Status:** ✓ PASS

### Euler Angle Extraction
- **Expected:** Fields `detector_rotx_deg`, `detector_roty_deg`, `detector_rotz_deg` present
- **Actual:**
  - `detector_rotx_deg = 180.0`
  - `detector_roty_deg = -0.0`
  - `detector_rotz_deg = 0.0`
- **Status:** ✓ PASS (fields exist, values correspond to panel axes [fast=(1,0,0), slow=(0,-1,0), normal=(0,0,-1)])

## Implementation Summary

**Test implementation:** ~70 lines (replaced pytest.skip() stub)
- Mock panel/beam fixtures using `unittest.mock.Mock`
- Direct `create_detector_config` call (no intermediate factory needed)
- Beam-center swap assertions with 1e-6 tolerance
- Euler field existence checks (defer exact value validation to Phase C)
- Debug output captured in test log

**Production code changes:** 0 (test-only loop per Phase A1 spec)

**xfail marker:** Removed after test PASSED

## Decision Path

**Path A (PASS):** Test assertions satisfied, xfail removed, registry updated, Phase A1 marked complete.

**Rejected alternatives:**
- Path B (FAIL): Not applicable (test passed on first run after fixture corrections)
- Path C (Error): Not applicable (no import/runtime errors)

## Registry Updates

**TESTING_GUIDE.md §2:** Updated "DIALS Mapping Parity" row (line 138)
- Status changed from "Active (xfail)" to "Active"
- Canonical metrics added: `beam_center_s=5.0`, `beam_center_f=5.0`, Euler angles
- Artifacts path updated to `2025-11-24T000100Z`

**TEST_SUITE_INDEX.md:** Updated "TORCH-API-ALIGN-001: DIALS Mapping Parity (A1)" row (line 20)
- Status changed from "active (xfail)" to "active"
- Phase A1 completion timestamp added
- Collection updated to "1 test, 1 passed"

## Next Actions

**Immediate:** Commit Phase A1 completion with test implementation + registry updates

**Next focus (per Exit Criteria assessment):**
- Exit Criterion #2: "DIALS mapping parity tests pass on fixtures" ✓ SATISFIED (Phase A1 test passes)
- Exit Criterion #1: "Unified simulator factory used by forward helpers" ✓ ALREADY SATISFIED (Phase B2 complete)
- Exit Criterion #3: "ExperimentModel parity tests pass" — RESCOPED (upstream bug blocker)
- Exit Criterion #5: "Refactor leaves existing smoke/perf selectors green" ✓ SATISFIED (regression guards passed throughout Phase B)
- Exit Criterion #6: "Documentation/testing registry reflects new selectors" ✓ SATISFIED (registry updated this loop)

**Exit Criteria Status (4 of 6 satisfied, 1 rescoped):**
1. ✓ SATISFIED
2. ✓ SATISFIED (this loop)
3. RESCOPED (upstream blocker)
4. N/A (CUSTOM override optional, default OFF)
5. ✓ SATISFIED
6. ✓ SATISFIED (this loop)

**Recommendation:** Return to supervisor for Exit Criteria review. TORCH-API-ALIGN-001 is near completion with factory-only path (Exit Criteria #1, #2, #5, #6 complete; #3 rescoped; #4 deferred as optional).

## Findings Applied

- **GEOMETRY-001:** DIALS beam-center swap convention validated
- **GEOMETRY-002:** Euler angle fields extracted from panel rotation matrix
- **CONFIG-001:** DetectorConvention enum usage (DIALS)
- **CONFIG-002:** Beam-center swap in config hydration
- **PERF-WARM-001:** Warm-cache OFF pattern (fixture applied)
- **POLICY-001:** Environment Freeze (test-only loop, no production changes)

## Artifacts

- `pytest_dials_mapping.log` (test execution log with debug output)
- `pytest_collect.log` (collection validation)
- `phase_a1_planning.md` (pre-implementation planning)
- `phase_a1_decision.md` (this document)
- `summary.md` (Turn Summary)

## References

- **Spec:** `docs/nanobrag_api.md:44-47`, `docs/config_crosswalk.md:29`
- **Implementation plan:** `plans/active/TORCH-API-ALIGN-001/implementation.md:42`
- **Test source:** `tests/dbex/test_bridge_mapping.py:35-102`
- **Bridge code:** `dbex/nanobrag_bridge.py:279-459` (create_detector_config)
