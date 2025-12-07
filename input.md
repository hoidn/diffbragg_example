# Input for Ralph (Loop i=130)

## Summary
Complete MAP-SCALE-005 Phase B (Option A): Add regression test validating CLI refined MTZ enforcement + update ARCH-CONTRACT documentation to reflect existing guard implementation.

## Mode
none

## ActionType
implementation_ready

## DecisionStatus
patch_ready

## InitiativeType
spec_change

## Focus
[MAP-SCALE-005] — CLI refined telemetry enforcement

## Branch
integration

## Mapped Tests
- `tests/dbex/test_refine_one_cli.py::test_refined_mtz_missing_file_fails_fast` (new test, expect PASS)
- `tests/dbex/test_refine_one_cli.py::test_refined_mtz_telemetry_provenance` (new test, expect PASS)
- `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` (regression check, expect PASS)

## Artifacts
`plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/`

## Findings Applied (Mandatory)
- **SCALE-007** (Active): "Zero-iteration bridge must emit structure-factor telemetry and DB_AT_024 must fail when refined assets present but telemetry reports raw or missing."
  - **Adherence**: Phase B implements regression tests ensuring CLI guard at `refine_one.py:382-389` is validated and cannot be silently removed.
  - **Gap closed**: Phase A discovered guard exists; Phase B adds automated enforcement per SCALE-007 requirement.

- **TESTING-003** (Active): "Selector status transitions to Active only after pytest --collect-only confirms >0 tests collected."
  - **Adherence**: Phase B will capture `pytest --collect-only` logs for new test selectors and update TEST_SUITE_INDEX.md.

## ARCH Contracts (Mandatory)

### ARCH-CONTRACT-CALIBRATION-001
- **Owner**: `dbex/refine_one.py::run_nanobrag_backend` (lines 375-393)
- **Current State**: Guard implemented (fail-fast on refined MTZ load failure)
- **Documentation Drift**: ARCH-CONTRACT-CALIBRATION-001 currently states "falls back silently" (incorrect per Phase A evidence)
- **Failure Classification**: Documentation bug (implementation correct, docs wrong)
- **Phase B Action**: Update ARCH-CONTRACT-CALIBRATION-001 description from "falls back silently" to "fails fast per spec-db-workflow.md:47"

### SCALE-007 (Enforcement via tests)
- **Owner**: `dbex/refine_one.py::run_nanobrag_backend` (CLI guard) + `tests/dbex/test_refine_one_cli.py` (test enforcement)
- **Current State**: CLI guard exists, test coverage missing
- **Failure Classification**: Implementation bug within architecture (guard exists, tests missing)
- **Phase B Action**: Add regression tests ensuring guard behavior is validated

## Do Now (Hard Validity Contract)

**Focus**: MAP-SCALE-005 Phase B - Regression Test Addition + ARCH-CONTRACT Update

**Implement**:
1. **Test Module** (`tests/dbex/test_refine_one_cli.py`):
   - Add `test_refined_mtz_missing_file_fails_fast`: Verify RuntimeError raised when `--refined-mtz` points to missing file, no HDF5 output written
   - Add `test_refined_mtz_telemetry_provenance`: Verify `hkl_source="raw"` when flag omitted, `hkl_source="refined"` when valid refined MTZ provided
   - Reuse existing fixtures/mocks from test_torch_diagnostics_metadata

2. **Documentation Updates**:
   - Update ARCH-CONTRACT-CALIBRATION-001 (location TBD - check `docs/architecture_contracts.md` or inline code comments)
   - Add cross-reference from guard code (`refine_one.py:382-389`) to spec-db-workflow.md:47
   - Update `docs/findings.md`: Add note that SCALE-007 CLI enforcement validated by test coverage

3. **Test Registry Updates**:
   - Update `docs/TESTING_GUIDE.md` with new selector descriptions
   - Update `docs/development/TEST_SUITE_INDEX.md` with test status

**Validating pytest**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
pytest -vv tests/dbex/test_refine_one_cli.py::test_refined_mtz_missing_file_fails_fast \
              tests/dbex/test_refine_one_cli.py::test_refined_mtz_telemetry_provenance \
              tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
```

**Artifacts**:
- Pytest logs (targeted + collect-only) → `plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/`
- Phase B summary documenting test coverage + doc updates
- Updated ARCH-CONTRACT text (quote before/after)

**Initiative Type Consistency**: `spec_change` (validating/documenting normative CLI behavior per spec-db-workflow.md:47)

## Forbidden This Loop
- No new probes or instrumentation
- No production code changes to guard (already correct at refine_one.py:382-389)
- Do not implement Option C (reimplementing existing guard)

## How-To Map
1. **Author Tests** (~50 lines total):
   - `test_refined_mtz_missing_file_fails_fast`: Mock `load_refined_mtz` to raise FileNotFoundError, assert pytest.raises(RuntimeError, match="refined")
   - `test_refined_mtz_telemetry_provenance`: Run with/without `--refined-mtz`, assert HDF5 `/torch_diagnostics` attrs

2. **Run Targeted Pytest**:
   ```bash
   pytest -vv tests/dbex/test_refine_one_cli.py::test_refined_mtz_missing_file_fails_fast \
                tests/dbex/test_refine_one_cli.py::test_refined_mtz_telemetry_provenance \
     > plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/pytest_targeted.log 2>&1
   ```

3. **Collect-Only Evidence**:
   ```bash
   pytest --collect-only tests/dbex/test_refine_one_cli.py \
     > plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/pytest_collect_only.log 2>&1
   ```

4. **Update Docs**:
   - Locate ARCH-CONTRACT-CALIBRATION-001 (grep for it in docs/)
   - Update description text, add code reference
   - Update findings.md with SCALE-007 validation note
   - Update TESTING_GUIDE.md + TEST_SUITE_INDEX.md

5. **Write Phase B Summary**:
   - Document test coverage added
   - Quote ARCH-CONTRACT before/after text
   - Link to SCALE-007 compliance
   - Mark Phase B complete

## Pitfalls to Avoid
1. **Type Discipline**: This is `spec_change` (documenting/validating normative behavior), not `bugfix` (no production code changes needed)
2. **No Stacking**: Guard already correct; only add test coverage
3. **Findings Paydown**: SCALE-007 explicitly requires test enforcement - must deliver regression coverage
4. **Evidence→Action**: Tests must fail if guard is removed (validates SCALE-007 intent)
5. **Environment Freeze**: Use existing pytest framework, no package changes
6. **Backward Compatibility**: Tests codify existing behavior, zero risk
7. **Implementation Floor**: This is implementation (test code), not docs-only
8. **Probe Saturation**: N/A (no probes, pure test addition)
9. **Shadow Pipeline Guard**: N/A (no plan-local scripts)
10. **ARCH Conformance**: Documentation alignment, not structural change

## If Blocked
- If ARCH-CONTRACT-CALIBRATION-001 doesn't exist: Create it inline as code comment at refine_one.py:382 with spec citation
- If test mocking proves complex: Use tmp_path fixture to create actual missing file instead of mocking
- If HDF5 telemetry assertions fail: Check that torch_diagnostics group structure matches existing test patterns
- Mark blocked with reason, switch focus to PHYSICS-LOSS-001 Tier 1 cleanup or DB-AT-SUITE-CARE-001 scoping

## Doc Sync Plan (Conditional)
**Not Required** - Existing test module being extended, no new files or test discovery changes needed. Collect-only run validates test discovery but TEST_SUITE_INDEX.md update is a doc hygiene step, not a collection sync requirement.
