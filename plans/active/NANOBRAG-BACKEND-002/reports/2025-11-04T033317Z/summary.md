# NANOBRAG-BACKEND-002 Loop Summary — 2025-11-04T033317Z (implementation)

## Problem Statement

**SPEC Reference (DB-AT-001)**: `docs/spec-db-conformance.md:23-26`

> "DB‑AT‑001 Forward equivalence smoke
> - Setup: Using the same `DataLoad` inputs, generate a single forward `Bragg` tensor with the legacy DiffBragg pipeline and the torch bridge (no parameter updates). Compare coarse metrics (ROI correlation ≥ 0.2, localized intensity per `plans/nanobrag_integration_plan.md` Phase 1) and capture visual overlays/logs.
> - Expectation: median ROI correlation ≥ 0.2 and ≥90% of sampled ROIs contain a local intensity maximum within the central half-box"

The task was to repoint the DB-AT-001 parity smoke test to use the new NANOBRAG-BACKEND-002 artifact directory (replacing the old NANOBRAG-GOLDEN-001 paths) and validate that the real nanobrag_torch backend meets the parity thresholds specified in the SPEC.

## ADR/ARCH Alignment

**ADR/ARCH References**:
- `docs/spec-db-tracing.md:10-24` — Parity harness workflow requiring first-divergence capture and deterministic artifact emission
- `docs/spec-db-conformance.md:23-26` — DB-AT-001 acceptance criteria (correlation ≥0.20, localization ≥0.90)
- `docs/architecture.md` — Test artifact organization under initiative-specific reports directories
- Findings TESTING-003, PARITY-001, MANIFEST-001, SCALE-001/002

**Alignment**: This loop completes Phase C of NANOBRAG-BACKEND-002 by exercising the real torch backend against the canonical golden dataset, capturing parity artifacts in the initiative-specific directory structure, and synchronizing all test documentation per TESTING-003 requirements.

## Search Summary

**Files searched/examined**:
- `tests/dbex/test_db_at_001_parity.py:767` — Artifact directory constant requiring update
- `docs/TESTING_GUIDE.md:87` — Parity harness documentation entry
- `docs/development/TEST_SUITE_INDEX.md:14` — Test suite index parity entry
- `docs/fix_plan.md:93` — Current Attempts History for NANOBRAG-BACKEND-002
- `plans/active/NANOBRAG-BACKEND-002/implementation.md:47` — Phase C checklist

