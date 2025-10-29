# PARITY-HARNESS-002 Closing Summary

**Initiative:** PARITY-HARNESS-002 — Implement DB-AT parity harness tests
**Status:** done
**Closure Date:** 2025-10-29T022212Z
**Branch:** integration
**Final Test Run:** 13 passed, 1 xfailed (expected), 14 total collected

---

## Exit Criteria Validation

All four exit criteria from `docs/fix_plan.md:19-23` have been satisfied:

### 1. Golden Dataset Provenance Documentation ✓

**Delivered:**
- Manifest schema documented in `tests/fixtures/golden_data/simple_cubic/manifest.json`
- SHA256 checksum validation implemented in `tests/fixtures/parity_loader.py:110-169`
- FALLBACK handling documented in manifest metadata (`docs/spec-db-conformance.md:23-26`, `docs/spec-db-core.md:20-58`)
- Three manifest integrity tests cover checksum validation, golden data sanity, and pixel pitch guards

**Evidence:**
- Manifest SHA256: `df88c7d20757f0900c2829d01ceb00fade96b68203bfbd00e4fcb1b5238ebf6d`
- Test coverage: `tests/dbex/test_db_at_001_parity.py:TestManifestIntegrity` (3 tests, all passed)

### 2. Reusable Parity Harness Utilities ✓

**Delivered:**
- `compute_parity_metrics()` (`tests/fixtures/parity_loader.py:310-457`): correlation, RMSE, MSE, max|Δ|, sum_ratio, localization
- `find_first_divergence()` (`tests/fixtures/parity_loader.py:588-677`): pixel-level mismatch metadata with deterministic row-major scan
- `write_parity_artifacts()` (`tests/fixtures/parity_loader.py:460-547`): JSON/CSV/NPY persistence under `parity_harness/` subdirectory
- `FirstDivergence` dataclass with numpy int64→JSON serialization guards

**Evidence:**
- 8 unit tests for metrics computation (`TestParityMetrics`)
- 2 unit tests for artifact emission (`TestArtifactEmission`)
- All utilities satisfy `docs/spec-db-tracing.md:18-72` trace requirements

### 3. DB_AT_001 Pytest Selector Implementation ✓

