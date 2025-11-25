# TOOLING-VIS-001 Phase D: Stage A Mapping ROI Diagnostics

**Date:** 2025-11-25T073500Z
**Focus:** Capture per-ROI mapping diagnostics on metadata-sigma smoke dataset
**Mode:** Parity
**Branch:** integration

## Objective

Diagnose whether Stage A's negative ROI correlations stem from geometric misregistration or structural mismatch by capturing per-ROI diagnostics from the mapping-aligned forward model on the metadata-sigma smoke dataset.

## Implementation

### Probe: `probe_mapping_roi_triptychs.py`

Created new T2 probe at `plans/active/TOOLING-VIS-001/bin/probe_mapping_roi_triptychs.py` implementing:

1. **DataLoad plumbing**: Metadata sigma source detection with early bailout if assets missing
2. **Mapping context**: Uses `build_mapping_stage_a_context` with metadata sigma tiles
3. **Per-ROI metrics**: Correlation, MSE, scale for all 92 ROIs
4. **Histogram generation**: Bin counts for correlation/MSE/scale distributions
5. **Triptych rendering**: PNG/NPZ artifacts for N lowest-correlation ROIs using `dbex.vis.triptych.plot_triptych`

### DB-AT-028/029 Execution

Ran `tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with metadata sigma source and artifact directories configured per `input.md`.

## Results

### Probe Metrics

**Critical Finding: Negative Median ROI Correlation**

```json
{
  "n_rois": 92,
  "correlation_median": -0.039912,
  "correlation_min": -0.204154,
  "correlation_max": 0.714256,
  "mse_median": 1387.6,
  "scale_median": 1.7866,
  "spot_scale_override": 3.1847e+17,
  "hkl_source": "raw",
  "hkl_count": 69614,
  "sigma_floor_value": 3.0
}
```

**Key Observations:**
- **Median correlation is NEGATIVE (-0.04)**: Most ROIs are anticorrelated with the experimental data
- **Correlation range [-0.20, 0.71]**: Wide spread, suggesting structural mismatch not just scaling
- **Spot scale override 3.2e+17**: Pathologically large calibration value (likely bug in helper calibration plumbing)
- **16 triptychs generated** for lowest-correlation ROIs (correlation < -0.08)

### DB-AT-028: Loss Scale Sanity (FAILED)

```
AssertionError: chi²/pixel initial 1.084e+05 exceeds 1e2 bound
```

**Failure Analysis:**
- Initial χ²/pixel: **1.084e+05** (spec tolerance: ≤ 1e2)
- **~1000x higher than spec bound**
- Indicates fundamental variance model mismatch or calibration failure
- Artifacts persisted: `db_at_028/db_at_028_metrics.json`, `db_at_028/mapping_context_fixture.json`

### DB-AT-029: Structure Parity (FAILED)

Expected failure given negative median correlation from probe. Artifacts persisted: `db_at_029/db_at_029_metrics.json`, `db_at_029/mapping_context_fixture.json`.

## Evidence Path

All artifacts under `plans/active/TOOLING-VIS-001/reports/2025-11-25T073500Z/`:

- `roi_diagnostics/roi_metrics.json` — per-ROI stats sorted by correlation
- `roi_diagnostics/roi_histogram.json` — bin counts for correlation/MSE/scale
- `roi_diagnostics/roi_*.png` — 16 triptychs for lowest-correlation ROIs
- `roi_diagnostics/roi_*.npz` — corresponding NPZ bundles
- `db_at_028/db_at_028_metrics.json` — chi²/pixel and clamp fraction
- `db_at_029/db_at_029_metrics.json` — ROI correlation before/after, scale ratios
- `pytest_db_at_028_029.log` — full pytest run log

## Diagnosis

The probe revealed a **systematic calibration or geometry alignment failure**:

1. **Negative median correlation (-0.04)** indicates the mapping model is anticorrelated with experimental data for most ROIs
2. **Chi²/pixel 1e5** (1000x spec bound) suggests the variance model or intensity scale is catastrophically wrong
3. **Spot scale override 3e+17** is pathologically large and likely indicates a bug in the calibration plumbing from `build_mapping_stage_a_context`

**Root Cause Hypothesis (based on artifacts):**
- The `spot_scale_override` value suggests the calibration plumbing may be missing a unit conversion or accumulating a product where it should set a scalar
- The negative correlations are **not** due to small geometric perturbations (those would shift correlation slightly, not flip sign)
- This points to a **structural mismatch** (wrong HKL grid, missing absorption term, or scale/flux miscalculation)

## Next Actions

Per input.md "If Blocked" section:
1. **Archive**: All probe/pytest artifacts captured per Hard Gate requirement
2. **Root cause**: The `spot_scale_override=3.2e+17` is the smoking gun; investigate `build_mapping_stage_a_context` calibration plumbing (likely `dbex.vis.mapping` or upstream factory)
3. **Escalate**: Mark TOOLING-VIS-001 as **blocked** pending calibration helper bugfix
4. **Follow-up probe**: Once calibration fixed, rerun probe + DB-AT-028/029 to validate chi²/pixel and ROI correlation recovery

## Spec Alignment

- **DB-AT-028** (docs/spec-db-conformance.md:287-315): χ²/pixel bound violated (1.08e5 >> 1e2)
- **DB-AT-029** (docs/spec-db-conformance.md:317-349): ROI correlation floor violated (median -0.04 << 0.2)
- **spec-db-vis.md §40-42**: Triptychs rendered per normative layout (Data | Model | Residual Z-score)

## Test Commands

**Probe:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=small \
python plans/active/TOOLING-VIS-001/bin/probe_mapping_roi_triptychs.py \
  --roi-count 16 \
  --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T073500Z/roi_diagnostics
```

**DB-AT-028/029:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T073500Z/db_at_028 \
DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T073500Z/db_at_029 \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
```

---

**Status:** Evidence captured, calibration bug identified, focus blocked pending fix
