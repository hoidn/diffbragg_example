"""
LBFGS refinement nucleus for nanobrag_torch backend (Stage A/B/C).

Implements the staged refinement loop per:
- plans/nanobrag_integration_plan.md:172-244 (Refinement + Stage B contract)
- docs/spec-db-workflow.md:30-41 (Staging policy + LBFGS optimizer)
- docs/pytorch_runtime_checklist.md (vectorization, device/dtype neutrality)

Stage A scope:
- Parameters: global scale (ADU mode) + full crystal (a/b/c log-deltas, alpha/beta/gamma bounded angles, orientation 3-vector→quaternion)
- Loss: variance-weighted chi-squared per dbex.physics.loss._compute_variance_weighted_loss
        (spec-db-core.md/spec-db-workflow.md), with masked MSE tracked for telemetry.
- ROI policy: deterministic ROI sampling for LBFGS closure; periodic full validation
- Convergence: ≥0.2% loss drop within ≤30 LBFGS steps; non-increasing full-loss trace (TORCH-REFINE-002D)

Stage B (optional, TORCH-REFINE-004):
- Parameters: per-resolution shell multipliers for |F| (softplus parameterization)
- Requires: halo-padded HKL grid (hkl_metadata["has_halo"]=True) and enable_hkl_interpolation=True
- Freezes Stage A parameters; applies modifiers lazily to a copy of hkl_grid
- Convergence: ≥3% loss drop; guards against default_F fallback

Stage C (optional, TORCH-REFINE-003):
- Parameters: per-panel detector distance offsets along normal
- Freezes Stage A (and Stage B if run) parameters
- Convergence: ≥0.002% loss drop (REFINE-007)

Telemetry emitted to `/torch_diagnostics`:
- Per-stage: optimizer metadata, stage label, ROI sampling, loss traces, param_deltas, status
- Multi-stage runs return Dict[str, RefinementTelemetry] keyed by stage ("A", "B", "C")
"""

import copy
import math
import os
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch

# Stage A helpers relocated to dbex.refinement.stage_a_impl (ARCH-REFINE-001)
from dbex.refinement.stage_a_impl import (
    vec_to_unit_quaternion,
    quaternion_to_rotation_matrix,
    quaternion_to_xyz_euler,
    StageAROIEntry,
    StageAContext,
    _build_stage_a_context,
    _sync_stage_a_crystal,
    _retarget_stage_a_simulators,
    _build_stage_a_params,
    _build_stage_a_lbfgs_closure,
    _run_stage_a_lbfgs,
    _clamp_log_cell_deltas,
    _get_sigma_floor_sq_tensor,
)

# Stage B helpers relocated to dbex.refinement.stage_b_impl (ARCH-REFINE-001)
from dbex.refinement.stage_b_impl import (
    compute_hkl_shell_lookup,
    compute_hkl_asu_map,
    initialize_asu_modifiers,
    apply_asu_modifiers,
    _build_stage_b_params,
    _build_stage_b_lbfgs_closure,
    _run_stage_b_lbfgs,
)

# Stage C helpers relocated to dbex.refinement.stage_c_impl (ARCH-REFINE-001 Phase A.3)
from dbex.refinement.stage_c_impl import (
    _retarget_stage_a_detectors,
    _build_stage_c_params,
    _build_stage_c_lbfgs_closure,
    _run_stage_c_lbfgs,
)

from dbex.physics.loss import _compute_variance_weighted_loss


