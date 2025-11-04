# MAP-SCALE-001 Loop Summary: Calibration Metadata Plumbing (2025-11-04T110000Z)

## Objective
Port DiffBragg calibration metadata (√spot_scale_override, beam flux/exposure) into the zero-iteration helper (`simulate_forward_once`) so DB_AT_024 can assert intensity thresholds with calibrated scaling applied.

## Implementation Summary

### Changes Made

1. **Created calibration loader** (`dbex/nanobrag_bridge.py:606-678`)
   - New function `load_calibration_metadata(config_json_path)` extracts:
     - `spot_scale_override` from `crystal.scale_override`
     - `beam_flux` and `beam_exposure` from `beam` section
   - Validates positive values per SCALE-002 requirements
   - Returns dict with calibration metadata

2. **Updated `simulate_forward_once` documentation** (`dbex/nanobrag_bridge.py:712-714`)
   - Added guidance to source `spot_scale_override` from DiffBragg metadata via `load_calibration_metadata()`
   - Clarified that default behavior (None) uses 1.0 scale factor

3. **Copied calibration fixture** (`tests/fixtures/golden_data/simple_cubic/config_torch.json`)
   - Canonical DiffBragg metadata from `plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T012616Z/golden_dataset/torch/config_torch.json`
   - Contains `spot_scale_override = 3.185e17`, `sqrt = 5.643e8`

4. **Updated DB_AT_024 test** (`tests/dbex/test_mapping_consistency.py:35-39, 73, 92-99, 137-152, 188-194, 254`)
   - Imports `load_calibration_metadata`
   - Loads calibration fixture in `canonical_assets` fixture
   - Passes `spot_scale_override` to `simulate_forward_once`
   - Adds calibration metadata to `summary_metrics` JSON output
   - Prints calibration info in test summary

