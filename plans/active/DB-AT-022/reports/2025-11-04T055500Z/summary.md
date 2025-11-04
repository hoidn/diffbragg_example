# DB-AT-022 Summary — Background Sentinel Guard Implementation

**Date:** 2025-11-04T055500Z
**Owner:** Ralph
**Status:** Complete
**Exit Criteria Met:** ✅ All 4 criteria satisfied

## Problem Statement

Implement and validate the background sentinel guard per **docs/simtbx_api.md:14**:

> `background_image`: same shape as `imgs` (`[panel, slow, fast]`), filled with −1 sentinel for invalid pixels; valid ROI pixels carry the plane/robust background estimate.

**SPEC Quote (docs/spec-db-conformance.md:35-38):**
> DB‑AT‑022 ROI background semantics
> - Setup: run simtbx background; confirm −1 sentinel outside ROIs; optional recompute with trusted mask.
> - Expectation: sentinel logic correct; ROI coverage matches reflection metadata.

## Implementation

### Code Changes

**dbex/nanobrag_bridge.py:132-171** — Added sentinel integrity guard to `prepare_refinement_inputs`:

1. **ROI union construction** from bbox/pids (lines 137-139)
2. **Sentinel detection** using <= -0.5 threshold (line 143)
3. **Guard Check 1:** No sentinel inside ROI union (lines 146-155)
4. **Guard Check 2:** Pixels outside ROI must be sentinel, allowing 0.1 tolerance (lines 158-171)

Key insight: simtbx background estimation can produce **slightly negative values** (> -0.5) inside ROIs from plane fitting. Sentinel is specifically **<= -0.5**.

**tests/dbex/test_background_semantics.py** — Authored 3 DB_AT_022 tests:

1. `test_DB_AT_022_sentinel_complement` — Validates sentinel mask equals complement of ROI union, zero overlap, coverage ~100%, sentinel_mean ≈ -1.0
2. `test_DB_AT_022_guard_enforcement` — Tests canonical data passes guard; tampered data (sentinel inside ROI, non-sentinel outside ROI) raises ValueError with actionable messages
3. `test_DB_AT_022_roi_coverage_metrics` — Captures per-ROI background statistics and global coverage metrics

## Test Results

**Targeted selector:**
```bash
DBAT022_ARTIFACT_DIR=plans/active/DB-AT-022/reports/2025-11-04T055500Z \
  KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_background_semantics.py -k DB_AT_022
```

**Result:** 3 passed in 4.84s

**Collection:**
```bash
pytest --collect-only tests -k DB_AT_022
```

**Result:** 3/58 tests collected (55 deselected)

**Full suite:** `pytest -v tests/`
**Result:** 57 passed, 1 skipped, 9 warnings in 9.11s (no regressions)

## Metrics (Canonical refGeom)

### Sentinel Coverage (sentinel_metrics.json)

```json
{
  "roi_count": 92,
  "sentinel_fraction": 0.9979,      // 99.8% sentinel coverage
  "roi_fraction": 0.0021,            // 0.2% ROI coverage
  "overlap_count": 0,                // Zero overlap ✅
  "sentinel_mean": -1.0,             // Exact -1 sentinel ✅
  "sentinel_std": 0.0,
  "coverage_sum": 1.0,               // Perfect complement ✅
  "total_pixels": 6224001,
  "sentinel_pixels": 6210753,
  "roi_pixels": 13248
}
```

### ROI Background (roi_coverage.json)

```json
{
  "roi_count": 92,
  "background_valid_pixels": 13158,           // 99.3% of ROI pixels
  "background_sentinel_pixels": 6210753,
  "background_valid_fraction": 0.0021,
  "background_sentinel_fraction": 0.9979,
  "mean_roi_bg_valid_fraction": 0.9932        // 99.3% valid bg in ROIs
}
```

**Key Insight:** 90 ROI pixels (0.7%) have **slightly negative** background values (between -0.5 and 0) from plane fitting. This is expected behavior, not sentinel leak.

## Documentation Updates

### docs/TESTING_GUIDE.md:68
- Status: Planned → **Active**
- Added environment flags: `KMP_DUPLICATE_LIB_OK=TRUE`, `DBAT022_ARTIFACT_DIR`
- Documented 3 tests, canonical metrics, artifact paths
- Applied findings: CONFORMANCE-001, TESTING-003, MASKING-001, CONFIG-001

### docs/development/TEST_SUITE_INDEX.md:24
- Status: planned → **active**
- Added test file reference, sentinel guard description, artifact paths
- Synchronized with TESTING_GUIDE.md

## Exit Criteria Validation

✅ **Criterion 1:** `prepare_refinement_inputs` enforces sentinel integrity guard
  - Implemented at dbex/nanobrag_bridge.py:132-171
  - Raises ValueError with actionable messages citing docs/simtbx_api.md:14
  - No regression to existing loss mask behavior (full suite passes)

✅ **Criterion 2:** Authored `tests/dbex/test_background_semantics.py` (DB_AT_022)
  - 3 tests: sentinel complement, guard enforcement, ROI coverage
  - Assertions: overlap=0, sentinel_mean=-1.0, coverage_sum=1.0
  - Captures mismatch diagnostics via pytest.raises

✅ **Criterion 3:** Persisted artifacts under `plans/active/DB-AT-022/reports/2025-11-04T055500Z/`
  - pytest_db_at_022.log (3 passed)
  - collect_db_at_022.log (3 collected)
  - sentinel_metrics.json (sentinel compliance)
  - roi_coverage.json (per-ROI statistics)

✅ **Criterion 4:** Promoted DB_AT_022 to Active in docs/TESTING_GUIDE.md + TEST_SUITE_INDEX.md
  - Referenced applied findings: CONFORMANCE-001, CONFIG-001, MASKING-001, TESTING-003
  - Archived artifact paths and canonical metrics

## Findings Applied

- **CONFORMANCE-001:** DB_AT selector naming + env flags
- **CONFIG-001:** ROI/mask geometry honored in sentinel guard
- **MASKING-001:** Sparse ROI coverage expected (0.2%)
- **TESTING-003:** Selector promoted to Active only after collect-only confirms >0 tests

## Artifacts

```
plans/active/DB-AT-022/reports/2025-11-04T055500Z/
├── pytest_db_at_022.log          # 3 passed, 4 warnings
├── collect_db_at_022.log         # 3 collected
├── sentinel_metrics.json         # Sentinel coverage + overlap validation
├── roi_coverage.json             # Per-ROI background statistics
└── summary.md                    # This file
```

## Next Actions (Optional)

From input.md:13:
1. **DB-AT-023** — Calibration guard (adu-per-photon policy) once sentinel coverage lands
2. **Extend determinism metrics** — Mask-aware ROI sampling if time remains

## Commands Reference

**Targeted test:**
```bash
export ARTIFACT_TS=2025-11-04T055500Z
export DBAT022_ARTIFACT_DIR=plans/active/DB-AT-022/reports/${ARTIFACT_TS}
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_background_semantics.py -k DB_AT_022 | \
  tee plans/active/DB-AT-022/reports/${ARTIFACT_TS}/pytest_db_at_022.log
```

**Collection:**
```bash
pytest --collect-only tests -k DB_AT_022 | \
  tee plans/active/DB-AT-022/reports/${ARTIFACT_TS}/collect_db_at_022.log
```

**Full suite regression:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/
```
