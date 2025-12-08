# A3 — Baseline Probe

## Methodology

Executed lightweight DataLoad inspection via Python REPL (thin wrapper ≤50 LOC per PROBE-FREEZE-001) to capture ROI and panel metrics from refGeom assets.

**Method**: Instantiated `dbex.data_load.DataLoad` with canonical args:
```python
args = Namespace(
    mtzFile="scaled.mtz",
    mtzCol="I(+),SIGI(+),I(-),SIGI(-)",
    exptName="refGeom.expt",
    exptIdx=0,
    reflName="refGeom.refl",
    maskFile="747_mask.pkl"
)
DL = DataLoad(args)
```

## Panel & ROI Summary

- **Panel count**: 1
- **ROI tally**: 92 reflections
- **Data shape**: `(1, 2527, 2463)` — [panel, slow, fast] per spec-db-core.md:20
- **Background shape**: `(1, 2527, 2463)` — matches data
- **Trusted mask shape**: `(1, 2527, 2463)` — DIALS convention (True=trusted)

## Panel Dimensions

| Panel | Image Size (fast, slow) | Fast Dimension | Slow Dimension |
|-------|-------------------------|----------------|----------------|
| 0     | (2463, 2527)            | 2463           | 2527           |

## Sample Bbox Deltas (first 10 ROIs)

**Bbox structure**: 4-tuple `(x0, x1, y0, y1)` per spec-db-core.md:22

| ROI | Panel | Bbox (x0, x1, y0, y1) | Width | Height | Data Shape | BG Shape |
|-----|-------|-----------------------|-------|--------|------------|----------|
| 0   | 0     | (582, 594, 0, 12)     | 12    | 12     | (12, 12)   | (12, 12) |
| 1   | 0     | (477, 489, 43, 55)    | 12    | 12     | (12, 12)   | (12, 12) |
| 2   | 0     | (1150, 1162, 91, 103) | 12    | 12     | (12, 12)   | (12, 12) |
| 3   | 0     | (1292, 1304, 109, 121)| 12    | 12     | (12, 12)   | (12, 12) |
| 4   | 0     | (178, 190, 312, 324)  | 12    | 12     | (12, 12)   | (12, 12) |
| 5   | 0     | (715, 727, 429, 441)  | 12    | 12     | (12, 12)   | (12, 12) |
| 6   | 0     | (1837, 1849, 440, 452)| 12    | 12     | (12, 12)   | (12, 12) |
| 7   | 0     | (570, 582, 448, 460)  | 12    | 12     | (12, 12)   | (12, 12) |
| 8   | 0     | (1155, 1167, 455, 467)| 12    | 12     | (12, 12)   | (12, 12) |
| 9   | 0     | (1280, 1292, 469, 481)| 12    | 12     | (12, 12)   | (12, 12) |

## Bounds Validation (first 5 ROIs)

All sampled ROIs satisfy bbox exclusivity and bounds conformance per spec-db-core.md:22:

| ROI | Panel | X Bounds [x0, x1] | Fast Dim | Y Bounds [y0, y1] | Slow Dim | Valid X | Valid Y |
|-----|-------|-------------------|----------|-------------------|----------|---------|---------|
| 0   | 0     | [582, 594]        | 2463     | [0, 12]           | 2527     | ✓       | ✓       |
| 1   | 0     | [477, 489]        | 2463     | [43, 55]          | 2527     | ✓       | ✓       |
| 2   | 0     | [1150, 1162]      | 2463     | [91, 103]         | 2527     | ✓       | ✓       |
| 3   | 0     | [1292, 1304]      | 2463     | [109, 121]        | 2527     | ✓       | ✓       |
| 4   | 0     | [178, 190]        | 2463     | [312, 324]        | 2527     | ✓       | ✓       |

**Validation criteria**:
- `x1 > x0` and `y1 > y0` (exclusivity) ✓
- `x0 >= 0`, `y0 >= 0` (non-negative lower bounds) ✓
- `x1 <= fast_dim`, `y1 <= slow_dim` (upper bounds within panel dimensions) ✓

## ROI Statistics (all 92 reflections)

| Metric | Width (x1 - x0) | Height (y1 - y0) |
|--------|-----------------|------------------|
| Min    | 12              | 12               |
| Max    | 12              | 12               |
| Mean   | 12.0            | 12.0             |
| Median | 12.0            | 12.0             |

