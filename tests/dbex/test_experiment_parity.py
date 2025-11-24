"""
TORCH-API-ALIGN-001 Phase A Test Stub: ExperimentModel Parity (A3)

Validates ExperimentModel(param_init="frozen") parity against legacy Simulator wiring
per docs/nanobrag_api.md (ExperimentModel interface, ROI-only compute behavior).

Acceptance Criteria (from implementation.md:50-54):
- ExperimentModel(param_init="frozen") outputs match legacy Simulator wiring within 1e-6
- ROI cropping parity (cropped DetectorConfig and beam center shift)
- Per-panel and stitched validation
- Structure factor attachment via experiment.set_structure_factors(F_grid, metadata)

This test is xfail-guarded until Phase B wiring lands (B3).

Findings applied:
- ARCH-ENGINE-002: Telemetry packaging
- PERF-WARM-001: Warm-cache OFF pattern
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
def test_parity_small_fixture(warm_cache_off):
    """
    Validates ExperimentModel parity against legacy Simulator wiring.

    Tests:
    - ExperimentModel(param_init="frozen") outputs match legacy within 1e-6
    - ROI cropping parity (cropped DetectorConfig + beam center shift)
    - Per-panel and stitched output consistency
    - Structure factor attachment (experiment.set_structure_factors)

    Acceptance: ExperimentModel outputs match legacy Simulator wiring
    within 1e-6 tolerance on tiny fixtures.

    Implementation note: Uses tiny fixture (<100x100 px) for fast execution.
    Forces warm-cache OFF via fixture. Phase B will implement actual
    ExperimentModel adapter wiring to satisfy this test.
    """
    pytest.skip("Phase B/C wiring pending")

    # Phase B implementation will:
    # 1. Load tiny dxtbx experiment + reflection fixture
    # 2. Build legacy Simulator via current wiring path
    # 3. Build ExperimentModel(param_init="frozen") via new adapter path
    # 4. Attach structure factors via experiment.set_structure_factors(F_grid, metadata)
    # 5. Run both paths on same ROI
    # 6. Assert outputs match within 1e-6 (per-pixel MSE or max abs diff)
    # 7. Validate ROI cropping parity (cropped DetectorConfig + beam center shift)
    # 8. Test per-panel and stitched modes

    pass
