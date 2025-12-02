# dbex/refinement/stage_a_impl.py
"""
Stage A implementation helpers extracted from dbex.nanobrag_refinement.

Provides:
- StageAROIEntry: ROI entry dataclass for warm cache
- StageAContext: Cached detector models and tensors for Stage A refinement
- Quaternion helpers: vec_to_unit_quaternion, quaternion_to_rotation_matrix, quaternion_to_xyz_euler
- _build_stage_a_context: Prebuild Stage A detector models and tensorize masks/HKL
- _build_stage_a_params: Build trainable parameters for Stage A LBFGS refinement
- _build_stage_a_lbfgs_closure: Build LBFGS closure for Stage A refinement
- _run_stage_a_lbfgs: Execute Stage A LBFGS optimization and final validation
- _sync_stage_a_crystal: Ensure warmed Crystal carries cached HKL grid + interpolation flag
- _retarget_stage_a_simulators: Attach warmed Crystal to every cached Simulator

References:
- docs/spec-db-workflow.md:30-41 (Staging policy + LBFGS optimizer)
- docs/pytorch_runtime_checklist.md (vectorization, device/dtype neutrality)
- ARCH-REFINE-001: Refinement Engine Modularization & Torch IO
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

# ARCH-STAGE-CONTEXT-001: Import new dataclasses for typed context
from dbex.refinement.context import RefinementSharedContext, StageATelemetryState


# ============================================================================
# Quaternion Helpers (Stage A orientation parameterization)
# ============================================================================


def vec_to_unit_quaternion(vec: torch.Tensor) -> torch.Tensor:
    """
    Convert 3-vector to unit quaternion for orientation perturbation.

    Maps R^3 → S^3 (unit quaternion) by treating vec as the imaginary part
    and normalizing: q = [sqrt(1 - ||v||^2), v] when ||v|| < 1, else normalize full [0, v].

    Args:
        vec: torch.Tensor shape (3,) representing orientation perturbation

    Returns:
        q: torch.Tensor shape (4,) with q[0]=w (real), q[1:4]=x,y,z (imaginary), ||q||=1
    """
    # Clamp norm to prevent gradient issues at ||v|| = 1
    norm_sq = (vec ** 2).sum()
    norm_sq_clamped = torch.clamp(norm_sq, max=0.99)

    # Real part: w = sqrt(1 - ||v||^2)
    w = torch.sqrt(1.0 - norm_sq_clamped)

    # Quaternion [w, x, y, z]
    q = torch.cat([w.unsqueeze(0), vec])

    # Normalize to ensure unit quaternion (handles edge cases)
    q = q / (q.norm() + 1e-8)

    return q


def quaternion_to_rotation_matrix(q: torch.Tensor) -> torch.Tensor:
    """
    Convert unit quaternion to 3×3 rotation matrix.

    Args:
        q: torch.Tensor shape (4,) with q[0]=w, q[1:4]=x,y,z, ||q||=1

    Returns:
        R: torch.Tensor shape (3, 3) rotation matrix
    """
    w, x, y, z = q[0], q[1], q[2], q[3]

    # Build rotation matrix per standard quaternion→matrix formula
    R = torch.stack([
        torch.stack([1 - 2*(y**2 + z**2), 2*(x*y - w*z), 2*(x*z + w*y)]),
        torch.stack([2*(x*y + w*z), 1 - 2*(x**2 + z**2), 2*(y*z - w*x)]),
        torch.stack([2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x**2 + y**2)])
    ])

    return R


def quaternion_to_xyz_euler(q: torch.Tensor) -> torch.Tensor:
    """
    Convert unit quaternion to XYZ extrinsic Euler angles (degrees).

    Per docs/spec-db-workflow.md:30 and docs/nanobrag_api.md:55-56, orientation
    is controlled via misset_deg XYZ extrinsic rotations applied after MOSFLM A*.

    Args:
        q: torch.Tensor of shape (4,) representing unit quaternion [w, x, y, z]
           where w is the scalar part

    Returns:
        xyz_deg: torch.Tensor of shape (3,) with XYZ extrinsic Euler angles in degrees
                 Convention: R = R_z(gamma) @ R_y(beta) @ R_x(alpha) (extrinsic XYZ)

    References:
        - reports/maintainer_responses.md:685 — misset_deg applied as XYZ extrinsic rotations
        - plans/nanobrag_integration_plan.md:114 — quaternion→XYZ conversion pattern
    """
    # Normalize quaternion to ensure unit length (differentiable)
    q = q / torch.sqrt(torch.sum(q**2) + 1e-8)

    w, x, y, z = q[0], q[1], q[2], q[3]

    # XYZ extrinsic Euler angles from quaternion
    # R = R_z(gamma) @ R_y(beta) @ R_x(alpha)
    # See: https://en.wikipedia.org/wiki/Conversion_between_quaternions_and_Euler_angles

    # Roll (alpha, rotation about X-axis)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x**2 + y**2)
    alpha_rad = torch.atan2(sinr_cosp, cosr_cosp)

    # Pitch (beta, rotation about Y-axis)
    sinp = 2 * (w * y - z * x)
    # Clamp to avoid NaN from asin at ±1
    sinp = torch.clamp(sinp, -1.0, 1.0)
    beta_rad = torch.asin(sinp)

    # Yaw (gamma, rotation about Z-axis)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y**2 + z**2)
    gamma_rad = torch.atan2(siny_cosp, cosy_cosp)

    # Convert to degrees
    xyz_deg = torch.stack([alpha_rad, beta_rad, gamma_rad]) * (180.0 / np.pi)

    return xyz_deg


# ============================================================================
# Stage A Data Structures
# ============================================================================


@dataclass
class StageAROIEntry:
    """Cached ROI detector + simulator pair for Stage A warm cache."""
    roi_index: int
    panel_id: int
    bbox: Tuple[int, int, int, int]
    slow_slice: slice
    fast_slice: slice
    detector_model: Any
    simulator: Any


@dataclass
class StageAContext:
    """
    Cached detector models and tensors for Stage A refinement (PERF-WARM-SIM-001).

    Hoists per-panel Detector model instantiation, mask tensorization, and HKL grid
    transfers out of the LBFGS closure. The closure then only updates parameter tensors
    and runs forward passes through cached models, eliminating repeated construction overhead.
    When ROI sampling is enabled, this context additionally stores cropped Detector/Simulator
    pairs per ROI so closures can simulate only the requested bounding boxes.

    Fields:
        detector_configs: List of DetectorConfig objects per panel (length n_panels)
        detector_models: List of Detector model instances per panel (length n_panels)
        simulators: List of Simulator instances per panel cached with detector/beam state
        roi_entries: Optional list of StageAROIEntry objects (length roi_count when ROI cache enabled)
        beam_config: Single BeamConfig shared across all panels/ROIs
        trusted_masks_t: torch.Tensor stacked trusted masks [panel, slow, fast] (dtype=bool)
        baseline_distance_mm: List of baseline detector distances per panel (length n_panels)
        roi_panel_map: Dict mapping ROI index to panel_id (PERF-WARM-013 Stage C retargeting)
        hkl_grid: torch.Tensor structure factor grid on target device
        hkl_metadata: dict with grid dimensions and halo status
        device: torch device for all tensors
        dtype: torch dtype for all tensors
        n_panels: int, number of panels
        roi_count: int, number of cached ROI entries
        enable_hkl_interpolation: bool, tricubic interpolation flag
        q_params: Optional quaternion parameters for U-matrix path (TORCH-GEOMETRY-PARITY-002 Phase B4)
        B_ideal_reciprocal: Optional B_ideal matrix for U-matrix path (TORCH-GEOMETRY-PARITY-002 Phase B4)
    """
    detector_configs: List
    detector_models: List
    simulators: List
    roi_entries: Optional[List[StageAROIEntry]]
    beam_config: object
    trusted_masks_t: Optional[torch.Tensor]
    baseline_distance_mm: List[float]
    roi_panel_map: Dict[int, int]
    hkl_grid: torch.Tensor
    hkl_metadata: Dict
    device: torch.device
    dtype: torch.dtype
    n_panels: int
    roi_count: int
    enable_hkl_interpolation: bool
    q_params: Optional[torch.Tensor] = None
    B_ideal_reciprocal: Optional[torch.Tensor] = None
    calibration_metadata: Optional[Dict[str, Any]] = None
    log_scale_baseline: Optional[float] = None
    spot_scale_override: Optional[float] = None
    sqrt_spot_scale: Optional[float] = None


# ============================================================================
# Stage A Helpers
# ============================================================================


def _sync_stage_a_crystal(stage_a_ctx: StageAContext, crystal_model):
    """
    Ensure the warmed Crystal carries the cached HKL grid + interpolation flag.
    """
    crystal_model.interpolate = stage_a_ctx.enable_hkl_interpolation
    crystal_model.hkl_data = stage_a_ctx.hkl_grid
    crystal_model.hkl_metadata = stage_a_ctx.hkl_metadata
    # Allow Simulator fallback (when beam_config argument omitted) to pick up cached beam config
    crystal_model.beam_config = stage_a_ctx.beam_config  # type: ignore[attr-defined]
    return crystal_model


def _retarget_stage_a_simulators(stage_a_ctx: StageAContext, crystal_model) -> None:
    """
    Attach the warmed Crystal to every cached Simulator so ROI/pixel caches stay hot.
    """
    for simulator in stage_a_ctx.simulators:
        simulator.crystal = crystal_model
        simulator.beam_config = stage_a_ctx.beam_config
    if stage_a_ctx.roi_entries:
        for entry in stage_a_ctx.roi_entries:
            entry.simulator.crystal = crystal_model
            entry.simulator.beam_config = stage_a_ctx.beam_config


def _build_stage_a_context(
    detector,
    beam,
    crystal,
    trusted_mask,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    enable_hkl_interpolation: bool,
    device: torch.device,
    dtype: torch.dtype,
    panel_slices,
    enable_roi_mode: bool,
    calibration_metadata: Optional[Dict[str, Any]] = None,
    log_scale_baseline: Optional[float] = None,
    apply_calibration_n_cells: bool = True,
) -> StageAContext:
    """
    Prebuild Stage A detector models and tensorize masks/HKL once (PERF-WARM-SIM-001).

    This helper constructs all per-panel Detector models, tensorizes trusted masks,
    and transfers the HKL grid to the target device. The LBFGS closure then reuses
    these cached models and only updates Crystal parameter tensors per iteration,
    eliminating repeated construction overhead.

    Args:
        detector: dxtbx Detector object (multi-panel)
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object providing baseline configuration
        trusted_mask: numpy array or tuple of masks [panel, slow, fast]
        hkl_grid: torch.Tensor structure factor grid (P1 dense)
        hkl_metadata: dict with grid dimensions and halo status
        enable_hkl_interpolation: bool, tricubic interpolation flag
        device: torch device
        dtype: torch dtype
        panel_slices: List of (panel_id, bbox) tuples describing ROI bounds
        enable_roi_mode: bool flag for ROI cache construction
        calibration_metadata: Optional dict with calibration payload (spot_scale_override,
            beam flux/exposure, N_cells). When provided, calibration is reused.
        log_scale_baseline: Optional baseline log_scale value
        apply_calibration_n_cells: Whether to apply N_cells from calibration_metadata when
            present (default True). Set to False for small-detector metadata fixtures per
            TOOLING-VIS-001 Phase D.C and SCALE-008.

    Returns:
        StageAContext with prebuilt models and tensorized data
    """
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from nanobrag_torch.simulator import Simulator
    from dbex.nanobrag_bridge import (
        create_detector_config,
        create_beam_config,
        create_crystal_config,
    )

    n_panels = len(detector)

    # Build detector configs and models per panel
    detector_configs = []
    detector_models = []
    simulators = []
    trusted_masks_t_list: List[torch.Tensor] = []
    roi_entries: List[StageAROIEntry] = []
    baseline_distance_mm: List[float] = []

    # Extract calibration payload (TOOLING-VIS-001 Phase D.C, DB-AT-027)
    # When calibration_metadata is provided, forward beam flux/exposure/beamsize
    # and N_cells into configs so zero-point Stage A matches mapping baseline
    beam_flux = None
    beam_exposure = None
    beamsize_mm = None
    N_cells = None
    spot_scale_override = None
    sqrt_spot_scale = None
    calibration_adjusted_for_n_cells = False
    if calibration_metadata is not None:
        beam_flux = calibration_metadata.get("beam_flux")
        beam_exposure = calibration_metadata.get("beam_exposure")
        beamsize_mm = calibration_metadata.get("beamsize_mm")
        N_cells = calibration_metadata.get("N_cells")
        calibration_adjusted_for_n_cells = calibration_metadata.get("calibration_adjusted_for_n_cells", False)
        # SCALE-008: Derive baseline from spot_scale_override to apply the mapping adjustment.
        # When N_cells is suppressed, mapping multiplies spot_scale_override by adjustment_factor
        # to compensate for the amplitude collapse. Stage A must apply this adjusted scale.
        if "spot_scale_override" in calibration_metadata:
            spot_scale_override = calibration_metadata.get("spot_scale_override")
            try:
                sqrt_spot_scale = float(np.sqrt(spot_scale_override))
                log_scale_baseline = float(np.log(sqrt_spot_scale))
            except (TypeError, ValueError):
                sqrt_spot_scale = None
                log_scale_baseline = None
    elif log_scale_baseline is None:
        # Propagate caller-provided baseline even when calibration metadata is absent
        log_scale_baseline = None

    beam_config = create_beam_config(beam, flux=beam_flux, beamsize_mm=beamsize_mm, exposure=beam_exposure)
    hkl_grid_device = hkl_grid.to(device=device, dtype=dtype)
    # Gate N_cells application per TOOLING-VIS-001 Phase D.C and SCALE-008
    # Apply only when N_cells is present AND apply_calibration_n_cells is True
    apply_n_cells = (N_cells is not None) and apply_calibration_n_cells
    crystal_config, _ = create_crystal_config(crystal, None, N_cells=N_cells, apply_n_cells=apply_n_cells)

    base_crystal_model = Crystal(crystal_config, beam_config=beam_config, device=device, dtype=dtype)
    base_crystal_model.interpolate = enable_hkl_interpolation
    base_crystal_model.hkl_data = hkl_grid_device
    base_crystal_model.hkl_metadata = hkl_metadata

    for pid in range(n_panels):
        panel = detector[pid]

        # Capture baseline distance for Stage C retargeting (PERF-WARM-SIM-001)
        baseline_distance_mm.append(panel.get_directed_distance())

        # Create detector config
        detector_config = create_detector_config(
            panel=panel,
            beam=beam,
            trusted_mask=trusted_mask[pid]
        )

        # Convert mask_array to torch.Tensor if it's a numpy array
        # Per dbex/nanobrag_bridge.py:998-1004, nanobrag_torch Simulator
        # expects torch.Tensor for mask_array
        mask_array = detector_config.mask_array
        if mask_array is not None and not isinstance(mask_array, torch.Tensor):
            mask_array = torch.tensor(mask_array, dtype=torch.float32, device=device)
            detector_config.mask_array = mask_array
        elif mask_array is not None and (mask_array.device != device or mask_array.dtype != torch.float32):
            mask_array = mask_array.to(device=device, dtype=torch.float32)
            detector_config.mask_array = mask_array

        # Instantiate Detector model
        detector_model = Detector(detector_config, device=device, dtype=dtype)

        detector_configs.append(detector_config)
        detector_models.append(detector_model)

        simulator = Simulator(
            detector=detector_model,
            crystal=base_crystal_model,
            beam_config=beam_config,
            device=device,
            dtype=dtype,
        )
        simulators.append(simulator)

        # Tensorize trusted mask (bool) for reuse in loss masks
        mask_bool = torch.as_tensor(trusted_mask[pid], dtype=torch.bool, device=device)
        trusted_masks_t_list.append(mask_bool)

    if enable_roi_mode and panel_slices:
        for roi_index, (pid, bbox) in enumerate(panel_slices):
            x0, x1, y0, y1 = bbox
            panel = detector[int(pid)]
            detector_config = create_detector_config(
                panel=panel,
                beam=beam,
                trusted_mask=trusted_mask[int(pid)],
                roi_bbox=bbox,
            )
            mask_array = detector_config.mask_array
            if mask_array is not None and not isinstance(mask_array, torch.Tensor):
                mask_array = torch.tensor(mask_array, dtype=torch.float32, device=device)
                detector_config.mask_array = mask_array
            elif mask_array is not None and (mask_array.device != device or mask_array.dtype != torch.float32):
                mask_array = mask_array.to(device=device, dtype=torch.float32)
                detector_config.mask_array = mask_array

            detector_model = Detector(detector_config, device=device, dtype=dtype)
            simulator = Simulator(
                detector=detector_model,
                crystal=base_crystal_model,
                beam_config=beam_config,
                device=device,
                dtype=dtype,
            )
            roi_entries.append(
                StageAROIEntry(
                    roi_index=roi_index,
                    panel_id=int(pid),
                    bbox=tuple(int(v) for v in bbox),
                    slow_slice=slice(int(y0), int(y1)),
                    fast_slice=slice(int(x0), int(x1)),
                    detector_model=detector_model,
                    simulator=simulator,
                )
            )

    trusted_masks_t = torch.stack(trusted_masks_t_list, dim=0) if trusted_masks_t_list else None

    # Build roi_panel_map for Stage C retargeting (PERF-WARM-013)
    roi_panel_map = {entry.roi_index: entry.panel_id for entry in roi_entries} if roi_entries else {}

    return StageAContext(
        detector_configs=detector_configs,
        detector_models=detector_models,
        simulators=simulators,
        roi_entries=roi_entries if roi_entries else None,
        beam_config=beam_config,
        trusted_masks_t=trusted_masks_t,
        baseline_distance_mm=baseline_distance_mm,
        roi_panel_map=roi_panel_map,
        hkl_grid=hkl_grid_device,
        hkl_metadata=hkl_metadata,
        device=device,
        dtype=dtype,
        n_panels=n_panels,
        roi_count=len(roi_entries),
        enable_hkl_interpolation=enable_hkl_interpolation,
        calibration_metadata=calibration_metadata,
        log_scale_baseline=log_scale_baseline,
        spot_scale_override=spot_scale_override,
        sqrt_spot_scale=sqrt_spot_scale,
    )


# ============================================================================
# Stage A Utility Functions
# ============================================================================


def _get_sigma_floor_sq_tensor(
    cache: Dict[Tuple[str, torch.dtype], torch.Tensor],
    device: torch.device,
    dtype: torch.dtype,
    sigma_floor_value: float,
) -> torch.Tensor:
    """Cache sigma_floor^2 scalars per (device, dtype) to avoid re-allocation."""
    key = (str(device), dtype)
    tensor = cache.get(key)
    if tensor is None:
        tensor = torch.tensor(sigma_floor_value ** 2, device=device, dtype=dtype)
        cache[key] = tensor
    return tensor


def _clamp_log_cell_deltas(
    log_cell_a_delta: torch.Tensor,
    log_cell_b_delta: torch.Tensor,
    log_cell_c_delta: torch.Tensor,
    max_delta: float,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Clamp log-cell deltas to keep derived unit-cell lengths finite/positive."""
    return (
        torch.clamp(log_cell_a_delta, min=-max_delta, max=max_delta),
        torch.clamp(log_cell_b_delta, min=-max_delta, max=max_delta),
        torch.clamp(log_cell_c_delta, min=-max_delta, max=max_delta),
    )


