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

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any
import numpy as np


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
        loss_mask: Boolean mask where loss should be computed, (background >= 0) & trusted
        panel_slices: List of (panel_id, bbox) tuples for per-panel ROIs
                     bbox format: (x0, x1, y0, y1) with exclusive upper bounds
        trusted_mask: Original trusted mask in [panel, slow, fast] order (True=include)
    """
    target: np.ndarray  # [panel, slow, fast] float, background-subtracted
    loss_mask: np.ndarray  # [panel, slow, fast] bool, (background >= 0) & trusted
    panel_slices: List[Tuple[int, Tuple[int, int, int, int]]]  # [(pid, (x0,x1,y0,y1))]
    trusted_mask: np.ndarray  # [panel, slow, fast] bool, True=include


def prepare_refinement_inputs(
    data: np.ndarray,
    background_image: np.ndarray,
    trusted_mask: np.ndarray,
    bbox: np.ndarray,
    pids: np.ndarray,
    detector
) -> RefinementInputs:
    """
    Prepare background-subtracted targets, loss masks, and panel slices for torch simulator.

    Implements spec-db-core.md contracts:
    - Array ordering: [panel, slow, fast] (spec-db-core.md:20)
    - Loss mask: (background >= 0) ∧ trusted_mask (spec-db-core.md:55)
    - Zeroing invalid pixels where loss_mask is False
    - ROI bbox semantics: (x0, x1, y0, y1) with exclusive upper bounds (spec-db-core.md:22)

    Guards:
    - Pixel pitch must be square (config_crosswalk.md:30)
    - Trusted mask polarity must be True=include (spec-db-core.md:29)

    Args:
        data: Raw pixel data [panel, slow, fast] in ADU
        background_image: Background estimate [panel, slow, fast], -1 outside ROIs
        trusted_mask: Per-panel mask tuple or array, True=include
        bbox: ROI bounding boxes, shape (n_roi, 4) as (x0, x1, y0, y1)
        pids: Panel IDs for each ROI, shape (n_roi,)
        detector: dxtbx Detector object for pixel pitch validation

    Returns:
        RefinementInputs with background-subtracted target, loss mask, and panel slices

    Raises:
        ValueError: If pixel pitch is not square or mask polarity is inverted
    """
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

    # Background-subtract target
    # Where background >= 0 (valid ROI pixels), subtract; elsewhere zero
    target = np.where(background_image >= 0, data - background_image, 0.0)

    # Loss mask: (background >= 0) & trusted_mask
    loss_mask = (background_image >= 0) & mask_array

    # Zero out invalid pixels in target
    target = np.where(loss_mask, target, 0.0)

    # Build panel slices list
    panel_slices = []
    for i, (pid, box) in enumerate(zip(pids, bbox)):
        # bbox is (x0, x1, y0, y1) with exclusive upper bounds
        x0, x1, y0, y1 = box
        panel_slices.append((int(pid), (int(x0), int(x1), int(y0), int(y1))))

    return RefinementInputs(
        target=target.astype(np.float32),
        loss_mask=loss_mask,
        panel_slices=panel_slices,
        trusted_mask=mask_array
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
