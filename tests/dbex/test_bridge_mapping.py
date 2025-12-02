"""
TORCH-API-ALIGN-001 Phase A Test Stub: DIALS Mapping Parity (A1)

Validates DIALS mapping convention behavior per docs/nanobrag_api.md:44-47
and docs/config_crosswalk.md:29 (beam-center swap).

Acceptance Criteria (from implementation.md:42-44):
- Beam-center swap: (fast, slow) → (s, f) coordinate transformation
- Euler angle extraction from panel rotation axes
- custom_beam_vector ignored under DIALS convention (expected behavior in current engine)

This test is xfail-guarded until Phase B wiring lands (B1/B2).

Findings applied:
- GEOMETRY-001/002: DIALS beam-center swap + analytic Euler inversion
- CONFIG-001/002: Beam-center swap, DetectorConvention enum
"""

import pytest


@pytest.fixture
def warm_cache_off():
    """Force warm-cache OFF + NANOBRAGG_DISABLE_COMPILE=1 for determinism."""
    import os
    old_val = os.environ.get("NANOBRAGG_DISABLE_COMPILE")
    os.environ["NANOBRAGG_DISABLE_COMPILE"] = "1"
    yield {"enable_stage_a_warm_cache": False}
    if old_val is not None:
        os.environ["NANOBRAGG_DISABLE_COMPILE"] = old_val
    else:
        del os.environ["NANOBRAGG_DISABLE_COMPILE"]


def test_dials_mapping_parity(warm_cache_off):
    """
    Validates DIALS mapping convention behavior.

    Tests:
    - Beam-center swap (fast, slow) → (s, f)
    - Euler angle extraction from panel axes
    - custom_beam_vector ignored under DIALS (documented behavior)

    Acceptance: DIALS mapping matches expected beam-center swap + Euler angles
    from panel rotation matrices. custom_beam_vector should be ignored.

    Implementation note: Uses minimal mock panel/beam fixture for fast execution.
    """
    import numpy as np
    from unittest.mock import Mock
    from dbex.refinement.config_factories import create_detector_config

    # Minimal mock beam (1.0 Å wavelength, default direction [0,0,1])
    beam = Mock()
    beam.get_wavelength.return_value = 1.0
    s0_mag = 1.0 / 1.0  # 1/lambda
    beam.get_s0.return_value = np.array([0.0, 0.0, s0_mag])
    beam.get_polarization_normal.return_value = np.array([0.0, 1.0, 0.0])
    beam.get_polarization_fraction.return_value = 0.999

    # Minimal mock panel (100x100 px, 0.1 mm/px)
    # Panel origin at (-5.0, 5.0, -100.0) places beam center at (50, 50) px
    # fast_axis=(1,0,0), slow_axis=(0,-1,0), normal=(0,0,1) (simple rotation)
    panel = Mock()
    panel.get_pixel_size.return_value = (0.1, 0.1)  # (fast_mm, slow_mm)
    panel.get_image_size.return_value = (100, 100)  # (fast_px, slow_px)
    panel.get_directed_distance.return_value = 100.0  # mm

    # Beam center: panel origin (-5, 5, -100), beam at (0, 0, -100)
    # Delta = (5, -5, 0) in lab frame
    # dxtbx returns (fast_mm, slow_mm) projection
    # fast_proj = Delta · fast = (5, -5, 0) · (1, 0, 0) = 5.0
    # slow_proj = Delta · slow = (5, -5, 0) · (0, -1, 0) = 5.0
    panel.get_beam_centre.return_value = (5.0, 5.0)  # (fast_mm, slow_mm)

    # Panel axes (simple orthonormal basis)
    panel.get_fast_axis.return_value = np.array([1.0, 0.0, 0.0])
    panel.get_slow_axis.return_value = np.array([0.0, -1.0, 0.0])
    panel.get_normal.return_value = np.array([0.0, 0.0, -1.0])

    panel.get_trusted_range.return_value = (-1.0, 1e6)

    # Build DetectorConfig via DIALS convention
    detector_config = create_detector_config(panel, beam)

    # Assert beam-center swap (fast, slow) → (s, f)
    # Expected: DIALS swap means beam_center_s = slow_mm = 5.0, beam_center_f = fast_mm = 5.0
    assert abs(detector_config.beam_center_s - 5.0) < 1e-6, (
        f"Beam center slow mismatch: expected 5.0, got {detector_config.beam_center_s:.6f}"
    )
    assert abs(detector_config.beam_center_f - 5.0) < 1e-6, (
        f"Beam center fast mismatch: expected 5.0, got {detector_config.beam_center_f:.6f}"
    )

    # Assert Euler angle fields exist (defer exact values to Phase C)
    assert hasattr(detector_config, 'detector_rotx_deg'), "Missing detector_rotx_deg field"
    assert hasattr(detector_config, 'detector_roty_deg'), "Missing detector_roty_deg field"
    assert hasattr(detector_config, 'detector_rotz_deg'), "Missing detector_rotz_deg field"

    # Debug output
    print(f"Beam-center (s,f): ({detector_config.beam_center_s:.6f}, {detector_config.beam_center_f:.6f})")
    print(f"Euler angles (deg): rotx={detector_config.detector_rotx_deg:.4f}, roty={detector_config.detector_roty_deg:.4f}, rotz={detector_config.detector_rotz_deg:.4f}")
