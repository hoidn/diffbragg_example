# DB-AT-023 Phase A2 — Baseline Metrics Capture

**Initiative**: DB-AT-023 (Calibration Policy Guard — ADU vs Photons)
**Phase**: A2 — Baseline Metrics Capture
**Date**: 2025-12-08T02:21:01Z
**Method**: Python probe via `dbex.data_load.DataLoad` with canonical refGeom assets

---

## Executive Summary

Baseline calibration context captured from `DataLoad` instantiation with canonical inputs (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`). Key findings:

1. **92 ROIs** extracted, covering 13,158 pixels (0.21% of detector)
2. **No sigma_readout_map** loaded (source=None) — Phase B tests will exercise sigma sourcing paths
3. **No torch_config** provided — current baseline uses hardcoded/MTZ defaults
4. **Unit mode**: ADU (implicit — no `--adu-per-photon` conversion applied)

---

## Data Shape & ROI Statistics

| Metric | Value |
|--------|-------|
| `data.shape` | `[1, 2527, 2463]` (1 panel, slow, fast) |
| `n_rois` | 92 |
| `n_panels` | 1 |
| `trusted_mask_shape` | `[1, 2527, 2463]` |
| `trusted_mask_fraction` | 91.53% |
| `roi_pixel_count` | 13,158 |
| `total_pixel_count` | 6,224,001 |
| `roi_fraction` | 0.21% |

---

## Background-Subtracted ROI Sample Metrics

These metrics anchor acceptance thresholds for Phase B calibration tests.

### ROI Background (estimated)
| Statistic | Value |
|-----------|-------|
| Mean | 2.97 ADU |
| Std | 2.21 ADU |
| Min | 0.01 ADU |
| Max | 12.98 ADU |

### ROI Target (background-subtracted)
| Statistic | Value |
|-----------|-------|
| Mean | 62.66 ADU |
| Std | 986.03 ADU |
| Min | -7.98 ADU |
| Max | 53,234.62 ADU |
| Sum | 824,445.81 ADU |

### ROI Raw Data
| Statistic | Value |
|-----------|-------|
| Mean | 65.63 ADU |
| Std | 986.12 ADU |
| Min | -2.0 ADU |
| Max | 53,238.0 ADU |

---

## Current Calibration Context

### Sigma Sourcing Status

| Attribute | Value | Notes |
|-----------|-------|-------|
| `sigma_readout_map_source` | `None` | No sigma map loaded |
| `sigma_readout_map_metadata` | `None` | No CLI --sigma-map or external_lookup |

**Interpretation**: Per spec-db-workflow.md:36-37, sigma_readout MUST follow the canonical ladder. With no map/scalar/external tiles provided, the current baseline relies on legacy hardcoded defaults (non-conformant per spec).

**Phase B requirement**: Test harness must exercise:
1. CLI `--sigma-map` path (scalar or map)
2. Experiment file `external_lookup` sigma metadata
3. Guardrail enforcement when sigma is missing

### Calibration Metadata (not provided)

The following calibration fields are NOT present in the current baseline (no torch_config):

| Field | Current State | Spec Requirement |
|-------|---------------|------------------|
| `spot_scale_override` | Not provided | MUST be provided (spec-db-workflow.md:40) |
| `sigma_floor` | Not provided | MUST be provided (spec-db-workflow.md:37) |
| `beam_flux` | Not provided | SHOULD be provided (spec-db-workflow.md:43) |
| `beam_exposure` | Not provided | SHOULD be provided (spec-db-workflow.md:43) |
| `beamsize_mm` | Not provided | MAY default to None (spec-db-workflow.md:44) |
| `N_cells` | Not provided | MAY default to 1 (spec-db-workflow.md:44) |
| `adu_per_photon` | Not provided | Unit mode = ADU when absent |

**Interpretation**: Current run uses implicit ADU mode with no gain conversion. Phase B implementation must surface these fields via CLI flags and torch_config.

---

## Detector/Beam/Crystal Geometry

### Detector (Panel 0)
| Attribute | Value |
|-----------|-------|
| Distance (mm) | 231.28 |
| Pixel size (mm) | [0.172, 0.172] |
| Image size (px) | [2463, 2527] (fast, slow) |

### Beam
| Attribute | Value |
|-----------|-------|
| Wavelength (A) | 0.9768 |
| Polarization fraction | 0.999 |

### Crystal
| Attribute | Value |
|-----------|-------|
| Unit cell | [27.38, 32.07, 34.47, 88.77, 71.63, 68.19] |
| Space group | P 1 |

### Structure Factors (MTZ)
| Attribute | Value |
|-----------|-------|
| Reflections | 64,333 (after Bijvoet mate generation) |
| Unit cell | [27.41, 32.12, 34.50, 88.66, 71.55, 68.10] |

**Note**: Minor unit cell discrepancy between crystal model (from refGeom.expt) and MTZ file — expected due to different refinement rounds.

---

## Phase B Input Requirements (derived from baseline)

Based on this baseline, Phase B (Implementation & Testing) must address:

### B1: CLI Extension (`--adu-per-photon`)

```bash
# Expected usage pattern
python -m dbex.refine_one --adu-per-photon 1.5 ...

# Validation: targets converted to photons
target_photons = target_adu / adu_per_photon
```

### B2: `prepare_refinement_inputs` Photon Conversion

When `adu_per_photon > 0`:
- `target = target_adu / adu_per_photon`
- `sigma_readout = sigma_readout_adu / adu_per_photon`
- `sigma_floor = sigma_floor_adu / adu_per_photon`

Surface in telemetry:
- `unit_mode: "photon" | "ADU"`
- `gain: <adu_per_photon value>`

### B3: Test Fixtures

Phase B tests should use baseline metrics for assertions:
- ROI count: 92
- Background mean: ~3 ADU
- Target mean: ~63 ADU (background-subtracted)
- Data shape: [1, 2527, 2463]

---

## Calibration Ladder Reference

From spec-db-workflow.md:34 (Precedence ladder, highest to lowest):

1. **torch_config** (if provided)
2. **CLI overrides**
3. **external_lookup payloads**
4. **refined MTZ metadata**
5. **raw MTZ defaults**
6. **hardcoded defaults**

**Phase B guard**: When torch_config and CLI both define the same field (gain/adu_per_photon, sigma_floor, spot_scale_override, beam flux/exposure, beamsize_mm, N_cells) and disagree, the run SHALL fail with a clear error (no silent overrides).

---

## Artifacts

- `baseline_metrics.md` — This report
- Python probe command: See `input.md:123-137` (How-To Map)