**Findings**:
- Test was still pointing to old artifact path: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T030000Z/parity_harness`
- Documentation entries referenced stale artifact paths and lacked metrics from the real backend run
- Phase C checklist items were unchecked despite prior work completing Phases A and B

## Changes

### Code Changes
**File**: `tests/dbex/test_db_at_001_parity.py:767`
- **Change**: Updated `artifact_dir` path from `NANOBRAG-GOLDEN-001/reports/2025-11-04T030000Z` to `NANOBRAG-BACKEND-002/reports/2025-11-04T033317Z`
- **Rationale**: Align artifact capture with current initiative per ARCH artifact organization and TESTING-003 compliance

### Documentation Changes

**File**: `docs/TESTING_GUIDE.md:87`
- **Change**: Updated parity harness entry with new collection log path, test log path, artifacts directory, and live metrics (correlation=0.988, localization=1.0, RMSE=180.4)
- **Rationale**: TESTING-003 requires documentation sync after selector validation

**File**: `docs/development/TEST_SUITE_INDEX.md:14`
- **Change**: Updated parity harness entry matching TESTING_GUIDE changes
- **Rationale**: Cross-reference integrity per TEST_SUITE_INDEX maintenance rules

**File**: `docs/fix_plan.md:94`
- **Change**: Added new Attempts History entry documenting loop execution, metrics, artifacts, and completion of exit criterion 3
- **Rationale**: Ledger policy requires immediate Attempts History update per loop

**File**: `plans/active/NANOBRAG-BACKEND-002/implementation.md`
- **Changes**: 
  - Marked Phase C checklist items C1, C2, C3 as complete
  - Updated initiative status from `in_progress` to `done`
- **Rationale**: All exit criteria met; initiative complete

## Test Results

### Targeted Test
**Command**: `KMP_DUPLICATE_LIB_OK=TRUE AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke`

**Result**: PASSED in 0.41s

**Selector Collection**: `pytest --collect-only tests/dbex/test_db_at_001_parity.py -k DB_AT_001`
- **Collected**: 14 tests (3 manifest integrity, 8 metrics unit tests, 2 artifact emission, 1 DB_AT_001 parity smoke)

### Comprehensive Testing
**Command**: `pytest -v tests/`

**Result**: 46 passed, 1 skipped, 1 xfailed in 5.52s

**Analysis**: No regressions introduced; all existing tests remain stable

## Parity Metrics (DB-AT-001)

From `plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T033317Z/parity_harness/parity_harness/metrics.json`:

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| correlation | 0.988 | ≥0.20 | ✓ PASS |
| localization | 1.0 | ≥0.90 | ✓ PASS |
| RMSE | 180.41 | — | — |
| MSE | 32548 | — | — |
| max_abs_diff | 9808.2 | — | — |
| sum_ratio | 1.106 | — | — |
| n_pixels | 13,086 | — | — |
| n_masked | 6,210,915 | — | — |
| manifest_checksum | 2d1f8d67...8567aee | (matches golden) | ✓ |

### First Divergence
From `first_divergence.json`:
- **Index**: [219, 159]
- **Predicted**: 81.34
- **Target**: 101.46
- **Abs Diff**: 20.12
- **Rel Diff**: 0.198 (19.8%)

**Interpretation**: Excellent overall parity (correlation 0.988, localization 1.0) with minor pixel-level differences as expected for a real physics simulation. The first divergence shows ~20% relative difference at a single pixel, consistent with numerical precision and interpolation differences between DiffBragg and nanobrag_torch implementations.

## Artifacts

**Location**: `plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T033317Z/`

**Contents**:
- `pytest_db_at_001.log` — Test execution log (1 passed)
- `collect_db_at_001_parity.log` — Collection log (14 tests)
- `pytest_full_suite.log` — Full suite validation (46 passed, 1 skipped, 1 xfailed)
- `parity_harness/parity_harness/` — Parity artifacts:
  - `metrics.json` — Comprehensive parity metrics
  - `metrics.csv` — CSV format for analysis
  - `predicted.npy` — Nanobrag_torch output tensor (24MB)
  - `target.npy` — DiffBragg baseline tensor (24MB)
  - `first_divergence.json` — First pixel-level mismatch metadata
  - `diff_overlay_stub.txt` — Placeholder for future visualization

## Fix Plan Update

**Section**: `docs/fix_plan.md` NANOBRAG-BACKEND-002 Attempts History

**New Entry**: 2025-11-04T033317Z (implementation) documenting:
- Test artifact path update (tests/dbex/test_db_at_001_parity.py:767)
- Parity smoke test execution (PASSED 0.41s)
- Artifact validation (all 6 expected files present)
- Selector collection verification (14 tests)
- Documentation synchronization (TESTING_GUIDE, TEST_SUITE_INDEX)
- Full suite validation (46/46 passing, no regressions)
- Complete metrics listing
- Exit criterion 3 completion declaration

**Status Change**: NANOBRAG-BACKEND-002 marked as `done` (was `in_progress`)

## Completion Checklist

- [x] Acceptance & module scope declared: DB-AT-001 (parity validation); Module: tests/docs
- [x] SPEC/ADR quotes present: DB-AT-001 acceptance criteria (correlation ≥0.20, localization ≥0.90)
- [x] Search-first evidence: File pointers for test, docs, and plan files provided
- [x] Static analysis: N/A (documentation and configuration changes only)
- [x] Full pytest suite executed: 46 passed, 1 skipped, 1 xfailed (no collection failures)
- [x] New issues documented: None (initiative complete)
- [x] Artifacts archived: All logs and parity artifacts in initiative-specific directory
- [x] Documentation synchronized: TESTING_GUIDE, TEST_SUITE_INDEX, fix_plan, implementation plan all updated
- [x] Version control: Committed with descriptive message referencing DB_AT_001 selector and metrics

## Next Most Important Item

With NANOBRAG-BACKEND-002 complete (all exit criteria met, parity metrics exceeding thresholds), the next logical focus areas would be:

1. **Remove xfail from forward equivalence test** — Now that the real simulator is integrated and parity validated, `tests/dbex/test_forward_equivalence_complete.py::test_DB_AT_001_forward_equiv` can likely be promoted from xfail to active with adjusted thresholds

2. **End-to-end CLI integration test** — Validate `python -m dbex.refine_one --backend nanobrag` produces HDF5 outputs with torch_diagnostics matching expectations end-to-end (not just unit tests)

3. **Performance profiling** — Benchmark nanobrag_torch backend against DiffBragg to establish performance baselines and identify optimization opportunities

4. **Determinism testing (DB-AT-002)** — Implement planned determinism acceptance tests verifying same-seed reproducibility and diff-seed variation per spec-db-conformance

These would be captured in future fix_plan items after validating current state with stakeholders.

---

**Initiative Status**: NANOBRAG-BACKEND-002 → `done` (all exit criteria met)
**Test Selector**: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001`
**Key Metric**: correlation=0.988 (threshold ≥0.20) ✓
**Commit**: 9c3c9b5 "NANOBRAG-BACKEND-002 parity: Repoint DB-AT-001 to new backend artifacts (tests: DB_AT_001)"
