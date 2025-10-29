# PARITY-HARNESS-002 Phase B+C Loop Summary

**Initiative:** PARITY-HARNESS-002 — DB-AT Parity Harness
**Loop:** 2025-10-29T015235Z
**Focus:** Phase B (metrics helper + artifact writers) + Phase C (doc sync)
**Mode:** Implementation (TDD)
**Status:** ✅ Complete

## Objectives

Advance DB_AT_001 parity harness from manifest-only coverage (Phase A) to metric-producing parity smoke with documented artifacts (Phase B+C).

## Deliverables

### Phase B1: Parity Metrics Helper
- **Implementation:** `tests/fixtures/parity_loader.py:268-457`
  - `ParityMetrics` dataclass (lines 268-307)
  - `compute_parity_metrics()` function (lines 310-457)
- **Features:**
  - Pearson correlation (using scipy.stats for stability)
  - RMSE, MSE, max|Δ|
  - Sum ratio (pred/target)
  - Peak localization (central half-box check per docs/forward_equivalence.md:48-49)
  - Loss mask support (exclude masked pixels)
  - NaN handling for edge cases (empty arrays, constant inputs)
- **Unit Tests:** 8 tests in `TestParityMetrics` class
  - `test_perfect_match`: Perfect correlation scenario
  - `test_correlation_computation`: Linear relationships
  - `test_error_metrics`: RMSE/MSE/max|Δ| validation
  - `test_sum_ratio`: Edge cases (zero denominator, zero numerator)
  - `test_localization_metric`: Peak localization checks
  - `test_mask_application`: Masked pixel exclusion
  - `test_edge_cases`: Empty arrays, single pixel, shape mismatch
  - `test_to_dict_serialization`: JSON serialization

### Phase B2: Artifact Writers
- **Implementation:** `tests/fixtures/parity_loader.py:460-547`
  - `write_parity_artifacts()` function
- **Features:**
  - Creates `parity_harness/` subdirectory
  - Writes `metrics.json` with manifest checksum + metadata
  - Writes `metrics.csv` with metric rows
  - Saves `predicted.npy` and `target.npy` for analysis
  - Generates `diff_overlay_stub.txt` (future: PNG heatmap)
- **Unit Tests:** 2 tests in `TestArtifactEmission` class
  - `test_artifact_emission`: Full artifact suite
  - `test_artifact_emission_minimal`: Minimal mode (no tensors)

### Phase B3: Parity Smoke Test
- **Implementation:** `tests/dbex/test_db_at_001_parity.py:689-794`
  - `TestDB_AT_001_Parity::test_db_at_001_parity_smoke`
- **Features:**
  - Loads golden data from simple_cubic dataset
  - Seeds RNG (np.random.seed(42)) for reproducibility
  - Introduces synthetic noise to simulate imperfect parity
  - Computes parity metrics
  - Emits artifacts with manifest checksum
  - Conditionally xfails when thresholds not met (correlation ≥0.2, localization ≥0.9)
- **Status:** xfails as expected with synthetic data

### Phase C3: Documentation Sync
- **Updated Files:**
  - `docs/TESTING_GUIDE.md` §2.1: Added parity harness row (line 84)
  - `docs/development/TEST_SUITE_INDEX.md`: Added parity harness entry (line 14)
  - `docs/fix_plan.md`: Added Attempts History entry with metrics/artifacts (line 27)
  - `plans/active/PARITY-HARNESS-002/implementation.md`: Marked Phase B+C complete

## Metrics

### Test Execution
- **Parity metrics unit tests:** 8/8 passed (0.25s, CPU)
- **Artifact emission tests:** 2/2 passed (0.25s, CPU)
- **DB_AT_001 parity smoke:** 1/1 xfailed (expected, 0.51s, CPU)
- **Total tests collected:** 14/14 (confirmed via `--collect-only`)

### Parity Smoke Metrics
From `test_db_at_001_parity_smoke` with synthetic noise:
```
correlation:     0.1395
RMSE:           979.82
MSE:         960042.31
max|Δ|:       52762.12
sum_ratio:       1.569
localization:      0.5
n_pixels:       13,086
n_masked:    6,210,915
```

