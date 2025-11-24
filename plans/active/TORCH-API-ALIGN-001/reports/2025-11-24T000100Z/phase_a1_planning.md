# Phase A1 Planning — DIALS Mapping Parity Validation

**Timestamp:** 2025-11-24T000100Z
**Focus:** TORCH-API-ALIGN-001 Phase A1 (DIALS Mapping Parity Test Implementation)
**Status:** Planning complete → ready_for_implementation

## Context

Phase B factory wiring COMPLETE (Exit Criterion #1 ✓ SATISFIED: factory used by all forward-only paths, -79 lines eliminated). Phase B3 RESCOPED (ExperimentModel adapter blocked by upstream bug ARCH-FACTORY-003; Exit Criterion #3 rescoped to "blocker documented, adapter deferred").

**Next objective:** Validate Exit Criterion #2 (DIALS mapping parity tests pass) via Phase A1 test implementation.

## Phase A1 Objective

Implement `test_dials_mapping_parity` (currently xfail stub in `tests/dbex/test_bridge_mapping.py`) to validate DIALS convention mapping behavior:

1. **Beam-center swap:** (fast, slow) → (s, f) coordinate transformation
2. **Euler angle extraction:** Panel rotation axes → Euler angles via analytic inversion
3. **custom_beam_vector ignored:** DIALS convention does NOT forward explicit −s0 (documented behavior)
4. **End-to-end parity:** Forward simulation output matches expected behavior on tiny fixture

## Implementation Strategy

### Test Structure

1. **Fixture construction:**
   - Minimal dxtbx beam (1.0 Å wavelength, default direction [0,0,1])
   - Minimal dxtbx panel (100x100 px, 0.1 mm pixel size, simple rotation)
   - DetectorConfig via `create_detector_config(detector, convention=DetectorConvention.DIALS)`

2. **Validation assertions:**
   - Beam-center swap: `detector_config.beam_center_mm_slow` vs `detector_config.beam_center_mm_fast` match expected (s,f) from (fast,slow)
   - Euler angles: Extract from `detector_config` and compare against expected from panel rotation matrix
   - custom_beam_vector ignored: Build two configs (with/without custom_beam_vector), assert identical DetectorConfig outputs

3. **Forward parity (optional):**
   - Run factory-based forward simulation on tiny HKL grid
   - Assert non-zero output (sanity check, no crash)
   - Document that DIALS ignores `custom_beam_vector` in test docstring

### Findings Applied

- **GEOMETRY-001:** DIALS beam-center swap convention (fast,slow)→(s,f)
- **GEOMETRY-002:** Analytic Euler angle inversion from rotation matrix
- **CONFIG-001:** DetectorConvention enum usage
- **CONFIG-002:** Beam-center swap in config hydration
- **PERF-WARM-001:** Warm-cache OFF pattern (warm_cache_off fixture)
- **ARCH-ENGINE-002:** Lazy imports (if needed for dxtbx/nanobrag_torch)
- **POLICY-001:** Environment Freeze (dbex-only test, no engine changes)

### Validation Protocol

**Primary test:** `tests/dbex/test_bridge_mapping.py::test_dials_mapping_parity`

**Expected outcome:** PASS (DIALS mapping validated)

**Regression guards:** None (test-only change, no production code modified)

**xfail removal:** Remove `@pytest.mark.xfail` decorator after implementation validates

### Estimated Effort

**1 loop** (~1.5-2 hours):
- Fixture construction: 30 min
- Assertion implementation: 45 min
- Validation + debug: 30 min
- Documentation + commit: 15 min

### Risk Assessment

**Low risk:**
- No production code changes (test implementation only)
- Factory wiring already proven correct (Phase B2 DB-AT-024 PASSED)
- DIALS mapping logic exists (bridge helpers already use it)
- Tiny fixture (<100x100 px) ensures fast execution

**Potential blockers:**
1. dxtbx import issues (LOW: existing tests use dxtbx)
2. Euler angle extraction API unclear (LOW: documented in GEOMETRY-002)
3. custom_beam_vector test unclear (MEDIUM: may need to inspect bridge implementation)

**Mitigation:** If blocked on custom_beam_vector validation, document expected behavior and defer assertion to Phase C (CUSTOM override).

## Decision Paths

**Path A: Test PASS**
- Remove xfail marker
- Update implementation.md A1 checklist COMPLETE
- Run `pytest --collect-only` and update test registry (TESTING_GUIDE.md + TEST_SUITE_INDEX.md)
- Commit Phase A1 completion
- Proceed to Exit Criteria assessment (check if #2, #5, #6 satisfied)

**Path B: Test FAIL (assertion error)**
- Debug DIALS mapping logic in bridge helpers
- Compare actual vs expected beam-center/Euler values
- Document delta in blocker report
- Return to Galph for investigation

**Path C: Import/Runtime Error**
- Log exact error + traceback
- Check dxtbx availability
- Verify bridge helper imports
- Document blocker, return to Galph

## Implementation Floor Compliance

✓ **Production code task:** Test implementation (~80-120 lines in test_bridge_mapping.py)
✓ **Validating pytest selector:** tests/dbex/test_bridge_mapping.py::test_dials_mapping_parity
✓ **Artifacts path:** plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T000100Z/

**Dwell status:** Last loop (2025-11-23T~19:00:00Z) was Galph review_or_housekeeping (Phase B3 rescope decision), this loop (2025-11-24T000100Z) is Galph planning (Phase A1 strategy). Dwell=0 for planning state. Next loop MUST be ready_for_implementation per max-1-docs-only-loop rule.

## Next Actions

Ralph executes Phase A1 implementation protocol (7 steps):
1. Read Phase A1 planning + review DIALS mapping spec sections
2. Implement test_dials_mapping_parity (~80-120 lines: fixture construction, 3-4 assertions, docstring)
3. Remove xfail marker, run test
4. If PASS: update implementation.md checklist, run pytest --collect-only, commit
5. If FAIL: document blocker (actual vs expected values), return to Galph
6. Update test registry (TESTING_GUIDE.md + TEST_SUITE_INDEX.md) after test PASS
7. Write decision.md + summary.md

## References

- **Spec:** docs/nanobrag_api.md:44-47 (DIALS convention), docs/config_crosswalk.md:29 (beam-center swap)
- **Findings:** docs/findings.md GEOMETRY-001/002, CONFIG-001/002
- **Implementation plan:** plans/active/TORCH-API-ALIGN-001/implementation.md:42-45 (Phase A1 checklist)
- **Test stub:** tests/dbex/test_bridge_mapping.py:36-61 (current xfail stub)
