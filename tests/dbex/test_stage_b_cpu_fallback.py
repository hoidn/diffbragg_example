"""
Tests for Stage B CPU fallback behavior (ARCH-REFINE-001 Phase B.5).

Validates that:
- _build_stage_b_params flips use_stage_b_cpu_fallback=True when config.stage_b_full_eval_on_cpu=True
  and device='cuda:0' and use_stage_a_roi_mode=False
- Stage B clones Stage A context to CPU when CPU fallback is active
- stage_b_cache_mode="warm" is preserved when Stage A warm cache is enabled

Spec references:
- docs/findings.md GRADIENT-003 (CPU fallback fragility)
- docs/findings.md PERF-WARM-011/012 (CPU panel path + warm cache semantics)
- REFINE-010 (Stage A ROI auto-panel threshold informing CPU fallback preconditions)
"""

import pytest
import torch
import numpy as np
from unittest.mock import patch, MagicMock


def test_stage_b_params_cpu_fallback_clones_stage_a_ctx():
    """
    Validate _build_stage_b_params flips use_stage_b_cpu_fallback=True and clones Stage A context to CPU.

    Acceptance (GRADIENT-003, PERF-WARM-011/012):
    - When config.stage_b_full_eval_on_cpu=True, device='cuda:0', use_stage_a_roi_mode=False:
      - use_stage_b_cpu_fallback=True
      - _build_stage_a_context is called with device=torch.device("cpu")
      - stage_b_eval_stage_a_ctx is the CPU-cloned context
      - stage_b_cache_mode="warm" when config.enable_stage_a_warm_cache=True
    - When config.stage_b_full_eval_on_cpu=False or device='cpu' or use_stage_a_roi_mode=True:
      - use_stage_b_cpu_fallback=False
      - Stage B reuses original Stage A context (no cloning)
    """
    from dbex.refinement.stage_b_impl import _build_stage_b_params
    from dbex.nanobrag_refinement import RefinementConfig

    # Mock RefinementInputs
    class MockRefinementInputs:
        target = np.zeros((1, 100, 100), dtype=np.float32)
        loss_mask = np.ones((1, 100, 100), dtype=bool)
        panel_slices = [(0, (0, 100, 0, 100))]
        trusted_mask = np.ones((1, 100, 100), dtype=bool)
        sigma_readout = np.ones((1, 100, 100), dtype=np.float32) * 3.0

    # Mock detector/beam/crystal
    class MockDetector:
        pass

    class MockBeam:
        pass

    class MockCrystal:
        pass

    # Mock HKL grid and metadata
    hkl_grid = torch.zeros((10, 10, 10), dtype=torch.complex64)
    hkl_metadata = {
        "has_halo": False,
        "nabc_grid": (10, 10, 10),
        "default_F": 0.0,
        "h_min": 0, "h_max": 9,
        "k_min": 0, "k_max": 9,
        "l_min": 0, "l_max": 9,
    }

    # Create minimal Stage A context dict
    stage_a_ctx = {
        "detector_models": [MagicMock()],
        "mask_tensors": [torch.ones(100, 100)],
        "hkl_grid_on_device": hkl_grid.cuda() if torch.cuda.is_available() else hkl_grid,
        "baseline_log_scale": 0.0,
    }

    # Canonical baseline (from Stage A)
    canonical_baseline = {
        "roi_count": 1,
        "log_scale": 0.0,
        "cell_a": 10.0, "cell_b": 10.0, "cell_c": 10.0,
        "cell_alpha": 90.0, "cell_beta": 90.0, "cell_gamma": 90.0,
        "misset_deg": (0.0, 0.0, 0.0),
        "chi_squared": 1e8,
        "masked_mse": 1e6,
    }

    panel_slices = [(slice(0, 100), slice(0, 100))]
    sampled_panel_ids = [0]

    # Create RefinementConfig with CPU fallback enabled
    config = RefinementConfig(
        device="cuda:0" if torch.cuda.is_available() else "cpu",
        stage_b_full_eval_on_cpu=True,
        enable_stage_a_warm_cache=True,
        stage_b_mode="shell",  # Shell mode for simplicity
    )

    # Mock _build_stage_a_context and compute_hkl_shell_lookup to avoid heavy dependencies
    with patch("dbex.refinement.stage_b_impl._build_stage_a_context") as mock_build_ctx, \
         patch("dbex.refinement.stage_b_impl.compute_hkl_shell_lookup") as mock_shell_lookup:

        # Configure mock Stage A context builder to return minimal CPU context
        cpu_stage_a_ctx = {
            "detector_models": [MagicMock()],
            "mask_tensors": [torch.ones(100, 100, device="cpu")],
            "hkl_grid_on_device": hkl_grid.cpu(),
            "baseline_log_scale": 0.0,
        }
        mock_build_ctx.return_value = cpu_stage_a_ctx

        # Configure mock shell lookup to return minimal shell data
        shell_indices = torch.zeros((10, 10, 10), dtype=torch.int32)
        shell_edges = np.array([0.0, 1.0, 2.0])
        mock_shell_lookup.return_value = (shell_indices, shell_edges)

        # Run _build_stage_b_params with CUDA device and panel mode (ROI mode disabled)
        device = torch.device(config.device)
        dtype = torch.float32
        sigma_floor_sq_cache = {}  # Empty cache dict for test
        param_values = _build_stage_b_params(
            config=config,
            device=device,
            dtype=dtype,
            stage_a_ctx=stage_a_ctx,
            canonical_baseline=canonical_baseline,
            n_panels=1,
            sampled_panel_ids=sampled_panel_ids,
            sigma_floor_sq_cache=sigma_floor_sq_cache,
            use_stage_a_roi_mode=False,  # Panel mode triggers CPU fallback
            crystal=MockCrystal(),
            hkl_metadata=hkl_metadata,
            hkl_grid=hkl_grid,
            detector=MockDetector(),
            beam=MockBeam(),
            inputs=MockRefinementInputs(),
            panel_slices=panel_slices,
        )

        # Validate CPU fallback was activated (only if CUDA is available)
        if torch.cuda.is_available():
            assert param_values["use_stage_b_cpu_fallback"] is True, \
                "use_stage_b_cpu_fallback should be True when stage_b_full_eval_on_cpu=True, device='cuda:0', panel mode"
        else:
            # On CPU-only systems, fallback is False (no need to clone CPU→CPU)
            assert param_values["use_stage_b_cpu_fallback"] is False, \
                "use_stage_b_cpu_fallback should be False when device='cpu'"

        # Validate Stage A context was cloned to CPU (only if CUDA is available)
        if torch.cuda.is_available():
            mock_build_ctx.assert_called_once()
            call_kwargs = mock_build_ctx.call_args[1]
            assert call_kwargs["device"] == torch.device("cpu"), \
                "_build_stage_a_context should be called with device='cpu' for CPU fallback"
            assert call_kwargs["enable_roi_mode"] is False, \
                "CPU fallback should use panel mode (enable_roi_mode=False)"
            assert param_values["stage_b_eval_stage_a_ctx"] is cpu_stage_a_ctx, \
                "stage_b_eval_stage_a_ctx should be the CPU-cloned context"
        else:
            # On CPU-only systems, no cloning occurs (reuses original context)
            assert param_values["stage_b_eval_stage_a_ctx"] is stage_a_ctx, \
                "stage_b_eval_stage_a_ctx should reuse original Stage A context on CPU-only"

        # Validate cache mode is "warm"
        assert param_values["stage_b_cache_mode"] == "warm", \
            "stage_b_cache_mode should be 'warm' when Stage A warm cache is enabled"


