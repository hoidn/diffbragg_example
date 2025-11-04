# DB-AT-020 Planning Notes — 2025-11-04T042625Z

## Problem Statement
DB_AT_020 (reflection ingestion sanity) remains a planned selector in `docs/TESTING_GUIDE.md:66` / `docs/development/TEST_SUITE_INDEX.md:22`. We need a pytest harness that validates DIALS bbox semantics and panel ordering using the canonical refGeom assets so downstream parity tests can rely on trustworthy ROI slicing.

## Evidence Review
- `docs/spec-db-conformance.md:24-32` — Defines DB_AT_020 setup (load .expt/.refl, slice first ROI) and expectations for bbox exclusivity + panel alignment.
- `docs/spec-db-core.md:20-26` — States bbox contract `(x0, x1, y0, y1)` with exclusive upper bounds; slicing as `img[pid, y0:y1, x0:x1]`.
- `docs/dials_api.md:1-32` — Details reflection table `panel` column, bbox exclusivity, and slicing rules consistent with simtbx helpers.
- `docs/architecture.md:122` — Runtime guard requiring ROI bbox bounds checks and panel index consistency across reflections/images/masks.
- `dbex/data_load.py:8-83` — Current ingestion logic leveraging `simtbx.diffBragg.utils.get_roi_background_and_selection_flags`, providing `bbox`, `pids`, `background_image`, and raw image data.

## One-off analysis (T1 — DataLoad probe)
```bash
python - <<'PY'
from argparse import Namespace
from pathlib import Path
from dbex.data_load import DataLoad
repo_root = Path.cwd()
args = Namespace(
    mtzFile=str(repo_root / 'scaled.mtz'),
    mtzCol='F,SIGF',
    exptName=str(repo_root / 'refGeom.expt'),
    exptIdx=0,
    reflName=str(repo_root / 'refGeom.refl')
)
dl = DataLoad(args)
print('panels', len(dl.data))
print('bbox_count', len(dl.bbox))
print('bbox_sample', dl.bbox[0])
print('pid_sample', dl.pids[0])
print('slice_shape', dl.data[dl.pids[0]][dl.bbox[0][2]:dl.bbox[0][3], dl.bbox[0][0]:dl.bbox[0][1]].shape)
print('bbox_deltas', (dl.bbox[0][1]-dl.bbox[0][0], dl.bbox[0][3]-dl.bbox[0][2]))
print('bbox_max_fast', max(b[1] for b in dl.bbox))
print('panel_fast_dim', dl.data[dl.pids[0]].shape[1])
print('bbox_min', min(min(b) for b in dl.bbox))
print('pid_range', (int(min(dl.pids)), int(max(dl.pids))))
PY
```
```
panels 1
bbox_count 92
bbox_sample (582, 594, 0, 12)
pid_sample 0
slice_shape (12, 12)
bbox_deltas (12, 12)
bbox_max_fast 2377
panel_fast_dim 2463
bbox_min 0
pid_range (0, 0)
```

## Next Steps
- Follow implementation plan Phases A-C under `plans/active/DB-AT-020/implementation.md`, beginning with dataset/spec validation (A1-A3) and authoring the DB_AT_020 pytest module (B1-B3).
- Capture pytest and collect-only logs plus documentation updates once the harness is implemented.
