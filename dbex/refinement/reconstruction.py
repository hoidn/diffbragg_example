"""
Shared final Bragg reconstruction helpers (ARCH-STAGE-CONTEXT-001 Phase D).

This module exports the helpers previously defined in `dbex/nanobrag_refinement.py`
so that both stage wrappers (StageA.run, StageB.run) and the engine path can import
them without touching the monolith.

Provides:
- build_final_bragg_from_stage_a_telemetry: Final Bragg reconstruction from Stage A telemetry
- build_final_bragg_from_stage_b_telemetry: Final Bragg reconstruction from Stage B telemetry

Per ARCH-STAGE-CONTEXT-001 Phase D:
- These helpers remain device/dtype neutral
- Stage A/B wrappers call them when they are the terminal stage
- run_nanobrag_refinement uses them as fallbacks when artifacts are unavailable

References:
- docs/spec-db-workflow.md §33 (engine artifact channel)
- ARCH-STAGE-CONTEXT-001 (artifact propagation)
- ARCH-ENGINE-ARTIFACTS-001 (final Bragg unification)
"""

import numpy as np
import torch
from typing import Any, Dict, Optional


def build_final_bragg_from_stage_a_telemetry(
    telemetry_a,
    detector,
    beam,
    crystal,
    inputs,
    hkl_grid,
    hkl_metadata,
    config,
    device,
    dtype,
    stage_a_ctx=None,
    baseline_crystal=None,
):
    """
    Build final Bragg array from Stage A telemetry (optimized crystal/scale params).

    Extracts Stage A final parameters from telemetry and regenerates full Bragg image.

    Args:
        telemetry_a: RefinementTelemetry instance with Stage A optimized param_deltas
        detector: dxtbx Detector object
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object
        inputs: RefinementInputs with panel_slices, trusted_mask
        hkl_grid: torch.Tensor structure factor grid
        hkl_metadata: dict with grid dimensions
        config: RefinementConfig with device, dtype
        device: torch.device for tensor operations
        dtype: torch.dtype for tensor operations
        stage_a_ctx: Optional Stage A context (detectors/simulators for warm cache)
        baseline_crystal: Optional baseline dxtbx Crystal for misset extraction

    Returns:
        bragg_full: np.ndarray, shape [n_panels, slow, fast], final Bragg image
    """
    # Lazy imports to avoid circular dependencies
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from dbex.refinement.config_factories import (
        create_detector_config,
        create_crystal_config,
    )
    from dbex.nanobrag_bridge import compute_baseline_misset_deg
    # ARCH-REFACTOR-001 Phase C.7: Import shared Stage A helper from stage_a_utils
    from dbex.refinement.stage_a_utils import _clamp_log_cell_deltas

    # Extract param_deltas from telemetry
    param_deltas_a = telemetry_a.param_deltas if hasattr(telemetry_a, 'param_deltas') else telemetry_a['param_deltas']

    # Extract Stage A final parameters
    log_scale = torch.tensor(param_deltas_a['log_scale']['final'], device=device, dtype=dtype, requires_grad=False)
    log_cell_a_delta = torch.tensor(param_deltas_a['log_cell_a_delta']['final'], device=device, dtype=dtype, requires_grad=False)
    log_cell_b_delta = torch.tensor(param_deltas_a['log_cell_b_delta']['final'], device=device, dtype=dtype, requires_grad=False)
    log_cell_c_delta = torch.tensor(param_deltas_a['log_cell_c_delta']['final'], device=device, dtype=dtype, requires_grad=False)
    angle_alpha_raw = torch.tensor(param_deltas_a['angle_alpha_raw']['final'], device=device, dtype=dtype, requires_grad=False)
    angle_beta_raw = torch.tensor(param_deltas_a['angle_beta_raw']['final'], device=device, dtype=dtype, requires_grad=False)
    angle_gamma_raw = torch.tensor(param_deltas_a['angle_gamma_raw']['final'], device=device, dtype=dtype, requires_grad=False)
    misset_xyz_deg_delta = param_deltas_a['misset_xyz_deg']['delta']
    misset_xyz_deg = torch.tensor(misset_xyz_deg_delta, device=device, dtype=dtype, requires_grad=False)

    # Apply Stage A cell perturbations (mirroring Stage B reconstruction pattern)
    cell_params = crystal.get_unit_cell().parameters()
    log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
        log_cell_a_delta,
        log_cell_b_delta,
        log_cell_c_delta,
        getattr(config, "log_cell_max_delta", 1.0),
    )
    cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
    cell_b_tensor = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
    cell_c_tensor = cell_params[2] * torch.exp(log_cell_c_delta_clamped)

    max_angle_delta = 10.0  # degrees
    cell_alpha_tensor = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
    cell_beta_tensor = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
    cell_gamma_tensor = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

    # Build crystal overrides
    crystal_overrides = {
        'cell_a': cell_a_tensor,
        'cell_b': cell_b_tensor,
        'cell_c': cell_c_tensor,
        'cell_alpha': cell_alpha_tensor,
        'cell_beta': cell_beta_tensor,
        'cell_gamma': cell_gamma_tensor
    }

    # Compute baseline misset if baseline_crystal provided (GEOMETRY-003)
    baseline_misset_deg_tensor = compute_baseline_misset_deg(
        crystal,
        baseline_crystal,
        device=device,
        dtype=dtype,
    )

    # Compute final misset (baseline + delta if baseline provided)
    if baseline_misset_deg_tensor is not None:
        final_misset = baseline_misset_deg_tensor + misset_xyz_deg
    else:
        final_misset = misset_xyz_deg

    # Build crystal config with refined parameters using override API
    crystal_config, _ = create_crystal_config(
        crystal=crystal,
        experiment=None,
        crystal_overrides=crystal_overrides,
        misset_deg_override=final_misset,
    )

    # Extract panel counts and full panel shape
    n_panels = len(detector)
    panel_shape = (
        detector[0].get_image_size()[1],  # slow
        detector[0].get_image_size()[0]   # fast
    )
    sampled_panel_ids = list(range(n_panels))

    # Extract spot_scale_override for post-run scaling (matches stage_a.py:442-443, SCALE-009)
    spot_scale_override = None
    if config.calibration_metadata is not None:
        spot_scale_override = config.calibration_metadata.get('spot_scale_override')

    sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override and spot_scale_override > 0 else 1.0

    # Build full Bragg array (panel mode)
    # Reuse warm cache simulators if available
    if stage_a_ctx is not None and hasattr(stage_a_ctx, 'simulators'):
        # Warm cache path: retarget existing simulators with refined crystal (GRADIENT-004, ARCH-FACTORY-001)
        # Build Crystal model with beam_config from context (BUGFIX: pass at construction time)
        crystal_model = Crystal(
            crystal_config,
            beam_config=stage_a_ctx.beam_config,  # FIXED: pass beam_config at construction time
            device=device,
            dtype=dtype,
        )
        crystal_model.interpolate = config.enable_hkl_interpolation
        crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
        crystal_model.hkl_metadata = hkl_metadata

        # ARCH-REFACTOR-001 Phase C.7: Import shared Stage A helper from stage_a_utils
        from dbex.refinement.stage_a_utils import _retarget_stage_a_simulators
        _retarget_stage_a_simulators(stage_a_ctx, crystal_model)
        simulators = stage_a_ctx.simulators
    else:
        # Cold path: build simulators via unified factory (ARCH-FACTORY-001 Phase B.4)
        from dbex.refinement.config_factories import create_beam_config
        from dbex.refinement.helpers import create_unified_simulator

        # Extract beam calibration for architectural consistency with Stage A (stage_a_utils.py:267)
        beam_flux = None
        beam_exposure = None
        beamsize_mm = None
        if config.calibration_metadata is not None:
            beam_flux = config.calibration_metadata.get('beam_flux')
            beam_exposure = config.calibration_metadata.get('beam_exposure')
            beamsize_mm = config.calibration_metadata.get('beamsize_mm')

        beam_config = create_beam_config(beam, flux=beam_flux, exposure=beam_exposure, beamsize_mm=beamsize_mm)
        simulators = []
        for pid in sampled_panel_ids:
            detector_config = create_detector_config(detector[pid], beam=beam)
            # Use unified factory for forward-only reconstruction (ARCH-FACTORY-001)
            # Pass spot_scale_override so factory can compute sqrt_scale for post-run application
            simulator, normalized_mask, sqrt_scale_from_factory, metadata = create_unified_simulator(
                detector_config=detector_config,
                crystal_config=crystal_config,
                beam_config=beam_config,
                hkl_grid=hkl_grid,
                hkl_metadata=hkl_metadata,
                mask_array=None,  # mask already in detector_config if needed
                spot_scale_override=spot_scale_override,  # Factory needs this to compute sqrt_scale
                device=device,
                dtype=dtype,
                calibration_metadata=getattr(config, 'calibration_metadata', None),
            )
            simulator.interpolate = config.enable_hkl_interpolation
            simulators.append(simulator)

    # Run forward model with refined parameters
    bragg_full = np.zeros((n_panels, *panel_shape), dtype=np.float32)

    # Extract log_scale_baseline from Stage A telemetry (TOOLING-VIS-001 Phase D.C, DB-AT-027)
    # When calibration metadata supplied the baseline, apply the same conditional clamp logic as Stage A
    log_scale_baseline_value = param_deltas_a.get('log_scale_baseline', {}).get('final')

    # Apply Stage A's log-scale clamp logic (matching stage_a.py lines 1194-1202)
    # When calibration metadata is present:
    #   log_scale_baseline = log(sqrt(spot_scale_override)) is the fixed baseline
    #   log_scale is a delta parameter, clamped to ±config.log_scale_max_delta (default ±3)
    #   Final scale = exp(log_scale_baseline + clamped_delta)
    # Otherwise (uncalibrated):
    #   log_scale is the direct learnable parameter, clamped to ±config.log_scale_max_delta_uncalibrated (default ±10)
    #   Final scale = exp(clamped_log_scale)
    max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
    delta_bound = getattr(config, "log_scale_max_delta", 3.0) if log_scale_baseline_value is not None else max_delta_uncal

    if log_scale_baseline_value is not None:
        # Calibrated path: add baseline to clamped delta
        log_scale_baseline_tensor = torch.tensor(log_scale_baseline_value, device=device, dtype=dtype)
        log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
        log_scale_clamped = log_scale_baseline_tensor + log_scale_delta_clamped
    else:
        # Uncalibrated path: clamp absolute log_scale (legacy behavior)
        log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)

    scale_factor = torch.exp(log_scale_clamped)
    for pid, sim in zip(sampled_panel_ids, simulators):
        bragg_panel = sim.run()
        bragg_scaled = bragg_panel * scale_factor
        bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)

    return bragg_full


