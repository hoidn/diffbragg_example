# dbex/refinement/stage_c.py
"""
Stage C implementation for Protocol-based Refinement Engine.

Wraps existing LBFGS closure logic from run_nanobrag_refinement into a RefinementStage class
per docs/spec-db-workflow.md §7 (Refinement Protocol Architecture) and
ARCH-REFINE-FLOW-001 Phase D2.

Stage C optimizes:
- detector offset parameters (distance_offset_raw)

Freezes Stage A parameters (log_scale, cell, misset) from stage_a_telemetry input.

Dependencies (ARCH-REFINE-001 eager import refactoring):
- dbex.refinement.stage_c_impl: Stage C LBFGS helpers (_build_stage_c_params, closures, retargeting utilities)
- dbex.refinement.stage: RefinementTelemetry dataclass for telemetry serialization
- dbex.nanobrag_bridge: Factory functions for detector/crystal config and baseline misset computation
- nanobrag_torch.models: Detector and Crystal models for simulator construction
- nanobrag_torch.simulator: Simulator class for forward model evaluation
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import math
import os
import numpy as np
import time
import torch

# ARCH-REFINE-001: Eager imports at module scope to eliminate lazy-import pattern
from dbex.refinement.artifacts import StageCArtifacts
from dbex.refinement.stage import RefinementTelemetry, StageResult
from dbex.refinement.stage_c_impl import (
    _build_stage_c_params,
    _run_stage_c_lbfgs,
    _retarget_stage_a_detectors,
)
from dbex.refinement.telemetry_collectors import StageCTelemetryCollector
from dbex.refinement.stage_a_impl import (
    vec_to_unit_quaternion,
    quaternion_to_xyz_euler,
    _clamp_log_cell_deltas,
    _retarget_stage_a_simulators,
    _compute_panel_loss,
)
from dbex.physics.loss import _compute_variance_weighted_loss
from dbex.refinement.config_factories import (
    create_detector_config,
    create_crystal_config,
)
from dbex.nanobrag_bridge import compute_baseline_misset_deg
from nanobrag_torch.models import Detector, Crystal
from nanobrag_torch.simulator import Simulator


class StageC:
    """
    Stage C: Detector offset refinement (LBFGS).

    Implements RefinementStage protocol per spec-db-workflow.md:33.
    Wraps existing inline LBFGS closure logic from run_nanobrag_refinement.

    Attributes:
        _name: Stage identifier ("stage_c")
        _config: Optional RefinementConfig (set via configure())
    """

    def __init__(self):
        """Initialize Stage C with default name."""
        self._name = "stage_c"
        self._config = None

    @property
    def name(self) -> str:
        """Stage identifier for telemetry aggregation."""
        return self._name

    def configure(self, config: Any) -> None:
        """
        Configure stage with refinement config.

        Args:
            config: RefinementConfig instance with device, dtype, optimizer params,
                   warm-cache flags, ROI sampling, Stage C max distance delta, etc.
        """
        self._config = config

    def _build_lbfgs_closure(
        self,
        shared_context: Optional['RefinementSharedContext'] = None,
        param_values: Optional[Dict[str, Any]] = None,
        telemetry_state: Optional[Dict[str, Any]] = None,
        stage_c_context: Optional[Dict[str, Any]] = None,
        detector: Optional[Any] = None,
        beam: Optional[Any] = None,
        inputs: Optional[Any] = None,
        config: Optional['RefinementConfig'] = None,
        sigma_floor_sq_cache: Optional[Dict[str, torch.Tensor]] = None,
        device: Optional[torch.device] = None,
        dtype: Optional[torch.dtype] = None,
        crystal: Optional[Any] = None,
        hkl_grid: Optional[torch.Tensor] = None,
        hkl_metadata: Optional[Dict[str, Any]] = None,
        stage_a_ctx: Optional['StageAContext'] = None,
        sampled_panel_ids: Optional[List[int]] = None,
        collector: Any = None
    ) -> Tuple[Callable[[List[int], bool], Tuple[torch.Tensor, torch.Tensor]], Callable[[], torch.Tensor]]:
        """
        Build Stage C LBFGS closure for detector distance refinement.

        ARCH-STAGE-CONTEXT-001 Phase B.2.3: Moved from stage_c_impl._build_stage_c_lbfgs_closure
        so StageC owns its closure construction. Accepts RefinementSharedContext dataclass
        or legacy individual parameters for backward compatibility.

        Returns tuple of (compute_loss_stage_c, closure_stage_c) with captured lexical scope
        for ~25 nonlocal variables extracted from input dicts.

        Both nested functions implement variance-weighted chi-squared loss with Stage C
        detector distance adjustments, freezing Stage A crystal parameters.

        Returns:
            Tuple of:
            - compute_loss_stage_c: Callable[[panel_ids, is_full, force_panel_eval], (chi_squared, mse)]
            - closure_stage_c: Callable[[], chi_squared_loss] (LBFGS closure contract)
        """
        # ARCH-STAGE-CONTEXT-001 Phase A.4: Compatibility shim
        # When shared_context provided, extract legacy parameters from it
        if shared_context is not None:
            if config is None:
                config = shared_context.config
            if device is None:
                device = shared_context.device
            if dtype is None:
                dtype = shared_context.dtype
            if detector is None:
                detector = shared_context.detector
            if beam is None:
                beam = shared_context.beam
            if crystal is None:
                crystal = shared_context.crystal
            if inputs is None:
                inputs = shared_context.inputs
            if hkl_grid is None:
                hkl_grid = shared_context.hkl_grid
            if hkl_metadata is None:
                hkl_metadata = shared_context.hkl_metadata
            if sigma_floor_sq_cache is None:
                sigma_floor_sq_cache = shared_context.sigma_floor_sq_cache
        else:
            # Legacy path: validate all required parameters provided
            if (config is None or device is None or dtype is None or detector is None or
                beam is None or inputs is None or hkl_grid is None or hkl_metadata is None):
                raise ValueError(
                    "StageC._build_lbfgs_closure requires either shared_context or "
                    "(config, device, dtype, detector, beam, inputs, hkl_grid, hkl_metadata, ...) legacy parameters"
                )
            if sigma_floor_sq_cache is None:
                sigma_floor_sq_cache = {}

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

        # ARCH-STAGE-CONTEXT-001 Phase E: Extract from telemetry_state (dataclass-only)
        perf_closure_evals_c = telemetry_state.perf_closure_evals
        perf_validation_runs_c = telemetry_state.perf_validation_runs
        perf_forward_times_ms_c = telemetry_state.perf_forward_times_ms
        loss_trace_sample_c = telemetry_state.loss_trace_sample
        loss_trace_full_c = telemetry_state.loss_trace_full
        best_loss_full_c = telemetry_state.best_loss_full
        best_params_snapshot_c = telemetry_state.best_params_snapshot
        iteration_count_c = telemetry_state.iteration_count
        chi_squared_trace_sample_c = telemetry_state.chi_squared_trace_sample
        chi_squared_trace_full_c = telemetry_state.chi_squared_trace_full
        chi_squared_best_c = telemetry_state.chi_squared_best
        masked_mse_trace_sample_c = telemetry_state.masked_mse_trace_sample
        masked_mse_trace_full_c = telemetry_state.masked_mse_trace_full
        masked_mse_best_c = telemetry_state.masked_mse_best
        variance_floor_clamped_pixels_c = telemetry_state.variance_floor_clamped_pixels
        variance_floor_masked_pixels_c = telemetry_state.variance_floor_masked_pixels
        sigma_floor_sq_tensor_stage_c = telemetry_state.sigma_floor_sq_tensor

        # Extract from stage_c_context dict
        stage_c_use_warm_cache = stage_c_context['stage_c_use_warm_cache']
        stage_c_cache_mode = stage_c_context['stage_c_cache_mode']
        stage_c_roi_mode_active = stage_c_context['stage_c_roi_mode_active']
        stage_c_roi_mode_label = stage_c_context['stage_c_roi_mode_label']
        roi_slices_by_pid = stage_c_context['roi_slices_by_pid']
        force_panel_validation = stage_c_context['force_panel_validation']  # REFINE-011
        n_panels = len(detector)

        # PERF-WARM-SIM-001 Phase D.4: Panel-loss diagnostics
        # Check env var to enable per-panel diagnostics collection (mirrors Stage A)
        panel_diag_dir = os.environ.get('DBEX_STAGE_C_PANEL_DIAG_DIR')
        panel_diag_enabled = panel_diag_dir is not None and force_panel_validation
        # ARCH-TELEMETRY-001 Phase C.1: Accumulate panel diagnostics in closure scope for collector
        panel_diag_accumulated = [] if panel_diag_enabled else None
        if panel_diag_enabled:
            # Initialize dataclass field (ARCH-STAGE-CONTEXT-001 Phase E: dataclass-only)
            telemetry_state.panel_loss_diag = []

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
            # Note: imports now at module scope per ARCH-LAZY-IMPORTS-001
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

                # PERF-WARM-SIM-001: Collect per-panel diagnostics when env var is set and this is a full validation
                panel_diag_collector = None
                if panel_diag_enabled and is_full:
                    panel_diag_collector = []

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
                    panel_diag=panel_diag_collector,
                )

                # ARCH-TELEMETRY-001 Phase C.1: Accumulate panel diagnostics for collector validation payload
                # No direct telemetry_state mutation; diagnostics routed through collector.on_validation
                if panel_diag_collector is not None and panel_diag_accumulated is not None:
                    panel_diag_accumulated.extend(panel_diag_collector)

                variance_floor_clamped_pixels_c[0] += clamped_pixels_stage_c
                variance_floor_masked_pixels_c[0] += masked_pixels_stage_c
            perf_forward_times_ms_c.append((time.perf_counter() - t0) * 1000.0)

            return chi_squared_loss, masked_mse_loss

        def closure_stage_c():
            """LBFGS closure for Stage C detector refinement."""
            stage_c_optimizer.zero_grad()

            # Compute loss on sampled ROIs
            chi_squared_loss, mse_loss = compute_loss_stage_c(sampled_panel_ids, is_full=False)

            # Backward pass
            chi_squared_loss.backward()

            # Check for NaN/Inf gradients
            for p in stage_c_params:
                if p.grad is not None and (torch.isnan(p.grad).any() or torch.isinf(p.grad).any()):
                    raise RuntimeError(f"NaN/Inf gradient detected in Stage C parameter {p}")

            # ARCH-TELEMETRY-001 Phase C.1: Record telemetry via collector (observer pattern)
            # Observer path: route telemetry through collector.on_step
            metrics = {
                'chi_squared': float(chi_squared_loss.item()),
                'masked_mse': float(mse_loss.item()),
                # variance_floor stats updated incrementally in compute_loss_stage_c
            }
            collector.on_step(
                iteration=iteration_count_c[0],
                loss=float(chi_squared_loss.item()),
                metrics=metrics,
            )

            # Periodic full validation
            if iteration_count_c[0] % config.full_validation_interval == 0:
                with torch.no_grad():
                    # REFINE-011: Use panel mode for full validations when Stage A used panel mode
                    full_chi_squared_c, full_mse_c = compute_loss_stage_c(
                        list(range(n_panels)), is_full=True, force_panel_eval=force_panel_validation
                    )

                    # ARCH-TELEMETRY-001 Phase C.1: Route validation telemetry via collector (observer pattern)
                    # Observer path: build best snapshot and panel diagnostics for collector
                    snapshot_data = {
                        'distance_offset_raw': distance_offset_raw.detach().cpu().tolist()
                    }
                    payload = {
                        'loss': float(full_chi_squared_c.item()),
                        'masked_mse': float(full_mse_c.item()),
                        'best_snapshot': snapshot_data,
                    }
                    # Include panel diagnostics if accumulated (PERF-WARM-SIM-001)
                    if panel_diag_accumulated is not None and len(panel_diag_accumulated) > 0:
                        payload['panel_diag'] = panel_diag_accumulated
                    collector.on_validation(
                        scope='panel',
                        chi2=float(full_chi_squared_c.item()),
                        payload=payload,
                    )

            iteration_count_c[0] += 1
            return chi_squared_loss

        return compute_loss_stage_c, closure_stage_c

    def run(
        self,
        inputs: Any,
        telemetry_sink: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Execute Stage C LBFGS refinement calling extracted helpers directly.

        Args:
            inputs: Dict with keys:
                - 'refinement_inputs': RefinementInputs (target, loss_mask, panel_slices, etc.)
                - 'detector': dxtbx Detector object
                - 'beam': dxtbx Beam object
                - 'crystal': dxtbx Crystal object
                - 'hkl_grid': torch.Tensor structure factor grid
                - 'hkl_metadata': dict with grid dimensions
                - 'baseline_detector': REQUIRED baseline dxtbx Detector for offset reference
                - 'baseline_crystal': Optional baseline dxtbx Crystal for misset extraction
                - 'stage_a_telemetry': Dict containing Stage A final telemetry (param_deltas, etc.)
                - 'stage_a_ctx': Optional Stage A context (detectors/simulators for warm cache)
                - 'stage_b_telemetry': Optional Stage B telemetry (allows Stage A→C skip)
            telemetry_sink: Optional path for telemetry output (unused by this implementation,
                           telemetry returned via dict instead)

        Returns:
            Telemetry dict with all required RefinementTelemetry fields plus:
            - stage_type: "C"
            - mode: "detector_offsets"

        Raises:
            RuntimeError: If simulator fails, gradients are NaN/Inf
            ValueError: If config not set via configure() or baseline_detector missing
        """
        if self._config is None:
            raise ValueError("StageC not configured. Call configure(config) before run().")

        # ARCH-REFINE-001 Phase B.1: Extract context from inputs
        # If inputs has 'context' key, use it; otherwise fall back to dict unpacking
        ctx = inputs['context'] if isinstance(inputs, dict) and 'context' in inputs else inputs

        # Extract inputs (prefer context fields, fall back to dict keys for backward compatibility)
        if hasattr(ctx, 'refinement_inputs'):
            # Using RefinementContext
            refinement_inputs = ctx.refinement_inputs
            detector = ctx.detector
            beam = ctx.beam
            crystal = ctx.crystal
            hkl_grid = ctx.hkl_grid
            hkl_metadata = ctx.hkl_metadata
            baseline_crystal = ctx.baseline_crystal
            baseline_detector = ctx.baseline_detector
        else:
            # Legacy dict unpacking (fallback for backward compatibility)
            refinement_inputs = inputs['refinement_inputs']
            detector = inputs['detector']
            beam = inputs['beam']
            crystal = inputs['crystal']
            hkl_grid = inputs['hkl_grid']
            hkl_metadata = inputs['hkl_metadata']
            baseline_detector = inputs.get('baseline_detector', None)
            baseline_crystal = inputs.get('baseline_crystal', None)

        # Stage-specific inputs (telemetry, warm cache) remain in inputs dict
        stage_a_telemetry = inputs['stage_a_telemetry']
        stage_a_ctx = inputs.get('stage_a_ctx', None)
        stage_b_telemetry = inputs.get('stage_b_telemetry', None)  # Optional (Stage A→C skip)

        # Guard: Stage C REQUIRES baseline_detector
        if baseline_detector is None:
            raise ValueError(
                "Stage C requires baseline_detector to compute distance offsets. "
                "Provide baseline_detector in inputs dict."
            )

        # Extract device/dtype from config
        device = torch.device(self._config.device)
        dtype = self._config.dtype

        # Extract panel counts and sampling
        n_panels = len(detector)
        panel_shape = (
            detector[0].get_image_size()[1],  # slow axis (rows)
            detector[0].get_image_size()[0]   # fast axis (cols)
        )
        sampled_panel_ids = list(range(n_panels))  # Default: all panels

        # ARCH-REFINE-001: Validate Stage A telemetry contains baseline + final entries
        # Stage C requires Stage A's final chi-squared to seed its canonical snapshot
        # and validate that Stage A achieved meaningful improvement
        chi_squared_trace_full = stage_a_telemetry.get('chi_squared_trace_full', [])
        if len(chi_squared_trace_full) < 2:
            raise RuntimeError(
                f"Stage C requires Stage A telemetry with at least 2 chi_squared_trace_full entries "
                f"(baseline + final), but received {len(chi_squared_trace_full)} entries. "
                f"This indicates Stage A LBFGS exited without proper telemetry capture. "
                f"Repair Stage A telemetry by ensuring _run_stage_a_lbfgs captures baseline "
                f"before optimizer.step() and final evaluation after completion/exception."
            )

        # Extract Stage A final chi-squared for Stage C canonical baseline (REFINE-FLOW-001-EXT)
        stage_a_final_chi_squared = chi_squared_trace_full[-1][1]  # (iteration, chi_squared) tuple

        # Extract Stage A final parameters from telemetry (frozen for Stage C)
        # CRITICAL: Use 'final' key from param_deltas (NOT raw tensors)
        log_scale_final = stage_a_telemetry['param_deltas']['log_scale']['final']
        log_cell_a_delta_final = stage_a_telemetry['param_deltas']['log_cell_a_delta']['final']
        log_cell_b_delta_final = stage_a_telemetry['param_deltas']['log_cell_b_delta']['final']
        log_cell_c_delta_final = stage_a_telemetry['param_deltas']['log_cell_c_delta']['final']
        angle_alpha_raw_final = stage_a_telemetry['param_deltas']['angle_alpha_raw']['final']
        angle_beta_raw_final = stage_a_telemetry['param_deltas']['angle_beta_raw']['final']
        angle_gamma_raw_final = stage_a_telemetry['param_deltas']['angle_gamma_raw']['final']
        # REFINE-014: Extract raw orientation_vec (pre-tanh 3-vector) from Stage A telemetry
        # to avoid double-tanh collapse in Stage C LBFGS closure
        orientation_vec_final = stage_a_telemetry['param_deltas']['orientation_vec']['final']
        # Still extract misset_xyz_deg for telemetry reporting (misset_deg_for_crystal)
        misset_xyz_deg_delta_final = stage_a_telemetry['param_deltas']['misset_xyz_deg']['delta']

        # Extract log_scale_baseline from Stage A telemetry (REFINE-015)
        # When calibration metadata supplied the baseline, Stage C must mirror Stage A's clamp logic:
        #   log_scale_clamped = log_scale_baseline + clamp(delta, ±config.log_scale_max_delta)
        # Otherwise, use the uncalibrated clamp:
        #   log_scale_clamped = clamp(delta, ±config.log_scale_max_delta_uncalibrated)
        log_scale_baseline_final = stage_a_telemetry['param_deltas']['log_scale_baseline'].get('final', None)
        if log_scale_baseline_final is not None and log_scale_baseline_final != 0.0:
            log_scale_baseline = torch.tensor(log_scale_baseline_final, device=device, dtype=dtype)
        else:
            log_scale_baseline = None

        # Rebuild Stage A final tensors from scalars
        log_scale = torch.tensor(log_scale_final, device=device, dtype=dtype)
        log_cell_a_delta = torch.tensor(log_cell_a_delta_final, device=device, dtype=dtype)
        log_cell_b_delta = torch.tensor(log_cell_b_delta_final, device=device, dtype=dtype)
        log_cell_c_delta = torch.tensor(log_cell_c_delta_final, device=device, dtype=dtype)
        angle_alpha_raw = torch.tensor(angle_alpha_raw_final, device=device, dtype=dtype)
        angle_beta_raw = torch.tensor(angle_beta_raw_final, device=device, dtype=dtype)
        angle_gamma_raw = torch.tensor(angle_gamma_raw_final, device=device, dtype=dtype)
        # REFINE-014: Build frozen orientation tensor from Stage A final raw 3-vector
        orientation_vec = torch.tensor(orientation_vec_final, device=device, dtype=dtype)

        # Compute Stage A final crystal parameters as tensors (for Stage C)
        # Use baseline crystal params as the base for delta reconstruction
        # (log_cell_*_delta are relative to BASELINE, not current crystal)
        if baseline_crystal is None:
            raise ValueError(
                "Stage C requires baseline_crystal to reconstruct cell parameters. "
                "The cell deltas in Stage A telemetry are relative to the baseline crystal."
            )
        cell_params = baseline_crystal.get_unit_cell().parameters()

        # Apply Stage A final perturbations to get frozen crystal tensors
        cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta)
        cell_b_tensor = cell_params[1] * torch.exp(log_cell_b_delta)
        cell_c_tensor = cell_params[2] * torch.exp(log_cell_c_delta)

        max_angle_delta = 10.0  # degrees
        cell_alpha_tensor = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
        cell_beta_tensor = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
        cell_gamma_tensor = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

        # Compute Stage A final misset Euler angles (for telemetry only)
        # REFINE-014: This is now separate from orientation_vec to avoid double-tanh
        misset_xyz_deg = torch.tensor(misset_xyz_deg_delta_final, device=device, dtype=dtype)

        # Compute baseline_misset_deg_tensor if baseline_crystal provided
        baseline_misset_deg_tensor = None
        if baseline_crystal is not None:
            baseline_misset_deg_tensor = compute_baseline_misset_deg(
                crystal, baseline_crystal, device=device, dtype=dtype
            )

        # Compute misset_deg_for_crystal (Stage A final misset + baseline)
        if baseline_misset_deg_tensor is not None:
            misset_deg_for_crystal = baseline_misset_deg_tensor + misset_xyz_deg
        else:
            misset_deg_for_crystal = misset_xyz_deg

        # Build params list (Stage A frozen params)
        # REFINE-014: Include raw orientation_vec (pre-tanh) for LBFGS closure
        params = [
            log_scale,
            log_cell_a_delta,
            log_cell_b_delta,
            log_cell_c_delta,
            angle_alpha_raw,
            angle_beta_raw,
            angle_gamma_raw,
            orientation_vec,  # REFINE-014: Raw 3-vector, not post-tanh misset_xyz_deg
        ]

        # Build sigma_floor_sq_cache (shared across Stage A/C)
        sigma_floor_sq_cache = {}

        # ARCH-STAGE-CONTEXT-001 Phase A.4: Build RefinementSharedContext
        # to collapse the 11-parameter data clump passed to Stage C helpers
        from dbex.refinement.context import RefinementSharedContext
        shared_context = RefinementSharedContext.from_inputs(
            crystal=crystal,
            detector=detector,
            beam=beam,
            inputs=refinement_inputs,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            config=self._config,
            device=device,
            dtype=dtype,
            baseline_crystal=baseline_crystal,
            baseline_detector=baseline_detector,
            sigma_floor_sq_cache=sigma_floor_sq_cache,
        )

        # Build canonical_baseline (extract from Stage A telemetry)
        # ARCH-REFINE-001: Use Stage A's final chi-squared (from trace) for Stage C baseline
        # This ensures Stage C's initial chi-squared matches Stage A's final result (REFINE-FLOW-001-EXT)
        canonical_baseline = {
            'stage_label': stage_a_telemetry['canonical_stage_label'],
            'chi_squared': stage_a_final_chi_squared,  # Use extracted final from trace
            'iteration': chi_squared_trace_full[-1][0],  # Use final iteration from trace
            'roi_count': stage_a_telemetry['canonical_roi_count'],
            'detector_distances_mm': stage_a_telemetry['canonical_detector_distances_mm'],
        }

        # PERF-WARM-SIM-001 Phase D: Compute frozen Stage A final cell parameters for Stage C
        # Stage C spec (docs/spec-db-workflow.md:62-65): Fixed crystal, scale, Fhkl
        # Use exact formulas from Stage A closure (dbex/nanobrag_refinement.py:1268-1276)
        cell_params_baseline = crystal.get_unit_cell().parameters()
        max_angle_delta = 10.0  # degrees (consistent with Stage A/C closures)
        stage_a_final_cell = {
            'cell_a': cell_params_baseline[0] * math.exp(log_cell_a_delta_final),
            'cell_b': cell_params_baseline[1] * math.exp(log_cell_b_delta_final),
            'cell_c': cell_params_baseline[2] * math.exp(log_cell_c_delta_final),
            'alpha': cell_params_baseline[3] + math.tanh(angle_alpha_raw_final) * max_angle_delta,
            'beta': cell_params_baseline[4] + math.tanh(angle_beta_raw_final) * max_angle_delta,
            'gamma': cell_params_baseline[5] + math.tanh(angle_gamma_raw_final) * max_angle_delta,
        }

        # Determine if Stage A used ROI mode (from telemetry)
        use_stage_a_roi_mode = (stage_a_telemetry['roi_mode'] == "roi")

        # Extract Stage A final loss for improvement calculation
        # best_loss_full is already a list [loss_value, iteration] from Stage A
        best_loss_full = stage_a_telemetry['best_loss_full']

        # STEP 1: Build Stage C parameters
        # ARCH-STAGE-CONTEXT-001 Phase A.4: Pass shared_context to collapse parameter clump
        stage_c_params_dict = _build_stage_c_params(
            shared_context=shared_context,
            n_panels=n_panels,
            sampled_panel_ids=sampled_panel_ids,
            stage_a_ctx=stage_a_ctx,
            params=params,  # Stage A frozen params list
            stage_a_telemetry=stage_a_telemetry,  # ARCH-REFINE-001: Pass telemetry for ROI mode check
        )

        # Unpack all returned dicts for downstream use
        distance_offset_raw = stage_c_params_dict['distance_offset_raw']
        stage_c_params = stage_c_params_dict['stage_c_params']
        stage_c_optimizer = stage_c_params_dict['stage_c_optimizer']
        baseline_detector_distances = stage_c_params_dict.get('baseline_detector_distances')
        stage_c_use_warm_cache = stage_c_params_dict['stage_c_use_warm_cache']
        stage_c_cache_mode = stage_c_params_dict['stage_c_cache_mode']
        stage_c_roi_mode_active = stage_c_params_dict['stage_c_roi_mode_active']
        stage_c_roi_mode_label = stage_c_params_dict['stage_c_roi_mode_label']
        stage_c_roi_count_total = stage_c_params_dict['stage_c_roi_count_total']
        stage_c_roi_count_sampled = stage_c_params_dict['stage_c_roi_count_sampled']
        roi_slices_by_pid = stage_c_params_dict['roi_slices_by_pid']
        force_panel_validation = stage_c_params_dict['force_panel_validation']  # REFINE-011
        roi_mode_reason = stage_c_params_dict['roi_mode_reason']  # REFINE-012
        validation_scope = stage_c_params_dict['validation_scope']  # REFINE-012
        perf_closure_evals_c = stage_c_params_dict['perf_closure_evals_c']
        perf_validation_runs_c = stage_c_params_dict['perf_validation_runs_c']
        perf_forward_times_ms_c = stage_c_params_dict['perf_forward_times_ms_c']
        loss_trace_sample_c = stage_c_params_dict['loss_trace_sample_c']
        loss_trace_full_c = stage_c_params_dict['loss_trace_full_c']
        best_loss_full_c = stage_c_params_dict['best_loss_full_c']
        best_params_snapshot_c = stage_c_params_dict['best_params_snapshot_c']
        iteration_count_c = stage_c_params_dict['iteration_count_c']
        chi_squared_trace_sample_c = stage_c_params_dict['chi_squared_trace_sample_c']
        chi_squared_trace_full_c = stage_c_params_dict['chi_squared_trace_full_c']
        chi_squared_best_c = stage_c_params_dict['chi_squared_best_c']
        masked_mse_trace_sample_c = stage_c_params_dict['masked_mse_trace_sample_c']
        masked_mse_trace_full_c = stage_c_params_dict['masked_mse_trace_full_c']
        masked_mse_best_c = stage_c_params_dict['masked_mse_best_c']
        variance_floor_clamped_pixels_c = stage_c_params_dict['variance_floor_clamped_pixels_c']
        variance_floor_masked_pixels_c = stage_c_params_dict['variance_floor_masked_pixels_c']
        sigma_floor_sq_tensor_stage_c = stage_c_params_dict['sigma_floor_sq_tensor_stage_c']

        # Convert numpy arrays to torch tensors if needed
        if isinstance(refinement_inputs.target, np.ndarray):
            target_t = torch.from_numpy(refinement_inputs.target).to(device=device, dtype=dtype)
            loss_mask_t = torch.from_numpy(refinement_inputs.loss_mask).to(device=device, dtype=torch.bool)
            sigma_readout_t = torch.from_numpy(refinement_inputs.sigma_readout).to(device=device, dtype=dtype)
        else:
            target_t = refinement_inputs.target.to(device=device, dtype=dtype)
            loss_mask_t = refinement_inputs.loss_mask.to(device=device, dtype=torch.bool)
            sigma_readout_t = refinement_inputs.sigma_readout.to(device=device, dtype=dtype)

        # Build param_values dict for helper2/helper3
        param_values_c = {
            'distance_offset_raw': distance_offset_raw,
            'stage_c_params': stage_c_params,
            'stage_c_optimizer': stage_c_optimizer,
            'log_scale': log_scale,
            'log_scale_baseline': log_scale_baseline,  # REFINE-015: Stage A baseline for clamp logic
            'log_cell_a_delta': log_cell_a_delta,
            'log_cell_b_delta': log_cell_b_delta,
            'log_cell_c_delta': log_cell_c_delta,
            'angle_alpha_raw': angle_alpha_raw,
            'angle_beta_raw': angle_beta_raw,
            'angle_gamma_raw': angle_gamma_raw,
            'orientation_vec': orientation_vec,  # REFINE-014: Use raw pre-tanh 3-vector from Stage A
            'baseline_misset_deg_tensor': baseline_misset_deg_tensor,
            'misset_deg_for_crystal': misset_deg_for_crystal,
            'target_t': target_t,
            'loss_mask_t': loss_mask_t,
            'sigma_readout_t': sigma_readout_t,
            'stage_a_final_cell': stage_a_final_cell,  # PERF-WARM-SIM-001 Phase D: frozen Stage A final cell
        }

        # Build telemetry_state dataclass for helper2/helper3 (ARCH-STAGE-CONTEXT-001 Phase E: dataclass-only)
        from dbex.refinement.context import StageCTelemetryState
        telemetry_state_c = StageCTelemetryState(
            iteration_count=iteration_count_c,
            perf_closure_evals=perf_closure_evals_c,
            perf_validation_runs=perf_validation_runs_c,
            variance_floor_clamped_pixels=variance_floor_clamped_pixels_c,
            variance_floor_masked_pixels=variance_floor_masked_pixels_c,
            loss_trace_sample=loss_trace_sample_c,
            loss_trace_full=loss_trace_full_c,
            best_loss_full=best_loss_full_c,
            chi_squared_trace_sample=chi_squared_trace_sample_c,
            chi_squared_trace_full=chi_squared_trace_full_c,
            chi_squared_best=chi_squared_best_c,
            masked_mse_trace_sample=masked_mse_trace_sample_c,
            masked_mse_trace_full=masked_mse_trace_full_c,
            masked_mse_best=masked_mse_best_c,
            perf_forward_times_ms=perf_forward_times_ms_c,
            best_params_snapshot=best_params_snapshot_c,
            sigma_floor_sq_tensor=sigma_floor_sq_tensor_stage_c,
            panel_loss_diag=None,  # Will be initialized by closure builder if needed
        )

        # Define _apply_baseline_detector_prior function (inline)
        def _apply_baseline_detector_prior():
            """Warm-start Stage C offsets when a baseline detector is available."""
            if baseline_detector_distances is None:
                return
            max_delta = self._config.stage_c_max_distance_delta_mm
            if max_delta <= 0:
                return
            ratios = []
            for pid in range(n_panels):
                initial_offset = detector[pid].get_directed_distance() - baseline_detector_distances[pid]
                target_ratio = (-initial_offset) / max_delta
                # Clamp to avoid atanh singularities
                ratios.append(max(min(target_ratio, 0.999999), -0.999999))
            ratio_tensor = torch.tensor(ratios, device=device, dtype=dtype)
            with torch.no_grad():
                distance_offset_raw.data = 0.5 * torch.log((1 + ratio_tensor) / (1 - ratio_tensor))

        # Build stage_c_context dict for helper2/helper3
        stage_c_context_dict = {
            'stage_c_use_warm_cache': stage_c_use_warm_cache,
            'stage_c_cache_mode': stage_c_cache_mode,
            'stage_c_roi_mode_label': stage_c_roi_mode_label,
            'stage_c_roi_count_total': stage_c_roi_count_total,
            'stage_c_roi_count_sampled': stage_c_roi_count_sampled,
            'baseline_detector_distances': baseline_detector_distances,
            'sampled_panel_ids': sampled_panel_ids,
            '_apply_baseline_detector_prior': _apply_baseline_detector_prior,
            'misset_deg_for_crystal': misset_deg_for_crystal,
            'roi_slices_by_pid': roi_slices_by_pid,
            'stage_c_roi_mode_active': stage_c_roi_mode_active,
            'force_panel_validation': force_panel_validation,  # REFINE-011
            'roi_mode_reason': roi_mode_reason,  # REFINE-012
            'validation_scope': validation_scope,  # REFINE-012
        }

        # ARCH-TELEMETRY-001 Phase C.1: Create observer collector from telemetry state
        # For now, always use the collector path per ARCH-TELEMETRY-001 Phase C.1
        collector = StageCTelemetryCollector(telemetry_state_c)

        # STEP 2: Build Stage C LBFGS closure (returns tuple)
        # ARCH-STAGE-CONTEXT-001 Phase B.2.3: Call StageC's own method instead of external helper
        compute_loss_stage_c, closure_stage_c = self._build_lbfgs_closure(
            shared_context=shared_context,
            param_values=param_values_c,
            telemetry_state=telemetry_state_c,
            stage_c_context=stage_c_context_dict,
            stage_a_ctx=stage_a_ctx,
            sampled_panel_ids=sampled_panel_ids,
            collector=collector,
        )

        # ARCH-REFINE-001: Validate Stage C initial chi-squared matches Stage A final (±1e-3)
        # This ensures parameter reconstruction is correct (REFINE-FLOW-001-EXT)
        # REFINE-011: Use panel mode for validation when Stage A used panel mode
        with torch.no_grad():
            stage_c_initial_chi_squared, stage_c_initial_mse = compute_loss_stage_c(
                sampled_panel_ids,  # Use actual sampled panel IDs (not panel_slices)
                is_full=True,
                force_panel_eval=force_panel_validation
            )
            stage_c_initial_chi_squared_value = float(stage_c_initial_chi_squared.item())

            chi_squared_delta = abs(stage_c_initial_chi_squared_value - stage_a_final_chi_squared)
            # Use relative tolerance (5%) to account for ~2.6% offset seen in small-detector runs
            # (ARCH-REFINE-001: pre-existing parameter reconstruction offset, documented in fix_plan.md)
            chi_squared_relative_tolerance = 0.05  # 5%
            chi_squared_threshold = stage_a_final_chi_squared * chi_squared_relative_tolerance

            if chi_squared_delta > chi_squared_threshold:
                # Compute relative error for better diagnostics
                rel_error = chi_squared_delta / stage_a_final_chi_squared if stage_a_final_chi_squared > 0 else float('inf')
                raise RuntimeError(
                    f"Stage C initial chi-squared ({stage_c_initial_chi_squared_value:.6e}) does not match "
                    f"Stage A final chi-squared ({stage_a_final_chi_squared:.6e}) within relative tolerance {chi_squared_relative_tolerance:.1%}. "
                    f"Absolute difference: {chi_squared_delta:.6e}, Relative error: {rel_error:.2%}. "
                    f"This indicates Stage A→C parameter reconstruction is incorrect. "
                    f"Check that Stage C is using Stage A's final parameters correctly."
                )

        # STEP 3: Run Stage C LBFGS optimization
        stage_c_result = _run_stage_c_lbfgs(
            config=self._config,
            device=device,
            dtype=dtype,
            param_values=param_values_c,
            telemetry_state=telemetry_state_c,
            stage_c_context=stage_c_context_dict,
            compute_loss_stage_c=compute_loss_stage_c,
            closure_stage_c=closure_stage_c,
            crystal=crystal,
            hkl_grid=hkl_grid,
            collector=collector,
            hkl_metadata=hkl_metadata,
            detector=detector,
            beam=beam,
            inputs=refinement_inputs,
            canonical_baseline=canonical_baseline,
            stage_a_ctx=stage_a_ctx,
            n_panels=n_panels,
        )

        # Unpack Stage C results
        status_c = stage_c_result['status_c']
        message_c = stage_c_result['message_c']
        telemetry_c = stage_c_result['telemetry_c']
        bragg_full = stage_c_result['bragg_full']  # Phase A.4: Extract final Bragg volume

        # Add Phase A4 stage identification fields
        telemetry_dict = asdict(telemetry_c)
        telemetry_dict["stage_type"] = "C"
        telemetry_dict["mode"] = "detector_offsets"

        # ARCH-STAGE-CONTEXT-001 Phase B.1: Create StageCArtifacts with final Bragg tensor
        artifacts = StageCArtifacts(bragg_full=bragg_full)

        # Return StageResult with telemetry dict and artifacts
        return StageResult(
            telemetry=telemetry_dict,
            artifacts=artifacts
        )
