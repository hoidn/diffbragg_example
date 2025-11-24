"""
TORCH-API-ALIGN-001 Phase A Test Stub: Unified Simulator Factory (A2)

Validates unified simulator factory shape/dtype/device validation and behavior
per docs/nanobrag_api.md (Simulator constructor, DetectorConfig).

Acceptance Criteria (from implementation.md:46-49):
- Factory validates shape/dtype/device for one-panel and multi-panel stitched runs
- spot_scale_override handling (sqrt applied post-run)
- Calibration metadata (beam_config, N_cells) gates preserved
- Mask array normalized on device/dtype

This test is xfail-guarded until Phase B wiring lands (B1/B2).

Findings applied:
- SCALE-004: Calibration metadata
- PERF-WARM-001: Warm-cache OFF pattern
"""

import pytest
import torch


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


def test_panel_and_stitched_shapes(warm_cache_off):
    """
    Validates unified simulator factory for one-panel and stitched multi-panel runs.

    Tests:
    - Factory validates shape/dtype/device
    - One-panel and multi-panel stitched outputs match expected shapes
    - spot_scale_override applied correctly (sqrt post-run)
    - Calibration metadata (beam_config, N_cells) preserved
    - Mask array normalized on device/dtype

    Acceptance: Factory produces correct tensor shapes, applies calibration,
    and maintains dtype/device consistency.

    Implementation note: Uses tiny fixtures (<100x100 px) for fast execution.
    Phase B will implement actual factory wiring to satisfy this test.
    """
    pytest.skip("Phase B/C wiring pending")

    # Phase B implementation will:
    # 1. Build one-panel DetectorConfig via create_detector_config
    # 2. Build multi-panel (stitched) DetectorConfig
    # 3. Call unified factory with/without spot_scale_override
    # 4. Assert shapes match expected [panel, slow, fast]
    # 5. Assert dtype/device consistency
    # 6. Assert calibration metadata (N_cells) applied
    # 7. Assert mask normalized on device/dtype

    pass


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_factory_cuda(warm_cache_off):
    """
    Validates unified simulator factory on CUDA device.

    Tests:
    - Factory accepts device='cuda'
    - Output tensors reside on CUDA device
    - dtype consistency maintained

    Acceptance: Factory produces CUDA tensors with correct dtype.

    Implementation note: Skipped when CUDA unavailable. Uses tiny fixture
    for fast execution. Phase B will implement actual factory wiring.
    """
    pytest.skip("Phase B/C wiring pending")

    # Phase B implementation will:
    # 1. Build DetectorConfig on CUDA
    # 2. Call unified factory with device='cuda'
    # 3. Assert output tensors on CUDA
    # 4. Assert dtype consistency

    pass
