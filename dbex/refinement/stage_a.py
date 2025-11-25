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
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional
import numpy as np
import torch

# Lazy imports for heavy modules (prevent circular imports)
def _lazy_import_refinement():
    """Lazy import nanobrag_refinement to avoid circular dependencies."""
    from dbex import nanobrag_refinement
    return nanobrag_refinement


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

        # Import helpers (lazy to avoid circular imports at module load time)
        from dbex.nanobrag_refinement import (
            _build_stage_a_params,
            _build_stage_a_lbfgs_closure,
            _run_stage_a_lbfgs,
            RefinementTelemetry,
            vec_to_unit_quaternion,
            quaternion_to_xyz_euler
        )

        # Extract inputs (unpack dict into individual params)
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
        perf_closure_evals = telemetry_state['perf_closure_evals']
        perf_validation_runs = telemetry_state['perf_validation_runs']
        perf_forward_times_ms = telemetry_state['perf_forward_times_ms']
        variance_floor_clamped_pixels = telemetry_state['variance_floor_clamped_pixels']
        variance_floor_masked_pixels = telemetry_state['variance_floor_masked_pixels']
        loss_trace_sample = telemetry_state['loss_trace_sample']
        loss_trace_full = telemetry_state['loss_trace_full']
        best_loss_full = telemetry_state['best_loss_full']
        chi_squared_trace_sample = telemetry_state['chi_squared_trace_sample']
        chi_squared_trace_full = telemetry_state['chi_squared_trace_full']
        chi_squared_best = telemetry_state['chi_squared_best']
        masked_mse_trace_sample = telemetry_state['masked_mse_trace_sample']
        masked_mse_trace_full = telemetry_state['masked_mse_trace_full']
        masked_mse_best = telemetry_state['masked_mse_best']

        # STEP 2: Build Stage A LBFGS closure
        compute_loss, closure = _build_stage_a_lbfgs_closure(
            param_values=param_values,
            telemetry_state=telemetry_state,
            stage_a_context=stage_a_context,
            crystal=crystal,
            detector=detector,
            beam=beam,
            inputs=refinement_inputs,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            config=self._config,
            sigma_floor_sq_cache=sigma_floor_sq_cache,
            device=device,
            dtype=dtype,
            baseline_crystal=baseline_crystal
        )

        # STEP 3: Run Stage A LBFGS optimization
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
        )

        log_cell_a_delta_clamped = torch.clamp(
            log_cell_a_delta, min=-self._config.log_cell_max_delta, max=self._config.log_cell_max_delta
        )
        log_cell_b_delta_clamped = torch.clamp(
            log_cell_b_delta, min=-self._config.log_cell_max_delta, max=self._config.log_cell_max_delta
        )
        log_cell_c_delta_clamped = torch.clamp(
            log_cell_c_delta, min=-self._config.log_cell_max_delta, max=self._config.log_cell_max_delta
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
            }
        }

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

        # Add stage_a_ctx for Stage B warm cache support (Phase C2)
        # This is a non-RefinementTelemetry field but required for engine propagation
        telemetry_output["stage_a_ctx"] = stage_a_context.get('stage_a_ctx', None)

        return telemetry_output
