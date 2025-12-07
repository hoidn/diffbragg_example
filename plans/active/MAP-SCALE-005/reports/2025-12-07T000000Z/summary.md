# MAP-SCALE-005 Phase B Summary (Loop i=130)

## Overview
**Initiative**: MAP-SCALE-005 — CLI refined telemetry enforcement
**Phase**: B (Regression Test Addition + ARCH-CONTRACT Documentation Update)
**Date**: 2025-12-07T000000Z
**Actor**: Ralph
**Mode**: implementation_ready
**ActionType**: implementation_ready
**DecisionStatus**: patch_ready
**InitiativeType**: spec_change

## Problem & SPEC/ARCH Alignment

Phase A (i=129) discovered that the CLI guard at `dbex/refine_one.py:382-389` already implements fail-fast enforcement when `--refined-mtz` is provided but cannot be loaded. However, two gaps remained:
1. **Regression test coverage missing**: No automated tests validated the guard behavior
2. **Documentation drift**: ARCH-CONTRACT-CALIBRATION-001 referenced in findings.md but not formalized in architecture docs

**SPEC Alignment**: `spec-db-workflow.md:47` normatively requires "fail if refined requested but missing"
**ARCH Alignment**: Guard implementation correct; documentation lagged behind reality

## Changes Made

### 1. Test Module (`tests/dbex/test_refine_one_cli.py`)

#### test_refined_mtz_missing_file_fails_fast (line 1159)
- **Purpose**: Validate RuntimeError raised when `--refined-mtz` points to missing file
- **Coverage**: FileNotFoundError path through CLI guard
- **Assertions**: Error message includes flag name, path, and policy enforcement text
- **Renamed from**: `test_nanobrag_backend_refined_mtz_missing_errors` (improved naming to match input.md spec)

#### test_refined_mtz_telemetry_provenance (line 1274, NEW)
- **Purpose**: Validate `hkl_source` telemetry accurately reflects raw vs refined MTZ usage
- **Test Case 1**: No `--refined-mtz` → `hkl_source="raw"`
- **Test Case 2**: Valid `--refined-mtz` → `hkl_source="refined"`
- **Assertions**: Telemetry passed to `write_torch_outputs` contains correct source/path/count
- **Implementation**: Mocked scoring to avoid scipy dependency; dual-path validation in single test

### 2. Architecture Documentation (`docs/architecture/calibration_scaling.md`)

Added **ARCH-CONTRACT-CALIBRATION-001** (lines 26-38):
- **Owner**: `dbex/refine_one.py::run_nanobrag_backend` (lines 382-389)
- **Contract**: Fail-fast when `--refined-mtz` provided but cannot load (no silent fallback)
- **Normative Source**: `spec-db-workflow.md:47`
- **Failure Modes**: FileNotFoundError, ValueError (parse/columns), ImportError (iotbx.mtz)
- **Error Contract**: RuntimeError (not SystemExit, preserves stack traces)
- **Telemetry Enforcement**: `hkl_source` field distinguishes raw/refined
- **Regression Coverage**: Cross-references both new test selectors
- **Cross-References**: SCALE-007 (findings.md), MAP-SCALE-005 (fix_plan.md)

### 3. Code Documentation (`dbex/refine_one.py`)

Added cross-reference comment block (lines 376-381):
```python
# ARCH-CONTRACT-CALIBRATION-001: Refined MTZ enforcement guard
# Per spec-db-workflow.md:47, when --refined-mtz is provided, the CLI MUST fail fast
# if the refined MTZ cannot be loaded. No silent fallback to raw MTZ is permitted.
# See docs/architecture/calibration_scaling.md ARCH-CONTRACT-CALIBRATION-001.
# Regression tests: tests/dbex/test_refine_one_cli.py::test_refined_mtz_missing_file_fails_fast
#                   tests/dbex/test_refine_one_cli.py::test_refined_mtz_telemetry_provenance
```

### 4. Findings Ledger (`docs/findings.md`)

Updated SCALE-007 (line 45):
- Added **CLI Enforcement** note documenting Phase B completion
- Expanded code citations to include `dbex/refine_one.py:376-399` and test selectors
- Added `docs/architecture/calibration_scaling.md:26-38` reference
- Added `plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/` artifact pointer
- Tagged `cli` in categories for discoverability

## Tests and Static Checks

### Pytest Execution
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
pytest -vv \
  tests/dbex/test_refine_one_cli.py::test_refined_mtz_missing_file_fails_fast \
  tests/dbex/test_refine_one_cli.py::test_refined_mtz_telemetry_provenance \
  tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
```

**Outcome**: **4 passed, 4 warnings** (warnings are deprecation notices from dials/swig, not test failures)

### Test Collection Verification
```bash
pytest --collect-only tests/dbex/test_refine_one_cli.py::test_refined_mtz_missing_file_fails_fast \
                      tests/dbex/test_refine_one_cli.py::test_refined_mtz_telemetry_provenance \
                      tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
```

**Collected**: 4 tests (2 new + 2 parametrized from existing `test_torch_diagnostics_metadata`)

### Static Checks
- **Linting**: No new issues (comments follow existing style)
- **Type hints**: N/A (test module and comments)
- **Formatting**: Followed existing test module conventions

### Regression Risk
**Zero production code changes** — only tests and documentation updated. Guard implementation unchanged from Phase A discovery.

## Docs & Ledgers Updates

- **Architecture Docs**: `docs/architecture/calibration_scaling.md` — formalized ARCH-CONTRACT-CALIBRATION-001
- **Findings Ledger**: `docs/findings.md` SCALE-007 — expanded CLI enforcement section with Phase B artifacts
- **Code Comments**: `dbex/refine_one.py:376-381` — added ARCH-CONTRACT cross-reference
- **Test Docs**: N/A (skipped TESTING_GUIDE.md / TEST_SUITE_INDEX.md per input.md note: "Not Required - Existing test module being extended")

## Next Step

**MAP-SCALE-005 Phase B complete**. Validation coverage now in place; guard behavior cannot be silently removed without breaking regression tests. Next action:
- Commit Phase B changes with cross-referenced test evidence
- Mark MAP-SCALE-005 done in fix_plan.md
- Proceed to next Tier 1 initiative per roadmap

## Artifacts

All artifacts written to `plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/`:
- **pytest_targeted.log**: Full test execution output (4 PASSED)
- **pytest_collect_only.log**: Test discovery evidence (4 collected)
- **summary.md**: This file

---

### Turn Summary

Delivered MAP-SCALE-005 Phase B: added regression tests `test_refined_mtz_missing_file_fails_fast` and `test_refined_mtz_telemetry_provenance` validating CLI guard at refine_one.py:382-389. Formalized ARCH-CONTRACT-CALIBRATION-001 in calibration_scaling.md documenting fail-fast enforcement per spec-db-workflow.md:47. Updated findings.md SCALE-007 with CLI enforcement note and test coverage. All 4 tests PASSED (2 new + 2 parametrized existing). Zero production code changes; pure test+doc delivery per patch_ready input. Next: commit Phase B and close MAP-SCALE-005.

**Artifacts**: `plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/` — `pytest_targeted.log`, `pytest_collect_only.log`, `summary.md`
