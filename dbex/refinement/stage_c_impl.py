"""
Stage C implementation helpers for detector distance offset refinement.

Extracted from dbex.nanobrag_refinement per ARCH-REFINE-001 Phase A.3.

Stage C scope (per docs/spec-db-workflow.md:62-65):
- Parameters: per-panel detector distance offsets (mm along panel normal)
- Freezes: Stage A crystal/scale/orientation parameters
- Loss: variance-weighted chi-squared with PHYSICS-LOSS-001/002 telemetry
- Warm cache: PERF-WARM-006/013 retarget cached Stage A detectors/simulators

Exports:
- _retarget_stage_a_detectors: Helper to update cached detector models with distance offsets
- _build_stage_c_params: Initialize Stage C parameters and optimizer
- _build_stage_c_lbfgs_closure: Build LBFGS closure for detector refinement
- _run_stage_c_lbfgs: Execute Stage C optimization and telemetry packaging
"""

import math
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch

# Import Stage A helpers for shared utilities
from dbex.refinement.stage_a_impl import (
    vec_to_unit_quaternion,
    quaternion_to_xyz_euler,
    StageAContext,
    _clamp_log_cell_deltas,
    _get_sigma_floor_sq_tensor,
    _retarget_stage_a_simulators,
    _compute_panel_loss,
)

from dbex.physics.loss import _compute_variance_weighted_loss


def _retarget_stage_a_detectors(
    stage_a_ctx: StageAContext,
    distance_deltas_mm: Dict[int, torch.Tensor],
    device: torch.device,
    dtype: torch.dtype
) -> None:
    """
    Retarget cached Stage A detector models with distance offsets for Stage C.

    Mutates stage_a_ctx in place by:
    1. Updating detector configs with new distances (baseline + delta)
    2. Rebuilding Detector models with updated configs
    3. Updating Simulator references to use new detectors

    This enables Stage C warm-cache path to reuse Stage A simulator/HKL caches
    while varying only detector distances (PERF-WARM-013).

    GRADIENT-004: Keeps distance offsets as tensors (no .item() conversion)
    so autograd graph remains intact for Stage C LBFGS optimization.

    Args:
        stage_a_ctx: StageAContext with cached detector_models/simulators
        distance_deltas_mm: Dict mapping panel_id to distance offset tensor (mm)
        device: torch device for Detector model instantiation
        dtype: torch dtype for Detector model instantiation
    """
    from nanobrag_torch.models import Detector

    for pid, delta_mm in distance_deltas_mm.items():
        if pid >= len(stage_a_ctx.detector_models):
            continue

        # Get baseline distance and apply offset
        # Convert baseline to tensor on correct device/dtype before addition (GRADIENT-004)
        baseline_distance_mm = stage_a_ctx.baseline_distance_mm[pid]
        baseline_tensor = torch.tensor(baseline_distance_mm, device=device, dtype=dtype)
        new_distance_mm = baseline_tensor + delta_mm

        # Clone detector config and update distance
        # (DetectorConfig is a dataclass, shallow copy is sufficient)
        detector_config = stage_a_ctx.detector_configs[pid]
        detector_config.distance_mm = new_distance_mm

        # Rebuild detector model with updated config
        detector_model = Detector(detector_config, device=device, dtype=dtype)

        # Update stage_a_ctx references (mutate in place)
        stage_a_ctx.detector_models[pid] = detector_model

        # Update the detector reference in the simulator
        # NOTE: Simulators have a .detector attribute that we update
        if hasattr(stage_a_ctx.simulators[pid], 'detector'):
            stage_a_ctx.simulators[pid].detector = detector_model


