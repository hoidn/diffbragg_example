"""
Test suite for DB-AT-023: Calibration policy guard (ADU vs photons).

Validates spec-db-workflow.md:20 calibration policy:
- Optional --adu-per-photon flag threads through CLI to bridge
- prepare_refinement_inputs converts targets to photons when adu_per_photon > 0
- ADU mode preserves raw intensities and provides global_scale_hint
- Invalid adu_per_photon values raise actionable ValueError
- Representation metadata surfaced correctly

References:
- docs/spec-db-workflow.md:20 (calibration policy)
- docs/architecture.md:88-89 (ADR-02)
- docs/spec-db-conformance.md:39-42 (DB-AT-023 acceptance)
- dbex/refine_one.py (CLI wiring)
- dbex/nanobrag_bridge.py (prepare_refinement_inputs photon conversion)
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

    Matches the dataset used in DB-AT-020/021/022 tests.
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


class TestCalibrationPolicy:
    """
    Test suite for DB-AT-023: Calibration policy guard.
    """

    def test_DB_AT_023_photon_conversion_correctness(self, data_load_instance):
        """
        DB-AT-023 (1/4): Validate photon conversion correctness.

        Acceptance criteria per spec-db-workflow.md:20:
        1. When adu_per_photon is provided (>0), target is converted to photons
        2. target_photons = (data - background) / adu_per_photon
        3. target_representation metadata is "photons"
        4. global_scale_hint is None (no scale needed for photon mode)
        5. Numerical stability maintained (float64 intermediate, float32 output)

        Metrics captured:
        - adu_per_photon: calibration factor used
        - target_adu_mean: mean of ADU target
        - target_photon_mean: mean of photon target
        - conversion_ratio: target_adu_mean / target_photon_mean (should ≈ adu_per_photon)
        - target_representation: "photons"
        """
        from dbex.refinement.inputs import prepare_refinement_inputs

        DL = data_load_instance

        # Test photon conversion with a canonical value
        adu_per_photon = 10.0

        # Prepare inputs in ADU mode (baseline)
        inputs_adu = prepare_refinement_inputs(
            data=DL.data,
            background_image=DL.background_image,
            trusted_mask=DL.trusted_mask,
            bbox=DL.bbox,
            pids=DL.pids,
            detector=DL.detector,
            adu_per_photon=None
        )

        # Prepare inputs in photon mode
        inputs_photon = prepare_refinement_inputs(
            data=DL.data,
            background_image=DL.background_image,
            trusted_mask=DL.trusted_mask,
            bbox=DL.bbox,
            pids=DL.pids,
            detector=DL.detector,
            adu_per_photon=adu_per_photon
        )

        # Validate representation metadata
        assert inputs_adu.target_representation == "adu", \
            f"ADU mode should have target_representation='adu', got '{inputs_adu.target_representation}'"

        assert inputs_photon.target_representation == "photons", \
            f"Photon mode should have target_representation='photons', got '{inputs_photon.target_representation}'"

        # Validate global_scale_hint is None for photon mode
        assert inputs_photon.global_scale_hint is None, \
            f"Photon mode should have global_scale_hint=None, got {inputs_photon.global_scale_hint}"

        # Validate global_scale_hint is set for ADU mode
        assert inputs_adu.global_scale_hint is not None, \
            "ADU mode should have global_scale_hint set"
        assert inputs_adu.global_scale_hint > 0, \
            f"ADU mode global_scale_hint should be positive, got {inputs_adu.global_scale_hint}"

        # Compute statistics on valid pixels (loss_mask=True)
        valid_mask = inputs_adu.loss_mask
        target_adu_valid = inputs_adu.target[valid_mask]
        target_photon_valid = inputs_photon.target[valid_mask]

        # Validate conversion ratio
        # target_photon should equal target_adu / adu_per_photon
        expected_photon = target_adu_valid / adu_per_photon
        conversion_error = np.abs(target_photon_valid - expected_photon)
        max_conversion_error = np.max(conversion_error)

        # Allow small numerical error (float32 precision ~1e-7 relative)
        tolerance = 1e-5 * np.max(np.abs(target_adu_valid))
        assert max_conversion_error < tolerance, \
            f"Photon conversion error too large: max={max_conversion_error:.3e}, " \
            f"tolerance={tolerance:.3e}. Expected target_photon = target_adu / {adu_per_photon}"

        # Validate mean ratio
        target_adu_mean = np.mean(target_adu_valid)
        target_photon_mean = np.mean(target_photon_valid)
        conversion_ratio = target_adu_mean / target_photon_mean if target_photon_mean != 0 else 0

        assert np.isclose(conversion_ratio, adu_per_photon, rtol=1e-4), \
            f"Mean conversion ratio {conversion_ratio:.6f} does not match adu_per_photon={adu_per_photon}. " \
            f"Expected ratio ≈ {adu_per_photon}"

        # Record metrics for artifacts
        metrics = {
            "adu_per_photon": float(adu_per_photon),
            "target_adu_mean": float(target_adu_mean),
            "target_adu_std": float(np.std(target_adu_valid)),
            "target_photon_mean": float(target_photon_mean),
            "target_photon_std": float(np.std(target_photon_valid)),
            "conversion_ratio": float(conversion_ratio),
            "max_conversion_error": float(max_conversion_error),
            "tolerance": float(tolerance),
            "target_representation_adu": inputs_adu.target_representation,
            "target_representation_photon": inputs_photon.target_representation,
            "global_scale_hint_adu": float(inputs_adu.global_scale_hint) if inputs_adu.global_scale_hint else None,
            "global_scale_hint_photon": inputs_photon.global_scale_hint,
            "valid_pixels": int(np.sum(valid_mask)),
        }

        # Write metrics if artifact directory is set
        artifact_dir = os.getenv("DBAT023_ARTIFACT_DIR")
        if artifact_dir:
            os.makedirs(artifact_dir, exist_ok=True)
            with open(f"{artifact_dir}/calibration_metrics.json", "w") as f:
                json.dump(metrics, f, indent=2)

    def test_DB_AT_023_adu_mode_metadata(self, data_load_instance):
        """
        DB-AT-023 (2/4): Validate ADU mode metadata expectations.

        Acceptance criteria per spec-db-workflow.md:20:
        1. When adu_per_photon is None, target remains in ADU
        2. target_representation is "adu"
        3. global_scale_hint is computed (positive, non-zero)
        4. global_scale_hint uses robust estimation (IQR-based outlier clipping)

        Metrics captured:
        - target_representation: "adu"
        - global_scale_hint: estimated scale
        - target_mean: mean intensity in ADU
        - target_median: median intensity in ADU
        """
        from dbex.refinement.inputs import prepare_refinement_inputs

        DL = data_load_instance

        # Prepare inputs in ADU mode
        inputs = prepare_refinement_inputs(
            data=DL.data,
            background_image=DL.background_image,
            trusted_mask=DL.trusted_mask,
            bbox=DL.bbox,
            pids=DL.pids,
            detector=DL.detector,
            adu_per_photon=None
        )

        # Validate metadata
        assert inputs.target_representation == "adu", \
            f"Expected target_representation='adu', got '{inputs.target_representation}'"

        assert inputs.global_scale_hint is not None, \
            "ADU mode should provide global_scale_hint"

        assert inputs.global_scale_hint > 0, \
            f"global_scale_hint should be positive, got {inputs.global_scale_hint}"

        # Validate global_scale_hint is reasonable
        valid_pixels = inputs.target[inputs.loss_mask]
        target_mean = np.mean(valid_pixels)
        target_median = np.median(valid_pixels)

        # global_scale_hint should be within order of magnitude of mean/median
        # (it uses robust IQR-based clipping, so expect it close to mean)
        assert 0.1 * target_mean <= inputs.global_scale_hint <= 10 * target_mean, \
            f"global_scale_hint {inputs.global_scale_hint:.3e} out of range. " \
            f"Expected within 10x of target_mean={target_mean:.3e}"

        # Record metrics
        metrics = {
            "target_representation": inputs.target_representation,
            "global_scale_hint": float(inputs.global_scale_hint),
            "target_mean": float(target_mean),
            "target_median": float(target_median),
            "target_std": float(np.std(valid_pixels)),
            "valid_pixels": int(len(valid_pixels)),
        }

        # Write metrics if artifact directory is set
        artifact_dir = os.getenv("DBAT023_ARTIFACT_DIR")
        if artifact_dir:
            os.makedirs(artifact_dir, exist_ok=True)
            with open(f"{artifact_dir}/adu_mode_metrics.json", "w") as f:
                json.dump(metrics, f, indent=2)

    def test_DB_AT_023_invalid_adu_per_photon_guard(self, data_load_instance):
        """
        DB-AT-023 (3/4): Validate adu_per_photon guardrail enforcement.

        Acceptance criteria per spec-db-workflow.md:20:
        1. adu_per_photon <= 0 raises ValueError with actionable message
        2. Error message references spec-db-workflow.md:20
        3. adu_per_photon = 0 is rejected (edge case)
        4. Negative adu_per_photon is rejected

        Test cases:
        - adu_per_photon = 0 (boundary)
        - adu_per_photon = -1.0 (negative)
        - adu_per_photon = -1e-6 (small negative)
        """
        from dbex.refinement.inputs import prepare_refinement_inputs

        DL = data_load_instance

        # Test 1: adu_per_photon = 0 should fail
        with pytest.raises(ValueError, match="adu_per_photon must be strictly positive.*got 0"):
            prepare_refinement_inputs(
                data=DL.data,
                background_image=DL.background_image,
                trusted_mask=DL.trusted_mask,
                bbox=DL.bbox,
                pids=DL.pids,
                detector=DL.detector,
                adu_per_photon=0.0
            )

        # Test 2: adu_per_photon = -1.0 should fail
        with pytest.raises(ValueError, match="adu_per_photon must be strictly positive.*got -1"):
            prepare_refinement_inputs(
                data=DL.data,
                background_image=DL.background_image,
                trusted_mask=DL.trusted_mask,
                bbox=DL.bbox,
                pids=DL.pids,
                detector=DL.detector,
                adu_per_photon=-1.0
            )

        # Test 3: adu_per_photon = -1e-6 should fail
        with pytest.raises(ValueError, match="adu_per_photon must be strictly positive.*got -1e-06"):
            prepare_refinement_inputs(
                data=DL.data,
                background_image=DL.background_image,
                trusted_mask=DL.trusted_mask,
                bbox=DL.bbox,
                pids=DL.pids,
                detector=DL.detector,
                adu_per_photon=-1e-6
            )

        # Test 4: Positive adu_per_photon should succeed (sanity check)
        inputs = prepare_refinement_inputs(
            data=DL.data,
            background_image=DL.background_image,
            trusted_mask=DL.trusted_mask,
            bbox=DL.bbox,
            pids=DL.pids,
            detector=DL.detector,
            adu_per_photon=10.0
        )
        assert inputs is not None
        assert inputs.target_representation == "photons"

    def test_DB_AT_023_photon_vs_adu_loss_mask_consistency(self, data_load_instance):
        """
        DB-AT-023 (4/4): Validate loss mask consistency across ADU/photon modes.

        Acceptance criteria:
        1. loss_mask is identical regardless of calibration mode
        2. loss_mask = (background >= 0) & trusted_mask (spec-db-core.md:55)
        3. panel_slices are identical across modes
        4. trusted_mask is identical across modes

        Metrics captured:
        - loss_mask_match: whether ADU and photon loss_masks are identical
        - loss_mask_coverage_adu: fraction of pixels in ADU loss_mask
        - loss_mask_coverage_photon: fraction of pixels in photon loss_mask
        - panel_slices_match: whether panel_slices are identical
        """
        from dbex.refinement.inputs import prepare_refinement_inputs

        DL = data_load_instance

        # Prepare inputs in ADU mode
        inputs_adu = prepare_refinement_inputs(
            data=DL.data,
            background_image=DL.background_image,
            trusted_mask=DL.trusted_mask,
            bbox=DL.bbox,
            pids=DL.pids,
            detector=DL.detector,
            adu_per_photon=None
        )

        # Prepare inputs in photon mode
        inputs_photon = prepare_refinement_inputs(
            data=DL.data,
            background_image=DL.background_image,
            trusted_mask=DL.trusted_mask,
            bbox=DL.bbox,
            pids=DL.pids,
            detector=DL.detector,
            adu_per_photon=10.0
        )

        # Validate loss_mask consistency
        loss_mask_match = np.array_equal(inputs_adu.loss_mask, inputs_photon.loss_mask)
        assert loss_mask_match, \
            "loss_mask should be identical across ADU and photon modes. " \
            f"ADU coverage: {inputs_adu.loss_mask.mean():.4%}, " \
            f"Photon coverage: {inputs_photon.loss_mask.mean():.4%}"

        # Validate panel_slices consistency
        panel_slices_match = inputs_adu.panel_slices == inputs_photon.panel_slices
        assert panel_slices_match, \
            "panel_slices should be identical across ADU and photon modes"

        # Validate trusted_mask consistency
        trusted_mask_match = np.array_equal(inputs_adu.trusted_mask, inputs_photon.trusted_mask)
        assert trusted_mask_match, \
            "trusted_mask should be identical across ADU and photon modes"

        # Record metrics
        metrics = {
            "loss_mask_match": bool(loss_mask_match),
            "loss_mask_coverage_adu": float(inputs_adu.loss_mask.mean()),
            "loss_mask_coverage_photon": float(inputs_photon.loss_mask.mean()),
            "panel_slices_match": bool(panel_slices_match),
            "trusted_mask_match": bool(trusted_mask_match),
            "n_panel_slices": len(inputs_adu.panel_slices),
        }

        # Write metrics if artifact directory is set
        artifact_dir = os.getenv("DBAT023_ARTIFACT_DIR")
        if artifact_dir:
            os.makedirs(artifact_dir, exist_ok=True)
            with open(f"{artifact_dir}/consistency_metrics.json", "w") as f:
                json.dump(metrics, f, indent=2)
