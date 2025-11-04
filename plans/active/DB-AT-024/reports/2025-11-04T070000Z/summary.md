# DB-AT-024 Implementation Summary — 2025-11-04T070000Z

## Scope
Implementation of helper extraction (`simulate_forward_once`) and DB_AT_024 acceptance test per input.md Do Now.

## Deliverables

### 1. Helper Function: `simulate_forward_once`
**File:** `dbex/nanobrag_bridge.py:602-745`

Extracted zero-iteration forward simulation helper from `run_nanobrag_backend` workflow:
- Returns `(bragg, diagnostics)` tuple with per-panel Bragg tensors and diagnostic dict
- Applies SCALE-001 (unscaled HKL grid) and SCALE-002 (post-simulation sqrt(spot_scale_override))
- Applies GEOMETRY-002 (analytic Euler inversion via `create_detector_config`)
- Device-neutral design (defaults to CPU, respects passed device)
- Converts mask_array to torch.Tensor when needed (per compute_zero_iteration_metrics.py:88-89)
- Does not write HDF5 or persist artifacts (caller's responsibility)

**Diagnostics returned:**
- `masked_mse`: Masked MSE between target and bragg
- `loss_mask_coverage`: Fraction of pixels in loss mask
- `n_rois`: Number of ROI bboxes
- `target_shape`: Shape of target tensor (as string)
- `global_scale_hint`: Scale hint from inputs (ADU mode only)
- `spot_scale_override`: Scale override used
- `sqrt_spot_scale`: Sqrt(spot_scale_override) applied
- `bragg_stats`: Dict with min/max/mean of bragg output
- `hkl_stats`: HKL grid metadata from build_structure_factor_grid

### 2. Acceptance Test: DB_AT_024
**File:** `tests/dbex/test_mapping_consistency.py`

- Class: `TestDB_AT_024_Mapping`
- Test: `test_db_at_024_mapping_smoke`
- Marks: `@pytest.mark.db_at_024`, `@pytest.mark.mapping`

**Validates:**
- Median ROI correlation >= 0.2 (per docs/spec-db-conformance.md:43-46)
- Localization success rate >= 90% (brightest pixel within central half-box)

**Artifact emission:**
- `mapping_metrics.json`: Aggregate metrics (n_roi, corr_median/min/max, localization_mean/success_rate, global_scale_hint, diagnostics)
- `mapping_metrics.csv`: Per-ROI metrics (roi_idx, panel_id, bbox, correlation, rmse, mse, max_abs_diff, sum_ratio, localization, n_pixels, n_masked)

**Skip guards:**
- `DBAT024_ARTIFACT_DIR` env var must be set
- Canonical assets (refGeom.expt, refGeom.refl, scaled.mtz, 747_mask.pkl) must exist

**Provisional xfail:**
- Current baseline metrics do not meet thresholds
- xfail reason cites measured metrics per input.md:29
- Test infrastructure complete; threshold improvement requires future parity work

## Test Execution

### Targeted Test Run
```bash
KMP_DUPLICATE_LIB_OK=TRUE DBAT024_ARTIFACT_DIR=plans/active/DB-AT-024/reports/2025-11-04T070000Z \
pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
```
**Result:** 1 xfailed (expected), 16.76s runtime

### Comprehensive Test Suite
```bash
pytest -v tests/
```
**Result:** 61 passed, 2 skipped, 11 warnings in 14.15s
- No regressions introduced
- DB_AT_024 skipped when DBAT024_ARTIFACT_DIR not set (expected)

### Collection
```bash
DBAT024_ARTIFACT_DIR=plans/active/DB-AT-024/reports/2025-11-04T070000Z \
pytest --collect-only tests -k DB_AT_024
```
**Result:** 1 test collected

## Metrics (Baseline from input.md / 2025-11-04T063053Z)
- **n_roi:** 92
- **corr_median:** 0.0488 (target: >= 0.2)
- **localization_success_rate:** 0.0 (target: >= 0.90)
- **global_scale_hint:** 62.66 ADU
- **masked_mse:** 981700.05
- **loss_mask_coverage:** 0.21%
- **bragg_stats:** min=0.0, max=0.0856, mean=0.0026

## Documentation Updates
- `docs/TESTING_GUIDE.md:70`: Promoted DB_AT_024 from "Planned" to "Active" with full selector, environment flags, baseline metrics, artifact paths, and finding refs
- `docs/development/TEST_SUITE_INDEX.md:26`: Added DB_AT_024 entry with selector, spec refs, test details, artifacts, and finding refs

## Artifacts
All artifacts stored under `plans/active/DB-AT-024/reports/2025-11-04T070000Z/`:
- `pytest_db_at_024.log`: Targeted test run output (1 xfailed)
- `collect_db_at_024.log`: Collection output (1 test collected)
- `mapping_metrics.json`: Aggregate metrics
- `mapping_metrics.csv`: Per-ROI metrics (92 rows)
- `summary.md`: This file

## Next Actions (per input.md:61)
Exit criteria satisfied for this loop:
- Helper extraction complete (simulate_forward_once in dbex/nanobrag_bridge.py:602-745)
- DB_AT_024 test authored and passing (xfail as expected per CONFORMANCE-001)
- Artifacts emitted under $DBAT024_ARTIFACT_DIR
- Documentation synchronized (TESTING_GUIDE.md, TEST_SUITE_INDEX.md)
- Comprehensive gate passed (61 passed, 2 skipped)
- DB_AT_024 selector Active

If scaling strategy is needed to lift correlation above 0.2, draft dedicated initiative per input.md:61 "Next Up".

## Code References
- `dbex/nanobrag_bridge.py:602-745` — `simulate_forward_once` helper
- `tests/dbex/test_mapping_consistency.py:1-254` — DB_AT_024 acceptance test
- `tests/fixtures/parity_loader.py:362-486` — `compute_parity_metrics` utility
- `docs/spec-db-conformance.md:43-46` — DB_AT_024 acceptance contract
- `docs/forward_equivalence.md:48-49` — Localization definition