def test_stage_b_params_no_cpu_fallback_when_roi_mode_enabled():
    """
    Validate use_stage_b_cpu_fallback=False when ROI mode is enabled.

    Acceptance (GRADIENT-003):
    - When use_stage_a_roi_mode=True, CPU fallback is disabled even if config.stage_b_full_eval_on_cpu=True
    - Stage B reuses original Stage A context (no CPU cloning)
    """
    from dbex.refinement.stage_b_impl import _build_stage_b_params
    from dbex.nanobrag_refinement import RefinementConfig

    class MockRefinementInputs:
        target = np.zeros((1, 100, 100), dtype=np.float32)
        loss_mask = np.ones((1, 100, 100), dtype=bool)
        panel_slices = [(0, (0, 100, 0, 100))]
        trusted_mask = np.ones((1, 100, 100), dtype=bool)
        sigma_readout = np.ones((1, 100, 100), dtype=np.float32) * 3.0

    class MockDetector:
        pass

    class MockBeam:
        pass

    class MockCrystal:
        pass

    hkl_grid = torch.zeros((10, 10, 10), dtype=torch.complex64)
    hkl_metadata = {
        "has_halo": False,
        "nabc_grid": (10, 10, 10),
        "default_F": 0.0,
        "h_min": 0, "h_max": 9,
        "k_min": 0, "k_max": 9,
        "l_min": 0, "l_max": 9,
    }

    stage_a_ctx = {
        "detector_models": [MagicMock()],
        "mask_tensors": [torch.ones(100, 100)],
        "hkl_grid_on_device": hkl_grid,
        "baseline_log_scale": 0.0,
    }

    canonical_baseline = {
        "roi_count": 50,  # Multiple ROIs
        "log_scale": 0.0,
        "cell_a": 10.0, "cell_b": 10.0, "cell_c": 10.0,
        "cell_alpha": 90.0, "cell_beta": 90.0, "cell_gamma": 90.0,
        "misset_deg": (0.0, 0.0, 0.0),
        "chi_squared": 1e8,
        "masked_mse": 1e6,
    }

    panel_slices = [(slice(0, 100), slice(0, 100))]
    sampled_panel_ids = [0]

    config = RefinementConfig(
        device="cuda:0" if torch.cuda.is_available() else "cpu",
        stage_b_full_eval_on_cpu=True,
        enable_stage_a_warm_cache=True,
        stage_b_mode="shell",
    )

    with patch("dbex.refinement.stage_b_impl._build_stage_a_context") as mock_build_ctx, \
         patch("dbex.refinement.stage_b_impl.compute_hkl_shell_lookup") as mock_shell_lookup:

        shell_indices = torch.zeros((10, 10, 10), dtype=torch.int32)
        shell_edges = np.array([0.0, 1.0, 2.0])
        mock_shell_lookup.return_value = (shell_indices, shell_edges)

        device = torch.device(config.device)
        dtype = torch.float32
        sigma_floor_sq_cache = {}  # Empty cache dict for test
        param_values = _build_stage_b_params(
            config=config,
            device=device,
            dtype=dtype,
            stage_a_ctx=stage_a_ctx,
            canonical_baseline=canonical_baseline,
            n_panels=1,
            sampled_panel_ids=sampled_panel_ids,
            sigma_floor_sq_cache=sigma_floor_sq_cache,
            use_stage_a_roi_mode=True,  # ROI mode enabled
            crystal=MockCrystal(),
            hkl_metadata=hkl_metadata,
            hkl_grid=hkl_grid,
            detector=MockDetector(),
            beam=MockBeam(),
            inputs=MockRefinementInputs(),
            panel_slices=panel_slices,
        )

        # Validate CPU fallback is disabled with ROI mode
        assert param_values["use_stage_b_cpu_fallback"] is False, \
            "use_stage_b_cpu_fallback should be False when ROI mode is enabled"

        # Validate _build_stage_a_context was NOT called (no CPU cloning)
        mock_build_ctx.assert_not_called()

        # Validate Stage B reuses original Stage A context
        assert param_values["stage_b_eval_stage_a_ctx"] is stage_a_ctx, \
            "stage_b_eval_stage_a_ctx should reuse original Stage A context when ROI mode enabled"


