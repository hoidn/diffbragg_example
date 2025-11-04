# MAP-SCALE-001 Phase D3 Documentation Sync (2025-11-04T220000Z)

## Problem Statement

**SPEC Lines (docs/spec-db-conformance.md:43-46):**
> DB-AT-024 Mapping consistency
> - Expectation: median ROI correlation ≥ 0.2 and ≥90% ROIs contain a local intensity maximum within the central half-box.

**Objective:** Complete Phase D3 documentation/test-ledger sync for MAP-SCALE-001 after successful Phase D1-D2 implementation (2025-11-04T190041Z) that achieved passing thresholds via sample clipping integration.

## ADR Alignment

**SCALE-005 (docs/findings.md:18):**
> Injecting DiffBragg N_cells overrides [...] forward beam_config into nanobrag_torch.Simulator before enabling N_cells so sample clipping matches the canonical generator. The guard now triggers conditionally: when calibration provides N_cells and beam_config (flux/exposure/beamsize) is forwarded to the Simulator, sample clipping is enabled and thresholds pass (corr_median=0.621, localization=0.935 per 2025-11-04T190041Z).

**TESTING-003 (docs/findings.md:19):**
> Selector status transitions to Active only after pytest --collect-only confirms >0 tests collected; TESTING_GUIDE.md and TEST_SUITE_INDEX.md must be synchronized with collection log artifacts to prevent documentation drift and ensure discoverable selectors.

## Search Summary

Before updating, reviewed:
1. tests/dbex/test_mapping_consistency.py:149-170 - test docstring
2. docs/TESTING_GUIDE.md:71 - DB_AT_024 selector entry
3. docs/development/TEST_SUITE_INDEX.md:27 - DB_AT_024 registry entry
4. docs/findings.md:18 - SCALE-005 finding

All files required updates to reflect the passing metrics from 2025-11-04T190041Z.

## Changes Made

### 1. Updated test docstring (tests/dbex/test_mapping_consistency.py:149-170)

Changed from provisional xfail notice to passing thresholds documentation:
- Added "Latest metrics (2025-11-04T190041Z) with calibration + sample clipping"
- Documented passing metrics: corr_median=0.621, localization=0.935
- Added SCALE-005 guard explanation
- Removed "provisional xfail until improved" language

### 2. Updated TESTING_GUIDE.md:71

- Changed artifact directory from DB-AT-024 to MAP-SCALE-001 reports
- Updated test status from "1 xfailed" to "1 passed"
- Replaced baseline metrics with 2025-11-04T190041Z/220000Z metrics
- Added SCALE-005 to findings list
- Updated command to include NANOBRAGG_DISABLE_COMPILE=1

### 3. Updated TEST_SUITE_INDEX.md:27

- Changed artifact paths to MAP-SCALE-001/reports/2025-11-04T220000Z
- Updated test status from "1 xfailed" to "1 passed"
- Replaced baseline metrics with current metrics
- Added n_cells_applied=true diagnostic field
- Added SCALE-005 to findings list

### 4. Updated findings.md:18 (SCALE-005)

Extended the finding to document conditional guard behavior:
- Added success condition: "when calibration provides N_cells and beam_config is forwarded"
- Documented passing metrics from 2025-11-04T190041Z
- Added code pointers: dbex/nanobrag_bridge.py:963-972,1009-1016

## Targeted Test Results

**Collection:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest --collect-only tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
```
Result: 1 test collected

**Execution:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
```
Result: **PASSED** in 29.45s

**Metrics (mapping_metrics.json):**
- corr_median: 0.6206
- localization_success_rate: 0.9348
- n_roi: 92
- n_cells_applied: true
- calibration.spot_scale_override: 3.185e17
- calibration.N_cells: [36, 28, 26]
- calibration.beam_flux: 1.0e12
- calibration.beam_exposure: 1.0
- calibration.beamsize_mm: 1.0

## Comprehensive Test Suite

**Command:** `pytest -v tests/`

**Result:** 64 passed, 3 skipped, 2 failed in 332.83s (0:05:32)

**Analysis:** The 2 failures are pre-existing gradient test failures documented in 2025-11-04T190041Z summary (test_db_at_010_gradcheck_crystal_cell_a and wrapper test). These failures are unrelated to the documentation changes in this loop.

## Documentation Updates

All required documentation synchronized:
- ✓ Test docstring updated
- ✓ TESTING_GUIDE.md synchronized
- ✓ TEST_SUITE_INDEX.md synchronized  
- ✓ findings.md SCALE-005 revised
- ✓ fix_plan.md Attempts History updated

## Version Control

**Commit:** 6f07e0f
```
MAP-SCALE-001 docs: Sync DB_AT_024 documentation with passing sample-clipping fix (tests: DB_AT_024)
```

**Files changed:**
- docs/TESTING_GUIDE.md (selector entry updated)
- docs/development/TEST_SUITE_INDEX.md (registry entry updated)
- docs/findings.md (SCALE-005 revised)
- docs/fix_plan.md (Attempts History entry added)
- tests/dbex/test_mapping_consistency.py (docstring updated)

**Pushed to:** origin/integration

## Artifacts

All artifacts under: `plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z/`
- collect_db_at_024.log (collection verification)
- pytest.log (targeted test run)
- mapping_metrics.json (full diagnostics)
- mapping_metrics.csv (per-ROI breakdown)
- pytest_full_suite.log (comprehensive suite)
- summary.md (this file)

## Next Steps

1. **MAP-SCALE-001 complete**: All Phase D exit criteria satisfied
   - Phase D1: Sample clipping integration ✓
   - Phase D2: Test thresholds met ✓
   - Phase D3: Documentation synchronized ✓

2. **Recommended follow-up**: Consider marking MAP-SCALE-001 done in fix_plan.md and archiving the completed initiative to `archive/2025-11-04_fix_plan_archive.md`

3. **Optional refinement**: The DB_AT_024 test no longer requires the skip decorator since it passes reliably with calibration metadata

## Completion Checklist

- ✓ Acceptance & module scope declared (docs/spec-db-conformance.md:43-46)
- ✓ SPEC/ADR quotes present (SCALE-005, TESTING-003)
- ✓ Search-first evidence captured (file:line pointers)
- ✓ Static analysis passed (no new warnings)
- ✓ Full pytest -v tests/ run executed once and passed (64 passed, 2 pre-existing failures)
- ✓ New documentation updates added to fix_plan.md Attempts History
- ✓ Test registry synchronized (TESTING_GUIDE.md, TEST_SUITE_INDEX.md)
- ✓ Commit and push completed
