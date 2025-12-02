"""
Tests for nanobrag_bridge module.

Tests verify spec-db-core.md compliance:
- [panel, slow, fast] tensor ordering
- Background subtraction and loss mask policy
- Pixel pitch guards
- Mask polarity enforcement
"""

import pytest
import numpy as np
from unittest.mock import Mock

from dbex.refinement.inputs import RefinementInputs, prepare_refinement_inputs


@pytest.fixture
def mock_detector():
    """
    Create a mock dxtbx Detector with square pixels.

    Mocks a simple 2-panel detector with 0.1mm square pixels.
    """
    detector = Mock()

    # Create two mock panels
    panel0 = Mock()
    panel0.get_pixel_size.return_value = (0.1, 0.1)  # (fast_mm, slow_mm)
    panel0.get_image_size.return_value = (512, 512)  # (fast_px, slow_px)

    panel1 = Mock()
    panel1.get_pixel_size.return_value = (0.1, 0.1)
    panel1.get_image_size.return_value = (512, 512)

    detector.__getitem__ = lambda self, idx: [panel0, panel1][idx]
    detector.__iter__ = lambda self: iter([panel0, panel1])
    detector.__len__ = lambda self: 2

    return detector


@pytest.fixture
def mock_detector_rectangular():
    """
    Create a mock detector with non-square pixels for guard testing.
    """
    detector = Mock()

    panel0 = Mock()
    panel0.get_pixel_size.return_value = (0.1, 0.15)  # Non-square!
    panel0.get_image_size.return_value = (512, 512)

    detector.__getitem__ = lambda self, idx: [panel0][idx]
    detector.__iter__ = lambda self: iter([panel0])
    detector.__len__ = lambda self: 1

    return detector


@pytest.fixture
def sample_data():
    """
    Create minimal sample data arrays for 2-panel detector with 2 ROIs.

    Shapes: [2 panels, 512 slow, 512 fast]
    """
    # Create 2-panel detector data
    data = np.random.uniform(100, 1000, size=(2, 512, 512)).astype(np.float32)

    # Background image: mostly -1, with some valid regions
    background = np.full((2, 512, 512), -1.0, dtype=np.float32)

    # Define two ROI regions with valid background
    # ROI 1: panel 0, bbox (100, 120, 100, 120)
    background[0, 100:120, 100:120] = np.random.uniform(10, 50, size=(20, 20))

    # ROI 2: panel 1, bbox (200, 230, 200, 230)
    background[1, 200:230, 200:230] = np.random.uniform(10, 50, size=(30, 30))

    # Trusted mask: True=include, mostly True with some bad pixels
    trusted_mask = np.ones((2, 512, 512), dtype=bool)
    # Add some bad pixels
    trusted_mask[0, 105:110, 105:110] = False
    trusted_mask[1, 210:215, 210:215] = False

    # ROI bounding boxes and panel IDs
    bbox = np.array([
        [100, 120, 100, 120],  # ROI 1 on panel 0
        [200, 230, 200, 230],  # ROI 2 on panel 1
    ])
    pids = np.array([0, 1])

    return {
        'data': data,
        'background': background,
        'trusted_mask': trusted_mask,
        'bbox': bbox,
        'pids': pids,
    }