Note: Low correlation (0.14 < 0.2 threshold) and partial localization (0.5 < 0.9 threshold) expected with synthetic noise added to golden data. Test xfails to capture diagnostics without failing the suite.

## Artifacts

All artifacts stored under: `plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/`

### Test Logs
- `pytest_parity_metrics.log`: 8 metrics unit tests
- `pytest_artifact_emission.log`: 2 artifact writer tests
- `pytest_db_at_001.log`: DB_AT_001 parity smoke (xfail)
- `collect_db_at_001.log`: pytest --collect-only evidence (14 tests)
- `pytest_final_all.log`: Full suite sanity check (13 passed, 1 xfailed)

### Parity Harness Artifacts
Under `parity_harness/` subdirectory:
- `metrics.json`: Full metrics with manifest checksum + metadata (1.8 KB)
- `metrics.csv`: Metrics as CSV rows (190 bytes)
- `predicted.npy`: Predicted tensor [2527, 2463] float32 (24.9 MB)
- `target.npy`: Target tensor [2527, 2463] float32 (24.9 MB)
- `diff_overlay_stub.txt`: Diff statistics stub (182 bytes)

Total artifact directory size: ~50 MB

## Spec Compliance

### Findings Applied
- **CONFORMANCE-001:** Thresholds (correlation ≥0.2, localization ≥0.9) enforced with xfail policy
- **GEOMETRY-001:** Pixel pitch guards and [panel, slow, fast] ordering preserved
- **MASKING-001:** Loss mask coverage interpretation (0.21% coverage expected for sparse Bragg peaks)
- **TESTING-003:** Collection logs archived, docs synchronized with Active status

### Spec Citations
- `docs/spec-db-conformance.md:23-26`: DB-AT-001 thresholds and xfail policy
- `docs/forward_equivalence.md:30-53`: ROI metrics and localization definition
- `docs/spec-db-tracing.md:10-24`: Artifact layout and traceability requirements
- `docs/spec-db-core.md:24`: [panel, slow, fast] tensor ordering
- `docs/spec-db-workflow.md:24-29`: Sparse loss mask coverage interpretation

## Next Actions

### Phase C Completion (Future Loop)
- Replace synthetic noise with real DiffBragg forward pass (legacy path)
- Add torch simulator forward pass when available
- Update test to compute parity between legacy and torch tensors
- Enforce thresholds without xfail when simulators converge

### Phase D (Optional Enhancements)
- Add first divergence capture (per-pixel trace)
- Document durable lessons in `docs/findings.md`
- Outline simulator upgrade readiness checklist

### Exit Criteria Status
✅ Exit criteria 1-4 satisfied for Phase B:
1. ✅ Parity metrics helper implemented with unit coverage
2. ✅ Artifact writers persist JSON/CSV/NPY with manifest checksum
3. ✅ DB_AT_001 parity smoke test with conditional xfail
4. ✅ Documentation synchronized (TESTING_GUIDE, TEST_SUITE_INDEX, fix_plan, implementation plan)

## Environment

- Python: 3.9.23
- pytest: 8.4.2
- PyTorch: 2.8.0 (CPU)
- Platform: Linux 6.14.0-33-generic
- Required flags: `KMP_DUPLICATE_LIB_OK=TRUE`

## Reproducibility

Run all tests:
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
pytest -v tests/dbex/test_db_at_001_parity.py
```

Run specific selectors:
```bash
# Metrics unit tests
pytest -v tests/dbex/test_db_at_001_parity.py::TestParityMetrics

# Artifact emission tests
pytest -v tests/dbex/test_db_at_001_parity.py::TestArtifactEmission

# DB_AT_001 parity smoke (xfail expected)
pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke

# Collection evidence
pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001
```

## References

- Initiative plan: `plans/active/PARITY-HARNESS-002/implementation.md`
- Fix plan ledger: `docs/fix_plan.md:16-27`
- Testing guide: `docs/TESTING_GUIDE.md:84`
- Test suite index: `docs/development/TEST_SUITE_INDEX.md:14`
- Spec citations: See "Spec Compliance" section above
