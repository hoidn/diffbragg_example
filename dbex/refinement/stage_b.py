# dbex/refinement/stage_b.py
"""
Stage B implementation for Protocol-based Refinement Engine.

Wraps existing LBFGS closure logic from run_nanobrag_refinement into a RefinementStage class
per docs/spec-db-workflow.md §7 (Refinement Protocol Architecture) and
ARCH-REFINE-FLOW-001 Phase C1b.

Stage B optimizes:
- shell_modifier_raw: Per-shell structure factor multipliers (softplus parameterization)

Freezes Stage A parameters (log_scale, cell, misset) from stage_a_telemetry input.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional
import numpy as np
import torch


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

        # Import helpers (lazy to avoid circular imports at module load time)
        from dbex.refinement.stage_b_impl import (
            _build_stage_b_params,
            _build_stage_b_lbfgs_closure,
            _run_stage_b_lbfgs,
        )
        from dbex.nanobrag_refinement import RefinementTelemetry
        from dbex.nanobrag_bridge import (
            create_detector_config,
            create_crystal_config,
            compute_baseline_misset_deg,
        )
        from nanobrag_torch.models import Detector, Crystal
        from nanobrag_torch.simulator import Simulator

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

        # Extract tensors from refinement_inputs for helper2
        # Convert numpy arrays to torch tensors if needed
        if isinstance(refinement_inputs.target, np.ndarray):
            target_t = torch.from_numpy(refinement_inputs.target).to(device=device, dtype=dtype)
            loss_mask_t = torch.from_numpy(refinement_inputs.loss_mask).to(device=device, dtype=torch.bool)
            sigma_readout_t = torch.from_numpy(refinement_inputs.sigma_readout).to(device=device, dtype=dtype)
        else:
            target_t = refinement_inputs.target.to(device=device, dtype=dtype)
            loss_mask_t = refinement_inputs.loss_mask.to(device=device, dtype=torch.bool)
            sigma_readout_t = refinement_inputs.sigma_readout.to(device=device, dtype=dtype)

        # STEP 2: Build Stage B LBFGS closure (returns tuple)
        compute_loss_stage_b, closure_stage_b = _build_stage_b_lbfgs_closure(
            config=self._config,
            device=device,
            dtype=dtype,
            param_values=param_values,
            stage_a_ctx=stage_a_ctx,
            stage_b_eval_stage_a_ctx=stage_b_eval_stage_a_ctx,
            canonical_baseline=canonical_baseline,
            n_panels=n_panels,
            sampled_stage_b_indices=sampled_stage_b_indices,
            full_stage_b_indices=full_stage_b_indices,
            sigma_floor_sq_cache=sigma_floor_sq_cache,
            use_stage_b_cpu_fallback=use_stage_b_cpu_fallback,
            stage_b_use_warm_cache=stage_b_use_warm_cache,
            use_stage_b_roi_mode=use_stage_b_roi_mode,
            crystal=crystal,
            hkl_metadata=hkl_metadata,
            hkl_grid=hkl_grid,
            shell_indices=shell_indices,
            detector=detector,
            beam=beam,
            inputs=refinement_inputs,
            target_t=target_t,
            loss_mask_t=loss_mask_t,
            sigma_readout_t=sigma_readout_t,
            baseline_misset_deg_tensor=baseline_misset_deg_tensor,
            panel_shape=panel_shape,
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
        )

        # Unpack results from helper3
        status_b = stage_b_results['status']
        message_b = stage_b_results['message']
        best_loss_full_b = stage_b_results['best_loss_full_b']
        chi_squared_best_b = stage_b_results['chi_squared_best_b']
        masked_mse_best_b = stage_b_results['masked_mse_best_b']
        final_loss_value = stage_b_results['final_loss_value']
        final_mse_value = stage_b_results['final_mse_value']

        # Extract telemetry accumulators from param_values (updated in-place by closures)
        telemetry = param_values['telemetry_state']
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

        # Add mode-specific telemetry
        if stage_b_mode == "per_reflection":
            telemetry_output["mode"] = "per_reflection"
            telemetry_output["stage_b_mode"] = "per_reflection"

            # Add per-reflection custom attributes (matches nanobrag_refinement.py:5196-5206)
            with torch.no_grad():
                modifiers_exp = torch.exp(log_modifiers)
                modifiers_clamped = torch.clamp(
                    modifiers_exp,
                    min=1.0 / self._config.stage_b_max_modifier,
                    max=self._config.stage_b_max_modifier
                )

            telemetry_output["n_asu_unique"] = int(n_asu_unique)
            telemetry_output["optimizer_type"] = optimizer_type
            telemetry_output["asu_modifier_stats"] = {
                "min": float(modifiers_clamped.min().item()),
                "max": float(modifiers_clamped.max().item()),
                "mean": float(modifiers_clamped.mean().item()),
                "std": float(modifiers_clamped.std().item()),
            }
        else:  # shell mode
            telemetry_output["mode"] = "shell_modifiers"
            telemetry_output["stage_b_mode"] = "shell"

            # Add shell metadata for engine path to rebuild modified HKL grid (Phase C2)
            telemetry_output["shell_edges"] = shell_edges.cpu().tolist()
            telemetry_output["shell_indices"] = shell_indices.cpu().tolist()
            telemetry_output["n_shells"] = self._config.stage_b_n_shells

        return telemetry_output