@dataclass
class RefinementConfig:
    """Configuration for Stage A and Stage C LBFGS refinement."""
    # LBFGS hyperparameters (shared across stages)
    history_size: int = 10
    max_iter: int = 30
    tolerance_grad: float = 1e-7
    tolerance_change: float = 1e-9

    # ROI sampling for LBFGS closure
    roi_sample_fraction: float = 0.15  # ~15% of ROIs per iteration
    full_validation_interval: int = 5  # Validate on full loss every N steps

    # Convergence guards (Stage A)
    min_loss_improvement: float = 0.002  # 0.2% minimum improvement (TORCH-REFINE-002D)
    early_stop_window: int = 3  # Stop if no improvement over last K validations
    max_loss_increase: float = 0.02  # 2% max increase before rollback

    # HKL interpolation (TORCH-REFINE-002D, REFINE-005)
    # Enable tricubic interpolation for structure factors; requires halo-padded grid
    # Defaults to False (nearest-neighbor) to protect datasets without halo support
    enable_hkl_interpolation: bool = False

    # U-matrix parameterization (TORCH-GEOMETRY-PARITY-002 Phase B)
    # Enable direct U-matrix quaternion parameterization for Stage A orientation.
    # When False (default), uses existing cell+misset decomposition path (GEOMETRY-003).
    # When True, parameterizes orientation as quaternion → U-matrix, preserving
    # mapping MOSFLM A* strain and eliminating the 1.37e-3 symmetric strain artifact.
    use_u_matrix_parameterization: bool = False

    # LBFGS optimizer for U-matrix path (TORCH-GEOMETRY-CONVERGENCE-001 Phase B Test B1)
    # When True, uses LBFGS optimizer instead of Adam for quaternion U-matrix refinement.
    # LBFGS eliminates momentum accumulation (H4), uses line search (H3), proven for scale-only.
    # Only applies when use_u_matrix_parameterization=True.
    use_lbfgs_for_u_matrix: bool = False

    # Learning rate for U-matrix path (TORCH-GEOMETRY-CONVERGENCE-001 Phase C2)
    # Learning rate for Adam optimizer when use_u_matrix_parameterization=True.
    # Default 1e-5 (10× lower than cell/misset LR) to accommodate quaternion gradient
    # scale O(150k). Per CONVERGENCE-001 Phase C1 root cause analysis.
    # Only applies when use_u_matrix_parameterization=True and use_lbfgs_for_u_matrix=False.
    u_matrix_learning_rate: float = 1e-5

    # Incremental UB parameterization (TORCH-GEOMETRY-UB-REALIGN-001 Phase B3)
    # Enable incremental UB parameterization around baseline dxtbx crystal state.
    # When False (default), uses existing cell+misset default path.
    # When True, parameterizes geometry as U(params) = ΔR(q_delta) @ U₀ and
    # B(params) via log-perturbations for lengths + angle deltas, constructing
    # A*(params) = U(params) @ B(params) in a single direction per spec-db-core.md:64-67.
    # Supersedes use_u_matrix_parameterization when both are enabled.
    use_incremental_ub: bool = False

    # Warm cache (PERF-WARM-SIM-001)
    # Enable Stage A warm cache (prebuild detector models/masks/HKL once).
    # Default True for production (2-5× speedup). Disable for benchmarking cold baseline.
    enable_stage_a_warm_cache: bool = True
    # Enable ROI-aware sampling/cropping when Stage A closures run (PERF-WARM-SIM-001 ROI follow-up)
    enable_stage_a_roi_mode: bool = True
    # Allow ROI sampling even when the warm cache is disabled (default False so cold benchmarks stay panel-scoped)
    allow_cold_stage_a_roi_mode: bool = False

    # Stage B structure factor modifiers (TORCH-REFINE-004)
    enable_stage_b: bool = False  # Enable Fhkl shell modifiers
    stage_b_mode: str = "per_reflection"  # "per_reflection" (default per spec:59) or "shell" (fallback per spec:60)
    stage_b_n_shells: int = 5  # Number of resolution shells for shell mode
    stage_b_min_loss_improvement: float = 1e-8  # 0.000001% minimum improvement for Stage B (calibrated per TORCH-REFINE-004 refGeom probe: measured ceiling ~6.4e-8%, essentially zero)
    stage_b_max_modifier: float = 2.0  # Maximum shell modifier (softplus clamp)
    stage_b_regularization: float = 0.0  # L2 regularization strength (reserved for future)
    stage_b_full_eval_on_cpu: bool = True  # Run Stage B evaluations on CPU to avoid GPU OOM when gradients require large buffers

    # Stage B per-reflection ASU mode (TORCH-REFINE-004 Phase 6)
    stage_b_optimizer_gate: int = 10000  # n_asu threshold for LBFGS vs Adam selection
    stage_b_adam_lr: float = 1e-2  # Adam learning rate for large parameter counts (≥10K) - Phase 7 tuned
    stage_b_modifier_clamp: Tuple[float, float] = (-3.0, 3.0)  # log-space clamp range (modifiers ∈ [0.05, 20.1])

    # Stage C detector microslip (TORCH-REFINE-003)
    enable_stage_c: bool = False  # Enable detector distance refinement
    stage_c_min_loss_improvement: float = 2e-5  # 0.002% minimum improvement for Stage C (calibrated per REFINE-007)
    stage_c_max_distance_delta_mm: float = 0.5  # Maximum distance adjustment per panel (mm)

    # Stage A panel validation (ARCH-REFINE-001, REFINE-007)
    # Force baseline/final validations to use panel mode instead of ROI sampling when Stage C is enabled
    # or when the canonical ROI count is small (≤32), ensuring Stage A telemetry reports panel-level chi²
    # that matches Stage C's initial state and satisfies REFINE-007 improvement gates.
    stage_a_force_panel_validation: bool = False  # Manually force panel-mode validations
    stage_a_panel_validation_roi_threshold: int = 32  # Auto-enable panel validations when ROI count ≤ threshold

    # Variance floor guard (PHYSICS-LOSS-002, spec-db-core.md:67)
    # Prevents infinite weights when I_model → 0 on GPU backends
    # Shares units with sigma_readout (target units: photons or ADU)
    sigma_floor_value: float = 1.0  # Default: ~1 photon equivalent

    # Sigma provenance metadata (PHYSICS-LOSS-001 A4)
    sigma_readout_provenance: Optional[str] = None
    sigma_readout_reference_value: Optional[float] = None

    # Calibration metadata (TOOLING-VIS-001 Phase D.C, DB-AT-027)
    # When provided, calibration payload from mapping (spot_scale_override,
    # beam flux/exposure, N_cells) is reused in Stage A context builders.
    # log_scale is then treated as a bounded delta (±3) around the calibrated baseline.
    calibration_metadata: Optional[Dict[str, Any]] = None
    # log_scale baseline when calibration is present (recorded in telemetry)
    log_scale_baseline: Optional[float] = None
    # Apply N_cells from calibration metadata (TOOLING-VIS-001 Phase D.C, SCALE-008)
    # When True (default), N_cells is applied if present in calibration_metadata.
    # When False, N_cells is suppressed even when present (for small-detector metadata fixtures).
    apply_calibration_n_cells: bool = True

    # Device and dtype for PyTorch operations
    device: str = "cpu"
    dtype: Any = torch.float32  # Actual dtype at runtime


