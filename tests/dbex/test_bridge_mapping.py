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


@pytest.mark.xfail(reason="TORCH-API-ALIGN-001 Phase B wiring not yet implemented")
def test_dials_mapping_parity(warm_cache_off):
    """
    Validates DIALS mapping convention behavior.

    Tests:
    - Beam-center swap (fast, slow) → (s, f)
    - Euler angle extraction from panel axes
    - custom_beam_vector ignored under DIALS (documented behavior)

    Acceptance: DIALS mapping matches expected beam-center swap + Euler angles
    from panel rotation matrices. custom_beam_vector should be ignored.

    Implementation note: Uses tiny dxtbx beam/panel fixture (<100x100 px)
    for fast execution. Phase B will implement actual wiring to satisfy this test.
    """
    pytest.skip("Phase B/C wiring pending")

    # Phase B implementation will:
    # 1. Construct minimal dxtbx beam/panel
    # 2. Build DetectorConfig via create_detector_config (DIALS mode)
    # 3. Assert beam-center swap (fast, slow) → (s, f)
    # 4. Assert Euler extraction from panel axes
    # 5. Assert custom_beam_vector ignored (no effect on forward output)
    # 6. Compare end-to-end forward parity on tiny fixture

    pass