# ============================================================================
# Stage A Parameter Setup, Closure Building, and LBFGS Execution
# ============================================================================


# Import loss function from physics module
from dbex.physics.loss import _compute_variance_weighted_loss


def _build_stage_a_params(
    crystal,
    detector,
    inputs,
    config: 'RefinementConfig',
    device,
    dtype,
    hkl_grid,
    hkl_metadata,
    sigma_floor_sq_cache,
    baseline_crystal,
    baseline_detector,
    beam
):
    """
    Build trainable parameters for Stage A LBFGS refinement.

    Supports 3 parameterization modes:
    - cell + misset (default)
    - U-matrix (config.use_u_matrix_parameterization=True)
    - incremental UB (config.use_incremental_ub=True)

    Returns:
        Dict with keys: params, param_values, telemetry_state, stage_a_context, optimizer
    """
    # Initialize refinement parameters
    # Stage A expansion: global scale + full crystal (a/b/c logs, alpha/beta/gamma bounded, orientation)

    # 1. log_scale: global intensity scale
    # When calibration_metadata is present (TOOLING-VIS-001 Phase D.C, DB-AT-027):
    #   - log_scale_baseline = log(sqrt(spot_scale_override)), recorded in telemetry
    #   - log_scale starts at 0.0 (neutral delta), will be clamped to ±log_scale_max_delta
    #   - Final scale applied = exp(log_scale_baseline + clamped_delta)
    # Otherwise:
    #   - Warm-start from global_scale_hint when available (per spec-db-workflow.md:20-40, REFINE-001)
    #   - log_scale is the direct learnable parameter (no baseline separation)
    log_scale_baseline = None
    log_scale_baseline_source = None
    spot_scale_override_adjustment_factor = None
    initial_log_scale = 0.0  # fallback: scale=1.0 (updated below when warm cache present)

    # Priority 1: Mapping-aware override when calibration was adjusted for N_cells
    # (SCALE-008 / TOOLING-VIS-001 Phase E — prevent double-application of spot_scale when mapping already corrected it)
    # Priority 1 (legacy): When calibration was adjusted for N_cells, use global_scale_hint if available.
    # SCALE-008: Skip this if log_scale_baseline was already set by warm cache context, which
    # already derives the correct baseline from spot_scale_override.
    if log_scale_baseline is None and config.calibration_metadata is not None:
        calibration_adjusted = config.calibration_metadata.get("calibration_adjusted_for_n_cells", False)
        if calibration_adjusted and inputs.global_scale_hint is not None and inputs.global_scale_hint > 1.0:
            # global_scale_hint is a RELATIVE scale (typically 1.0), not an absolute intensity scale.
            # Only use it if it's significantly different from 1.0 (otherwise defer to Priority 2)
            try:
                log_scale_baseline = float(np.log(inputs.global_scale_hint))
                log_scale_baseline_source = "mapping_global_scale_hint"
                # Record the adjustment factor so telemetry shows the mapping correction was honored
                adjustment_factor_raw = config.calibration_metadata.get("spot_scale_override_adjustment_factor")
                if adjustment_factor_raw is not None:
                    spot_scale_override_adjustment_factor = float(adjustment_factor_raw)
            except (TypeError, ValueError, OverflowError):
                # Fallback to standard path if conversion fails
                pass

    # Priority 2: Standard calibration path (when calibration not adjusted for N_cells)
    if log_scale_baseline is None and config.calibration_metadata is not None:
        spot_scale_override = config.calibration_metadata.get("spot_scale_override")
        if spot_scale_override is not None:
            try:
                sqrt_spot_scale = float(np.sqrt(spot_scale_override))
                log_scale_baseline = float(np.log(sqrt_spot_scale))
                log_scale_baseline_source = "spot_scale_override_sqrt"
            except (TypeError, ValueError):
                log_scale_baseline = None

    config.log_scale_baseline = log_scale_baseline
    log_scale = torch.tensor(initial_log_scale, device=device, dtype=dtype, requires_grad=True)

    # 2. Unit cell length deltas (log parameterization for positivity)
    log_cell_a_delta = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    log_cell_b_delta = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    log_cell_c_delta = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)

    # 3. Unit cell angle deltas (unbounded, will be mapped via tanh to bounded range)
    # angles in degrees: alpha, beta, gamma typically near 90° for orthorhombic/cubic
    # Use tanh(x) * max_delta to bound perturbations (e.g., ±10°)
    angle_alpha_raw = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    angle_beta_raw = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    angle_gamma_raw = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)

    # 4. Orientation perturbation (3-vector that will be converted to unit quaternion)
    # Initialize to small values near identity rotation
    orientation_vec = torch.zeros(3, device=device, dtype=dtype, requires_grad=True)

    # TORCH-GEOMETRY-PARITY-002 Phase B4: U-matrix quaternion parameterization (opt-in)
    q_params = None
    B_ideal_reciprocal_torch = None
    if config.use_u_matrix_parameterization:
        from dbex.nanobrag_bridge import (
            derive_u_matrix_from_mosflm_a_star,
            matrix_to_quaternion,
        )
        # Extract MOSFLM A* from the crystal (mapping zero point)
        A_star_np = np.array(crystal.get_A()).reshape(3, 3)
        cell_params = crystal.get_unit_cell().parameters()

        # Derive U-matrix from mapping MOSFLM A* (no SO(3) projection)
        # Get BOTH U and B_ideal from same TorchCrystal computation (CONVERGENCE-001 bugfix)
        # CRITICAL FIX (Phase B Deep Diagnostic): Use the MOSFLM-derived B_ideal, do NOT recompute from cctbx
        U_0, B_ideal_reciprocal_np = derive_u_matrix_from_mosflm_a_star(A_star_np, cell_params)

        # Convert to quaternion
        q_0 = matrix_to_quaternion(torch.tensor(U_0, dtype=torch.float64))

        # Initialize trainable quaternion params (float64 for precision)
        q_params = q_0.clone().to(device=device, dtype=dtype).requires_grad_(True)

        # Use the MOSFLM-derived B_ideal (ensures U @ B_ideal == A*_MOSFLM at initialization)
        # Prior bug: recomputed B_ideal from cctbx cell, causing catastrophic chi²=1.425B divergence
        # Root cause: cctbx cell.parameters() → TorchCrystal → compute_cell_tensors() produces
        # DIFFERENT B_ideal than MOSFLM A* decomposition, breaking U @ B_ideal = A*_MOSFLM invariant
        B_ideal_reciprocal_torch = torch.tensor(B_ideal_reciprocal_np, device=device, dtype=dtype)

    # TORCH-GEOMETRY-UB-REALIGN-001 Phase B3: Incremental UB parameterization (opt-in)
    # Trainable parameters for incremental UB path:
    #   - q_delta: quaternion delta [w,x,y,z] (4 params), identity = [1,0,0,0]
    #   - delta_log_a/b/c: log-perturbations for cell lengths (3 params), zero = no change
    #   - delta_alpha/beta/gamma: angle deltas in degrees (3 params), zero = no change
    #   - log_scale: global intensity scale (1 param, shared with default path)
    # Total: 10 DOF (4 orientation + 3 lengths + 3 angles)
    q_delta = None
    delta_log_a = None
    delta_log_b = None
    delta_log_c = None
    delta_alpha = None
    delta_beta = None
    delta_gamma = None
    U_baseline = None
    cell_baseline = None
    if config.use_incremental_ub:
        # Extract baseline crystal state from dxtbx
        U_baseline = torch.tensor(
            np.array(crystal.get_U()).reshape(3, 3),
            dtype=dtype,
            device=device
        )
        unit_cell = crystal.get_unit_cell()
        cell_baseline = torch.tensor(
            [unit_cell.parameters()[i] for i in range(6)],  # [a, b, c, α, β, γ]
            dtype=dtype,
            device=device
        )

        # Initialize quaternion delta to identity [w=1, x=0, y=0, z=0]
        q_delta = torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=dtype, device=device, requires_grad=True)

        # Initialize cell perturbations to zero (no change at params=0)
        delta_log_a = torch.tensor(0.0, dtype=dtype, device=device, requires_grad=True)
        delta_log_b = torch.tensor(0.0, dtype=dtype, device=device, requires_grad=True)
        delta_log_c = torch.tensor(0.0, dtype=dtype, device=device, requires_grad=True)
        delta_alpha = torch.tensor(0.0, dtype=dtype, device=device, requires_grad=True)
        delta_beta = torch.tensor(0.0, dtype=dtype, device=device, requires_grad=True)
        delta_gamma = torch.tensor(0.0, dtype=dtype, device=device, requires_grad=True)

    params = [
        log_scale,
        log_cell_a_delta, log_cell_b_delta, log_cell_c_delta,
        angle_alpha_raw, angle_beta_raw, angle_gamma_raw,
        orientation_vec
    ]

    # Add q_params to optimizer if U-matrix mode is enabled
    if config.use_u_matrix_parameterization:
        params.append(q_params)

    # Add incremental UB params to optimizer if incremental UB mode is enabled
    if config.use_incremental_ub:
        params = [
            log_scale,
            q_delta,
            delta_log_a, delta_log_b, delta_log_c,
            delta_alpha, delta_beta, delta_gamma
        ]

    # Setup LBFGS optimizer
    optimizer = torch.optim.LBFGS(
        params,
        history_size=config.history_size,
        max_iter=config.max_iter,
        tolerance_grad=config.tolerance_grad,
        tolerance_change=config.tolerance_change,
        line_search_fn="strong_wolfe"  # Enable strong Wolfe line search for stability
    )

    # Telemetry accumulators
    loss_trace_sample = []  # Deprecated: chi_squared only (PHYSICS-LOSS-001)
    loss_trace_full = []  # Deprecated: chi_squared only (PHYSICS-LOSS-001)
    best_loss_full = (float('inf'), -1)  # Deprecated: chi_squared only (PHYSICS-LOSS-001)
    best_params_snapshot = None
    iteration_count = [0]  # Mutable counter for closure

    # PHYSICS-LOSS-001: Dual metric tracking (chi_squared + masked_mse)
    chi_squared_trace_sample = []
    chi_squared_trace_full = []
    chi_squared_best = (float('inf'), -1)
    masked_mse_trace_sample = []
    masked_mse_trace_full = []
    masked_mse_best = (float('inf'), -1)

    # Perf counters (PERF-WARM-SIM-001)
    perf_closure_evals = [0]  # Total closure calls
    perf_validation_runs = [0]  # Full validation runs
    perf_forward_times_ms = []  # Per-closure forward pass timings

    # PHYSICS-LOSS-002: Variance floor clamp statistics
    variance_floor_clamped_pixels = [0]  # Total pixels where floor engaged
    variance_floor_masked_pixels = [0]  # Total masked pixels evaluated
    sigma_floor_sq_tensor = _get_sigma_floor_sq_tensor(
        sigma_floor_sq_cache, device, dtype, config.sigma_floor_value
    )

    # Deterministic ROI/Panel sampling seeds
    np.random.seed(42)  # Fixed seed for deterministic behavior
    n_panels = len(detector)
    baseline_detector_distances = None
    if baseline_detector is not None:
        if len(baseline_detector) != n_panels:
            raise ValueError(
                "baseline_detector must have the same number of panels as detector"
            )
        baseline_detector_distances = [
            baseline_detector[pid].get_directed_distance() for pid in range(n_panels)
        ]
    panel_shape = inputs.target.shape[1:]  # (slow, fast)
    panel_slices = inputs.panel_slices
    canonical_roi_count = len(panel_slices)
    if baseline_detector_distances is not None:
        canonical_detector_distances = list(baseline_detector_distances)
    else:
        canonical_detector_distances = [
            detector[pid].get_directed_distance() for pid in range(n_panels)
        ]
    canonical_baseline = {
        "stage_label": "A",
        "chi_squared": None,
        "iteration": None,
        "roi_count": canonical_roi_count,
        "detector_distances_mm": canonical_detector_distances,
    }

    # Sample panels (~15%) for Stage B reuse + fallback
    sampled_panel_ids = sorted(
        np.random.choice(
            n_panels,
            size=max(1, int(n_panels * config.roi_sample_fraction)),
            replace=False,
        ).tolist()
    )

    # Stage A ROI sampling (panel_slices-defined) with fallback to panel sampling
    # ARCH-REFINE-001, REFINE-010: Auto-disable ROI mode when canonical_roi_count ≤ threshold
    # to ensure sufficient signal for convergence (refGeom_small: 29 ROIs → 0% improvement with ROI mode, 57.4% with panel mode)
    use_stage_a_roi_mode = bool(
        config.enable_stage_a_roi_mode
        and canonical_roi_count > config.stage_a_min_roi_for_roi_mode
        and (config.enable_stage_a_warm_cache or config.allow_cold_stage_a_roi_mode)
    )
    stage_a_roi_label = "roi" if use_stage_a_roi_mode else "panel"
    stage_a_total_work_items = canonical_roi_count if use_stage_a_roi_mode else n_panels
    if use_stage_a_roi_mode:
        roi_sample_size = max(1, int(stage_a_total_work_items * config.roi_sample_fraction))
        roi_sample_size = min(stage_a_total_work_items, roi_sample_size)
        sampled_stage_a_indices = sorted(
            np.random.choice(stage_a_total_work_items, size=roi_sample_size, replace=False).tolist()
        )
    else:
        sampled_stage_a_indices = list(sampled_panel_ids)
    full_stage_a_indices = list(range(stage_a_total_work_items))

    # Build Stage A context conditionally (PERF-WARM-SIM-001)
    # When warm cache is enabled (default), prebuild detector models and tensorize masks once
    # for 2-5× speedup. When disabled (benchmarking), rebuild inside compute_loss for cold baseline.
    stage_a_ctx = None
    if config.enable_stage_a_warm_cache:
        stage_a_ctx = _build_stage_a_context(
            detector=detector,
            beam=beam,
            crystal=crystal,
            trusted_mask=inputs.trusted_mask,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            enable_hkl_interpolation=config.enable_hkl_interpolation,
            device=device,
            dtype=dtype,
            panel_slices=panel_slices,
            enable_roi_mode=use_stage_a_roi_mode,
            calibration_metadata=config.calibration_metadata,
            log_scale_baseline=log_scale_baseline,
            apply_calibration_n_cells=config.apply_calibration_n_cells,
        )

    # Priority 1 (revised): When calibration was adjusted for N_cells, derive Stage A baseline
    # from warmed simulator output instead of using global_scale_hint directly (TOOLING-VIS-001 Phase E).
    # This ensures the baseline matches what the Stage A model actually produces at the mapping zero point.
    target_mean_masked = None
    model_mean_masked = None
    if stage_a_ctx is not None and config.calibration_metadata is not None:
        calibration_adjusted = config.calibration_metadata.get("calibration_adjusted_for_n_cells", False)
        if calibration_adjusted:
            # Tensorize inputs.target and inputs.loss_mask onto stage_a_ctx.device for device-neutral computation
            # (TOOLING-VIS-001 Phase D.E — keep dtype/device agnostic so CUDA runs remain supported)
            target_t = None
            loss_mask_t = None
            if inputs.target is not None and inputs.loss_mask is not None:
                try:
                    target_t = torch.as_tensor(inputs.target, device=device, dtype=dtype)
                    loss_mask_t = torch.as_tensor(inputs.loss_mask, device=device, dtype=torch.bool)
                except Exception:
                    # Device mismatch or conversion error; fall back to numpy path
                    target_t = None
                    loss_mask_t = None

            # Compute target mean from MASKED pixels (use actual target intensity, not global_scale_hint)
            # global_scale_hint is a relative scale factor, not an absolute intensity
            if target_t is not None and loss_mask_t is not None:
                try:
                    target_mean_masked = float(target_t[loss_mask_t].mean().item())
                except Exception:
                    # Fallback to numpy if tensor indexing fails
                    target_mean_masked = float(inputs.target[inputs.loss_mask].mean())

            # Compute model mean from Stage A warmed simulators at delta=0
            # Build zero-iteration Bragg stack from warmed simulators
            try:
                with torch.no_grad():
                    bragg_samples = [simulator.run() for simulator in stage_a_ctx.simulators]
                    bragg_stack = torch.stack(bragg_samples, dim=0)
                    # Apply spot_scale_override per SCALE-002 (sqrt factor)
                    # When calibration was adjusted for N_cells, spot_scale_override contains
                    # the adjustment-factor-corrected value, so applying it here gives the
                    # mapping-aligned model intensity (TOOLING-VIS-001 Phase D.E, SCALE-008)
                    spot_scale_override = config.calibration_metadata.get("spot_scale_override", 1.0)
                    sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override > 0 else 1.0
                    bragg_stack_scaled = bragg_stack * sqrt_spot_scale
                    # Compute masked mean to match target_mean computation (use tensorized mask)
                    if loss_mask_t is not None:
                        model_mean_masked = float(bragg_stack_scaled[loss_mask_t].mean().item())
                    else:
                        # Fallback to numpy mask if tensorization failed
                        model_mean_masked = float(bragg_stack_scaled[inputs.loss_mask].mean().item())
            except Exception:
                # Fall back to previous behavior if simulator forward fails
                model_mean_masked = None

            # Compute log_scale_baseline from ratio (guard against invalid values)
            if target_mean_masked is not None and target_mean_masked > 0 and model_mean_masked is not None and model_mean_masked > 0:
                try:
                    log_scale_baseline = float(np.log(target_mean_masked / model_mean_masked))
                    log_scale_baseline_source = "mapping_global_scale_hint"
                    # Update stage_a_ctx so engine + inline callers share the same baseline telemetry
                    stage_a_ctx.log_scale_baseline = log_scale_baseline
                    # Record the adjustment factor so telemetry shows the mapping correction was honored
                    adjustment_factor_raw = config.calibration_metadata.get("spot_scale_override_adjustment_factor")
                    if adjustment_factor_raw is not None:
                        spot_scale_override_adjustment_factor = float(adjustment_factor_raw)
                except (TypeError, ValueError, OverflowError):
                    # Fallback: keep the baseline from Priority 2 or None
                    pass

    # Heuristic scale warm-start (ADU mode): estimate model mean at delta=0 and
    # initialize log_scale to match the observed target mean. Skip when no cache.
    if log_scale_baseline is None and stage_a_ctx is not None:
        target_hint = inputs.global_scale_hint
        if target_hint is None and inputs.target is not None:
            target_hint = float(inputs.target[inputs.loss_mask].mean())
        model_mean = None
        try:
            with torch.no_grad():
                bragg_samples = [simulator.run() for simulator in stage_a_ctx.simulators]
                bragg_stack = torch.stack(bragg_samples, dim=0)
                model_mean = float(bragg_stack.mean().item())
        except Exception:
            model_mean = None
        if target_hint is not None and target_hint > 0 and model_mean is not None and model_mean > 0:
            scaled_log_scale = float(np.log(target_hint / model_mean))
            max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
            scaled_log_scale = float(np.clip(scaled_log_scale, -max_delta_uncal, max_delta_uncal))
            initial_log_scale = scaled_log_scale
            log_scale = torch.tensor(initial_log_scale, device=device, dtype=dtype, requires_grad=True)
            params[0] = log_scale

    # Telemetry step counter (TORCH-GEOMETRY-CONVERGENCE-001 Phase A1)
    # Mutable list for closure capture; increments after each closure call
    telemetry_step_counter = [0]

    # Lifecycle tracking for U-matrix and A* reconstruction (TORCH-GEOMETRY-CONVERGENCE-001 Phase B4)
    u_matrix_lifecycle_log = []  # Track U checksum per closure call
    a_star_lifecycle_log = []    # Track A* reconstruction per closure call

    # Build param_values dict for return
    param_values = {
        'initial_log_scale': initial_log_scale,  # Store initial value for telemetry
        'log_scale_baseline': log_scale_baseline,  # Baseline from calibration (None if uncalibrated)
        'log_scale_baseline_source': log_scale_baseline_source,  # Source of baseline (TOOLING-VIS-001 Phase E)
        'spot_scale_override_adjustment_factor': spot_scale_override_adjustment_factor,  # N_cells adjustment factor (TOOLING-VIS-001 Phase E)
        'target_mean_masked': target_mean_masked,  # Masked mean of target data (TOOLING-VIS-001 Phase D.E)
        'model_mean_masked': model_mean_masked,  # Masked mean of Stage A zero-iteration model (TOOLING-VIS-001 Phase D.E)
        'log_scale': log_scale,
        'log_cell_a_delta': log_cell_a_delta,
        'log_cell_b_delta': log_cell_b_delta,
        'log_cell_c_delta': log_cell_c_delta,
        'angle_alpha_raw': angle_alpha_raw,
        'angle_beta_raw': angle_beta_raw,
        'angle_gamma_raw': angle_gamma_raw,
        'orientation_vec': orientation_vec,
        'params': params,  # List of Parameter objects for optimizer
        'optimizer': optimizer,  # LBFGS optimizer for closure
        'q_params': q_params,
        'B_ideal_reciprocal_torch': B_ideal_reciprocal_torch,
        'q_delta': q_delta,
        'delta_log_a': delta_log_a,
        'delta_log_b': delta_log_b,
        'delta_log_c': delta_log_c,
        'delta_alpha': delta_alpha,
        'delta_beta': delta_beta,
        'delta_gamma': delta_gamma,
        'U_baseline': U_baseline,
        'cell_baseline': cell_baseline,
    }

    # Build telemetry_state dict
    telemetry_state = {
        'loss_trace_sample': loss_trace_sample,
        'loss_trace_full': loss_trace_full,
        'best_loss_full': best_loss_full,
        'best_params_snapshot': best_params_snapshot,
        'iteration_count': iteration_count,
        'chi_squared_trace_sample': chi_squared_trace_sample,
        'chi_squared_trace_full': chi_squared_trace_full,
        'chi_squared_best': chi_squared_best,
        'masked_mse_trace_sample': masked_mse_trace_sample,
        'masked_mse_trace_full': masked_mse_trace_full,
        'masked_mse_best': masked_mse_best,
        'perf_closure_evals': perf_closure_evals,
        'perf_validation_runs': perf_validation_runs,
        'perf_forward_times_ms': perf_forward_times_ms,
        'variance_floor_clamped_pixels': variance_floor_clamped_pixels,
        'variance_floor_masked_pixels': variance_floor_masked_pixels,
        'sigma_floor_sq_tensor': sigma_floor_sq_tensor,
        'telemetry_step_counter': telemetry_step_counter,
        'u_matrix_lifecycle_log': u_matrix_lifecycle_log,
        'a_star_lifecycle_log': a_star_lifecycle_log,
    }

    # Build stage_a_context dict
    stage_a_context = {
        'stage_a_ctx': stage_a_ctx,
        'sampled_panel_ids': sampled_panel_ids,
        'canonical_baseline': canonical_baseline,
        'use_stage_a_roi_mode': use_stage_a_roi_mode,
        'stage_a_roi_label': stage_a_roi_label,
        'stage_a_total_work_items': stage_a_total_work_items,
        'sampled_stage_a_indices': sampled_stage_a_indices,
        'full_stage_a_indices': full_stage_a_indices,
    }

    return {
        'params': params,
        'param_values': param_values,
        'telemetry_state': telemetry_state,
        'stage_a_context': stage_a_context,
        'optimizer': optimizer
    }