### Test Results

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T110000Z \
pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
```

**Status:** XFAIL (expected, thresholds not yet met)

**Metrics** (`mapping_metrics.json`):
- `corr_median`: 0.0489 (target ≥ 0.2)
- `localization_success_rate`: 0.0 (target ≥ 0.90)
- `spot_scale_override`: 3.185e17
- `sqrt_spot_scale`: 5.643e8 (applied post-simulation per SCALE-002)
- `target_mean_masked`: 63.03 ADU
- `bragg_stats.mean`: 1.45e6 (post-scaling)
- `mean_ratio_scaled`: 1.39e-05 (target/bragg) — **overshoot by ~23,000×**

### Key Observations

1. **Calibration metadata successfully plumbed**: The code loads and applies `√spot_scale_override` correctly per SCALE-002.

2. **Overshooting by ~23,000×**: After applying the calibration scale, the Bragg output is **vastly larger** than the target intensities. The ratio `target/bragg_scaled ≈ 1.4e-05` indicates the simulator is producing intensities ~23,000× too bright.

3. **Root cause confirmed**: Per `plans/active/MAP-SCALE-001/reports/2025-11-04T084948Z/summary.md`, the scale gap decomposes into:
   - **(a)** Missing DiffBragg `spot_scale_override` — **NOW ADDRESSED**
   - **(b)** Absence of refined structure-factor amplitudes (`Fopt`) — **STILL MISSING**

4. **Structure factor mismatch**: The zero-iteration helper uses **unrefined MTZ amplitudes** (`scaled.mtz`), while the golden dataset (and DiffBragg refinement) uses **refined Fopt** that are ~94,000× smaller (per 2025-11-04T084948Z analysis). Applying `√spot_scale` to unrefined |F| values produces the observed overshoot.

### Implications

**Calibration metadata is necessary but not sufficient** to reach DB_AT_024 thresholds. To align with the golden dataset:

1. **Option A (recommended)**: Source refined structure factors (`Fopt`) from DiffBragg outputs instead of `scaled.mtz`. This requires:
   - Capturing `Fopt` during DiffBragg refinement (e.g., write to HDF5 or separate MTZ)
   - Updating `simulate_forward_once` or test fixture to load refined amplitudes
   - Maintaining SCALE-001 (no pre-scaling of |F|) and SCALE-002 (post-sim scaling)

2. **Option B (analysis-mode fallback)**: Apply an empirical downscale factor (~1/√94000 ≈ 0.00326) to the current MTZ amplitudes as a diagnostic proxy. This would align intensities but violates provenance (not DiffBragg-derived).

**Next action**: The current loop delivers on the "Do Now" (plumb calibration metadata) but does **not** resolve the intensity mismatch. A follow-up loop is required to source refined structure factors per Option A.

### Artifacts

All artifacts saved under `plans/active/MAP-SCALE-001/reports/2025-11-04T110000Z/`:
- `mapping_metrics.json` — Per-ROI correlation/localization with calibration metadata
- `mapping_metrics.csv` — Per-ROI detailed metrics table
- `pytest.log` — Full test run log (targeted)
- `collect_db_at_024.log` — pytest collection log for DB_AT_024 selector
- `summary.md` — This document

## Acceptance & Module Scope

**Acceptance focus:** AT-49 (DB_AT_024 mapping consistency with calibrated scaling)

**Module scope:** `{ data models }` — calibration loader + test fixture updates; no simulator changes required

## SPEC/ADR Alignment

**SPEC references implemented:**
- `docs/spec-db-workflow.md:30` — Stage A global scale expectations (ADU mode)
- `docs/spec-db-conformance.md:43-46` — DB_AT_024 acceptance thresholds and artifact requirements
- `docs/architecture.md:88` — ADR-02 (ADU vs photon policy and learnable scale)

**ADRs applied:**
- SCALE-001 — Structure factors pass through unscaled (maintained)
- SCALE-002 — Reapply DiffBragg √spot_scale_override post-simulation (implemented)
- SCALE-003 — Source calibration metadata from DiffBragg outputs (implemented)

## Testing Gate

**Targeted test:** `pytest -v tests -k DB_AT_024` — **PASSED** (XFAIL as expected)

**Full suite:** Deferred (no production simulator changes; only test/fixture updates)

**Selector status:** Active, collects 1 test (`test_db_at_024_mapping_smoke`)

## Version Control

**Files changed:**
- `dbex/nanobrag_bridge.py` — Added `load_calibration_metadata()`, updated docstrings
- `tests/dbex/test_mapping_consistency.py` — Load/apply calibration metadata, add to metrics output
- `tests/fixtures/golden_data/simple_cubic/config_torch.json` — New fixture (copied from golden dataset)

**Commit message:**
```
MAP-SCALE-001 calibration: plumb spot_scale_override into DB_AT_024 (tests: DB_AT_024 XFAIL)

- Add load_calibration_metadata() to bridge for DiffBragg config JSON parsing
- Update DB_AT_024 test to load config_torch.json fixture and apply spot_scale_override
- Copy canonical calibration metadata to tests/fixtures/golden_data/simple_cubic/
- Confirm SCALE-002 (sqrt scaling post-sim) applied correctly
- Metrics: corr_median=0.049 (overshoot ~23k×), confirming refined Fopt still needed

Addresses: MAP-SCALE-001, DB-AT-024, SCALE-002, SCALE-003
Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T110000Z/
Next: Source refined structure factors (Fopt) to resolve intensity mismatch
```

## Next Most-Important Item

**MAP-SCALE-002** (new, recommended): Source refined structure-factor amplitudes (`Fopt`) from DiffBragg refinement outputs to resolve the ~23,000× intensity overshoot observed after applying calibration scale. This requires:
1. Identifying where DiffBragg writes refined `Fopt` (HDF5 group, separate MTZ, or in-memory during refinement)
2. Updating `simulate_forward_once` or test fixture loader to substitute refined amplitudes for MTZ |F|
3. Validating that median correlation reaches ≥ 0.2 and localization ≥ 90% per DB_AT_024 thresholds
4. Documenting the Fopt sourcing strategy in `docs/findings.md` as SCALE-004
