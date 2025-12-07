# MAP-SCALE-005 Phase B Planning Notes (Loop i=130, Galph)

## Executive Summary

**Decision**: Proceed with Option A (Regression Test Addition + ARCH-CONTRACT Update)

**Rationale**: Ralph's Phase A discovery (enforcement guard already exists at refine_one.py:382-389) changes the initiative scope from implementation to validation. However, SCALE-007 finding explicitly requires regression test coverage to prevent silent removal of the guard. Option A delivers this requirement in 1-2 loops with minimal risk.

## Phase A Outcomes Review

Ralph's Phase A (loop i=129) delivered comprehensive analysis under `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/`:

1. **fallback_reproduction.md**: CLI fails fast when --refined-mtz points to missing file (RuntimeError raised, no silent fallback)
2. **spec_citations.md**: spec-db-workflow.md:47 normative requirement confirmed (fail fast on refined missing)
3. **guard_design.md**: Guard at refine_one.py:382-389 implements 6 failure surfaces correctly
4. **summary.md**: Comprehensive Option A/B/C analysis with recommendation for Option A

### Key Finding

**The enforcement mechanism is already implemented and spec-compliant.** The gap is:
- **Missing**: Regression test coverage (SCALE-007 requirement)
- **Missing**: Updated ARCH-CONTRACT documentation (reflects reality)

## Phase B Scope (Option A)

### Primary Deliverable: Regression Tests

Add two new tests to `tests/dbex/test_refine_one_cli.py`:

1. **test_refined_mtz_missing_file_fails_fast** (~25 lines):
   - Mock `load_refined_mtz` to raise FileNotFoundError
   - Assert pytest.raises(RuntimeError, match="refined")
   - Verify no HDF5 output written to tmp_path
   - Documents guard behavior explicitly in test code

2. **test_refined_mtz_telemetry_provenance** (~25 lines):
   - Run CLI without --refined-mtz flag → assert hkl_source="raw"
   - Run CLI with valid --refined-mtz → assert hkl_source="refined"
   - Uses existing fixtures from test_torch_diagnostics_metadata
   - Validates telemetry integrity

### Secondary Deliverable: Documentation Updates

1. **ARCH-CONTRACT-CALIBRATION-001**:
   - Locate current text (likely in code comments or docs/architecture_contracts.md)
   - Update description from "falls back silently" to "fails fast per spec-db-workflow.md:47"
   - Add code reference: dbex/refine_one.py:382-389

2. **docs/findings.md** (SCALE-007 note):
   - Add: "CLI enforcement validated by regression tests added in MAP-SCALE-005 Phase B"
   - Cross-reference: tests/dbex/test_refine_one_cli.py::test_refined_mtz_missing_file_fails_fast

3. **docs/TESTING_GUIDE.md** + **docs/development/TEST_SUITE_INDEX.md**:
   - Document new selector: test_refined_mtz_missing_file_fails_fast
   - Document new selector: test_refined_mtz_telemetry_provenance
   - Status: Active (after pytest --collect-only confirms)

## Why Not Option B (Close as Already Satisfied)?

**Findings Paydown Rule**: SCALE-007 explicitly states "DB_AT_024 must fail when refined assets present but telemetry reports raw or missing, so regressions that drop refined usage are caught immediately."

The CLI guard exists but **lacks automated enforcement**. If a future refactor removes the try-except block at refine_one.py:382-389, there's no test to catch it. Option A closes this gap in 1-2 loops.

## Why Not Option C (Reimplement Guard)?

Violates multiple non-negotiables:
- **No Stacking**: Guard already correct
- **Pragmatic over Dogmatic**: No value in replacing working code
- **Incremental Progress**: Rework introduces regression risk for zero benefit

## Implementation Strategy

### Reuse Existing Test Patterns

Ralph noted that `test_torch_diagnostics_metadata` already mocks the CLI pipeline. The new tests will:
- Reuse the same mocking fixtures (DataLoad, run_nanobrag_backend)
- Follow the same assertion pattern (HDF5 attrs, stdout/stderr)
- Integrate cleanly into existing test module (no new file)

### Validation Plan

1. **Targeted Pytest** (3 selectors):
   ```bash
   pytest -vv tests/dbex/test_refine_one_cli.py::test_refined_mtz_missing_file_fails_fast \
                tests/dbex/test_refine_one_cli.py::test_refined_mtz_telemetry_provenance \
                tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
   ```
   Expected: 3/3 PASS

2. **Collect-Only** (registry validation):
   ```bash
   pytest --collect-only tests/dbex/test_refine_one_cli.py
   ```
   Expected: Both new tests appear in collection output

3. **Regression Check**:
   Run `test_torch_diagnostics_metadata` to ensure no breakage from test additions

## Risk Assessment

### Low Risk Deliverable

- **No production code changes**: Guard already correct at refine_one.py:382-389
- **Test-only additions**: Cannot break existing functionality
- **Reuses existing fixtures**: Minimal new surface area
- **Environment Freeze compliant**: pytest framework already present