def _compute_panel_loss(
    panel_ids: List[int],
    stage_a_ctx: Optional['StageAContext'],
    detector,
    beam,
    crystal,
    crystal_overrides: Dict[str, Any],
    misset_deg_for_crystal: Optional[torch.Tensor],
    beam_config_for_run,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    config: 'RefinementConfig',
    log_scale_clamped: torch.Tensor,
    target_t: torch.Tensor,
    loss_mask_t: torch.Tensor,
    sigma_readout_t: torch.Tensor,
    sigma_floor_sq_tensor: torch.Tensor,
    device,
    dtype,
    trusted_mask_array: Optional[np.ndarray] = None,
    panel_diag: Optional[List[Dict]] = None,
) -> Tuple[torch.Tensor, torch.Tensor, int, int]:
    """
    Compute panel-mode loss over specified panel IDs (Stage A / Stage C shared helper).

    Implements the canonical panel-mode loss computation that Stage A uses when ROI mode
    is disabled or when force_panel_eval=True. Stage C calls this helper to ensure its
    initial/full validations measure the identical pixel population as Stage A's final
    validation (REFINE-007, PERF-WARM-SIM-001).

    Warm mode (stage_a_ctx present): Reuses cached simulators from Stage A context.
    Cold mode (stage_a_ctx is None): Instantiates detector/crystal/simulator per panel.

    Args:
        panel_ids: List of panel indices to evaluate
        stage_a_ctx: Optional StageAContext with cached simulators + trusted masks (warm mode)
        detector: dxtbx Detector object
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object (baseline, not perturbed)
        crystal_overrides: Dict with perturbed cell/orientation parameters
        misset_deg_for_crystal: Misset angles tensor (cell+misset mode) or None (U-matrix mode)
        beam_config_for_run: BeamConfig for simulation
        hkl_grid: Structure factor grid tensor
        hkl_metadata: HKL metadata dict
        config: RefinementConfig (enable_hkl_interpolation, etc.)
        log_scale_clamped: Clamped log-scale parameter
        target_t: Target intensities tensor [n_panels, slow, fast]
        loss_mask_t: Loss mask tensor [n_panels, slow, fast]
        sigma_readout_t: Readout noise tensor [n_panels, slow, fast]
        sigma_floor_sq_tensor: Variance floor tensor (scalar)
        device: torch device
        dtype: torch dtype
        trusted_mask_array: Optional numpy array of trusted masks (cold-path Stage A only; [n_panels, slow, fast])
        panel_diag: Optional list to collect per-panel diagnostics. When provided, appends
                   dicts with {panel_id, chi_squared, masked_pixels, mask_true_count,
                   target_sum, sigma_sum} for each panel before aggregating totals.
                   PERF-WARM-SIM-001 Phase D.4 instrumentation.

    Returns:
        Tuple of (chi_squared_loss, masked_mse_loss, masked_pixels, clamped_pixels)
    """
    from dbex.nanobrag_bridge import create_detector_config, create_crystal_config
    from dbex.physics.loss import _compute_variance_weighted_loss

    # PERF-WARM-SIM-001: When diagnostics are requested, compute per-panel metrics serially
    # so we can capture chi², mask, sigma, and target checksums before aggregating.
    # Otherwise, use the fast-path stacked evaluation.
    if panel_diag is not None:
        # Per-panel evaluation path for diagnostics
        total_chi_squared = torch.tensor(0.0, device=device, dtype=dtype)
        total_masked_mse = torch.tensor(0.0, device=device, dtype=dtype)
        total_masked_pixels = 0
        total_clamped_pixels = 0

        for pid in panel_ids:
            # Generate Bragg for this panel
            if stage_a_ctx is not None:
                simulator = stage_a_ctx.simulators[pid]
            else:
                # Cold path: build detector/crystal/simulator on the fly
                panel_trusted_mask = trusted_mask_array[pid] if trusted_mask_array is not None else None
                detector_config = create_detector_config(
                    panel=detector[pid],
                    beam=beam,
                    trusted_mask=panel_trusted_mask
                )
                if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                    detector_config.mask_array = torch.tensor(
                        detector_config.mask_array, dtype=torch.float32, device=device
                    )
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

                if beam_config_for_run is None:
                    from dbex.nanobrag_bridge import create_beam_config
                    beam_config_for_run = create_beam_config(beam)

                from nanobrag_torch.simulator import Simulator
                simulator = Simulator(
                    detector=detector_model,
                    crystal=crystal_model,
                    beam_config=beam_config_for_run,
                    device=device,
                    dtype=dtype
                )

            bragg_panel = simulator.run()
            bragg_scaled = bragg_panel * torch.exp(log_scale_clamped)

            # Extract panel-specific tensors
            target_panel = target_t[pid]
            mask_panel = loss_mask_t[pid]
            # REFINE-016: Apply trusted-mask gating when warm context is available
            if stage_a_ctx is not None and stage_a_ctx.trusted_masks_t is not None:
                trusted_panel = stage_a_ctx.trusted_masks_t[pid]
                mask_panel = torch.logical_and(mask_panel, trusted_panel)
            sigma_panel = sigma_readout_t[pid]

            # Compute per-panel loss (unsqueeze to match batch dimension)
            (
                panel_chi_squared,
                panel_masked_mse,
                panel_masked_pixels,
                panel_clamped_pixels,
            ) = _compute_variance_weighted_loss(
                bragg_scaled.unsqueeze(0),
                target_panel.unsqueeze(0),
                mask_panel.unsqueeze(0),
                sigma_panel.unsqueeze(0),
                sigma_floor_sq_tensor,
            )

            # Collect diagnostics
            panel_diag.append({
                'panel_id': int(pid),
                'chi_squared': float(panel_chi_squared.item()),
                'masked_pixels': int(panel_masked_pixels),
                'mask_true_count': int(mask_panel.sum().item()),
                'target_sum': float(target_panel.sum().item()),
                'sigma_sum': float(sigma_panel.sum().item()),
            })

            # Accumulate totals
            total_chi_squared += panel_chi_squared
            total_masked_mse += panel_masked_mse
            total_masked_pixels += panel_masked_pixels
            total_clamped_pixels += panel_clamped_pixels

        return total_chi_squared, total_masked_mse, total_masked_pixels, total_clamped_pixels

    else:
        # Fast-path: stacked evaluation when diagnostics not requested
        bragg_panels = []
        for pid in panel_ids:
            if stage_a_ctx is not None:
                simulator = stage_a_ctx.simulators[pid]
            else:
                # Cold path: build detector/crystal/simulator on the fly
                # ARCH-REFINE-001: This path should rarely execute when Stage C reuses Stage A context
                panel_trusted_mask = trusted_mask_array[pid] if trusted_mask_array is not None else None
                detector_config = create_detector_config(
                    panel=detector[pid],
                    beam=beam,
                    trusted_mask=panel_trusted_mask
                )
                if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                    detector_config.mask_array = torch.tensor(
                        detector_config.mask_array, dtype=torch.float32, device=device
                    )
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

                # Build BeamConfig if not provided (Stage C cold path)
                if beam_config_for_run is None:
                    from dbex.nanobrag_bridge import create_beam_config
                    beam_config_for_run = create_beam_config(beam)

                from nanobrag_torch.simulator import Simulator
                simulator = Simulator(
                    detector=detector_model,
                    crystal=crystal_model,
                    beam_config=beam_config_for_run,
                    device=device,
                    dtype=dtype
                )
            bragg_panels.append(simulator.run())

        bragg_stacked = torch.stack(bragg_panels, dim=0)
        bragg_scaled = bragg_stacked * torch.exp(log_scale_clamped)

        target_subset = target_t[panel_ids]
        mask_subset = loss_mask_t[panel_ids]
        # REFINE-016: Apply trusted-mask gating when warm context is available
        if stage_a_ctx is not None and stage_a_ctx.trusted_masks_t is not None:
            trusted_subset = stage_a_ctx.trusted_masks_t[panel_ids]
            mask_subset = torch.logical_and(mask_subset, trusted_subset)
        sigma_subset = sigma_readout_t[panel_ids]

        # Compute variance-weighted loss (spec-db-core.md §§57-68)
        (
            chi_squared_loss,
            masked_mse_loss,
            masked_pixels,
            clamped_pixels,
        ) = _compute_variance_weighted_loss(
            bragg_scaled,
            target_subset,
            mask_subset,
            sigma_subset,
            sigma_floor_sq_tensor,
        )

        return chi_squared_loss, masked_mse_loss, masked_pixels, clamped_pixels


