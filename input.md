# Input for Ralph — Loop i=135

**Summary**: DB-AT-SUITE-CARE-001 Phase B.4 — Fix pre-existing test signature bugs exposed by Phase B.3 import fixes

**Mode**: none

**ActionType**: implementation_ready

**DecisionStatus**: patch_ready

**InitiativeType**: harness

**Focus**: [DB-AT-SUITE-CARE-001] — Acceptance Suite Upkeep (DB-AT-002/010/020—024)

**Branch**: integration

**Mapped tests**:
- `env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_nanobrag_smoke.py::test_nanobrag_smoke_tensor_output` (must PASS after variance fix)
- `env KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_vis_triptych_smoke.py::test_triptych_from_roi_slice` (must PASS after kwarg fix)
- `env KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_vis_triptych_smoke.py::test_compute_z_scores_array_output` (test 3: renamed, must PASS after redesign)

**Artifacts**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T140000Z/`

**Findings Applied (Mandatory)**:
- **TESTING-003** — Test harness fixes must validate with pytest before marking Phase B.4 complete
- **PHYSICS-LOSS-002** — Variance computation per spec-db-core.md (variance = model + sigma_readout^2)

**ARCH Contracts (mandatory)**:
1. **ARCH-CONTRACT-VIS-001** (Visualization function signatures)
   - **Owner**: `dbex.vis.residuals::compute_z_scores`, `dbex.vis.triptych::plot_triptych`
   - **Failure**: Test contract bugs (tests call vis functions with incorrect signatures)
   - **Fix**: Update test calls to match actual function signatures

**Do Now**:

Fix 3 pre-existing test signature bugs exposed by Phase B.3 import fixes.

**Context**: Loop i=134 (Ralph) Phase B.3 fixed imports successfully (collection check PASSED), but regression checks revealed pre-existing bugs where tests were calling vis functions with wrong signatures:

1. **test_nanobrag_smoke.py:448** — Missing required `variance` argument to `compute_z_scores()`
2. **test_vis_triptych_smoke.py:19** — Using `out_path=` kwarg instead of `filename=` for `plot_triptych()`
3. **test_vis_triptych_smoke.py:38** — Calling `compute_z_scores()` with rendering kwargs (`out_path`, `title`) that don't exist in the signature

**Implementation**:

**Fix 1**: test_nanobrag_smoke.py — Add missing variance argument

Edit `tests/dbex/test_nanobrag_smoke.py`:
- Find line 448 (or nearby) where `compute_z_scores` is called
- **old_string** (approximate):
  ```python
      residual_z = compute_z_scores(
          data_roi,
          bragg_roi,
          mask=mask_roi,
      )
  ```

- **new_string**:
  ```python
      # Compute variance per spec-db-core.md (variance = model + sigma_readout^2)
      sigma_readout_sq = 5.0 ** 2  # ADU, per spec-db-core.md:64
      variance_roi = bragg_roi + sigma_readout_sq
      residual_z = compute_z_scores(
          data_roi,
          bragg_roi,
          variance_roi,
          mask=mask_roi,
      )
  ```

**Fix 2**: test_vis_triptych_smoke.py — Change `out_path=` to `filename=`

Edit `tests/dbex/test_vis_triptych_smoke.py`:
- Find line 19 where `plot_triptych` is called with `out_path=`
- **old_string** (approximate):
  ```python
      plot_triptych(
          data_roi=data_roi,
          model_roi=bragg_roi,
          mask=mask_roi,
          out_path=out_path,
          title="Test Triptych"
      )
  ```

- **new_string**:
  ```python
      plot_triptych(
          data_roi=data_roi,
          model_roi=bragg_roi,
          mask=mask_roi,
          filename=out_path,
          title="Test Triptych"
      )
  ```

**Fix 3**: test_vis_triptych_smoke.py — Fix compute_z_scores test (redesign for actual API)

The second test (`test_compute_z_scores_smoke` around line 38) is **fundamentally broken** — it calls `compute_z_scores()` expecting it to render/save plots, but `compute_z_scores()` only computes z-scores (returns ndarray, doesn't save files).

**Solution**: Rename test to reflect actual behavior and remove rendering expectations

Edit `tests/dbex/test_vis_triptych_smoke.py`:
- Find the second test function (around line 30-50)
- **old_string** (approximate function signature and call):
  ```python
  def test_compute_z_scores_smoke(tmp_path, data_roi, bragg_roi, mask_roi):
      """Smoke test for compute_z_scores function."""
      out_path = tmp_path / "z_scores.png"

      result_path = compute_z_scores(
          data_roi,
          bragg_roi,
          mask=mask_roi,
          out_path=out_path,
          title="Z-Score Map"
      )

      assert result_path.exists(), "compute_z_scores must write an artifact"
  ```

- **new_string**:
  ```python
  def test_compute_z_scores_array_output(data_roi, bragg_roi, mask_roi):
      """Smoke test for compute_z_scores function (returns z-score array, does not render)."""
      # Compute variance per spec-db-core.md
      sigma_readout_sq = 5.0 ** 2  # ADU
      variance_roi = bragg_roi + sigma_readout_sq

      z_scores = compute_z_scores(
          data_roi,
          bragg_roi,
          variance_roi,
          mask=mask_roi,
      )

      # Validate z-score array properties
      assert z_scores.shape == data_roi.shape, "Z-scores must match input data shape"
      assert not np.all(np.isnan(z_scores)), "Z-scores should contain valid values where mask is True"
  ```

**Validation**:

1. **Run all 3 fixed tests individually** (before committing):
   ```bash
   mkdir -p plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T140000Z/

   # Test 1: variance fix
   env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
       pytest -vv tests/dbex/test_nanobrag_smoke.py::test_nanobrag_smoke_tensor_output \
       > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T140000Z/pytest_nanobrag_variance_fix.log 2>&1

   # Test 2: filename kwarg fix
   env KMP_DUPLICATE_LIB_OK=TRUE \
       pytest -vv tests/dbex/test_vis_triptych_smoke.py::test_triptych_from_roi_slice \
       > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T140000Z/pytest_triptych_filename_fix.log 2>&1

   # Test 3: compute_z_scores array output test
   env KMP_DUPLICATE_LIB_OK=TRUE \
       pytest -vv tests/dbex/test_vis_triptych_smoke.py::test_compute_z_scores_array_output \
       > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T140000Z/pytest_z_scores_array_fix.log 2>&1
   ```

   **Exit criteria**: All 3 tests PASS

2. **Full file regression check** (after individual tests pass):
   ```bash
   env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
       pytest -v tests/dbex/test_nanobrag_smoke.py \
       > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T140000Z/pytest_nanobrag_full.log 2>&1

   env KMP_DUPLICATE_LIB_OK=TRUE \
       pytest -v tests/dbex/test_vis_triptych_smoke.py \
       > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T140000Z/pytest_vis_triptych_full.log 2>&1
   ```

   **Exit criteria**: Both files PASS completely (no errors, no failures)

**Summary Report**:

Create `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T140000Z/summary.md` documenting:
- Phase B.4 complete (pre-existing test signature bugs fixed)
- All 3 fixes applied with rationale (variance per spec, kwarg name correction, test redesign for actual API)
- Test outcomes for each fix (individual + full file regression)
- Next steps (Phase B.1: Re-run DB-AT-010 full verification now that harness is clean)

**Forbidden This Loop**:
- No production code changes to `dbex.vis` or other modules (test fixes only)
- No DB-AT-010 full pytest execution (defer to Phase B.1 after harness validation)
- No additional test refactoring beyond the 3 identified signature bugs

**DMI Section**: Not applicable (harness fixes, not parity work)

**ARCH Conformance Remediation**: Not applicable (no ARCH-CONTRACT violations found)

**SYNC Closure**: Not applicable (no SYNC mid-air)

**Pitfalls**:
1. `compute_z_scores()` requires exactly 3 positional args (data, model, variance) plus optional mask/sigma_floor — missing variance triggers TypeError
2. `plot_triptych()` uses `filename=` not `out_path=` — wrong kwarg name causes "unexpected keyword argument" error
3. Test 3 name mismatch: the old test was called `test_compute_z_scores_smoke` but tested rendering behavior that `compute_z_scores()` doesn't provide — new name `test_compute_z_scores_array_output` reflects actual function behavior
4. `sigma_readout_sq` must be squared before adding to model (variance = model + sigma²), per spec-db-core.md:64
5. If Fix 3 pytest fails with missing fixtures, add back only the fixtures that are actually used (remove tmp_path since no file writing)
6. Import numpy if not already imported in test_vis_triptych_smoke.py (for `np.all` and `np.isnan` in Fix 3 assertions)

**How-To Map**:

All commands are shell-direct pytest invocations with artifacts routed to `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T140000Z/`.

Environment flags:
- `KMP_DUPLICATE_LIB_OK=TRUE`: Required for PyTorch tests (TESTING_GUIDE.md §1.1)
- `NANOBRAGG_DISABLE_COMPILE=1`: Required for test_nanobrag_smoke.py (gradient/torch safety, RUNTIME-001)

Artifact structure:
- Individual test logs: `pytest_<test_area>_<fix_type>.log`
- Full file logs: `pytest_<file>_full.log`
- Summary: `summary.md` (Phase B.4 completion status)

**If Blocked**:
- If Fix 1 fails: Check actual line number for `compute_z_scores` call in test_nanobrag_smoke.py, may differ from line 448
- If Fix 2 fails: Verify `plot_triptych` signature in `dbex/vis/triptych.py` hasn't changed
- If Fix 3 fails with fixture errors: Check test function signature, may need to keep some fixtures for data_roi setup
- If Fix 3 fails with NameError for np: Add `import numpy as np` to test file imports
- If any test still fails after signature fix: Document the actual error in summary.md, mark Phase B.4 blocked, escalate to Galph

**Doc Sync Plan (Conditional)**:
Not applicable (no new tests added, existing tests fixed). TEST_SUITE_INDEX.md unchanged.
