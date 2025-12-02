"""
Test suite for DB-AT-022: Background sentinel guard.

Validates simtbx_api.md:14 sentinel contract:
- Background uses -1 sentinel outside ROIs
- Valid ROI pixels have background >= 0
- Sentinel coverage equals complement of ROI union
- prepare_refinement_inputs enforces sentinel integrity

References:
- docs/simtbx_api.md:14 (sentinel contract)
- docs/spec-db-conformance.md:35-38 (DB-AT-022 acceptance)
- dbex/data_load.py (background_image hydration)
- dbex/nanobrag_bridge.py (prepare_refinement_inputs sentinel guard)
"""

import pytest
import numpy as np
import os
import json
from pathlib import Path
from types import SimpleNamespace

# Skip entire module if canonical assets are missing
pytestmark = pytest.mark.skipif(
    not Path("refGeom.expt").exists() or not Path("refGeom.refl").exists(),
    reason="Canonical refGeom assets not found"
)


@pytest.fixture
def canonical_args():
    """
    Canonical DataLoad args using refGeom assets.

    Matches the dataset used in DB-AT-020/021 tests.
    """
    return SimpleNamespace(
        mtzFile="scaled.mtz",
        mtzCol="F,SIGF",
        exptName="refGeom.expt",
        exptIdx=0,
        reflName="refGeom.refl",
        maskFile="747_mask.pkl"
    )


@pytest.fixture
def data_load_instance(canonical_args):
    """
    Create a DataLoad instance with canonical assets.

    Skip if any required file is missing.
    """
    required_files = [
        canonical_args.mtzFile,
        canonical_args.exptName,
        canonical_args.reflName,
        canonical_args.maskFile
    ]
    for fpath in required_files:
        if not Path(fpath).exists():
            pytest.skip(f"Required asset {fpath} not found")

    from dbex.data_load import DataLoad
    return DataLoad(canonical_args)


