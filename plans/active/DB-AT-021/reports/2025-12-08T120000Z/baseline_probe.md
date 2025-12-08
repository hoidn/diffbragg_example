# DB-AT-021 Phase A3 Baseline Probe

**Objective**: Establish baseline metrics for DataLoad mask handling

**Assets**: refGeom.expt, refGeom.refl, scaled.mtz, 747_mask.pkl (canonical per DB-AT-SUITE-CARE-001 Phase B.2)

---

## Metrics

- **trusted_mask_shape**: (1, 2527, 2463)
- **trusted_mask_dtype**: bool
- **trusted_pixel_count**: 5696996
- **untrusted_pixel_count**: 527005
- **loss_mask_construction_formula**: (background >= 0) & trusted_mask
- **loss_mask_pixel_count**: 13084
- **sample_roi_index**: 0
- **sample_roi_bbox**: (582, 594, 0, 12)
- **sample_roi_trusted_pixels**: 144
- **sample_roi_loss_mask_pixels**: 144
- **sample_roi_background_valid_pixels**: 144
- **sample_roi_background_sentinel_pixels**: 0

---

## Validation

**trusted_mask polarity**: DIALS convention (True=trusted)
- Verified dtype: bool (expected: bool)

**loss_mask construction**: Per spec-db-core.md:124
- Formula: `(background >= 0) & trusted_mask`
- Computed pixels: 13084
- Expected: trusted pixels (5696996) intersected with background-valid pixels

**Background sentinel**: -1 outside ROIs (per spec-db-core.md, architecture.md ADR-07)
- Sample ROI 0: 144 valid, 0 sentinel

**Status**: ✅ Baseline metrics captured
