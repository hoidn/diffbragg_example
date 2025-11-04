# DB-AT-023 Planning Summary — 2025-11-04T052222Z

## Focus & Sources
- Guard calibration pipeline per `docs/spec-db-workflow.md:21-28` (photon conversion when `--adu-per-photon` provided, ADU + global scale otherwise).
- Align with architectural pitfall ADR-02 in `docs/architecture.md:175-194` (never mix ADU and photon representations within a run).
- Cross-check unit expectations from `docs/config_crosswalk.md:96-112` (target defaults to ADU; photon conversion optional).

## One-off analysis (T1 — calibration probe)
Python command:
```bash
python - <<'PY'
from types import SimpleNamespace
from dbex.data_load import DataLoad
args = SimpleNamespace(
    mtzFile="scaled.mtz",
    mtzCol="F,SIGF",
    exptName="refGeom.expt",
    exptIdx=0,
    reflName="refGeom.refl",
    maskFile="747_mask.pkl"
)
DL = DataLoad(args)
import numpy as np
import json
metrics = {
    "data_mean": float(DL.data.mean()),
    "data_std": float(DL.data.std()),
    "background_mean_roi": float(DL.background_image[DL.background_image >= 0].mean()),
    "background_std_roi": float(DL.background_image[DL.background_image >= 0].std()),
    "roi_count": int(len(DL.pids)),
    "adu_sample_roi_sum": float(np.sum(DL.data[DL.pids[0], DL.bbox[0][2]:DL.bbox[0][3], DL.bbox[0][0]:DL.bbox[0][1]])),
    "background_sample_roi_sum": float(np.sum(DL.background_image[DL.pids[0], DL.bbox[0][2]:DL.bbox[0][3], DL.bbox[0][0]:DL.bbox[0][1]]))
}
print(json.dumps(metrics, indent=2))
PY
```

Output:
```json
{
  "data_mean": 1.2643682094524085,
  "data_std": 48.93890326634683,
  "background_mean_roi": 2.9689304257089026,
  "background_std_roi": 2.2139766616978247,
  "roi_count": 92,
  "adu_sample_roi_sum": 279.0,
  "background_sample_roi_sum": 207.2187624320689
}
```

## Observations
- Canonical dataset remains ADU-valued with positive ROI background, confirming need for explicit conversion hook rather than assuming photon units.
- ROI sums offer baseline to validate `--adu-per-photon` scaling (expect photon-mode target = `(data - background)/adu_per_photon`).
- No existing code path surfaces representation metadata, so acceptance tests must cover both conversion correctness and guard messaging for invalid factors.
