"""
Test suite for DB-AT-021: Mask semantics guard.

Validates spec-db-core.md:29-55 contracts:
- DIALS trusted mask polarity (True=include)
- Shape alignment with data/background arrays [panel, slow, fast]
- Loss mask consistency: (background >= 0) & trusted_mask
- Target zeroing outside loss mask regions

References:
- docs/spec-db-core.md:29-55 (mask contracts)
- docs/spec-db-conformance.md:31-34 (DB-AT-021 acceptance)
- dbex/data_load.py (trusted_mask hydration)
- dbex/nanobrag_bridge.py (prepare_refinement_inputs)
"""

import pytest
import numpy as np
import os
import json
from pathlib import Path
from types import SimpleNamespace

# Skip entire module if canonical mask file is missing
pytestmark = pytest.mark.skipif(
    not Path("747_mask.pkl").exists(),
    reason="Canonical mask file 747_mask.pkl not found"
)


@pytest.fixture
def canonical_args():
    """
    Canonical DataLoad args using refGeom assets.

    Matches the dataset used in DB-AT-020 reflection ingestion tests.
    """
    return SimpleNamespace(
        mtzFile="scaled.mtz",
        mtzCol="F,SIGF",  # Canonical column per test_reflection_ingestion.py:60
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


class TestMaskSemantics:
    """
    Test suite for DB-AT-021: Mask semantics guard.
    """

    def test_DB_AT_021_trusted_mask_shape_and_polarity(self, data_load_instance):
        """
        DB-AT-021 (1/2): Validate trusted mask shape, dtype, and polarity.

        Acceptance criteria per spec-db-core.md:29-55:
        1. trusted_mask dtype is bool
        2. Shape matches data/background: [panel, slow, fast]
        3. Polarity guard: >50% True (include semantics)
        4. Shape alignment with data.shape and background_image.shape

        Metrics captured:
        - trusted_fraction: fraction of True pixels
        - shape: mask array shape
        - dtype: mask array dtype
        """
        DL = data_load_instance

        # Assert trusted_mask exists and is a numpy array
        assert hasattr(DL, 'trusted_mask'), "DataLoad missing trusted_mask attribute"
        assert isinstance(DL.trusted_mask, np.ndarray), \
            f"trusted_mask should be np.ndarray, got {type(DL.trusted_mask)}"

        # Validate dtype (bool)
        assert DL.trusted_mask.dtype == bool, \
            f"trusted_mask dtype should be bool, got {DL.trusted_mask.dtype}"

        # Validate shape alignment with data/background
        assert DL.trusted_mask.shape == DL.data.shape, \
            f"Mask shape {DL.trusted_mask.shape} != data shape {DL.data.shape}"
        assert DL.trusted_mask.shape == DL.background_image.shape, \
            f"Mask shape {DL.trusted_mask.shape} != background shape {DL.background_image.shape}"

        # Validate polarity: True should be majority (>50% coverage)
        # Per spec-db-core.md:29, DIALS trusted mask uses True=include
        trusted_fraction = np.mean(DL.trusted_mask)
        assert trusted_fraction > 0.5, \
            f"Mask polarity check failed: only {trusted_fraction*100:.1f}% True. " \
            f"Expected >50% for True=include semantics (spec-db-core.md:29)"

        # Optional: validate shape is [panel, slow, fast] format
        # For single-panel detectors, shape should be (1, slow, fast)
        assert DL.trusted_mask.ndim == 3, \
            f"Expected 3D mask [panel, slow, fast], got shape {DL.trusted_mask.shape}"

        # Record metrics for artifacts
        metrics = {
            "trusted_fraction": float(trusted_fraction),
            "shape": list(DL.trusted_mask.shape),
            "dtype": str(DL.trusted_mask.dtype),
            "n_panels": DL.trusted_mask.shape[0],
            "n_trusted": int(np.sum(DL.trusted_mask)),
            "n_total": int(DL.trusted_mask.size),
        }

        # Write metrics if artifact directory is set
        artifact_dir = os.getenv("DBAT021_ARTIFACT_DIR")
        if artifact_dir:
            os.makedirs(artifact_dir, exist_ok=True)
            with open(f"{artifact_dir}/mask_shape_polarity_metrics.json", "w") as f:
                json.dump(metrics, f, indent=2)

    def test_DB_AT_021_loss_mask_consistency(self, data_load_instance):
        """
        DB-AT-021 (2/2): Validate loss mask consistency via prepare_refinement_inputs.

        Acceptance criteria per spec-db-core.md:55:
        1. Loss mask equals (background >= 0) & trusted_mask
        2. Target pixels outside loss_mask are zeroed
        3. Loss mask coverage metrics align with ROI geometry

        Metrics captured:
        - roi_count: number of ROIs processed
        - trusted_fraction: global trusted mask coverage
        - loss_mask_fraction: global loss mask coverage
        - background_valid_fraction: fraction where background >= 0
        - per_roi_metrics: list of {roi_id, loss_coverage, target_nonzero}
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

        # Validate loss_mask equals (background >= 0) & trusted_mask
        expected_loss_mask = (DL.background_image >= 0) & DL.trusted_mask
        np.testing.assert_array_equal(
            inputs.loss_mask,
            expected_loss_mask,
            err_msg="Loss mask should equal (background >= 0) & trusted_mask per spec-db-core.md:55"
        )

        # Validate target zeroing: all pixels where loss_mask is False should be zero
        invalid_pixels = ~inputs.loss_mask
        target_at_invalid = inputs.target[invalid_pixels]
        assert np.all(target_at_invalid == 0), \
            f"Target should be zeroed outside loss_mask, found {np.sum(target_at_invalid != 0)} nonzero invalid pixels"

        # Validate target non-zero only where loss_mask is True (allow for background subtraction artifacts)
        # Note: Due to background subtraction, valid pixels MAY have zero/negative values
        # So we check the converse: all nonzero pixels must be in the loss mask
        nonzero_mask = inputs.target != 0
        nonzero_outside_loss = nonzero_mask & ~inputs.loss_mask
        assert not np.any(nonzero_outside_loss), \
            f"Found {np.sum(nonzero_outside_loss)} nonzero target pixels outside loss_mask"

        # Collect global metrics
        trusted_fraction = np.mean(DL.trusted_mask)
        loss_mask_fraction = np.mean(inputs.loss_mask)
        background_valid_fraction = np.mean(DL.background_image >= 0)

        # Collect per-ROI metrics
        per_roi_metrics = []
        for roi_id, (pid, (x0, x1, y0, y1)) in enumerate(inputs.panel_slices):
            roi_loss_mask = inputs.loss_mask[pid, y0:y1, x0:x1]
            roi_target = inputs.target[pid, y0:y1, x0:x1]

            roi_metrics = {
                "roi_id": roi_id,
                "panel_id": pid,
                "bbox": [x0, x1, y0, y1],
                "loss_coverage": float(np.mean(roi_loss_mask)),
                "target_nonzero_frac": float(np.mean(roi_target != 0)),
                "roi_pixels": int(roi_loss_mask.size),
                "roi_valid_pixels": int(np.sum(roi_loss_mask)),
            }
            per_roi_metrics.append(roi_metrics)

        metrics = {
            "roi_count": len(inputs.panel_slices),
            "trusted_fraction": float(trusted_fraction),
            "loss_mask_fraction": float(loss_mask_fraction),
            "background_valid_fraction": float(background_valid_fraction),
            "n_rois": len(per_roi_metrics),
            "mean_roi_loss_coverage": float(np.mean([m["loss_coverage"] for m in per_roi_metrics])),
            "per_roi_metrics": per_roi_metrics,
        }

        # Write metrics if artifact directory is set
        artifact_dir = os.getenv("DBAT021_ARTIFACT_DIR")
        if artifact_dir:
            os.makedirs(artifact_dir, exist_ok=True)
            with open(f"{artifact_dir}/mask_metrics.json", "w") as f:
                json.dump(metrics, f, indent=2)

    def test_DB_AT_021_detector_beam_crystal_fixtures(self, data_load_instance):
        """
        DB-AT-021 (bonus): Validate DataLoad exposes detector/beam/crystal fixtures.

        These attributes are required by prepare_refinement_inputs and bridge code.
        """
        DL = data_load_instance

        # Validate detector fixture
        assert hasattr(DL, 'detector'), "DataLoad missing detector attribute"
        assert DL.detector is not None, "detector should not be None"
        # Basic duck-type check: should have panels
        assert len(DL.detector) > 0, "detector should have at least one panel"

        # Validate beam fixture
        assert hasattr(DL, 'beam'), "DataLoad missing beam attribute"
        assert DL.beam is not None, "beam should not be None"

        # Validate crystal fixture
        assert hasattr(DL, 'crystal'), "DataLoad missing crystal attribute"
        assert DL.crystal is not None, "crystal should not be None"
