# DB-AT-023 Phase A1 — Asset Availability Check

**Initiative**: DB-AT-023 (Calibration Policy Guard — ADU vs Photons)
**Phase**: A1 — Asset Availability
**Date**: 2025-12-08T02:21:01Z
**Cross-reference**: Loop i=143 asset validation (`plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/asset_validation.md`)

---

## Executive Summary

**Status**: ALL VALID — Cross-referenced loop i=143 centralized validation confirms all 4 canonical assets are present, loadable, and format-valid.

---

## Asset Inventory (from i=143 validation)

| Asset | Path | Size | SHA256 (first 16 hex) | Format Check | Status |
|-------|------|------|----------------------|--------------|--------|
| `refGeom.expt` | `./refGeom.expt` | 5.1K | 184d744fe62d51c1 | Valid JSON with detector/beam/crystal keys (1 panel) | VALID |
| `refGeom.refl` | `./refGeom.refl` | 202K | 7ab679640d867a8c | DIALS reflection table, 282 reflections, bbox column present | VALID |
| `scaled.mtz` | `./scaled.mtz` | 2.8M | 341108a13c56bc82 | MTZ structure factors, 34807 reflections, 21 columns | VALID |
| `747_mask.pkl` | `./747_mask.pkl` | 6.0M | 3603bd8aa32a36fd | Pickle loadable (tuple container) | VALID |

**Full checksums** (baseline established in i=143):
```
184d744fe62d51c129b8972318b8a778e3dcbb904775948527e9c575e93a24c1  refGeom.expt
7ab679640d867a8ccbb0652575647a830e2cca42bc49211128ed855ff0685774  refGeom.refl
341108a13c56bc8290ea96d5b8a0bae33ab7670340d191273eecb29de0cce2ae  scaled.mtz
3603bd8aa32a36fd48cae271494a762c4315a4a45ba7e5d1239d0c8f57bb5848  747_mask.pkl
```

---

## DB-AT-023 Asset Requirements

Per `plans/active/DB-AT-023/implementation.md:4-6`:

1. **refGeom.expt** — Required for experiment geometry (detector, beam, crystal)
2. **refGeom.refl** — Required for reflection table with bbox/panel columns
3. **scaled.mtz** — Required for structure factor amplitudes
4. **747_mask.pkl** — Required for trusted pixel mask

**Cross-reference confirmation**: All assets listed in DB-AT-023 Phase A1 requirements match the centralized validation in loop i=143. No additional asset validation needed.

---

## Calibration-Specific Asset Notes

For DB-AT-023 Phase B (Calibration Policy Guard implementation), the following calibration assets MAY be required:

1. **torch_config JSON** — Optional calibration config (e.g., `sp.proc/calibration/config_torch_smoke.json`)
   - Provides: `spot_scale_override`, `flux`, `exposure`, `beamsize_mm`, `N_cells`
   - Status: Optional for Phase A (baseline capture); required for Phase B unit mode testing

2. **Sigma readout map** — Optional external sigma tiles
   - Sources: CLI `--sigma-map` OR experiment file `external_lookup`
   - Status: Documented in spec-db-core.md:32-68; Phase B tests will exercise both paths

3. **MTZ metadata** — Structure factors with optional calibration columns
   - Standard columns: H, K, L, IMEAN, SIGIMEAN, F, SIGF, anomalous pairs
   - Status: `scaled.mtz` confirmed valid with 21 columns including anomalous pairs

---

## Validation Method

This report cross-references the centralized asset validation performed in loop i=143 (DB-AT-SUITE-CARE-001 Phase B.2) rather than duplicating file existence checks. The i=143 validation:

1. Confirmed file existence via `ls -lh`
2. Computed SHA256 checksums
3. Executed format sanity checks using DIALS/cctbx imports
4. Verified all format checks passed

**Rationale**: Per `input.md:119` (Pitfalls To Avoid #3): "Cross-reference existing assets — i=143 already validated; don't duplicate file checks."

---

## Findings & Recommendations

1. **No asset blockers** for DB-AT-023 Phase A — all required assets are valid
2. **Proceed to A2** (baseline metrics capture) using canonical asset paths
3. **Phase B prerequisites**: torch_config and sigma_readout_map assets documented for reference but not strictly required for Phase A

---

## Artifacts

- `asset_availability.md` — This report
- Cross-reference: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/asset_validation.md`
