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


def test_parity_small_fixture(warm_cache_off):
    """
    Validates ExperimentModel parity against unified simulator factory.

    Tests:
    - ExperimentModel(param_init="frozen") outputs match factory within 1e-6
    - Shape/dtype/device consistency
    - Per-pixel max abs diff ≤ 1e-6
    """
    import torch
    import numpy as np
    from pathlib import Path
    from argparse import Namespace
    from dbex.data_load import DataLoad
    from dbex.nanobrag_bridge import (
        create_detector_config,
        create_beam_config,
        create_crystal_config,
        build_structure_factor_grid
    )
    from dbex.refinement.helpers import create_unified_simulator, simulate_via_experiment_model

    # Load tiny dxtbx fixture (same as test_stage_a_expansion for consistency)
    repo_root = Path(__file__).parent.parent.parent

    # Use small detector fixture for fast execution
    expt_path = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small.expt"
    refl_path = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small.refl"
    mtz_path = repo_root / "scaled.mtz"

    # Construct DataLoad (minimal Args object)
    args = Namespace(
        exptName=str(expt_path),
        reflName=str(refl_path),
        exptIdx=0,
        maskFile=None,  # No mask for simplicity
        mtzFile=str(mtz_path),
        mtzCol="F,SIGF"
    )

    DL = DataLoad(args)

    # Get HKL grid and metadata
    hkl_indices = DL.F.indices()
    hkl_amplitudes = DL.F.data()

    device = torch.device("cpu")
    dtype = torch.float32

    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device,
        halo=False  # No halo needed for forward-only parity test
    )

    # Single panel test (use panel 0)
    panel_id = 0
    panel = DL.detector[panel_id]

    # Create configs (no calibration metadata for simplicity)
    detector_config = create_detector_config(
        panel=panel,
        beam=DL.beam,
        trusted_mask=None
    )
    beam_config = create_beam_config(DL.beam)
    crystal_config, _ = create_crystal_config(DL.crystal, DL.Expt)

    # Run factory path (baseline)
    simulator_factory, _, sqrt_scale_factory, metadata_factory = create_unified_simulator(
        detector_config=detector_config,
        crystal_config=crystal_config,
        beam_config=beam_config,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        mask_array=None,
        spot_scale_override=1.0,
        device=device,
        dtype=dtype,
        calibration_metadata=None
    )
    image_factory = simulator_factory.run()

    # Run ExperimentModel adapter path
    image_adapter, sqrt_scale_adapter, metadata_adapter = simulate_via_experiment_model(
        detector_config=detector_config,
        crystal_config=crystal_config,
        beam_config=beam_config,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        mask_array=None,
        spot_scale_override=1.0,
        device=device,
        dtype=dtype,
        calibration_metadata=None
    )

    # Parity checks
    # 1. Shape/dtype/device consistency
    assert image_factory.shape == image_adapter.shape, \
        f"Shape mismatch: factory {image_factory.shape} != adapter {image_adapter.shape}"
    assert image_factory.dtype == image_adapter.dtype, \
        f"Dtype mismatch: factory {image_factory.dtype} != adapter {image_adapter.dtype}"
    assert image_factory.device == image_adapter.device, \
        f"Device mismatch: factory {image_factory.device} != adapter {image_adapter.device}"

    # 2. sqrt_scale consistency
    assert abs(sqrt_scale_factory - sqrt_scale_adapter) < 1e-9, \
        f"sqrt_scale mismatch: factory {sqrt_scale_factory} != adapter {sqrt_scale_adapter}"

    # 3. Per-pixel parity (max abs diff ≤ 1e-6)
    max_abs_diff = torch.max(torch.abs(image_factory - image_adapter)).item()

    # 4. Per-pixel MSE (informational)
    mse = torch.mean((image_factory - image_adapter) ** 2).item()

    # Debug: Print statistics
    print(f"\n[PARITY CHECK DEBUG]")
    print(f"  Factory image stats: min={image_factory.min().item():.2e}, max={image_factory.max().item():.2e}, mean={image_factory.mean().item():.2e}")
    print(f"  Adapter image stats: min={image_adapter.min().item():.2e}, max={image_adapter.max().item():.2e}, mean={image_adapter.mean().item():.2e}")
    print(f"  Parity metrics: max_abs_diff={max_abs_diff:.2e}, MSE={mse:.2e}, sqrt_scale={sqrt_scale_factory}")
    print(f"  Factory metadata: {metadata_factory}")
    print(f"  Adapter metadata: {metadata_adapter}")

    assert max_abs_diff <= 1e-6, \
        f"Parity FAIL: max abs diff {max_abs_diff:.2e} > 1e-6 tolerance"

    # PASS if all assertions pass