**Observation**: All ROIs have uniform 12×12 dimensions, consistent with `shoebox_sz=12` parameter in `utils.get_roi_background_and_selection_flags()` (dbex/data_load.py:354-357).

## Panel Slicing Verification

For all sampled ROIs, slicing `DL.data[pid, y0:y1, x0:x1]` and `DL.background_image[pid, y0:y1, x0:x1]` produces shapes matching `(y1 - y0, x1 - x0)` as expected per dials_api.md:26 and spec-db-core.md:22.

Example (ROI 0):
- Bbox: `(582, 594, 0, 12)` → width=12, height=12
- Data slice shape: `(12, 12)` ✓
- Background slice shape: `(12, 12)` ✓

## Alignment with ARCH-CONTRACT-DATA-LOAD-001

**Owner API**: `dbex.data_load.DataLoad.__init__(args)` (docs/architecture/module_map.md:45-62)

**Boundary outputs validated**:
1. **Reflection table ingestion**: 92 reflections loaded from `refGeom.refl` for experiment index 0
2. **Bbox extraction**: 92 ROI bboxes in 4-tuple format `(x0, x1, y0, y1)`
3. **Panel alignment**: All `DL.pids` values are 0 (single-panel detector), within detector range `[0, 1)`
4. **DataLoad outputs**: `data`, `background_image`, `bbox`, `pids`, `trusted_mask` all present and aligned

## Findings

- **Bbox format**: DataLoad produces 4-tuple `(x0, x1, y0, y1)` (not 6-tuple), consistent with spec-db-core.md:22 and dials_api.md:9
- **Exclusivity conformance**: All sampled bboxes satisfy `x1 > x0`, `y1 > y0`, and upper bounds within panel dimensions
- **Panel slicing**: Slicing `data[pid, y0:y1, x0:x1]` produces expected shapes for all sampled ROIs
- **Panel ordering**: Single-panel detector with all `pids=0`; panel alignment trivial but valid
- **Mask polarity**: Trusted mask loaded successfully with DIALS convention (True=trusted) per spec-db-core.md:29

## Phase B Test Assertions (grounded by baseline)

DB-AT-020 Phase B tests will validate:

1. **Bbox exclusivity**:
   ```python
   for bbox in dl.bbox:
       x0, x1, y0, y1 = bbox
       assert x1 > x0, f"Invalid bbox width: {bbox}"
       assert y1 > y0, f"Invalid bbox height: {bbox}"
   ```

2. **Bounds conformance**:
   ```python
   for i, (bbox, pid) in enumerate(zip(dl.bbox, dl.pids)):
       x0, x1, y0, y1 = bbox
       panel = dl.detector[pid]
       fast_dim, slow_dim = panel.get_image_size()
       assert x0 >= 0 and x1 <= fast_dim, f"ROI {i} x-bounds outside panel"
       assert y0 >= 0 and y1 <= slow_dim, f"ROI {i} y-bounds outside panel"
   ```

3. **Slicing shape validation**:
   ```python
   for i, (bbox, pid) in enumerate(zip(dl.bbox, dl.pids)):
       x0, x1, y0, y1 = bbox
       data_slice = dl.data[pid, y0:y1, x0:x1]
       bg_slice = dl.background_image[pid, y0:y1, x0:x1]
       assert data_slice.shape == (y1 - y0, x1 - x0), f"ROI {i} data slice shape mismatch"
       assert bg_slice.shape == (y1 - y0, x1 - x0), f"ROI {i} background slice shape mismatch"
   ```

4. **Panel ID range**:
   ```python
   for pid in dl.pids:
       assert 0 <= pid < len(dl.detector), f"Panel ID {pid} outside detector range"
   ```

## Cross-references

- **SPEC**: docs/spec-db-core.md:22 (bbox semantics), docs/dials_api.md:9 (reflection schema)
- **ARCH**: docs/architecture/module_map.md:45-62 (DataLoad boundary), docs/architecture.md:122 (runtime guards)
- **Implementation**: dbex/data_load.py:353-357 (bbox extraction via `utils.get_roi_background_and_selection_flags`)
- **Raw output**: plans/active/DB-AT-020/reports/2025-12-08T050000Z/baseline_probe_output.txt