class TestPrepareRefinementInputs:
    """Test suite for prepare_refinement_inputs function."""

    def test_tensor_contract(self, mock_detector, sample_data):
        """
        Test that outputs satisfy spec-db-core.md tensor contracts.

        Verifies:
        - Output shapes match input [panel, slow, fast] ordering
        - Background subtraction applied correctly in ROI regions
        - Pixels outside ROIs are zeroed
        - Loss mask combines background validity and trusted mask
        - Panel slices list format is correct
        """
        result = prepare_refinement_inputs(
            data=sample_data['data'],
            background_image=sample_data['background'],
            trusted_mask=sample_data['trusted_mask'],
            bbox=sample_data['bbox'],
            pids=sample_data['pids'],
            detector=mock_detector
        )

        # Check return type
        assert isinstance(result, RefinementInputs)

        # Check shapes: [panel, slow, fast]
        assert result.target.shape == (2, 512, 512)
        assert result.loss_mask.shape == (2, 512, 512)
        assert result.trusted_mask.shape == (2, 512, 512)
        assert result.sigma_readout.shape == (2, 512, 512)

        # Check dtypes
        assert result.target.dtype == np.float32
        assert result.loss_mask.dtype == bool
        assert result.trusted_mask.dtype == bool
        assert result.sigma_readout.dtype == np.float32

        # Verify background subtraction in ROI 1 (panel 0, 100:120, 100:120)
        roi1_data = sample_data['data'][0, 100:120, 100:120]
        roi1_bg = sample_data['background'][0, 100:120, 100:120]
        roi1_target = result.target[0, 100:120, 100:120]

        # Where mask is True, should have data - background
        roi1_mask = result.loss_mask[0, 100:120, 100:120]
        expected = roi1_data - roi1_bg
        np.testing.assert_allclose(
            roi1_target[roi1_mask],
            expected[roi1_mask],
            rtol=1e-5,
            err_msg="Background subtraction incorrect in ROI 1"
        )

        # Pixels outside ROIs (background == -1) should be zeroed
        outside_roi = sample_data['background'][0, 0, 0] == -1
        assert result.target[0, 0, 0] == 0.0, "Pixels outside ROI should be zero"

        # Loss mask should be (background >= 0) & trusted_mask
        expected_loss_mask = (sample_data['background'] >= 0) & sample_data['trusted_mask']
        np.testing.assert_array_equal(
            result.loss_mask,
            expected_loss_mask,
            err_msg="Loss mask does not match (background >= 0) & trusted"
        )

        # Check panel_slices format
        assert len(result.panel_slices) == 2

        pid0, bbox0 = result.panel_slices[0]
        assert pid0 == 0
        assert bbox0 == (100, 120, 100, 120)

        pid1, bbox1 = result.panel_slices[1]
        assert pid1 == 1
        assert bbox1 == (200, 230, 200, 230)

        # Verify pixels are zeroed where loss_mask is False
        assert np.all(result.target[~result.loss_mask] == 0.0), \
            "Target should be zeroed where loss_mask is False"
        assert np.all(result.sigma_readout[~result.loss_mask] == 0.0), \
            "Sigma_readout should be zeroed where loss_mask is False"

    def test_sigma_readout_broadcast_and_conversion(self, mock_detector, sample_data):
        """Ensure sigma_readout supports broadcast inputs and photon conversion."""
        sigma_constant = 5.0  # ADU units
        result_adu = prepare_refinement_inputs(
            data=sample_data['data'],
            background_image=sample_data['background'],
            trusted_mask=sample_data['trusted_mask'],
            bbox=sample_data['bbox'],
            pids=sample_data['pids'],
            detector=mock_detector,
            sigma_readout=sigma_constant
        )
        assert np.allclose(
            result_adu.sigma_readout[result_adu.loss_mask],
            sigma_constant,
            rtol=1e-6
        )

        result_photons = prepare_refinement_inputs(
            data=sample_data['data'],
            background_image=sample_data['background'],
            trusted_mask=sample_data['trusted_mask'],
            bbox=sample_data['bbox'],
            pids=sample_data['pids'],
            detector=mock_detector,
            adu_per_photon=2.0,
            sigma_readout=sigma_constant
        )
        assert np.allclose(
            result_photons.sigma_readout[result_photons.loss_mask],
            sigma_constant / 2.0,
            rtol=1e-6
        )

    def test_mask_polarity(self, mock_detector):
        """
        Test that inverted mask polarity is detected and rejected.

        Guards against using inverted (False=include) masks which violate
        spec-db-core.md:29 trusted mask polarity requirement.
        """
        # Create minimal test data
        data = np.ones((1, 100, 100), dtype=np.float32)
        background = np.zeros((1, 100, 100), dtype=np.float32)

        # Inverted mask: mostly False (should be rejected)
        inverted_mask = np.zeros((1, 100, 100), dtype=bool)
        inverted_mask[0, 10:20, 10:20] = True  # Only 1% True

        bbox = np.array([[10, 20, 10, 20]])
        pids = np.array([0])

        # Should raise ValueError about mask polarity
        with pytest.raises(ValueError, match="Trusted mask appears inverted"):
            prepare_refinement_inputs(
                data=data,
                background_image=background,
                trusted_mask=inverted_mask,
                bbox=bbox,
                pids=pids,
                detector=mock_detector
            )

    def test_pixel_pitch_guard(self, mock_detector_rectangular, sample_data):
        """
        Test that non-square pixel pitch is detected and rejected.

        Enforces spec-db-core.md:40 requirement for square pixels.
        """
        # Use only single-panel data
        single_panel_data = {
            'data': sample_data['data'][0:1],
            'background': sample_data['background'][0:1],
            'trusted_mask': sample_data['trusted_mask'][0:1],
            'bbox': sample_data['bbox'][0:1],
            'pids': np.array([0]),
        }

        # Should raise ValueError about non-square pixels
        with pytest.raises(ValueError, match="non-square pixels"):
            prepare_refinement_inputs(
                data=single_panel_data['data'],
                background_image=single_panel_data['background'],
                trusted_mask=single_panel_data['trusted_mask'],
                bbox=single_panel_data['bbox'],
                pids=single_panel_data['pids'],
                detector=mock_detector_rectangular
            )

    def test_tuple_mask_input(self, mock_detector, sample_data):
        """
        Test that DIALS tuple-of-flex.bool mask format is handled correctly.

        DIALS trusted masks are often provided as tuples of per-panel arrays.
        """
        # Convert array mask to tuple format (DIALS style)
        tuple_mask = tuple(sample_data['trusted_mask'][i] for i in range(2))

        result = prepare_refinement_inputs(
            data=sample_data['data'],
            background_image=sample_data['background'],
            trusted_mask=tuple_mask,  # Tuple instead of array
            bbox=sample_data['bbox'],
            pids=sample_data['pids'],
            detector=mock_detector
        )

        # Should produce same result as array input
        assert result.trusted_mask.shape == (2, 512, 512)
        assert result.trusted_mask.dtype == bool

        # Verify mask values match original
        expected_mask = np.array([sample_data['trusted_mask'][0],
                                  sample_data['trusted_mask'][1]])
        np.testing.assert_array_equal(result.trusted_mask, expected_mask)
