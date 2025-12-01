# refGeom_small fixture

This directory stores the cropped refGeom assets used by DBEX Stage A/B/C smoke tests.

## Generation Command
```bash
plans/active/PERF-SMOKE-DETSIZE/bin/crop_refgeom_to_small.py --expt refGeom.expt --refl refGeom.refl --cbf lys_nitr_10_6_0001.cbf --mask 747_mask.pkl --fast-start 751 --slow-start 719 --width 1024 --height 1024 --output-root sp.proc/refGeom_small --report plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/refGeom_small_crop_report.json --background-pad 3
```

## Cropping Window
- Fast pixels: [751, 1775)
- Slow pixels: [719, 1743)
- Output detector: 1024 (fast) × 1024 (slow)
- Background margin enforced: 3 px

## ROI Statistics
- Experiment id retained: 0
- Reflections kept: 29 / 92 (31.5%)
- Fast span (post-crop bbox): [74, 984]
- Slow span (post-crop bbox): [20, 950]
- ROI pixel coverage (sum of bbox areas): 1158

## Artifacts
- refGeom_small.expt
- refGeom_small.refl
- refGeom_small_mask.pkl
- lys_nitr_10_6_0001_small.cbf
- Crop report: plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/refGeom_small_crop_report.json