def test_stage_b_params_no_cpu_fallback_when_config_disabled():
    """
    Validate use_stage_b_cpu_fallback=False when config.stage_b_full_eval_on_cpu=False.

    Acceptance (PERF-WARM-011):
    - When config.stage_b_full_eval_on_cpu=False, CPU fallback is disabled regardless of device
    - Stage B reuses original Stage A context
    """
    from dbex.refinement.stage_b_impl import _build_stage_b_params
    from dbex.nanobrag_refinement import RefinementConfig

    class MockRefinementInputs:
        target = np.zeros((1, 100, 100), dtype=np.float32)
        loss_mask = np.ones((1, 100, 100), dtype=bool)
        panel_slices = [(0, (0, 100, 0, 100))]
        trusted_mask = np.ones((1, 100, 100), dtype=bool)
        sigma_readout = np.ones((1, 100, 100), dtype=np.float32) * 3.0

    class MockDetector:
        pass

    class MockBeam:
        pass

    class MockCrystal:
        pass

    hkl_grid = torch.zeros((10, 10, 10), dtype=torch.complex64)
    hkl_metadata = {
        "has_halo": False,
        "nabc_grid": (10, 10, 10),
        "default_F": 0.0,
        "h_min": 0, "h_max": 9,
        "k_min": 0, "k_max": 9,
        "l_min": 0, "l_max": 9,
    }

    stage_a_ctx = {
        "detector_models": [MagicMock()],
        "mask_tensors": [torch.ones(100, 100)],
        "hkl_grid_on_device": hkl_grid,
        "baseline_log_scale": 0.0,
    }

    canonical_baseline = {
        "roi_count": 1,
        "log_scale": 0.0,
        "cell_a": 10.0, "cell_b": 10.0, "cell_c": 10.0,
        "cell_alpha": 90.0, "cell_beta": 90.0, "cell_gamma": 90.0,
        "misset_deg": (0.0, 0.0, 0.0),
        "chi_squared": 1e8,
        "masked_mse": 1e6,
    }

    panel_slices = [(slice(0, 100), slice(0, 100))]
    sampled_panel_ids = [0]

    config = RefinementConfig(
        device="cuda:0" if torch.cuda.is_available() else "cpu",
        stage_b_full_eval_on_cpu=False,  # CPU fallback disabled
        enable_stage_a_warm_cache=True,
        stage_b_mode="shell",
    )

    with patch("dbex.refinement.stage_b_impl._build_stage_a_context") as mock_build_ctx, \
         patch("dbex.refinement.stage_b_impl.compute_hkl_shell_lookup") as mock_shell_lookup:

        shell_indices = torch.zeros((10, 10, 10), dtype=torch.int32)
        shell_edges = np.array([0.0, 1.0, 2.0])
        mock_shell_lookup.return_value = (shell_indices, shell_edges)

        device = torch.device(config.device)
        dtype = torch.float32
        sigma_floor_sq_cache = {}  # Empty cache dict for test
        param_values = _build_stage_b_params(
            config=config,
            device=device,
            dtype=dtype,
            stage_a_ctx=stage_a_ctx,
            canonical_baseline=canonical_baseline,
            n_panels=1,
            sampled_panel_ids=sampled_panel_ids,
            sigma_floor_sq_cache=sigma_floor_sq_cache,
            use_stage_a_roi_mode=False,  # Panel mode
            crystal=MockCrystal(),
            hkl_metadata=hkl_metadata,
            hkl_grid=hkl_grid,
            detector=MockDetector(),
            beam=MockBeam(),
            inputs=MockRefinementInputs(),
            panel_slices=panel_slices,
        )

        # Validate CPU fallback is disabled
        assert param_values["use_stage_b_cpu_fallback"] is False, \
            "use_stage_b_cpu_fallback should be False when config.stage_b_full_eval_on_cpu=False"

        # Validate _build_stage_a_context was NOT called
        mock_build_ctx.assert_not_called()

        # Validate Stage B reuses original Stage A context
        assert param_values["stage_b_eval_stage_a_ctx"] is stage_a_ctx, \
            "stage_b_eval_stage_a_ctx should reuse original Stage A context when fallback disabled"


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
