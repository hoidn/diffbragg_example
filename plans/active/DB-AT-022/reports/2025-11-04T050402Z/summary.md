# DB-AT-022 — Planning Summary (2025-11-04T050402Z)

## Focus
- Initiative: DB-AT-022 — Background sentinel guard
- Goal: Verify simtbx background sentinel behavior and scope acceptance test + guard implementation for ROI background semantics.

## Key References Consulted
- `docs/spec-db-conformance.md:34-45` — DB_AT_022 setup and expectations (sentinel logic, ROI coverage).
- `docs/simtbx_api.md:18-44` — Background estimation contract (`-1` sentinel, bbox semantics).
- `docs/TESTING_GUIDE.md:60-96`, `docs/development/TEST_SUITE_INDEX.md:1-40` — Selector registry showing DB_AT_022 as Planned.
- `docs/dials_api.md:10-68` — Reflection bbox schema aligning ROI slices.
- Findings applied: CONFORMANCE-001, CONFIG-001, MASKING-001, TESTING-003.

## Micro / One-off Probes
### Sentinel Coverage Probe (T1)
```python
from types import SimpleNamespace
import numpy as np
from pathlib import Path
from dbex.data_load import DataLoad

args = SimpleNamespace(
    mtzFile='scaled.mtz',
    mtzCol='F,SIGF',
    exptName='refGeom.expt',
    exptIdx=0,
    reflName='refGeom.refl',
    maskFile='747_mask.pkl'
)
for path in [args.mtzFile, args.exptName, args.reflName, args.maskFile]:
    assert Path(path).exists(), f"Missing asset: {path}"
DL = DataLoad(args)
roi_mask = np.zeros_like(DL.background_image, dtype=bool)
for pid, (x0, x1, y0, y1) in zip(DL.pids, DL.bbox):
    roi_mask[int(pid), int(y0):int(y1), int(x0):int(x1)] = True
sentinel_mask = np.isclose(DL.background_image, -1.0)
print({
    'shape': DL.background_image.shape,
    'roi_count': len(DL.bbox),
    'roi_pixels': int(roi_mask.sum()),
    'sentinel_pixels': int(sentinel_mask.sum()),
    'overlap_pixels': int(np.sum(roi_mask & sentinel_mask)),
    'roi_fraction': float(roi_mask.mean()),
    'sentinel_fraction': float(sentinel_mask.mean()),
})
```
Output:
```
{'shape': (1, 2527, 2463), 'roi_count': 92, 'roi_pixels': 13248, 'sentinel_pixels': 6210753, 'overlap_pixels': 0, 'roi_fraction': 0.002128534362382011, 'sentinel_fraction': 0.997871465637618}
```

### ROI Background Distribution Probe (T1)
```python
roi_bg = DL.background_image[roi_mask]
neg_bg = roi_bg[roi_bg < 0]
print({
    'roi_bg_min': float(roi_bg.min()),
    'roi_bg_max': float(roi_bg.max()),
    'neg_fraction': float(neg_bg.size / roi_bg.size),
    'neg_min': float(neg_bg.min()),
    'neg_max': float(neg_bg.max()),
})
```
Output:
```
{'roi_bg_min': -0.4896034835461235, 'roi_bg_max': 12.975452507699648, 'neg_fraction': 0.006793478260869565, 'neg_min': -0.4896034835461235, 'neg_max': -0.007444087472769145}
```

Findings: Sentinel mask aligns exactly with the complement of ROI coverage (0 overlap). Small negative background values occur inside ROIs but are > -1, so `(background >= 0)` loss mask remains the correct inclusion filter.

## Planning Decisions
- Add explicit sentinel integrity guard inside `prepare_refinement_inputs` (raises when sentinel values deviate from -1) to prevent silent regressions.
- Acceptance tests will materialize ROI union from bbox/pids and assert complementarity with sentinel mask, capturing metrics in JSON for artifact parity.
- Artifact plan includes `sentinel_metrics.json` summarizing coverage fractions and mismatch counts to feed future diagnostics.

## Next Loop Expectations
- Move to implementation loop executing Do Now with production guard + new DB_AT_022 test module and mapped pytest selectors.
- Documented commands and artifacts will satisfy TESTING-003 once tests land.

