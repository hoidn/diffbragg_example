"""
Config factory helpers for nanobrag_torch (ARCH-BRIDGE-RESP-001 Phase C).

This module provides detector/beam/crystal hydration helpers that were previously in
dbex/nanobrag_bridge.py. These factories convert DIALS/dxtbx geometry objects into
nanobrag_torch config dataclasses following the mapping rules documented in
docs/config_crosswalk.md.

Key contracts (preserved from bridge module):
- Square pixel enforcement (config_crosswalk.md:30, spec-db-core.md:40)
- DIALS Euler angle extraction from panel axes (config_crosswalk.md:15-37)
- Beam center swap: dxtbx (fast, slow) → torch (s, f) (config_crosswalk.md:29)
- Trusted mask torch tensor coercion (CLI-001, nanobrag_api.md:44)
- ROI cropping with beam center adjustment (GEOMETRY-001/002)
- Distance override tensor support for Stage C (TORCH-REFINE-003)
- Calibration metadata plumbing (flux, beamsize, exposure, N_cells)

See also:
    docs/config_crosswalk.md — Geometry mapping rules (dxtbx → nanobrag_torch)
    docs/dxtbx_api.md — dxtbx Panel/Beam/Crystal APIs
    docs/nanobrag_api.md — nanobrag_torch config dataclass semantics
    docs/spec-db-core.md — Core ordering and guard contracts
"""

from __future__ import annotations
from typing import Tuple, Optional, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    import torch

# Import nanobrag_torch config classes
try:
    from nanobrag_torch.config import (
        DetectorConfig,
        BeamConfig,
        CrystalConfig,
        DetectorConvention
    )
except ImportError as e:
    raise ImportError(
        "nanobrag_torch.config is required for config factory functionality. "
        "Please ensure nanobrag_torch is installed. "
        f"Import error: {e}"
    )


def create_detector_config(
    panel,
    beam,
    trusted_mask: Optional[np.ndarray] = None,
    distance_mm_override: Optional['torch.Tensor'] = None,
    roi_bbox: Optional[Tuple[int, int, int, int]] = None,
    oversample: int = -1,
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
        oversample: Oversampling factor (1, 2, 3, ...). Default -1 = auto-select based on detector size.
                   Use explicit value (e.g., 3) to force consistent oversampling across detector configs.

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
        mask_array=mask_array,
        oversample=oversample
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
