# dbex/refinement/stage_b.py
"""
Stage B implementation for Protocol-based Refinement Engine.

Wraps existing LBFGS closure logic from run_nanobrag_refinement into a RefinementStage class
per docs/spec-db-workflow.md §7 (Refinement Protocol Architecture) and
ARCH-REFINE-FLOW-001 Phase C1b.

Stage B optimizes:
- shell_modifier_raw: Per-shell structure factor multipliers (softplus parameterization)

Freezes Stage A parameters (log_scale, cell, misset) from stage_a_telemetry input.

Dependencies (ARCH-REFINE-001 eager import refactoring):
- dbex.refinement.stage_b_impl: Stage B LBFGS helpers (_build_stage_b_params, closures, ASU/shell utilities)
- dbex.refinement.stage: RefinementTelemetry dataclass for telemetry serialization
- dbex.nanobrag_bridge: Factory functions for detector/crystal config and baseline misset computation
- nanobrag_torch.models: Detector and Crystal models for simulator construction
- nanobrag_torch.simulator: Simulator class for forward model evaluation
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import time
import torch

# ARCH-REFINE-001: Eager imports at module scope to eliminate lazy-import pattern
from dbex.refinement.artifacts import StageBArtifacts
from dbex.refinement.stage import RefinementTelemetry, StageResult
from dbex.refinement.stage_b_impl import (
    _build_stage_b_params,
    _run_stage_b_lbfgs,
    # ARCH-STAGE-CONTEXT-001 Phase B.2: Closure builder moved to StageB._build_lbfgs_closure
    _retarget_stage_a_simulators,
    _get_sigma_floor_sq_tensor,
    apply_asu_modifiers,
)
from dbex.refinement.context import RefinementSharedContext
from dbex.refinement.telemetry_collectors import StageBTelemetryCollector
from dbex.physics.loss import _compute_variance_weighted_loss
from dbex.refinement.config_factories import (
    create_detector_config,
    create_crystal_config,
)
from dbex.nanobrag_bridge import compute_baseline_misset_deg
from nanobrag_torch.models import Detector, Crystal
from nanobrag_torch.simulator import Simulator


class StageB:
    """
    Stage B: Structure factor shell modifier refinement (LBFGS).

    Implements RefinementStage protocol per spec-db-workflow.md:33.
    Wraps existing inline LBFGS closure logic from run_nanobrag_refinement.

    Attributes:
        _name: Stage identifier ("stage_b")
        _config: Optional RefinementConfig (set via configure())
    """

    def __init__(self):
        """Initialize Stage B with default name."""
        self._name = "stage_b"
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
                   warm-cache flags, ROI sampling, Stage B shell count, max modifier, etc.
        """
        self._config = config

    def _build_lbfgs_closure(
        self,
        shared_context: RefinementSharedContext,
        param_values: Dict[str, Any],
        stage_a_ctx: Optional[Any],
        stage_b_eval_stage_a_ctx: Optional[Any],
        canonical_baseline: Dict[str, Any],
        sampled_stage_b_indices: List[int],
        full_stage_b_indices: List[int],
        use_stage_b_cpu_fallback: bool,
        stage_b_use_warm_cache: bool,
        use_stage_b_roi_mode: bool,
        shell_indices: Optional[torch.Tensor],
        baseline_misset_deg_tensor: Optional[torch.Tensor],
        collector: Optional[Any] = None,
    ) -> Tuple[Callable[[List[int], bool, bool], Tuple[torch.Tensor, torch.Tensor]], Callable[[], torch.Tensor]]:
        """
        Build LBFGS closure for Stage B shell modifier refinement.

        ARCH-STAGE-CONTEXT-001 Phase B.2: Moved from stage_b_impl._build_stage_b_lbfgs_closure.
        Now owned by StageB class to eliminate 11-argument helper export.

        Args:
            shared_context: RefinementSharedContext dataclass with config/device/dtype/crystal/detector/beam/
                           inputs/hkl_grid/hkl_metadata/sigma_floor_sq_cache
            param_values: Dict with trainable tensors and telemetry accumulators
            stage_a_ctx: Optional Stage A context for warm cache
            stage_b_eval_stage_a_ctx: Optional CPU fallback Stage A context
            canonical_baseline: Dict with Stage A final state for parity checks
            sampled_stage_b_indices: List of sampled ROI indices
            full_stage_b_indices: List of all ROI indices
            use_stage_b_cpu_fallback: Bool flag for CPU fallback
            stage_b_use_warm_cache: Bool flag for warm cache
            use_stage_b_roi_mode: Bool flag for ROI mode
            shell_indices: Tensor of shell indices for shell mode (required for shell mode)
            baseline_misset_deg_tensor: Optional baseline misset tensor

        Returns:
            Tuple of (compute_loss_stage_b, closure_stage_b):
            - compute_loss_stage_b: Callable for manual loss evaluation (used for final validation).
            - closure_stage_b: Callable for LBFGS optimizer.
        """
        # Extract shared parameters from context
        config = shared_context.config
        device = shared_context.device
        dtype = shared_context.dtype
        crystal = shared_context.crystal
        detector = shared_context.detector
        beam = shared_context.beam
        inputs = shared_context.inputs
        hkl_grid = shared_context.hkl_grid
        hkl_metadata = shared_context.hkl_metadata
        sigma_floor_sq_cache = shared_context.sigma_floor_sq_cache

        # Compute derived tensors from inputs (on-demand conversion)
        if isinstance(inputs.target, np.ndarray):
            target_t = torch.from_numpy(inputs.target).to(device=device, dtype=dtype)
            loss_mask_t = torch.from_numpy(inputs.loss_mask).to(device=device, dtype=torch.bool)
            sigma_readout_t = torch.from_numpy(inputs.sigma_readout).to(device=device, dtype=dtype)
        else:
            target_t = inputs.target.to(device=device, dtype=dtype)
            loss_mask_t = inputs.loss_mask.to(device=device, dtype=torch.bool)
            sigma_readout_t = inputs.sigma_readout.to(device=device, dtype=dtype)

        # Derive n_panels from detector
        n_panels = len(detector)

        # Extract parameters from param_values dict
        stage_b_mode = param_values['stage_b_mode']
        stage_b_optimizer = param_values['optimizer']

        # Extract mode-specific parameters
        if stage_b_mode == "per_reflection":
            asu_indices = param_values['asu_indices']
            log_modifiers = param_values['log_modifiers']
            n_asu_unique = param_values['n_asu_unique']
        else:  # shell mode
            shell_modifier_raw = param_values['shell_modifier_raw']
            shell_indices = param_values['shell_indices']
        log_scale = param_values['log_scale']
        cell_a_tensor = param_values['cell_a_tensor']
        cell_b_tensor = param_values['cell_b_tensor']
        cell_c_tensor = param_values['cell_c_tensor']
        cell_alpha_tensor = param_values['cell_alpha_tensor']
        cell_beta_tensor = param_values['cell_beta_tensor']
        cell_gamma_tensor = param_values['cell_gamma_tensor']
        misset_xyz_deg = param_values['misset_xyz_deg']
        stage_b_params = param_values['params']

        # ARCH-STAGE-CONTEXT-001 Phase B.3.2: Extract telemetry accumulators from dataclass
        # Support both dataclass (new) and dict (legacy) via isinstance check for compatibility
        telemetry = param_values['telemetry_state']
        if isinstance(telemetry, dict):
            # Legacy dict path (backward compatibility during migration)
            loss_trace_sample_b = telemetry['loss_trace_sample_b']
            loss_trace_full_b = telemetry['loss_trace_full_b']
            chi_squared_trace_sample_b = telemetry['chi_squared_trace_sample_b']
            chi_squared_trace_full_b = telemetry['chi_squared_trace_full_b']
            masked_mse_trace_sample_b = telemetry['masked_mse_trace_sample_b']
            masked_mse_trace_full_b = telemetry['masked_mse_trace_full_b']
            chi_squared_best_b = telemetry['chi_squared_best_b']
            masked_mse_best_b = telemetry['masked_mse_best_b']
            best_loss_full_b = telemetry['best_loss_full_b']
            best_params_snapshot_b = telemetry['best_params_snapshot_b']
            variance_floor_clamped_pixels_b = telemetry['variance_floor_clamped_pixels_b']
            variance_floor_masked_pixels_b = telemetry['variance_floor_masked_pixels_b']
            perf_closure_evals_b = telemetry['perf_closure_evals_b']
            perf_validation_runs_b = telemetry['perf_validation_runs_b']
            perf_forward_times_ms_b = telemetry['perf_forward_times_ms_b']
        else:
            # New dataclass path (StageBTelemetryState)
            loss_trace_sample_b = telemetry.loss_trace_sample
            loss_trace_full_b = telemetry.loss_trace_full
            chi_squared_trace_sample_b = telemetry.chi_squared_trace_sample
            chi_squared_trace_full_b = telemetry.chi_squared_trace_full
            masked_mse_trace_sample_b = telemetry.masked_mse_trace_sample
            masked_mse_trace_full_b = telemetry.masked_mse_trace_full
            chi_squared_best_b = telemetry.chi_squared_best
            masked_mse_best_b = telemetry.masked_mse_best
            best_loss_full_b = telemetry.best_loss_full
            best_params_snapshot_b = telemetry.best_params_snapshot
            variance_floor_clamped_pixels_b = telemetry.variance_floor_clamped_pixels
            variance_floor_masked_pixels_b = telemetry.variance_floor_masked_pixels
            perf_closure_evals_b = telemetry.perf_closure_evals
            perf_validation_runs_b = telemetry.perf_validation_runs
            perf_forward_times_ms_b = telemetry.perf_forward_times_ms

        def compute_loss_stage_b(work_item_ids: List[int], is_full: bool = False, force_panel_eval: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            Compute variance-weighted chi-squared loss with Stage B shell-modified structure factors.

            Uses Stage A's final crystal parameters (frozen) and varies per-shell Fhkl multipliers.

            Args:
                work_item_ids: List of ROI or panel indices to evaluate
                is_full: Whether this is a full validation run (counts toward perf telemetry)
                force_panel_eval: If True, always use panel-mode evaluation regardless of ROI config
                              (reuses warmed simulators when available). Used for initial/periodic/final
                              validations to ensure shell modifiers stay within ±1% gate (PERF-WARM-009).

            Returns:
                Tuple of (chi_squared_loss, masked_mse_loss): Both scalar tensors for telemetry
            """
            t0 = time.perf_counter()
            if is_full:
                perf_validation_runs_b[0] += 1

            # PERF-WARM-011: Route to CPU when fallback is active (panel mode + CUDA + config flag)
            eval_device = torch.device("cpu") if use_stage_b_cpu_fallback else device

            chi_squared_accum = torch.tensor(0.0, device=eval_device, dtype=dtype)
            mse_numerator_accum = torch.tensor(0.0, device=eval_device, dtype=dtype)
            n_pixels_accum = 0
            sigma_floor_sq_eval = _get_sigma_floor_sq_tensor(
                sigma_floor_sq_cache, eval_device, dtype, config.sigma_floor_value
            )

            cell_a_eval = cell_a_tensor if eval_device == device else cell_a_tensor.to(device=eval_device)
            cell_b_eval = cell_b_tensor if eval_device == device else cell_b_tensor.to(device=eval_device)
            cell_c_eval = cell_c_tensor if eval_device == device else cell_c_tensor.to(device=eval_device)
            cell_alpha_eval = cell_alpha_tensor if eval_device == device else cell_alpha_tensor.to(device=eval_device)
            cell_beta_eval = cell_beta_tensor if eval_device == device else cell_beta_tensor.to(device=eval_device)
            cell_gamma_eval = cell_gamma_tensor if eval_device == device else cell_gamma_tensor.to(device=eval_device)
            misset_eval = misset_xyz_deg if eval_device == device else misset_xyz_deg.to(device=eval_device)
            baseline_misset_eval = None
            if baseline_misset_deg_tensor is not None:
                baseline_misset_eval = (
                    baseline_misset_deg_tensor
                    if eval_device == device
                    else baseline_misset_deg_tensor.to(device=eval_device)
                )
            log_scale_eval = log_scale if eval_device == device else log_scale.to(device=eval_device)

            crystal_overrides_eval = {
                'cell_a': cell_a_eval,
                'cell_b': cell_b_eval,
                'cell_c': cell_c_eval,
                'cell_alpha': cell_alpha_eval,
                'cell_beta': cell_beta_eval,
                'cell_gamma': cell_gamma_eval,
            }

            # ARCH-REFINE-FLOW-001 Phase C2.4: When CPU fallback active, use CPU-native HKL grid from
            # stage_b_eval_stage_a_ctx (built at line 2234-2246) instead of transferring CUDA hkl_grid.
            # Minimal reproducer (loop i=220) proved CPU simulator works with native CPU HKL grid;
            # CUDA→CPU transfer in closure causes device mismatch or data corruption (0% Bragg output).
            if use_stage_b_cpu_fallback and stage_b_eval_stage_a_ctx is not None:
                # CPU fallback: use CPU-native HKL grid from cloned Stage A context (PERF-WARM-012)
                hkl_grid_local = stage_b_eval_stage_a_ctx.hkl_grid
            else:
                # Normal path: transfer to eval device if needed
                hkl_grid_local = hkl_grid if eval_device == device else hkl_grid.to(device=eval_device, dtype=dtype)

            # Phase 7.3: Mode-aware modifier application
            if stage_b_mode == "per_reflection":
                # ASU mode: apply per-reflection modifiers using Phase 6 helper
                asu_indices_local = asu_indices if eval_device == device else asu_indices.to(device=eval_device)
                log_modifiers_local = log_modifiers if eval_device == device else log_modifiers.to(device=eval_device)
                hkl_grid_modified = apply_asu_modifiers(
                    hkl_grid_base=hkl_grid_local,
                    log_modifiers=log_modifiers_local,
                    hkl_asu_map=asu_indices_local,
                    modifier_clamp=config.stage_b_modifier_clamp  # (-3.0, 3.0) default
                )
            else:  # "shell" mode
                # Existing shell modifier path
                shell_modifiers = torch.nn.functional.softplus(shell_modifier_raw) * 2.0
                shell_modifiers = torch.clamp(shell_modifiers, max=config.stage_b_max_modifier)
                shell_indices_local = shell_indices if eval_device == device else shell_indices.to(device=eval_device)
                # Initialize hkl_grid_modified as clone of local grid
                hkl_grid_modified = hkl_grid_local.clone()
                for shell_idx in range(config.stage_b_n_shells):
                    mask = (shell_indices_local == shell_idx)
                    modifier_value = shell_modifiers[shell_idx]
                    if modifier_value.device != eval_device:
                        modifier_value = modifier_value.to(device=eval_device)
                    # Out-of-place: creates NEW tensor with gradient graph
                    hkl_grid_modified = torch.where(
                        mask,  # Boolean mask [panels, slow, fast]
                        hkl_grid_local * modifier_value,  # Gradient-enabled operation
                        hkl_grid_modified  # Keep existing values for non-matching shells
                    )

            # PERF-WARM-012: Use the eval-device-specific Stage A context (CPU or CUDA)
            use_warm_eval = stage_b_use_warm_cache
            if use_warm_eval:
                misset_override = misset_eval
                if baseline_misset_eval is not None:
                    misset_override = baseline_misset_eval + misset_eval
                warm_crystal_config, _ = create_crystal_config(
                    crystal,
                    None,
                    crystal_overrides=crystal_overrides_eval,
                    misset_deg_override=misset_override,
                    apply_n_cells=False,
                )
                warm_crystal_model = Crystal(
                    warm_crystal_config,
                    beam_config=stage_b_eval_stage_a_ctx.beam_config,
                    device=eval_device,
                    dtype=dtype,
                )
                warm_crystal_model.interpolate = True
                warm_crystal_model.hkl_data = hkl_grid_modified
                warm_crystal_model.hkl_metadata = hkl_metadata
                _retarget_stage_a_simulators(stage_b_eval_stage_a_ctx, warm_crystal_model)

            # PERF-WARM-SIM-001: Branch on ROI vs panel mode
            # PERF-WARM-009: force_panel_eval overrides ROI mode for validations
            use_roi_for_this_eval = use_stage_b_roi_mode and not force_panel_eval
            if use_roi_for_this_eval:
                # ROI mode: iterate over Stage A's cached ROI entries
                indices = work_item_ids if work_item_ids else full_stage_b_indices
                for roi_index in indices:
                    roi_entry = stage_b_eval_stage_a_ctx.roi_entries[roi_index]
                    pid, bbox = roi_entry.panel_id, roi_entry.bbox
                    x0, x1, y0, y1 = map(int, bbox)
                    slow_slice = slice(y0, y1)
                    fast_slice = slice(x0, x1)

                    target_subset = target_t[pid, slow_slice, fast_slice].to(device=eval_device, dtype=dtype)
                    mask_subset = loss_mask_t[pid, slow_slice, fast_slice].to(device=eval_device)
                    if stage_b_eval_stage_a_ctx.trusted_masks_t is not None:
                        trusted_slice = stage_b_eval_stage_a_ctx.trusted_masks_t[pid, slow_slice, fast_slice].to(device=eval_device)
                        mask_subset = torch.logical_and(mask_subset, trusted_slice)
                    sigma_subset = sigma_readout_t[pid, slow_slice, fast_slice].to(device=eval_device, dtype=dtype)

                    simulator = roi_entry.simulator
                    bragg_patch = simulator.run()
                    log_scale_clamped = torch.clamp(log_scale_eval, min=-10.0, max=10.0)
                    bragg_scaled = bragg_patch * torch.exp(log_scale_clamped)

                    (
                        chi_sq_roi,
                        masked_mse_roi,
                        masked_pixels_roi,
                        clamped_pixels_roi,
                    ) = _compute_variance_weighted_loss(
                        bragg_scaled,
                        target_subset,
                        mask_subset,
                        sigma_subset,
                        sigma_floor_sq_eval,
                    )
                    chi_squared_accum = chi_squared_accum + chi_sq_roi
                    mse_numerator_accum = mse_numerator_accum + masked_mse_roi * masked_pixels_roi
                    n_pixels_accum += masked_pixels_roi
                    variance_floor_clamped_pixels_b[0] += clamped_pixels_roi
                    variance_floor_masked_pixels_b[0] += masked_pixels_roi
            else:
                # Panel mode: iterate over panels
                panel_ids = work_item_ids if work_item_ids else full_stage_b_indices
                for pid in panel_ids:
                    if use_warm_eval:
                        simulator = stage_b_eval_stage_a_ctx.simulators[pid]
                        bragg_panel = simulator.run()
                    else:
                        detector_config = create_detector_config(
                            panel=detector[pid],
                            beam=beam,
                            trusted_mask=inputs.trusted_mask[pid]
                        )
                        mask_array = detector_config.mask_array
                        if mask_array is not None and not isinstance(mask_array, torch.Tensor):
                            mask_array = torch.tensor(mask_array, dtype=torch.float32, device=eval_device)
                            detector_config.mask_array = mask_array
                        elif mask_array is not None and mask_array.device != eval_device:
                            detector_config.mask_array = mask_array.to(device=eval_device, dtype=torch.float32)
                        misset_override = misset_eval
                        if baseline_misset_eval is not None:
                            misset_override = baseline_misset_eval + misset_eval
                        crystal_config, _ = create_crystal_config(
                            crystal,
                            None,
                            crystal_overrides=crystal_overrides_eval,
                            misset_deg_override=misset_override,
                            apply_n_cells=False
                        )
                        detector_model = Detector(detector_config, device=eval_device, dtype=dtype)
                        crystal_model = Crystal(crystal_config, device=eval_device, dtype=dtype)
                        crystal_model.interpolate = True
                        crystal_model.hkl_data = hkl_grid_modified
                        crystal_model.hkl_metadata = hkl_metadata
                        simulator = Simulator(detector=detector_model, crystal=crystal_model, device=eval_device, dtype=dtype)
                        bragg_panel = simulator.run()

                    target_panel = target_t[pid].to(device=eval_device, dtype=dtype)
                    loss_mask_panel = loss_mask_t[pid].to(device=eval_device)
                    sigma_panel = sigma_readout_t[pid].to(device=eval_device, dtype=dtype)
                    log_scale_clamped = torch.clamp(log_scale_eval, min=-10.0, max=10.0)
                    bragg_scaled = bragg_panel * torch.exp(log_scale_clamped)

                    (
                        chi_sq_panel,
                        masked_mse_panel,
                        masked_pixels_panel,
                        clamped_pixels_panel,
                    ) = _compute_variance_weighted_loss(
                        bragg_scaled,
                        target_panel,
                        loss_mask_panel,
                        sigma_panel,
                        sigma_floor_sq_eval,
                    )
                    chi_squared_accum = chi_squared_accum + chi_sq_panel
                    mse_numerator_accum = mse_numerator_accum + masked_mse_panel * masked_pixels_panel
                    n_pixels_accum += masked_pixels_panel
                    variance_floor_clamped_pixels_b[0] += clamped_pixels_panel
                    variance_floor_masked_pixels_b[0] += masked_pixels_panel

            chi_squared_loss = chi_squared_accum
            if n_pixels_accum > 0:
                masked_mse_loss = mse_numerator_accum / n_pixels_accum
            else:
                masked_mse_loss = mse_numerator_accum

            perf_forward_times_ms_b.append((time.perf_counter() - t0) * 1000.0)

            return chi_squared_loss, masked_mse_loss

        def closure_stage_b():
            """LBFGS closure for Stage B shell modifier refinement."""
            nonlocal chi_squared_best_b, masked_mse_best_b, best_loss_full_b, best_params_snapshot_b
            stage_b_optimizer.zero_grad()

            # Sample ROIs or panels for efficiency (PERF-WARM-SIM-001)
            chi_squared_loss, mse_loss = compute_loss_stage_b(sampled_stage_b_indices, is_full=False)

            chi_squared_loss.backward()

            # Gradient NaN/Inf guard
            for p in stage_b_params:
                if p.grad is not None and (torch.isnan(p.grad).any() or torch.isinf(p.grad).any()):
                    raise RuntimeError(f"NaN/Inf gradient detected in Stage B parameter {p}")

            # ARCH-TELEMETRY-001 Phase C.1: Record telemetry via collector or fall back to direct mutations
            if collector is not None:
                # Observer path: route telemetry through collector.on_step
                metrics = {
                    'chi_squared': float(chi_squared_loss.item()),
                    'masked_mse': float(mse_loss.item()),
                    # variance_floor stats updated incrementally in compute_loss_stage_b
                }
                collector.on_step(
                    iteration=len(loss_trace_sample_b),
                    loss=float(chi_squared_loss.item()),
                    metrics=metrics,
                )
            else:
                # Legacy path: direct list mutation for backward compatibility
                perf_closure_evals_b[0] += 1
                loss_trace_sample_b.append(float(chi_squared_loss.item()))
                # PHYSICS-LOSS-001: Record both metrics
                chi_squared_trace_sample_b.append(float(chi_squared_loss.item()))
                masked_mse_trace_sample_b.append(float(mse_loss.item()))

            # Periodic full validation
            # PERF-WARM-009: Force panel evaluation for periodic validations to keep modifiers within ±1%
            if len(loss_trace_sample_b) % config.full_validation_interval == 0:
                with torch.no_grad():
                    full_chi_squared_b, full_mse_b = compute_loss_stage_b(
                        list(range(n_panels)), is_full=True, force_panel_eval=True
                    )

                    # ARCH-TELEMETRY-001 Phase C.1: Route validation telemetry via collector or legacy path
                    if collector is not None:
                        # Observer path: build best snapshot for collector
                        snapshot_data = {}
                        if stage_b_mode == "per_reflection":
                            snapshot_data['log_modifiers'] = log_modifiers.data.clone()
                        else:
                            snapshot_data['shell_modifier_raw'] = shell_modifier_raw.data.clone()

                        payload = {
                            'loss': float(full_chi_squared_b.item()),
                            'masked_mse': float(full_mse_b.item()),
                            'best_snapshot': snapshot_data,
                        }
                        collector.on_validation(
                            scope='panel',
                            chi2=float(full_chi_squared_b.item()),
                            payload=payload,
                        )
                    else:
                        # Legacy path: direct mutations
                        loss_trace_full_b.append((len(loss_trace_sample_b), float(full_chi_squared_b.item())))
                        # PHYSICS-LOSS-001: Record both metrics
                        chi_squared_trace_full_b.append((len(loss_trace_sample_b), float(full_chi_squared_b.item())))
                        masked_mse_trace_full_b.append((len(loss_trace_sample_b), float(full_mse_b.item())))

                        # Update best snapshot
                        # PHYSICS-LOSS-001: Track best for both metrics
                        if full_chi_squared_b.item() < chi_squared_best_b[0]:
                            chi_squared_best_b = (float(full_chi_squared_b.item()), len(loss_trace_sample_b))
                            best_loss_full_b = (float(full_chi_squared_b.item()), len(loss_trace_sample_b))  # Deprecated legacy field
                            # Phase 7: Mode-aware best params snapshot
                            # ARCH-STAGE-CONTEXT-001 Phase B.3.2: Handle both list and dict snapshot types
                            snapshot_data = {}
                            if stage_b_mode == "per_reflection":
                                snapshot_data['log_modifiers'] = log_modifiers.data.clone()
                            else:
                                snapshot_data['shell_modifier_raw'] = shell_modifier_raw.data.clone()
                            if isinstance(best_params_snapshot_b, list):
                                best_params_snapshot_b.clear()
                                best_params_snapshot_b.append(snapshot_data)
                            else:
                                best_params_snapshot_b.update(snapshot_data)
                        if full_mse_b.item() < masked_mse_best_b[0]:
                            masked_mse_best_b = (float(full_mse_b.item()), len(loss_trace_sample_b))

            return chi_squared_loss

        return compute_loss_stage_b, closure_stage_b

    def run(
        self,
        inputs: Any,
        telemetry_sink: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Execute Stage B LBFGS refinement calling extracted helpers directly.

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
                - 'stage_a_telemetry': Dict containing Stage A final telemetry (param_deltas, etc.)
                - 'stage_a_ctx': Optional Stage A context (detectors/simulators for warm cache)
            telemetry_sink: Optional path for telemetry output (unused by this implementation,
                           telemetry returned via dict instead)

        Returns:
            Telemetry dict with all required RefinementTelemetry fields plus:
            - stage_type: "B"
            - mode: "shell_modifiers"

        Raises:
            RuntimeError: If simulator fails, gradients are NaN/Inf, or halo grid missing
            ValueError: If config not set via configure()
        """
        if self._config is None:
            raise ValueError("StageB not configured. Call configure(config) before run().")

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

        # Stage-specific inputs (telemetry, warm cache) remain in inputs dict
        stage_a_telemetry = inputs['stage_a_telemetry']
        stage_a_ctx = inputs.get('stage_a_ctx', None)

        # Extract device/dtype from config
        # NOTE: Keep device as CUDA here so that _build_stage_b_params can detect
        # the need for CPU fallback via config.stage_b_full_eval_on_cpu
        device = torch.device(self._config.device)
        dtype = self._config.dtype

        # Guard: Stage B requires halo-padded HKL grid and interpolation enabled (REFINE-005)
        if not hkl_metadata.get("has_halo", False):
            raise RuntimeError(
                "Stage B requires halo-padded HKL grid (hkl_metadata['has_halo']=True). "
                "Rebuild structure factor grid with build_structure_factor_grid(..., halo=True) "
                "and set config.enable_hkl_interpolation=True before enabling Stage B."
            )

        if not self._config.enable_hkl_interpolation:
            raise RuntimeError(
                "Stage B requires tricubic HKL interpolation (config.enable_hkl_interpolation=True). "
                "Set this flag before enabling Stage B to prevent default_F fallback and gradient loss."
            )

        # Extract panel counts and sampling
        n_panels = len(detector)
        panel_shape = (
            detector[0].get_image_size()[1],  # slow axis (rows)
            detector[0].get_image_size()[0]   # fast axis (cols)
        )
        sampled_panel_ids = list(range(n_panels))  # Default: all panels

        # Extract Stage A final parameters from telemetry (frozen for Stage B)
        # CRITICAL: Use 'final' key from param_deltas (NOT raw tensors)
        log_scale_final = stage_a_telemetry['param_deltas']['log_scale']['final']
        log_cell_a_delta_final = stage_a_telemetry['param_deltas']['log_cell_a_delta']['final']
        log_cell_b_delta_final = stage_a_telemetry['param_deltas']['log_cell_b_delta']['final']
        log_cell_c_delta_final = stage_a_telemetry['param_deltas']['log_cell_c_delta']['final']
        angle_alpha_raw_final = stage_a_telemetry['param_deltas']['angle_alpha_raw']['final']
        angle_beta_raw_final = stage_a_telemetry['param_deltas']['angle_beta_raw']['final']
        angle_gamma_raw_final = stage_a_telemetry['param_deltas']['angle_gamma_raw']['final']
        misset_xyz_deg_delta_final = stage_a_telemetry['param_deltas']['misset_xyz_deg']['delta']

        # Rebuild Stage A final tensors from scalars
        log_scale = torch.tensor(log_scale_final, device=device, dtype=dtype)
        log_cell_a_delta = torch.tensor(log_cell_a_delta_final, device=device, dtype=dtype)
        log_cell_b_delta = torch.tensor(log_cell_b_delta_final, device=device, dtype=dtype)
        log_cell_c_delta = torch.tensor(log_cell_c_delta_final, device=device, dtype=dtype)
        angle_alpha_raw = torch.tensor(angle_alpha_raw_final, device=device, dtype=dtype)
        angle_beta_raw = torch.tensor(angle_beta_raw_final, device=device, dtype=dtype)
        angle_gamma_raw = torch.tensor(angle_gamma_raw_final, device=device, dtype=dtype)

        # Compute Stage A final crystal parameters as tensors (for Stage B)
        # Use baseline crystal params as the base for delta reconstruction
        # (log_cell_*_delta are relative to BASELINE, not current crystal)
        if baseline_crystal is None:
            raise ValueError(
                "Stage B requires baseline_crystal to reconstruct cell parameters. "
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

        # Compute Stage A final misset (for Stage B)
        misset_xyz_deg = torch.tensor(misset_xyz_deg_delta_final, device=device, dtype=dtype)

        # Compute baseline_misset_deg_tensor if baseline_crystal provided
        baseline_misset_deg_tensor = None
        if baseline_crystal is not None:
            baseline_misset_deg_tensor = compute_baseline_misset_deg(
                crystal, baseline_crystal, device=device, dtype=dtype
            )

        # Build sigma_floor_sq_cache (shared across Stage A/B)
        sigma_floor_sq_cache = {}

        # ARCH-STAGE-CONTEXT-001 Phase A.2: Build RefinementSharedContext
        # to collapse the 11-parameter data clump passed to _build_stage_b_lbfgs_closure
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
        canonical_baseline = {
            'stage_label': stage_a_telemetry['canonical_stage_label'],
            'chi_squared': stage_a_telemetry['canonical_chi_squared'],
            'iteration': stage_a_telemetry['canonical_chi_squared_iteration'],
            'roi_count': stage_a_telemetry['canonical_roi_count'],
            'detector_distances_mm': stage_a_telemetry['canonical_detector_distances_mm'],
        }

        # Determine if Stage A used ROI mode (from telemetry)
        use_stage_a_roi_mode = (stage_a_telemetry['roi_mode'] == "roi")

        # Extract Stage A final loss for improvement calculation
        # best_loss_full is already a list [loss_value, iteration] from Stage A
        best_loss_full = stage_a_telemetry['best_loss_full']

        # STEP 1: Build Stage B parameters
        # Pass context to enable ASU map reuse (ARCH-REFINE-001 Phase B.3)
        param_values = _build_stage_b_params(
            config=self._config,
            device=device,
            dtype=dtype,
            stage_a_ctx=stage_a_ctx,
            canonical_baseline=canonical_baseline,
            n_panels=n_panels,
            sampled_panel_ids=sampled_panel_ids,
            sigma_floor_sq_cache=sigma_floor_sq_cache,
            use_stage_a_roi_mode=use_stage_a_roi_mode,
            crystal=crystal,
            hkl_metadata=hkl_metadata,
            hkl_grid=hkl_grid,
            detector=detector,
            beam=beam,
            inputs=refinement_inputs,
            panel_slices=refinement_inputs.panel_slices,
            context=ctx,  # ARCH-REFINE-001 Phase B.3: Thread context for asu_map reuse
        )

        # Add frozen Stage A tensors to param_values (required by helper2)
        param_values['log_scale'] = log_scale
        param_values['cell_a_tensor'] = cell_a_tensor
        param_values['cell_b_tensor'] = cell_b_tensor
        param_values['cell_c_tensor'] = cell_c_tensor
        param_values['cell_alpha_tensor'] = cell_alpha_tensor
        param_values['cell_beta_tensor'] = cell_beta_tensor
        param_values['cell_gamma_tensor'] = cell_gamma_tensor
        param_values['misset_xyz_deg'] = misset_xyz_deg
        param_values['best_loss_full'] = best_loss_full  # Stage A final loss for improvement calc

        # Extract mode-specific parameters (per-reflection vs shell)
        stage_b_mode = param_values['stage_b_mode']

        if stage_b_mode == "per_reflection":
            # Per-reflection mode: extract ASU parameters
            asu_indices = param_values['asu_indices']
            log_modifiers = param_values['log_modifiers']
            n_asu_unique = param_values['n_asu_unique']
            shell_indices = None  # Not used in per-reflection mode
            shell_edges = None
            shell_modifier_raw = None
        else:  # shell mode
            # Shell mode: extract shell parameters
            shell_indices = param_values['shell_indices']
            shell_edges = param_values['shell_edges']
            shell_modifier_raw = param_values['shell_modifier_raw']
            asu_indices = None  # Not used in shell mode
            n_asu_unique = 0
            log_modifiers = None

        stage_b_params = param_values['params']
        stage_b_optimizer = param_values['optimizer']
        stage_b_eval_stage_a_ctx = param_values['stage_b_eval_stage_a_ctx']
        use_stage_b_cpu_fallback = param_values['use_stage_b_cpu_fallback']
        stage_b_use_warm_cache = param_values['stage_b_use_warm_cache']
        stage_b_cache_mode = param_values['stage_b_cache_mode']
        use_stage_b_roi_mode = param_values['use_stage_b_roi_mode']
        stage_b_roi_label = param_values['stage_b_roi_label']
        sampled_stage_b_indices = param_values['sampled_stage_b_indices']
        full_stage_b_indices = param_values['full_stage_b_indices']
        stage_b_param_device = param_values['stage_b_param_device']

        # ARCH-TELEMETRY-001 Phase C.1: Create observer collector from telemetry state
        telemetry_state = param_values['telemetry_state']
        # For now, always use the collector path per ARCH-TELEMETRY-001 Phase C.1
        collector = StageBTelemetryCollector(telemetry_state)

        # STEP 2: Build Stage B LBFGS closure (returns tuple)
        # ARCH-STAGE-CONTEXT-001 Phase B.2: Call class method instead of helper
        compute_loss_stage_b, closure_stage_b = self._build_lbfgs_closure(
            shared_context=shared_context,
            param_values=param_values,
            stage_a_ctx=stage_a_ctx,
            stage_b_eval_stage_a_ctx=stage_b_eval_stage_a_ctx,
            canonical_baseline=canonical_baseline,
            sampled_stage_b_indices=sampled_stage_b_indices,
            full_stage_b_indices=full_stage_b_indices,
            use_stage_b_cpu_fallback=use_stage_b_cpu_fallback,
            stage_b_use_warm_cache=stage_b_use_warm_cache,
            use_stage_b_roi_mode=use_stage_b_roi_mode,
            shell_indices=shell_indices,
            baseline_misset_deg_tensor=baseline_misset_deg_tensor,
            collector=collector,
        )

        # STEP 3: Run Stage B LBFGS optimization
        stage_b_results = _run_stage_b_lbfgs(
            config=self._config,
            device=device,
            dtype=dtype,
            param_values=param_values,
            closure_stage_b=closure_stage_b,
            compute_loss_stage_b=compute_loss_stage_b,
            n_panels=n_panels,
            collector=collector,
        )

        # Unpack results from helper3
        status_b = stage_b_results['status']
        message_b = stage_b_results['message']
        best_loss_full_b = stage_b_results['best_loss_full_b']
        chi_squared_best_b = stage_b_results['chi_squared_best_b']
        masked_mse_best_b = stage_b_results['masked_mse_best_b']
        final_loss_value = stage_b_results['final_loss_value']
        final_mse_value = stage_b_results['final_mse_value']

        # ARCH-STAGE-CONTEXT-001 Phase B.3.2: Extract telemetry from dataclass (with dict compat)
        # Accumulators updated in-place by closures
        telemetry = param_values['telemetry_state']
        if isinstance(telemetry, dict):
            loss_trace_sample_b = telemetry['loss_trace_sample_b']
            loss_trace_full_b = telemetry['loss_trace_full_b']
            chi_squared_trace_sample_b = telemetry['chi_squared_trace_sample_b']
            chi_squared_trace_full_b = telemetry['chi_squared_trace_full_b']
            masked_mse_trace_sample_b = telemetry['masked_mse_trace_sample_b']
            masked_mse_trace_full_b = telemetry['masked_mse_trace_full_b']
            perf_closure_evals_b = telemetry['perf_closure_evals_b']
            perf_validation_runs_b = telemetry['perf_validation_runs_b']
            perf_forward_times_ms_b = telemetry['perf_forward_times_ms_b']
            variance_floor_clamped_pixels_b = telemetry['variance_floor_clamped_pixels_b']
            variance_floor_masked_pixels_b = telemetry['variance_floor_masked_pixels_b']
        else:
            loss_trace_sample_b = telemetry.loss_trace_sample
            loss_trace_full_b = telemetry.loss_trace_full
            chi_squared_trace_sample_b = telemetry.chi_squared_trace_sample
            chi_squared_trace_full_b = telemetry.chi_squared_trace_full
            masked_mse_trace_sample_b = telemetry.masked_mse_trace_sample
            masked_mse_trace_full_b = telemetry.masked_mse_trace_full
            perf_closure_evals_b = telemetry.perf_closure_evals
            perf_validation_runs_b = telemetry.perf_validation_runs
            perf_forward_times_ms_b = telemetry.perf_forward_times_ms
            variance_floor_clamped_pixels_b = telemetry.variance_floor_clamped_pixels
            variance_floor_masked_pixels_b = telemetry.variance_floor_masked_pixels

        # REFINE-FLOW-001: Extract baseline parity diagnostics
        # Support both dict and dataclass (getattr with default for dataclass)
        if isinstance(telemetry, dict):
            stage_b_baseline_rel_diff = telemetry.get('stage_b_baseline_rel_diff', None)
            stage_b_baseline_abs_diff = telemetry.get('stage_b_baseline_abs_diff', None)
            stage_b_baseline_diff_path = telemetry.get('stage_b_baseline_diff_path', None)
        else:
            stage_b_baseline_rel_diff = getattr(telemetry, 'stage_b_baseline_rel_diff', None)
            stage_b_baseline_abs_diff = getattr(telemetry, 'stage_b_baseline_abs_diff', None)
            stage_b_baseline_diff_path = getattr(telemetry, 'stage_b_baseline_diff_path', None)

        # Build param_deltas dict for telemetry (mode-aware)
        param_deltas_b = {}

        if stage_b_mode == "per_reflection":
            # Per-reflection mode: compute ASU modifier stats
            with torch.no_grad():
                modifiers_exp = torch.exp(log_modifiers)
                modifiers_clamped = torch.clamp(
                    modifiers_exp,
                    min=1.0 / self._config.stage_b_max_modifier,
                    max=self._config.stage_b_max_modifier
                )
                modifiers_np = modifiers_clamped.cpu().numpy()

            # Store summary statistics instead of per-ASU values (too many for param_deltas)
            param_deltas_b["asu_modifiers_summary"] = {
                'initial': 1.0,  # Identity at initialization
                'final_min': float(modifiers_np.min()),
                'final_max': float(modifiers_np.max()),
                'final_mean': float(modifiers_np.mean()),
                'final_std': float(modifiers_np.std()),
            }
        else:  # shell mode
            with torch.no_grad():
                shell_modifiers_final = torch.nn.functional.softplus(shell_modifier_raw) * 2.0
                shell_modifiers_final = torch.clamp(shell_modifiers_final, max=self._config.stage_b_max_modifier)
                shell_modifiers_final_np = shell_modifiers_final.cpu().numpy()

            for shell_idx in range(self._config.stage_b_n_shells):
                d_min_shell = float(shell_edges[shell_idx + 1].item()) if shell_idx + 1 < len(shell_edges) else 0.0
                d_max_shell = float(shell_edges[shell_idx].item())
                # Store initial/final/delta structure (mirroring Stage A pattern)
                param_deltas_b[f"shell_{shell_idx}_modifier (d={d_min_shell:.2f}-{d_max_shell:.2f}Å)"] = {
                    'initial': 1.0,  # Identity at initialization
                    'final': float(shell_modifiers_final_np[shell_idx]),
                    'delta': float(shell_modifiers_final_np[shell_idx]) - 1.0,
                }

        # Build perf counters payload (PERF-WARM-SIM-001)
        stage_b_roi_count_total = canonical_baseline["roi_count"]
        stage_b_roi_count_sampled = canonical_baseline["roi_count"] if not use_stage_b_roi_mode else len(sampled_stage_b_indices)

        forward_stats_b = {
            'mean': float(np.mean(perf_forward_times_ms_b)) if perf_forward_times_ms_b else 0.0,
            'min': float(np.min(perf_forward_times_ms_b)) if perf_forward_times_ms_b else 0.0,
            'max': float(np.max(perf_forward_times_ms_b)) if perf_forward_times_ms_b else 0.0,
            'total': float(np.sum(perf_forward_times_ms_b)) if perf_forward_times_ms_b else 0.0,
        }
        perf_counters_b = {
            'cache_mode': stage_b_cache_mode,
            'roi_mode': stage_b_roi_label,
            'roi_count_total': stage_b_roi_count_total,
            'roi_count_sampled': stage_b_roi_count_sampled,
            'closure_evals': perf_closure_evals_b[0],
            'validation_runs': perf_validation_runs_b[0],
            'forward_time_ms': forward_stats_b,
        }

        # Assemble RefinementTelemetry object (matches run_nanobrag_refinement lines 3418-3456)
        # Extract optimizer type from param_values (dynamic: lbfgs or adam)
        # Keep lowercase for custom attribute, uppercase for telemetry.optimizer field
        optimizer_type = param_values.get('optimizer_type', 'lbfgs')

        telemetry_b = RefinementTelemetry(
            optimizer=optimizer_type.upper(),
            stage="B",
            history_size=self._config.history_size,
            max_iter=self._config.max_iter,
            tolerance_grad=self._config.tolerance_grad,
            tolerance_change=self._config.tolerance_change,
            roi_sample_fraction=self._config.roi_sample_fraction,
            roi_count_sampled=stage_b_roi_count_sampled,
            roi_count_total=stage_b_roi_count_total,
            loss_trace_sample=loss_trace_sample_b,
            loss_trace_full=loss_trace_full_b,
            best_loss_full=best_loss_full_b,
            param_deltas=param_deltas_b,
            status=status_b,
            message=message_b,
            perf_counters=perf_counters_b,
            # PHYSICS-LOSS-001: Dual loss metrics
            chi_squared_trace_sample=chi_squared_trace_sample_b,
            chi_squared_trace_full=chi_squared_trace_full_b,
            chi_squared_best=chi_squared_best_b,
            masked_mse_trace_sample=masked_mse_trace_sample_b,
            masked_mse_trace_full=masked_mse_trace_full_b,
            masked_mse_best=masked_mse_best_b,
            sigma_readout_provenance=self._config.sigma_readout_provenance,
            sigma_readout_reference_value=self._config.sigma_readout_reference_value,
            # PHYSICS-LOSS-002: Variance floor telemetry
            variance_floor_value=self._config.sigma_floor_value**2,
            variance_floor_clamp_fraction=(
                float(variance_floor_clamped_pixels_b[0]) / float(variance_floor_masked_pixels_b[0])
                if variance_floor_masked_pixels_b[0] > 0 else 0.0
            ),
            canonical_stage_label=canonical_baseline["stage_label"],
            canonical_chi_squared=canonical_baseline["chi_squared"],
            canonical_chi_squared_iteration=canonical_baseline["iteration"],
            canonical_roi_count=canonical_baseline["roi_count"],
            canonical_detector_distances_mm=canonical_baseline["detector_distances_mm"],
            roi_mode=stage_b_roi_label,
        )

        # Add mode-specific custom attributes to dataclass before serialization
        # (matches pattern in nanobrag_refinement.py:5226-5238)
        telemetry_b.stage_b_mode = stage_b_mode

        if stage_b_mode == "per_reflection":
            # Per-reflection mode: add ASU-specific attributes
            with torch.no_grad():
                modifiers_exp = torch.exp(log_modifiers)
                modifiers_clamped = torch.clamp(
                    modifiers_exp,
                    min=1.0 / self._config.stage_b_max_modifier,
                    max=self._config.stage_b_max_modifier
                )

            telemetry_b.n_asu_unique = int(n_asu_unique)
            telemetry_b.optimizer_type = optimizer_type  # Already lowercase from fix #1
            telemetry_b.asu_modifier_stats = {
                "min": float(modifiers_clamped.min().item()),
                "max": float(modifiers_clamped.max().item()),
                "mean": float(modifiers_clamped.mean().item()),
                "std": float(modifiers_clamped.std().item()),
            }

        # Convert to dict for engine aggregation
        telemetry_output = asdict(telemetry_b)

        # Add Phase A4 stage identification fields (backward compatible with engine contract)
        telemetry_output["stage_type"] = "B"

        # ARCH-STAGE-CONTEXT-001 Phase B.4: baseline parity diagnostics moved to artifacts
        # Writer sources these from StageBArtifacts instead of telemetry to maintain dataclass schema stability

        # ARCH-STAGE-CONTEXT-001 Phase B.1: Build artifacts based on mode
        if stage_b_mode == "per_reflection":
            telemetry_output["mode"] = "per_reflection"

            # Add per-reflection custom attributes (matches nanobrag_refinement.py:5196-5206)
            with torch.no_grad():
                modifiers_exp = torch.exp(log_modifiers)
                modifiers_clamped = torch.clamp(
                    modifiers_exp,
                    min=1.0 / self._config.stage_b_max_modifier,
                    max=self._config.stage_b_max_modifier
                )

            asu_modifier_stats = {
                "min": float(modifiers_clamped.min().item()),
                "max": float(modifiers_clamped.max().item()),
                "mean": float(modifiers_clamped.mean().item()),
                "std": float(modifiers_clamped.std().item()),
            }

            # Create StageBArtifacts for per-reflection mode (no shell metadata)
            artifacts = StageBArtifacts(
                shell_edges=None,
                shell_indices=None,
                n_shells=0,
                stage_b_baseline_rel_diff=stage_b_baseline_rel_diff,
                stage_b_baseline_abs_diff=stage_b_baseline_abs_diff,
                stage_b_baseline_diff_path=stage_b_baseline_diff_path,
                stage_b_mode="per_reflection",
                n_asu_unique=int(n_asu_unique),
                optimizer_type=optimizer_type,
                asu_modifier_stats=asu_modifier_stats
            )
        else:  # shell mode
            telemetry_output["mode"] = "shell_modifiers"

            # Create StageBArtifacts with shell metadata for final Bragg reconstruction
            artifacts = StageBArtifacts(
                shell_edges=shell_edges.cpu().numpy(),
                shell_indices=shell_indices.cpu().numpy(),
                n_shells=self._config.stage_b_n_shells,
                stage_b_baseline_rel_diff=stage_b_baseline_rel_diff,
                stage_b_baseline_abs_diff=stage_b_baseline_abs_diff,
                stage_b_baseline_diff_path=stage_b_baseline_diff_path,
                stage_b_mode="shell"
            )

        # ARCH-STAGE-CONTEXT-001 Phase D: Compute final Bragg when Stage B is terminal
        # Stage B is terminal when Stage C is disabled
        bragg_full_artifact = None
        is_terminal_stage = not self._config.enable_stage_c
        if is_terminal_stage:
            # Import reconstruction helper
            from dbex.refinement.reconstruction import build_final_bragg_from_stage_b_telemetry

            # Build reconstruction payload: merge telemetry dict with shell metadata from artifacts
            # This ensures the helper receives shell_edges, shell_indices, n_shells, and stage_b_mode
            # while keeping the payload compact (numpy arrays, no GPU tensors)
            reconstruction_payload = telemetry_output.copy()

            if stage_b_mode == "shell":
                # Shell mode: add shell metadata from artifacts
                reconstruction_payload['shell_edges'] = artifacts.shell_edges
                reconstruction_payload['shell_indices'] = artifacts.shell_indices
                reconstruction_payload['n_shells'] = artifacts.n_shells
                reconstruction_payload['stage_b_mode'] = artifacts.stage_b_mode
            else:
                # Per-reflection mode: mark mode in payload
                reconstruction_payload['stage_b_mode'] = artifacts.stage_b_mode

            # Build final Bragg from Stage B telemetry using the shared helper
            # Per input.md: use the CPU fallback flag so the helper mirrors the existing CLI path
            use_stage_b_cpu_fallback = self._config.stage_b_full_eval_on_cpu
            bragg_full_artifact = build_final_bragg_from_stage_b_telemetry(
                telemetry_a=stage_a_telemetry,
                telemetry_b=reconstruction_payload,
                detector=detector,
                beam=beam,
                crystal=crystal,
                baseline_crystal=baseline_crystal,
                inputs=refinement_inputs,
                hkl_grid=hkl_grid,
                hkl_metadata=hkl_metadata,
                config=self._config,
                device=device,
                dtype=dtype,
                use_stage_b_cpu_fallback=use_stage_b_cpu_fallback,
                stage_a_ctx=stage_a_ctx,
            )
            # Update artifacts with the final Bragg tensor (attach numpy volume back onto artifact)
            artifacts.bragg_full = bragg_full_artifact

        # Return StageResult with telemetry dict and artifacts
        return StageResult(
            telemetry=telemetry_output,
            artifacts=artifacts
        )
