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
from typing import List, Tuple, Optional, Any, TYPE_CHECKING, Dict
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
        sigma_readout: Per-pixel or per-panel readout noise aligned with target units.
        target_representation: "photons" or "adu" indicating target units
        global_scale_hint: Optional scale hint for ADU mode (mean(target)/mean(sim) estimate)
    """
    target: np.ndarray  # [panel, slow, fast] float, background-subtracted
    loss_mask: np.ndarray  # [panel, slow, fast] bool, (background >= 0) & trusted
    panel_slices: List[Tuple[int, Tuple[int, int, int, int]]]  # [(pid, (x0,x1,y0,y1))]
    trusted_mask: np.ndarray  # [panel, slow, fast] bool, True=include
    sigma_readout: np.ndarray  # [panel, slow, fast] float, readout noise in target units
    target_representation: str = "adu"  # "adu" or "photons"
    global_scale_hint: Optional[float] = None  # For ADU mode initialization
    sigma_readout_provenance: Optional[str] = None  # Source of sigma tensor (cli_override, external_lookup, ...)


def prepare_refinement_inputs(
    data: np.ndarray,
    background_image: np.ndarray,
    trusted_mask: np.ndarray,
    bbox: np.ndarray,
    pids: np.ndarray,
    detector,
    adu_per_photon: Optional[float] = None,
    sigma_readout: Optional[np.ndarray] = None,
    sigma_readout_provenance: Optional[str] = None,
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
        sigma_readout: Optional readout noise estimates aligned with target units (photons if
                       adu_per_photon provided, else ADU). Accepts scalar, per-panel, or per-pixel
                       arrays broadcastable to data shape.

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

    # Prepare sigma_readout array; allow scalars or broadcastable inputs.
    if sigma_readout is not None:
        sigma_array = np.asarray(sigma_readout, dtype=np.float64)
        if sigma_array.shape != data.shape:
            try:
                sigma_array = np.broadcast_to(sigma_array, data.shape).copy()
            except ValueError as e:
                raise ValueError(
                    f"sigma_readout shape {sigma_array.shape} is not broadcastable to data shape {data.shape}"
                ) from e
    else:
        sigma_array = None

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
        if sigma_array is not None:
            sigma_array = sigma_array / adu_per_photon
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

    # Zero out invalid pixels in target and sigma, then cast to float32
    target = np.where(loss_mask, target, 0.0).astype(np.float32)
    if sigma_array is None:
        sigma_array = np.zeros_like(target, dtype=np.float32)
    else:
        sigma_array = np.where(loss_mask, sigma_array, 0.0).astype(np.float32)

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
        sigma_readout=sigma_array,
        target_representation=target_representation,
        global_scale_hint=global_scale_hint,
        sigma_readout_provenance=sigma_readout_provenance,
    )


# ============================================================================
# Config hydration functions
# ============================================================================

def create_detector_config(
    panel,
    beam,
    trusted_mask: Optional[np.ndarray] = None,
    distance_mm_override: Optional[torch.Tensor] = None,
    roi_bbox: Optional[Tuple[int, int, int, int]] = None,
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
        distance_mm_override: Optional torch.Tensor scalar for distance override (TORCH-REFINE-003)
                             If provided, replaces panel.get_directed_distance() for Stage C
        roi_bbox: Optional tuple (x0, x1, y0, y1) with exclusive upper bounds specifying a cropped
                  ROI. When provided, the detector's fpixels/spixels and beam center are adjusted
                  so pixel (0,0) maps to the ROI's top-left corner, and the trusted mask is sliced.

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
    roi_offsets: Optional[Tuple[int, int]] = None
    if roi_bbox is not None:
        x0, x1, y0, y1 = map(int, roi_bbox)
        if x0 < 0 or x1 > fast_px or y0 < 0 or y1 > slow_px:
            raise ValueError(
                f"ROI bbox {roi_bbox} out of bounds for panel size (fast={fast_px}, slow={slow_px})"
            )
        if x0 >= x1 or y0 >= y1:
            raise ValueError(f"Invalid ROI bbox {roi_bbox}: upper bounds must exceed lower bounds")
        roi_offsets = (x0, y0)
        fast_px = x1 - x0
        slow_px = y1 - y0

    # Distance (config_crosswalk.md:28)
    # Allow Stage C to override distance with differentiable tensor (TORCH-REFINE-003)
    if distance_mm_override is not None:
        # distance_mm_override is a torch.Tensor; extract scalar value or use directly
        # DetectorConfig expects a Python float, so we need to handle tensor→scalar conversion
        distance_mm = distance_mm_override
    else:
        distance_mm = panel.get_directed_distance()

    # Beam center swap: dxtbx returns (fast_mm, slow_mm), torch expects (s, f)
    # (config_crosswalk.md:29, docs/nanobrag_api.md:28)
    fast_mm, slow_mm = panel.get_beam_centre(beam.get_s0())
    beam_center_s = slow_mm
    beam_center_f = fast_mm
    if roi_offsets is not None:
        x0, y0 = roi_offsets
        beam_center_f -= x0 * px_fast_mm
        beam_center_s -= y0 * px_slow_mm

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

    # Mask array: convert bool to float tensor (config_crosswalk.md:31)
    # CRITICAL: Simulator expects mask_array as torch.Tensor, not numpy (CLI-001)
    # Use torch.as_tensor to avoid device changes; assert 0/1 values
    import torch
    mask_array = None
    if trusted_mask is not None:
        mask_np = np.array(trusted_mask, copy=False)
        if roi_bbox is not None:
            x0, x1, y0, y1 = map(int, roi_bbox)
            mask_np = mask_np[y0:y1, x0:x1]
        mask_array = torch.as_tensor(mask_np.astype(np.float32), dtype=torch.float32)
        # Assert tensor stays 0/1-valued per nanobrag_api.md:44
        unique_vals = torch.unique(mask_array)
        assert torch.all((unique_vals == 0.0) | (unique_vals == 1.0)), \
            f"mask_array must be 0/1-valued, got unique values: {unique_vals.tolist()}"

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


def create_beam_config(beam, flux=None, beamsize_mm=None, exposure=None) -> BeamConfig:
    """
    Create BeamConfig from dxtbx beam with optional calibration overrides.

    Implements beam mapping per docs/config_crosswalk.md:39-53:
    - Wavelength in Angstroms
    - Polarization factor=0.0 for parity
    - Polarization axis from metadata or fallback defaults
    - Optional flux/beamsize/exposure from DiffBragg calibration metadata

    Args:
        beam: dxtbx Beam object
        flux: Optional beam flux in photons/s (from calibration metadata)
        beamsize_mm: Optional beam size in mm (from calibration metadata)
        exposure: Optional exposure time in seconds (from calibration metadata)

    Returns:
        BeamConfig with wavelength, polarization, and optional calibration fields
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

    # Build kwargs for BeamConfig, only including calibration overrides if provided
    # BeamConfig.__post_init__ doesn't handle None gracefully (TypeError: '>' not supported)
    beam_kwargs = {
        'wavelength_A': wavelength_A,
        'polarization_factor': 0.0,  # Parity default
        'nopolar': False,
        'polarization_axis': polarization_axis,
        'dmin': 0.0
    }

    # Only add flux/beamsize/exposure if all three are provided
    # (BeamConfig.__post_init__ requires all three to compute fluence)
    if flux is not None:
        beam_kwargs['flux'] = flux
    if beamsize_mm is not None:
        beam_kwargs['beamsize_mm'] = beamsize_mm
    if exposure is not None:
        beam_kwargs['exposure'] = exposure

    return BeamConfig(**beam_kwargs)