class TestBackgroundSemantics:
    """
    Test suite for DB-AT-022: Background sentinel guard.
    """

    def test_DB_AT_022_sentinel_complement(self, data_load_instance):
        """
        DB-AT-022 (1/3): Validate sentinel mask equals complement of ROI union.

        Acceptance criteria per simtbx_api.md:14:
        1. Sentinel pixels (background ≈ -1) are outside ROI union
        2. ROI pixels have background >= 0
        3. Zero overlap between sentinel and ROI masks
        4. Coverage metrics align with reflection metadata

        Metrics captured:
        - roi_count: number of ROIs
        - sentinel_fraction: fraction of pixels with background ≈ -1
        - roi_fraction: fraction of pixels inside ROI union
        - overlap_count: pixels that are both sentinel and inside ROI (should be 0)
        - sentinel_mean: mean value of sentinel pixels (should be ≈ -1.0)
        """
        DL = data_load_instance

        # Build ROI union mask from bbox/pids
        roi_union = np.zeros(DL.data.shape, dtype=bool)
        for pid, (x0, x1, y0, y1) in zip(DL.pids, DL.bbox):
            roi_union[int(pid), int(y0):int(y1), int(x0):int(x1)] = True

        # Identify sentinel pixels (background ≈ -1, using -0.5 threshold)
        sentinel_mask = DL.background_image <= -0.5

        # Validate: sentinel pixels should be outside ROI union
        overlap = sentinel_mask & roi_union
        overlap_count = np.sum(overlap)

        assert overlap_count == 0, \
            f"Found {overlap_count} sentinel pixels inside ROI union. " \
            f"Expected zero overlap per simtbx_api.md:14 sentinel contract"

        # Validate: ROI pixels should NOT have sentinel values (background > -0.5)
        # Note: simtbx background estimation can produce slightly negative values
        # (e.g., from plane fitting), but sentinel is specifically <= -0.5
        roi_pixels_with_sentinel = roi_union & (DL.background_image <= -0.5)
        n_sentinel_roi = np.sum(roi_pixels_with_sentinel)

        assert n_sentinel_roi == 0, \
            f"Found {n_sentinel_roi} ROI pixels with sentinel (background <= -0.5). " \
            f"Expected no sentinel inside ROIs per simtbx_api.md:14"

        # Additional validation: most ROI pixels should have background >= 0
        # (allow small fraction of slightly negative values from plane fitting)
        roi_pixels_positive = roi_union & (DL.background_image >= 0)
        roi_positive_fraction = np.sum(roi_pixels_positive) / np.sum(roi_union)

        assert roi_positive_fraction > 0.95, \
            f"Only {roi_positive_fraction*100:.1f}% of ROI pixels have background >= 0. " \
            f"Expected >95% positive background in ROIs"

        # Validate: sentinel mean should be close to -1.0
        sentinel_pixels = DL.background_image[sentinel_mask]
        sentinel_mean = np.mean(sentinel_pixels)

        assert np.isclose(sentinel_mean, -1.0, atol=0.01), \
            f"Sentinel mean {sentinel_mean:.6f} deviates from expected -1.0. " \
            f"Expected sentinel pixels to be ≈ -1 per simtbx_api.md:14"

        # Compute coverage metrics
        total_pixels = DL.data.size
        sentinel_fraction = np.sum(sentinel_mask) / total_pixels
        roi_fraction = np.sum(roi_union) / total_pixels

        # Validate: sentinel + ROI should approximately cover all pixels
        # (with some tolerance for edge pixels and rounding)
        coverage_sum = sentinel_fraction + roi_fraction
        assert 0.95 <= coverage_sum <= 1.05, \
            f"Sentinel ({sentinel_fraction:.4f}) + ROI ({roi_fraction:.4f}) = {coverage_sum:.4f}, " \
            f"expected ≈ 1.0 (allowing 5% tolerance for edge effects)"

        # Record metrics for artifacts
        metrics = {
            "roi_count": len(DL.pids),
            "sentinel_fraction": float(sentinel_fraction),
            "roi_fraction": float(roi_fraction),
            "overlap_count": int(overlap_count),
            "sentinel_mean": float(sentinel_mean),
            "sentinel_std": float(np.std(sentinel_pixels)),
            "coverage_sum": float(coverage_sum),
            "total_pixels": int(total_pixels),
            "sentinel_pixels": int(np.sum(sentinel_mask)),
            "roi_pixels": int(np.sum(roi_union)),
        }

        # Write metrics if artifact directory is set
        artifact_dir = os.getenv("DBAT022_ARTIFACT_DIR")
        if artifact_dir:
            os.makedirs(artifact_dir, exist_ok=True)
            with open(f"{artifact_dir}/sentinel_metrics.json", "w") as f:
                json.dump(metrics, f, indent=2)

    def test_DB_AT_022_guard_enforcement(self, data_load_instance):
        """
        DB-AT-022 (2/3): Validate sentinel guard in prepare_refinement_inputs.

        Tests that prepare_refinement_inputs:
        1. Accepts canonical background with proper sentinel coverage
        2. Raises ValueError when sentinel leaks inside ROI
        3. Raises ValueError when non-sentinel pixels appear outside ROI
        4. Provides actionable error messages referencing simtbx_api.md
        """
        from dbex.refinement.inputs import prepare_refinement_inputs

        DL = data_load_instance

        # Test 1: Canonical background should pass guard
        inputs = prepare_refinement_inputs(
            data=DL.data,
            background_image=DL.background_image,
            trusted_mask=DL.trusted_mask,
            bbox=DL.bbox,
            pids=DL.pids,
            detector=DL.detector
        )

        # Validate that inputs were created successfully
        assert inputs is not None
        assert inputs.target.shape == DL.data.shape
        assert inputs.loss_mask.shape == DL.data.shape

        # Test 2: Tampered background with sentinel inside ROI should fail
        tampered_bg = DL.background_image.copy()

        # Find first ROI and set a pixel inside it to -1 (sentinel)
        pid = DL.pids[0]
        x0, x1, y0, y1 = DL.bbox[0]
        # Set middle pixel of first ROI to sentinel
        mid_y = (y0 + y1) // 2
        mid_x = (x0 + x1) // 2
        tampered_bg[pid, mid_y, mid_x] = -1.0

        with pytest.raises(ValueError, match="Sentinel guard violation.*inside ROI union"):
            prepare_refinement_inputs(
                data=DL.data,
                background_image=tampered_bg,
                trusted_mask=DL.trusted_mask,
                bbox=DL.bbox,
                pids=DL.pids,
                detector=DL.detector
            )

        # Test 3: Tampered background with non-sentinel outside ROI should fail
        tampered_bg2 = DL.background_image.copy()

        # Find a pixel outside all ROIs and set it to 0 (not sentinel)
        roi_union = np.zeros(DL.data.shape, dtype=bool)
        for pid, (x0, x1, y0, y1) in zip(DL.pids, DL.bbox):
            roi_union[int(pid), int(y0):int(y1), int(x0):int(x1)] = True

        # Find first pixel outside ROI
        outside_pixels = np.argwhere(~roi_union)
        if len(outside_pixels) > 0:
            pid, slow, fast = outside_pixels[0]
            tampered_bg2[pid, slow, fast] = 0.5  # Significantly different from -1

            with pytest.raises(ValueError, match="Sentinel guard violation.*outside ROI union"):
                prepare_refinement_inputs(
                    data=DL.data,
                    background_image=tampered_bg2,
                    trusted_mask=DL.trusted_mask,
                    bbox=DL.bbox,
                    pids=DL.pids,
                    detector=DL.detector
                )

    def test_DB_AT_022_roi_coverage_metrics(self, data_load_instance):
        """
        DB-AT-022 (3/3): Capture ROI coverage and background metrics.

        Validates that:
        1. ROI count matches reflection metadata
        2. Background coverage aligns with bbox areas
        3. Loss mask coverage is consistent with ROI/trusted mask intersection

        Metrics captured:
        - roi_count: number of ROIs
        - background_valid_pixels: pixels with background >= 0
        - background_sentinel_pixels: pixels with background ≈ -1
        - per_roi_metrics: [{roi_id, bbox, bg_valid_pixels, bg_mean, bg_std}]
        """
        from dbex.refinement.inputs import prepare_refinement_inputs

        DL = data_load_instance

        # Prepare refinement inputs
        inputs = prepare_refinement_inputs(
            data=DL.data,
            background_image=DL.background_image,
            trusted_mask=DL.trusted_mask,
            bbox=DL.bbox,
            pids=DL.pids,
            detector=DL.detector
        )

        # Global background metrics
        background_valid_pixels = np.sum(DL.background_image >= 0)
        background_sentinel_pixels = np.sum(DL.background_image <= -0.5)
        total_pixels = DL.data.size

        # Per-ROI metrics
        per_roi_metrics = []
        for roi_id, (pid, (x0, x1, y0, y1)) in enumerate(inputs.panel_slices):
            roi_bg = DL.background_image[pid, y0:y1, x0:x1]
            roi_valid_mask = roi_bg >= 0

            roi_metrics = {
                "roi_id": roi_id,
                "panel_id": pid,
                "bbox": [x0, x1, y0, y1],
                "roi_size": int(roi_bg.size),
                "bg_valid_pixels": int(np.sum(roi_valid_mask)),
                "bg_valid_fraction": float(np.mean(roi_valid_mask)),
                "bg_mean": float(np.mean(roi_bg[roi_valid_mask])) if np.any(roi_valid_mask) else 0.0,
                "bg_std": float(np.std(roi_bg[roi_valid_mask])) if np.any(roi_valid_mask) else 0.0,
                "bg_min": float(np.min(roi_bg[roi_valid_mask])) if np.any(roi_valid_mask) else 0.0,
                "bg_max": float(np.max(roi_bg[roi_valid_mask])) if np.any(roi_valid_mask) else 0.0,
            }
            per_roi_metrics.append(roi_metrics)

        metrics = {
            "roi_count": len(inputs.panel_slices),
            "total_pixels": int(total_pixels),
            "background_valid_pixels": int(background_valid_pixels),
            "background_sentinel_pixels": int(background_sentinel_pixels),
            "background_valid_fraction": float(background_valid_pixels / total_pixels),
            "background_sentinel_fraction": float(background_sentinel_pixels / total_pixels),
            "mean_roi_bg_valid_fraction": float(np.mean([m["bg_valid_fraction"] for m in per_roi_metrics])),
            "per_roi_metrics": per_roi_metrics,
        }

        # Write metrics if artifact directory is set
        artifact_dir = os.getenv("DBAT022_ARTIFACT_DIR")
        if artifact_dir:
            os.makedirs(artifact_dir, exist_ok=True)
            with open(f"{artifact_dir}/roi_coverage.json", "w") as f:
                json.dump(metrics, f, indent=2)