**Delivered:**
- Selector: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001`
- Test module: `tests/dbex/test_db_at_001_parity.py`
- Parity smoke test: `TestDB_AT_001_Parity::test_db_at_001_parity_smoke`
- Threshold enforcement: correlation ≥0.2, localization ≥0.9 (`docs/spec-db-conformance.md:23-26`, `docs/forward_equivalence.md:28-74`)
- xfail policy: test xfails with diagnostics when thresholds unmet (prevents hard failure with stub simulators)

**Evidence:**
- 1 parity smoke test xfailed as expected (synthetic data mismatch)
- Metrics captured: correlation=0.1395, RMSE=979.82, MSE=960042.31, max|Δ|=52762.12, sum_ratio=1.569, localization=0.5
- First divergence logged: pixel [0,582], abs_diff=4.29, rel_diff=8.81

### 4. Testing Documentation Synchronization ✓

**Delivered:**
- `docs/TESTING_GUIDE.md` §2.1 updated with DB_AT_001 parity harness selector row (line 84)
- `docs/development/TEST_SUITE_INDEX.md` updated with parity harness entry (line 14)
- Environment requirements documented: `KMP_DUPLICATE_LIB_OK=TRUE`
- Artifact paths synchronized to `plans/active/PARITY-HARNESS-002/reports/2025-10-29T022212Z/`
- Collection log referenced: `collect_db_at_001.log` (14 tests collected)
- Finding cross-references added: CONFORMANCE-001, GEOMETRY-001, MASKING-001, DIAGNOSTICS-001, TESTING-003, PARITY-001

**Evidence:**
- `pytest --collect-only` confirms 14 tests collected (compliance with TESTING-003)
- All Active selectors have >0 tests collected (no ledger violations)

---

## Artifacts Summary

All artifacts stored under `plans/active/PARITY-HARNESS-002/reports/2025-10-29T022212Z/`:

**Test Logs:**
- `pytest_db_at_001.log` (13 passed, 1 xfailed, 0.52s runtime)
- `collect_db_at_001.log` (14 tests collected, 0.23s runtime)

**Parity Harness Artifacts (`parity_harness/`):**
- `metrics.json` (correlation, RMSE, MSE, max|Δ|, sum_ratio, localization, metadata)
- `metrics.csv` (tabular metrics for spreadsheet analysis)
- `predicted.npy` (synthetic Gaussian Bragg tensor, 2527×2463, float32, 24.9MB)
- `target.npy` (background-subtracted refGeom data, 2527×2463, float32, 24.9MB)
- `diff_overlay_stub.txt` (placeholder for future heatmap visualization)
- `first_divergence.json` (pixel [0,582], abs_diff=4.29, rel_diff=8.81)

**Closing Documentation:**
- `closing/summary.md` (this document)

---

## Outstanding TODOs

The following simulator integration tasks remain pending and should be prioritized in future initiatives:

### TODO-001: Replace FALLBACK golden dataset with canonical nanoBragg2 parity baseline

**Priority:** High
**Blocker for:** Real parity validation (Phase C from `plans/active/PARITY-HARNESS-002/implementation.md`)
**Description:**
- Current golden dataset uses synthetic Gaussian Bragg tensor (`tests/fixtures/golden_data/simple_cubic/`)
- Real parity requires nanoBragg2 mirror data with known ground truth
- Manifest metadata documents FALLBACK status (see `metrics.json:metadata.notes`)

**Action Items:**
1. Acquire canonical nanoBragg2 golden tensors (or coordinate with nanoBragg2 maintainers to generate them)
2. Update `tests/fixtures/golden_data/simple_cubic/manifest.json` with new provenance, checksums, and remove FALLBACK notes
3. Regenerate `bragg.npy`, `target.npy`, `loss_mask.npy` from nanoBragg2 outputs
4. Rerun DB_AT_001 selector and validate correlation ≥0.2, localization ≥0.9 thresholds met
5. Update manifest SHA256 checksum and rerun manifest integrity tests

**Spec References:**
- `docs/spec-db-conformance.md:23-26` (threshold requirements)
- `docs/spec-db-core.md:20-58` (golden dataset schema)

### TODO-002: Integrate real nanobrag_torch simulator into parity smoke test

**Priority:** High
**Blocker for:** Forward equivalence validation beyond stub outputs
**Description:**
- Current parity smoke test uses synthetic Gaussian pattern as predicted Bragg tensor
- Real parity requires nanobrag_torch forward pass outputs
- Stub mismatch is expected (correlation=0.1395, localization=0.5)

**Action Items:**
1. Replace `stub_bragg_tensor` generation (lines 745-759 in `tests/dbex/test_db_at_001_parity.py`) with actual nanobrag_torch simulator call
2. Pass golden dataset configs (detector, beam, crystal) to nanobrag_torch via bridge helpers from `tests/dbex/test_nanobrag_bridge.py`
3. Ensure nanobrag_torch outputs match `[panel, slow, fast]` ordering (`docs/spec-db-core.md:24`)
4. Rerun parity smoke test and validate thresholds pass (test should no longer xfail)
5. Capture new parity artifacts with real simulator metrics

**Spec References:**
- `docs/architecture.md` (nanobrag_torch integration architecture)
- `docs/pytorch_runtime_checklist.md` (vectorization, dtype neutrality)
- `plans/nanobrag_integration_plan.md` (Phase 1 forward equivalence goals)

### TODO-003: Author diff heatmap overlay visualization

**Priority:** Medium
**Blocker for:** Enhanced diagnostics per `docs/spec-db-tracing.md:48-72`
**Description:**
- Current artifact output includes `diff_overlay_stub.txt` placeholder
- Heatmap visualization would help localize divergence patterns (e.g., edge effects, ROI boundaries)

**Action Items:**
1. Extend `write_parity_artifacts()` to accept optional `--write-heatmap` flag
2. Generate PNG/SVG heatmap using matplotlib or PIL (predicted - target, colormap centered at zero)
3. Include ROI boundaries overlay (dotted lines at panel edges)
4. Save heatmap as `parity_harness/diff_heatmap.png` alongside existing artifacts
5. Update artifact policy in `docs/TESTING_GUIDE.md` §2.2 to reference heatmap outputs

**Spec References:**
- `docs/spec-db-tracing.md:48-72` (overlay visualization requirements)

---

## Applied Findings

This initiative successfully applied the following findings from `docs/findings.md`:

### CONFORMANCE-001: DB_AT_001 selector must xfail with diagnostics when thresholds unmet

**Application:**
- Parity smoke test implements `@pytest.mark.xfail(strict=False, reason=...)` decorator
- Thresholds checked: correlation ≥0.2, localization ≥0.9
- Diagnostics emitted: metrics.json, first_divergence.json, NPY tensors
- Test xfails gracefully with synthetic data (expected behavior until TODO-001/002 resolved)

**Source:** `tests/dbex/test_db_at_001_parity.py:737-744`

### DIAGNOSTICS-001: First-divergence capture must use deterministic row-major scan

**Application:**
- `find_first_divergence()` implements C-order (row-major) flat iteration
- Ensures reproducible pixel index across runs
- Metadata includes `n_pixels_scanned=1` (first mismatch found immediately)
- JSON serialization guards handle numpy int64 types

**Source:** `tests/fixtures/parity_loader.py:588-677`, `docs/spec-db-tracing.md:15-19`

### TESTING-003: Active selectors must collect >0 tests before marking initiative done

**Application:**
- Ran `pytest --collect-only` before closure (14 tests collected)
- Updated `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` with collection log paths
- Verified DB_AT_001 selector Active status with non-zero test count
- Ledger Attempts History references `collect_db_at_001.log` artifact

**Source:** `docs/fix_plan.md:9`, `docs/TESTING_GUIDE.md:56-90`

### PARITY-001: Deterministic first-divergence scan with numpy serialization guards (NEW)

**Application:**
- Added in Phase D (2025-10-29T020937Z)
- Implements row-major flat iteration with `threshold=1e-6`
- JSON serialization converts numpy int64→Python int via `int()` casting
- Metadata captures `pixel_index`, `predicted_value`, `target_value`, `abs_diff`, `rel_diff`, `n_pixels_scanned`

**Source:** `tests/fixtures/parity_loader.py:550-585`, `docs/findings.md:PARITY-001`

---

## Metrics Summary

**Final Test Run (2025-10-29T022212Z):**
- **Tests:** 13 passed, 1 xfailed (expected), 14 total collected
- **Runtime:** 0.52s (test run), 0.23s (collection)
- **Environment:** Python 3.9.23, pytest 8.4.2, CPU
- **Selector:** `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001`

**Parity Smoke Metrics (Synthetic Data Baseline):**
- correlation: 0.1395 (threshold ≥0.2 unmet → xfail expected)
- RMSE: 979.82
- MSE: 960042.31
- max|Δ|: 52762.12
- sum_ratio: 1.569
- localization: 0.5 (threshold ≥0.9 unmet → xfail expected)
- n_pixels: 13086 (unmasked)
- n_masked: 6210915 (masked background)

**First Divergence:**
- pixel_index: [0, 582]
- predicted_value: 3.80
- target_value: -0.49
- abs_diff: 4.29
- rel_diff: 8.81
- n_pixels_scanned: 1

---

## Documentation Updates

The following documentation files were updated during this initiative:

1. **`docs/fix_plan.md`**
   - Changed Status: `in_progress` → `done`
   - Added final Attempts History entry (2025-10-29T022212Z)

2. **`docs/TESTING_GUIDE.md`**
   - Updated §2.1 parity harness selector row (line 84)
   - Synchronized artifact paths to `2025-10-29T022212Z/`
   - Added PARITY-001 finding reference

3. **`docs/development/TEST_SUITE_INDEX.md`**
   - Updated parity harness entry (line 14)
   - Synchronized collection log reference to `2025-10-29T022212Z/collect_db_at_001.log`
   - Added PARITY-001 finding reference

4. **`docs/findings.md`**
   - Added PARITY-001 finding (Phase D, 2025-10-29T020937Z)

All doc updates maintain compliance with `docs/spec-db-conformance.md:25-26` and `docs/TESTING_GUIDE.md:52-78`.

---

## Archival Readiness

**Status:** Initiative complete and ready for archival
**Next Steps:**
1. Move `plans/active/PARITY-HARNESS-002/` → `plans/archived/PARITY-HARNESS-002/`
2. Retain all reports under `plans/archived/PARITY-HARNESS-002/reports/` for future reference
3. Outstanding TODOs (TODO-001, TODO-002, TODO-003) should be captured in a follow-up initiative (e.g., `PARITY-REAL-SIM-001`)

**Dependencies for Future Work:**
- TODO-001 requires nanoBragg2 maintainer coordination or external golden data acquisition
- TODO-002 depends on nanobrag_torch simulator availability (currently stubbed)
- TODO-003 is independent and can proceed anytime

---

## Findings Applied Summary

| Finding ID | Description | Source Reference |
|------------|-------------|------------------|
| CONFORMANCE-001 | DB_AT_001 xfail policy with thresholds | `tests/dbex/test_db_at_001_parity.py:737-744` |
| DIAGNOSTICS-001 | First-divergence deterministic scan | `tests/fixtures/parity_loader.py:588-677` |
| TESTING-003 | Active selector compliance (>0 tests) | `docs/fix_plan.md:9`, collection logs |
| PARITY-001 | Numpy serialization guards | `tests/fixtures/parity_loader.py:550-585` |

---

**End of Closing Summary**
**Initiative:** PARITY-HARNESS-002
**Closure Timestamp:** 2025-10-29T022212Z
**Final Status:** done ✓