def build_final_bragg_from_stage_b_telemetry(
    telemetry_a,
    telemetry_b,
    detector,
    beam,
    crystal,
    baseline_crystal,
    inputs,
    hkl_grid,
    hkl_metadata,
    config,
    device,
    dtype,
    use_stage_b_cpu_fallback=False,
    stage_a_ctx=None,
):
    """
    Build final Bragg array from Stage B telemetry (shell modifiers + Stage A frozen params).

    Extracts Stage A frozen parameters and Stage B shell modifiers from telemetry,
    applies modifiers to HKL grid, and regenerates full Bragg image.

    Args:
        telemetry_a: RefinementTelemetry instance or dict with Stage A optimized param_deltas
        telemetry_b: RefinementTelemetry instance or dict with Stage B shell modifiers
        detector: dxtbx Detector object
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object
        baseline_crystal: Optional baseline dxtbx Crystal object for extracting deterministic
                          misset when `crystal` is perturbed. When provided, computes
                          U_delta = U_perturbed @ U_baseline^{-1} and adds it to the orientation
                          path as a tensor to preserve differentiability. Defaults to None.
        inputs: RefinementInputs with panel_slices, trusted_mask
        hkl_grid: torch.Tensor structure factor grid (unmodified baseline)
        hkl_metadata: dict with grid dimensions
        config: RefinementConfig with device, dtype, Stage B settings
        device: torch.device for tensor operations
        dtype: torch.dtype for tensor operations
        use_stage_b_cpu_fallback: Route computation to CPU (Stage B CPU fallback mode)
        stage_a_ctx: Optional Stage A context (detectors/simulators for warm cache)

    Returns:
        bragg_full: np.ndarray, shape [n_panels, slow, fast], final Bragg image with shell modifiers
    """
    # Route device to CPU when CPU fallback is active
    final_device = torch.device("cpu") if use_stage_b_cpu_fallback else device

    # Lazy imports to avoid circular dependencies
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from dbex.refinement.config_factories import (
        create_detector_config,
        create_crystal_config,
    )
    from dbex.nanobrag_bridge import compute_baseline_misset_deg
    # ARCH-REFACTOR-001 Phase C.7: Import shared Stage A helper from stage_a_utils
    from dbex.refinement.stage_a_utils import _clamp_log_cell_deltas, _retarget_stage_a_simulators

    # Extract param_deltas from telemetry (handle both RefinementTelemetry and dict)
    if hasattr(telemetry_a, 'param_deltas'):
        param_deltas_a = telemetry_a.param_deltas
    else:
        param_deltas_a = telemetry_a['param_deltas']

    if hasattr(telemetry_b, 'param_deltas'):
        param_deltas_b = telemetry_b.param_deltas
    else:
        param_deltas_b = telemetry_b['param_deltas']

    # Extract Stage A frozen parameters (final values)
    # Use final_device for tensor creation to respect CPU fallback mode
    log_scale = torch.tensor(param_deltas_a['log_scale']['final'], device=final_device, dtype=dtype, requires_grad=False)
    log_cell_a_delta = torch.tensor(param_deltas_a['log_cell_a_delta']['final'], device=final_device, dtype=dtype, requires_grad=False)
    log_cell_b_delta = torch.tensor(param_deltas_a['log_cell_b_delta']['final'], device=final_device, dtype=dtype, requires_grad=False)
    log_cell_c_delta = torch.tensor(param_deltas_a['log_cell_c_delta']['final'], device=final_device, dtype=dtype, requires_grad=False)
    angle_alpha_raw = torch.tensor(param_deltas_a['angle_alpha_raw']['final'], device=final_device, dtype=dtype, requires_grad=False)
    angle_beta_raw = torch.tensor(param_deltas_a['angle_beta_raw']['final'], device=final_device, dtype=dtype, requires_grad=False)
    angle_gamma_raw = torch.tensor(param_deltas_a['angle_gamma_raw']['final'], device=final_device, dtype=dtype, requires_grad=False)

    # Extract misset from Stage A (this is the delta, not frozen in Stage B inline code but added to baseline)
    misset_xyz_deg_delta = param_deltas_a['misset_xyz_deg']['delta']
    misset_xyz_deg = torch.tensor(misset_xyz_deg_delta, device=final_device, dtype=dtype, requires_grad=False)

    # Check Stage B mode (per-reflection or shell)
    # Per-reflection mode doesn't have shell_edges/shell_indices
    stage_b_mode = None
    if hasattr(telemetry_b, 'stage_b_mode'):
        stage_b_mode = telemetry_b.stage_b_mode
    elif isinstance(telemetry_b, dict) and 'stage_b_mode' in telemetry_b:
        stage_b_mode = telemetry_b['stage_b_mode']

    # Extract shell metadata from Stage B telemetry (shell mode only)
    if stage_b_mode == "per_reflection":
        # Per-reflection mode: no shell metadata, skip shell modifier application
        shell_edges = None
        shell_indices = None
        n_shells = 0
        shell_modifiers_final = None
    else:
        # Shell mode: extract shell metadata and modifiers
        # Use final_device for tensor creation to respect CPU fallback mode
        if hasattr(telemetry_b, 'shell_edges'):
            shell_edges = torch.tensor(telemetry_b.shell_edges, device=final_device, dtype=dtype)
            shell_indices = torch.tensor(telemetry_b.shell_indices, device=final_device, dtype=torch.long)
            n_shells = telemetry_b.n_shells
        else:
            shell_edges = torch.tensor(telemetry_b['shell_edges'], device=final_device, dtype=dtype)
            shell_indices = torch.tensor(telemetry_b['shell_indices'], device=final_device, dtype=torch.long)
            n_shells = telemetry_b['n_shells']

        # Extract shell modifiers from Stage B param_deltas
        shell_modifiers_final = torch.zeros(n_shells, device=final_device, dtype=dtype)
        for shell_idx in range(n_shells):
            # Find the shell modifier key in param_deltas_b
            shell_key = None
            for key in param_deltas_b.keys():
                if key.startswith(f'shell_{shell_idx}_modifier'):
                    shell_key = key
                    break
            if shell_key is None:
                raise RuntimeError(f"Missing shell_{shell_idx}_modifier in Stage B telemetry param_deltas")
            shell_modifiers_final[shell_idx] = param_deltas_b[shell_key]['final']

    # Get n_panels and panel_shape
    n_panels = len(detector)
    panel_shape = inputs.target.shape[1:]  # (slow, fast)

    # Compute baseline misset if baseline_crystal provided (matches inline path lines 3115-3120)
    # Use final_device for tensor creation to respect CPU fallback mode
    baseline_misset_deg_tensor = compute_baseline_misset_deg(
        crystal,
        baseline_crystal,
        device=final_device,
        dtype=dtype,
    )

    # Apply Stage A cell perturbations
    cell_params = crystal.get_unit_cell().parameters()
    log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
        log_cell_a_delta,
        log_cell_b_delta,
        log_cell_c_delta,
        getattr(config, "log_cell_max_delta", 1.0),
    )
    cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
    cell_b_tensor = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
    cell_c_tensor = cell_params[2] * torch.exp(log_cell_c_delta_clamped)

    max_angle_delta = 10.0  # degrees
    cell_alpha_tensor = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
    cell_beta_tensor = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
    cell_gamma_tensor = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

    # Apply shell modifiers to HKL grid (shell mode only; per-reflection uses base grid)
    if stage_b_mode == "per_reflection":
        # Per-reflection mode: use unmodified HKL grid (ASU modifiers applied per-reflection during forward pass)
        hkl_grid_modified = hkl_grid
    else:
        # Shell mode: apply shell modifiers to HKL grid (mirroring inline code lines 3314-3317)
        with torch.no_grad():
            hkl_grid_modified = hkl_grid.clone()
            for shell_idx in range(n_shells):
                mask = (shell_indices == shell_idx)
                hkl_grid_modified[mask] = hkl_grid[mask] * shell_modifiers_final[shell_idx]

    bragg_full = np.zeros((n_panels, *panel_shape), dtype=np.float32)

    # Build crystal overrides
    crystal_overrides = {
        'cell_a': cell_a_tensor,
        'cell_b': cell_b_tensor,
        'cell_c': cell_c_tensor,
        'cell_alpha': cell_alpha_tensor,
        'cell_beta': cell_beta_tensor,
        'cell_gamma': cell_gamma_tensor
    }

    # Compute final misset (baseline + delta if baseline provided)
    if baseline_misset_deg_tensor is not None:
        final_misset = baseline_misset_deg_tensor + misset_xyz_deg
    else:
        final_misset = misset_xyz_deg

    # Check if warm cache is enabled AND stage_a_ctx is available
    stage_b_use_warm_cache = config.enable_stage_a_warm_cache and stage_a_ctx is not None

    if stage_b_use_warm_cache:
        # Warm cache path: retarget Stage A simulators with modified crystal
        warm_crystal_config, _ = create_crystal_config(
            crystal,
            None,
            crystal_overrides=crystal_overrides,
            misset_deg_override=final_misset,
            apply_n_cells=False,
        )
        warm_crystal_model = Crystal(
            warm_crystal_config,
            beam_config=stage_a_ctx.beam_config,
            device=final_device,
            dtype=dtype,
        )
        warm_crystal_model.interpolate = True
        warm_crystal_model.hkl_data = hkl_grid_modified.to(device=final_device, dtype=dtype)
        warm_crystal_model.hkl_metadata = hkl_metadata
        _retarget_stage_a_simulators(stage_a_ctx, warm_crystal_model)

        for pid in range(n_panels):
            simulator = stage_a_ctx.simulators[pid]
            bragg_panel = simulator.run()
            log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
            bragg_scaled = bragg_panel * torch.exp(log_scale_clamped)
            bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
    else:
        # Cold path: instantiate simulators via unified factory (ARCH-FACTORY-001 Phase B.4)
        from dbex.refinement.config_factories import create_beam_config
        from dbex.refinement.helpers import create_unified_simulator
        # Transfer shell-modified HKL grid to final_device before factory invocation (CPU fallback determinism)
        hkl_grid_final = hkl_grid_modified.to(device=final_device, dtype=dtype)
        beam_config = create_beam_config(beam)
        for pid in range(n_panels):
            detector_config = create_detector_config(
                panel=detector[pid],
                beam=beam,
                trusted_mask=inputs.trusted_mask[pid]
            )
            crystal_config, _ = create_crystal_config(
                crystal, None,
                crystal_overrides=crystal_overrides,
                misset_deg_override=final_misset,
                apply_n_cells=False
            )
            # Use unified factory for forward-only reconstruction (ARCH-FACTORY-001)
            simulator, normalized_mask, sqrt_scale, metadata = create_unified_simulator(
                detector_config=detector_config,
                crystal_config=crystal_config,
                beam_config=beam_config,
                hkl_grid=hkl_grid_final,
                hkl_metadata=hkl_metadata,
                mask_array=None,  # mask already in detector_config from create_detector_config
                spot_scale_override=None,  # scale handled via log_scale parameter
                device=final_device,
                dtype=dtype,
                calibration_metadata=getattr(config, 'calibration_metadata', None),
            )
            simulator.interpolate = True
            bragg_panel = simulator.run()
            log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
            bragg_scaled = bragg_panel * torch.exp(log_scale_clamped)
            bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)

    return bragg_full