@dataclass
class RefinementTelemetry:
    """Telemetry captured during refinement.

    For multi-stage refinement (Stage A + Stage C), this structure represents
    a single stage. The calling code aggregates multiple telemetry objects into
    a Dict[str, RefinementTelemetry] keyed by stage label ("A", "C").

    PHYSICS-LOSS-001: Tracks both chi_squared (variance-weighted loss, the optimization objective)
    and masked_mse (legacy metric for comparison). All stages minimize chi_squared per spec-db-core.md:57-68.

    ARCH-REFACTOR-001 Phase B: Dataclass with to_dict() for HDF5 serialization.
    """
    optimizer: str
    stage: str
    history_size: int
    max_iter: int
    tolerance_grad: float
    tolerance_change: float
    roi_sample_fraction: float
    roi_count_sampled: int
    roi_count_total: int
    loss_trace_sample: List[float] = field(default_factory=list)  # Deprecated: will be chi_squared_trace_sample after PHYSICS-LOSS-001
    loss_trace_full: List[Tuple[int, float]] = field(default_factory=list)  # Deprecated: will be chi_squared_trace_full after PHYSICS-LOSS-001
    best_loss_full: Tuple[float, int] = (0.0, 0)  # Deprecated: will be chi_squared_best after PHYSICS-LOSS-001
    param_deltas: Dict[str, float] = field(default_factory=dict)
    status: str = "ok"  # "ok" | "early_stop" | "rollback" | "error"
    message: str = ""
    perf_counters: Optional[Dict[str, Any]] = None  # PERF-WARM-SIM-001: closure_evals, forward_time_ms, validations
    # PHYSICS-LOSS-001: Dual loss metrics for cross-stage comparison
    chi_squared_trace_sample: Optional[List[float]] = None  # Chi-squared sampled trace (ROI subset)
    chi_squared_trace_full: Optional[List[Tuple[int, float]]] = None  # Chi-squared full trace [(iter, chi2), ...]
    chi_squared_best: Optional[Tuple[float, int]] = None  # Best chi-squared (value, iteration)
    masked_mse_trace_sample: Optional[List[float]] = None  # Masked-MSE sampled trace (legacy metric)
    masked_mse_trace_full: Optional[List[Tuple[int, float]]] = None  # Masked-MSE full trace [(iter, mse), ...]
    masked_mse_best: Optional[Tuple[float, int]] = None  # Best masked-MSE (value, iteration)
    sigma_readout_provenance: Optional[str] = None  # Source of sigma tensor (cli_override, calibrated_map, etc.)
    sigma_readout_reference_value: Optional[float] = None  # Reference scalar (target units, e.g., photons)
    # PHYSICS-LOSS-002: Variance floor telemetry (spec-db-core.md:67)
    variance_floor_value: Optional[float] = None  # sigma_floor^2 used in variance clamping
    variance_floor_clamp_fraction: Optional[float] = None  # Fraction of masked pixels where floor engaged
    variance_floor_masked_pixels: Optional[int] = None  # Total masked pixels used in variance stats
    variance_floor_clamped_pixels: Optional[int] = None  # Pixels where sigma_floor clamp engaged
    # SCALE-008 / TOOLING-VIS-001: Mapping-aware log-scale baseline telemetry
    log_scale_baseline_source: Optional[str] = None  # Source of log_scale_baseline (mapping_global_scale_hint, spot_scale_override_sqrt, etc.)
    spot_scale_override_adjustment_factor: Optional[float] = None  # Adjustment factor when calibration was corrected for N_cells
    # TOOLING-VIS-001 Phase D.E: Masked-mean telemetry for Stage A baseline derivation
    target_mean_masked: Optional[float] = None  # Masked mean of target data used for log_scale_baseline
    model_mean_masked: Optional[float] = None  # Masked mean of Stage A zero-iteration model used for log_scale_baseline
    # PHYSICS-LOSS-003: Canonical Stage A snapshot propagated to downstream stages
    canonical_stage_label: Optional[str] = None
    canonical_chi_squared: Optional[float] = None
    canonical_chi_squared_iteration: Optional[int] = None
    canonical_roi_count: Optional[int] = None
    canonical_detector_distances_mm: Optional[List[float]] = None
    roi_mode: Optional[str] = None
    # Phase A4: Stage identification for engine aggregation
    stage_type: Optional[str] = None  # Stage identifier (A, B, C, or custom)
    mode: Optional[str] = None  # Stage mode (e.g., "shell_modifiers", "detector_offsets")
    # Phase E: Engine delegation telemetry
    engine_protocol: Optional[str] = None  # e.g., "A→B→C", "A-only", "A→B"
    stage_modes: Optional[Dict[str, str]] = None  # e.g., {"B": "shell", "C": "detector_offsets"}
    telemetry_version: str = "1.0"  # Schema versioning for future compatibility

    def to_dict(self) -> Dict[str, Any]:
        """Convert telemetry to dict for HDF5 serialization."""
        return asdict(self)


