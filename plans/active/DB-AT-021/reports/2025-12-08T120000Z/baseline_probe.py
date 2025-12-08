#!/usr/bin/env python3
"""DB-AT-021 Phase A3 Baseline Probe: DataLoad Mask Metrics

Thin wrapper probe (<100 LOC) calling DataLoad API directly to establish
baseline metrics for trusted_mask, loss_mask construction, and ROI intersection.

Per input.md A3 deliverable requirements.
"""
import numpy as np
from pathlib import Path
from argparse import Namespace

# Determine repo root - hardcode to ensure correctness
import sys
repo_root = Path("/home/ollie/Documents/diffbragg_example_2/diffbragg_example")
sys.path.insert(0, str(repo_root))

from dbex.data_load import DataLoad

# Build DataLoad args (per conftest.py pattern) with absolute paths
args = Namespace(
    exptName=str(repo_root / "refGeom.expt"),
    reflName=str(repo_root / "refGeom.refl"),
    mtzFile=str(repo_root / "scaled.mtz"),
    mtzCol="I(+),SIGI(+),I(-),SIGI(-)",
    exptIdx=0,
    maskFile=str(repo_root / "747_mask.pkl"),
    sigma_map=None,
    config_path=None,
    calibration_config_path=None,
)

# Load canonical assets (per DB-AT-SUITE-CARE-001 Phase B.2 validation)
dl = DataLoad(args)

# Metric 1: trusted_mask shape and dtype
trusted_mask_shape = dl.trusted_mask.shape
trusted_mask_dtype = str(dl.trusted_mask.dtype)
trusted_pixel_count = int(np.sum(dl.trusted_mask))
untrusted_pixel_count = int(np.sum(~dl.trusted_mask))

# Metric 2: loss_mask construction validation (per spec-db-core.md:124)
# Formula: loss_mask = (background >= 0) & trusted_mask
loss_mask_computed = (dl.background_image >= 0) & dl.trusted_mask
loss_mask_pixel_count = int(np.sum(loss_mask_computed))

# Metric 3: Sample ROI intersection (ROI 0)
if len(dl.pids) > 0:
    roi_idx = 0
    pid = dl.pids[roi_idx]
    bbox = dl.bbox[roi_idx]
    x0, x1, y0, y1 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

    # Slice ROI from trusted_mask
    roi_trusted_mask = dl.trusted_mask[pid, y0:y1, x0:x1]
    sample_roi_trusted_pixels = int(np.sum(roi_trusted_mask))

    # Slice ROI from loss_mask
    roi_loss_mask = loss_mask_computed[pid, y0:y1, x0:x1]
    sample_roi_loss_mask_pixels = int(np.sum(roi_loss_mask))

    # ROI background validity (sentinel check)
    roi_background = dl.background_image[pid, y0:y1, x0:x1]
    sample_roi_background_valid_pixels = int(np.sum(roi_background >= 0))
    sample_roi_background_sentinel_pixels = int(np.sum(roi_background == -1))
else:
    sample_roi_trusted_pixels = "N/A (no ROIs)"
    sample_roi_loss_mask_pixels = "N/A (no ROIs)"
    sample_roi_background_valid_pixels = "N/A (no ROIs)"
    sample_roi_background_sentinel_pixels = "N/A (no ROIs)"

# Collect metrics
metrics = {
    "trusted_mask_shape": trusted_mask_shape,
    "trusted_mask_dtype": trusted_mask_dtype,
    "trusted_pixel_count": trusted_pixel_count,
    "untrusted_pixel_count": untrusted_pixel_count,
    "loss_mask_construction_formula": "(background >= 0) & trusted_mask",
    "loss_mask_pixel_count": loss_mask_pixel_count,
    "sample_roi_index": 0 if len(dl.pids) > 0 else "N/A",
    "sample_roi_bbox": (x0, x1, y0, y1) if len(dl.pids) > 0 else "N/A",
    "sample_roi_trusted_pixels": sample_roi_trusted_pixels,
    "sample_roi_loss_mask_pixels": sample_roi_loss_mask_pixels,
    "sample_roi_background_valid_pixels": sample_roi_background_valid_pixels,
    "sample_roi_background_sentinel_pixels": sample_roi_background_sentinel_pixels,
}

# Write to baseline_probe.md
output_path = Path("plans/active/DB-AT-021/reports/2025-12-08T120000Z/baseline_probe.md")
with open(output_path, "w") as f:
    f.write("# DB-AT-021 Phase A3 Baseline Probe\n\n")
    f.write("**Objective**: Establish baseline metrics for DataLoad mask handling\n\n")
    f.write("**Assets**: refGeom.expt, refGeom.refl, scaled.mtz, 747_mask.pkl (canonical per DB-AT-SUITE-CARE-001 Phase B.2)\n\n")
    f.write("---\n\n")
    f.write("## Metrics\n\n")
    for k, v in metrics.items():
        f.write(f"- **{k}**: {v}\n")
    f.write("\n---\n\n")
    f.write("## Validation\n\n")
    f.write("**trusted_mask polarity**: DIALS convention (True=trusted)\n")
    f.write(f"- Verified dtype: {trusted_mask_dtype} (expected: bool)\n\n")
    f.write("**loss_mask construction**: Per spec-db-core.md:124\n")
    f.write("- Formula: `(background >= 0) & trusted_mask`\n")
    f.write(f"- Computed pixels: {loss_mask_pixel_count}\n")
    f.write(f"- Expected: trusted pixels ({trusted_pixel_count}) intersected with background-valid pixels\n\n")
    f.write("**Background sentinel**: -1 outside ROIs (per spec-db-core.md, architecture.md ADR-07)\n")
    if len(dl.pids) > 0:
        f.write(f"- Sample ROI 0: {sample_roi_background_valid_pixels} valid, {sample_roi_background_sentinel_pixels} sentinel\n\n")
    else:
        f.write("- No ROIs in dataset\n\n")
    f.write("**Status**: ✅ Baseline metrics captured\n")

print(f"Baseline probe complete. Metrics written to {output_path}")
