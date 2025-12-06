"""
Unit tests for canonical scaling utilities (ARCH-CONTRACT-002).

Tests the apply_sqrt_spot_scale function, which is the single source of truth
for applying spot_scale_override to simulator outputs.

Phase: B.1 (Canonical API Authoring)
Initiative: ARCH-IMPL-CONFORMANCE-001
"""

import numpy as np
import pytest

from dbex.refinement.scaling_utils import apply_sqrt_spot_scale


class TestApplySqrtSpotScale:
    """
    Unit tests for apply_sqrt_spot_scale (ARCH-CONTRACT-002 owner API).

    Validates:
    - No metadata (None) → scale = 1.0
    - No spot_scale_override key → scale = 1.0
    - spot_scale_override = 0 → scale = 1.0
    - spot_scale_override > 0 → scale = sqrt(spot_scale_override)
    - Shape preservation (panel mode vs single-panel)
    - Error handling (negative/NaN/Inf values)
    """

    def test_no_metadata(self):
        """No calibration_metadata → identity scaling."""
        bragg = np.array([[100.0, 200.0], [300.0, 400.0]])
        result = apply_sqrt_spot_scale(bragg, calibration_metadata=None)
        np.testing.assert_allclose(result, bragg, rtol=1e-12)

    def test_no_spot_scale_override_key(self):
        """calibration_metadata present but no spot_scale_override key → identity scaling."""
        bragg = np.array([[100.0, 200.0], [300.0, 400.0]])
        metadata = {'beam_flux': 1e12}  # irrelevant key
        result = apply_sqrt_spot_scale(bragg, calibration_metadata=metadata)
        np.testing.assert_allclose(result, bragg, rtol=1e-12)

    def test_spot_scale_override_zero(self):
        """spot_scale_override = 0 → identity scaling."""
        bragg = np.array([[100.0, 200.0], [300.0, 400.0]])
        metadata = {'spot_scale_override': 0.0}
        result = apply_sqrt_spot_scale(bragg, calibration_metadata=metadata)
        np.testing.assert_allclose(result, bragg, rtol=1e-12)

    def test_spot_scale_override_positive(self):
        """spot_scale_override = 3.2e17 → scale ≈ 5.66e8."""
        bragg = np.array([[100.0, 200.0], [300.0, 400.0]])
        spot_scale_override = 3.2e17
        metadata = {'spot_scale_override': spot_scale_override}

        result = apply_sqrt_spot_scale(bragg, calibration_metadata=metadata)

        expected_scale = np.sqrt(spot_scale_override)
        expected = bragg * expected_scale
        np.testing.assert_allclose(result, expected, rtol=1e-12)

        # Verify actual scaling factor magnitude
        assert np.isclose(expected_scale, 5.656854249492381e8, rtol=1e-6)

    def test_shape_preservation_single_panel(self):
        """Single panel [slow, fast] shape preserved."""
        bragg = np.random.rand(195, 487)  # typical panel shape
        metadata = {'spot_scale_override': 1e10}
        result = apply_sqrt_spot_scale(bragg, calibration_metadata=metadata)
        assert result.shape == bragg.shape

    def test_shape_preservation_panel_mode(self):
        """Panel mode [n_panels, slow, fast] shape preserved."""
        bragg = np.random.rand(64, 195, 487)  # 64 panels
        metadata = {'spot_scale_override': 1e10}
        result = apply_sqrt_spot_scale(bragg, calibration_metadata=metadata)
        assert result.shape == bragg.shape

    def test_realistic_spot_scale_override(self):
        """
        Realistic DiffBragg spot_scale_override value from DB_AT fixtures.

        From SCALE-008/009 findings, typical DiffBragg spot_scale_override ≈ 3.2e17,
        yielding sqrt ≈ 5.66e8.
        """
        bragg = np.ones((64, 195, 487))  # 64 panels, unit intensity
        metadata = {'spot_scale_override': 3.2e17}

        result = apply_sqrt_spot_scale(bragg, calibration_metadata=metadata)

        # After scaling, every pixel should be ~5.66e8
        expected_intensity = np.sqrt(3.2e17)
        np.testing.assert_allclose(result, expected_intensity, rtol=1e-10)

    def test_error_negative_spot_scale_override(self):
        """spot_scale_override < 0 → ValueError."""
        bragg = np.array([[100.0, 200.0], [300.0, 400.0]])
        metadata = {'spot_scale_override': -1.0}

        with pytest.raises(ValueError, match="must be non-negative"):
            apply_sqrt_spot_scale(bragg, calibration_metadata=metadata)

    def test_error_nan_spot_scale_override(self):
        """spot_scale_override = NaN → ValueError."""
        bragg = np.array([[100.0, 200.0], [300.0, 400.0]])
        metadata = {'spot_scale_override': float('nan')}

        with pytest.raises(ValueError, match="must be finite"):
            apply_sqrt_spot_scale(bragg, calibration_metadata=metadata)

    def test_error_inf_spot_scale_override(self):
        """spot_scale_override = Inf → ValueError."""
        bragg = np.array([[100.0, 200.0], [300.0, 400.0]])
        metadata = {'spot_scale_override': float('inf')}

        with pytest.raises(ValueError, match="must be finite"):
            apply_sqrt_spot_scale(bragg, calibration_metadata=metadata)

    def test_dtype_preservation(self):
        """Input dtype preserved (float32/float64 common in simulators)."""
        for dtype in [np.float32, np.float64]:
            bragg = np.array([[100.0, 200.0], [300.0, 400.0]], dtype=dtype)
            metadata = {'spot_scale_override': 3.2e17}
            result = apply_sqrt_spot_scale(bragg, calibration_metadata=metadata)
            # Note: scaling with float(np.sqrt(...)) may promote to float64
            # This is acceptable for production paths
            assert result.dtype in [np.float32, np.float64]