def create_crystal_config(crystal, experiment, N_cells=None, apply_n_cells=True, crystal_overrides=None, misset_deg_override=None) -> Tuple[CrystalConfig, bool]:
    """
    Create CrystalConfig from dxtbx crystal and experiment with optional calibration overrides.

    Implements crystal mapping per docs/config_crosswalk.md:55-72:
    - Unit cell parameters in Angstroms and degrees (no conversion)
    - MOSFLM A* injection from crystal.get_A() columns
    - Misset angles default to zero (identity rotation)
    - Stills defaults: phi_steps=1, osc_range_deg=0, mosaic off
    - Optional N_cells from DiffBragg calibration metadata (gated by apply_n_cells per SCALE-005)

    Args:
        crystal: dxtbx Crystal object
        experiment: dxtbx Experiment object (for scan/goniometer)
        N_cells: Optional tuple of 3 ints for mosaic domain counts (from calibration metadata)
        apply_n_cells: If False, ignore N_cells even if provided (SCALE-005 guard)
        crystal_overrides: Optional dict of tensor-valued crystal parameter overrides
                          for refinement. Supports keys: 'cell_a', 'cell_b', 'cell_c',
                          'cell_alpha', 'cell_beta', 'cell_gamma'. Tensors must have
                          requires_grad=True to preserve gradient flow (GRADIENT-001).
        misset_deg_override: Optional array/tensor of XYZ extrinsic Euler angles (degrees)
                            for orientation refinement (TORCH-REFINE-002). When provided,
                            overrides the default zero misset. Can be torch.Tensor to preserve
                            gradient flow for differentiable orientation refinement.

    Returns:
        Tuple of (CrystalConfig, n_cells_applied: bool) where n_cells_applied indicates
        whether N_cells was actually included in the config
    """
    # Unit cell parameters (config_crosswalk.md:61)
    # dxtbx returns (a, b, c, alpha, beta, gamma) in Angstroms and degrees
    a, b, c, alpha, beta, gamma = crystal.get_unit_cell().parameters()

    # Apply crystal_overrides if provided (GRADIENT-001)
    # This allows tensor-valued parameters to flow through for refinement
    if crystal_overrides is not None:
        if 'cell_a' in crystal_overrides:
            a = crystal_overrides['cell_a']
        if 'cell_b' in crystal_overrides:
            b = crystal_overrides['cell_b']
        if 'cell_c' in crystal_overrides:
            c = crystal_overrides['cell_c']
        if 'cell_alpha' in crystal_overrides:
            alpha = crystal_overrides['cell_alpha']
        if 'cell_beta' in crystal_overrides:
            beta = crystal_overrides['cell_beta']
        if 'cell_gamma' in crystal_overrides:
            gamma = crystal_overrides['cell_gamma']

    # MOSFLM A* injection (config_crosswalk.md:62)
    # Columns of A matrix are (a*, b*, c*) in 1/Angstrom
    # get_A() returns a tuple of 9 elements (row-major 3x3 matrix)
    # IMPORTANT: When crystal_overrides are provided, skip A* injection and let
    # nanobrag_torch compute A* from the overridden cell parameters instead.
    # Otherwise A* from the base crystal will override the cell parameter changes.
    # EXCEPTION (CONVERGENCE-001): If crystal_overrides contains mosflm_a/b/c_star
    # keys, use those instead of dxtbx crystal.get_A() (for U-matrix mode).
    if crystal_overrides is None:
        A_tuple = crystal.get_A()
        A = np.array(A_tuple).reshape(3, 3)
        mosflm_a_star = np.array(A[:, 0])
        mosflm_b_star = np.array(A[:, 1])
        mosflm_c_star = np.array(A[:, 2])
    elif 'mosflm_a_star' in crystal_overrides:
        # Use MOSFLM A* from overrides (U-matrix mode, CONVERGENCE-001 fix)
        mosflm_a_star = crystal_overrides['mosflm_a_star']
        mosflm_b_star = crystal_overrides['mosflm_b_star']
        mosflm_c_star = crystal_overrides['mosflm_c_star']
    else:
        # Let nanobrag_torch compute A* from overridden cell parameters
        mosflm_a_star = None
        mosflm_b_star = None
        mosflm_c_star = None

    # Misset defaults to zero (config_crosswalk.md:63)
    # Allow override for orientation refinement (TORCH-REFINE-002)
    if misset_deg_override is not None:
        misset_deg = misset_deg_override
    else:
        misset_deg = np.array([0.0, 0.0, 0.0])

    # Stills defaults (config_crosswalk.md:64)
    # For stills (no scan), use phi_steps=1, osc_range_deg=0
    phi_steps = 1
    osc_range_deg = 0.0
    mosaic_domains = 1
    mosaic_spread_deg = 0.0

    # Build kwargs for CrystalConfig, only including N_cells if provided AND apply_n_cells=True
    crystal_kwargs = {
        'cell_a': a,
        'cell_b': b,
        'cell_c': c,
        'cell_alpha': alpha,
        'cell_beta': beta,
        'cell_gamma': gamma,
        'mosflm_a_star': mosflm_a_star,
        'mosflm_b_star': mosflm_b_star,
        'mosflm_c_star': mosflm_c_star,
        'misset_deg': misset_deg,
        'phi_steps': phi_steps,
        'osc_range_deg': osc_range_deg,
        'mosaic_domains': mosaic_domains,
        'mosaic_spread_deg': mosaic_spread_deg
    }

    # Guard: Only add N_cells if provided AND apply_n_cells=True (SCALE-005)
    # Prevents 3.2e5× intensity inflation until sample clipping semantics are validated
    n_cells_applied = False
    if N_cells is not None and apply_n_cells:
        crystal_kwargs['N_cells'] = N_cells
        n_cells_applied = True

    return CrystalConfig(**crystal_kwargs), n_cells_applied


def recover_cell_from_a_star(a_star_matrix: np.ndarray) -> Tuple[float, float, float, float, float, float]:
    """
    Recover real-space unit cell parameters (a, b, c, α, β, γ) from a reciprocal
    matrix A* using cctbx.

    This helper enables Phase A2 baseline B_ideal variants by reconstructing the
    effective unit cell encoded in a given 3×3 A* matrix (e.g., from MOSFLM A*
    injection or mapping geometry).

    Args:
        a_star_matrix: 3×3 numpy array with reciprocal basis vectors as columns:
            [a* | b* | c*] in 1/Å.

    Returns:
        Tuple (a, b, c, alpha_deg, beta_deg, gamma_deg) in Å and degrees.

    Raises:
        ImportError: If cctbx.uctbx is unavailable.
        ValueError: If a_star_matrix is singular or produces a degenerate cell.
    """
    try:
        from cctbx import uctbx  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "recover_cell_from_a_star requires cctbx.uctbx. "
            f"Import failed: {exc}"
        ) from exc

    # cctbx.uctbx.unit_cell can be constructed from reciprocal space parameters.
    # Extract reciprocal vectors from columns of A*
    a_star_vec = a_star_matrix[:, 0]
    b_star_vec = a_star_matrix[:, 1]
    c_star_vec = a_star_matrix[:, 2]

    # Compute reciprocal metric tensor G* = A*^T @ A*
    # This gives us the magnitudes and angles in reciprocal space
    a_star_len = np.linalg.norm(a_star_vec)
    b_star_len = np.linalg.norm(b_star_vec)
    c_star_len = np.linalg.norm(c_star_vec)

    # Compute reciprocal angles (α*, β*, γ*) in radians
    cos_alpha_star = np.dot(b_star_vec, c_star_vec) / (b_star_len * c_star_len)
    cos_beta_star = np.dot(a_star_vec, c_star_vec) / (a_star_len * c_star_len)
    cos_gamma_star = np.dot(a_star_vec, b_star_vec) / (a_star_len * b_star_len)

    # Clamp to [-1, 1] to handle numerical errors
    cos_alpha_star = np.clip(cos_alpha_star, -1.0, 1.0)
    cos_beta_star = np.clip(cos_beta_star, -1.0, 1.0)
    cos_gamma_star = np.clip(cos_gamma_star, -1.0, 1.0)

    alpha_star_deg = float(np.degrees(np.arccos(cos_alpha_star)))
    beta_star_deg = float(np.degrees(np.arccos(cos_beta_star)))
    gamma_star_deg = float(np.degrees(np.arccos(cos_gamma_star)))

    # Build a reciprocal cell using cctbx, then extract real-space parameters
    # cctbx.uctbx.unit_cell can be constructed from reciprocal parameters
    try:
        reciprocal_cell = uctbx.unit_cell(
            (a_star_len, b_star_len, c_star_len, alpha_star_deg, beta_star_deg, gamma_star_deg)
        )
        # The reciprocal() method returns the real-space cell
        real_cell = reciprocal_cell.reciprocal()
        params = real_cell.parameters()

        # Validate that the cell is not degenerate
        if any(p <= 0 for p in params[:3]):
            raise ValueError(
                f"Recovered cell has non-positive edge lengths: {params[:3]}"
            )

        return tuple(params)  # (a, b, c, alpha, beta, gamma)
    except Exception as exc:
        raise ValueError(
            f"Failed to recover unit cell from A* matrix. "
            f"Reciprocal params: a*={a_star_len:.6f}, b*={b_star_len:.6f}, "
            f"c*={c_star_len:.6f}, α*={alpha_star_deg:.2f}°, "
            f"β*={beta_star_deg:.2f}°, γ*={gamma_star_deg:.2f}°. "
            f"Error: {exc}"
        ) from exc


def derive_b_ideal_from_mosflm_a_star(a_star: np.ndarray, device: str = "cpu") -> np.ndarray:
    """
    Derive the effective reciprocal basis B_ideal from mapping MOSFLM A* matrix.

    This helper enables mapping-aligned Stage-A geometry by extracting the effective
    reciprocal cell encoded in the MOSFLM A* injection path. When Stage-A uses
    explicit cell+misset parameterization (crystal_overrides), the baseline misset
    must be computed against this mapping-derived B_ideal to ensure zero deltas
    reproduce the mapping zero-point geometry without strain artifacts.

    Per TORCH-REFINE-002E Phase C1 Branch G decision:
    - The mapping path injects MOSFLM A* directly into nanobrag_torch
    - The explicit Stage-A path derives U = A* @ B_ideal^{-1}
    - If B_ideal comes from dxtbx unit cell (old GEOMETRY-003), a symmetric strain
      of ~1.4e-3 appears because dxtbx cell ≠ effective MOSFLM cell
    - To close the gap, recover the effective cell from A* and build B_ideal from it

    Algorithm:
        1. Recover the effective unit cell (a, b, c, α, β, γ) from the A* matrix
           using cctbx (via recover_cell_from_a_star)
        2. Build a nanobrag_torch Crystal from that recovered cell (no MOSFLM injection)
        3. Extract B_ideal from nanobrag_torch's compute_cell_tensors()
        4. This B_ideal encodes the same effective cell as the mapping A*, ensuring
           that U = A*_mapping @ B_ideal^{-1} is a pure rotation (no strain)

    Args:
        a_star: 3×3 MOSFLM A* matrix from dxtbx crystal.get_A() (reshaped).
                Columns are reciprocal basis vectors (a*, b*, c*) in 1/Å.
        device: Torch device string for intermediate calculations (default: cpu).

    Returns:
        3×3 reciprocal basis B_ideal with columns (a*, b*, c*) in 1/Å.
        This is the **mapping-aligned B_ideal** that Stage-A must use to reproduce
        the mapping zero-point without strain.

    Raises:
        ValueError: If A* is singular, ill-conditioned, or cell recovery fails.

    References:
        - docs/spec-db-workflow.md:39 (Stage A mapping zero-point invariant)
        - plans/active/TORCH-REFINE-002E/implementation.md (Phase C1 Branch G)
        - docs/findings.md (GEOMETRY-003 extended per Phase C1)
    """
    # Validate input shape
    a_star = np.asarray(a_star, dtype=np.float64)
    if a_star.shape != (3, 3):
        raise ValueError(
            f"a_star must be a 3×3 array, got shape {a_star.shape}"
        )

    # Recover the effective unit cell from A*
    try:
        recovered_cell_params = recover_cell_from_a_star(a_star)
    except Exception as exc:
        raise ValueError(
            f"Failed to recover unit cell from A* matrix: {exc}"
        ) from exc

    # Build B_ideal from the recovered cell using nanobrag_torch
    try:
        from nanobrag_torch.config import CrystalConfig as TorchCrystalConfig
        from nanobrag_torch.models.crystal import Crystal as TorchCrystal
        import torch

        a, b, c, alpha, beta, gamma = recovered_cell_params
        cfg = TorchCrystalConfig(
            cell_a=a,
            cell_b=b,
            cell_c=c,
            cell_alpha=alpha,
            cell_beta=beta,
            cell_gamma=gamma,
            misset_deg=(0.0, 0.0, 0.0),
            mosflm_a_star=None,  # No MOSFLM injection for B_ideal
            mosflm_b_star=None,
            mosflm_c_star=None,
        )
        crystal_nb = TorchCrystal(cfg, device=torch.device(device), dtype=torch.float64)
        geom = crystal_nb.compute_cell_tensors()
        a_star_nb = geom["a_star"].detach().cpu().numpy().reshape(3)
        b_star_nb = geom["b_star"].detach().cpu().numpy().reshape(3)
        c_star_nb = geom["c_star"].detach().cpu().numpy().reshape(3)
        b_ideal = np.column_stack([a_star_nb, b_star_nb, c_star_nb]).astype(np.float64)
        return b_ideal
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "derive_b_ideal_from_mosflm_a_star requires nanobrag_torch and torch"
        ) from exc


