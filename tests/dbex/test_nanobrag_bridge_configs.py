"""
Tests for nanobrag_bridge config hydration functions.

Tests verify spec-db-core.md and config_crosswalk.md compliance:
- Detector: beam center swap (fast,slow) -> (s,f), sample->source vector, mask 0/1 float
- Beam: wavelength, polarization fallback
- Crystal: MOSFLM A* injection, stills phi defaults, unit cell angles in degrees
"""

import pytest
import numpy as np
from unittest.mock import Mock


class TestDetectorConfigMapping:
    """Test suite for Detector config hydration from dxtbx to nanobrag_torch."""

    @pytest.fixture
    def mock_panel(self):
        """
        Create a mock dxtbx Panel with standard geometry.

        Provides square pixels, standard orthonormal basis, and typical beam center.
        """
        panel = Mock()

        # Pixel metrics (config_crosswalk.md:20)
        panel.get_pixel_size.return_value = (0.172, 0.172)  # (fast_mm, slow_mm)
        panel.get_image_size.return_value = (2463, 2527)  # (fast_px, slow_px)

        # Distance (config_crosswalk.md:28)
        panel.get_directed_distance.return_value = 125.0  # mm

        # Beam center (config_crosswalk.md:19)
        # dxtbx returns (fast_mm, slow_mm)
        panel.get_beam_centre.return_value = (212.01, 217.35)

        # Basis vectors (lab frame, config_crosswalk.md:24-26)
        panel.get_fast_axis.return_value = np.array([1.0, 0.0, 0.0])
        panel.get_slow_axis.return_value = np.array([0.0, 1.0, 0.0])
        panel.get_normal.return_value = np.array([0.0, 0.0, 1.0])

        # Trusted range
        panel.get_trusted_range.return_value = (0.0, 65535.0)

        return panel

    @pytest.fixture
    def mock_beam(self):
        """
        Create a mock dxtbx Beam with standard wavelength and s0.

        s0 points source->sample per dxtbx convention (config_crosswalk.md:27, dxtbx_api.md:27).
        """
        beam = Mock()

        # Wavelength (config_crosswalk.md:46)
        beam.get_wavelength.return_value = 0.9795  # Angstroms

        # s0: source->sample, magnitude 1/lambda (dxtbx_api.md:27)
        wavelength = 0.9795
        s0_mag = 1.0 / wavelength
        # Typical geometry: beam along +z initially
        s0 = np.array([0.0, 0.0, s0_mag])
        beam.get_s0.return_value = s0

        # Polarization (config_crosswalk.md:48-49)
        beam.get_polarization_normal.return_value = np.array([0.0, 1.0, 0.0])
        beam.get_polarization_fraction.return_value = 0.999

        return beam

    def test_beam_center_swap(self, mock_panel, mock_beam):
        """
        Test that beam center coordinates are correctly swapped from dxtbx to torch.

        dxtbx returns (fast_mm, slow_mm) but torch expects (beam_center_s, beam_center_f)
        per config_crosswalk.md:29.

        This test will fail until create_detector_config is implemented.
        """
        from dbex.nanobrag_bridge import create_detector_config

        config = create_detector_config(mock_panel, mock_beam)

        fast_mm, slow_mm = mock_panel.get_beam_centre.return_value

        # Verify swap: torch expects (s, f)
        assert config.beam_center_s == slow_mm, \
            f"beam_center_s should be slow_mm={slow_mm}, got {config.beam_center_s}"
        assert config.beam_center_f == fast_mm, \
            f"beam_center_f should be fast_mm={fast_mm}, got {config.beam_center_f}"
        assert config.beam_center_source == "explicit", \
            "beam_center_source must be 'explicit' to skip MOSFLM +0.5px offset"

    def test_sample_to_source_vector(self, mock_panel, mock_beam):
        """
        Test that beam vector is correctly converted from source->sample to sample->source.

        dxtbx beam.get_s0() returns source->sample (dxtbx_api.md:27).
        torch requires sample->source as custom_beam_vector (config_crosswalk.md:27).

        This test will fail until create_detector_config is implemented.
        """
        from dbex.nanobrag_bridge import create_detector_config

        config = create_detector_config(mock_panel, mock_beam)

        s0 = mock_beam.get_s0.return_value
        expected_beam_vector = -s0 / np.linalg.norm(s0)

        # Verify normalization and direction reversal
        np.testing.assert_allclose(
            config.custom_beam_vector,
            expected_beam_vector,
            rtol=1e-6,
            err_msg="custom_beam_vector should be normalized -s0 (sample->source)"
        )

        # Verify unit vector
        norm = np.linalg.norm(config.custom_beam_vector)
        assert abs(norm - 1.0) < 1e-9, \
            f"custom_beam_vector should be normalized, got norm={norm}"

    def test_detector_convention_custom(self, mock_panel, mock_beam):
        """
        Test that detector convention is set to CUSTOM with all required basis vectors.

        Per config_crosswalk.md:23, we use CUSTOM convention with explicit basis vectors
        from dxtbx panel.get_*_axis() methods.

        This test will fail until create_detector_config is implemented.
        """
        from dbex.nanobrag_bridge import create_detector_config

        config = create_detector_config(mock_panel, mock_beam)

        # Verify convention
        # Note: We'll need to import DetectorConvention from nanobrag_torch
        # For now, check the string/enum value
        assert str(config.detector_convention) == "DetectorConvention.CUSTOM" or \
               config.detector_convention == "CUSTOM", \
            "detector_convention must be CUSTOM"

        # Verify basis vectors match panel axes
        np.testing.assert_array_equal(
            config.custom_fdet_vector,
            mock_panel.get_fast_axis.return_value,
            err_msg="custom_fdet_vector should match panel.get_fast_axis()"
        )
        np.testing.assert_array_equal(
            config.custom_sdet_vector,
            mock_panel.get_slow_axis.return_value,
            err_msg="custom_sdet_vector should match panel.get_slow_axis()"
        )
        np.testing.assert_array_equal(
            config.custom_odet_vector,
            mock_panel.get_normal.return_value,
            err_msg="custom_odet_vector should match panel.get_normal()"
        )

    def test_mask_array_float_conversion(self, mock_panel, mock_beam):
        """
        Test that trusted mask is correctly converted to 0/1 float tensor.

        Input: DIALS trusted mask (bool, True=include)
        Output: torch mask_array (float, 1=include) with shape (spixels, fpixels)
        per config_crosswalk.md:33 and nanobrag_api.md:34.

        This test will fail until create_detector_config is implemented.
        """
        from dbex.nanobrag_bridge import create_detector_config

        # Create sample trusted mask
        fast_px, slow_px = mock_panel.get_image_size.return_value
        trusted_mask = np.ones((slow_px, fast_px), dtype=bool)
        # Add some bad pixels
        trusted_mask[100:110, 200:210] = False

        config = create_detector_config(mock_panel, mock_beam, trusted_mask=trusted_mask)

        # Verify shape
        assert config.mask_array.shape == (slow_px, fast_px), \
            f"mask_array shape should be (spixels={slow_px}, fpixels={fast_px})"

        # Verify dtype is float
        assert config.mask_array.dtype in [np.float32, np.float64], \
            f"mask_array dtype should be float, got {config.mask_array.dtype}"

        # Verify polarity: True -> 1.0, False -> 0.0
        expected_float = trusted_mask.astype(np.float32)
        np.testing.assert_array_equal(
            config.mask_array,
            expected_float,
            err_msg="mask_array should be float with 1=include, 0=exclude"
        )

    def test_pixel_size_and_dimensions(self, mock_panel, mock_beam):
        """
        Test that pixel size and image dimensions are correctly mapped.

        Per config_crosswalk.md:30-31:
        - pixel_size_mm should be the (square) pixel pitch
        - spixels, fpixels should match panel.get_image_size()

        This test will fail until create_detector_config is implemented.
        """
        from dbex.nanobrag_bridge import create_detector_config

        config = create_detector_config(mock_panel, mock_beam)

        px_fast, px_slow = mock_panel.get_pixel_size.return_value
        fast_px, slow_px = mock_panel.get_image_size.return_value

        # Verify pixel size (should be square, so either value works)
        assert config.pixel_size_mm == px_fast, \
            f"pixel_size_mm should be {px_fast}, got {config.pixel_size_mm}"

        # Verify dimensions
        assert config.spixels == slow_px, \
            f"spixels should be {slow_px}, got {config.spixels}"
        assert config.fpixels == fast_px, \
            f"fpixels should be {fast_px}, got {config.fpixels}"

    def test_distance_mm(self, mock_panel, mock_beam):
        """
        Test that detector distance is correctly extracted.

        Per config_crosswalk.md:28, use panel.get_directed_distance() directly.

        This test will fail until create_detector_config is implemented.
        """
        from dbex.nanobrag_bridge import create_detector_config

        config = create_detector_config(mock_panel, mock_beam)

        expected_distance = mock_panel.get_directed_distance.return_value

        assert config.distance_mm == expected_distance, \
            f"distance_mm should be {expected_distance}, got {config.distance_mm}"


