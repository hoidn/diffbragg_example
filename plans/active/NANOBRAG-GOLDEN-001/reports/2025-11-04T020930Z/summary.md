# NANOBRAG-GOLDEN-001 Loop Summary — 2025-11-04T020930Z

## Objective
Align DB-AT-001 parity harness artifacts/docs with the canonical 2025-11-04 capture and rerun the smoke selector.

## Actions Completed

### 1. Code Changes
- **tests/dbex/test_db_at_001_parity.py:760** — Updated `artifact_dir` path from `2025-10-29T190533Z` to `2025-11-04T020930Z` to point parity harness to canonical capture directory.

### 2. Documentation Updates
- **docs/TESTING_GUIDE.md:87** — Updated parity harness entry with:
  - Canonical 2025-11-04 capture reference
  - New collection log path: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/collect_db_at_001_parity.log`
  - New artifact directory: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/parity_harness/`
  - Replaced "xfails with synthetic data" with "canonical DiffBragg vs nanobrag_torch comparison"
  - Added finding refs: MANIFEST-001, SCALE-001/002

- **docs/development/TEST_SUITE_INDEX.md:14** — Updated parity harness row with same changes for consistency.

### 3. Test Execution
- **Targeted selector:** `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke`
  - **Result:** PASSED (0.41s)
  - **Collection:** 14 tests total (per `collect_db_at_001_parity.log`)

- **Full suite:** `pytest -v tests/`
  - **Result:** 41 passed, 1 skipped, 1 xfailed (no regressions, 5.45s)
  - **Collection:** All tests collected successfully

### 4. Artifacts Generated
Under `plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/parity_harness/parity_harness/`:
- `metrics.json` — Parity metrics (correlation, RMSE, max|Δ|, sum_ratio, localization)
- `metrics.csv` — CSV format metrics
- `predicted.npy` — nanobrag_torch Bragg tensor (24.9 MB)
- `target.npy` — DiffBragg Bragg tensor (24.9 MB)
- `first_divergence.json` — First pixel-level mismatch metadata
- `diff_overlay_stub.txt` — Placeholder for visual diagnostics
- `pytest_db_at_001.log` — Test execution log
- `collect_db_at_001_parity.log` — Collection log (14 tests)

## Metrics Summary

From `metrics.json`:
```json
{
  "correlation": 0.988,
  "rmse": 180.41,
  "mse": 32548.02,
  "max_abs_diff": 9808.16,
  "sum_ratio": 1.106,
  "localization": 1.0,
  "n_pixels": 13086,
  "n_masked": 6210915,
  "manifest_checksum": "2d1f8d...8567aee"
}
```

**Strong parity achieved** — correlation=0.988 (≫0.2 threshold), localization=1.0 (100% ≫90% threshold), canonical DiffBragg vs nanobrag_torch comparison with manifest checksum validation.

## Acceptance Criteria

Per `docs/spec-db-conformance.md:23-26`:
- ✓ Median ROI correlation ≥ 0.2 (achieved: 0.988)
- ✓ ≥90% ROIs with localized peaks (achieved: 100%)
- ✓ Artifacts captured with manifest checksum and metadata
- ✓ Pytest selector active and collecting >0 tests (14 tests)

## SPEC/ADR Alignment

Implemented per:
- `docs/spec-db-conformance.md:23-26` — DB-AT-001 acceptance thresholds
- `docs/forward_equivalence.md:46-52` — Parity metrics and artifact layout
- `docs/spec-db-tracing.md:15-24` — First-divergence debugging workflow

## Findings Applied

- **CONFIG-001** — Maintained bridge mapping invariants
- **MANIFEST-001** — Preserved manifest checksum/metadata in parity artifacts
- **SCALE-001/002** — Respected structure-factor and global-scale handling (no extra normalization)
- **TESTING-003** — Updated TESTING_GUIDE and TEST_SUITE_INDEX in lockstep after collection verification

## Next Actions

1. ✓ Registry synchronization complete (collection log captured, docs updated)
2. Mark NANOBRAG-GOLDEN-001 focus item as progressing in `docs/fix_plan.md` Attempts History
3. Consider D2 knowledge-base update with canonical parity metrics once loop is committed

## Status

**COMPLETE** — All acceptance criteria met (correlation=0.988 ≫0.2, localization=1.0 ≫0.9), full test suite passes, documentation synchronized with canonical 2025-11-04 capture.
