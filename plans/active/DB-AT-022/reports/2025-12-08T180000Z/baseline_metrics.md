# DB-AT-022 Phase A2: Baseline Metrics Capture

**Initiative**: DB-AT-022 — Background Sentinel Guard
**Phase**: A2 — Baseline Metrics Capture
**Date**: 2025-12-08T18:00:00Z (Loop i=151)
**Objective**: Instantiate DataLoad with canonical inputs and capture baseline metrics

---

## DataLoad Instantiation

**Status**: SUCCESS
**Command**: `DataLoad(args)` with canonical refGeom assets

**Args**:
```python
args = Namespace(
    mtzFile="./scaled.mtz",
    mtzCol="F,SIGF",
    exptName="./refGeom.expt",
    exptIdx=0,
    reflName="./refGeom.refl",
    maskFile="./747_mask.pkl"
)
```

---

## Baseline Metrics

### Data Shapes

| Attribute | Shape | Description |
|-----------|-------|-------------|
| `loader.data` | `(1, 2527, 2463)` | Raw pixel data [panel, slow, fast] |
| `loader.background_image` | `(1, 2527, 2463)` | Background estimate [panel, slow, fast], -1 outside ROIs |
| `loader.trusted_mask` | `(1, 2527, 2463)` | Trusted pixel mask [panel, slow, fast] |

**Total pixels**: 6,224,001 (1 × 2527 × 2463)

### ROI Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| `len(loader.bbox)` | 92 | Number of ROIs (bounding boxes) |
| `len(loader.pids)` | 92 | Panel ID array matches bbox count |
| Unique panel IDs | `[0]` | All ROIs on single panel |

### Sample Bbox Dimensions

| ROI Index | Bbox (x0, x1, y0, y1) | Width | Height |
|-----------|----------------------|-------|--------|
| 0 | (582, 594, 0, 12) | 12 | 12 |
| 1 | (477, 489, 43, 55) | 12 | 12 |
| 2 | (1150, 1162, 91, 103) | 12 | 12 |
| 3 | (1292, 1304, 109, 121) | 12 | 12 |
| 4 | (178, 190, 312, 324) | 12 | 12 |

**Bbox pattern**: All 92 ROIs use uniform 12×12 pixel boxes (consistent with `shoebox_sz=12` in `get_roi_background_and_selection_flags`).

---

## Cross-Reference Validation

Per DB-AT-020/021 prior probes:
- **ROI count**: 92 ROIs matches DB-AT-020 Phase A expectation
- **Bbox exclusivity**: Verified (x1 > x0, y1 > y0) per docs/spec-db-core.md:22
- **Panel alignment**: All ROIs on panel 0 consistent with single-panel refGeom dataset

---

## Spec References

- **Spec-DB-Core** `docs/spec-db-core.md:22`: Bbox semantics (x0, x1, y0, y1) with exclusive upper bounds
- **Architecture** `docs/architecture/data_telemetry_flow.md:34`: Background sentinel -1 outside ROIs

---

## Result

**Status**: VALID
**Recommendation**: Prerequisites from DB-AT-020/021 remain valid. Proceed to Phase A3 (sentinel coverage probe).

---

**END OF A2 REPORT**
