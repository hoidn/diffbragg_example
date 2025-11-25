# TOOLING-VIS-001 Loop Summary — 2025-11-25T190500Z

## Problem Statement

**Quoted SPEC lines (docs/spec-db-vis.md:41-47)**:
> For visuals that claim DB-AT-024 mapping parity (e.g., TOOLING-VIS-001 Stage-A ROI triptychs), the "before" model SHALL come from the mapping-aligned configuration defined in `spec-db-workflow.md` (Canon. Initial Configuration) and enforced by DB-AT-027: same geometry/masks/sigma/HKL/calibration as DB-AT-024, and zero geometry deltas/baseline scale reproduce the mapping Bragg tensor within tolerance.

**Requirement**: Capture raw vs calibrated ROI evidence inside the dataset-comparison probe so we can quantify how calibration alters Stage A inputs before re-running the failing smoke selectors.

## Key Finding

Raw case (no calibration) achieves BETTER correlation (0.047) than calibrated cases (-0.044), confirming the calibration bug is making things worse rather than fixing a zero-point mismatch. The pathologically large spot_scale_override (~3e+17 vs expected O(1e2)) in calibrated cases is the smoking gun.

## Metrics

**scaled_raw** (no calibration): roi_cc_median=0.047, spot_scale_override=1.0, bragg_mean=0.01 ADU
**scaled_calibrated**: roi_cc_median=-0.044, spot_scale_override=3.1e+17, bragg_mean=1.43 ADU
**refined_calibrated**: roi_cc_median=-0.044, spot_scale_override=3.2e+17, bragg_mean=1.01 ADU

pytest DB-AT-028: chi²/pixel initial=2.098e+05 (spec ≤1e2, ~1000× violation)
pytest DB-AT-029: negative median correlation (spec ≥0.2)

## Artifacts

All under plans/active/TOOLING-VIS-001/reports/2025-11-25T190500Z/:
- mapping_dataset_metrics/ (probe.log, JSON, 48 PNG/NPZ ROI artifacts)
- db_at_028/, db_at_029/ (pytest logs, metrics JSONs)

### Turn Summary
Extended dataset comparison probe to emit raw vs calibrated ROI artifacts (PNG/NPZ); raw case (no calibration) achieved better correlation (0.047) than calibrated cases (-0.044), confirming calibration bug is making things worse not better.
Probe captured 48 ROI artifacts (16 per case) under mapping_dataset_metrics/ subdirs; pytest DB-AT-028/029 failed as expected (chi²/pixel ~1e5, negative correlations) but artifacts persisted per Hard Gate.
Next: audit calibration loading path to trace spot_scale_override=3.1e+17 derivation and identify missing unit conversion or structural mismatch.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T190500Z/mapping_dataset_metrics/ (probe.log, JSON, 48 PNG/NPZ), db_at_028/, db_at_029/ (pytest logs, metrics JSONs)