def _build_stage_a_lbfgs_closure(
    # Parameters from helper 1 return dict
    param_values: Dict[str, Any],
    telemetry_state: Dict[str, Any],
    stage_a_context: Dict[str, Any],
    # Additional closure context (11 params) - ARCH-STAGE-CONTEXT-001: support both dict and dataclass
    crystal=None,
    detector=None,
    beam=None,
    inputs=None,
    hkl_grid: Optional[torch.Tensor] = None,
    hkl_metadata: Optional[Dict] = None,
    config: Optional['RefinementConfig'] = None,
    sigma_floor_sq_cache: Optional[Dict] = None,
    device=None,
    dtype=None,
    baseline_crystal=None,
    # ARCH-STAGE-CONTEXT-001 Phase A.1: new dataclass parameter (optional)
    shared_context: Optional['RefinementSharedContext'] = None,
) -> Tuple['Callable', 'Callable']:
    """
    Build LBFGS closure for Stage A refinement with nested compute_loss and closure functions.

    Captures lexical scope for ~30 nonlocal variables from param_values, telemetry_state, stage_a_context.
    Supports 3 parameterization modes: cell+misset, U-matrix, incremental UB.

    ARCH-STAGE-CONTEXT-001 Phase A.1: Supports both legacy dict-based calling (11 individual params)
    and new dataclass-based calling (shared_context parameter). If shared_context is provided,
    individual params are ignored.

    Args:
        param_values: Dict with trainable tensors (log_scale, log_cell_*_delta, angle_*_raw,
                     orientation_vec, q_params, delta_log_*, delta_alpha/beta/gamma, q_delta)
        telemetry_state: Dict with mutable telemetry accumulators (loss traces, perf counters,
                        variance floor stats, lifecycle logs)
        stage_a_context: Dict with ROI/panel sampling state, warm cache context
        crystal: dxtbx Crystal object (legacy path)
        detector: dxtbx Detector object (legacy path)
        beam: dxtbx Beam object (legacy path)
        inputs: RefinementInputs (target, loss_mask, panel_slices, trusted_mask) (legacy path)
        hkl_grid: Structure factor grid tensor (legacy path)
        hkl_metadata: HKL metadata dict (legacy path)
        config: RefinementConfig (use_u_matrix_parameterization, use_incremental_ub, telemetry_output_dir) (legacy path)
        sigma_floor_sq_cache: Optional precomputed variance floor tensor (legacy path)
        device: torch device (legacy path)
        dtype: torch dtype (legacy path)
        baseline_crystal: Optional baseline dxtbx Crystal for incremental UB mode (legacy path)
        shared_context: Optional RefinementSharedContext dataclass (new path, ARCH-STAGE-CONTEXT-001)

    Returns:
        Tuple of (compute_loss, closure) callables with captured lexical scope
    """
    # ARCH-STAGE-CONTEXT-001: Compatibility shim - accept either dataclass or individual params
    if shared_context is not None:
        # New dataclass path
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
    else:
        # Legacy dict path - validate that required params are provided
        if any(x is None for x in [crystal, detector, beam, inputs, hkl_grid, hkl_metadata, config, device, dtype]):
            raise ValueError(
                "When shared_context is not provided, all individual parameters "
                "(crystal, detector, beam, inputs, hkl_grid, hkl_metadata, config, device, dtype) "
                "must be explicitly passed. Per ARCH-STAGE-CONTEXT-001, prefer using shared_context."
            )
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

    # Unpack telemetry_state (mutable lists/dicts for closure capture)
    iteration_count = telemetry_state['iteration_count']
    loss_trace_sample = telemetry_state['loss_trace_sample']
    loss_trace_full = telemetry_state['loss_trace_full']
    best_loss_full = telemetry_state['best_loss_full']
    best_params_snapshot = telemetry_state['best_params_snapshot']
    chi_squared_trace_sample = telemetry_state['chi_squared_trace_sample']
    chi_squared_trace_full = telemetry_state['chi_squared_trace_full']
    chi_squared_best = telemetry_state['chi_squared_best']
    masked_mse_trace_sample = telemetry_state['masked_mse_trace_sample']
    masked_mse_trace_full = telemetry_state['masked_mse_trace_full']
    masked_mse_best = telemetry_state['masked_mse_best']
    perf_closure_evals = telemetry_state['perf_closure_evals']
    perf_validation_runs = telemetry_state['perf_validation_runs']
    perf_forward_times_ms = telemetry_state['perf_forward_times_ms']
    variance_floor_clamped_pixels = telemetry_state['variance_floor_clamped_pixels']
    variance_floor_masked_pixels = telemetry_state['variance_floor_masked_pixels']
    sigma_floor_sq_tensor = telemetry_state['sigma_floor_sq_tensor']
    telemetry_step_counter = telemetry_state['telemetry_step_counter']
    u_matrix_lifecycle_log = telemetry_state.get('u_matrix_lifecycle_log', [])
    a_star_lifecycle_log = telemetry_state.get('a_star_lifecycle_log', [])

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
        telemetry_state['panel_loss_diag'] = []  # Will collect baseline + final

    beam_config_kwargs: Dict[str, Any] = {}
    n_cells_override = None
    if getattr(config, "calibration_metadata", None) is not None:
        beam_config_kwargs = {
            "flux": config.calibration_metadata.get("beam_flux"),
            "beamsize_mm": config.calibration_metadata.get("beamsize_mm"),
            "exposure": config.calibration_metadata.get("beam_exposure"),
        }
        n_cells_override = config.calibration_metadata.get("N_cells")

    # Telemetry step counter (TORCH-GEOMETRY-CONVERGENCE-001 Phase A1)
    # Mutable list for closure capture; increments after each closure call
    # NOTE: Already unpacked from telemetry_state above, but keeping these lines
    # for compatibility with original source lines 1320-1326
    # telemetry_step_counter = [0]

    # Lifecycle tracking for U-matrix and A* reconstruction (TORCH-GEOMETRY-CONVERGENCE-001 Phase B4)
    # NOTE: Already unpacked from telemetry_state above
    # u_matrix_lifecycle_log = []  # Track U checksum per closure call
    # a_star_lifecycle_log = []    # Track A* reconstruction per closure call
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
        delta_bound = config.log_scale_max_delta if log_scale_baseline_value is not None else max_delta_uncal
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
                # docs/config_crosswalk.md “I_model” mapping and TODO‑PHYSICS for planned
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

            # Store collected diagnostics in telemetry_state
            if panel_diag_collector is not None:
                telemetry_state['panel_loss_diag'].extend(panel_diag_collector)
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

        # Increment closure evaluation counter (PERF-WARM-SIM-001)
        perf_closure_evals[0] += 1

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

        # Record loss (use chi_squared for optimizer feedback)
        loss_trace_sample.append(float(chi_squared_loss.item()))  # Deprecated legacy field
        # PHYSICS-LOSS-001: Record both metrics
        chi_squared_trace_sample.append(float(chi_squared_loss.item()))
        masked_mse_trace_sample.append(float(masked_mse_loss.item()))

        # Periodic full validation
        if iteration_count[0] % config.full_validation_interval == 0:
            perf_validation_runs[0] += 1  # PERF-WARM-SIM-001
            with torch.no_grad():
                # ARCH-REFINE-001: Use panel mode for periodic validations when force_panel_validation is True (REFINE-007)
                full_chi_squared, full_mse = compute_loss(full_stage_a_indices, is_full=True, force_panel_eval=force_panel_validation)
                loss_trace_full.append((iteration_count[0], float(full_chi_squared.item())))  # Deprecated legacy field
                # PHYSICS-LOSS-001: Record both metrics
                chi_squared_trace_full.append((iteration_count[0], float(full_chi_squared.item())))
                masked_mse_trace_full.append((iteration_count[0], float(full_mse.item())))

                # Update best snapshot
                nonlocal best_loss_full, best_params_snapshot, chi_squared_best, masked_mse_best
                # PHYSICS-LOSS-001: Track best for both metrics
                if full_chi_squared.item() < chi_squared_best[0]:
                    chi_squared_best = (float(full_chi_squared.item()), iteration_count[0])
                    best_loss_full = (float(full_chi_squared.item()), iteration_count[0])  # Deprecated legacy field
                    # Compute misset XYZ for snapshot (TORCH-REFINE-002)
                    max_orientation_deg = 3.0
                    bounded_orientation_vec_snap = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
                    quat_snap = vec_to_unit_quaternion(bounded_orientation_vec_snap)
                    misset_xyz_deg_snap = quaternion_to_xyz_euler(quat_snap)

                    best_params_snapshot = {
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
                # PHYSICS-LOSS-001: Track masked_mse best separately (informational only, not for rollback)
                if full_mse.item() < masked_mse_best[0]:
                    masked_mse_best = (float(full_mse.item()), iteration_count[0])

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



def _run_stage_a_lbfgs(
    compute_loss,  # Callable from helper 2
    closure,  # Callable from helper 2
    optimizer,  # torch.optim.LBFGS from helper 1
    params,  # List[Parameter] from helper 1
    telemetry_state: Dict[str, Any],  # From helper 1
    config: 'RefinementConfig',
    canonical_baseline: Dict[str, Any],  # From run_nanobrag_refinement
    full_stage_a_indices: List[int],  # From run_nanobrag_refinement
    log_scale,  # Parameter from helper 1
    log_cell_a_delta, log_cell_b_delta, log_cell_c_delta,  # Parameters from helper 1
    angle_alpha_raw, angle_beta_raw, angle_gamma_raw,  # Parameters from helper 1
    orientation_vec,  # Parameter from helper 1
    device,
    dtype,
    masked_pixel_reference: Optional[int] = None,
    force_panel_validation: bool = False,  # ARCH-REFINE-001, REFINE-007
) -> Tuple[str, str, Optional[float], Optional[float], Optional[Dict[str, Any]]]:
    """
    Execute Stage A LBFGS optimization and final validation.

    Args:
        force_panel_validation: If True, baseline/final/exception evaluations use panel mode
                               instead of ROI sampling (ARCH-REFINE-001, REFINE-007)

    Returns:
        Tuple of (status, message, final_chi_squared_value, final_masked_mse_value, best_params_snapshot)
        variance_floor_masked_pixels in telemetry uses masked_pixel_reference when provided to
        keep chi²-per-pixel denominators aligned with the loss mask.
    """
    # Unpack telemetry_state variables
    iteration_count = telemetry_state['iteration_count']
    loss_trace_full = telemetry_state['loss_trace_full']
    chi_squared_trace_full = telemetry_state['chi_squared_trace_full']
    chi_squared_best = telemetry_state['chi_squared_best']
    masked_mse_trace_full = telemetry_state['masked_mse_trace_full']
    masked_mse_best = telemetry_state['masked_mse_best']
    best_loss_full = telemetry_state['best_loss_full']
    perf_validation_runs = telemetry_state['perf_validation_runs']
    best_params_snapshot = telemetry_state.get('best_params_snapshot')

    # Run LBFGS optimization
    status = "ok"
    message = ""

    final_chi_squared_value: Optional[float] = None
    final_masked_mse_value: Optional[float] = None
    log_cell_max_delta = getattr(config, "log_cell_max_delta", 1.0)

    # ARCH-REFINE-001: Capture baseline evaluation BEFORE LBFGS runs
    # This ensures loss_trace_full, chi_squared_trace_full, and masked_mse_trace_full
    # always contain the Stage A baseline, which downstream stages (B/C) need to
    # validate improvements and seed their canonical snapshots.
    # REFINE-007: Use panel mode when force_panel_validation is True so Stage C sees consistent chi²
    perf_validation_runs[0] += 1  # PERF-WARM-SIM-001
    with torch.no_grad():
        baseline_chi_squared, baseline_mse = compute_loss(full_stage_a_indices, is_full=True, force_panel_eval=force_panel_validation)
        baseline_chi_squared_value = float(baseline_chi_squared.item())
        baseline_mse_value = float(baseline_mse.item())

        # Append baseline to traces (iteration 0)
        loss_trace_full.append((0, baseline_chi_squared_value))  # Deprecated legacy field
        chi_squared_trace_full.append((0, baseline_chi_squared_value))
        masked_mse_trace_full.append((0, baseline_mse_value))

        # Initialize best tracking with baseline
        best_loss_full = (baseline_chi_squared_value, 0)  # Deprecated legacy field
        chi_squared_best = (baseline_chi_squared_value, 0)
        masked_mse_best = (baseline_mse_value, 0)

        # Update telemetry state with baseline tracking
        telemetry_state['best_loss_full'] = best_loss_full
        telemetry_state['chi_squared_best'] = chi_squared_best
        telemetry_state['masked_mse_best'] = masked_mse_best

        # Update canonical baseline with initial chi-squared
        canonical_baseline["chi_squared"] = baseline_chi_squared_value
        canonical_baseline["iteration"] = 0

    try:
        optimizer.step(closure)

        # Final full validation
        # REFINE-007: Use panel mode when force_panel_validation is True
        perf_validation_runs[0] += 1  # PERF-WARM-SIM-001
        with torch.no_grad():
            final_chi_squared, final_mse = compute_loss(full_stage_a_indices, is_full=True, force_panel_eval=force_panel_validation)
            final_chi_squared_value = float(final_chi_squared.item())
            final_masked_mse_value = float(final_mse.item())
            loss_trace_full.append((iteration_count[0], final_chi_squared_value))  # Deprecated legacy field
            # PHYSICS-LOSS-001: Record both metrics
            chi_squared_trace_full.append((iteration_count[0], final_chi_squared_value))
            masked_mse_trace_full.append((iteration_count[0], final_masked_mse_value))

            if final_chi_squared_value < best_loss_full[0]:
                best_loss_full = (final_chi_squared_value, iteration_count[0])  # Deprecated legacy field
            # PHYSICS-LOSS-001: Track best for both metrics
            if final_chi_squared_value < chi_squared_best[0]:
                chi_squared_best = (final_chi_squared_value, iteration_count[0])
            if final_masked_mse_value < masked_mse_best[0]:
                masked_mse_best = (final_masked_mse_value, iteration_count[0])

            if final_chi_squared_value < best_loss_full[0]:
                # Compute misset XYZ for final snapshot (TORCH-REFINE-002)
                max_orientation_deg = 3.0
                bounded_orientation_vec_final = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
                quat_final = vec_to_unit_quaternion(bounded_orientation_vec_final)
                misset_xyz_deg_final = quaternion_to_xyz_euler(quat_final)
                log_cell_a_value = float(torch.clamp(log_cell_a_delta, min=-log_cell_max_delta, max=log_cell_max_delta).item())
                log_cell_b_value = float(torch.clamp(log_cell_b_delta, min=-log_cell_max_delta, max=log_cell_max_delta).item())
                log_cell_c_value = float(torch.clamp(log_cell_c_delta, min=-log_cell_max_delta, max=log_cell_max_delta).item())

                best_params_snapshot = {
                    'log_scale': float(log_scale.item()),
                    'log_cell_a_delta': log_cell_a_value,
                    'log_cell_b_delta': log_cell_b_value,
                    'log_cell_c_delta': log_cell_c_value,
                    'angle_alpha_raw': float(angle_alpha_raw.item()),
                    'angle_beta_raw': float(angle_beta_raw.item()),
                    'angle_gamma_raw': float(angle_gamma_raw.item()),
                    'orientation_vec': orientation_vec.detach().cpu().tolist(),
                    'misset_xyz_deg': misset_xyz_deg_final.detach().cpu().tolist()
                }
            if final_chi_squared_value is not None:
                canonical_baseline["chi_squared"] = final_chi_squared_value
                canonical_baseline["iteration"] = iteration_count[0]

        # Check convergence: did we achieve ≥0.2% improvement?
        if len(loss_trace_full) > 0:
            initial_loss = loss_trace_full[0][1]
            final_loss_val = loss_trace_full[-1][1]
            improvement = (initial_loss - final_loss_val) / initial_loss

            if improvement < config.min_loss_improvement:
                status = "early_stop"
                message = f"Improvement {improvement:.2%} < {config.min_loss_improvement:.2%} (Stage A gate calibrated per TORCH-REFINE-002D)"

    except Exception as e:
        status = "error"
        message = str(e)
        # Use best snapshot if available
        if best_params_snapshot is not None:
            log_scale.data = torch.tensor(best_params_snapshot['log_scale'], device=device, dtype=dtype)
            log_cell_a_delta.data = torch.tensor(best_params_snapshot['log_cell_a_delta'], device=device, dtype=dtype)
            log_cell_b_delta.data = torch.tensor(best_params_snapshot['log_cell_b_delta'], device=device, dtype=dtype)
            log_cell_c_delta.data = torch.tensor(best_params_snapshot['log_cell_c_delta'], device=device, dtype=dtype)
            angle_alpha_raw.data = torch.tensor(best_params_snapshot['angle_alpha_raw'], device=device, dtype=dtype)
            angle_beta_raw.data = torch.tensor(best_params_snapshot['angle_beta_raw'], device=device, dtype=dtype)
            angle_gamma_raw.data = torch.tensor(best_params_snapshot['angle_gamma_raw'], device=device, dtype=dtype)
            orientation_vec.data = torch.tensor(best_params_snapshot['orientation_vec'], device=device, dtype=dtype)
        else:
            # Fall back to neutral parameters to keep telemetry/reconstruction sane
            log_scale.data = torch.tensor(0.0, device=device, dtype=dtype)
            zero_cell = torch.tensor(0.0, device=device, dtype=dtype)
            log_cell_a_delta.data = zero_cell
            log_cell_b_delta.data = zero_cell
            log_cell_c_delta.data = zero_cell
            angle_alpha_raw.data = zero_cell
            angle_beta_raw.data = zero_cell
            angle_gamma_raw.data = zero_cell
            orientation_vec.data = torch.zeros_like(orientation_vec)

        # ARCH-REFINE-001: Ensure final evaluation is appended even on exception
        # This guarantees downstream stages always see at least baseline + final entries
        # REFINE-007: Use panel mode when force_panel_validation is True
        perf_validation_runs[0] += 1  # PERF-WARM-SIM-001
        with torch.no_grad():
            error_chi_squared, error_mse = compute_loss(full_stage_a_indices, is_full=True, force_panel_eval=force_panel_validation)
            final_chi_squared_value = float(error_chi_squared.item())
            final_masked_mse_value = float(error_mse.item())
            loss_trace_full.append((iteration_count[0], final_chi_squared_value))  # Deprecated legacy field
            chi_squared_trace_full.append((iteration_count[0], final_chi_squared_value))
            masked_mse_trace_full.append((iteration_count[0], final_masked_mse_value))

            # Update canonical baseline
            canonical_baseline["chi_squared"] = final_chi_squared_value
            canonical_baseline["iteration"] = iteration_count[0]

    if not chi_squared_trace_full:
        fallback_chi2 = final_chi_squared_value
        fallback_iter = iteration_count[0]
        if fallback_chi2 is None and chi_squared_best[0] < float('inf'):
            fallback_chi2 = chi_squared_best[0]
            fallback_iter = chi_squared_best[1]
        if fallback_chi2 is None and best_loss_full[0] < float('inf'):
            fallback_chi2 = best_loss_full[0]
            fallback_iter = best_loss_full[1]
        if fallback_chi2 is not None:
            chi_squared_trace_full.append((fallback_iter, fallback_chi2))
            if not loss_trace_full:
                loss_trace_full.append((fallback_iter, fallback_chi2))
            if fallback_chi2 < chi_squared_best[0]:
                chi_squared_best = (fallback_chi2, fallback_iter)

    if not masked_mse_trace_full:
        fallback_mse = final_masked_mse_value
        fallback_iter = iteration_count[0]
        if fallback_mse is None and masked_mse_best[0] < float('inf'):
            fallback_mse = masked_mse_best[0]
            fallback_iter = masked_mse_best[1]
        if fallback_mse is not None:
            masked_mse_trace_full.append((fallback_iter, fallback_mse))
            if fallback_mse < masked_mse_best[0]:
                masked_mse_best = (fallback_mse, fallback_iter)

    if canonical_baseline["chi_squared"] is None:
        if chi_squared_trace_full:
            last_iter, last_val = chi_squared_trace_full[-1]
            canonical_baseline["chi_squared"] = last_val
            canonical_baseline["iteration"] = last_iter
        elif chi_squared_best[0] < float('inf'):
            canonical_baseline["chi_squared"] = chi_squared_best[0]
            canonical_baseline["iteration"] = chi_squared_best[1]

    # Update telemetry_state (mutations visible to caller via dict reference)
    telemetry_state['loss_trace_full'] = loss_trace_full
    telemetry_state['chi_squared_trace_full'] = chi_squared_trace_full
    telemetry_state['chi_squared_best'] = chi_squared_best
    telemetry_state['masked_mse_trace_full'] = masked_mse_trace_full
    telemetry_state['masked_mse_best'] = masked_mse_best
    telemetry_state['best_loss_full'] = best_loss_full
    telemetry_state['best_params_snapshot'] = best_params_snapshot

    # Canonical_baseline mutations are visible via dict reference (no need to return)

    # PERF-WARM-SIM-001 Phase D.4: Write panel-loss diagnostics JSON if collected
    import os
    import json
    from pathlib import Path
    panel_diag_dir = os.environ.get('DBEX_STAGE_C_PANEL_DIAG_DIR')
    if panel_diag_dir and 'panel_loss_diag' in telemetry_state:
        diag_path = Path(panel_diag_dir)
        diag_path.mkdir(parents=True, exist_ok=True)
        diag_file = diag_path / 'stage_a_panel_diag.json'
        with open(diag_file, 'w') as f:
            json.dump({
                'stage': 'A',
                'panels': telemetry_state['panel_loss_diag'],
                'n_panels': len(set(p['panel_id'] for p in telemetry_state['panel_loss_diag'])) if telemetry_state['panel_loss_diag'] else 0,
            }, f, indent=2)

    return (status, message, final_chi_squared_value, final_masked_mse_value, best_params_snapshot)