def _build_stage_c_params(
    config: 'RefinementConfig',
    device: torch.device,
    dtype: torch.dtype,
    n_panels: int,
    baseline_detector: Optional[Any],  # dxtbx.model.Detector
    detector: Any,  # dxtbx.model.Detector
    sampled_panel_ids: List[int],
    panel_slices: List[Tuple[int, int, int, int, int]],
    stage_a_ctx: Optional['StageAContext'],
    sigma_floor_sq_cache: Dict[str, torch.Tensor],
    params: List[torch.Tensor],  # Stage A params to freeze
    stage_a_telemetry: Dict[str, Any]  # Stage A telemetry for ROI mode check (ARCH-REFINE-001)
) -> Dict[str, Any]:
    """
    Initialize Stage C detector distance offset parameters and optimizer.

    Stage C refines per-panel translations along detector normal (distance offset)
    with crystal orientation/cell frozen from Stage A.

    Returns dict with keys:
        - 'distance_offset_raw': torch.Tensor (n_panels,) trainable parameter
        - 'stage_c_params': List[torch.Tensor] (optimizer params)
        - 'stage_c_optimizer': torch.optim.LBFGS
        - 'baseline_detector_distances': Optional[List[float]] (mm per panel)
        - 'stage_c_use_warm_cache': bool
        - 'stage_c_cache_mode': str ('warm' or 'cold')
        - 'stage_c_roi_mode_active': bool
        - 'stage_c_roi_mode_label': str ('roi' or 'panel')
        - 'stage_c_roi_count_total': int
        - 'stage_c_roi_count_sampled': int
        - 'roi_slices_by_pid': Dict[int, List[Tuple[int, int, int, int]]]
        - 'force_panel_validation': bool (REFINE-011: bypass ROI for full validations when True)
        - 'perf_closure_evals_c': List[int] (mutable counter)
        - 'perf_validation_runs_c': List[int] (mutable counter)
        - 'perf_forward_times_ms_c': List[float] (mutable accumulator)
        - 'loss_trace_sample_c': List[float]
        - 'loss_trace_full_c': List[float]
        - 'best_loss_full_c': Tuple[float, int] (value, iteration)
        - 'best_params_snapshot_c': Optional[List[torch.Tensor]]
        - 'iteration_count_c': List[int] (mutable counter)
        - 'chi_squared_trace_sample_c': List[float]
        - 'chi_squared_trace_full_c': List[float]
        - 'chi_squared_best_c': Tuple[float, int]
        - 'masked_mse_trace_sample_c': List[float]
        - 'masked_mse_trace_full_c': List[float]
        - 'masked_mse_best_c': Tuple[float, int]
        - 'variance_floor_clamped_pixels_c': List[int]
        - 'variance_floor_masked_pixels_c': List[int]
        - 'sigma_floor_sq_tensor_stage_c': torch.Tensor
    """
    # Compute baseline_detector_distances for Stage C telemetry (TORCH-REFINE-003)
    # This is used to report initial detector offsets relative to nominal geometry
    baseline_detector_distances = None
    if baseline_detector is not None:
        baseline_detector_distances = [
            baseline_detector[pid].get_directed_distance() for pid in range(n_panels)
        ]

    # Freeze Stage A parameters (no grad)
    for p in params:
        p.requires_grad = False

    # Initialize per-panel distance offsets (mm along panel normal)
    # Start at zero (identity), bounded by tanh to ±max_distance_delta_mm
    distance_offset_raw = torch.zeros(n_panels, device=device, dtype=dtype, requires_grad=True)

    stage_c_params = [distance_offset_raw]
    # PERF-WARM-SIM-001: Stage C warm cache mirrors Stage B logic (ARCH-REFINE-001 auto-panel fix)
    # Only check stage_a_ctx existence and warm cache config flag (device/dtype always match config)
    stage_c_use_warm_cache = (
        stage_a_ctx is not None
        and config.enable_stage_a_warm_cache
    )
    stage_c_cache_mode = "warm" if stage_c_use_warm_cache else "cold"
    perf_closure_evals_c = [0]
    perf_validation_runs_c = [0]
    perf_forward_times_ms_c: List[float] = []
    roi_slices_by_pid: Dict[int, List[Tuple[int, int, int, int]]] = defaultdict(list)
    for pid, bbox in panel_slices:
        roi_slices_by_pid[int(pid)].append(tuple(int(v) for v in bbox))
    # ARCH-REFINE-001, REFINE-010: Stage C ROI mode mirrors Stage A's actual ROI mode
    # (from telemetry), not the config flag, to support auto-panel threshold
    stage_a_used_roi_mode = (stage_a_telemetry.get("roi_mode") == "roi")

    # REFINE-011: Extract Stage A validation scope to control Stage C full validations
    # When Stage A used panel-mode validations, Stage C full validations must also use panel mode
    # to ensure chi² measurements are comparable (REFINE-007 non-regression gate)
    stage_a_perf_counters = stage_a_telemetry.get('perf_counters', {})
    stage_a_validation_scope = stage_a_perf_counters.get('validation_scope', 'roi')
    force_panel_validation = (stage_a_validation_scope == 'panel')

    # REFINE-012 (revised 2025-12-01T200900Z): Re-enable ROI closures while keeping
    # panel validations. ROI closures optimize via ROI minibatching; validation_scope
    # forces panel mode independently per REFINE-011/012.
    stage_c_roi_mode_active = (
        stage_c_use_warm_cache
        and stage_a_used_roi_mode
        and len(roi_slices_by_pid) > 0
    )

    # Compute roi_mode_reason for telemetry provenance (REFINE-012 extension)
    # Only report reason when ROI mode is disabled; otherwise use empty string
    if not stage_c_roi_mode_active:
        if not stage_c_use_warm_cache:
            roi_mode_reason = "warm_cache_disabled"
        elif not stage_a_used_roi_mode:
            roi_mode_reason = "stage_a_panel_mode"
        elif len(roi_slices_by_pid) == 0:
            roi_mode_reason = "no_rois"
        else:
            roi_mode_reason = "unknown"  # should not happen
    else:
        roi_mode_reason = ""  # ROI mode active, no reason needed

    stage_c_roi_mode_label = "roi" if stage_c_roi_mode_active else "panel"

    # REFINE-011 extension: validation_scope is independent from closure ROI mode
    # Full validations MUST use panel mode whenever Stage A forced panel validations,
    # even when closures use ROI minibatching (spec-db-workflow.md:127)
    validation_scope = "panel" if force_panel_validation else stage_c_roi_mode_label
    sampled_pid_set = set(sampled_panel_ids)
    if stage_c_roi_mode_active:
        stage_c_roi_count_total = sum(len(bboxes) for bboxes in roi_slices_by_pid.values())
        stage_c_roi_count_sampled = sum(len(roi_slices_by_pid.get(pid, [])) for pid in sampled_pid_set)
    else:
        # REFINE-010: Report canonical ROI count even in panel mode (mirrors Stage A/B telemetry)
        stage_c_roi_count_total = len(panel_slices)
        stage_c_roi_count_sampled = len(panel_slices)

    # Setup LBFGS optimizer for Stage C
    stage_c_optimizer = torch.optim.LBFGS(
        stage_c_params,
        history_size=config.history_size,
        max_iter=config.max_iter,
        tolerance_grad=config.tolerance_grad,
        tolerance_change=config.tolerance_change,
        line_search_fn="strong_wolfe"
    )

    # Telemetry accumulators for Stage C
    loss_trace_sample_c = []
    loss_trace_full_c = []
    best_loss_full_c = (float('inf'), -1)
    best_params_snapshot_c = None
    iteration_count_c = [0]

    # PHYSICS-LOSS-001: Dual metric tracking (chi_squared + masked_mse)
    chi_squared_trace_sample_c = []
    chi_squared_trace_full_c = []
    chi_squared_best_c = (float('inf'), -1)
    masked_mse_trace_sample_c = []
    masked_mse_trace_full_c = []
    masked_mse_best_c = (float('inf'), -1)

    # PHYSICS-LOSS-002: Variance floor clamp statistics for Stage C
    variance_floor_clamped_pixels_c = [0]  # Total pixels where floor engaged
    variance_floor_masked_pixels_c = [0]  # Total masked pixels evaluated
    sigma_floor_sq_tensor_stage_c = _get_sigma_floor_sq_tensor(
        sigma_floor_sq_cache, device, dtype, config.sigma_floor_value
    )

    return {
        'distance_offset_raw': distance_offset_raw,
        'stage_c_params': stage_c_params,
        'stage_c_optimizer': stage_c_optimizer,
        'baseline_detector_distances': baseline_detector_distances,
        'stage_c_use_warm_cache': stage_c_use_warm_cache,
        'stage_c_cache_mode': stage_c_cache_mode,
        'stage_c_roi_mode_active': stage_c_roi_mode_active,
        'stage_c_roi_mode_label': stage_c_roi_mode_label,
        'stage_c_roi_count_total': stage_c_roi_count_total,
        'stage_c_roi_count_sampled': stage_c_roi_count_sampled,
        'roi_slices_by_pid': roi_slices_by_pid,
        'force_panel_validation': force_panel_validation,  # REFINE-011: For Stage C full validation bypass
        'roi_mode_reason': roi_mode_reason,  # REFINE-012: Provenance tag for ROI-mode decision
        'validation_scope': validation_scope,  # REFINE-011/012: Independent from closure mode (panel when forced)
        'perf_closure_evals_c': perf_closure_evals_c,
        'perf_validation_runs_c': perf_validation_runs_c,
        'perf_forward_times_ms_c': perf_forward_times_ms_c,
        'loss_trace_sample_c': loss_trace_sample_c,
        'loss_trace_full_c': loss_trace_full_c,
        'best_loss_full_c': best_loss_full_c,
        'best_params_snapshot_c': best_params_snapshot_c,
        'iteration_count_c': iteration_count_c,
        'chi_squared_trace_sample_c': chi_squared_trace_sample_c,
        'chi_squared_trace_full_c': chi_squared_trace_full_c,
        'chi_squared_best_c': chi_squared_best_c,
        'masked_mse_trace_sample_c': masked_mse_trace_sample_c,
        'masked_mse_trace_full_c': masked_mse_trace_full_c,
        'masked_mse_best_c': masked_mse_best_c,
        'variance_floor_clamped_pixels_c': variance_floor_clamped_pixels_c,
        'variance_floor_masked_pixels_c': variance_floor_masked_pixels_c,
        'sigma_floor_sq_tensor_stage_c': sigma_floor_sq_tensor_stage_c,
    }


