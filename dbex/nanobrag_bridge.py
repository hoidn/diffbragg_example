"""
Bridge module to prepare DataLoad outputs for nanobrag_torch simulator.

This module provides helpers to convert DIALS/simtbx data structures into
torch-compatible tensors aligned with spec-db-core.md contracts:
- [panel, slow, fast] ordering
- background-subtracted targets
- trusted mask polarity (True=include, 1=include in torch)
- per-panel slicing information

Config hydration functions map dxtbx geometry to nanobrag_torch configs per:
- docs/config_crosswalk.md
- docs/dxtbx_api.md
- docs/nanobrag_api.md
- docs/spec-db-core.md
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    import torch


# ============================================================================
# Import real nanobrag_torch config classes
# ============================================================================

try:
    from nanobrag_torch.config import (
        DetectorConfig,
        BeamConfig,
        CrystalConfig,
        DetectorConvention
    )
except ImportError as e:
    raise ImportError(
        "nanobrag_torch.config is required for bridge functionality. "
        "Please ensure nanobrag_torch is installed. "
        f"Import error: {e}"
    )


# ============================================================================
# Existing RefinementInputs and prepare_refinement_inputs
# ============================================================================


@dataclass
class RefinementInputs:
    """
    Prepared inputs for nanobrag_torch simulator following spec-db-core.md.

    Attributes:
        target: Background-subtracted pixel data in [panel, slow, fast] order
                (in photons if adu_per_photon was provided, else ADU)
        loss_mask: Boolean mask where loss should be computed, (background >= 0) & trusted
        panel_slices: List of (panel_id, bbox) tuples for per-panel ROIs
                     bbox format: (x0, x1, y0, y1) with exclusive upper bounds
        trusted_mask: Original trusted mask in [panel, slow, fast] order (True=include)
        target_representation: "photons" or "adu" indicating target units
        global_scale_hint: Optional scale hint for ADU mode (mean(target)/mean(sim) estimate)
    """
    target: np.ndarray  # [panel, slow, fast] float, background-subtracted
    loss_mask: np.ndarray  # [panel, slow, fast] bool, (background >= 0) & trusted
    panel_slices: List[Tuple[int, Tuple[int, int, int, int]]]  # [(pid, (x0,x1,y0,y1))]
    trusted_mask: np.ndarray  # [panel, slow, fast] bool, True=include
    target_representation: str = "adu"  # "adu" or "photons"
    global_scale_hint: Optional[float] = None  # For ADU mode initialization


def prepare_refinement_inputs(
    data: np.ndarray,
    background_image: np.ndarray,
    trusted_mask: np.ndarray,
    bbox: np.ndarray,
    pids: np.ndarray,
    detector,
    adu_per_photon: Optional[float] = None
) -> RefinementInputs:
    """
    Prepare background-subtracted targets, loss masks, and panel slices for torch simulator.

    Implements spec-db-core.md contracts:
    - Array ordering: [panel, slow, fast] (spec-db-core.md:20)
    - Loss mask: (background >= 0) ∧ trusted_mask (spec-db-core.md:55)
    - Zeroing invalid pixels where loss_mask is False
    - ROI bbox semantics: (x0, x1, y0, y1) with exclusive upper bounds (spec-db-core.md:22)
    - ADU vs photon calibration policy (spec-db-workflow.md:20, ADR-02)

    Guards:
    - Pixel pitch must be square (config_crosswalk.md:30)
    - Trusted mask polarity must be True=include (spec-db-core.md:29)
    - adu_per_photon must be strictly positive if provided (spec-db-workflow.md:20)

    Args:
        data: Raw pixel data [panel, slow, fast] in ADU
        background_image: Background estimate [panel, slow, fast], -1 outside ROIs
        trusted_mask: Per-panel mask tuple or array, True=include
        bbox: ROI bounding boxes, shape (n_roi, 4) as (x0, x1, y0, y1)
        pids: Panel IDs for each ROI, shape (n_roi,)
        detector: dxtbx Detector object for pixel pitch validation
        adu_per_photon: Optional calibration factor to convert ADU to photons (must be >0)

    Returns:
        RefinementInputs with background-subtracted target (ADU or photons), loss mask,
        panel slices, representation metadata, and global_scale_hint for ADU mode

    Raises:
        ValueError: If pixel pitch is not square, mask polarity is inverted,
                   or adu_per_photon is invalid (<=0)
    """
    # Guard: validate adu_per_photon is strictly positive if provided
    if adu_per_photon is not None and adu_per_photon <= 0:
        raise ValueError(
            f"adu_per_photon must be strictly positive (>0), got {adu_per_photon}. "
            f"Per spec-db-workflow.md:20, calibration factor must be positive to convert ADU to photons."
        )

    # Guard: validate pixel pitch is square for all panels
    for panel_id, panel in enumerate(detector):
        px_fast, px_slow = panel.get_pixel_size()
        if abs(px_fast - px_slow) > 1e-9:
            raise ValueError(
                f"Panel {panel_id} has non-square pixels: "
                f"fast={px_fast:.6f}mm, slow={px_slow:.6f}mm. "
                f"Square pixels required per spec-db-core.md:40"
            )

    # Convert trusted_mask to numpy array if it's a tuple (DIALS format)
    if isinstance(trusted_mask, tuple):
        # Ensure correct shape and dtype
        mask_array = np.array([np.asarray(m, dtype=bool) for m in trusted_mask])
    else:
        mask_array = np.asarray(trusted_mask, dtype=bool)

    # Guard: validate mask polarity (True should be much more common than False)
    # A proper trusted mask should have >50% True values for typical detectors
    true_fraction = np.mean(mask_array)
    if true_fraction < 0.5:
        raise ValueError(
            f"Trusted mask appears inverted: only {true_fraction*100:.1f}% True. "
            f"Expected True=include polarity per spec-db-core.md:29"
        )

    # Ensure data shapes match
    assert data.shape == background_image.shape, \
        f"data shape {data.shape} != background {background_image.shape}"
    assert data.shape == mask_array.shape, \
        f"data shape {data.shape} != mask {mask_array.shape}"

    # Guard: validate sentinel integrity per simtbx_api.md:14
    # Background should use -1 sentinel outside ROIs
    # Inside ROIs, background is typically >= 0, but plane fitting can produce
    # slightly negative values (> -0.5). Sentinel is specifically <= -0.5.
    # Build ROI union mask from bbox/pids to validate sentinel coverage
    roi_union = np.zeros(data.shape, dtype=bool)
    for pid, (x0, x1, y0, y1) in zip(pids, bbox):
        roi_union[int(pid), int(y0):int(y1), int(x0):int(x1)] = True

    # Sentinel pixels are <= -0.5 (tolerant to floating point, but expect ~-1.0)
    # ROI pixels should not contain sentinel values (though may be slightly negative from fitting)
    sentinel_mask = background_image <= -0.5
    valid_background_mask = background_image >= 0

    # Check 1: Sentinel pixels should be outside ROI union
    sentinel_inside_roi = sentinel_mask & roi_union
    if np.any(sentinel_inside_roi):
        n_violations = np.sum(sentinel_inside_roi)
        first_violation = np.argwhere(sentinel_inside_roi)[0]
        pid, slow, fast = first_violation
        raise ValueError(
            f"Sentinel guard violation: {n_violations} pixels with background <= -0.5 "
            f"found inside ROI union. First violation at panel={pid}, slow={slow}, fast={fast} "
            f"with background={background_image[pid, slow, fast]:.3f}. "
            f"Expected background >= 0 inside ROIs per docs/simtbx_api.md:14"
        )

    # Check 2: Pixels outside ROI union should be sentinel (allow some tolerance for edge effects)
    outside_roi = ~roi_union
    non_sentinel_outside = outside_roi & ~sentinel_mask
    # Count pixels that are significantly different from -1 (not just rounding errors)
    significant_deviation = non_sentinel_outside & (np.abs(background_image + 1.0) > 0.1)
    if np.any(significant_deviation):
        n_violations = np.sum(significant_deviation)
        first_violation = np.argwhere(significant_deviation)[0]
        pid, slow, fast = first_violation
        raise ValueError(
            f"Sentinel guard violation: {n_violations} pixels outside ROI union "
            f"deviate significantly from -1 sentinel. First violation at panel={pid}, slow={slow}, fast={fast} "
            f"with background={background_image[pid, slow, fast]:.3f}. "
            f"Expected background ≈ -1 outside ROIs per docs/simtbx_api.md:14"
        )

    # Background-subtract target
    # Where background >= 0 (valid ROI pixels), subtract; elsewhere zero
    # Use float64 intermediate for numerical stability, then cast to float32
    target = np.where(background_image >= 0,
                     (data - background_image).astype(np.float64),
                     0.0)

    # Apply photon conversion if adu_per_photon is provided (ADR-02, spec-db-workflow.md:20)
    target_representation = "adu"
    global_scale_hint = None

    if adu_per_photon is not None:
        # Convert ADU to photons: target_photons = target_adu / adu_per_photon
        # Use float64 for the division, then cast back to float32
        target = (target / adu_per_photon).astype(np.float64)
        target_representation = "photons"
    else:
        # ADU mode: compute global_scale_hint for initialization
        # Estimate as mean of background-subtracted ROI intensities
        # Use simple mean over valid pixels (robust clipping not needed for scale hint)
        valid_target_pixels = target[background_image >= 0]
        if len(valid_target_pixels) > 0:
            global_scale_hint = float(np.mean(valid_target_pixels))
        else:
            global_scale_hint = 1.0  # Fallback if no valid pixels

    # Loss mask: (background >= 0) & trusted_mask
    loss_mask = (background_image >= 0) & mask_array

    # Zero out invalid pixels in target and cast to float32
    target = np.where(loss_mask, target, 0.0).astype(np.float32)

    # Build panel slices list
    panel_slices = []
    for i, (pid, box) in enumerate(zip(pids, bbox)):
        # bbox is (x0, x1, y0, y1) with exclusive upper bounds
        x0, x1, y0, y1 = box
        panel_slices.append((int(pid), (int(x0), int(x1), int(y0), int(y1))))

    return RefinementInputs(
        target=target,
        loss_mask=loss_mask,
        panel_slices=panel_slices,
        trusted_mask=mask_array,
        target_representation=target_representation,
        global_scale_hint=global_scale_hint
    )


# ============================================================================
# Config hydration functions
# ============================================================================

def create_detector_config(
    panel,
    beam,
    trusted_mask: Optional[np.ndarray] = None
) -> DetectorConfig:
    """
    Create DetectorConfig from dxtbx panel and beam.

    Implements geometry mapping per docs/config_crosswalk.md:15-37:
    - Beam center swap: dxtbx (fast, slow) -> torch (s, f)
    - DIALS convention with XYZ rotation angles derived from panel axes
    - Uses BEAM pivot to preserve beam center per docs/nanobrag_api.md:32-45
    - Square pixel guard
    - Mask array conversion to float (1=include, 0=exclude)

    The detector rotation angles are extracted from the panel's fast/slow/normal
    axes by forming a rotation matrix and converting to XYZ Euler angles via
    scitbx.matrix utilities.

    Args:
        panel: dxtbx Panel object
        beam: dxtbx Beam object
        trusted_mask: Optional boolean mask [slow, fast], True=include

    Returns:
        DetectorConfig with geometry, beam center, and mask

    Raises:
        ValueError: If pixels are not square or panel axes do not form a valid rotation matrix
    """
    from scitbx import matrix as scitbx_matrix

    # Pixel pitch guard (config_crosswalk.md:30)
    px_fast_mm, px_slow_mm = panel.get_pixel_size()
    if abs(px_fast_mm - px_slow_mm) > 1e-9:
        raise ValueError(
            f"Non-square pixels not supported: fast={px_fast_mm:.6f}mm, "
            f"slow={px_slow_mm:.6f}mm (spec-db-core.md:40)"
        )

    # Image dimensions (config_crosswalk.md:31)
    fast_px, slow_px = panel.get_image_size()

    # Distance (config_crosswalk.md:28)
    distance_mm = panel.get_directed_distance()

    # Beam center swap: dxtbx returns (fast_mm, slow_mm), torch expects (s, f)
    # (config_crosswalk.md:29, docs/nanobrag_api.md:28)
    fast_mm, slow_mm = panel.get_beam_centre(beam.get_s0())
    beam_center_s = slow_mm
    beam_center_f = fast_mm

    # Extract per-panel detector rotations from fast/slow/normal axes
    # Form rotation matrix with columns = (fast, slow, normal)
    fast_axis = np.array(panel.get_fast_axis())
    slow_axis = np.array(panel.get_slow_axis())
    normal_axis = np.array(panel.get_normal())

    # Build 3x3 rotation matrix as columns [fast, slow, normal]
    R = np.column_stack([fast_axis, slow_axis, normal_axis])

    # Validate that the matrix is a proper rotation (within numerical tolerance)
    # Check: R @ R^T = I and det(R) = 1
    identity_error = np.linalg.norm(R @ R.T - np.eye(3))
    det_error = abs(np.linalg.det(R) - 1.0)
    if identity_error > 1e-6 or det_error > 1e-6:
        raise ValueError(
            f"Panel axes do not form a valid rotation matrix. "
            f"Identity error: {identity_error:.6e}, Det error: {det_error:.6e}. "
            f"Fast axis: {fast_axis}, Slow axis: {slow_axis}, Normal: {normal_axis}"
        )

    # Convert rotation matrix to XYZ Euler angles using analytic inversion
    # The forward rotation is R = Rz @ Ry @ Rx, which gives:
    # R[0,2] = sin(phi_y), R[2,1] = -sin(phi_x)*cos(phi_y), R[2,2] = cos(phi_x)*cos(phi_y)
    # R[1,0] = sin(phi_x)*sin(phi_y)*cos(phi_z) + cos(phi_x)*sin(phi_z)
    # R[0,0] = cos(phi_y)*cos(phi_z)
    #
    # Solving: phi_y = arcsin(R[0,2]), phi_x = atan2(-R[2,1], R[2,2]), phi_z = atan2(-R[1,0], R[0,0])
    # However, the nanobrag convention uses negated signs for the inversion
    # Per input.md analysis, the correct inversion is:
    phi_y_rad = -np.arcsin(np.clip(R[2, 0], -1.0, 1.0))
    phi_x_rad = np.arctan2(R[2, 1], R[2, 2])
    phi_z_rad = np.arctan2(R[1, 0], R[0, 0])

    # Verify reconstruction to ensure the inversion is correct
    # Reconstruct R from the extracted angles and compare
    cos_x, sin_x = np.cos(phi_x_rad), np.sin(phi_x_rad)
    cos_y, sin_y = np.cos(phi_y_rad), np.sin(phi_y_rad)
    cos_z, sin_z = np.cos(phi_z_rad), np.sin(phi_z_rad)

    # Build individual rotation matrices
    Rx = np.array([[1, 0, 0],
                   [0, cos_x, -sin_x],
                   [0, sin_x, cos_x]])
    Ry = np.array([[cos_y, 0, sin_y],
                   [0, 1, 0],
                   [-sin_y, 0, cos_y]])
    Rz = np.array([[cos_z, -sin_z, 0],
                   [sin_z, cos_z, 0],
                   [0, 0, 1]])

    # Compose in XYZ order: R_reconstructed = Rz @ Ry @ Rx
    R_reconstructed = Rz @ Ry @ Rx
    reconstruction_error = np.linalg.norm(R - R_reconstructed)

    if reconstruction_error > 1e-9:
        raise ValueError(
            f"Euler angle reconstruction failed. Error: {reconstruction_error:.6e}. "
            f"This may indicate gimbal lock or numerical issues. "
            f"Angles (deg): phi_x={np.degrees(phi_x_rad):.4f}, "
            f"phi_y={np.degrees(phi_y_rad):.4f}, phi_z={np.degrees(phi_z_rad):.4f}"
        )

    # Convert to degrees
    detector_rotx_deg = np.degrees(phi_x_rad)
    detector_roty_deg = np.degrees(phi_y_rad)
    detector_rotz_deg = np.degrees(phi_z_rad)

    # Mask array: convert bool to float (config_crosswalk.md:33)
    mask_array = None
    if trusted_mask is not None:
        mask_array = trusted_mask.astype(np.float32)

    # Use DIALS convention with rotation angles derived from panel axes
    # This preserves BEAM pivot and correctly represents panel geometry
    return DetectorConfig(
        distance_mm=distance_mm,
        pixel_size_mm=px_fast_mm,
        spixels=slow_px,
        fpixels=fast_px,
        beam_center_s=beam_center_s,
        beam_center_f=beam_center_f,
        beam_center_source="explicit",
        detector_convention=DetectorConvention.DIALS,
        detector_rotx_deg=detector_rotx_deg,
        detector_roty_deg=detector_roty_deg,
        detector_rotz_deg=detector_rotz_deg,
        mask_array=mask_array
    )


def create_beam_config(beam) -> BeamConfig:
    """
    Create BeamConfig from dxtbx beam.

    Implements beam mapping per docs/config_crosswalk.md:39-53:
    - Wavelength in Angstroms
    - Polarization factor=0.0 for parity
    - Polarization axis from metadata or fallback defaults

    Args:
        beam: dxtbx Beam object

    Returns:
        BeamConfig with wavelength and polarization
    """
    # Wavelength (config_crosswalk.md:46)
    wavelength_A = beam.get_wavelength()

    # Polarization: try to extract metadata, fallback to defaults
    # (config_crosswalk.md:48-49, spec-db-core.md:44)
    try:
        polarization_axis_array = np.array(beam.get_polarization_normal())
        polarization_axis = tuple(polarization_axis_array.tolist())
    except (AttributeError, TypeError):
        # Fallback defaults
        polarization_axis = (0.0, 0.0, 1.0)

    return BeamConfig(
        wavelength_A=wavelength_A,
        polarization_factor=0.0,  # Parity default
        nopolar=False,
        polarization_axis=polarization_axis,
        dmin=0.0
    )


def create_crystal_config(crystal, experiment) -> CrystalConfig:
    """
    Create CrystalConfig from dxtbx crystal and experiment.

    Implements crystal mapping per docs/config_crosswalk.md:55-72:
    - Unit cell parameters in Angstroms and degrees (no conversion)
    - MOSFLM A* injection from crystal.get_A() columns
    - Misset angles default to zero (identity rotation)
    - Stills defaults: phi_steps=1, osc_range_deg=0, mosaic off

    Args:
        crystal: dxtbx Crystal object
        experiment: dxtbx Experiment object (for scan/goniometer)

    Returns:
        CrystalConfig with cell, orientation, and stills defaults
    """
    # Unit cell parameters (config_crosswalk.md:61)
    # dxtbx returns (a, b, c, alpha, beta, gamma) in Angstroms and degrees
    a, b, c, alpha, beta, gamma = crystal.get_unit_cell().parameters()

    # MOSFLM A* injection (config_crosswalk.md:62)
    # Columns of A matrix are (a*, b*, c*) in 1/Angstrom
    # get_A() returns a tuple of 9 elements (row-major 3x3 matrix)
    A_tuple = crystal.get_A()
    A = np.array(A_tuple).reshape(3, 3)
    mosflm_a_star = np.array(A[:, 0])
    mosflm_b_star = np.array(A[:, 1])
    mosflm_c_star = np.array(A[:, 2])

    # Misset defaults to zero (config_crosswalk.md:63)
    misset_deg = np.array([0.0, 0.0, 0.0])

    # Stills defaults (config_crosswalk.md:64)
    # For stills (no scan), use phi_steps=1, osc_range_deg=0
    phi_steps = 1
    osc_range_deg = 0.0
    mosaic_domains = 1
    mosaic_spread_deg = 0.0

    return CrystalConfig(
        cell_a=a,
        cell_b=b,
        cell_c=c,
        cell_alpha=alpha,
        cell_beta=beta,
        cell_gamma=gamma,
        mosflm_a_star=mosflm_a_star,
        mosflm_b_star=mosflm_b_star,
        mosflm_c_star=mosflm_c_star,
        misset_deg=misset_deg,
        phi_steps=phi_steps,
        osc_range_deg=osc_range_deg,
        mosaic_domains=mosaic_domains,
        mosaic_spread_deg=mosaic_spread_deg
    )


# ============================================================================
# Structure factor grid helper
# ============================================================================


def build_structure_factor_grid(indices, amplitudes, device=None):
    """Build dense 3D HKL grid for nanobrag_torch from MTZ reflections.

    Implements SCALE-001: Structure factors pass through unscaled.
    DiffBragg applies spot_scale_override internally to final intensities;
    applying it here would duplicate scaling and break parity.

    Args:
        indices: Miller indices array-like, shape (n_reflections, 3), dtype int
        amplitudes: Structure factor amplitudes |F|, shape (n_reflections,), dtype float
        device: torch device (optional; defaults to CPU if not provided)

    Returns:
        tuple: (grid, metadata) where
            - grid: torch.Tensor, shape (h_range, k_range, l_range), dtype float32
            - metadata: dict with HKL range, grid stats, and coverage info

    Raises:
        ImportError: If torch is not available

    Note:
        Per SCALE-001 (docs/findings.md:15), structure factors are NOT scaled by
        spot_scale_override. Scaling is applied post-simulation per SCALE-002.
    """
    import logging

    try:
        import torch
    except ImportError as e:
        raise ImportError(
            "torch is required for build_structure_factor_grid. "
            f"Import error: {e}"
        )

    logger = logging.getLogger(__name__)

    # Default to CPU if device not specified
    if device is None:
        device = torch.device('cpu')

    # Convert inputs to numpy arrays
    hkls = np.asarray(indices, dtype=int)
    amps = np.abs(np.asarray(amplitudes, dtype=np.float32))

    # Per SCALE-001: Do NOT scale structure factors
    # DiffBragg applies spot_scale_override internally to final intensities
    # Applying sqrt(scale_override) here duplicates the scale and breaks parity
    logger.info(
        f"Structure factors (no scaling applied per SCALE-001): "
        f"min={amps.min():.3e}, max={amps.max():.3e}, mean={amps.mean():.3e}"
    )

    # Compute HKL grid bounds
    h_min, h_max = int(hkls[:, 0].min()), int(hkls[:, 0].max())
    k_min, k_max = int(hkls[:, 1].min()), int(hkls[:, 1].max())
    l_min, l_max = int(hkls[:, 2].min()), int(hkls[:, 2].max())

    h_range = h_max - h_min + 1
    k_range = k_max - k_min + 1
    l_range = l_max - l_min + 1

    # Allocate grid on specified device
    grid = torch.zeros((h_range, k_range, l_range), device=device, dtype=torch.float32)

    # Populate grid with structure factor amplitudes
    n_total = len(hkls)
    n_inrange = 0

    for (h, k, l), amp in zip(hkls, amps):
        idx_h = int(h - h_min)
        idx_k = int(k - k_min)
        idx_l = int(l - l_min)

        if 0 <= idx_h < h_range and 0 <= idx_k < k_range and 0 <= idx_l < l_range:
            grid[idx_h, idx_k, idx_l] = float(amp)
            n_inrange += 1

    # Compute grid statistics for diagnostics
    grid_nonzero_count = int((grid != 0).sum().item())
    grid_min = float(grid.min().item())
    grid_max = float(grid.max().item())
    grid_mean = float(grid.mean().item())

    logger.info(
        f"Structure factor grid stats: min={grid_min:.3e}, max={grid_max:.3e}, "
        f"mean={grid_mean:.3e}, nonzero={grid_nonzero_count}"
    )

    # Build metadata dict
    metadata = {
        "h_min": h_min,
        "h_max": h_max,
        "k_min": k_min,
        "k_max": k_max,
        "l_min": l_min,
        "l_max": l_max,
        "h_range": h_range,
        "k_range": k_range,
        "l_range": l_range,
        "n_reflections": n_total,
        "n_in_range": n_inrange,
        "in_range_fraction": float(n_inrange / n_total) if n_total > 0 else 0.0,
        "grid_nonzero": grid_nonzero_count,
        "grid_min": grid_min,
        "grid_max": grid_max,
        "grid_mean": grid_mean,
    }

    return grid, metadata


# ============================================================================
# Forward simulation helper for testing and validation
# ============================================================================

def simulate_forward_once(
    inputs: RefinementInputs,
    detector,
    beam,
    crystal,
    experiment,
    hkl_indices: np.ndarray,
    hkl_amplitudes: np.ndarray,
    spot_scale_override: Optional[float] = None,
    device=None
) -> Tuple[np.ndarray, dict]:
    """
    Run zero-iteration forward simulation without HDF5 emission.

    Extracts per-panel Bragg tensors using nanobrag_torch Simulator with
    SCALE-002 post-simulation scaling applied. Designed for acceptance testing
    (DB-AT-024) and diagnostic artifact emission.

    Args:
        inputs: RefinementInputs from prepare_refinement_inputs containing
                target, loss_mask, panel_slices, and global_scale_hint
        detector: dxtbx Detector object for geometry
        beam: dxtbx Beam object for wavelength/polarization
        crystal: dxtbx Crystal object for unit cell/orientation
        experiment: dxtbx Experiment object (for create_crystal_config)
        hkl_indices: Miller indices array from MTZ, shape (n_refl, 3)
        hkl_amplitudes: Structure factor amplitudes from MTZ, shape (n_refl,)
        spot_scale_override: Optional scale factor (default 1.0 if None)
        device: torch.device for simulation (default cpu)

    Returns:
        bragg: Per-panel Bragg tensors [panel, slow, fast] as float32 numpy array
               with SCALE-002 sqrt(spot_scale_override) applied post-simulation
        diagnostics: Dict containing:
            - masked_mse: Masked MSE between target and bragg
            - loss_mask_coverage: Fraction of pixels in loss mask
            - n_rois: Number of ROI bboxes
            - target_shape: Shape of target tensor (as string)
            - global_scale_hint: Scale hint from inputs (ADU mode only)
            - spot_scale_override: Scale override used
            - sqrt_spot_scale: Sqrt(spot_scale_override) applied
            - bragg_stats: Dict with min/max/mean of bragg output
            - hkl_stats: HKL grid metadata from build_structure_factor_grid

    Raises:
        ImportError: If nanobrag_torch is not available
        ValueError: If config creation fails or simulation errors

    Notes:
        - Honors RUNTIME-001 (NANOBRAGG_DISABLE_COMPILE=1 recommended)
        - Applies SCALE-001 (unscaled HKL grid) and SCALE-002 (post-sim scaling)
        - Applies GEOMETRY-002 (analytic Euler inversion in create_detector_config)
        - Device-neutral design: defaults to CPU, respects passed device
        - Does not write HDF5 or persist artifacts (caller's responsibility)
    """
    try:
        import torch
        from nanobrag_torch.simulator import Simulator
        from nanobrag_torch.models.detector import Detector as TorchDetector
        from nanobrag_torch.models.crystal import Crystal as TorchCrystal
    except ImportError as e:
        raise ImportError(
            f"nanobrag_torch is required for simulate_forward_once. Import error: {e}"
        )

    # Default device to CPU if not provided
    if device is None:
        device = torch.device('cpu')
    elif not isinstance(device, torch.device):
        device = torch.device(device)

    # Build structure factor grid (SCALE-001: unscaled)
    hkl_grid, hkl_metadata = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device
    )

    # Determine spot scale override (SCALE-002)
    if spot_scale_override is None:
        spot_scale_override = 1.0
    sqrt_spot_scale = np.sqrt(spot_scale_override)

    # Prepare configs (shared across panels where applicable)
    beam_config = create_beam_config(beam)
    crystal_config = create_crystal_config(crystal, experiment)

    # Run simulator per panel
    n_panels = len(detector)
    panel_shape = inputs.target.shape[1:]  # (slow, fast)
    bragg = np.zeros((n_panels, *panel_shape), dtype=np.float32)

    for panel_id in range(n_panels):
        panel = detector[panel_id]

        # Create detector config for this panel
        detector_config = create_detector_config(
            panel=panel,
            beam=beam,
            trusted_mask=inputs.trusted_mask[panel_id]
        )

        # Convert mask_array to torch.Tensor if it's a numpy array
        # Per compute_zero_iteration_metrics.py:88-89, nanobrag_torch Simulator
        # expects torch.Tensor for mask_array
        if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
            detector_config.mask_array = torch.tensor(
                detector_config.mask_array, dtype=torch.float32, device=device
            )

        # Instantiate models
        detector_model = TorchDetector(detector_config, device=device)
        crystal_model = TorchCrystal(crystal_config)

        # Attach HKL data to crystal model
        crystal_model.hkl_data = hkl_grid
        crystal_model.hkl_metadata = hkl_metadata

        # Run simulator (single source, GEOMETRY-002/HKL-ORIENT-001 applied in bridge)
        simulator = Simulator(detector=detector_model, crystal=crystal_model, device=device)
        panel_output = simulator.run()  # Returns torch.Tensor on device

        # Move to CPU and convert to numpy
        panel_output_np = panel_output.cpu().detach().numpy().astype(np.float32)

        # Apply sqrt(spot_scale_override) post-simulation (SCALE-002)
        panel_output_scaled = panel_output_np * sqrt_spot_scale

        # Store in bragg array
        bragg[panel_id] = panel_output_scaled

    # Compute diagnostics
    masked_diff = np.where(inputs.loss_mask, inputs.target - bragg, 0.0)
    masked_mse = float((masked_diff ** 2).sum() / inputs.loss_mask.sum()) if inputs.loss_mask.sum() > 0 else float('nan')

    diagnostics = {
        "masked_mse": masked_mse,
        "loss_mask_coverage": float(inputs.loss_mask.mean()),
        "n_rois": len(inputs.panel_slices),
        "target_shape": str(inputs.target.shape),
        "global_scale_hint": inputs.global_scale_hint,
        "spot_scale_override": float(spot_scale_override),
        "sqrt_spot_scale": float(sqrt_spot_scale),
        "bragg_stats": {
            "min": float(bragg.min()),
            "max": float(bragg.max()),
            "mean": float(bragg.mean())
        },
        "hkl_stats": hkl_metadata
    }

    return bragg, diagnostics


# ============================================================================
# Torch-mode helpers for gradient testing (DB-AT-010)
# ============================================================================

def simulate_forward_torch(
    inputs: RefinementInputs,
    detector,
    beam,
    crystal,
    experiment,
    hkl_indices: np.ndarray,
    hkl_amplitudes: np.ndarray,
    spot_scale_override: Optional[float] = None,
    device=None,
    dtype=None
) -> "torch.Tensor":
    """
    Run forward simulation returning torch tensor for gradient testing.

    Similar to simulate_forward_once but preserves torch gradients by avoiding
    .detach().numpy() conversions. Designed for DB-AT-010 gradcheck acceptance
    testing with RUNTIME-001 (NANOBRAGG_DISABLE_COMPILE=1) enforcement.

    Args:
        inputs: RefinementInputs from prepare_refinement_inputs containing
                target, loss_mask, panel_slices, and global_scale_hint
        detector: dxtbx Detector object for geometry
        beam: dxtbx Beam object for wavelength/polarization
        crystal: dxtbx Crystal object for unit cell/orientation
        experiment: dxtbx Experiment object (for create_crystal_config)
        hkl_indices: Miller indices array from MTZ, shape (n_refl, 3)
        hkl_amplitudes: Structure factor amplitudes from MTZ, shape (n_refl,)
        spot_scale_override: Optional scale factor (default 1.0 if None)
        device: torch.device for simulation (default cpu)
        dtype: torch.dtype for computation (default float32, use float64 for gradcheck)

    Returns:
        bragg_torch: Per-panel Bragg tensors [panel, slow, fast] as torch.Tensor
                     with SCALE-002 sqrt(spot_scale_override) applied differentiably

    Raises:
        ImportError: If nanobrag_torch is not available
        ValueError: If config creation fails or simulation errors

    Notes:
        - RUNTIME-001: Use with NANOBRAGG_DISABLE_COMPILE=1 for gradient tests
        - SCALE-001: Structure factors unscaled in grid
        - SCALE-002: sqrt(spot_scale) applied post-simulation as differentiable torch op
        - Preserves gradient graph (no .detach() or .numpy() conversions)
        - Defaults to float32 but accepts float64 for gradcheck (per runtime checklist §2)
    """
    try:
        import torch
        from nanobrag_torch.simulator import Simulator
        from nanobrag_torch.models.detector import Detector as TorchDetector
        from nanobrag_torch.models.crystal import Crystal as TorchCrystal
    except ImportError as e:
        raise ImportError(
            f"nanobrag_torch is required for simulate_forward_torch. Import error: {e}"
        )

    # Default device and dtype per runtime checklist §2
    if device is None:
        device = torch.device('cpu')
    elif not isinstance(device, torch.device):
        device = torch.device(device)

    if dtype is None:
        dtype = torch.float32

    # Build structure factor grid (SCALE-001: unscaled)
    hkl_grid, hkl_metadata = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device
    )

    # Ensure hkl_grid is correct dtype
    if hkl_grid.dtype != dtype:
        hkl_grid = hkl_grid.to(dtype=dtype)

    # Determine spot scale override (SCALE-002)
    if spot_scale_override is None:
        spot_scale_override = 1.0
    # Convert to tensor for differentiable scaling
    sqrt_spot_scale_tensor = torch.tensor(
        np.sqrt(spot_scale_override), dtype=dtype, device=device
    )

    # Prepare configs (shared across panels where applicable)
    beam_config = create_beam_config(beam)
    crystal_config = create_crystal_config(crystal, experiment)

    # Run simulator per panel
    n_panels = len(detector)
    panel_shape = inputs.target.shape[1:]  # (slow, fast)
    bragg_panels = []

    for panel_id in range(n_panels):
        panel = detector[panel_id]

        # Create detector config for this panel
        detector_config = create_detector_config(
            panel=panel,
            beam=beam,
            trusted_mask=inputs.trusted_mask[panel_id]
        )

        # Convert mask_array to torch.Tensor with correct dtype
        if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
            detector_config.mask_array = torch.tensor(
                detector_config.mask_array, dtype=dtype, device=device
            )
        elif isinstance(detector_config.mask_array, torch.Tensor):
            # Ensure dtype matches
            if detector_config.mask_array.dtype != dtype:
                detector_config.mask_array = detector_config.mask_array.to(dtype=dtype, device=device)

        # Instantiate models
        detector_model = TorchDetector(detector_config, device=device)
        crystal_model = TorchCrystal(crystal_config)

        # Attach HKL data to crystal model
        crystal_model.hkl_data = hkl_grid
        crystal_model.hkl_metadata = hkl_metadata

        # Run simulator (single source, GEOMETRY-002/HKL-ORIENT-001 applied in bridge)
        simulator = Simulator(detector=detector_model, crystal=crystal_model, device=device)
        panel_output = simulator.run()  # Returns torch.Tensor on device

        # Ensure correct dtype
        if panel_output.dtype != dtype:
            panel_output = panel_output.to(dtype=dtype)

        # Apply sqrt(spot_scale_override) post-simulation (SCALE-002, differentiable)
        panel_output_scaled = panel_output * sqrt_spot_scale_tensor

        bragg_panels.append(panel_output_scaled)

    # Stack panels into single tensor [panel, slow, fast]
    bragg_torch = torch.stack(bragg_panels, dim=0)

    return bragg_torch


def compute_masked_mse_loss(
    prediction: "torch.Tensor",
    target: "torch.Tensor",
    mask: "torch.Tensor"
) -> "torch.Tensor":
    """
    Compute masked MSE loss for gradient-based optimization.

    Computes mean squared error over pixels where mask is True, preserving
    gradient graph for torch.autograd.gradcheck. Follows SCALE-001/002 policy
    (target and prediction must already include any spot scale adjustments).

    Args:
        prediction: Predicted Bragg intensities [panel, slow, fast], torch.Tensor
        target: Target intensities [panel, slow, fast], torch.Tensor
        mask: Loss mask [panel, slow, fast], torch.Tensor with dtype bool or numeric

    Returns:
        loss: Scalar tensor with mean squared error over masked pixels

    Raises:
        ValueError: If shapes don't match or mask has no valid pixels

    Notes:
        - Preserves gradient graph (no .detach() or numpy conversions)
        - Respects SCALE-002: target/prediction must have same post-simulation scaling
        - Returns scalar tensor suitable for torch.autograd.gradcheck
        - Mask expected to be boolean or numeric (0/1); numeric values treated as weights
    """
    import torch

    # Validate shapes
    if prediction.shape != target.shape:
        raise ValueError(
            f"Shape mismatch: prediction {prediction.shape} vs target {target.shape}"
        )
    if mask.shape != prediction.shape:
        raise ValueError(
            f"Mask shape {mask.shape} doesn't match prediction shape {prediction.shape}"
        )

    # Ensure mask is boolean
    if mask.dtype != torch.bool:
        mask = mask.bool()

    # Check for valid mask pixels
    n_valid = mask.sum()
    if n_valid == 0:
        raise ValueError("Loss mask contains no valid pixels")

    # Compute masked squared error
    squared_error = (prediction - target) ** 2
    masked_squared_error = torch.where(mask, squared_error, torch.zeros_like(squared_error))

    # Mean over valid pixels
    loss = masked_squared_error.sum() / n_valid.to(prediction.dtype)

    return loss