### Potential Blockers

1. **ARCH-CONTRACT-CALIBRATION-001 doesn't exist**:
   - Mitigation: Create it inline as code comment at refine_one.py:382 with spec citation
   - Fallback: Document in findings.md instead

2. **Test mocking proves complex**:
   - Mitigation: Use tmp_path fixture to create actual missing file instead of mocking
   - Ralph's Phase A tested this path manually; known to work

3. **HDF5 telemetry assertions fail**:
   - Mitigation: Verify torch_diagnostics group structure matches test_torch_diagnostics_metadata pattern
   - Ralph confirmed structure in Phase A reproduction

## MAP-SCALE-SYNC-001 Roll-up Impact

### Current Roll-up Status

- MAP-SCALE-001: ✅ Done (November reports)
- MAP-SCALE-002: ✅ Done (November reports)
- MAP-SCALE-003: ✅ Done (Phase B complete loop i=128)
- MAP-SCALE-004: ✅ Done (November reports)
- MAP-SCALE-005: 🔄 Phase A complete (loop i=129), Phase B pending (this loop i=130)

### Phase B Completion Closes Roll-up

Once Phase B delivers:
- 5/5 member plans complete
- MAP-SCALE-SYNC-001 ready for closure summary
- Next loop: either close MAP-SCALE-SYNC-001 or select next Tier 1 focus

## Lifecycle Compliance

### Loop Budget

- **Current**: Loop 2/2 for MAP-SCALE-005 (planning → implementation)
- **Dwell**: 0 (first implementation loop, second overall)
- **Budget Status**: ✅ Well within limits (implementation floor satisfied)

### Non-Negotiables Adherence

- **Findings Paydown**: ✅ SCALE-007 requirement addressed
- **Type Discipline**: ✅ spec_change (documenting normative behavior)
- **Evidence→Action**: ✅ Tests validate guard cannot be silently removed
- **No Stacking**: ✅ No production edits, guard already correct
- **Environment Freeze**: ✅ Uses existing pytest framework

## Expected Outcomes

### Phase B Success Criteria

1. Both new tests PASS (test_refined_mtz_missing_file_fails_fast, test_refined_mtz_telemetry_provenance)
2. Regression test PASS (test_torch_diagnostics_metadata)
3. ARCH-CONTRACT updated (quote before/after in summary)
4. findings.md + TESTING_GUIDE.md + TEST_SUITE_INDEX.md updated
5. Artifacts under `plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/`

### Next Loop Decision Point

**If Phase B Succeeds**:
- Option 1: Mark MAP-SCALE-005 done, write MAP-SCALE-SYNC-001 closure summary
- Option 2: Mark MAP-SCALE-005 done, select next Tier 1 focus (DB-AT-SUITE-CARE-001, TORCH-GEOMETRY-SYNC-001, etc.)

**If Phase B Blocked**:
- Identify blocker type (test complexity, missing ARCH-CONTRACT, etc.)
- Apply mitigation from Risk Assessment
- If still blocked: switch focus, document reason

## Artifacts Plan

### Loop i=130 Deliverables

Under `plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/`:
- `pytest_targeted.log` — 3 test run outputs
- `pytest_collect_only.log` — Registry validation evidence
- `summary.md` — Phase B completion notes
- `arch_contract_before_after.md` — Documentation update evidence

### Fix Plan Update

Add to `docs/fix_plan.md` MAP-SCALE-SYNC-001 Attempts History:
```
* 2025-12-07T000000Z — [Galph i=130] MAP-SCALE-005 Phase B scoped: Option A (regression tests + ARCH-CONTRACT update). Ralph's Phase A discovered guard already exists at refine_one.py:382-389; Phase B adds automated enforcement per SCALE-007. Mapped tests: test_refined_mtz_missing_file_fails_fast + test_refined_mtz_telemetry_provenance (new), test_torch_diagnostics_metadata (regression). Next: Ralph implements tests + doc updates.
```

## References

- **Phase A Artifacts**: `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/`
- **Existing CLI Guard**: `dbex/refine_one.py:382-389`
- **Spec Citation**: `docs/spec-db-workflow.md:47`
- **Finding**: SCALE-007 (docs/findings.md)
- **Test Module**: `tests/dbex/test_refine_one_cli.py`
- **Existing Test Pattern**: `test_torch_diagnostics_metadata`

## Turn Summary

Loop i=130 (Galph): Transitioned MAP-SCALE-005 from Phase A (planning/reality check) → Phase B (implementation/validation). Ralph's Phase A discovered CLI enforcement guard already exists at refine_one.py:382-389 (no silent fallback), but regression test coverage missing per SCALE-007 requirement. Selected Option A: add 2 regression tests (~50 lines total) + update ARCH-CONTRACT docs. DecisionStatus: exploring → patch_ready. Dwell: 0 (second loop for focus, first implementation). Next: Ralph implements test coverage, captures pytest logs, updates docs, closes MAP-SCALE-005 Phase B.
