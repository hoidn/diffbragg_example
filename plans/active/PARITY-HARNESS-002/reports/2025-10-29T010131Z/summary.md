# PARITY-HARNESS-002 Phase A Summary

**Date:** 2025-10-29T010131Z  
**Focus:** PARITY-HARNESS-002 — Bootstrap DB-AT parity harness with golden data and manifest validation  
**Status:** Complete (A1-A4)

## Deliverables

### A1: Dataset Inventory (Complete)
- Probed for nanoBragg2 golden data: NOT FOUND (external repo not cloned)
- Documented fallback strategy in `notes_phase_a.md`
- Confirmed refGeom.expt, refGeom.refl, scaled.mtz available for fallback generation

### A2: Golden Data Generation (Complete)
- Created `scripts/generate_simple_cubic_golden.py` generator script
- Generated FALLBACK golden dataset under `tests/fixtures/golden_data/simple_cubic/`:
  - `bragg_panel_0.npy` (synthetic Gaussian pattern on ROI support)
  - `target_panel_0.npy` (background-subtracted refGeom data)
  - `loss_mask_panel_0.npy` (loss mask from bridge)
  - `metadata.json` (detector/beam/crystal config snapshot)
  - `manifest.json` (SHA256 checksums per spec)
- Manifest SHA256: `df88c7d20757f0900c2829d01ceb00fade96b68203bfbd00e4fcb1b5238ebf6d`
- All files validated with SHA256 checksums
- Provenance documented: synthetic Bragg (stub), refGeom targets, FALLBACK pending canonical nanoBragg2 data

### A3: Loader & Fixture Implementation (Complete)
- Created `tests/fixtures/parity_loader.py` with:
  - `load_golden_data()` function with SHA256 checksum validation
  - `validate_manifest()` enforcing checksum integrity per `docs/parity_harness_spec.md:36-37`
  - `validate_tensor_ordering()` enforcing `[panel, slow, fast]` per `docs/spec-db-core.md:24`
  - `validate_pixel_pitch()` enforcing square pixels per `docs/spec-db-core.md:43`
  - `GoldenData` NamedTuple container for golden data + metadata
- Created `tests/dbex/test_db_at_001_parity.py` with minimal manifest integrity tests:
  - `test_manifest_integrity`: Validates checksums, shapes, dtypes, [slow, fast] ordering
  - `test_golden_data_sanity`: Sanity checks on tensor content (non-negative, finite, coverage)
  - `test_pixel_pitch_guard`: Validates square pixel pitch constraint
- All 3 tests PASS (1.07s runtime, CPU, Python 3.9.23, pytest 8.4.2)

### A4: Baseline Smoke Guard (Complete)
- Re-ran `tests/dbex/test_nanobrag_smoke.py`: 3/3 tests PASSED (1.82s runtime)
- Confirmed fixture integration did not break existing bridge smoke coverage
- Collected smoke selector evidence: 3 tests

## Metrics

- **Tests authored:** 3 (DB_AT_001 manifest integrity tests)
- **Tests passing:** 3/3 DB_AT_001 + 3/3 smoke = 6/6
- **Collection counts:**
  - DB_AT_001: 3 tests collected (up from 0)
  - Smoke: 3 tests collected (unchanged)
- **Runtime:** 1.07s (DB_AT_001), 1.82s (smoke)
- **Golden data files:** 5 (bragg, target, loss_mask, metadata, manifest)
- **Manifest checksum:** df88c7d20757f0900c2829d01ceb00fade96b68203bfbd00e4fcb1b5238ebf6d
- **Provenance:** FALLBACK dataset (synthetic Bragg, refGeom targets)

## Artifacts

All artifacts stored under `plans/active/PARITY-HARNESS-002/reports/2025-10-29T010131Z/`:
- `notes_phase_a.md` — Dataset inventory and fallback strategy
- `generate_golden_data.log` — Golden data generation log
- `checksums.txt` — Manifest with SHA256 checksums
- `pytest_DB_AT_001.log` — DB_AT_001 test run log (3 passed)
- `collect_DB_AT_001.log` — DB_AT_001 collection log (3 tests)
- `pytest_smoke.log` — Smoke test run log (3 passed)
- `collect_smoke.log` — Smoke test collection log (3 tests)
- `summary.md` — This file

## Documentation Updates

- `docs/TESTING_GUIDE.md`:
  - Updated DB_AT_001 status to "Active (manifest only)"
  - Added fallback dataset provenance notes
  - Added collection log reference
  - Added new row in §2.1 for "Parity harness (manifest)"
- `docs/development/TEST_SUITE_INDEX.md`:
  - Updated DB_AT_001 status to "active (partial)"
  - Added new row in Active Implementation Coverage
  - Synchronized with TESTING_GUIDE.md

## Findings Applied

- **CONFORMANCE-001**: Manifest validation with SHA256 checksums per spec
- **GEOMETRY-001**: Enforced [panel, slow, fast] ordering and pixel pitch guards
- **TESTING-003**: Collected pytest evidence for selector compliance
- **DIAGNOSTICS-001**: Artifact capture aligns with HDF5 diagnostics expectations

## Next Actions

Per `plans/active/PARITY-HARNESS-002/implementation.md`:

**Phase B (pending):** Harness utilities
- B1: Implement `compute_parity_metrics()` helper (correlation, MSE, RMSE, max|Δ|, sum_ratio)
- B2: Artifact writers for `metrics.json` and trace logs
- B3: Trace capture integration with nanobrag_torch debug_config

**Phase C (pending):** Full DB-AT-001 parity test
- C1: Parametrize over dtype/device
- C2: Enforce correlation ≥0.99 and RMSE thresholds
- C3: Generate diff heatmaps and trace logs

**Blocked pending:** Real nanobrag_torch simulator (currently using stub Bragg tensor)

## Exit Criteria Status

Per PARITY-HARNESS-002 in `docs/fix_plan.md`:

1. ✅ Document parity dataset gap and ship manifest schema + checksum validation
2. ⏸️  Author reusable parity harness utilities (Phase B, pending)
3. ⏸️  Implement pytest selector DB_AT_001 enforcing thresholds (Phase C, pending simulator)
4. ✅ Update testing registries with Active selector and collect-only logs

**Overall status:** Phase A complete, Phases B-E remain in_progress pending simulator availability.