def derive_u_matrix_from_mosflm_a_star(a_star: np.ndarray, cell: Tuple[float, float, float, float, float, float]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract U-matrix from mapping MOSFLM A* without SO(3) projection (GEOMETRY-004, TORCH-GEOMETRY-PARITY-002).

    Computes the orientation matrix U from the relationship A* = U @ B_ideal_reciprocal,
    where B_ideal_reciprocal is derived from the specified unit cell parameters.
    Unlike `derive_robust_misset`, this function does NOT call `proper_rotation()` or
    perform any SO(3) projection, preserving any symmetric strain embedded in the
    mapping MOSFLM A* matrix.

    This helper is required for Phase B (TORCH-GEOMETRY-PARITY-002) to enable direct
    U-matrix parameterization in Stage A refinement, avoiding the 1.37e-3 symmetric
    strain artifact introduced by the cell+misset decomposition path.

    Args:
        a_star: 3×3 MOSFLM A* matrix from dxtbx crystal.get_A() (reshaped).
                Columns are reciprocal basis vectors (a*, b*, c*) in 1/Å.
        cell: Tuple of 6 unit cell parameters (a, b, c, alpha, beta, gamma)
              where a, b, c are in Å and angles are in degrees.

    Returns:
        Tuple of (U_matrix, B_ideal_reciprocal), both 3×3 numpy arrays (dtype=float64).
        U_matrix: Orientation matrix from A* = U @ B_ideal relationship (may have det ≈ 1 ± ε if strain present).
        B_ideal_reciprocal: Ideal reciprocal cell matrix from TorchCrystal computation (same source as U extraction).

    Notes:
        - CONVERGENCE-001 bugfix: Both U and B_ideal are derived from the SAME TorchCrystal computation
          to ensure numerical consistency when reconstructing A* = U @ B_ideal.
        - Prior to this fix, callers independently computed B_ideal via cctbx, causing reconstruction errors
          and catastrophic forward model chi-squared (1.425B vs expected ~990k).

    Raises:
        ValueError: If a_star shape is invalid or B_ideal is singular.

    References:
        - docs/spec-db-workflow.md:39 (Stage A mapping zero-point invariant)
        - plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md:146 (Phase B1)
    """
    # Validate inputs
    a_star = np.asarray(a_star, dtype=np.float64)
    if a_star.shape != (3, 3):
        raise ValueError(
            f"a_star must be a 3×3 array, got shape {a_star.shape}"
        )

    # Extract cell parameters
    a, b, c, alpha, beta, gamma = cell

    # Build B_ideal_reciprocal using derive_b_ideal_from_mosflm_a_star logic
    # (recover cell from A*, then build nanobrag_torch B_ideal)
    # For U-matrix extraction, we use the provided cell directly instead of
    # recovering from A*, since the caller provides the authoritative cell.
    try:
        from nanobrag_torch.config import CrystalConfig as TorchCrystalConfig
        from nanobrag_torch.models.crystal import Crystal as TorchCrystal
        import torch

        # Build B_ideal from the provided cell
        cfg = TorchCrystalConfig(
            cell_a=a,
            cell_b=b,
            cell_c=c,
            cell_alpha=alpha,
            cell_beta=beta,
            cell_gamma=gamma,
            misset_deg=(0.0, 0.0, 0.0),
            mosflm_a_star=None,  # No MOSFLM injection for B_ideal
            mosflm_b_star=None,
            mosflm_c_star=None,
        )
        crystal_nb = TorchCrystal(cfg, device=torch.device("cpu"), dtype=torch.float64)
        geom = crystal_nb.compute_cell_tensors()
        a_star_nb = geom["a_star"].detach().cpu().numpy().reshape(3)
        b_star_nb = geom["b_star"].detach().cpu().numpy().reshape(3)
        c_star_nb = geom["c_star"].detach().cpu().numpy().reshape(3)
        B_ideal_reciprocal = np.column_stack([a_star_nb, b_star_nb, c_star_nb]).astype(np.float64)

    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "derive_u_matrix_from_mosflm_a_star requires nanobrag_torch and torch"
        ) from exc

    # Compute U = A* @ inv(B_ideal_reciprocal)
    # Do NOT call proper_rotation() or any SO(3) projection
    try:
        B_inv = np.linalg.inv(B_ideal_reciprocal)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            f"B_ideal_reciprocal is singular or ill-conditioned: {exc}"
        ) from exc

    U = a_star @ B_inv

    return U, B_ideal_reciprocal


def matrix_to_quaternion(U: Union[np.ndarray, 'torch.Tensor']) -> 'torch.Tensor':
    """
    Convert rotation matrix to quaternion using scipy convention ([x, y, z, w]).

    This helper enables quaternion-based U-matrix parameterization for Stage A
    (TORCH-GEOMETRY-PARITY-002 Phase B2). Uses scipy.spatial.transform.Rotation
    for robust conversion, then converts to torch.Tensor for autodiff.

    Args:
        U: 3×3 rotation matrix (numpy array or torch.Tensor).

    Returns:
        torch.Tensor of shape (4,) with quaternion in scipy convention [x, y, z, w].
        Dtype is float64 to match TORCH-GEOMETRY-PARITY-002 precision requirements.

    Raises:
        ImportError: If scipy is unavailable.
        ValueError: If U is not a valid 3×3 matrix.

    References:
        - plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md:148 (Phase B2)
        - input.md:45-46 (scipy convention and roundtrip validation)
    """
    try:
        from scipy.spatial.transform import Rotation
        import torch
    except ImportError as exc:
        raise ImportError(
            "matrix_to_quaternion requires scipy and torch"
        ) from exc

    # Convert to numpy if needed
    if hasattr(U, 'detach'):  # torch.Tensor
        U_np = U.detach().cpu().numpy()
    else:
        U_np = np.asarray(U, dtype=np.float64)

    if U_np.shape != (3, 3):
        raise ValueError(
            f"U must be a 3×3 matrix, got shape {U_np.shape}"
        )

    # Convert using scipy (returns [x, y, z, w])
    R = Rotation.from_matrix(U_np)
    q_np = R.as_quat()  # scipy convention: [x, y, z, w]

    # Convert to torch.Tensor with float64
    q_torch = torch.tensor(q_np, dtype=torch.float64)

    return q_torch


def quaternion_to_matrix(q: 'torch.Tensor') -> 'torch.Tensor':
    """
    Convert quaternion to rotation matrix using scipy convention ([x, y, z, w]).

    This helper enables quaternion-based U-matrix parameterization for Stage A
    (TORCH-GEOMETRY-PARITY-002 Phase B2). Uses scipy.spatial.transform.Rotation
    for robust conversion.

    Args:
        q: torch.Tensor of shape (4,) with quaternion in scipy convention [x, y, z, w].

    Returns:
        torch.Tensor of shape (3, 3) representing the rotation matrix.
        Dtype and device are preserved from input quaternion q.

    Raises:
        ImportError: If scipy is unavailable.
        ValueError: If q is not shape (4,).

    References:
        - plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md:148 (Phase B2)
        - input.md:45-46 (scipy convention and roundtrip validation)
    """
    try:
        from scipy.spatial.transform import Rotation
        import torch
    except ImportError as exc:
        raise ImportError(
            "quaternion_to_matrix requires scipy and torch"
        ) from exc

    # Validate shape
    if q.shape != (4,):
        raise ValueError(
            f"q must be a 4-element quaternion, got shape {q.shape}"
        )

    # Convert to numpy (scipy convention: [x, y, z, w])
    q_np = q.detach().cpu().numpy()

    # Convert using scipy
    R = Rotation.from_quat(q_np)  # scipy convention: [x, y, z, w]
    U_np = R.as_matrix()

    # Convert to torch.Tensor preserving dtype and device from input quaternion
    U_torch = torch.tensor(U_np, dtype=q.dtype, device=q.device)

    return U_torch


def derive_robust_misset(
    crystal_dxtbx,
    crystal_nanobrag_default: Optional[Any] = None,
    *,
    device=None,
    dtype=None,
    b_ideal_override: Optional[np.ndarray] = None,
    use_mapping_b_ideal: bool = False,
):
    """
    Derive robust misset angles (XYZ extrinsic Euler, degrees) mapping nanobrag's
    default orthogonalization to the dxtbx A* matrix.

    GEOMETRY-003 (mapping misset):
    - Let B_ideal be nanobrag_torch's default reciprocal basis constructed from
      the unit cell parameters (no MOSFLM injection, zero misset).
    - Let A* be the dxtbx reciprocal lattice matrix from crystal.get_A()
      (columns a*, b*, c* in 1/Å).
    - We seek U such that A* ≈ U @ B_ideal.
    - Compute U_raw = A* @ B_ideal^{-1}, project to the nearest proper rotation
      matrix R via SVD, then invert to XYZ Euler angles using the GEOMETRY-002
      convention:

          R = R_z(gamma) @ R_y(beta) @ R_x(alpha)
          phi_y = -asin(R[2,0])
          phi_x = atan2(R[2,1], R[2,2])
          phi_z = atan2(R[1,0], R[0,0])

    Args:
        crystal_dxtbx: dxtbx Crystal object providing get_A() and unit cell.
        crystal_nanobrag_default: Optional nanobrag_torch Crystal instance whose
            compute_cell_tensors() defines B_ideal. When None, a temporary
            CrystalConfig/Crystal is constructed from crystal_dxtbx's unit cell
            with MOSFLM injection disabled and misset_deg=[0,0,0].
        device: Optional torch.device or device-like string for the returned tensor.
        dtype: Optional torch dtype for the returned tensor.
        b_ideal_override: Optional 3×3 numpy array to use as B_ideal instead of
            deriving it from crystal_nanobrag_default. Enables Phase A2 testing
            of alternative B_ideal candidates (e.g., from recovered MOSFLM A* cell).
            When provided, crystal_nanobrag_default is ignored.
        use_mapping_b_ideal: If True, derive B_ideal from the MOSFLM A* matrix itself
            via derive_b_ideal_from_mosflm_a_star(), ensuring Stage-A explicit
            parameterization uses the same effective cell as the mapping path.
            This closes the 1.4e-3 symmetric strain gap (TORCH-REFINE-002E Phase C1).
            When True, both crystal_nanobrag_default and b_ideal_override are ignored.

    Returns:
        Baseline misset angles as either:
            - np.ndarray shape (3,) in degrees when device/dtype are None
            - torch.Tensor shape (3,) on (device, dtype) when both are provided

    Raises:
        ImportError: If nanobrag_torch or torch are unavailable.
        ValueError: If B_ideal is singular or ill-conditioned.
    """
    try:
        import torch
        from nanobrag_torch.config import CrystalConfig as TorchCrystalConfig
        from nanobrag_torch.models.crystal import Crystal as TorchCrystal
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "derive_robust_misset requires nanobrag_torch and torch. "
            f"Import failed: {exc}"
        ) from exc

    if device is None:
        device_t = torch.device("cpu")
    elif isinstance(device, torch.device):
        device_t = device
    else:
        device_t = torch.device(device)

    if dtype is None:
        dtype_t = torch.float64
    else:
        dtype_t = dtype

    # Determine B_ideal matrix
    if use_mapping_b_ideal:
        # Phase C1 Branch G: Derive B_ideal from the MOSFLM A* matrix itself
        # This ensures Stage-A explicit parameterization aligns with the mapping effective cell
        A_tuple = crystal_dxtbx.get_A()
        A_np = np.array(A_tuple, dtype=np.float64).reshape(3, 3)
        B_np = derive_b_ideal_from_mosflm_a_star(A_np, device=str(device_t))
    elif b_ideal_override is not None:
        # Phase A2: Use the override B_ideal directly (e.g., from recovered MOSFLM A* cell)
        B_np = np.asarray(b_ideal_override, dtype=np.float64)
        if B_np.shape != (3, 3):
            raise ValueError(
                f"b_ideal_override must be a 3×3 array, got shape {B_np.shape}"
            )
    elif isinstance(crystal_nanobrag_default, TorchCrystal):
        crystal_nb = crystal_nanobrag_default.to(device=device_t, dtype=dtype_t)
        geom = crystal_nb.compute_cell_tensors()
        a_star = geom["a_star"]
        b_star = geom["b_star"]
        c_star = geom["c_star"]
        # Stack reciprocal vectors into B_ideal with columns (a*, b*, c*)
        B_mat = torch.stack([a_star, b_star, c_star], dim=1)  # [3,3]
        B_np = B_mat.detach().cpu().numpy().astype(np.float64)
    else:
        # Build a default Crystal using the dxtbx unit cell with MOSFLM injection disabled
        a, b, c, alpha, beta, gamma = crystal_dxtbx.get_unit_cell().parameters()
        cfg = TorchCrystalConfig(
            cell_a=a,
            cell_b=b,
            cell_c=c,
            cell_alpha=alpha,
            cell_beta=beta,
            cell_gamma=gamma,
            misset_deg=(0.0, 0.0, 0.0),
            mosflm_a_star=None,
            mosflm_b_star=None,
            mosflm_c_star=None,
        )
        crystal_nb = TorchCrystal(cfg, device=device_t, dtype=dtype_t)
        geom = crystal_nb.compute_cell_tensors()
        a_star = geom["a_star"]
        b_star = geom["b_star"]
        c_star = geom["c_star"]
        # Stack reciprocal vectors into B_ideal with columns (a*, b*, c*)
        B_mat = torch.stack([a_star, b_star, c_star], dim=1)  # [3,3]
        B_np = B_mat.detach().cpu().numpy().astype(np.float64)

    # dxtbx A* matrix (columns a*, b*, c*)
    A_tuple = crystal_dxtbx.get_A()
    A_np = np.array(A_tuple, dtype=np.float64).reshape(3, 3)

    # Compute U_raw = A* @ B_ideal^{-1}
    try:
        B_inv = np.linalg.inv(B_np)
    except np.linalg.LinAlgError:
        # Fall back to pseudo-inverse to handle near-singular cases
        B_inv = np.linalg.pinv(B_np)

    U_raw = A_np @ B_inv

    # Project to the nearest proper rotation matrix via SVD
    U_u, _, U_vt = np.linalg.svd(U_raw)
    R = U_u @ U_vt
    if np.linalg.det(R) < 0:
        U_u[:, -1] *= -1.0
        R = U_u @ U_vt

    # Extract XYZ Euler angles in radians using GEOMETRY-002 convention
    phi_y_rad = -np.arcsin(np.clip(R[2, 0], -1.0, 1.0))
    phi_x_rad = np.arctan2(R[2, 1], R[2, 2])
    phi_z_rad = np.arctan2(R[1, 0], R[0, 0])

    misset_xyz_deg = np.array(
        [phi_x_rad, phi_y_rad, phi_z_rad], dtype=np.float64
    ) * (180.0 / np.pi)

    if device is not None and dtype is not None:
        return torch.tensor(misset_xyz_deg, dtype=dtype_t, device=device_t)

    return misset_xyz_deg


def derive_orientation_from_quaternion_delta(
    q_delta: "torch.Tensor",
    U_baseline: "torch.Tensor",
    dtype: "torch.dtype" = None,
    device: "torch.device" = None,
) -> "torch.Tensor":
    """
    Derive U(params) from quaternion-based incremental rotation ΔR.

    Formula:
        U(params) = ΔR(q_delta) @ U₀
    where:
        ΔR = quaternion_to_matrix(q_delta / ||q_delta||)

    Args:
        q_delta: Quaternion [w, x, y, z] (shape: (4,))
        U_baseline: Baseline orientation matrix U₀ from dxtbx (shape: (3, 3))
        dtype: Target dtype (spec-db-runtime.md:12 device/dtype neutrality)
        device: Target device

    Returns:
        U(params): Orientation matrix (shape: (3, 3))

    Spec Reference:
        - spec-db-core.md:58-60 (Incremental parameterization ΔR @ U₀)
        - DB-AT-026 Test 1: ||U(0) - U₀|| < 1e-12 for identity quaternion [1,0,0,0]

    Note:
        scipy.spatial.transform.Rotation uses [x,y,z,w] quaternion order.
        Our convention is [w,x,y,z].
        Conversion: R.from_quat([q[1], q[2], q[3], q[0]])
    """
    import torch
    from scipy.spatial.transform import Rotation as R

    # Infer dtype/device from input tensors if not provided
    if dtype is None:
        dtype = q_delta.dtype if hasattr(q_delta, 'dtype') else torch.float64
    if device is None:
        device = q_delta.device if hasattr(q_delta, 'device') else torch.device("cpu")

    # Ensure q_delta is a tensor
    if not isinstance(q_delta, torch.Tensor):
        q_delta = torch.tensor(q_delta, dtype=dtype, device=device)

    # 1. Normalize quaternion
    q_norm = q_delta / torch.linalg.norm(q_delta)

    # 2. Convert quaternion to rotation matrix ΔR (via scipy)
    #    CRITICAL: scipy uses [x,y,z,w] order; we use [w,x,y,z]
    q_np = q_norm.detach().cpu().numpy()
    delta_R_np = R.from_quat([q_np[1], q_np[2], q_np[3], q_np[0]]).as_matrix()
    delta_R = torch.tensor(delta_R_np, dtype=dtype, device=device)

    # 3. Ensure U_baseline on target dtype/device
    if not isinstance(U_baseline, torch.Tensor):
        U_baseline = torch.tensor(U_baseline, dtype=dtype, device=device)
    else:
        U_baseline = U_baseline.to(dtype=dtype, device=device)

    # 4. Compute U(params) = ΔR @ U₀
    U_params = delta_R @ U_baseline

    return U_params


def busing_levy_B_torch(
    a: "torch.Tensor",
    b: "torch.Tensor",
    c: "torch.Tensor",
    alpha_deg: "torch.Tensor",
    beta_deg: "torch.Tensor",
    gamma_deg: "torch.Tensor",
    dtype: "torch.dtype" = None,
    device: "torch.device" = None,
) -> "torch.Tensor":
    """
    Compute Busing-Levy reciprocal metric tensor B from cell parameters.

    This implementation uses cctbx.uctbx.unit_cell.fractionalization_matrix()
    and transposes it to match dxtbx crystal.get_B() convention (lower triangular
    with reciprocal vectors as columns).

    Args:
        a, b, c: Unit cell lengths (Ångströms)
        alpha_deg, beta_deg, gamma_deg: Unit cell angles (degrees)
        dtype: Target dtype
        device: Target device

    Returns:
        B: Reciprocal metric tensor (shape: (3, 3)), lower triangular

    Spec Reference:
        - spec-db-core.md:60 (Busing-Levy compatible metric tensor)
        - DB-AT-026 Test 2: ||B(0) - B₀|| < 1e-12 for zero deltas

    Note:
        dxtbx B-matrix convention: B = fractionalization_matrix().T
        where fractionalization_matrix is upper triangular.
    """
    import torch
    import numpy as np
    from cctbx import uctbx

    # Infer dtype/device from inputs if not provided
    if dtype is None:
        dtype = a.dtype if hasattr(a, 'dtype') else torch.float64
    if device is None:
        device = a.device if hasattr(a, 'device') else torch.device("cpu")

    # Extract scalar values (handle both tensors and scalars)
    a_val = float(a.item() if hasattr(a, 'item') else a)
    b_val = float(b.item() if hasattr(b, 'item') else b)
    c_val = float(c.item() if hasattr(c, 'item') else c)
    alpha_val = float(alpha_deg.item() if hasattr(alpha_deg, 'item') else alpha_deg)
    beta_val = float(beta_deg.item() if hasattr(beta_deg, 'item') else beta_deg)
    gamma_val = float(gamma_deg.item() if hasattr(gamma_deg, 'item') else gamma_deg)

    # Create cctbx unit cell
    uc = uctbx.unit_cell((a_val, b_val, c_val, alpha_val, beta_val, gamma_val))

    # Get fractionalization matrix (upper triangular)
    frac_mat = np.array(uc.fractionalization_matrix()).reshape(3, 3)

    # Transpose to get dxtbx B-matrix convention (lower triangular)
    B_np = frac_mat.T

    # Convert to PyTorch tensor with target dtype/device
    B = torch.tensor(B_np, dtype=dtype, device=device)

    return B


def derive_B_from_cell_deltas(
    delta_log_a: "torch.Tensor",
    delta_log_b: "torch.Tensor",
    delta_log_c: "torch.Tensor",
    delta_alpha_deg: "torch.Tensor",
    delta_beta_deg: "torch.Tensor",
    delta_gamma_deg: "torch.Tensor",
    cell_baseline: tuple,  # (a₀, b₀, c₀, α₀, β₀, γ₀)
    dtype: "torch.dtype" = None,
    device: "torch.device" = None,
) -> "torch.Tensor":
    """
    Derive B(params) from cell parameter deltas around baseline.

    Formula:
        a(params) = a₀ * exp(δlog_a)
        b(params) = b₀ * exp(δlog_b)
        c(params) = c₀ * exp(δlog_c)

        α(params) = α₀ + Δα  (degrees)
        β(params) = β₀ + Δβ
        γ(params) = γ₀ + Δγ

        B(params) = busing_levy_B_torch(a, b, c, α, β, γ)

    Args:
        delta_log_a/b/c: Log-perturbations for lengths
        delta_alpha/beta/gamma_deg: Angle deltas (degrees)
        cell_baseline: (a₀, b₀, c₀, α₀, β₀, γ₀) from crystal.get_unit_cell().parameters()
        dtype: Target dtype
        device: Target device

    Returns:
        B(params): Reciprocal metric tensor (shape: (3, 3))

    Spec Reference:
        - spec-db-core.md:58 (Cell perturbations via log-exp)
        - spec-db-workflow.md:36 (Trainable: logs/angles)
        - DB-AT-026 Test 2: ||B(0) - B₀|| < 1e-12 for zero deltas
    """
    import torch

    # Infer dtype/device from inputs if not provided
    if dtype is None:
        dtype = delta_log_a.dtype if hasattr(delta_log_a, 'dtype') else torch.float64
    if device is None:
        device = delta_log_a.device if hasattr(delta_log_a, 'device') else torch.device("cpu")

    a0, b0, c0, alpha0, beta0, gamma0 = cell_baseline

    # Baseline scalars → tensors on target dtype/device
    a0 = torch.tensor(a0, dtype=dtype, device=device)
    b0 = torch.tensor(b0, dtype=dtype, device=device)
    c0 = torch.tensor(c0, dtype=dtype, device=device)
    alpha0 = torch.tensor(alpha0, dtype=dtype, device=device)
    beta0 = torch.tensor(beta0, dtype=dtype, device=device)
    gamma0 = torch.tensor(gamma0, dtype=dtype, device=device)

    # Deltas → target dtype/device
    delta_log_a = torch.as_tensor(delta_log_a, dtype=dtype, device=device)
    delta_log_b = torch.as_tensor(delta_log_b, dtype=dtype, device=device)
    delta_log_c = torch.as_tensor(delta_log_c, dtype=dtype, device=device)
    delta_alpha_deg = torch.as_tensor(delta_alpha_deg, dtype=dtype, device=device)
    delta_beta_deg = torch.as_tensor(delta_beta_deg, dtype=dtype, device=device)
    delta_gamma_deg = torch.as_tensor(delta_gamma_deg, dtype=dtype, device=device)

    # Apply log-exp for lengths (ensures a,b,c > 0)
    a = a0 * torch.exp(delta_log_a)
    b = b0 * torch.exp(delta_log_b)
    c = c0 * torch.exp(delta_log_c)

    # Apply delta-add for angles
    alpha_deg = alpha0 + delta_alpha_deg
    beta_deg = beta0 + delta_beta_deg
    gamma_deg = gamma0 + delta_gamma_deg

    # Derive B via Busing-Levy
    B_params = busing_levy_B_torch(
        a, b, c, alpha_deg, beta_deg, gamma_deg, dtype=dtype, device=device
    )

    return B_params


def compute_baseline_misset_deg(
    crystal,
    baseline_crystal,
    *,
    device=None,
    dtype=None,
):
    """
    Compute baseline misset angles (XYZ extrinsic Euler, degrees) using a
    nanobrag_torch-aligned derivation.

    Updated per TORCH-REFINE-002E / GEOMETRY-003:
    - Let B_ideal be nanobrag_torch's default reciprocal basis constructed
      from the baseline crystal's unit cell (no MOSFLM injection, zero misset).
    - For a given dxtbx crystal with A* matrix A_crystal, define:
          U_crystal = A_crystal @ B_ideal^{-1}
      and project U_crystal to the nearest proper rotation matrix.
    - When baseline_crystal is provided, compute U_baseline from its A* matrix
      and return the Euler angles corresponding to:
          R_delta = U_crystal @ U_baseline^{-1}
      so the baseline misset encodes the rotation from baseline → crystal in
      nanobrag's XYZ convention.
    - When baseline_crystal is None, this helper returns the absolute misset
      of `crystal` relative to B_ideal (useful for mapping-aligned baselines).

    When device and dtype are provided (torch device / dtype), this returns a
    torch.Tensor on the requested device; otherwise it returns a numpy.ndarray
    of shape (3,) in degrees.
    """
    if crystal is None:
        return None

    if baseline_crystal is None:
        return derive_robust_misset(crystal, None, device=device, dtype=dtype)

    # Use the baseline crystal's unit cell to define B_ideal once, then compute
    # robust orientations for both baseline and perturbed crystals relative to
    # this shared frame so the delta is purely rotational.
    try:
        import torch
        from nanobrag_torch.config import CrystalConfig as TorchCrystalConfig
        from nanobrag_torch.models.crystal import Crystal as TorchCrystal
    except ImportError:
        # Fallback to legacy U-matrix-based derivation when nanobrag_torch is unavailable.
        # This path preserves prior behavior for environments without the torch backend.
        try:
            from scitbx.matrix import sqr  # type: ignore
        except Exception as exc:  # pragma: no cover - environment dependent
            raise ImportError(
                "compute_baseline_misset_deg requires scitbx.matrix.sqr when "
                "nanobrag_torch is unavailable; import failed: "
                f"{exc}"
            ) from exc

        U_baseline_tuple = baseline_crystal.get_U()
        U_perturbed_tuple = crystal.get_U()
        U_baseline = sqr(U_baseline_tuple)
        U_perturbed = sqr(U_perturbed_tuple)
        U_delta = U_perturbed * U_baseline.inverse()
        U_delta_np = np.array(U_delta).reshape(3, 3)

        phi_y_rad = -np.arcsin(np.clip(U_delta_np[2, 0], -1.0, 1.0))
        phi_x_rad = np.arctan2(U_delta_np[2, 1], U_delta_np[2, 2])
        phi_z_rad = np.arctan2(U_delta_np[1, 0], U_delta_np[0, 0])
        baseline_misset_xyz_deg = np.array(
            [phi_x_rad, phi_y_rad, phi_z_rad], dtype=np.float64
        ) * (180.0 / np.pi)

        if device is not None and dtype is not None:
            try:
                import torch as _torch  # type: ignore
            except ImportError:
                return baseline_misset_xyz_deg
            return _torch.tensor(baseline_misset_xyz_deg, dtype=dtype, device=device)

        return baseline_misset_xyz_deg

    # nanobrag_torch path: build a shared B_ideal from baseline_crystal
    if device is None:
        device_t = torch.device("cpu")
    elif isinstance(device, torch.device):
        device_t = device
    else:
        device_t = torch.device(device)

    if dtype is None:
        dtype_t = torch.float64
    else:
        dtype_t = dtype

    a_b, b_b, c_b, alpha_b, beta_b, gamma_b = baseline_crystal.get_unit_cell().parameters()
    baseline_cfg = TorchCrystalConfig(
        cell_a=a_b,
        cell_b=b_b,
        cell_c=c_b,
        cell_alpha=alpha_b,
        cell_beta=beta_b,
        cell_gamma=gamma_b,
        misset_deg=(0.0, 0.0, 0.0),
        mosflm_a_star=None,
        mosflm_b_star=None,
        mosflm_c_star=None,
    )
    baseline_nb = TorchCrystal(baseline_cfg, device=device_t, dtype=dtype_t)

    # Derive robust orientations for both crystals in the shared B_ideal frame
    misset_baseline = derive_robust_misset(
        baseline_crystal,
        crystal_nanobrag_default=baseline_nb,
        device=device_t,
        dtype=dtype_t,
    )
    misset_crystal = derive_robust_misset(
        crystal,
        crystal_nanobrag_default=baseline_nb,
        device=device_t,
        dtype=dtype_t,
    )

    # Convert to numpy for delta computation
    def _to_numpy(x):
        import numpy as _np
        try:
            import torch as _torch  # type: ignore
        except ImportError:  # pragma: no cover - torch-less environments
            return _np.asarray(x, dtype=_np.float64)
        if isinstance(x, _torch.Tensor):
            return x.detach().cpu().numpy().astype(_np.float64)
        return _np.asarray(x, dtype=_np.float64)

    misset_baseline_np = _to_numpy(misset_baseline).reshape(3)
    misset_crystal_np = _to_numpy(misset_crystal).reshape(3)
    baseline_misset_xyz_deg = (misset_crystal_np - misset_baseline_np).astype(
        np.float64
    )

    if device is not None and dtype is not None:
        return torch.tensor(baseline_misset_xyz_deg, dtype=dtype_t, device=device_t)

    return baseline_misset_xyz_deg


# ============================================================================
# Structure factor grid helper
# ============================================================================


def build_structure_factor_grid(indices, amplitudes, device=None, halo=False):
    """Build dense 3D HKL grid and ASU mapping for nanobrag_torch from MTZ reflections.

    Implements SCALE-001: Structure factors pass through unscaled.
    DiffBragg applies spot_scale_override internally to final intensities;
    applying it here would duplicate scaling and break parity.

    Args:
        indices: Miller indices array-like, shape (n_reflections, 3), dtype int
        amplitudes: Structure factor amplitudes |F|, shape (n_reflections,), dtype float
        device: torch device (optional; defaults to CPU if not provided)
        halo: bool (optional; default False). If True, adds a ±1 padding layer to each
            axis (h/k/l) to support tricubic interpolation without default_F fallback
            near grid boundaries (REFINE-005, TORCH-REFINE-002D). Padded cells are
            filled with zeros.

    Returns:
        tuple: (grid, metadata, asu_map) where
            - grid: torch.Tensor, shape (h_range, k_range, l_range), dtype float32
            - metadata: dict with HKL range, grid stats, coverage info, and 'has_halo' flag
            - asu_map: torch.Tensor, same shape as grid, dtype int32 with ASU indices or -1

    Raises:
        ImportError: If torch is not available

    Note:
        Per SCALE-001 (docs/findings.md:15), structure factors are NOT scaled by
        spot_scale_override. Scaling is applied post-simulation per SCALE-002.
        Per REFINE-005 (docs/findings.md:18), halo padding prevents tricubic
        interpolation from falling back to default_F near grid boundaries.
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
    # Base bounds from reflection data
    h_min_data, h_max_data = int(hkls[:, 0].min()), int(hkls[:, 0].max())
    k_min_data, k_max_data = int(hkls[:, 1].min()), int(hkls[:, 1].max())
    l_min_data, l_max_data = int(hkls[:, 2].min()), int(hkls[:, 2].max())

    # Apply ±1 halo if requested (TORCH-REFINE-002D, REFINE-005)
    # Halo padding prevents tricubic interpolation from falling back to default_F
    # near grid boundaries when fractional HKL indices land outside the data envelope
    halo_width = 1 if halo else 0
    h_min = h_min_data - halo_width
    h_max = h_max_data + halo_width
    k_min = k_min_data - halo_width
    k_max = k_max_data + halo_width
    l_min = l_min_data - halo_width
    l_max = l_max_data + halo_width

    h_range = h_max - h_min + 1
    k_range = k_max - k_min + 1
    l_range = l_max - l_min + 1

    # Allocate grid and ASU map on specified device (padded if halo enabled)
    grid = torch.zeros((h_range, k_range, l_range), device=device, dtype=torch.float32)
    asu_map = torch.full(
        (h_range, k_range, l_range), fill_value=-1, device=device, dtype=torch.int32
    )
    asu_lookup: Dict[Tuple[int, int, int], int] = {}
    next_asu_idx = 0

    def canonicalize_asu(h: int, k: int, l: int) -> Tuple[int, int, int]:
        """Map Friedel mates to a deterministic ASU representative."""
        if h > 0:
            return (h, k, l)
        if h < 0:
            return (-h, -k, -l)
        if k > 0:
            return (h, k, l)
        if k < 0:
            return (-h, -k, -l)
        if l >= 0:
            return (h, k, l)
        return (-h, -k, -l)

    if halo:
        logger.info(
            f"HKL grid with ±1 halo: h=[{h_min},{h_max}], k=[{k_min},{k_max}], l=[{l_min},{l_max}] "
            f"(data envelope: h=[{h_min_data},{h_max_data}], k=[{k_min_data},{k_max_data}], l=[{l_min_data},{l_max_data}])"
        )

    # Populate grid with structure factor amplitudes
    n_total = len(hkls)
    n_inrange = 0

    for (h, k, l), amp in zip(hkls, amps):
        idx_h = int(h - h_min)
        idx_k = int(k - k_min)
        idx_l = int(l - l_min)

        if 0 <= idx_h < h_range and 0 <= idx_k < k_range and 0 <= idx_l < l_range:
            grid[idx_h, idx_k, idx_l] = float(amp)
            canonical_hkl = canonicalize_asu(int(h), int(k), int(l))
            asu_idx = asu_lookup.get(canonical_hkl)
            if asu_idx is None:
                asu_idx = next_asu_idx
                asu_lookup[canonical_hkl] = asu_idx
                next_asu_idx += 1
            asu_map[idx_h, idx_k, idx_l] = asu_idx
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
        "has_halo": halo,  # TORCH-REFINE-002D: Flag for Stage B interpolation tests
        "n_unique_asu": len(asu_lookup),
    }

    return grid, metadata, asu_map


