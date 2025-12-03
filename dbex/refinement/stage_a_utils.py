"""
Stage A utilities for cross-stage refinement support.

Provides general-purpose helpers extracted from Stage A implementation for reuse
across Stage B, Stage C, and reconstruction workflows.

Functions:
- Quaternion utilities: vec_to_unit_quaternion, quaternion_to_rotation_matrix, quaternion_to_xyz_euler
- Warm cache helpers: _retarget_stage_a_simulators, _build_stage_a_context, _get_sigma_floor_sq_tensor
- Loss/parameter helpers: _compute_panel_loss, _clamp_log_cell_deltas

References:
- ARCH-ENGINE-002 (Stage wrappers are canonical seams)
- ARCH-STAGE-CTX-001 (Typed contexts only)
- GRADIENT-004 (Device/dtype neutrality)
- PERF-WARM-016 (Warm cache performance optimization)
"""

import copy
import math
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np
import torch

if TYPE_CHECKING:
    from dbex.refinement.config import RefinementConfig

# ARCH-LAZY-IMPORTS-001 / ARCH-ENGINE-002: Module-scope dependencies
from nanobrag_torch.models.detector import Detector
from nanobrag_torch.models.crystal import Crystal
from nanobrag_torch.simulator import Simulator
from dbex.refinement.config_factories import (
    create_detector_config,
    create_beam_config,
    create_crystal_config,
)
from dbex.physics.loss import _compute_variance_weighted_loss


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
# Stage A Warm Cache Helpers
# ============================================================================


def _retarget_stage_a_simulators(stage_a_ctx: 'StageAContext', crystal_model) -> None:
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
    config: Optional['RefinementConfig'] = None,  # DIAG-NANOBRAGG-OVERSAMPLE-001
    debug_config: Optional[Dict[str, Any]] = None,  # DIAG-NANOBRAGG-OVERSAMPLE-001 Phase F
) -> 'StageAContext':
    """
    Prebuild Stage A detector models and tensorize masks/HKL once (PERF-WARM-SIM-001).

    This helper constructs all per-panel Detector models, tensorizes trusted masks,
    and transfers the HKL grid to the target device. The LBFGS closure then reuses
    these cached models and only updates Crystal parameter tensors per iteration,
    eliminating repeated construction overhead.

    Note (DIAG-NANOBRAGG-OVERSAMPLE-001 Phase F):
        The `debug_config` parameter enables optional HKL statistics collection for
        diagnostics. Production Stage A runs should leave this as None; only diagnostic
        scripts should enable it (e.g., {'collect_hkl_stats': True}).

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
        debug_config: Optional dict for diagnostic instrumentation (default None). When
            provided, forwarded to Simulator instantiations to enable optional telemetry
            (e.g., {'collect_hkl_stats': True} for HKL coverage probes). Production Stage A
            runs should leave this as None.

    Returns:
        StageAContext with prebuilt models and tensorized data
    """
    # Import here to avoid circular dependency
    from dbex.refinement.context import StageAContext, StageAROIEntry

    # Extract oversample from config or use default (DIAG-NANOBRAGG-OVERSAMPLE-001)
    oversample_value = 3  # Default fallback
    if config is not None:
        oversample_value = config.oversample

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
            trusted_mask=trusted_mask[pid],
            oversample=oversample_value,  # DIAG-NANOBRAGG-OVERSAMPLE-001
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
            debug_config=debug_config,  # DIAG-NANOBRAGG-OVERSAMPLE-001 Phase F
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
                oversample=oversample_value,  # DIAG-NANOBRAGG-OVERSAMPLE-001
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
                debug_config=debug_config,  # DIAG-NANOBRAGG-OVERSAMPLE-001 Phase F
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
    # Extract oversample from config or use default (DIAG-NANOBRAGG-OVERSAMPLE-001)
    oversample_value = 3
    if config is not None:
        oversample_value = config.oversample

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
                    trusted_mask=panel_trusted_mask,
                    oversample=oversample_value,  # DIAG-NANOBRAGG-OVERSAMPLE-001
                )
                if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                    detector_config.mask_array = torch.tensor(
                        detector_config.mask_array, dtype=torch.float32, device=device
                    )
                detector_model = Detector(detector_config, device=device, dtype=dtype)

                crystal_config, _ = create_crystal_config(
                    crystal,
                    None,
                    crystal_overrides=crystal_overrides,
                    misset_deg_override=misset_deg_for_crystal
                )
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
                    beam_config_for_run = create_beam_config(beam)

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
                    trusted_mask=panel_trusted_mask,
                    oversample=oversample_value,  # DIAG-NANOBRAGG-OVERSAMPLE-001
                )
                if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                    detector_config.mask_array = torch.tensor(
                        detector_config.mask_array, dtype=torch.float32, device=device
                    )
                detector_model = Detector(detector_config, device=device, dtype=dtype)

                crystal_config, _ = create_crystal_config(
                    crystal,
                    None,
                    crystal_overrides=crystal_overrides,
                    misset_deg_override=misset_deg_for_crystal
                )
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
                    beam_config_for_run = create_beam_config(beam)

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