class TestBeamCrystalConfigMapping:
    """Test suite for Beam and Crystal config hydration from dxtbx to nanobrag_torch."""

    @pytest.fixture
    def mock_beam(self):
        """Create mock dxtbx Beam with standard parameters."""
        beam = Mock()
        beam.get_wavelength.return_value = 0.9795  # Angstroms

        # s0: source->sample
        wavelength = 0.9795
        s0_mag = 1.0 / wavelength
        s0 = np.array([0.0, 0.0, s0_mag])
        beam.get_s0.return_value = s0

        # Polarization
        beam.get_polarization_normal.return_value = np.array([0.0, 1.0, 0.0])
        beam.get_polarization_fraction.return_value = 0.999

        return beam

    @pytest.fixture
    def mock_beam_no_polarization(self):
        """Create mock Beam without polarization metadata for fallback testing."""
        beam = Mock()
        beam.get_wavelength.return_value = 1.0

        s0 = np.array([0.0, 0.0, 1.0])
        beam.get_s0.return_value = s0

        # Simulate missing polarization metadata
        beam.get_polarization_normal.side_effect = AttributeError("No polarization")
        beam.get_polarization_fraction.side_effect = AttributeError("No polarization")

        return beam

    @pytest.fixture
    def mock_crystal(self):
        """Create mock dxtbx Crystal with triclinic cell."""
        crystal = Mock()

        # Unit cell parameters: (a, b, c, alpha, beta, gamma)
        # Triclinic cell in Angstroms and degrees
        unit_cell = Mock()
        unit_cell.parameters.return_value = (50.0, 60.0, 70.0, 90.0, 95.0, 100.0)
        crystal.get_unit_cell.return_value = unit_cell

        # A matrix: columns are (a*, b*, c*) in 1/Angstrom (dxtbx_api.md:41)
        # These are realistic reciprocal vectors for the above cell
        A = np.array([
            [0.0200, 0.0000, -0.0017],
            [0.0000, 0.0167, -0.0029],
            [0.0000, 0.0000, 0.0144]
        ])
        crystal.get_A.return_value = A

        return crystal

    @pytest.fixture
    def mock_experiment_stills(self):
        """Create mock Experiment for stills (no scan)."""
        expt = Mock()
        expt.scan = None
        expt.goniometer = None
        return expt

    def test_beam_wavelength(self, mock_beam):
        """
        Test that beam wavelength is correctly extracted.

        Per config_crosswalk.md:46, wavelength_A should match beam.get_wavelength().

        This test will fail until create_beam_config is implemented.
        """
        from dbex.nanobrag_bridge import create_beam_config

        config = create_beam_config(mock_beam)

        expected_wavelength = mock_beam.get_wavelength.return_value

        assert config.wavelength_A == expected_wavelength, \
            f"wavelength_A should be {expected_wavelength}, got {config.wavelength_A}"

    def test_polarization_factor_parity_default(self, mock_beam):
        """
        Test that polarization factor defaults to 0.0 for parity with DiffBragg.

        Per config_crosswalk.md:47 and spec-db-core.md:44, default parity is
        polarization_factor=0.0, nopolar=False.

        This test will fail until create_beam_config is implemented.
        """
        from dbex.nanobrag_bridge import create_beam_config

        config = create_beam_config(mock_beam)

        assert config.polarization_factor == 0.0, \
            "polarization_factor should default to 0.0 for parity"
        assert config.nopolar is False, \
            "nopolar should be False"

    def test_polarization_metadata_extraction(self, mock_beam):
        """
        Test that polarization axis and fraction are extracted when available.

        Per config_crosswalk.md:48-49, use beam.get_polarization_normal() and
        beam.get_polarization_fraction() when available.

        This test will fail until create_beam_config is implemented.
        """
        from dbex.nanobrag_bridge import create_beam_config

        config = create_beam_config(mock_beam)

        expected_axis = mock_beam.get_polarization_normal.return_value
        expected_fraction = mock_beam.get_polarization_fraction.return_value

        np.testing.assert_array_equal(
            config.polarization_axis,
            expected_axis,
            err_msg="polarization_axis should match beam.get_polarization_normal()"
        )
        assert config.polarization_fraction == expected_fraction, \
            f"polarization_fraction should be {expected_fraction}, got {config.polarization_fraction}"

    def test_polarization_fallback(self, mock_beam_no_polarization):
        """
        Test that polarization falls back to defaults when metadata is missing.

        Per config_crosswalk.md:48-49, fallback to axis=[0,0,1], fraction=0.999.

        This test will fail until create_beam_config is implemented.
        """
        from dbex.nanobrag_bridge import create_beam_config

        config = create_beam_config(mock_beam_no_polarization)

        # Verify fallback values
        np.testing.assert_array_equal(
            config.polarization_axis,
            np.array([0.0, 0.0, 1.0]),
            err_msg="polarization_axis should fallback to [0,0,1]"
        )
        assert config.polarization_fraction == 0.999, \
            f"polarization_fraction should fallback to 0.999, got {config.polarization_fraction}"

    def test_crystal_unit_cell_parameters(self, mock_crystal, mock_experiment_stills):
        """
        Test that crystal unit cell parameters are correctly extracted in degrees.

        Per config_crosswalk.md:61, cell_alpha/beta/gamma must be in degrees.
        dxtbx returns degrees, torch expects degrees (no conversion needed).

        This test will fail until create_crystal_config is implemented.
        """
        from dbex.nanobrag_bridge import create_crystal_config

        config = create_crystal_config(mock_crystal, mock_experiment_stills)

        a, b, c, alpha, beta, gamma = mock_crystal.get_unit_cell().parameters()

        # Verify cell parameters
        assert config.cell_a == a, f"cell_a should be {a}, got {config.cell_a}"
        assert config.cell_b == b, f"cell_b should be {b}, got {config.cell_b}"
        assert config.cell_c == c, f"cell_c should be {c}, got {config.cell_c}"

        # Verify angles are in degrees (no conversion)
        assert config.cell_alpha == alpha, \
            f"cell_alpha should be {alpha} degrees, got {config.cell_alpha}"
        assert config.cell_beta == beta, \
            f"cell_beta should be {beta} degrees, got {config.cell_beta}"
        assert config.cell_gamma == gamma, \
            f"cell_gamma should be {gamma} degrees, got {config.cell_gamma}"

    def test_mosflm_astar_injection(self, mock_crystal, mock_experiment_stills):
        """
        Test that MOSFLM A* is correctly injected from dxtbx crystal.get_A().

        Per config_crosswalk.md:62, columns of A matrix should be assigned to
        mosflm_a_star, mosflm_b_star, mosflm_c_star.

        This test will fail until create_crystal_config is implemented.
        """
        from dbex.nanobrag_bridge import create_crystal_config

        config = create_crystal_config(mock_crystal, mock_experiment_stills)

        A = mock_crystal.get_A.return_value
        expected_a_star = A[:, 0]
        expected_b_star = A[:, 1]
        expected_c_star = A[:, 2]

        np.testing.assert_allclose(
            config.mosflm_a_star,
            expected_a_star,
            rtol=1e-6,
            err_msg="mosflm_a_star should be first column of A"
        )
        np.testing.assert_allclose(
            config.mosflm_b_star,
            expected_b_star,
            rtol=1e-6,
            err_msg="mosflm_b_star should be second column of A"
        )
        np.testing.assert_allclose(
            config.mosflm_c_star,
            expected_c_star,
            rtol=1e-6,
            err_msg="mosflm_c_star should be third column of A"
        )

    def test_stills_phi_defaults(self, mock_crystal, mock_experiment_stills):
        """
        Test that stills experiments get correct phi_steps and osc_range_deg defaults.

        Per config_crosswalk.md:64, stills should have:
        - phi_steps=1
        - osc_range_deg=0
        - mosaic_domains=1
        - mosaic_spread_deg=0

        This test will fail until create_crystal_config is implemented.
        """
        from dbex.nanobrag_bridge import create_crystal_config

        config = create_crystal_config(mock_crystal, mock_experiment_stills)

        # Verify stills defaults
        assert config.phi_steps == 1, \
            f"phi_steps should be 1 for stills, got {config.phi_steps}"
        assert config.osc_range_deg == 0.0, \
            f"osc_range_deg should be 0.0 for stills, got {config.osc_range_deg}"
        assert config.mosaic_domains == 1, \
            f"mosaic_domains should be 1 for stills, got {config.mosaic_domains}"
        assert config.mosaic_spread_deg == 0.0, \
            f"mosaic_spread_deg should be 0.0 for stills, got {config.mosaic_spread_deg}"

    def test_crystal_misset_zero_default(self, mock_crystal, mock_experiment_stills):
        """
        Test that misset_deg defaults to zero (identity rotation).

        Per config_crosswalk.md:63, misset_deg is applied after MOSFLM injection.
        Initially, we should set it to (0, 0, 0) to preserve the MOSFLM orientation.

        This test will fail until create_crystal_config is implemented.
        """
        from dbex.nanobrag_bridge import create_crystal_config

        config = create_crystal_config(mock_crystal, mock_experiment_stills)

        # Verify misset defaults to zero
        expected_misset = np.array([0.0, 0.0, 0.0])
        np.testing.assert_array_equal(
            config.misset_deg,
            expected_misset,
            err_msg="misset_deg should default to [0, 0, 0]"
        )