# ============================================================================
# Calibration metadata loader
# ============================================================================

def load_calibration_metadata(config_json_path):
    """Load DiffBragg calibration metadata from config_torch.json.

    Extracts spot_scale_override, beam flux/beamsize/exposure, and crystal N_cells
    from a canonical config_torch.json file produced by DiffBragg refinement. This
    metadata is required to align zero-iteration simulations with calibrated intensities.

    Args:
        config_json_path: Path to config_torch.json file containing DiffBragg metadata

    Returns:
        dict with keys:
            - spot_scale_override: float, DiffBragg scale factor (to be sqrt'ed per SCALE-002)
            - beam_flux: float, beam flux in photons/s
            - beam_exposure: float, exposure time in seconds
            - beamsize_mm: float or None, beam size in mm (optional)
            - N_cells: tuple of 3 ints or None, crystal mosaic domain counts (optional)

    Raises:
        FileNotFoundError: If config_json_path does not exist
        KeyError: If required fields (spot_scale_override, flux, exposure) are missing
        ValueError: If calibration values are invalid (non-positive or wrong shape)

    Notes:
        - Per SCALE-002 (docs/findings.md), sqrt(spot_scale_override) is applied post-simulation
        - Beam flux/exposure/beamsize and N_cells flow through to nanobrag_torch simulator configs
        - Config format matches plans/active/NANOBRAG-GOLDEN-001/reports/.../config_torch.json
    """
    import json
    from pathlib import Path

    config_path = Path(config_json_path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Calibration config not found: {config_json_path}. "
            f"Expected config_torch.json with DiffBragg metadata (spot_scale_override, beam flux/exposure)."
        )

    with open(config_path, "r") as f:
        config = json.load(f)

    # Extract spot_scale_override from crystal section
    try:
        spot_scale_override = float(config["crystal"]["scale_override"])
    except (KeyError, TypeError) as e:
        raise KeyError(
            f"Missing crystal.scale_override in {config_json_path}. "
            f"Expected DiffBragg calibration metadata. Error: {e}"
        )

    # Extract beam flux and exposure (informational)
    try:
        beam_flux = float(config["beam"]["flux"])
        beam_exposure = float(config["beam"]["exposure"])
    except (KeyError, TypeError) as e:
        raise KeyError(
            f"Missing beam.flux or beam.exposure in {config_json_path}. "
            f"Expected DiffBragg beam metadata. Error: {e}"
        )

    # Validate calibration values are positive
    if spot_scale_override <= 0:
        raise ValueError(
            f"Invalid spot_scale_override={spot_scale_override}. Must be positive per SCALE-002."
        )
    if beam_flux <= 0 or beam_exposure <= 0:
        raise ValueError(
            f"Invalid beam metadata: flux={beam_flux}, exposure={beam_exposure}. Must be positive."
        )

    # Extract beam beamsize (optional, with fallback)
    try:
        beamsize_mm = float(config["beam"]["beamsize_mm"])
    except (KeyError, TypeError):
        beamsize_mm = None  # Will use BeamConfig default if not provided

    # Extract crystal N_cells (optional, with fallback)
    try:
        N_cells_list = config["crystal"]["N_cells"]
        N_cells = tuple(int(x) for x in N_cells_list)
        if len(N_cells) != 3:
            raise ValueError(f"N_cells must have 3 elements, got {len(N_cells)}")
    except (KeyError, TypeError):
        N_cells = None  # Will use CrystalConfig default if not provided

    return {
        "spot_scale_override": spot_scale_override,
        "beam_flux": beam_flux,
        "beam_exposure": beam_exposure,
        "beamsize_mm": beamsize_mm,
        "N_cells": N_cells,
    }


