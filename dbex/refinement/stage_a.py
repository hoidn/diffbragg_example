# dbex/refinement/stage_a.py
"""
Stage A implementation for Protocol-based Refinement Engine.

Wraps existing LBFGS closure logic from run_nanobrag_refinement into a RefinementStage class
per docs/spec-db-workflow.md §7 (Refinement Protocol Architecture) and
ARCH-REFINE-FLOW-001 Phase B.

Stage A optimizes:
- log_scale: global intensity scale (ADU mode)
- log_cell_*_delta: unit cell length perturbations (a/b/c)
- angle_*_raw: unit cell angle perturbations (alpha/beta/gamma)
- orientation_vec: crystal misorientation (3-vector → quaternion → XYZ Euler)

Supports multiple parameterization modes (config.use_incremental_ub, config.use_u_matrix_parameterization).

Dependencies (ARCH-REFINE-001 eager import refactoring):
- dbex.refinement.stage_a_impl: Stage A LBFGS helpers (_build_stage_a_params, closures, quaternion conversion)
- dbex.refinement.stage: RefinementTelemetry dataclass for telemetry serialization
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import time
import torch

# ARCH-REFINE-001: Eager imports at module scope to eliminate lazy-import pattern
from dbex.refinement.artifacts import StageAArtifacts
from dbex.refinement.stage import StageResult
from dbex.refinement.stage_a_impl import (
    _build_stage_a_params,
    _clamp_log_cell_deltas,
    _compute_panel_loss,
    _compute_variance_weighted_loss,
    _retarget_stage_a_simulators,
    _run_stage_a_lbfgs,
    _sync_stage_a_crystal,
    vec_to_unit_quaternion,
    quaternion_to_xyz_euler,
)
from dbex.refinement.stage import RefinementTelemetry


class StageA:
    """
    Stage A: Global scale + full crystal refinement (LBFGS).

    Implements RefinementStage protocol per spec-db-workflow.md:33.
    Wraps existing inline LBFGS closure logic from run_nanobrag_refinement.

    Attributes:
        _name: Stage identifier ("stage_a")
        _config: Optional RefinementConfig (set via configure())
    """

    def __init__(self):
        """Initialize Stage A with default name."""
        self._name = "stage_a"
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
                   warm-cache flags, ROI sampling, incremental UB mode, etc.
        """
        self._config = config

    def _build_lbfgs_closure(
        self,
        # Parameters from helper 1 return dict
        param_values: Dict[str, Any],
        telemetry_state: Dict[str, Any],
        stage_a_context: Dict[str, Any],
        # ARCH-STAGE-CONTEXT-001 Phase B.2: Use shared_context parameter
        shared_context: 'RefinementSharedContext',
        # ARCH-TELEMETRY-001 Phase B.1: Accept StageATelemetryCollector for observer-based telemetry
        collector: 'StageATelemetryCollector',
    ) -> Tuple[Callable, Callable]:
        """
        Build LBFGS closure for Stage A refinement with nested compute_loss and closure functions.

        Captures lexical scope for ~30 nonlocal variables from param_values, telemetry_state, stage_a_context.
        Supports 3 parameterization modes: cell+misset, U-matrix, incremental UB.

        ARCH-STAGE-CONTEXT-001 Phase B.2: Inlined from _build_stage_a_lbfgs_closure so StageA owns
        the loss/telemetry lifecycle instead of delegating to stage_a_impl.py. Keeps the warm-cache/
        shared-context plumbing intact.

        ARCH-TELEMETRY-001 Phase B.1: Thread StageATelemetryCollector through closure to eliminate
        direct telemetry_state dict mutations. Closures emit telemetry via collector.record_step and
        collector.record_validation callbacks.

        Args:
            param_values: Dict with trainable tensors (log_scale, log_cell_*_delta, angle_*_raw,
                         orientation_vec, q_params, delta_log_*, delta_alpha/beta/gamma, q_delta)
            telemetry_state: Dict with mutable telemetry accumulators (DEPRECATED: Use collector.state)
            stage_a_context: Dict with ROI/panel sampling state, warm cache context
            shared_context: RefinementSharedContext dataclass (new path, ARCH-STAGE-CONTEXT-001)
            collector: StageATelemetryCollector instance for observer-based telemetry emission

        Returns:
            Tuple of (compute_loss, closure) callables with captured lexical scope
        """
        # Extract from shared context
        crystal = shared_context.crystal
        detector = shared_context.detector
        beam = shared_context.beam
        inputs = shared_context.inputs
        hkl_grid = shared_context.hkl_grid
        hkl_metadata = shared_context.hkl_metadata
        config = shared_context.config
        sigma_floor_sq_cache = shared_context.sigma_floor_sq_cache
        device = shared_context.device
        dtype = shared_context.dtype
        baseline_crystal = shared_context.baseline_crystal

        # Unpack param_values
        log_scale = param_values['log_scale']
        log_cell_a_delta = param_values.get('log_cell_a_delta')
        log_cell_b_delta = param_values.get('log_cell_b_delta')
        log_cell_c_delta = param_values.get('log_cell_c_delta')
        angle_alpha_raw = param_values.get('angle_alpha_raw')
        angle_beta_raw = param_values.get('angle_beta_raw')
        angle_gamma_raw = param_values.get('angle_gamma_raw')
        orientation_vec = param_values.get('orientation_vec')
        q_params = param_values.get('q_params')
        delta_log_a = param_values.get('delta_log_a')
        delta_log_b = param_values.get('delta_log_b')
        delta_log_c = param_values.get('delta_log_c')
        delta_alpha = param_values.get('delta_alpha')
        delta_beta = param_values.get('delta_beta')
        delta_gamma = param_values.get('delta_gamma')
        q_delta = param_values.get('q_delta')
        params = param_values.get('params', [])  # List of Parameter objects
        B_ideal_reciprocal_torch = param_values.get('B_ideal_reciprocal_torch')

        # ARCH-TELEMETRY-001 Phase B.1: Unpack from collector.state (observer migration)
        # Access telemetry state through collector instead of direct dict mutations
        telemetry_state = collector.state
        iteration_count = telemetry_state.iteration_count
        loss_trace_sample = telemetry_state.loss_trace_sample
        loss_trace_full = telemetry_state.loss_trace_full
        best_loss_full = telemetry_state.best_loss_full
        best_params_snapshot = telemetry_state.best_params_snapshot
        chi_squared_trace_sample = telemetry_state.chi_squared_trace_sample
        chi_squared_trace_full = telemetry_state.chi_squared_trace_full
        chi_squared_best = telemetry_state.chi_squared_best
        masked_mse_trace_sample = telemetry_state.masked_mse_trace_sample
        masked_mse_trace_full = telemetry_state.masked_mse_trace_full
        masked_mse_best = telemetry_state.masked_mse_best
        perf_closure_evals = telemetry_state.perf_closure_evals
        perf_validation_runs = telemetry_state.perf_validation_runs
        perf_forward_times_ms = telemetry_state.perf_forward_times_ms
        variance_floor_clamped_pixels = telemetry_state.variance_floor_clamped_pixels
        variance_floor_masked_pixels = telemetry_state.variance_floor_masked_pixels
        sigma_floor_sq_tensor = telemetry_state.sigma_floor_sq_tensor
        telemetry_step_counter = telemetry_state.telemetry_step_counter
        u_matrix_lifecycle_log = telemetry_state.u_matrix_lifecycle_log
        a_star_lifecycle_log = telemetry_state.a_star_lifecycle_log

        # Unpack stage_a_context
        stage_a_ctx = stage_a_context.get('stage_a_ctx')
        sampled_panel_ids = stage_a_context.get('sampled_panel_ids')
        use_stage_a_roi_mode = stage_a_context['use_stage_a_roi_mode']
        sampled_stage_a_indices = stage_a_context['sampled_stage_a_indices']
        full_stage_a_indices = stage_a_context['full_stage_a_indices']
        force_panel_validation = stage_a_context.get('force_panel_validation', False)  # ARCH-REFINE-001, REFINE-007

        # Additional context for incremental UB mode
        U_baseline = param_values.get('U_baseline')
        cell_baseline = param_values.get('cell_baseline')

        # Extract additional context needed for compute_loss
        from dbex.nanobrag_bridge import (
            create_detector_config,
            create_beam_config,
            create_crystal_config,
            compute_baseline_misset_deg,
        )

        target_t = torch.from_numpy(inputs.target).to(device=device, dtype=dtype)
        loss_mask_t = torch.from_numpy(inputs.loss_mask).to(device=device, dtype=torch.bool)
        sigma_readout_t = torch.from_numpy(inputs.sigma_readout).to(device=device, dtype=dtype)

        baseline_misset_deg_tensor = compute_baseline_misset_deg(
            crystal,
            baseline_crystal,
            device=device,
            dtype=dtype,
        )

        n_panels = len(detector)
        panel_slices = inputs.panel_slices

        # PERF-WARM-SIM-001 Phase D.4: Panel-loss diagnostics
        # Check env var to enable per-panel diagnostics collection
        import os
        panel_diag_dir = os.environ.get('DBEX_STAGE_C_PANEL_DIAG_DIR')
        panel_diag_enabled = panel_diag_dir is not None and force_panel_validation
        if panel_diag_enabled:
            # Initialize panel_loss_diag list (ARCH-STAGE-CONTEXT-001 Phase E: dataclass-only)
            telemetry_state.panel_loss_diag = []

        beam_config_kwargs: Dict[str, Any] = {}
        n_cells_override = None
        if getattr(config, "calibration_metadata", None) is not None:
            beam_config_kwargs = {
                "flux": config.calibration_metadata.get("beam_flux"),
                "beamsize_mm": config.calibration_metadata.get("beamsize_mm"),
                "exposure": config.calibration_metadata.get("beam_exposure"),
            }
            n_cells_override = config.calibration_metadata.get("N_cells")

        log_cell_max_delta = getattr(config, "log_cell_max_delta", 1.0)

        def compute_loss(work_item_ids: List[int], is_full: bool = False, force_panel_eval: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            Compute variance-weighted chi-squared loss over specified work items.

            Implements spec-db-core.md:57-68 variance model:
            - Variance: V = I_model.detach() + sigma_readout^2
            - Loss: Sum((I_model - I_obs)^2 / V) over trusted pixels
            - Detached denominator implements IRLS (prevents "attraction to zero")

            Warm mode (default): Reuses cached detector models and masks (PERF-WARM-SIM-001).
            Cold mode (benchmarking): Rebuilds detector models/masks inside closure.

            Args:
                work_item_ids: List of ROI indices (when ROI sampling enabled) or panel indices
                is_full: If True, this is a full validation run
                force_panel_eval: If True, skip ROI mode and use panel mode even when ROI sampling is enabled
                                (ARCH-REFINE-001, REFINE-007: ensures Stage A telemetry reports panel-level chi²
                                that matches Stage C's initial state)

            Returns:
                Tuple of (chi_squared_loss, masked_mse_loss): Both scalar tensors for telemetry
            """
            # Time forward pass (CPU-only, PERF-WARM-SIM-001)
            t0 = time.perf_counter()

            # Compute cell/orientation parameters once per loss evaluation (shared across panels/ROIs)
            cell_params = crystal.get_unit_cell().parameters()  # (a, b, c, alpha, beta, gamma)

            # 1. Unit cell lengths (log-parameterized)
            log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
                log_cell_a_delta,
                log_cell_b_delta,
                log_cell_c_delta,
                log_cell_max_delta,
            )
            perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
            perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
            perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta_clamped)

            # 2. Unit cell angles (bounded via tanh, max perturbation ±10°)
            max_angle_delta = 10.0  # degrees
            perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
            perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
            perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

            # 3. Orientation perturbation via quaternion→XYZ misset (TORCH-REFINE-002)
            # TORCH-GEOMETRY-UB-REALIGN-001 Phase B3: Branch on incremental UB vs U-matrix vs cell+misset path
            if config.use_incremental_ub:
                # Incremental UB path: Derive A* = U(q_delta) @ B(cell_deltas)
                from dbex.nanobrag_bridge import (
                    derive_orientation_from_quaternion_delta,
                    derive_B_from_cell_deltas,
                )

                # Derive U(params) = ΔR(q_delta) @ U_baseline
                U_current = derive_orientation_from_quaternion_delta(
                    q_delta, U_baseline, dtype=dtype, device=device
                )

                # Derive B(params) from cell perturbations
                B_current = derive_B_from_cell_deltas(
                    delta_log_a, delta_log_b, delta_log_c,
                    delta_alpha, delta_beta, delta_gamma,
                    cell_baseline=tuple(cell_baseline.detach().cpu().numpy().tolist()),
                    dtype=dtype,
                    device=device
                )

                # Construct A* = U @ B (one-way construction per spec-db-core.md:64-67)
                A_star_new = U_current @ B_current  # Shape: [3, 3]

                # Extract MOSFLM a/b/c_star for crystal_config injection
                # A* columns are reciprocal lattice vectors a*, b*, c*
                a_star = A_star_new[:, 0].detach().cpu().numpy()  # Shape: [3]
                b_star = A_star_new[:, 1].detach().cpu().numpy()
                c_star = A_star_new[:, 2].detach().cpu().numpy()

                # Inject via MOSFLM a/b/c_star (per GRADIENT-001: no cell overrides with MOSFLM injection)
                crystal_overrides = {
                    'mosflm_a_star': tuple(a_star.tolist()),
                    'mosflm_b_star': tuple(b_star.tolist()),
                    'mosflm_c_star': tuple(c_star.tolist()),
                }
                # CRITICAL: Do NOT inject cell parameters when using MOSFLM a/b/c_star (GRADIENT-001)
                misset_deg_for_crystal = None  # MOSFLM A* is provided directly

            elif config.use_u_matrix_parameterization:
                # U-matrix path: Normalize quaternion, convert to U, compute A*
                from dbex.nanobrag_bridge import quaternion_to_matrix
                q_norm = q_params / torch.norm(q_params)  # Enforce ||q|| = 1

                U = quaternion_to_matrix(q_norm)  # 3x3 rotation matrix
                A_star_new = U @ B_ideal_reciprocal_torch  # Compute updated A*

                # Lifecycle logging: U-matrix and A* reconstruction (TORCH-GEOMETRY-CONVERGENCE-001 Phase B4)
                if not is_full:
                    U_checksum = U.sum().item()
                    A_star_checksum = A_star_new.sum().item()
                    B_ideal_checksum = B_ideal_reciprocal_torch.sum().item()

                    u_matrix_lifecycle_log.append({
                        "closure_call_index": len(u_matrix_lifecycle_log),
                        "U_checksum": U_checksum,
                        "q_params_norm": torch.norm(q_params).item(),
                        "log_scale_value": log_scale.item()
                    })

                    a_star_lifecycle_log.append({
                        "closure_call_index": len(a_star_lifecycle_log),
                        "A_star_checksum": A_star_checksum,
                        "U_checksum": U_checksum,
                        "B_ideal_checksum": B_ideal_checksum
                    })

                # Telemetry: Capture parameters (TORCH-GEOMETRY-CONVERGENCE-001 Phase B2)
                if not is_full and getattr(config, "telemetry_output_dir", None):
                    q_norm_value = torch.norm(q_params).item()
                    telemetry_params = {
                        'step_index': telemetry_step_counter[0],
                        'q_params': q_params.detach().cpu().tolist(),
                        'q_norm_value': q_norm_value,
                        'log_scale': log_scale.item(),
                        'u_matrix_checksum': U.sum().item(),  # Phase B2: U-matrix checksum
                    }

                # Convert A* to numpy for crystal_overrides
                A_star_np = A_star_new.detach().cpu().numpy()
                mosflm_a_star_tuple = tuple(A_star_np[:, 0].tolist())
                mosflm_b_star_tuple = tuple(A_star_np[:, 1].tolist())
                mosflm_c_star_tuple = tuple(A_star_np[:, 2].tolist())

                crystal_overrides = {
                    'cell_a': perturbed_cell_a,
                    'cell_b': perturbed_cell_b,
                    'cell_c': perturbed_cell_c,
                    'cell_alpha': perturbed_alpha,
                    'cell_beta': perturbed_beta,
                    'cell_gamma': perturbed_gamma,
                    'mosflm_a_star': mosflm_a_star_tuple,
                    'mosflm_b_star': mosflm_b_star_tuple,
                    'mosflm_c_star': mosflm_c_star_tuple,
                }
                # FIX: Define misset_deg_for_crystal here in U-matrix branch
                misset_deg_for_crystal = None  # MOSFLM A* is provided directly
            else:
                # Existing cell+misset path (GEOMETRY-003)
                max_orientation_deg = 3.0  # degrees (per input.md pitfalls)
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
                # FIX: Define misset_deg_for_crystal here in cell+misset branch
                misset_deg_for_crystal = misset_xyz_deg

            # Clamp log_scale and apply baseline if calibration is present (TOOLING-VIS-001 Phase D.C, DB-AT-027)
            # When calibration_metadata is provided:
            #   - log_scale_baseline = log(sqrt(spot_scale_override)) is the fixed baseline
            #   - log_scale is a delta parameter, clamped to ±log_scale_max_delta (default ±3)
            #   - Final scale = exp(log_scale_baseline + clamped_delta)
            # Otherwise:
            #   - log_scale is the direct learnable parameter, clamped to ±10 (legacy wide range)
            #   - Final scale = exp(clamped_log_scale)
            log_scale_baseline_value = param_values.get('log_scale_baseline')
            max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
            delta_bound = getattr(config, "log_scale_max_delta", 3.0) if log_scale_baseline_value is not None else max_delta_uncal
            if log_scale_baseline_value is not None:
                log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
                log_scale_clamped = log_scale_baseline_value + log_scale_delta_clamped
            else:
                # Absolute clamp when no baseline is available
                log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
            beam_config_for_run = stage_a_ctx.beam_config if stage_a_ctx is not None else create_beam_config(
                beam,
                **beam_config_kwargs,
            )

            warm_crystal_model: Optional['Crystal'] = None
            if stage_a_ctx is not None:
                warm_crystal_config, _ = create_crystal_config(
                    crystal,
                    None,
                    crystal_overrides=crystal_overrides,
                    misset_deg_override=misset_deg_for_crystal,
                    N_cells=n_cells_override,
                    apply_n_cells=(n_cells_override is not None),
                )
                from nanobrag_torch.models.crystal import Crystal
                warm_crystal_model = Crystal(
                    warm_crystal_config,
                    beam_config=beam_config_for_run,
                    device=device,
                    dtype=dtype
                )
                warm_crystal_model = _sync_stage_a_crystal(stage_a_ctx, warm_crystal_model)
                _retarget_stage_a_simulators(stage_a_ctx, warm_crystal_model)

            # ARCH-REFINE-001: Force panel mode when requested (REFINE-007)
            # Skip ROI branch if force_panel_eval is True, ensuring baseline/final validations
            # report panel-level chi² that matches Stage C's initial state
            if use_stage_a_roi_mode and not force_panel_eval:
                indices = work_item_ids if work_item_ids else full_stage_a_indices
                chi_squared_accum = torch.zeros((), device=device, dtype=dtype)
                mse_numerator_accum = torch.zeros((), device=device, dtype=dtype)
                masked_pixels_total = 0
                clamped_pixels_total = 0

                # Telemetry: Initialize variance component accumulators (TORCH-GEOMETRY-CONVERGENCE-001 Phase B2)
                if not is_full and getattr(config, "telemetry_output_dir", None) and config.use_u_matrix_parameterization:
                    i_model_min_global = float('inf')
                    i_model_max_global = float('-inf')
                    i_model_values_list = []
                    v_denom_values_list = []
                    weighted_residuals_list = []

                for roi_index in indices:
                    pid, bbox = panel_slices[roi_index]
                    x0, x1, y0, y1 = map(int, bbox)
                    slow_slice = slice(y0, y1)
                    fast_slice = slice(x0, x1)

                    target_subset = target_t[pid, slow_slice, fast_slice]
                    mask_subset = loss_mask_t[pid, slow_slice, fast_slice]
                    if stage_a_ctx is not None and stage_a_ctx.trusted_masks_t is not None:
                        trusted_slice = stage_a_ctx.trusted_masks_t[pid, slow_slice, fast_slice]
                        mask_subset = torch.logical_and(mask_subset, trusted_slice)
                    sigma_subset = sigma_readout_t[pid, slow_slice, fast_slice]

                    if stage_a_ctx is not None and stage_a_ctx.roi_entries:
                        simulator = stage_a_ctx.roi_entries[roi_index].simulator
                    else:
                        detector_config = create_detector_config(
                            panel=detector[pid],
                            beam=beam,
                            trusted_mask=inputs.trusted_mask[pid],
                            roi_bbox=(x0, x1, y0, y1),
                        )
                        mask_array = detector_config.mask_array
                        if mask_array is not None and not isinstance(mask_array, torch.Tensor):
                            detector_config.mask_array = torch.tensor(mask_array, dtype=torch.float32, device=device)
                        elif mask_array is not None and (mask_array.device != device or mask_array.dtype != torch.float32):
                            detector_config.mask_array = mask_array.to(device=device, dtype=torch.float32)
                        from nanobrag_torch.models.detector import Detector
                        detector_model = Detector(detector_config, device=device, dtype=dtype)

                        crystal_config, _ = create_crystal_config(
                            crystal,
                            None,
                            crystal_overrides=crystal_overrides,
                            misset_deg_override=misset_deg_for_crystal
                        )
                        from nanobrag_torch.models.crystal import Crystal
                        crystal_model = Crystal(
                            crystal_config,
                            beam_config=beam_config_for_run,
                            device=device,
                            dtype=dtype
                        )
                        crystal_model.interpolate = config.enable_hkl_interpolation
                        crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
                        crystal_model.hkl_metadata = hkl_metadata

                        from nanobrag_torch.simulator import Simulator
                        simulator = Simulator(
                            detector=detector_model,
                            crystal=crystal_model,
                            beam_config=beam_config_for_run,
                            device=device,
                            dtype=dtype
                        )

                    bragg_patch = simulator.run()
                    bragg_scaled = bragg_patch * torch.exp(log_scale_clamped)

                    # NOTE: In the current Stage A implementation, `bragg_scaled` plays the role
                    # of I_model in the variance term while `target_subset` is background-subtracted
                    # I_obs. Spec-DB core defines I_model as Bragg+background on raw data; see
                    # docs/config_crosswalk.md "I_model" mapping and TODO‑PHYSICS for planned
                    # reconciliation.
                    chi_sq_roi, mse_roi, masked_pixels, clamped_pixels = _compute_variance_weighted_loss(
                        bragg_scaled,
                        target_subset,
                        mask_subset,
                        sigma_subset,
                        sigma_floor_sq_tensor,
                    )

                    # Telemetry: Capture I_model, V_denom, and weighted residuals (TORCH-GEOMETRY-CONVERGENCE-001 Phase B2)
                    if not is_full and getattr(config, "telemetry_output_dir", None) and config.use_u_matrix_parameterization:
                        # I_model stats
                        i_model_values = bragg_scaled[mask_subset]
                        i_model_min_global = min(i_model_min_global, torch.min(bragg_scaled).item())
                        i_model_max_global = max(i_model_max_global, torch.max(bragg_scaled).item())
                        i_model_values_list.append(i_model_values.detach().cpu())

                        # V_denom (variance denominator) stats
                        variance_raw = bragg_scaled.detach() + sigma_subset ** 2
                        v_denom = torch.maximum(variance_raw, sigma_floor_sq_tensor)
                        v_denom_values_list.append(v_denom[mask_subset].detach().cpu())

                        # Weighted residuals stats
                        diff = bragg_scaled - target_subset
                        squared_error = diff ** 2
                        weighted_error = squared_error / v_denom
                        weighted_residuals_list.append(weighted_error[mask_subset].detach().cpu())
                    chi_squared_accum = chi_squared_accum + chi_sq_roi
                    mse_numerator_accum = mse_numerator_accum + (mse_roi * masked_pixels)
                    masked_pixels_total += masked_pixels
                    clamped_pixels_total += clamped_pixels

                if masked_pixels_total > 0:
                    masked_mse_loss = mse_numerator_accum / masked_pixels_total
                else:
                    masked_mse_loss = mse_numerator_accum
                chi_squared_loss = chi_squared_accum

                # Telemetry: Capture loss components and variance stats (TORCH-GEOMETRY-CONVERGENCE-001 Phase B2)
                if not is_full and getattr(config, "telemetry_output_dir", None) and config.use_u_matrix_parameterization:
                    clamp_fraction = clamped_pixels_total / max(masked_pixels_total, 1)
                    mean_per_pixel_chi_squared = chi_squared_loss.item() / max(masked_pixels_total, 1)

                    telemetry_loss = {
                        'chi_squared': chi_squared_loss.item(),
                        'mean_per_pixel_chi_squared': mean_per_pixel_chi_squared,
                        'masked_mse': masked_mse_loss.item() if masked_pixels_total > 0 else 0.0,
                        'masked_pixels': masked_pixels_total,
                        'clamped_pixels': clamped_pixels_total,
                        'clamp_fraction': clamp_fraction,
                    }

                    # Compute variance component statistics
                    if i_model_values_list:
                        i_model_all = torch.cat(i_model_values_list)
                        v_denom_all = torch.cat(v_denom_values_list)
                        weighted_residuals_all = torch.cat(weighted_residuals_list)

                        telemetry_variance = {
                            'i_model_min': i_model_min_global,
                            'i_model_median': torch.median(i_model_all).item(),
                            'i_model_max': i_model_max_global,
                            'i_model_mean': torch.mean(i_model_all).item(),
                            'i_model_std': torch.std(i_model_all).item() if i_model_all.numel() > 1 else 0.0,
                            'v_denom_min': torch.min(v_denom_all).item(),
                            'v_denom_median': torch.median(v_denom_all).item(),
                            'v_denom_max': torch.max(v_denom_all).item(),
                            'weighted_residuals_min': torch.min(weighted_residuals_all).item(),
                            'weighted_residuals_median': torch.median(weighted_residuals_all).item(),
                            'weighted_residuals_max': torch.max(weighted_residuals_all).item(),
                            'weighted_residuals_mean': torch.mean(weighted_residuals_all).item(),
                        }
                    else:
                        telemetry_variance = {
                            'i_model_min': None,
                            'i_model_median': None,
                            'i_model_max': None,
                            'i_model_mean': None,
                            'i_model_std': None,
                            'v_denom_min': None,
                            'v_denom_median': None,
                            'v_denom_max': None,
                            'weighted_residuals_min': None,
                            'weighted_residuals_median': None,
                            'weighted_residuals_max': None,
                            'weighted_residuals_mean': None,
                        }

                # Track the latest variance-floor statistics for telemetry (no accumulation)
                variance_floor_clamped_pixels[0] = clamped_pixels_total
                variance_floor_masked_pixels[0] = masked_pixels_total
            else:
                # ARCH-REFINE-001 / PERF-WARM-SIM-001: Panel-mode loss computation
                # When force_panel_eval is True, always use panel IDs (not ROI indices)
                # work_item_ids may contain ROI indices when forcing panel mode from ROI-enabled runs (REFINE-007)
                if force_panel_eval:
                    panel_ids = list(range(n_panels))
                else:
                    panel_ids = work_item_ids if work_item_ids else list(range(n_panels))

                # PERF-WARM-SIM-001: Collect per-panel diagnostics when env var is set and forced panel validation is active
                panel_diag_collector = None
                if panel_diag_enabled and is_full:
                    panel_diag_collector = []

                # Call shared helper for panel-mode loss (Stage A / Stage C parity, PERF-WARM-SIM-001)
                (
                    chi_squared_loss,
                    masked_mse_loss,
                    masked_pixels,
                    clamped_pixels,
                ) = _compute_panel_loss(
                    panel_ids=panel_ids,
                    stage_a_ctx=stage_a_ctx,
                    detector=detector,
                    beam=beam,
                    crystal=crystal,
                    crystal_overrides=crystal_overrides,
                    misset_deg_for_crystal=misset_deg_for_crystal,
                    beam_config_for_run=beam_config_for_run,
                    hkl_grid=hkl_grid,
                    hkl_metadata=hkl_metadata,
                    config=config,
                    log_scale_clamped=log_scale_clamped,
                    target_t=target_t,
                    loss_mask_t=loss_mask_t,
                    sigma_readout_t=sigma_readout_t,
                    sigma_floor_sq_tensor=sigma_floor_sq_tensor,
                    device=device,
                    dtype=dtype,
                    trusted_mask_array=inputs.trusted_mask,
                    panel_diag=panel_diag_collector,
                )

                # Store collected diagnostics in telemetry_state (ARCH-STAGE-CONTEXT-001 Phase E: dataclass-only)
                if panel_diag_collector is not None:
                    telemetry_state.panel_loss_diag.extend(panel_diag_collector)
                # Track the latest variance-floor statistics for telemetry (no accumulation)
                variance_floor_clamped_pixels[0] = clamped_pixels
                variance_floor_masked_pixels[0] = masked_pixels

            if not is_full:  # Only track closure forward times, not validation
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                perf_forward_times_ms.append(elapsed_ms)

            return chi_squared_loss, masked_mse_loss

        def closure():
            """LBFGS closure: recompute loss and gradients."""
            optimizer = param_values.get('optimizer')
            optimizer.zero_grad()

            # Compute loss on sampled ROIs or panels depending on mode
            chi_squared_loss, masked_mse_loss = compute_loss(sampled_stage_a_indices, is_full=False)

            # Backward pass (optimize chi_squared, not MSE)
            chi_squared_loss.backward()

            # Check for NaN/Inf gradients
            for p in params:
                if p.grad is not None and (torch.isnan(p.grad).any() or torch.isinf(p.grad).any()):
                    raise RuntimeError(f"NaN/Inf gradient detected in {p}")

            # Telemetry: Capture gradients and emit JSON (TORCH-GEOMETRY-CONVERGENCE-001 Phase B2)
            if getattr(config, "telemetry_output_dir", None) and config.use_u_matrix_parameterization:
                # Capture detailed gradient statistics
                if q_params.grad is not None:
                    q_grad_has_nan = bool(torch.isnan(q_params.grad).any().item())
                    q_grad_has_inf = bool(torch.isinf(q_params.grad).any().item())
                    q_grad_norm = torch.norm(q_params.grad).item()
                    q_grad_min = torch.min(q_params.grad).item()
                    q_grad_max = torch.max(q_params.grad).item()
                    q_grad_mean = torch.mean(q_params.grad).item()
                    q_grad_std = torch.std(q_params.grad).item() if q_params.grad.numel() > 1 else 0.0
                    # Sign consistency: count positive vs negative elements
                    q_grad_positive_count = int((q_params.grad > 0).sum().item())
                    q_grad_negative_count = int((q_params.grad < 0).sum().item())
                else:
                    q_grad_has_nan = None
                    q_grad_has_inf = None
                    q_grad_norm = None
                    q_grad_min = None
                    q_grad_max = None
                    q_grad_mean = None
                    q_grad_std = None
                    q_grad_positive_count = None
                    q_grad_negative_count = None

                if log_scale.grad is not None:
                    log_scale_grad_has_nan = bool(torch.isnan(log_scale.grad).any().item())
                    log_scale_grad_has_inf = bool(torch.isinf(log_scale.grad).any().item())
                    log_scale_grad_norm = torch.norm(log_scale.grad).item()
                    log_scale_grad_value = log_scale.grad.item()
                else:
                    log_scale_grad_has_nan = None
                    log_scale_grad_has_inf = None
                    log_scale_grad_norm = None
                    log_scale_grad_value = None

                telemetry_gradients = {
                    'log_scale': {
                        'norm': log_scale_grad_norm,
                        'value': log_scale_grad_value,
                        'has_nan': log_scale_grad_has_nan,
                        'has_inf': log_scale_grad_has_inf,
                    },
                    'q_params': {
                        'norm': q_grad_norm,
                        'min': q_grad_min,
                        'max': q_grad_max,
                        'mean': q_grad_mean,
                        'std': q_grad_std,
                        'positive_count': q_grad_positive_count,
                        'negative_count': q_grad_negative_count,
                        'has_nan': q_grad_has_nan,
                        'has_inf': q_grad_has_inf,
                    },
                }

                # Combine all telemetry with structured format per input.md Phase B2
                # Note: telemetry_params, telemetry_loss, telemetry_variance are nonlocal from compute_loss
                telemetry_step = {
                    'step': telemetry_params['step_index'],
                    'parameters': {
                        'log_scale': telemetry_params['log_scale'],
                        'q_params': telemetry_params['q_params'],
                        'q_norm': telemetry_params['q_norm_value'],
                        'u_matrix_checksum': telemetry_params['u_matrix_checksum'],
                    },
                    'gradients': telemetry_gradients,
                    'variance': telemetry_variance,
                    'loss': telemetry_loss,
                }

                # Emit telemetry JSON
                import json
                from pathlib import Path
                try:
                    telemetry_path = Path(getattr(config, "telemetry_output_dir", None)) / f"telemetry_step_{telemetry_step_counter[0]:03d}.json"
                    telemetry_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(telemetry_path, 'w') as f:
                        json.dump(telemetry_step, f, indent=2)
                except Exception as e:
                    import sys
                    print(f"Warning: Failed to write telemetry JSON: {e}", file=sys.stderr)

                # Increment step counter
                telemetry_step_counter[0] += 1

            # ARCH-TELEMETRY-001 Phase B.1: Record telemetry via collector instead of direct mutations
            # Build metrics dict for observer callback
            metrics = {
                'chi_squared': float(chi_squared_loss.item()),
                'masked_mse': float(masked_mse_loss.item()),
                # Variance floor stats updated incrementally via collector.on_step
                # (forward_time_ms captured in compute_loss if needed)
            }
            collector.on_step(
                iteration=iteration_count[0],
                loss=float(chi_squared_loss.item()),
                metrics=metrics,
            )

            # Periodic full validation
            if iteration_count[0] % config.full_validation_interval == 0:
                with torch.no_grad():
                    # ARCH-REFINE-001: Use panel mode for periodic validations when force_panel_validation is True (REFINE-007)
                    full_chi_squared, full_mse = compute_loss(full_stage_a_indices, is_full=True, force_panel_eval=force_panel_validation)

                    # ARCH-TELEMETRY-001 Phase B.1: Build best snapshot if improved
                    nonlocal best_params_snapshot, chi_squared_best
                    best_snapshot = None
                    if full_chi_squared.item() < chi_squared_best[0]:
                        # Compute misset XYZ for snapshot (TORCH-REFINE-002)
                        max_orientation_deg = 3.0
                        bounded_orientation_vec_snap = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
                        quat_snap = vec_to_unit_quaternion(bounded_orientation_vec_snap)
                        misset_xyz_deg_snap = quaternion_to_xyz_euler(quat_snap)

                        best_snapshot = {
                            'log_scale': float(log_scale.item()),
                            'log_cell_a_delta': float(log_cell_a_delta.item()),
                            'log_cell_b_delta': float(log_cell_b_delta.item()),
                            'log_cell_c_delta': float(log_cell_c_delta.item()),
                            'angle_alpha_raw': float(angle_alpha_raw.item()),
                            'angle_beta_raw': float(angle_beta_raw.item()),
                            'angle_gamma_raw': float(angle_gamma_raw.item()),
                            'orientation_vec': orientation_vec.detach().cpu().tolist(),
                            'misset_xyz_deg': misset_xyz_deg_snap.detach().cpu().tolist()
                        }

                    # ARCH-TELEMETRY-001 Phase B.1: Record validation via collector
                    scope = "panel" if force_panel_validation else "roi"
                    payload = {
                        'loss': float(full_chi_squared.item()),
                        'masked_mse': float(full_mse.item()),
                        'best_snapshot': best_snapshot,
                    }
                    collector.on_validation(
                        scope=scope,
                        chi2=float(full_chi_squared.item()),
                        payload=payload,
                    )

            iteration_count[0] += 1

            # Emit lifecycle JSON (TORCH-GEOMETRY-CONVERGENCE-001 Phase B4)
            if getattr(config, "telemetry_output_dir", None) and config.use_u_matrix_parameterization:
                import json
                from pathlib import Path
                try:
                    lifecycle_path = Path(getattr(config, "telemetry_output_dir", None)) / f"u_matrix_lifecycle_step_{telemetry_step_counter[0]-1:03d}.json"
                    lifecycle_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(lifecycle_path, 'w') as f:
                        json.dump({
                            "u_matrix_lifecycle": u_matrix_lifecycle_log,
                            "a_star_lifecycle": a_star_lifecycle_log
                        }, f, indent=2)
                except Exception as e:
                    import sys
                    print(f"Warning: Failed to write lifecycle JSON: {e}", file=sys.stderr)

            return chi_squared_loss

        return compute_loss, closure

    def run(
        self,
        inputs: Any,
        telemetry_sink: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Execute Stage A LBFGS refinement calling extracted helpers directly.

        Args:
            inputs: Dict with keys:
                - 'refinement_inputs': RefinementInputs (target, loss_mask, panel_slices, etc.)
                - 'detector': dxtbx Detector object
                - 'beam': dxtbx Beam object
                - 'crystal': dxtbx Crystal object
                - 'hkl_grid': torch.Tensor structure factor grid
                - 'hkl_metadata': dict with grid dimensions
                - 'baseline_crystal': Optional baseline dxtbx Crystal for misset extraction
                - 'baseline_detector': Optional baseline dxtbx Detector for Stage C telemetry
            telemetry_sink: Optional path for telemetry output (unused by this implementation,
                           telemetry returned via dict instead)

        Returns:
            Telemetry dict with all required RefinementTelemetry fields plus:
            - stage_type: "stage_a"
            - mode: None (or "incremental_ub"/"u_matrix" if those modes are enabled)

        Raises:
            RuntimeError: If simulator fails or gradients are NaN/Inf
            ValueError: If config not set via configure()
        """
        if self._config is None:
            raise ValueError("StageA not configured. Call configure(config) before run().")

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
            baseline_crystal = inputs.get('baseline_crystal', None)
            baseline_detector = inputs.get('baseline_detector', None)

        # Extract device/dtype from config
        device = self._config.device
        dtype = self._config.dtype

        # Build sigma_floor_sq_cache (Stage A warmup)
        # CRITICAL: This dict MUST match the construction in run_nanobrag_refinement
        # (dbex/nanobrag_refinement.py line 2195: empty dict, populated by _get_sigma_floor_sq_tensor)
        sigma_floor_sq_cache = {}

        # Compute baseline_misset_deg_tensor if baseline_crystal provided
        # (Matches run_nanobrag_refinement logic lines ~1958-1968)
        baseline_misset_deg_tensor = None
        if baseline_crystal is not None:
            from dbex.nanobrag_bridge import compute_baseline_misset_deg
            baseline_misset_deg_tensor = compute_baseline_misset_deg(
                crystal, baseline_crystal, device=device, dtype=dtype
            )

        # STEP 1: Build Stage A parameters
        helper1_result = _build_stage_a_params(
            crystal=crystal,
            detector=detector,
            inputs=refinement_inputs,
            config=self._config,
            device=device,
            dtype=dtype,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            sigma_floor_sq_cache=sigma_floor_sq_cache,
            baseline_crystal=baseline_crystal,
            baseline_detector=baseline_detector,
            beam=beam
        )

        # Unpack helper1 result
        params = helper1_result['params']
        param_values = helper1_result['param_values']
        telemetry_state = helper1_result['telemetry_state']
        stage_a_context = helper1_result['stage_a_context']
        optimizer = helper1_result['optimizer']

        # Extract needed variables for helper 2/3 calls and telemetry assembly
        initial_log_scale = param_values['initial_log_scale']
        log_scale = param_values['log_scale']
        log_cell_a_delta = param_values['log_cell_a_delta']
        log_cell_b_delta = param_values['log_cell_b_delta']
        log_cell_c_delta = param_values['log_cell_c_delta']
        log_scale_baseline = param_values.get('log_scale_baseline')
        log_scale_baseline_source = param_values.get('log_scale_baseline_source')  # TOOLING-VIS-001 Phase E
        spot_scale_override_adjustment_factor = param_values.get('spot_scale_override_adjustment_factor')  # TOOLING-VIS-001 Phase E
        target_mean_masked = param_values.get('target_mean_masked')  # TOOLING-VIS-001 Phase D.E
        model_mean_masked = param_values.get('model_mean_masked')  # TOOLING-VIS-001 Phase D.E
        angle_alpha_raw = param_values['angle_alpha_raw']
        angle_beta_raw = param_values['angle_beta_raw']
        angle_gamma_raw = param_values['angle_gamma_raw']
        orientation_vec = param_values['orientation_vec']
        canonical_baseline = stage_a_context['canonical_baseline']
        full_stage_a_indices = stage_a_context['full_stage_a_indices']
        stage_a_roi_label = stage_a_context['stage_a_roi_label']
        stage_a_total_work_items = stage_a_context['stage_a_total_work_items']
        sampled_stage_a_indices = stage_a_context['sampled_stage_a_indices']
        masked_pixel_reference = int(refinement_inputs.loss_mask.sum())

        # ARCH-STAGE-CONTEXT-001 Phase E: Extract telemetry fields (dataclass-only)
        perf_closure_evals = telemetry_state.perf_closure_evals
        perf_validation_runs = telemetry_state.perf_validation_runs
        perf_forward_times_ms = telemetry_state.perf_forward_times_ms
        variance_floor_clamped_pixels = telemetry_state.variance_floor_clamped_pixels
        variance_floor_masked_pixels = telemetry_state.variance_floor_masked_pixels
        loss_trace_sample = telemetry_state.loss_trace_sample
        loss_trace_full = telemetry_state.loss_trace_full
        best_loss_full = telemetry_state.best_loss_full
        chi_squared_trace_sample = telemetry_state.chi_squared_trace_sample
        chi_squared_trace_full = telemetry_state.chi_squared_trace_full
        chi_squared_best = telemetry_state.chi_squared_best
        masked_mse_trace_sample = telemetry_state.masked_mse_trace_sample
        masked_mse_trace_full = telemetry_state.masked_mse_trace_full
        masked_mse_best = telemetry_state.masked_mse_best

        # ARCH-REFINE-001 Phase E.2: Compute force_panel_validation flag (REFINE-FLOW-001, REFINE-007)
        # Switch Stage A baseline/final validations to panel mode whenever Stage B or Stage C runs,
        # or when ROI count is small (≤32), so Stage A telemetry reports panel-level chi² that
        # matches Stage B/C initial states. This ensures REFINE-FLOW-001 parity (Stage B initial chi²
        # must match Stage A final within 0.1%) holds for ROI-heavy configs where ROI sampling would
        # prevent Stage A from seeing the full-panel convergence that Stage B will use.
        canonical_roi_count = len(refinement_inputs.panel_slices)
        force_panel_validation = (
            self._config.stage_a_force_panel_validation or
            self._config.enable_stage_b or
            self._config.enable_stage_c or
            canonical_roi_count <= self._config.stage_a_panel_validation_roi_threshold
        )
        # Stash flag on context for closure builder
        stage_a_context['force_panel_validation'] = force_panel_validation

        # ARCH-STAGE-CONTEXT-001: Build RefinementSharedContext to replace 11-parameter data clump
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

        # STEP 2: Build Stage A LBFGS closure
        # ARCH-TELEMETRY-001 Phase B.1: Instantiate StageATelemetryCollector
        from .telemetry_collectors import StageATelemetryCollector
        collector = StageATelemetryCollector(state=telemetry_state)

        # ARCH-STAGE-CONTEXT-001 Phase B.2: Call inlined StageA._build_lbfgs_closure
        compute_loss, closure = self._build_lbfgs_closure(
            param_values=param_values,
            telemetry_state=telemetry_state,
            stage_a_context=stage_a_context,
            shared_context=shared_context,
            collector=collector,
        )

        # STEP 3: Run Stage A LBFGS optimization
        # ARCH-TELEMETRY-001 Phase B.1: Pass collector for baseline/final/exception validations
        status, message, final_chi_squared_value, final_masked_mse_value, best_params_snapshot = _run_stage_a_lbfgs(
            compute_loss=compute_loss,
            closure=closure,
            optimizer=optimizer,
            params=params,
            telemetry_state=telemetry_state,
            config=self._config,
            canonical_baseline=canonical_baseline,
            full_stage_a_indices=full_stage_a_indices,
            log_scale=log_scale,
            log_cell_a_delta=log_cell_a_delta,
            log_cell_b_delta=log_cell_b_delta,
            log_cell_c_delta=log_cell_c_delta,
            angle_alpha_raw=angle_alpha_raw,
            angle_beta_raw=angle_beta_raw,
            angle_gamma_raw=angle_gamma_raw,
            orientation_vec=orientation_vec,
            device=device,
            dtype=dtype,
            masked_pixel_reference=int(refinement_inputs.loss_mask.sum()),
            force_panel_validation=force_panel_validation,
            collector=collector,
        )

        log_cell_max_delta = getattr(self._config, 'log_cell_max_delta', 1.0)
        log_cell_a_delta_clamped = torch.clamp(
            log_cell_a_delta, min=-log_cell_max_delta, max=log_cell_max_delta
        )
        log_cell_b_delta_clamped = torch.clamp(
            log_cell_b_delta, min=-log_cell_max_delta, max=log_cell_max_delta
        )
        log_cell_c_delta_clamped = torch.clamp(
            log_cell_c_delta, min=-log_cell_max_delta, max=log_cell_max_delta
        )

        # Build param_deltas dict for telemetry (matches run_nanobrag_refinement lines 2156-2198)
        param_deltas = {
            'log_scale': {
                'initial': initial_log_scale,
                'final': float(log_scale.item()),
                'delta': float(log_scale.item()) - initial_log_scale
            },
            'log_scale_baseline': {
                'initial': log_scale_baseline if log_scale_baseline is not None else 0.0,
                'final': log_scale_baseline if log_scale_baseline is not None else 0.0,
            },
            'log_cell_a_delta': {
                'initial': 0.0,
                'final': float(log_cell_a_delta_clamped.item()),
                'delta': float(log_cell_a_delta_clamped.item())
            },
            'log_cell_b_delta': {
                'initial': 0.0,
                'final': float(log_cell_b_delta_clamped.item()),
                'delta': float(log_cell_b_delta_clamped.item())
            },
            'log_cell_c_delta': {
                'initial': 0.0,
                'final': float(log_cell_c_delta_clamped.item()),
                'delta': float(log_cell_c_delta_clamped.item())
            },
            'angle_alpha_raw': {
                'initial': 0.0,
                'final': float(angle_alpha_raw.item()),
                'delta': float(angle_alpha_raw.item())
            },
            'angle_beta_raw': {
                'initial': 0.0,
                'final': float(angle_beta_raw.item()),
                'delta': float(angle_beta_raw.item())
            },
            'angle_gamma_raw': {
                'initial': 0.0,
                'final': float(angle_gamma_raw.item()),
                'delta': float(angle_gamma_raw.item())
            },
            'orientation_vec': {
                'initial': [0.0, 0.0, 0.0],
                'final': orientation_vec.detach().cpu().tolist(),
                'delta': orientation_vec.detach().cpu().tolist(),
                'norm': float(orientation_vec.norm().item())
            }
        }

        # Compute final misset XYZ degrees for telemetry (TORCH-REFINE-002)
        with torch.no_grad():
            max_orientation_deg = 3.0
            bounded_orientation_vec_final = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
            quat_final = vec_to_unit_quaternion(bounded_orientation_vec_final)
            misset_xyz_deg_final = quaternion_to_xyz_euler(quat_final)

            # Add baseline misset from perturbed geometry if provided (TORCH-REFINE-002D)
            if baseline_misset_deg_tensor is not None:
                misset_xyz_deg_final_total = misset_xyz_deg_final + baseline_misset_deg_tensor
                initial_misset = baseline_misset_deg_tensor.cpu().tolist()
            else:
                misset_xyz_deg_final_total = misset_xyz_deg_final
                initial_misset = [0.0, 0.0, 0.0]

            # Add misset telemetry
            param_deltas['misset_xyz_deg'] = {
                'initial': initial_misset,
                'final': misset_xyz_deg_final_total.cpu().tolist(),
                'delta': misset_xyz_deg_final.cpu().tolist(),
                'quaternion_norm': float(quat_final.norm().item())
            }

        # Build perf counters payload (PERF-WARM-SIM-001)
        cache_mode = "warm" if self._config.enable_stage_a_warm_cache else "cold"
        perf_counters = {
            'cache_mode': cache_mode,
            'roi_mode': stage_a_roi_label,
            'roi_count_total': stage_a_total_work_items,
            'roi_count_sampled': len(sampled_stage_a_indices),
            'closure_evals': perf_closure_evals[0],
            'validation_runs': perf_validation_runs[0],
            'forward_time_ms': {
                'mean': float(np.mean(perf_forward_times_ms)) if perf_forward_times_ms else 0.0,
                'min': float(np.min(perf_forward_times_ms)) if perf_forward_times_ms else 0.0,
                'max': float(np.max(perf_forward_times_ms)) if perf_forward_times_ms else 0.0,
                'total': float(np.sum(perf_forward_times_ms)) if perf_forward_times_ms else 0.0
            },
            # REFINE-011: Tag validation scope so Stage C knows whether to use panel mode for full validations
            'validation_scope': "panel" if force_panel_validation else "roi"
        }

        # ARCH-REFINE-001, REFINE-010: Add ROI mode reason to explain auto-panel switching
        if stage_a_roi_label == "panel":
            if not self._config.enable_stage_a_roi_mode:
                perf_counters['roi_mode_reason'] = "config_disabled"
            elif canonical_roi_count <= self._config.stage_a_min_roi_for_roi_mode:
                perf_counters['roi_mode_reason'] = f"auto_panel_threshold (roi_count={canonical_roi_count} <= {self._config.stage_a_min_roi_for_roi_mode})"
            elif not (self._config.enable_stage_a_warm_cache or self._config.allow_cold_stage_a_roi_mode):
                perf_counters['roi_mode_reason'] = "warm_cache_disabled"
            else:
                perf_counters['roi_mode_reason'] = "panel_mode_default"
        else:
            perf_counters['roi_mode_reason'] = f"roi_mode_active (roi_count={canonical_roi_count} > {self._config.stage_a_min_roi_for_roi_mode})"

        # Assemble RefinementTelemetry object (matches run_nanobrag_refinement lines 2241-2280)
        telemetry_a = RefinementTelemetry(
            optimizer="LBFGS",
            stage="A",
            history_size=self._config.history_size,
            max_iter=self._config.max_iter,
            tolerance_grad=self._config.tolerance_grad,
            tolerance_change=self._config.tolerance_change,
            roi_sample_fraction=self._config.roi_sample_fraction,
            roi_count_sampled=len(sampled_stage_a_indices),
            roi_count_total=stage_a_total_work_items,
            loss_trace_sample=loss_trace_sample,
            loss_trace_full=loss_trace_full,
            best_loss_full=best_loss_full,
            param_deltas=param_deltas,
            status=status,
            message=message,
            perf_counters=perf_counters,
            # PHYSICS-LOSS-001: Dual loss metrics
            chi_squared_trace_sample=chi_squared_trace_sample,
            chi_squared_trace_full=chi_squared_trace_full,
            chi_squared_best=chi_squared_best,
            masked_mse_trace_sample=masked_mse_trace_sample,
            masked_mse_trace_full=masked_mse_trace_full,
            masked_mse_best=masked_mse_best,
            sigma_readout_provenance=self._config.sigma_readout_provenance,
            sigma_readout_reference_value=self._config.sigma_readout_reference_value,
            # PHYSICS-LOSS-002: Variance floor telemetry
            variance_floor_value=self._config.sigma_floor_value**2,
            variance_floor_clamp_fraction=(
                float(variance_floor_clamped_pixels[0]) / float(masked_pixel_reference)
                if masked_pixel_reference > 0 else 0.0
            ),
            variance_floor_masked_pixels=int(masked_pixel_reference),
            variance_floor_clamped_pixels=int(variance_floor_clamped_pixels[0]),
            # SCALE-008 / TOOLING-VIS-001 Phase E: Mapping-aware log-scale baseline telemetry
            log_scale_baseline_source=log_scale_baseline_source,
            spot_scale_override_adjustment_factor=spot_scale_override_adjustment_factor,
            # TOOLING-VIS-001 Phase D.E: Masked-mean telemetry for Stage A baseline derivation
            target_mean_masked=target_mean_masked,
            model_mean_masked=model_mean_masked,
            # PHYSICS-LOSS-003: Canonical Stage A metadata
            canonical_stage_label=canonical_baseline["stage_label"],
            canonical_chi_squared=canonical_baseline["chi_squared"],
            canonical_chi_squared_iteration=canonical_baseline["iteration"],
            canonical_roi_count=canonical_baseline["roi_count"],
            canonical_detector_distances_mm=canonical_baseline["detector_distances_mm"],
            roi_mode=stage_a_roi_label,
        )

        # Convert to dict for engine aggregation
        telemetry_output = asdict(telemetry_a)

        # Add Phase A4 stage identification fields
        telemetry_output["stage_type"] = "stage_a"

        # Determine mode based on config flags
        if self._config.use_incremental_ub:
            telemetry_output["mode"] = "incremental_ub"
        elif self._config.use_u_matrix_parameterization:
            telemetry_output["mode"] = "u_matrix"
        else:
            telemetry_output["mode"] = None  # Default cell+misset path

        # ARCH-STAGE-CONTEXT-001 Phase B.1: Extract stage_a_ctx into artifacts
        stage_a_ctx = stage_a_context.get('stage_a_ctx', None)

        # ARCH-STAGE-CONTEXT-001 Phase D: Compute final Bragg when Stage A is terminal
        # Stage A is terminal when both Stage B and Stage C are disabled
        bragg_full_artifact = None
        is_terminal_stage = (not self._config.enable_stage_b) and (not self._config.enable_stage_c)
        if is_terminal_stage:
            # Import reconstruction helper
            from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry
            # Build final Bragg from Stage A telemetry using the shared helper
            bragg_full_artifact = build_final_bragg_from_stage_a_telemetry(
                telemetry_a=telemetry_output,
                detector=detector,
                beam=beam,
                crystal=crystal,
                inputs=refinement_inputs,
                hkl_grid=hkl_grid,
                hkl_metadata=hkl_metadata,
                config=self._config,
                device=device,
                dtype=dtype,
                stage_a_ctx=stage_a_ctx,
                baseline_crystal=baseline_crystal,
            )

        # Create StageAArtifacts with warm context payload + optional final Bragg
        artifacts = StageAArtifacts(
            stage_a_ctx=stage_a_ctx,
            context_schema_version="v1",
            bragg_full=bragg_full_artifact
        ) if stage_a_ctx is not None else None

        # Return StageResult with telemetry dict and artifacts
        # Engine will convert telemetry dict to RefinementTelemetry and cache artifacts
        return StageResult(
            telemetry=telemetry_output,
            artifacts=artifacts
        )