def _build_stage_c_lbfgs_closure(
    param_values: Dict[str, Any],
    telemetry_state: Dict[str, Any],
    stage_c_context: Dict[str, Any],
    detector: Any,  # dxtbx.model.Detector
    beam: Any,  # dxtbx.model.Beam
    inputs: Any,  # RefinementInputs
    config: 'RefinementConfig',
    sigma_floor_sq_cache: Dict[str, torch.Tensor],
    device: torch.device,
    dtype: torch.dtype,
    crystal: Any,  # dxtbx.model.Crystal (Stage A final params)
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict[str, Any],
    stage_a_ctx: Optional['StageAContext'],
    sampled_panel_ids: List[int]
) -> Tuple[Callable[[List[int], bool], Tuple[torch.Tensor, torch.Tensor]], Callable[[], torch.Tensor]]:
    """
    Build Stage C LBFGS closure for detector distance refinement.

    Returns tuple of (compute_loss_stage_c, closure_stage_c) with captured lexical scope
    for ~25 nonlocal variables extracted from input dicts.

    Both nested functions implement variance-weighted chi-squared loss with Stage C
    detector distance adjustments, freezing Stage A crystal parameters.

    Returns:
        Tuple of:
        - compute_loss_stage_c: Callable[[panel_ids, is_full, force_panel_eval], (chi_squared, mse)]
        - closure_stage_c: Callable[[], chi_squared_loss] (LBFGS closure contract)
    """
    # Extract from param_values dict
    distance_offset_raw = param_values['distance_offset_raw']
    stage_c_params = param_values['stage_c_params']
    stage_c_optimizer = param_values['stage_c_optimizer']
    log_scale = param_values['log_scale']
    log_scale_baseline = param_values.get('log_scale_baseline')  # REFINE-015: Stage A baseline for clamp logic
    log_cell_a_delta = param_values.get('log_cell_a_delta')
    log_cell_b_delta = param_values.get('log_cell_b_delta')
    log_cell_c_delta = param_values.get('log_cell_c_delta')
    angle_alpha_raw = param_values.get('angle_alpha_raw')
    angle_beta_raw = param_values.get('angle_beta_raw')
    angle_gamma_raw = param_values.get('angle_gamma_raw')
    orientation_vec = param_values.get('orientation_vec')
    baseline_misset_deg_tensor = param_values.get('baseline_misset_deg_tensor')
    misset_deg_for_crystal = param_values.get('misset_deg_for_crystal')
    target_t = param_values['target_t']
    loss_mask_t = param_values['loss_mask_t']
    sigma_readout_t = param_values['sigma_readout_t']

    # Extract from telemetry_state dict
    perf_closure_evals_c = telemetry_state['perf_closure_evals_c']
    perf_validation_runs_c = telemetry_state['perf_validation_runs_c']
    perf_forward_times_ms_c = telemetry_state['perf_forward_times_ms_c']
    loss_trace_sample_c = telemetry_state['loss_trace_sample_c']
    loss_trace_full_c = telemetry_state['loss_trace_full_c']
    best_loss_full_c = telemetry_state['best_loss_full_c']
    best_params_snapshot_c = telemetry_state['best_params_snapshot_c']
    iteration_count_c = telemetry_state['iteration_count_c']
    chi_squared_trace_sample_c = telemetry_state['chi_squared_trace_sample_c']
    chi_squared_trace_full_c = telemetry_state['chi_squared_trace_full_c']
    chi_squared_best_c = telemetry_state['chi_squared_best_c']
    masked_mse_trace_sample_c = telemetry_state['masked_mse_trace_sample_c']
    masked_mse_trace_full_c = telemetry_state['masked_mse_trace_full_c']
    masked_mse_best_c = telemetry_state['masked_mse_best_c']
    variance_floor_clamped_pixels_c = telemetry_state['variance_floor_clamped_pixels_c']
    variance_floor_masked_pixels_c = telemetry_state['variance_floor_masked_pixels_c']
    sigma_floor_sq_tensor_stage_c = telemetry_state['sigma_floor_sq_tensor_stage_c']

    # Extract from stage_c_context dict
    stage_c_use_warm_cache = stage_c_context['stage_c_use_warm_cache']
    stage_c_cache_mode = stage_c_context['stage_c_cache_mode']
    stage_c_roi_mode_active = stage_c_context['stage_c_roi_mode_active']
    stage_c_roi_mode_label = stage_c_context['stage_c_roi_mode_label']
    roi_slices_by_pid = stage_c_context['roi_slices_by_pid']
    force_panel_validation = stage_c_context['force_panel_validation']  # REFINE-011
    n_panels = len(detector)

    def compute_loss_stage_c(panel_ids: List[int], is_full: bool = False, force_panel_eval: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute variance-weighted chi-squared loss with Stage C detector distance adjustments.

        Uses Stage A's final crystal parameters (frozen) and varies per-panel distances.

        Args:
            panel_ids: List of panel indices to evaluate
            is_full: If True, this is a validation run (records perf_validation_runs_c)
            force_panel_eval: If True, bypass ROI mode even if stage_c_roi_mode_active (REFINE-011)

        Returns:
            Tuple of (chi_squared_loss, masked_mse_loss): Both scalar tensors for telemetry
        """
        # Lazy imports inside nested function (device-specific, conditional)
        from nanobrag_torch.models import Detector, Crystal
        from nanobrag_torch.simulator import Simulator
        from dbex.nanobrag_bridge import create_detector_config, create_crystal_config

        t0 = time.perf_counter()
        if is_full:
            perf_validation_runs_c[0] += 1
        bragg_panels = []
        target_panels = []
        mask_panels = []
        sigma_panels = []

        # PERF-WARM-SIM-001 Phase D: Use frozen Stage A final cell parameters
        # Stage C spec (docs/spec-db-workflow.md:62-65): Fixed crystal, scale, Fhkl
        stage_a_final_cell = param_values.get('stage_a_final_cell')
        if stage_a_final_cell is not None:
            # Frozen values from Stage A (no recomputation)
            perturbed_cell_a = stage_a_final_cell['cell_a']
            perturbed_cell_b = stage_a_final_cell['cell_b']
            perturbed_cell_c = stage_a_final_cell['cell_c']
            perturbed_alpha = stage_a_final_cell['alpha']
            perturbed_beta = stage_a_final_cell['beta']
            perturbed_gamma = stage_a_final_cell['gamma']
        else:
            # Fallback: recompute from baseline (backward compatibility)
            cell_params = crystal.get_unit_cell().parameters()
            log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
                log_cell_a_delta,
                log_cell_b_delta,
                log_cell_c_delta,
                getattr(config, "log_cell_max_delta", 1.0),
            )
            perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
            perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
            perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta_clamped)

            max_angle_delta = 10.0
            perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
            perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
            perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

        max_orientation_deg = 3.0
        bounded_orientation_vec = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
        quat = vec_to_unit_quaternion(bounded_orientation_vec)
        misset_xyz_deg = quaternion_to_xyz_euler(quat)

        if baseline_misset_deg_tensor is not None:
            misset_xyz_deg = misset_xyz_deg + baseline_misset_deg_tensor

        crystal_overrides = {
            'cell_a': perturbed_cell_a,
            'cell_b': perturbed_cell_b,
            'cell_c': perturbed_cell_c,
            'cell_alpha': perturbed_alpha,
            'cell_beta': perturbed_beta,
            'cell_gamma': perturbed_gamma
        }
        crystal_config, _ = create_crystal_config(
            crystal,
            None,
            crystal_overrides=crystal_overrides,
            misset_deg_override=misset_deg_for_crystal
        )

        crystal_model = Crystal(crystal_config, device=device, dtype=dtype)
        crystal_model.interpolate = config.enable_hkl_interpolation
        crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
        crystal_model.hkl_metadata = hkl_metadata

        # PERF-WARM-013: Build distance deltas dict once before panel loop for retargeting
        if stage_c_use_warm_cache:
            distance_deltas_mm = {}
            for pid in panel_ids:
                bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
                # Keep as tensor to preserve autograd graph (GRADIENT-004)
                distance_deltas_mm[pid] = bounded_offset

            # Retarget cached detectors with distance offsets (mutates stage_a_ctx in place)
            _retarget_stage_a_detectors(
                stage_a_ctx=stage_a_ctx,
                distance_deltas_mm=distance_deltas_mm,
                device=device,
                dtype=dtype
            )

            # PERF-WARM-SIM-001: Attach frozen crystal_model to all simulators (Stage A/C parity)
            # This ensures Stage C uses the canonical Stage A final crystal parameters
            _retarget_stage_a_simulators(stage_a_ctx, crystal_model)

        # REFINE-011: Bypass ROI mode for full validations when Stage A used panel-mode validations
        # This ensures Stage C chi² measurements are comparable to Stage A baseline (REFINE-007)
        use_roi_mode_this_eval = stage_c_roi_mode_active and not (is_full and force_panel_eval)

        if use_roi_mode_this_eval:
            # ROI mode: Build outputs for each panel, then slice ROIs
            bragg_panels = []
            target_panels = []
            mask_panels = []
            sigma_panels = []
            for pid in panel_ids:
                panel = detector[pid]

                if stage_c_use_warm_cache:
                    # Warm path: reuse retargeted detector/simulator from stage_a_ctx
                    # PERF-WARM-SIM-001: crystal already attached via _retarget_stage_a_simulators above
                    simulator = stage_a_ctx.simulators[pid]
                else:
                    # Cold path: instantiate fresh
                    bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
                    baseline_distance_mm = panel.get_directed_distance()
                    distance_mm_override = baseline_distance_mm + bounded_offset

                    detector_config = create_detector_config(
                        panel=panel,
                        beam=beam,
                        trusted_mask=inputs.trusted_mask[pid],
                        distance_mm_override=distance_mm_override
                    )
                    if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                        detector_config.mask_array = torch.tensor(
                            detector_config.mask_array, dtype=torch.float32, device=device
                        )
                    detector_model = Detector(detector_config, device=device, dtype=dtype)
                    simulator = Simulator(detector=detector_model, crystal=crystal_model, device=device, dtype=dtype)

                panel_bragg = simulator.run()

                bragg_panels.append(panel_bragg)
                target_panels.append(target_t[pid])
                mask_panels.append(loss_mask_t[pid])
                sigma_panels.append(sigma_readout_t[pid])

            # REFINE-015: Apply Stage A's log-scale clamp logic in Stage C
            # When calibration metadata supplied the baseline:
            #   log_scale_clamped = log_scale_baseline + clamp(delta, ±config.log_scale_max_delta)
            # Otherwise (uncalibrated):
            #   log_scale_clamped = clamp(delta, ±config.log_scale_max_delta_uncalibrated)
            max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
            delta_bound = config.log_scale_max_delta if log_scale_baseline is not None else max_delta_uncal
            if log_scale_baseline is not None:
                log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
                log_scale_clamped = log_scale_baseline + log_scale_delta_clamped
            else:
                # Absolute clamp when no baseline is available
                log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)

            panel_outputs = {pid: panel for pid, panel in zip(panel_ids, bragg_panels)}
            target_outputs = {pid: panel for pid, panel in zip(panel_ids, target_panels)}
            mask_outputs = {pid: panel for pid, panel in zip(panel_ids, mask_panels)}
            sigma_outputs = {pid: panel for pid, panel in zip(panel_ids, sigma_panels)}

            # ROI mode loss computation:
            chi_squared_accum = torch.zeros((), device=device, dtype=dtype)
            mse_numerator_accum = torch.zeros((), device=device, dtype=dtype)
            masked_pixels_total = 0
            clamped_pixels_total = 0
            for pid in panel_ids:
                roi_list = roi_slices_by_pid.get(pid, [])
                if not roi_list:
                    continue
                panel_output = panel_outputs[pid]
                target_panel = target_outputs[pid]
                mask_panel = mask_outputs[pid]
                sigma_panel = sigma_outputs[pid]
                for bbox in roi_list:
                    x0, x1, y0, y1 = bbox
                    slow_slice = slice(y0, y1)
                    fast_slice = slice(x0, x1)
                    bragg_roi = panel_output[slow_slice, fast_slice] * torch.exp(log_scale_clamped)
                    target_roi = target_panel[slow_slice, fast_slice]
                    mask_roi = mask_panel[slow_slice, fast_slice]
                    # REFINE-016: Apply trusted mask parity with Stage A (dbex/refinement/stage_a_impl.py:1348-1350)
                    # Warm path uses precomputed trusted_masks_t; cold path tensorizes inputs.trusted_mask on demand
                    if stage_a_ctx is not None and stage_a_ctx.trusted_masks_t is not None:
                        trusted_slice = stage_a_ctx.trusted_masks_t[pid, slow_slice, fast_slice]
                        mask_roi = torch.logical_and(mask_roi, trusted_slice)
                    elif not stage_c_use_warm_cache and inputs.trusted_mask is not None and inputs.trusted_mask[pid] is not None:
                        trusted_mask_np = inputs.trusted_mask[pid]
                        trusted_mask_t = torch.tensor(trusted_mask_np, dtype=torch.bool, device=device)
                        trusted_slice = trusted_mask_t[slow_slice, fast_slice]
                        mask_roi = torch.logical_and(mask_roi, trusted_slice)
                    sigma_roi = sigma_panel[slow_slice, fast_slice]
                    (
                        chi_roi,
                        mse_roi,
                        masked_pixels_roi,
                        clamped_pixels_roi,
                    ) = _compute_variance_weighted_loss(
                        bragg_roi,
                        target_roi,
                        mask_roi,
                        sigma_roi,
                        sigma_floor_sq_tensor_stage_c,
                    )
                    chi_squared_accum = chi_squared_accum + chi_roi
                    mse_numerator_accum = mse_numerator_accum + mse_roi * masked_pixels_roi
                    masked_pixels_total += masked_pixels_roi
                    clamped_pixels_total += clamped_pixels_roi

            if masked_pixels_total > 0:
                masked_mse_loss = mse_numerator_accum / masked_pixels_total
            else:
                masked_mse_loss = mse_numerator_accum
            chi_squared_loss = chi_squared_accum
            variance_floor_clamped_pixels_c[0] += clamped_pixels_total
            variance_floor_masked_pixels_c[0] += masked_pixels_total
        else:
            # Panel mode: Use shared Stage A/C helper for chi² parity (PERF-WARM-SIM-001)
            # REFINE-015: Apply Stage A's log-scale clamp logic in Stage C
            max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
            delta_bound = config.log_scale_max_delta if log_scale_baseline is not None else max_delta_uncal
            if log_scale_baseline is not None:
                log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
                log_scale_clamped = log_scale_baseline + log_scale_delta_clamped
            else:
                log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)

            # Call shared helper (simulators already retargeted with distance offsets and crystal attached)
            # misset_xyz_deg computed above at line 430; crystal_overrides built at line 435
            # For warm mode, use stage_a_ctx.beam_config; for cold mode, helper will need to build it
            (
                chi_squared_loss,
                masked_mse_loss,
                masked_pixels_stage_c,
                clamped_pixels_stage_c,
            ) = _compute_panel_loss(
                panel_ids=panel_ids,
                stage_a_ctx=stage_a_ctx,
                detector=detector,
                beam=beam,
                crystal=crystal,
                crystal_overrides=crystal_overrides,
                misset_deg_for_crystal=misset_xyz_deg,
                beam_config_for_run=stage_a_ctx.beam_config if stage_a_ctx is not None else None,
                hkl_grid=hkl_grid,
                hkl_metadata=hkl_metadata,
                config=config,
                log_scale_clamped=log_scale_clamped,
                target_t=target_t,
                loss_mask_t=loss_mask_t,
                sigma_readout_t=sigma_readout_t,
                sigma_floor_sq_tensor=sigma_floor_sq_tensor_stage_c,
                device=device,
                dtype=dtype,
                trusted_mask_array=inputs.trusted_mask if not stage_c_use_warm_cache else None,
            )
            variance_floor_clamped_pixels_c[0] += clamped_pixels_stage_c
            variance_floor_masked_pixels_c[0] += masked_pixels_stage_c
        perf_forward_times_ms_c.append((time.perf_counter() - t0) * 1000.0)

        return chi_squared_loss, masked_mse_loss

    def closure_stage_c():
        """LBFGS closure for Stage C detector refinement."""
        stage_c_optimizer.zero_grad()
        perf_closure_evals_c[0] += 1

        # Compute loss on sampled ROIs
        chi_squared_loss, mse_loss = compute_loss_stage_c(sampled_panel_ids, is_full=False)

        # Backward pass
        chi_squared_loss.backward()

        # Check for NaN/Inf gradients
        for p in stage_c_params:
            if p.grad is not None and (torch.isnan(p.grad).any() or torch.isinf(p.grad).any()):
                raise RuntimeError(f"NaN/Inf gradient detected in Stage C parameter {p}")

        # Record loss
        loss_trace_sample_c.append(float(chi_squared_loss.item()))
        # PHYSICS-LOSS-001: Record both metrics
        chi_squared_trace_sample_c.append(float(chi_squared_loss.item()))
        masked_mse_trace_sample_c.append(float(mse_loss.item()))

        # Periodic full validation
        if iteration_count_c[0] % config.full_validation_interval == 0:
            with torch.no_grad():
                # REFINE-011: Use panel mode for full validations when Stage A used panel mode
                full_chi_squared_c, full_mse_c = compute_loss_stage_c(
                    list(range(n_panels)), is_full=True, force_panel_eval=force_panel_validation
                )
                loss_trace_full_c.append((iteration_count_c[0], float(full_chi_squared_c.item())))
                # PHYSICS-LOSS-001: Record both metrics
                chi_squared_trace_full_c.append((iteration_count_c[0], float(full_chi_squared_c.item())))
                masked_mse_trace_full_c.append((iteration_count_c[0], float(full_mse_c.item())))

                # Update best snapshot
                nonlocal best_loss_full_c, best_params_snapshot_c, chi_squared_best_c, masked_mse_best_c
                # PHYSICS-LOSS-001: Track best for both metrics
                if full_chi_squared_c.item() < chi_squared_best_c[0]:
                    chi_squared_best_c = (float(full_chi_squared_c.item()), iteration_count_c[0])
                    best_loss_full_c = (float(full_chi_squared_c.item()), iteration_count_c[0])  # Deprecated legacy field
                    best_params_snapshot_c = {
                        'distance_offset_raw': distance_offset_raw.detach().cpu().tolist()
                    }
                    # REFINE-013: Persist best tuples to telemetry_state so _run_stage_c_lbfgs can see them
                    telemetry_state['chi_squared_best_c'] = chi_squared_best_c
                    telemetry_state['best_loss_full_c'] = best_loss_full_c
                    telemetry_state['best_params_snapshot_c'] = best_params_snapshot_c
                if full_mse_c.item() < masked_mse_best_c[0]:
                    masked_mse_best_c = (float(full_mse_c.item()), iteration_count_c[0])
                    # REFINE-013: Persist masked_mse_best_c to telemetry_state
                    telemetry_state['masked_mse_best_c'] = masked_mse_best_c

        iteration_count_c[0] += 1
        return chi_squared_loss

    return compute_loss_stage_c, closure_stage_c


def _run_stage_c_lbfgs(
    config: 'RefinementConfig',
    device: torch.device,
    dtype: torch.dtype,
    param_values: Dict[str, Any],
    telemetry_state: Dict[str, Any],
    stage_c_context: Dict[str, Any],
    compute_loss_stage_c: Callable,
    closure_stage_c: Callable,
    crystal,  # dxtbx Crystal
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    detector,  # dxtbx Detector
    beam,  # dxtbx Beam
    inputs,  # DataLoad (untyped to avoid import)
    canonical_baseline: Dict[str, Any],
    stage_a_ctx: Optional[StageAContext],
    n_panels: int,
) -> Dict[str, Any]:
    """
    Execute Stage C LBFGS optimization, final validation, improvement gate,
    best snapshot restore, final Bragg regeneration, and telemetry packaging.

    Returns dict with keys:
        - 'status_c': str ('ok', 'early_stop', 'error')
        - 'message_c': str
        - 'telemetry_c': RefinementTelemetry
        - 'bragg_full': np.ndarray (n_panels, slow, fast)
        - 'final_step_c': int
        - 'final_loss_value_c': float
        - 'final_mse_value_c': float
    """
    # Import RefinementTelemetry (lazy to avoid circular import at module load)
    # ARCH-REFINE-001 Phase C.1: Import from canonical location
    from dbex.refinement import RefinementTelemetry

    # Extract from param_values dict
    distance_offset_raw = param_values['distance_offset_raw']
    stage_c_params = param_values['stage_c_params']
    stage_c_optimizer = param_values['stage_c_optimizer']
    log_scale = param_values['log_scale']
    log_scale_baseline = param_values.get('log_scale_baseline')  # REFINE-015: Stage A baseline for clamp logic
    log_cell_a_delta = param_values.get('log_cell_a_delta')
    log_cell_b_delta = param_values.get('log_cell_b_delta')
    log_cell_c_delta = param_values.get('log_cell_c_delta')
    angle_alpha_raw = param_values.get('angle_alpha_raw')
    angle_beta_raw = param_values.get('angle_beta_raw')
    angle_gamma_raw = param_values.get('angle_gamma_raw')
    orientation_vec = param_values.get('orientation_vec')
    baseline_misset_deg_tensor = param_values.get('baseline_misset_deg_tensor')

    # Extract from telemetry_state dict (ALL as mutable references via list wrappers)
    chi_squared_best_c = telemetry_state['chi_squared_best_c']
    masked_mse_best_c = telemetry_state['masked_mse_best_c']
    best_params_snapshot_c = telemetry_state.get('best_params_snapshot_c')
    iteration_count_c = telemetry_state['iteration_count_c']
    loss_trace_sample_c = telemetry_state['loss_trace_sample_c']
    loss_trace_full_c = telemetry_state['loss_trace_full_c']
    chi_squared_trace_sample_c = telemetry_state['chi_squared_trace_sample_c']
    chi_squared_trace_full_c = telemetry_state['chi_squared_trace_full_c']
    masked_mse_trace_sample_c = telemetry_state['masked_mse_trace_sample_c']
    masked_mse_trace_full_c = telemetry_state['masked_mse_trace_full_c']
    variance_floor_clamped_pixels_c = telemetry_state['variance_floor_clamped_pixels_c']
    variance_floor_masked_pixels_c = telemetry_state['variance_floor_masked_pixels_c']
    perf_closure_evals_c = telemetry_state['perf_closure_evals_c']
    perf_validation_runs_c = telemetry_state['perf_validation_runs_c']
    perf_forward_times_ms_c = telemetry_state['perf_forward_times_ms_c']
    best_loss_full_c = telemetry_state['best_loss_full_c']

    # Extract from stage_c_context dict
    stage_c_use_warm_cache = stage_c_context['stage_c_use_warm_cache']
    stage_c_cache_mode = stage_c_context['stage_c_cache_mode']
    stage_c_roi_mode_label = stage_c_context['stage_c_roi_mode_label']
    stage_c_roi_count_total = stage_c_context['stage_c_roi_count_total']
    stage_c_roi_count_sampled = stage_c_context['stage_c_roi_count_sampled']
    baseline_detector_distances = stage_c_context.get('baseline_detector_distances')
    sampled_panel_ids = stage_c_context['sampled_panel_ids']
    _apply_baseline_detector_prior = stage_c_context['_apply_baseline_detector_prior']
    misset_deg_for_crystal = stage_c_context['misset_deg_for_crystal']
    force_panel_validation = stage_c_context['force_panel_validation']  # REFINE-011
    roi_mode_reason = stage_c_context['roi_mode_reason']  # REFINE-012
    validation_scope = stage_c_context['validation_scope']  # REFINE-012

    # Extract from canonical_baseline dict (needed for improvement gate)
    best_loss_full = (canonical_baseline['chi_squared'], canonical_baseline['iteration'])

    # Derived variables
    panel_shape = inputs.target.shape[1:]

    # Lazy imports (inside helper to avoid circular deps)
    from nanobrag_torch.models import Detector, Crystal
    from nanobrag_torch.simulator import Simulator
    from dbex.nanobrag_bridge import create_detector_config, create_crystal_config

    # Run Stage C LBFGS optimization
    status_c = "ok"
    message_c = ""

    try:
        # Apply baseline detector prior BEFORE LBFGS so the warm-start is captured in best snapshot
        # (REFINE-013: The rehydration after LBFGS reloads best_params_snapshot_c, which must include the prior)
        _apply_baseline_detector_prior()

        stage_c_optimizer.step(closure_stage_c)

        # REFINE-013: Rehydrate best tuples from telemetry_state after LBFGS
        # The closure updates these during optimization, but the local variables read them before the step
        chi_squared_best_c = telemetry_state['chi_squared_best_c']
        masked_mse_best_c = telemetry_state['masked_mse_best_c']
        best_loss_full_c = telemetry_state['best_loss_full_c']
        best_params_snapshot_c = telemetry_state.get('best_params_snapshot_c')

        # Assert that at least one full validation populated the best snapshot
        if chi_squared_best_c[0] >= float('inf'):
            raise RuntimeError(
                "Stage C best snapshot never recorded: chi_squared_best_c remains infinite after LBFGS. "
                "Check that full_validation_interval allows at least one periodic validation."
            )

    except Exception as e:
        status_c = "error"
        message_c = str(e)
        # Use best snapshot if available
        if best_params_snapshot_c is not None:
            distance_offset_raw.data = torch.tensor(best_params_snapshot_c['distance_offset_raw'], device=device, dtype=dtype)

    final_step_c = iteration_count_c[0]
    with torch.no_grad():
        # REFINE-011: Use panel mode for final validation when Stage A used panel mode
        candidate_final_chi2, candidate_final_mse = compute_loss_stage_c(
            list(range(n_panels)), is_full=True, force_panel_eval=force_panel_validation
        )
    candidate_loss_value_c = float(candidate_final_chi2.item())
    candidate_mse_value_c = float(candidate_final_mse.item())
    if candidate_loss_value_c < chi_squared_best_c[0]:
        chi_squared_best_c = (candidate_loss_value_c, final_step_c)
        best_loss_full_c = (candidate_loss_value_c, final_step_c)
        best_params_snapshot_c = {
            'distance_offset_raw': distance_offset_raw.detach().cpu().tolist()
        }
        # REFINE-013: Persist best tuples to telemetry_state so final telemetry reflects best snapshot
        telemetry_state['chi_squared_best_c'] = chi_squared_best_c
        telemetry_state['best_loss_full_c'] = best_loss_full_c
        telemetry_state['best_params_snapshot_c'] = best_params_snapshot_c
    if candidate_mse_value_c < masked_mse_best_c[0]:
        masked_mse_best_c = (candidate_mse_value_c, final_step_c)
        # REFINE-013: Persist masked_mse_best_c to telemetry_state
        telemetry_state['masked_mse_best_c'] = masked_mse_best_c

    # REFINE-013: Use best chi-squared from periodic validations for final telemetry
    # The best snapshot was already validated during LBFGS, so use stored values directly
    final_loss_value_c = chi_squared_best_c[0] if chi_squared_best_c[0] < float('inf') else candidate_loss_value_c
    final_mse_value_c = masked_mse_best_c[0] if masked_mse_best_c[0] < float('inf') else candidate_mse_value_c

    # REFINE-013: Reload best parameters before final trace entry
    # This ensures final Bragg regeneration uses optimal parameters, not last iterate
    if best_params_snapshot_c is not None and chi_squared_best_c[0] < float('inf'):
        distance_offset_raw.data = torch.tensor(
            best_params_snapshot_c['distance_offset_raw'],
            device=device,
            dtype=dtype,
        )

    loss_trace_full_c.append((final_step_c, final_loss_value_c))
    chi_squared_trace_full_c.append((final_step_c, final_loss_value_c))
    masked_mse_trace_full_c.append((final_step_c, final_mse_value_c))

    # Check convergence: did we achieve ≥5% improvement on top of Stage A?
    if best_loss_full[0] is not None and best_loss_full[0] > 0:
        stage_a_final_loss = best_loss_full[0]
        improvement_c = (stage_a_final_loss - final_loss_value_c) / stage_a_final_loss
        if improvement_c < config.stage_c_min_loss_improvement:
            status_c = "early_stop"
            message_c = f"Stage C improvement {improvement_c:.4%} < {config.stage_c_min_loss_improvement:.4%} (≥0.002% gate calibrated per REFINE-007)"

    # Generate final Bragg array with Stage C adjustments
    with torch.no_grad():
        bragg_full_stage_c = np.zeros((n_panels, *panel_shape), dtype=np.float32)
        cell_params = crystal.get_unit_cell().parameters()
        log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
            log_cell_a_delta,
            log_cell_b_delta,
            log_cell_c_delta,
            getattr(config, "log_cell_max_delta", 1.0),
        )
        perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
        perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
        perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta_clamped)
        max_angle_delta = 10.0
        perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
        perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
        perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta
        max_orientation_deg = 3.0
        bounded_orientation_vec = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
        quat = vec_to_unit_quaternion(bounded_orientation_vec)
        misset_xyz_deg = quaternion_to_xyz_euler(quat)

        if baseline_misset_deg_tensor is not None:
            misset_xyz_deg = misset_xyz_deg + baseline_misset_deg_tensor

        crystal_overrides = {
            'cell_a': perturbed_cell_a,
            'cell_b': perturbed_cell_b,
            'cell_c': perturbed_cell_c,
            'cell_alpha': perturbed_alpha,
            'cell_beta': perturbed_beta,
            'cell_gamma': perturbed_gamma
        }
        crystal_config, _ = create_crystal_config(
            crystal,
            None,
            crystal_overrides=crystal_overrides,
            misset_deg_override=misset_deg_for_crystal
        )
        crystal_model = Crystal(crystal_config, device=device, dtype=dtype)
        crystal_model.interpolate = config.enable_hkl_interpolation
        crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
        crystal_model.hkl_metadata = hkl_metadata

        # PERF-WARM-013: Retarget cached detectors before final reconstruction loop
        if stage_c_use_warm_cache:
            distance_deltas_mm_final = {}
            for pid in range(n_panels):
                bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
                # Keep as tensor to preserve autograd graph (GRADIENT-004)
                distance_deltas_mm_final[pid] = bounded_offset

            _retarget_stage_a_detectors(
                stage_a_ctx=stage_a_ctx,
                distance_deltas_mm=distance_deltas_mm_final,
                device=device,
                dtype=dtype
            )

        for pid in range(n_panels):
            panel = detector[pid]

            if stage_c_use_warm_cache:
                # Warm path: reuse retargeted detector/simulator from stage_a_ctx
                detector_model = stage_a_ctx.detector_models[pid]
                simulator = stage_a_ctx.simulators[pid]
                # Attach final crystal model
                simulator.crystal = crystal_model
                simulator.beam_config = stage_a_ctx.beam_config
            else:
                # Cold path: instantiate fresh (existing code, keep AS-IS)
                # Apply final bounded distance offset
                bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
                baseline_distance_mm = panel.get_directed_distance()
                distance_mm_override = baseline_distance_mm + bounded_offset

                detector_config = create_detector_config(
                    panel=panel,
                    beam=beam,
                    trusted_mask=inputs.trusted_mask[pid],
                    distance_mm_override=distance_mm_override
                )

                if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                    detector_config.mask_array = torch.tensor(
                        detector_config.mask_array, dtype=torch.float32, device=device
                    )

                detector_model = Detector(detector_config, device=device, dtype=dtype)
                simulator = Simulator(detector=detector_model, crystal=crystal_model, device=device, dtype=dtype)

            panel_bragg = simulator.run()

            # REFINE-015: Apply Stage A's log-scale clamp logic in final Stage C reconstruction
            # When calibration metadata supplied the baseline:
            #   log_scale_clamped = log_scale_baseline + clamp(delta, ±config.log_scale_max_delta)
            # Otherwise (uncalibrated):
            #   log_scale_clamped = clamp(delta, ±config.log_scale_max_delta_uncalibrated)
            max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
            delta_bound = config.log_scale_max_delta if log_scale_baseline is not None else max_delta_uncal
            if log_scale_baseline is not None:
                log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
                log_scale_clamped = log_scale_baseline + log_scale_delta_clamped
            else:
                # Absolute clamp when no baseline is available
                log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
            panel_bragg_scaled = panel_bragg * torch.exp(log_scale_clamped)
            bragg_full_stage_c[pid] = panel_bragg_scaled.cpu().numpy().astype(np.float32)

    # Assemble Stage C telemetry
    param_deltas_c = {}
    for pid in range(n_panels):
        bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
        bounded_offset_value = float(bounded_offset.item())
        initial_offset_mm = 0.0
        if baseline_detector_distances is not None:
            initial_offset_mm = detector[pid].get_directed_distance() - baseline_detector_distances[pid]
        final_offset_mm = initial_offset_mm + bounded_offset_value
        param_deltas_c[f'panel_{pid}_distance_offset_mm'] = {
            'initial': initial_offset_mm,
            'final': final_offset_mm,
            'delta': bounded_offset_value
        }

    forward_stats_c = {
        'mean': float(np.mean(perf_forward_times_ms_c)) if perf_forward_times_ms_c else 0.0,
        'min': float(np.min(perf_forward_times_ms_c)) if perf_forward_times_ms_c else 0.0,
        'max': float(np.max(perf_forward_times_ms_c)) if perf_forward_times_ms_c else 0.0,
        'total': float(np.sum(perf_forward_times_ms_c)) if perf_forward_times_ms_c else 0.0,
    }
    perf_counters_c = {
        'cache_mode': stage_c_cache_mode,
        'roi_mode': stage_c_roi_mode_label,
        'roi_mode_reason': roi_mode_reason,  # REFINE-012: Provenance for ROI-mode decision
        'validation_scope': validation_scope,  # REFINE-011/012: Independent from closure mode (panel when forced)
        'roi_count_total': stage_c_roi_count_total,
        'roi_count_sampled': stage_c_roi_count_sampled,
        'closure_evals': perf_closure_evals_c[0],
        'validation_runs': perf_validation_runs_c[0],
        'forward_time_ms': forward_stats_c,
    }

    telemetry_c = RefinementTelemetry(
        optimizer="LBFGS",
        stage="C",
        history_size=config.history_size,
        max_iter=config.max_iter,
        tolerance_grad=config.tolerance_grad,
        tolerance_change=config.tolerance_change,
        roi_sample_fraction=config.roi_sample_fraction,
        roi_count_sampled=stage_c_roi_count_sampled,
        roi_count_total=stage_c_roi_count_total,
        loss_trace_sample=loss_trace_sample_c,
        loss_trace_full=loss_trace_full_c,
        best_loss_full=best_loss_full_c,
        param_deltas=param_deltas_c,
        status=status_c,
        message=message_c,
        perf_counters=perf_counters_c,
        # PHYSICS-LOSS-001: Dual loss metrics
        chi_squared_trace_sample=chi_squared_trace_sample_c,
        chi_squared_trace_full=chi_squared_trace_full_c,
        chi_squared_best=chi_squared_best_c,
        masked_mse_trace_sample=masked_mse_trace_sample_c,
        masked_mse_trace_full=masked_mse_trace_full_c,
        masked_mse_best=masked_mse_best_c,
        sigma_readout_provenance=config.sigma_readout_provenance,
        sigma_readout_reference_value=config.sigma_readout_reference_value,
        # PHYSICS-LOSS-002: Variance floor telemetry
        variance_floor_value=config.sigma_floor_value**2,
        variance_floor_clamp_fraction=(
            float(variance_floor_clamped_pixels_c[0]) / float(variance_floor_masked_pixels_c[0])
            if variance_floor_masked_pixels_c[0] > 0 else 0.0
        ),
        canonical_stage_label=canonical_baseline["stage_label"],
        canonical_chi_squared=canonical_baseline["chi_squared"],
        canonical_chi_squared_iteration=canonical_baseline["iteration"],
        canonical_roi_count=canonical_baseline["roi_count"],
        canonical_detector_distances_mm=canonical_baseline["detector_distances_mm"],
        roi_mode=stage_c_roi_mode_label,
    )

    return {
        'status_c': status_c,
        'message_c': message_c,
        'telemetry_c': telemetry_c,
        'bragg_full': bragg_full_stage_c,
        'final_step_c': final_step_c,
        'final_loss_value_c': final_loss_value_c,
        'final_mse_value_c': final_mse_value_c,
    }
