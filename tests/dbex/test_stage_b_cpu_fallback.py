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
import os
from pathlib import Path
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


@pytest.mark.mini
def test_stage_b_baseline_guard_diff_payload():
    """
    Test Stage B baseline parity guard (REFINE-FLOW-001) JSON payload emission without optimizer construction.

    Validates that _check_stage_b_baseline_parity raises RuntimeError when Stage B initial chi² differs from
    Stage A canonical chi² by >0.1%, emitting stage_b_baseline_diff.json with per-panel breakdown.

    Acceptance (REFINE-FLOW-001):
    - When Stage B initial chi² exceeds canonical by >0.1%, RuntimeError cites REFINE-FLOW-001
    - stage_b_baseline_diff.json is emitted with:
        - canonical_snapshot (stage_label, chi_squared, iteration, roi_count, cell params, misset)
        - stage_b_reconstructed (cell params, cache_mode, cpu_fallback, stage_b_mode)
        - stage_b_initial_chi_squared, absolute_difference, relative_difference, tolerance
        - per_panel_breakdown (list of {panel_id, chi_squared, masked_mse})
    - When parity passes (<0.1%), stage_b_baseline_diff_path remains None
    """
    from dbex.refinement.stage_b_impl import _check_stage_b_baseline_parity
    from dbex.refinement.context import StageBTelemetryState
    from dbex.refinement.telemetry_collectors import StageBTelemetryCollector
    import tempfile
    import json

    device = torch.device("cpu")
    dtype = torch.float32

    # Test Case 1: Parity FAILS (chi² drift exceeds tolerance)
    baseline_chi_squared = 1e8
    canonical_baseline_fail = {
        "roi_count": 1,
        "log_scale": 0.0,
        "cell_a": 10.0, "cell_b": 10.0, "cell_c": 10.0,
        "cell_alpha": 90.0, "cell_beta": 90.0, "cell_gamma": 90.0,
        "misset_deg": (0.0, 0.0, 0.0),
        "chi_squared": baseline_chi_squared * 0.98,  # 2% lower to force guard
        "masked_mse": 1e6,
        "stage_label": "A",
        "iteration": 10,
    }

    param_values_fail = {
        "canonical_baseline": canonical_baseline_fail,
        "log_scale": torch.tensor(0.0, device=device, dtype=dtype),
        "cell_a_tensor": torch.tensor(10.0, device=device, dtype=dtype),
        "cell_b_tensor": torch.tensor(10.0, device=device, dtype=dtype),
        "cell_c_tensor": torch.tensor(10.0, device=device, dtype=dtype),
        "cell_alpha_tensor": torch.tensor(90.0, device=device, dtype=dtype),
        "cell_beta_tensor": torch.tensor(90.0, device=device, dtype=dtype),
        "cell_gamma_tensor": torch.tensor(90.0, device=device, dtype=dtype),
        "misset_xyz_deg": torch.tensor([0.0, 0.0, 0.0], device=device, dtype=dtype),
        "stage_b_cache_mode": "cold",
        "use_stage_b_cpu_fallback": False,
        "stage_b_mode": "shell",
    }

    def mock_compute_loss_fail(panel_ids, is_full=False, force_panel_eval=False):
        if is_full and force_panel_eval:
            if len(panel_ids) == 1:
                panel_chi2 = baseline_chi_squared / 2
                panel_mse = 1e6 / 2
                return torch.tensor(panel_chi2, device=device, dtype=dtype), torch.tensor(panel_mse, device=device, dtype=dtype)
        return torch.tensor(baseline_chi_squared, device=device, dtype=dtype), torch.tensor(1e6, device=device, dtype=dtype)

    with tempfile.TemporaryDirectory() as tmpdir:
        telemetry_path = f"{tmpdir}/telemetry.json"
        with patch.dict(os.environ, {"DBEX_SMOKE_TELEMETRY_PATH": telemetry_path}):
            # ARCH-TELEMETRY-001 Phase C.1: Create collector for observer-based telemetry
            telemetry_state_fail = StageBTelemetryState(
                iteration_count=[0],
                loss_trace_sample=[],
                loss_trace_full=[],
                best_loss_full=[],
                best_params_snapshot=[],
                chi_squared_trace_sample=[],
                chi_squared_trace_full=[],
                chi_squared_best=[float('inf'), 0],
                masked_mse_trace_sample=[],
                masked_mse_trace_full=[],
                masked_mse_best=[float('inf'), 0],
                perf_closure_evals=[0],
                perf_validation_runs=[0],
                perf_forward_times_ms=[],
                variance_floor_clamped_pixels=[0],
                variance_floor_masked_pixels=[0],
            )
            collector_fail = StageBTelemetryCollector(telemetry_state_fail)
            initial_chi_squared_b = torch.tensor(baseline_chi_squared, device=device, dtype=dtype)

            with pytest.raises(RuntimeError) as exc_info:
                _check_stage_b_baseline_parity(
                    canonical_baseline=canonical_baseline_fail,
                    initial_chi_squared_b=initial_chi_squared_b,
                    collector=collector_fail,
                    param_values=param_values_fail,
                    compute_loss_stage_b=mock_compute_loss_fail,
                    n_panels=2,
                )

            assert "REFINE-FLOW-001" in str(exc_info.value), \
                f"RuntimeError should cite REFINE-FLOW-001, got: {exc_info.value}"

            # Access metrics from collector state
            assert collector_fail.state.stage_b_baseline_rel_diff is not None
            assert collector_fail.state.stage_b_baseline_abs_diff is not None
            assert abs(collector_fail.state.stage_b_baseline_rel_diff) > 1e-3, \
                "relative_difference should exceed tolerance for this test"

            diff_path = Path(tmpdir) / "stage_b_baseline_diff.json"
            assert diff_path.exists(), f"stage_b_baseline_diff.json should be emitted at {diff_path}"

            with open(diff_path, 'r') as f:
                diff_data = json.load(f)

            expected_keys = {
                "canonical_snapshot", "stage_b_reconstructed", "stage_b_initial_chi_squared",
                "absolute_difference", "relative_difference", "tolerance", "per_panel_breakdown"
            }
            assert set(diff_data.keys()) == expected_keys, \
                f"Expected keys {expected_keys}, got {set(diff_data.keys())}"

            canonical_snap = diff_data["canonical_snapshot"]
            assert canonical_snap["stage_label"] == "A"
            assert canonical_snap["chi_squared"] == baseline_chi_squared * 0.98
            assert canonical_snap["iteration"] == 10
            assert canonical_snap["roi_count"] == 1
            assert "log_scale" in canonical_snap
            assert "cell_a" in canonical_snap
            assert "misset_deg" in canonical_snap

            stage_b_recon = diff_data["stage_b_reconstructed"]
            assert "log_scale" in stage_b_recon
            assert "cell_a" in stage_b_recon
            assert "cache_mode" in stage_b_recon
            assert stage_b_recon["cache_mode"] == "cold"
            assert "cpu_fallback" in stage_b_recon
            assert stage_b_recon["cpu_fallback"] is False
            assert stage_b_recon["stage_b_mode"] == "shell"

            per_panel = diff_data["per_panel_breakdown"]
            assert isinstance(per_panel, list)
            assert len(per_panel) == 2
            for panel_entry in per_panel:
                assert "panel_id" in panel_entry
                assert "chi_squared" in panel_entry
                assert "masked_mse" in panel_entry
                assert isinstance(panel_entry["chi_squared"], (float, int))
                assert isinstance(panel_entry["masked_mse"], (float, int))

            assert abs(diff_data["relative_difference"]) > 1e-3, \
                "relative_difference should exceed tolerance for this test"
            assert diff_data["tolerance"] == 1e-3

    # Test Case 2: Parity PASSES (chi² drift within tolerance)
    canonical_baseline_pass = {
        "roi_count": 1,
        "log_scale": 0.0,
        "cell_a": 10.0, "cell_b": 10.0, "cell_c": 10.0,
        "cell_alpha": 90.0, "cell_beta": 90.0, "cell_gamma": 90.0,
        "misset_deg": (0.0, 0.0, 0.0),
        "chi_squared": baseline_chi_squared * 1.0001,  # 0.01% higher (within 0.1% tolerance)
        "masked_mse": 1e6,
        "stage_label": "A",
        "iteration": 10,
    }

    param_values_pass = {
        "canonical_baseline": canonical_baseline_pass,
        "log_scale": torch.tensor(0.0, device=device, dtype=dtype),
        "cell_a_tensor": torch.tensor(10.0, device=device, dtype=dtype),
        "cell_b_tensor": torch.tensor(10.0, device=device, dtype=dtype),
        "cell_c_tensor": torch.tensor(10.0, device=device, dtype=dtype),
        "cell_alpha_tensor": torch.tensor(90.0, device=device, dtype=dtype),
        "cell_beta_tensor": torch.tensor(90.0, device=device, dtype=dtype),
        "cell_gamma_tensor": torch.tensor(90.0, device=device, dtype=dtype),
        "misset_xyz_deg": torch.tensor([0.0, 0.0, 0.0], device=device, dtype=dtype),
        "stage_b_cache_mode": "cold",
        "use_stage_b_cpu_fallback": False,
        "stage_b_mode": "shell",
    }

    def mock_compute_loss_pass(panel_ids, is_full=False, force_panel_eval=False):
        return torch.tensor(baseline_chi_squared, device=device, dtype=dtype), torch.tensor(1e6, device=device, dtype=dtype)

    # ARCH-TELEMETRY-001 Phase C.1: Create collector for observer-based telemetry
    telemetry_state_pass = StageBTelemetryState(
        iteration_count=[0],
        loss_trace_sample=[],
        loss_trace_full=[],
        best_loss_full=[],
        best_params_snapshot=[],
        chi_squared_trace_sample=[],
        chi_squared_trace_full=[],
        chi_squared_best=[float('inf'), 0],
        masked_mse_trace_sample=[],
        masked_mse_trace_full=[],
        masked_mse_best=[float('inf'), 0],
        perf_closure_evals=[0],
        perf_validation_runs=[0],
        perf_forward_times_ms=[],
        variance_floor_clamped_pixels=[0],
        variance_floor_masked_pixels=[0],
    )
    collector_pass = StageBTelemetryCollector(telemetry_state_pass)
    initial_chi_squared_b_pass = torch.tensor(baseline_chi_squared, device=device, dtype=dtype)

    _check_stage_b_baseline_parity(
        canonical_baseline=canonical_baseline_pass,
        initial_chi_squared_b=initial_chi_squared_b_pass,
        collector=collector_pass,
        param_values=param_values_pass,
        compute_loss_stage_b=mock_compute_loss_pass,
        n_panels=2,
    )

    # Access metrics from collector state
    assert collector_pass.state.stage_b_baseline_rel_diff is not None
    assert collector_pass.state.stage_b_baseline_abs_diff is not None
    assert abs(collector_pass.state.stage_b_baseline_rel_diff) < 1e-3, \
        "relative_difference should be within tolerance for passing case"
    assert collector_pass.state.stage_b_baseline_diff_path is None, \
        "stage_b_baseline_diff_path should be None when parity passes"



if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