def _build_final_bragg_from_stage_b_telemetry(
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
    from dbex.nanobrag_bridge import (
        create_detector_config,
        create_crystal_config,
        compute_baseline_misset_deg,
    )

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
    log_scale = torch.tensor(param_deltas_a['log_scale']['final'], device=device, dtype=dtype, requires_grad=False)
    log_cell_a_delta = torch.tensor(param_deltas_a['log_cell_a_delta']['final'], device=device, dtype=dtype, requires_grad=False)
    log_cell_b_delta = torch.tensor(param_deltas_a['log_cell_b_delta']['final'], device=device, dtype=dtype, requires_grad=False)
    log_cell_c_delta = torch.tensor(param_deltas_a['log_cell_c_delta']['final'], device=device, dtype=dtype, requires_grad=False)
    angle_alpha_raw = torch.tensor(param_deltas_a['angle_alpha_raw']['final'], device=device, dtype=dtype, requires_grad=False)
    angle_beta_raw = torch.tensor(param_deltas_a['angle_beta_raw']['final'], device=device, dtype=dtype, requires_grad=False)
    angle_gamma_raw = torch.tensor(param_deltas_a['angle_gamma_raw']['final'], device=device, dtype=dtype, requires_grad=False)

    # Extract misset from Stage A (this is the delta, not frozen in Stage B inline code but added to baseline)
    misset_xyz_deg_delta = param_deltas_a['misset_xyz_deg']['delta']
    misset_xyz_deg = torch.tensor(misset_xyz_deg_delta, device=device, dtype=dtype, requires_grad=False)

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
        if hasattr(telemetry_b, 'shell_edges'):
            shell_edges = torch.tensor(telemetry_b.shell_edges, device=device, dtype=dtype)
            shell_indices = torch.tensor(telemetry_b.shell_indices, device=device, dtype=torch.long)
            n_shells = telemetry_b.n_shells
        else:
            shell_edges = torch.tensor(telemetry_b['shell_edges'], device=device, dtype=dtype)
            shell_indices = torch.tensor(telemetry_b['shell_indices'], device=device, dtype=torch.long)
            n_shells = telemetry_b['n_shells']

        # Extract shell modifiers from Stage B param_deltas
        shell_modifiers_final = torch.zeros(n_shells, device=device, dtype=dtype)
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
    baseline_misset_deg_tensor = compute_baseline_misset_deg(
        crystal,
        baseline_crystal,
        device=device,
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
        # Cold path: instantiate fresh simulators per panel
        for pid in range(n_panels):
            detector_config = create_detector_config(
                panel=detector[pid],
                beam=beam,
                trusted_mask=inputs.trusted_mask[pid]
            )
            if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                detector_config.mask_array = torch.tensor(
                    detector_config.mask_array, dtype=torch.float32, device=final_device
                )
            crystal_config, _ = create_crystal_config(
                crystal, None,
                crystal_overrides=crystal_overrides,
                misset_deg_override=final_misset,
                apply_n_cells=False
            )
            detector_model = Detector(detector_config, device=final_device, dtype=dtype)
            crystal_model = Crystal(crystal_config, device=final_device, dtype=dtype)
            crystal_model.interpolate = True
            crystal_model.hkl_data = hkl_grid_modified.to(device=final_device, dtype=dtype)
            crystal_model.hkl_metadata = hkl_metadata
            simulator = Simulator(detector=detector_model, crystal=crystal_model, device=final_device, dtype=dtype)
            bragg_panel = simulator.run()
            log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
            bragg_scaled = bragg_panel * torch.exp(log_scale_clamped)
            bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)

    return bragg_full


def run_nanobrag_refinement(
    inputs,
    detector,
    beam,
    crystal,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    config: Optional[RefinementConfig] = None,
    baseline_crystal=None,
    baseline_detector=None
) -> Tuple[np.ndarray, Dict[str, RefinementTelemetry]]:
    """
    Run Stage A (+ optional Stage C) LBFGS refinement on nanobrag_torch simulator.

    Stage A optimizes:
    - log_scale: global intensity scale (ADU mode)
    - log_cell_*_delta: unit cell length perturbations (a/b/c)
    - angle_*_raw: unit cell angle perturbations (alpha/beta/gamma)
    - orientation_vec: crystal misorientation (3-vector → quaternion → XYZ Euler)

    Stage C (when config.enable_stage_c=True) optimizes:
    - per-panel detector distance offsets along panel normal (odet_vec)

    Args:
        inputs: RefinementInputs with target, loss_mask, panel_slices, trusted_mask
        detector: dxtbx Detector object (multi-panel, possibly perturbed for Stage C smoke)
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object (possibly perturbed from baseline)
        hkl_grid: torch.Tensor structure factor grid (P1 dense)
        hkl_metadata: dict with grid dimensions and metadata
        config: Optional RefinementConfig; uses defaults if None
        baseline_crystal: Optional baseline dxtbx Crystal object for extracting deterministic
                        misset when `crystal` is perturbed (TORCH-REFINE-002D). When provided,
                        computes U_delta = U_perturbed @ U_baseline^{-1} and adds it to the
                        orientation refinement path as a tensor to preserve differentiability.
        baseline_detector: Optional dxtbx Detector capturing the unperturbed geometry. When
                        provided, Stage C telemetry records initial/final offsets relative to this
                        baseline; otherwise offsets are reported relative to the perturbed detector.

    Returns:
        Tuple of:
        - Bragg: np.ndarray [panel, slow, fast] final simulated intensities after all stages (CPU, float32)
        - telemetry_dict: Dict[str, RefinementTelemetry] keyed by stage label ("A", "C")
                         Always contains "A"; contains "C" only when config.enable_stage_c=True

    Raises:
        RuntimeError: If simulator fails or gradients are NaN/Inf
    """
    if os.environ.get("NANOBRAGG_DISABLE_COMPILE") == "1":
        os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from dbex.nanobrag_bridge import (
        create_detector_config,
        create_beam_config,
        create_crystal_config,
        compute_baseline_misset_deg,
    )

    if config is None:
        config = RefinementConfig()

    # Detect Stage-A-only mode for conditional engine delegation (Phase B2)
    stage_a_only_mode = (not config.enable_stage_c and not config.enable_stage_b)

    # Detect Stage A→B mode for conditional engine delegation (Phase C2)
    stage_a_b_mode = (not config.enable_stage_c and config.enable_stage_b)

    if stage_a_only_mode:
        # === ENGINE DELEGATION PATH (Phase B2) ===
        # Lazy imports to avoid circular dependencies at module load time
        from dbex.refinement.engine import RefinementEngine
        from dbex.refinement.stage_a import StageA

        # Build inputs dict per StageA.run() contract (dbex/refinement/stage_a.py:71-78)
        engine_inputs = {
            'refinement_inputs': inputs,
            'detector': detector,
            'beam': beam,
            'crystal': crystal,
            'hkl_grid': hkl_grid,
            'hkl_metadata': hkl_metadata,
            'baseline_crystal': baseline_crystal,
            'baseline_detector': baseline_detector,
        }

        # Instantiate RefinementEngine with StageA
        engine = RefinementEngine(stages=[StageA()], config=config)

        # Execute engine and get telemetry dict (keyed by stage.name = "stage_a")
        telemetry_dict = engine.run(engine_inputs)
        stage_a_ctx = getattr(engine, "_stage_a_ctx_cache", None)

        # Extract StageA telemetry (keyed by "stage_a" per StageA.name property)
        telemetry_a = telemetry_dict["stage_a"]

        # Phase E: Enrich telemetry with engine protocol and stage modes
        from dataclasses import asdict
        telemetry_a_dict = asdict(telemetry_a)
        telemetry_a_dict["engine_protocol"] = "stage_a"  # Stage-A-only mode
        telemetry_a_dict["stage_modes"] = {}  # No Stage B/C enabled
        telemetry_a_enriched = RefinementTelemetry(**telemetry_a_dict)

        # Build final Bragg array using optimized parameters from telemetry
        device = torch.device(config.device)
        dtype = config.dtype
        bragg_full = _build_final_bragg_from_stage_a_telemetry(
            telemetry_a_enriched, detector, beam, crystal, inputs, hkl_grid,
            hkl_metadata, config, device, dtype,
            stage_a_ctx=stage_a_ctx,
            baseline_crystal=baseline_crystal,
        )

        # Return with telemetry dict using "A" key for backward compatibility
        # (Legacy code expects {"A": RefinementTelemetry, ...})
        return bragg_full, {"A": telemetry_a_enriched}

    elif stage_a_b_mode:
        # === ENGINE DELEGATION PATH (Phase C2: A→B) ===
        from dbex.refinement.engine import RefinementEngine
        from dbex.refinement.stage_a import StageA
        from dbex.refinement.stage_b import StageB

        # Build inputs dict per StageA/StageB.run() contract
        engine_inputs = {
            'refinement_inputs': inputs,
            'detector': detector,
            'beam': beam,
            'crystal': crystal,
            'hkl_grid': hkl_grid,
            'hkl_metadata': hkl_metadata,
            'baseline_crystal': baseline_crystal,
            'baseline_detector': baseline_detector,
        }

        # Instantiate RefinementEngine with StageA → StageB sequence
        # Note: CPU fallback for Stage B (PERF-WARM-011/012) is handled internally by
        # _build_stage_b_params which receives stage_a_ctx from StageA via engine propagation
        engine = RefinementEngine(stages=[StageA(), StageB()], config=config)

        # Execute engine and get telemetry dict (keyed by stage.name = "stage_a", "stage_b")
        telemetry_dict = engine.run(engine_inputs)

        # Extract Stage A and Stage B telemetry (keyed by "stage_a", "stage_b" per stage.name property)
        telemetry_a_raw = telemetry_dict["stage_a"]
        telemetry_b_raw = telemetry_dict["stage_b"]

        # Build final Bragg array using Stage B optimized shell modifiers
        device = torch.device(config.device)
        dtype = config.dtype

        # Extract stage_a_ctx from engine cache (cached separately from telemetry)
        stage_a_ctx = getattr(engine, '_stage_a_ctx_cache', None)

        # PERF-WARM-011: Recompute CPU fallback decision for final Bragg reconstruction
        # Same logic as in _build_stage_b_params (lines 2178-2182)
        panel_slices = inputs.panel_slices
        canonical_roi_count = len(panel_slices)
        use_stage_a_roi_mode = bool(
            config.enable_stage_a_roi_mode
            and canonical_roi_count > 0
            and (config.enable_stage_a_warm_cache or config.allow_cold_stage_a_roi_mode)
        )
        use_stage_b_cpu_fallback = (
            config.stage_b_full_eval_on_cpu
            and str(device).startswith("cuda")
            and not use_stage_a_roi_mode  # ROI mode is disabled (panel mode)
        )

        # If CPU fallback is active, use CPU device for final Bragg reconstruction
        final_device = torch.device("cpu") if use_stage_b_cpu_fallback else device

        # PERF-WARM-012: Clone Stage A context to CPU when CPU fallback is active
        # (Mirrors logic in _build_stage_b_params lines 2199-2220)
        stage_b_eval_stage_a_ctx = None
        if use_stage_b_cpu_fallback and stage_a_ctx is not None and config.enable_stage_a_warm_cache:
            # Build a fresh Stage A context on CPU device
            cpu_device = torch.device("cpu")
            stage_b_eval_stage_a_ctx = _build_stage_a_context(
                detector=detector,
                beam=beam,
                crystal=crystal,
                trusted_mask=inputs.trusted_mask,
                hkl_grid=hkl_grid,
                hkl_metadata=hkl_metadata,
                enable_hkl_interpolation=config.enable_hkl_interpolation,
                device=cpu_device,
                dtype=dtype,
                panel_slices=panel_slices,
                enable_roi_mode=False,  # CPU fallback is panel-mode only
                calibration_metadata=config.calibration_metadata,
                log_scale_baseline=config.log_scale_baseline,
                apply_calibration_n_cells=config.apply_calibration_n_cells,
            )
        elif not use_stage_b_cpu_fallback:
            # No CPU fallback: reuse the original CUDA Stage A context
            stage_b_eval_stage_a_ctx = stage_a_ctx

        # Extract shell metadata from engine cache (cached separately from telemetry)
        shell_edges = getattr(engine, '_stage_b_shell_edges', None)
        shell_indices = getattr(engine, '_stage_b_shell_indices', None)
        n_shells = getattr(engine, '_stage_b_n_shells', None)

        # Extract custom attributes from engine cache (Phase 8 fix #2)
        stage_b_mode = getattr(engine, '_stage_b_mode', None)
        n_asu_unique = getattr(engine, '_stage_b_n_asu_unique', None)
        optimizer_type = getattr(engine, '_stage_b_optimizer_type', None)
        asu_modifier_stats = getattr(engine, '_stage_b_asu_modifier_stats', None)

        # Create a dict version of telemetry_b with shell metadata for the helper
        from dataclasses import asdict
        telemetry_b_dict = asdict(telemetry_b_raw)
        if shell_edges is not None:
            telemetry_b_dict['shell_edges'] = shell_edges
        if shell_indices is not None:
            telemetry_b_dict['shell_indices'] = shell_indices
        if n_shells is not None:
            telemetry_b_dict['n_shells'] = n_shells
        # Add custom attributes back to dict (Phase 8 fix #2)
        if stage_b_mode is not None:
            telemetry_b_dict['stage_b_mode'] = stage_b_mode
        if n_asu_unique is not None:
            telemetry_b_dict['n_asu_unique'] = n_asu_unique
        if optimizer_type is not None:
            telemetry_b_dict['optimizer_type'] = optimizer_type
        if asu_modifier_stats is not None:
            telemetry_b_dict['asu_modifier_stats'] = asu_modifier_stats

        bragg_full = _build_final_bragg_from_stage_b_telemetry(
            telemetry_a=telemetry_a_raw,
            telemetry_b=telemetry_b_dict,
            detector=detector,
            beam=beam,
            crystal=crystal,
            baseline_crystal=baseline_crystal,
            inputs=inputs,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            config=config,
            device=final_device,  # Use CPU device if CPU fallback is active
            dtype=dtype,
            use_stage_b_cpu_fallback=use_stage_b_cpu_fallback,
            stage_a_ctx=stage_b_eval_stage_a_ctx,  # Use CPU-cloned context when fallback active
        )

        # Repackage telemetry with backward-compatible keys ("A", "B")
        # Use engine's telemetry objects directly to preserve custom attributes (Phase 8 Alternative pattern)
        # The engine already restored custom attributes (stage_b_mode, n_asu_unique, etc.) per engine.py:161-168
        telemetry_a = telemetry_a_raw
        telemetry_b = telemetry_b_raw

        # Add engine protocol and stage modes for Phase E telemetry enrichment
        engine_protocol_value = "stage_a→stage_b"
        stage_modes_value = {
            "B": config.stage_b_mode  # Use actual config value ("per_reflection" or "shell")
        }
        telemetry_a.engine_protocol = engine_protocol_value
        telemetry_a.stage_modes = stage_modes_value
        telemetry_b.engine_protocol = engine_protocol_value
        telemetry_b.stage_modes = stage_modes_value

        return bragg_full, {"A": telemetry_a, "B": telemetry_b}

    else:
        # === ENGINE DELEGATION PATH (Phase A.4: A→C or A→B→C) ===
        # Lazy imports to avoid circular dependencies
        from dbex.refinement.engine import RefinementEngine
        from dbex.refinement.stage_a import StageA
        from dbex.refinement.stage_b import StageB
        from dbex.refinement.stage_c import StageC

        # Build stage list based on config flags
        stages = [StageA()]  # Stage A always runs

        if config.enable_stage_b:
            # Guard: Stage B requires baseline_detector
            if baseline_detector is None:
                raise ValueError(
                    "Stage B requires baseline_detector parameter. "
                    "Pass the baseline dxtbx Detector object to run_nanobrag_refinement()."
                )
            stages.append(StageB())

        if config.enable_stage_c:
            # Guard: Stage C requires baseline_detector
            if baseline_detector is None:
                raise ValueError(
                    "Stage C requires baseline_detector parameter. "
                    "Pass the baseline dxtbx Detector object to run_nanobrag_refinement()."
                )
            stages.append(StageC())

        # Build engine protocol string for telemetry
        stage_names = [s.name for s in stages]
        engine_protocol = "→".join(stage_names)  # e.g., "stage_a→stage_c", "stage_a→stage_b→stage_c"

        # Build stage_modes dict for telemetry
        stage_modes = {}
        if config.enable_stage_b:
            stage_modes["B"] = config.stage_b_mode  # "per_reflection" or "shell"
        if config.enable_stage_c:
            stage_modes["C"] = "detector_offsets"

        # Prepare RefinementInputs for engine
        engine_inputs = {
            "refinement_inputs": inputs,
            "detector": detector,
            "beam": beam,
            "crystal": crystal,
            "hkl_grid": hkl_grid,
            "hkl_metadata": hkl_metadata,
            "baseline_crystal": baseline_crystal,
            "baseline_detector": baseline_detector,
        }

        # Execute engine
        engine = RefinementEngine(stages=stages, config=config)
        engine_telemetry = engine.run(inputs=engine_inputs, telemetry_sink=None)

        # Extract final Bragg array based on last stage
        last_stage_name = stage_names[-1]
        device = torch.device(config.device)
        dtype = config.dtype

        if last_stage_name == "stage_c":
            # Stage C produces final Bragg directly
            bragg_full = getattr(engine, '_stage_c_bragg_full', None)
            if bragg_full is None:
                raise RuntimeError(
                    "Stage C did not produce final Bragg array. "
                    "This is a bug in the Stage C wrapper."
                )
        elif last_stage_name == "stage_b":
            # Build final Bragg from Stage B telemetry
            # (This path already handled above in stage_a_b_mode, shouldn't reach here)
            raise RuntimeError(
                "Unexpected: Stage A→B path should have been handled by stage_a_b_mode branch. "
                "This is a bug in run_nanobrag_refinement control flow."
            )
        else:
            # Stage A only
            # (This path already handled above in stage_a_only_mode, shouldn't reach here)
            raise RuntimeError(
                "Unexpected: Stage A-only path should have been handled by stage_a_only_mode branch. "
                "This is a bug in run_nanobrag_refinement control flow."
            )

        # Enrich telemetry with engine protocol + stage modes
        telemetry_out = {}
        stage_name_map = {"stage_a": "A", "stage_b": "B", "stage_c": "C"}

        for stage_name, telem_obj in engine_telemetry.items():
            # Add engine protocol fields directly to existing object
            telem_obj.engine_protocol = engine_protocol
            telem_obj.stage_modes = stage_modes

            legacy_key = stage_name_map.get(stage_name, stage_name)
            telemetry_out[legacy_key] = telem_obj

        return bragg_full, telemetry_out

