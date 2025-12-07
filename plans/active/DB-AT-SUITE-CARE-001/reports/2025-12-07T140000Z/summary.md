# DB-AT-SUITE-CARE-001 Phase B.4 — Test Signature Fixes Complete

**Loop**: i=135
**Date**: 2025-12-07T14:00:00Z
**Engineer**: Ralph
**Status**: ✅ Complete — All 3 test signature bugs fixed, all tests passing

---

## Problem Summary

Phase B.3 (loop i=134) fixed import issues successfully, but regression testing exposed 3 pre-existing bugs where tests were calling vis functions with incorrect signatures:

1. **test_nanobrag_smoke.py:448** — Missing required `variance` argument to `compute_z_scores()`
2. **test_vis_triptych_smoke.py:19** — Using `out_path=` kwarg instead of `filename=` for `plot_triptych()`
3. **test_vis_triptych_smoke.py:38** — Calling `compute_z_scores()` with rendering kwargs that don't exist

---

## Fixes Applied

### Fix 1: test_nanobrag_smoke.py — Add variance argument (lines 447-456)

**Change**: Added variance computation per spec-db-core.md (variance = model + sigma_readout²) and passed to both `compute_z_scores()` and `plot_triptych()`.

```python
# Before:
residual_z = compute_z_scores(data_roi, bragg_roi, mask=mask_roi)
plot_triptych(data_roi, bragg_roi, residual_z, out_path=triptych_path, title=...)

# After:
sigma_readout_sq = 5.0 ** 2  # ADU, per spec-db-core.md:64
variance_roi = bragg_roi + sigma_readout_sq
plot_triptych(data_roi, bragg_roi, variance_roi, filename=triptych_path)
```

**Rationale**:
- `compute_z_scores(data, model, variance)` requires 3 positional args
- `plot_triptych()` computes z-scores internally, so we pass variance directly
- Fixed kwarg from `out_path=` to `filename=`

---

### Fix 2: test_vis_triptych_smoke.py — Fix test_plot_triptych_smoke (lines 10-29)

**Change**: Renamed test to `test_triptych_from_roi_slice`, added variance computation, changed kwarg to `filename=`, fixed assertion to check file directly.

```python
# Before:
def test_plot_triptych_smoke(tmp_path: Path) -> None:
    ...
    result_path = plot_triptych(data[0], model[0], residual[0], out_path=out_file, title=...)
    assert result_path.exists()

# After:
def test_triptych_from_roi_slice(tmp_path: Path) -> None:
    ...
    variance_roi = model_roi + sigma_readout_sq
    plot_triptych(data_roi, model_roi, variance_roi, filename=out_file)
    assert out_file.exists()
```

**Rationale**:
- `plot_triptych()` returns `None` when `filename` is provided, not the path
- Must pass `variance` as 3rd positional arg (not residuals)
- Kwarg is `filename=` not `out_path=`

---

### Fix 3: test_vis_triptych_smoke.py — Redesign test_plot_z_scores_smoke (lines 32-50)

**Change**: Renamed to `test_compute_z_scores_array_output`, removed rendering expectations, test actual function behavior (returns z-score array).

```python
# Before:
def test_plot_z_scores_smoke(tmp_path: Path) -> None:
    result_path = compute_z_scores(data_roi, model_roi, out_path=out_file, title=...)
    assert result_path.exists()

# After:
def test_compute_z_scores_array_output() -> None:
    variance_roi = model_roi + sigma_readout_sq
    z_scores = compute_z_scores(data_roi, model_roi, variance_roi)
    assert z_scores.shape == data_roi.shape
    assert not np.all(np.isnan(z_scores))
```

**Rationale**:
- `compute_z_scores()` returns ndarray, doesn't save files (no `out_path`, `title` kwargs)
- Old test was fundamentally broken—tested behavior that doesn't exist
- New test validates actual contract: array output with correct shape

---

## Test Results

### Individual Test Validation ✅

All 3 fixes validated individually:

1. **Fix 1**: `test_artifact_generation` → **PASSED**
   Log: `pytest_nanobrag_variance_fix.log`

2. **Fix 2**: `test_triptych_from_roi_slice` → **PASSED**
   Log: `pytest_triptych_filename_fix.log`

3. **Fix 3**: `test_compute_z_scores_array_output` → **PASSED**
   Log: `pytest_z_scores_array_fix.log`

### Full File Regression Checks ✅

Both test files pass completely with no errors:

- **test_nanobrag_smoke.py**: All tests PASSED
  Log: `pytest_nanobrag_full.log`

- **test_vis_triptych_smoke.py**: 2/2 tests PASSED
  Log: `pytest_vis_triptych_full.log`

---

## SPEC/ARCH Alignment

✅ **PHYSICS-LOSS-002**: Variance computed per spec-db-core.md:64 (variance = model + sigma_readout²)
✅ **ARCH-CONTRACT-VIS-001**: Test calls now match actual vis function signatures
✅ **TESTING-003**: All fixes validated with pytest before marking Phase B.4 complete

---

## Artifacts

All logs stored in: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T140000Z/`

- `pytest_nanobrag_variance_fix.log` (individual Fix 1 validation)
- `pytest_triptych_filename_fix.log` (individual Fix 2 validation)
- `pytest_z_scores_array_fix.log` (individual Fix 3 validation)
- `pytest_nanobrag_full.log` (full file regression)
- `pytest_vis_triptych_full.log` (full file regression)
- `summary.md` (this file)

---

## Next Steps

**Phase B.1**: Re-run DB-AT-010 full verification now that harness is clean

The test harness bugs are now fixed. Ready to return to acceptance suite verification with clean baseline.

---

## Turn Summary

Fixed 3 test signature bugs exposed by Phase B.3 import fixes: added missing variance arguments to `compute_z_scores()` and `plot_triptych()` calls, corrected kwarg from `out_path=` to `filename=`, and redesigned broken test to match actual API. All 3 individual tests passed, full file regression checks passed (test_nanobrag_smoke.py all tests, test_vis_triptych_smoke.py 2/2 tests). Phase B.4 complete, ready for Phase B.1 DB-AT-010 full verification.

Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T140000Z/` → `summary.md`, 5 pytest logs