def load_refined_mtz(mtz_path, column="F"):
    """Load refined structure factors from DiffBragg-refined MTZ file.

    Reads Miller indices and refined amplitudes from an MTZ file produced by
    DiffBragg refinement (e.g., refined_structure_factors.mtz). These refined
    Fopt values are typically ~94k× smaller than raw MTZ amplitudes and are
    required for zero-iteration mapping tests per SCALE-003/SCALE-004.

    Args:
        mtz_path: Path to refined MTZ file (e.g., "refined_structure_factors.mtz")
        column: MTZ column name for structure factor amplitudes (default "F")

    Returns:
        tuple: (indices, amplitudes) where:
            - indices: numpy array of Miller indices, shape (n_refl, 3), dtype int
            - amplitudes: numpy array of refined |F| values, shape (n_refl,), dtype float32

    Raises:
        FileNotFoundError: If mtz_path does not exist
        ImportError: If iotbx.mtz is not available
        ValueError: If MTZ file is invalid or column is missing

    Notes:
        - Per SCALE-001, amplitudes are returned unscaled (no sqrt(spot_scale) multiplication)
        - Per SCALE-003/SCALE-004, these refined amplitudes must be used with calibration
          metadata (spot_scale_override) to achieve mapping thresholds
        - MTZ format matches DiffBragg output: column root "F" with (+)/(-) Friedel pairs
        - Returns CPU numpy arrays (device-neutral per runtime checklist)

    Example:
        >>> indices, amps = load_refined_mtz("tests/fixtures/.../refined_structure_factors.mtz")
        >>> bragg, diag = simulate_forward_once(..., hkl_indices=indices, hkl_amplitudes=amps)
    """
    from pathlib import Path

    mtz_file = Path(mtz_path)
    if not mtz_file.exists():
        raise FileNotFoundError(
            f"Refined MTZ not found: {mtz_path}. "
            f"Expected DiffBragg-refined structure factors for parity testing."
        )

    try:
        from iotbx import mtz as iotbx_mtz
    except ImportError as e:
        raise ImportError(
            f"iotbx.mtz is required to read MTZ files. Import error: {e}"
        )

    # Read MTZ object
    try:
        mtz_obj = iotbx_mtz.object(str(mtz_file))
    except Exception as e:
        raise ValueError(
            f"Failed to parse MTZ file {mtz_path}. "
            f"Expected valid DiffBragg-refined MTZ. Error: {e}"
        )

    # Extract Miller array for specified column
    # DiffBragg writes with column_root_label="F", creating F(+),SIGF(+),F(-),SIGF(-) labels
    try:
        miller_arrays = mtz_obj.as_miller_arrays()
        # Find array matching column label
        # For DiffBragg MTZ: label is "F(+),SIGF(+),F(-),SIGF(-)" and type is "amplitude"
        # We want the amplitude array (not just SIGF)
        f_array = None
        for ma in miller_arrays:
            label = ma.info().label_string()
            type_hints = str(ma.info().type_hints_from_file)
            # Check if this is an amplitude array (not just sigma)
            # The label will contain both F and SIGF, but type_hints should be "amplitude"
            if column in label and "amplitude" in type_hints:
                f_array = ma
                break

        if f_array is None:
            available_labels = [
                f"{ma.info().label_string()} (type: {ma.info().type_hints_from_file})"
                for ma in miller_arrays
            ]
            raise ValueError(
                f"Column '{column}' with type 'amplitude' not found in {mtz_path}. "
                f"Available arrays: {available_labels}"
            )

    except Exception as e:
        raise ValueError(
            f"Failed to extract structure factors from {mtz_path}. Error: {e}"
        )

    # Extract indices and amplitudes
    indices = np.array(f_array.indices(), dtype=np.int32)  # shape (n_refl, 3)
    amplitudes = np.array(f_array.data(), dtype=np.float32)  # shape (n_refl,)

    # Validate shapes
    if indices.ndim != 2 or indices.shape[1] != 3:
        raise ValueError(
            f"Invalid Miller indices shape: {indices.shape}. Expected (n_refl, 3)."
        )
    if amplitudes.ndim != 1 or len(amplitudes) != len(indices):
        raise ValueError(
            f"Invalid amplitudes shape: {amplitudes.shape}. "
            f"Expected ({len(indices)},) to match indices."
        )

    return indices, amplitudes


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
    calibration: Optional[dict] = None,
    hkl_source: Optional[str] = None,
    hkl_path: Optional[str] = None,
    device=None,
    sigma_floor_value: float = 1.0,
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
        spot_scale_override: Optional scale factor (default 1.0 if None).
                           DEPRECATED: Use calibration dict instead.
                           For calibrated simulations, source from DiffBragg
                           metadata via load_calibration_metadata().
        calibration: Optional dict from load_calibration_metadata() containing:
                    - spot_scale_override: Scale factor (overrides spot_scale_override param)
                    - beam_flux: Beam flux in photons/s
                    - beam_exposure: Exposure time in seconds
                    - beamsize_mm: Beam size in mm (optional)
                    - N_cells: Crystal mosaic domain counts (optional)
        hkl_source: Optional telemetry tag ("refined" or "raw") for MTZ provenance
        hkl_path: Optional path to MTZ file for diagnostics
        device: torch.device for simulation (default cpu)
        sigma_floor_value: Variance floor (sigma_floor) in target units (photons or ADU).

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
            - n_cells_applied: Bool indicating whether N_cells was passed to CrystalConfig
            - bragg_stats: Dict with min/max/mean of bragg output
            - hkl_stats: HKL grid metadata from build_structure_factor_grid
            - hkl_telemetry: Dict with structure-factor metadata:
                - hkl_source: "refined" or "raw" (or None if not provided)
                - hkl_n_reflections: Number of reflections
                - hkl_mean_amplitude: Mean structure factor amplitude
                - hkl_path: Path to MTZ file (or empty string if not provided)
            - chi_squared: Variance-weighted chi-squared sum (spec-db-core.md:57-68)
            - sigma_floor_value: Variance floor (sigma_floor) used in diagnostics
            - variance_floor_clamp_fraction: Fraction of masked pixels clamped to sigma_floor^2

    Raises:
        ImportError: If nanobrag_torch is not available
        ValueError: If config creation fails or simulation errors

    Notes:
        - Honors RUNTIME-001 (NANOBRAGG_DISABLE_COMPILE=1 recommended)
        - Applies SCALE-001 (unscaled HKL grid) and SCALE-002 (post-sim scaling)
        - Applies GEOMETRY-002 (analytic Euler inversion in create_detector_config)
        - Applies SCALE-005 (N_cells enabled when calibration provides domain counts)
        - Device-neutral design: defaults to CPU, respects passed device
        - Does not write HDF5 or persist artifacts (caller's responsibility)
        - Calibration dict sources beam flux/exposure/beamsize per SCALE-003
        - beam_config propagated to Simulator for sample clipping (2025-11-04T185107Z)
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
    hkl_grid, hkl_metadata, asu_map = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device
    )

    # Extract calibration values if provided (SCALE-003)
    # Calibration dict takes precedence over spot_scale_override parameter
    if calibration is not None:
        spot_scale_override = calibration.get('spot_scale_override', spot_scale_override)
        beam_flux = calibration.get('beam_flux')
        beam_exposure = calibration.get('beam_exposure')
        beamsize_mm = calibration.get('beamsize_mm')
        N_cells = calibration.get('N_cells')
    else:
        beam_flux = None
        beam_exposure = None
        beamsize_mm = None
        N_cells = None

    # Determine spot scale override (SCALE-002)
    if spot_scale_override is None:
        spot_scale_override = 1.0
    sqrt_spot_scale = np.sqrt(spot_scale_override)

    # Prepare configs (shared across panels where applicable)
    # Build beam_config with calibration overrides (input.md Do Now step 4)
    beam_config = create_beam_config(
        beam,
        flux=beam_flux,
        beamsize_mm=beamsize_mm,
        exposure=beam_exposure
    )

    # Build crystal_config with N_cells gating per SCALE-005
    # Enable apply_n_cells when calibration provides N_cells (sample clipping via beam_config)
    # Per 2025-11-04T185107Z analysis: N_cells + beam sample clipping recovers parity
    apply_n_cells = N_cells is not None
    crystal_config, n_cells_applied = create_crystal_config(
        crystal,
        experiment,
        N_cells=N_cells,
        apply_n_cells=apply_n_cells
    )

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

        # Instantiate models (input.md Do Now step 4: wire beam_config to TorchCrystal)
        detector_model = TorchDetector(detector_config, device=device)
        crystal_model = TorchCrystal(
            crystal_config,
            beam_config=beam_config,
            device=device
        )

        # Attach HKL data to crystal model
        crystal_model.hkl_data = hkl_grid
        crystal_model.hkl_metadata = hkl_metadata

        # Run simulator (single source, GEOMETRY-002/HKL-ORIENT-001 applied in bridge)
        # Per input.md Do Now: propagate beam_config for sample clipping when N_cells is enabled
        simulator = Simulator(
            detector=detector_model,
            crystal=crystal_model,
            beam_config=beam_config,
            device=device
        )
        panel_output = simulator.run()  # Returns torch.Tensor on device

        # Move to CPU and convert to numpy
        panel_output_np = panel_output.cpu().detach().numpy().astype(np.float32)

        # Apply sqrt(spot_scale_override) post-simulation (SCALE-002)
        panel_output_scaled = panel_output_np * sqrt_spot_scale

        # Store in bragg array
        bragg[panel_id] = panel_output_scaled

    # Compute pre-scale Bragg statistics (before SCALE-002 sqrt adjustment)
    # This is the raw simulator output divided by sqrt_spot_scale
    bragg_raw = bragg / sqrt_spot_scale if sqrt_spot_scale != 0.0 else bragg
    bragg_raw_mean = float(bragg_raw.mean())
    bragg_raw_max = float(bragg_raw.max())

    # Compute target mean over loss mask (background-subtracted data in ROIs)
    target_masked = inputs.target[inputs.loss_mask]
    target_mean_masked = float(target_masked.mean()) if len(target_masked) > 0 else float('nan')

    # Compute derived ratios: target/bragg for scale alignment analysis
    # Use masked mean to exclude sentinel/invalid pixels
    bragg_mean_masked = float(bragg[inputs.loss_mask].mean()) if inputs.loss_mask.sum() > 0 else float('nan')
    target_bragg_mean_ratio = target_mean_masked / bragg_mean_masked if bragg_mean_masked != 0.0 and not np.isnan(bragg_mean_masked) else float('nan')

    # Also compute raw (pre-scale) ratios for forensics
    bragg_raw_mean_masked = float(bragg_raw[inputs.loss_mask].mean()) if inputs.loss_mask.sum() > 0 else float('nan')
    target_bragg_raw_mean_ratio = target_mean_masked / bragg_raw_mean_masked if bragg_raw_mean_masked != 0.0 and not np.isnan(bragg_raw_mean_masked) else float('nan')

    if sigma_floor_value <= 0:
        raise ValueError(
            f"sigma_floor_value must be > 0 (got {sigma_floor_value}). "
            "Per spec-db-core.md:67 the variance floor enforces a physical lower bound."
        )

    # Compute diagnostics
    masked_pixels = int(inputs.loss_mask.sum())
    target_float = inputs.target.astype(np.float64)
    bragg_float = bragg.astype(np.float64)
    masked_diff = np.where(inputs.loss_mask, target_float - bragg_float, 0.0)
    masked_mse = float((masked_diff ** 2).sum() / masked_pixels) if masked_pixels > 0 else float('nan')

    sigma_floor_sq = float(sigma_floor_value ** 2)
    sigma_sq = inputs.sigma_readout.astype(np.float64) ** 2
    variance_raw = bragg_float + sigma_sq
    variance = np.maximum(variance_raw, sigma_floor_sq)
    diff_sq = (bragg_float - target_float) ** 2
    weighted = diff_sq / variance
    chi_squared = float(weighted[inputs.loss_mask].sum()) if masked_pixels > 0 else float('nan')
    clamp_pixels = int(np.logical_and(inputs.loss_mask, variance_raw < sigma_floor_sq).sum())
    clamp_fraction = float(clamp_pixels / masked_pixels) if masked_pixels > 0 else 0.0

    sigma_values = inputs.sigma_readout[inputs.loss_mask]
    if sigma_values.size == 0:
        sigma_values = inputs.sigma_readout.reshape(-1)
    sigma_reference_value = float(np.median(sigma_values)) if sigma_values.size > 0 else float("nan")

    diagnostics = {
        "masked_mse": masked_mse,
        "loss_mask_coverage": float(inputs.loss_mask.mean()),
        "n_rois": len(inputs.panel_slices),
        "target_shape": str(inputs.target.shape),
        "global_scale_hint": inputs.global_scale_hint,
        "spot_scale_override": float(spot_scale_override),
        "sqrt_spot_scale": float(sqrt_spot_scale),
        "n_cells_applied": n_cells_applied,  # input.md Do Now step 4: track whether N_cells was used
        "bragg_stats": {
            "min": float(bragg.min()),
            "max": float(bragg.max()),
            "mean": float(bragg.mean())
        },
        "bragg_raw_stats": {
            "mean": bragg_raw_mean,
            "max": bragg_raw_max
        },
        "target_stats": {
            "mean_masked": target_mean_masked
        },
        "target_bragg_ratios": {
            "mean_ratio_scaled": target_bragg_mean_ratio,
            "mean_ratio_raw": target_bragg_raw_mean_ratio
        },
        "hkl_stats": hkl_metadata,
        "hkl_telemetry": {
            "hkl_source": hkl_source if hkl_source is not None else None,
            "hkl_n_reflections": len(hkl_indices),
            "hkl_mean_amplitude": float(hkl_amplitudes.mean()),
            "hkl_path": hkl_path if hkl_path is not None else ""
        },
        "chi_squared": chi_squared,
        "sigma_floor_value": float(sigma_floor_value),
        "variance_floor_clamp_fraction": clamp_fraction,
        "variance_floor_masked_pixels": masked_pixels,
        "variance_floor_clamped_pixels": clamp_pixels,
        "sigma_readout_provenance": inputs.sigma_readout_provenance,
        "sigma_readout_reference_value": sigma_reference_value,
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
    dtype=None,
    crystal_overrides: Optional[dict] = None
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
        crystal_overrides: Optional dict of tensor-valued crystal parameter overrides
                          for gradcheck. Supports keys: 'cell_a', 'cell_b', 'cell_c',
                          'cell_alpha', 'cell_beta', 'cell_gamma'. Tensors must have
                          requires_grad=True to preserve gradient flow (GRADIENT-001).

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
        - GRADIENT-001: crystal_overrides enables tensor-valued parameter injection without
                       .item()/.numpy() detaching, preserving autograd graph for gradcheck
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
    hkl_grid, hkl_metadata, asu_map = build_structure_factor_grid(
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
    # simulate_forward_torch doesn't use calibration, so apply_n_cells=True (default)
    # is fine for gradient testing; N_cells will be None anyway
    crystal_config, _ = create_crystal_config(crystal, experiment)

    # Apply crystal_overrides if provided (GRADIENT-001)
    # This allows tensor-valued parameters to flow through without .item() detaching
    if crystal_overrides is not None:
        # Get base unit cell parameters
        a, b, c, alpha, beta, gamma = crystal.get_unit_cell().parameters()

        # Override with tensor values (keep as torch tensors for autograd)
        if 'cell_a' in crystal_overrides:
            a = crystal_overrides['cell_a']
        if 'cell_b' in crystal_overrides:
            b = crystal_overrides['cell_b']
        if 'cell_c' in crystal_overrides:
            c = crystal_overrides['cell_c']
        if 'cell_alpha' in crystal_overrides:
            alpha = crystal_overrides['cell_alpha']
        if 'cell_beta' in crystal_overrides:
            beta = crystal_overrides['cell_beta']
        if 'cell_gamma' in crystal_overrides:
            gamma = crystal_overrides['cell_gamma']

        # Rebuild crystal_config with possibly-tensor unit cell params
        # CrystalConfig accepts numeric values, torch tensors should work
        crystal_config.cell_a = a
        crystal_config.cell_b = b
        crystal_config.cell_c = c
        crystal_config.cell_alpha = alpha
        crystal_config.cell_beta = beta
        crystal_config.cell_gamma = gamma

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

        # Instantiate models (wire beam_config for consistency with simulate_forward_once)
        detector_model = TorchDetector(detector_config, device=device)
        crystal_model = TorchCrystal(
            crystal_config,
            beam_config=beam_config,
            device=device,
            dtype=dtype
        )

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
    mask: "torch.Tensor",
    sigma_readout: Optional["torch.Tensor"] = None
) -> "torch.Tensor":
    """
    Compute variance-weighted chi-squared loss for gradient-based optimization.

    Implements spec-db-core.md:57-68 variance model when sigma_readout is provided:
    - Variance: V = I_model.detach() + sigma_readout^2 (Poisson + readout noise)
    - Loss: Sum((I_model - I_obs)^2 / V) over masked pixels
    - Detached denominator implements IRLS (prevents "attraction to zero")

    When sigma_readout is None, falls back to masked MSE (legacy behavior).

    Args:
        prediction: Predicted Bragg intensities [panel, slow, fast], torch.Tensor
        target: Target intensities [panel, slow, fast], torch.Tensor
        mask: Loss mask [panel, slow, fast], torch.Tensor with dtype bool or numeric
        sigma_readout: Optional readout noise [panel, slow, fast], torch.Tensor in target units.
                      When provided, computes variance-weighted chi-squared loss per spec-db-core.md.
                      When None, falls back to masked MSE (legacy).

    Returns:
        loss: Scalar tensor with variance-weighted chi-squared (or MSE if sigma_readout=None)

    Raises:
        ValueError: If shapes don't match or mask has no valid pixels

    Notes:
        - Preserves gradient graph (no .detach() or numpy conversions except variance term)
        - Respects SCALE-002: target/prediction must have same post-simulation scaling
        - Returns scalar tensor suitable for torch.autograd.gradcheck
        - Mask expected to be boolean or numeric (0/1); numeric values treated as weights
        - PHYSICS-LOSS-001: Variance-weighted loss is the normative path per spec-db-core.md:57
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
    if sigma_readout is not None and sigma_readout.shape != prediction.shape:
        raise ValueError(
            f"sigma_readout shape {sigma_readout.shape} doesn't match prediction shape {prediction.shape}"
        )

    # Ensure mask is boolean
    if mask.dtype != torch.bool:
        mask = mask.bool()

    # Check for valid mask pixels
    n_valid = mask.sum()
    if n_valid == 0:
        raise ValueError("Loss mask contains no valid pixels")

    # Compute squared error numerator
    squared_error = (prediction - target) ** 2

    if sigma_readout is not None:
        # Variance-weighted chi-squared loss (spec-db-core.md:57-68)
        # Variance = I_model.detach() + sigma_readout^2 (Poisson + readout noise in quadrature)
        # Detach denominator to prevent "attraction to zero" (IRLS approach)
        variance = torch.clamp(prediction.detach() + sigma_readout**2, min=1e-12)

        # Chi-squared: Sum((I_model - I_obs)^2 / V) over masked pixels
        weighted_squared_error = squared_error / variance
        masked_weighted_error = torch.where(mask, weighted_squared_error, torch.zeros_like(weighted_squared_error))

        # Sum over valid pixels (chi-squared is a sum, not a mean)
        loss = masked_weighted_error.sum()
    else:
        # Legacy MSE fallback (when sigma_readout not provided)
        masked_squared_error = torch.where(mask, squared_error, torch.zeros_like(squared_error))

        # Mean over valid pixels
        loss = masked_squared_error.sum() / n_valid.to(prediction.dtype)

    return loss
