# MAP-SCALE-005 Closure Summary

## Initiative
- **ID**: MAP-SCALE-005
- **Title**: CLI refined telemetry enforcement
- **Type**: spec_change
- **Status**: ✅ **DONE** (2025-12-07T024500Z)

## Exit Criteria Assessment

### 1. Harden run_nanobrag_backend fail-fast guard
**Status**: ✅ **SATISFIED**

**Evidence**:
- Phase A (i=129) discovered guard already implemented at `dbex/refine_one.py:382-389`
- Enforcement behavior: RuntimeError raised when `--refined-mtz` provided but load fails
- No silent fallback path exists (assertion confirmed via code audit + spec alignment)

### 2. Regression test coverage
**Status**: ✅ **SATISFIED**

**Evidence** (Phase B, i=130):
- `test_refined_mtz_missing_file_fails_fast` (tests/dbex/test_refine_one_cli.py:1159)
  - Validates RuntimeError on missing refined MTZ
  - Error message includes flag name, path, policy enforcement text
- `test_refined_mtz_telemetry_provenance` (tests/dbex/test_refine_one_cli.py:1274)
  - Dual-path validation: raw MTZ → hkl_source="raw", refined MTZ → hkl_source="refined"
  - Telemetry correctness validated at write_torch_outputs boundary
- Test execution: **4 PASSED** (2025-12-07T000000Z)
  - Pytest logs: `plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/pytest_targeted.log`
  - Collection validation: 4 items collected

### 3. Documentation updates
**Status**: ✅ **SATISFIED**

**Evidence** (Phase B, i=130):
- **ARCH-CONTRACT formalization**: `docs/architecture/calibration_scaling.md:26-38`
  - ARCH-CONTRACT-CALIBRATION-001 documents fail-fast contract
  - Owner: `dbex/refine_one.py::run_nanobrag_backend` (lines 382-389)
  - Normative source: `spec-db-workflow.md:47`
  - Failure modes: FileNotFoundError, ValueError, ImportError
  - Error contract: RuntimeError (not SystemExit)
  - Regression coverage: both test selectors cross-referenced
- **Code cross-reference**: `dbex/refine_one.py:376-381`
  - Comment block links guard to ARCH-CONTRACT + test selectors
- **Findings ledger**: `docs/findings.md` SCALE-007 (line 45)
  - CLI Enforcement note added with Phase B completion evidence
  - Expanded code citations: refine_one.py:376-399, test selectors, calibration_scaling.md
  - Artifact pointer: `plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/`
  - CLI tag added for discoverability

## Phase Summary

### Phase A (i=129, 2025-12-06T235959Z): Reality Check
**Outcome**: CRITICAL DISCOVERY — enforcement already implemented

**Deliverables**:
1. `fallback_reproduction.md`: CLI already fails fast (no silent fallback)
2. `spec_citations.md`: spec-db-workflow.md:47 normative requirement confirmed
3. `guard_design.md`: 6 failure surfaces covered, production-quality error messages
4. `summary.md`: Revised Phase B scope (validation + documentation only)

**Decision**: Proceed with Option A (add tests + formalize ARCH-CONTRACT)

### Phase B (i=130, 2025-12-07T000000Z): Validation + Documentation
**Outcome**: Regression coverage + architectural documentation delivered

**Deliverables**:
1. Two regression tests (test_refined_mtz_missing_file_fails_fast + test_refined_mtz_telemetry_provenance)
2. ARCH-CONTRACT-CALIBRATION-001 formalization in calibration_scaling.md
3. Code cross-reference comments at guard site (refine_one.py:376-381)
4. SCALE-007 findings update with CLI enforcement note

**Test Results**: 4 PASSED (zero production code changes)

## Artifacts Index

### Phase A Reports
- `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/`
  - fallback_reproduction.md
  - spec_citations.md
  - guard_design.md
  - summary.md

### Phase B Reports
- `plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/`
  - pytest_targeted.log (4 PASSED)
  - pytest_collect_only.log (4 collected)
  - summary.md

### Production Files Touched
- `tests/dbex/test_refine_one_cli.py` (lines 1159-1413, +2 tests)
- `docs/architecture/calibration_scaling.md` (lines 26-38, +ARCH-CONTRACT-CALIBRATION-001)
- `dbex/refine_one.py` (lines 376-381, +cross-reference comments)
- `docs/findings.md` (SCALE-007 update, line 45)

## Dependencies Resolved

**Blocked by**: MAP-SCALE-003 (resolved i=127)

**Unblocks**: MAP-SCALE-SYNC-001 closure (5/5 member plans complete)

## Governance References

**Governed by**:
- SCALE-007 (findings.md) — CLI telemetry enforcement guardrail
- SCALE-003 (findings.md) — Calibration metadata threading contract
- SCALE-004 (findings.md) — HKL source telemetry provenance

**Normative SPEC**:
- `docs/spec-db-workflow.md:47` — "fail if refined requested but missing"

**ARCH Contract**:
- ARCH-CONTRACT-CALIBRATION-001 (docs/architecture/calibration_scaling.md:26-38)

## Next Steps

1. ✅ Mark MAP-SCALE-005 status: `pending` → `done` in docs/fix_plan.md
2. ✅ Update MAP-SCALE-SYNC-001: 5/5 member plans complete, ready for closure
3. ✅ Portfolio steering: Select next Tier 1 focus (DB-AT-SUITE-CARE-001 candidate)

---

**Closure Date**: 2025-12-07T024500Z
**Closed By**: Galph (supervisor, loop i=131)
**Final Status**: ✅ DONE — All 3/3 exit criteria satisfied
