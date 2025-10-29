# PARITY-HARNESS-002 Phase D Loop Summary — 2025-10-29T020937Z

**Objective**: Instrument DB_AT_001 parity harness with first-divergence diagnostics and refresh docs/test evidence.

**Mode**: Parity

**Branch**: integration

## Tasks Completed

### D1 — First-Divergence Diagnostics Instrumentation

1. **Extended `tests/fixtures/parity_loader.py`** with first-divergence capture utilities:
   - Added `FirstDivergence` dataclass (lines 550-585) to store pixel-level mismatch metadata
   - Implemented `find_first_divergence()` function (lines 588-677) that:
     - Scans tensors in deterministic row-major order
     - Captures first pixel where `abs(predicted - target) > abs_threshold` OR `abs(predicted - target) / abs(target) > rel_threshold`
     - Respects loss mask (skips masked pixels)
     - Returns metadata: pixel_index, predicted_value, target_value, abs_diff, rel_diff, threshold, n_pixels_scanned

2. **Fixed JSON serialization issue**: Updated `FirstDivergence.to_dict()` to handle numpy int64→JSON conversion (`[int(x) for x in self.pixel_index]`)

3. **Wired first-divergence into DB_AT_001 parity smoke test** (`test_db_at_001_parity.py`):
   - Import `find_first_divergence` and `FirstDivergence`
   - Call `find_first_divergence()` after computing parity metrics
   - Emit `first_divergence.json` artifact to `parity_harness/` subdirectory
   - Log first-divergence metadata in test output

### C3 — Documentation Synchronization

1. **Ran pytest collect-only** and captured evidence:
   - Command: `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001`
   - Result: 14 tests collected
   - Log: `plans/active/PARITY-HARNESS-002/reports/2025-10-29T020937Z/collect_db_at_001.log`

2. **Updated `docs/TESTING_GUIDE.md` §2.1** (Parity harness row):
   - Added "first-divergence capture (pixel-level mismatch metadata)" to description
   - Updated collection log reference to `2025-10-29T020937Z/collect_db_at_001.log`
   - Updated artifacts path to `2025-10-29T020937Z/parity_harness/`
   - Added `first_divergence.json` to artifact list
   - Added DIAGNOSTICS-001 to finding refs

3. **Updated `docs/development/TEST_SUITE_INDEX.md`** (Parity harness row):
   - Same updates as TESTING_GUIDE.md for consistency

### D2 — Findings and Fix Plan Updates

1. **Added PARITY-001 finding to `docs/findings.md`**:
   - ID: PARITY-001
   - Tags: parity, diagnostics, first-divergence, tracing
   - Summary: Documents deterministic row-major scanning, numpy int64→JSON serialization, loss mask respect, artifact emission workflow
   - Source: tests/fixtures/parity_loader.py:550-677, docs/spec-db-tracing.md:15-19
   - Status: Active

2. **Appended `docs/fix_plan.md` Attempts History**:
   - Timestamp: 2025-10-29T020937Z
   - Metrics: 13/13 tests passed, 1/1 xfailed (expected), 14/14 collected, runtime 0.53s (CPU)
   - First divergence: pixel [0,582], abs_diff=4.29, rel_diff=8.81, n_pixels_scanned=1
   - Parity smoke metrics: correlation=0.1395, RMSE=979.82, MSE=960042.31, max|Δ|=52762.12, sum_ratio=1.569, localization=0.5, n_pixels=13086, n_masked=6210915
   - Artifacts: 8 files (pytest_db_at_001.log, collect_db_at_001.log, 6 parity_harness files)

3. **Updated `plans/active/PARITY-HARNESS-002/implementation.md`**:
   - Marked Phase D checklist items (D1, D2, D3) as complete

## Test Results

**Full suite**: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py`
- 13 passed
- 1 xfailed (expected with synthetic data)
- Runtime: 0.53s (CPU)
- Python 3.9.23, pytest 8.4.2

**Test breakdown**:
- 3 manifest integrity tests: PASSED
- 8 metrics unit tests: PASSED
- 2 artifact emission tests: PASSED
- 1 DB_AT_001 parity smoke: XFAIL (correlation < 0.2, localization < 0.9, as expected with synthetic noise)

## Artifacts Generated

All artifacts stored under `plans/active/PARITY-HARNESS-002/reports/2025-10-29T020937Z/`:

1. **Test logs**:
   - `pytest_db_at_001.log` (full test output)
   - `collect_db_at_001.log` (collect-only evidence)

2. **Parity harness artifacts** (under `parity_harness/` subdirectory):
   - `metrics.json` (full metrics + metadata)
   - `metrics.csv` (metrics in CSV format)
   - `predicted.npy` (predicted tensor, 24.9 MB)
   - `target.npy` (target tensor, 24.9 MB)
   - `diff_overlay_stub.txt` (diff statistics stub)
   - **`first_divergence.json`** (NEW: first pixel-level mismatch metadata)

## First Divergence Metadata

```json
{
  "pixel_index": [0, 582],
  "predicted_value": 3.8002262115478516,
  "target_value": -0.48643404245376587,
  "abs_diff": 4.286660254001617,
  "rel_diff": 8.812418292885107,
  "threshold": 1e-06,
  "n_pixels_scanned": 1
}
```

**Interpretation**: First divergence detected at pixel [0, 582] on the first scan (n_pixels_scanned=1), with absolute difference of 4.29 and relative difference of 8.81. This is expected behavior with synthetic noise added to the predicted tensor.

## Compliance Checks

- ✅ All "Active" selectors collect >0 tests (TESTING-003)
- ✅ KMP_DUPLICATE_LIB_OK=TRUE environment requirement documented
- ✅ Collection logs archived under artifacts directory
- ✅ TESTING_GUIDE.md and TEST_SUITE_INDEX.md synchronized
- ✅ Findings ledger updated with new PARITY-001 entry
- ✅ Fix plan Attempts History includes Metrics/Artifacts lines
- ✅ First Divergence metadata captured per spec-db-tracing.md:15-19

## Next Actions

1. **Phase D complete**: All implementation.md Phase D checklist items marked done
2. **Phase C partially complete**: Real simulator integration for threshold validation remains pending (nanobrag_torch availability)
3. **Initiative status**: Consider closing PARITY-HARNESS-002 initiative pending simulator availability; all instrumentation/harness scaffolding is complete

## References

- Input: `input.md` (tasks D1, D2, C3)
- Spec: `docs/spec-db-tracing.md:15-19` (first-divergence workflow)
- Spec: `docs/spec-db-conformance.md:23-26` (DB_AT_001 thresholds)
- Spec: `docs/forward_equivalence.md:30-53` (parity metrics)
- Finding: PARITY-001 (first-divergence scanning)
- Finding: TESTING-003 (selector compliance)
- Finding: DIAGNOSTICS-001 (artifact metadata standards)
