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
from enum import Enum
import numpy as np


# ============================================================================
# Config dataclass stubs matching nanobrag_torch API
# These will be replaced with actual imports when nanobrag_torch is available
# ============================================================================

class DetectorConvention(Enum):
    """Detector convention enum stub matching nanobrag_torch."""
    CUSTOM = "CUSTOM"


@dataclass
class DetectorConfig:
    """
    Detector configuration stub matching nanobrag_torch.config.DetectorConfig.

    Per docs/nanobrag_api.md:23-39 and docs/config_crosswalk.md:15-37.
    """
    # Distance and pixel metrics
    distance_mm: float
    pixel_size_mm: float
    spixels: int
    fpixels: int

    # Beam center (explicit, no MOSFLM +0.5px offset)
    beam_center_s: float  # slow direction, mm
    beam_center_f: float  # fast direction, mm
    beam_center_source: str = "explicit"

    # CUSTOM convention vectors
    detector_convention: DetectorConvention = DetectorConvention.CUSTOM
    custom_fdet_vector: np.ndarray = field(default_factory=lambda: np.array([1., 0., 0.]))
    custom_sdet_vector: np.ndarray = field(default_factory=lambda: np.array([0., 1., 0.]))
    custom_odet_vector: np.ndarray = field(default_factory=lambda: np.array([0., 0., 1.]))
    custom_beam_vector: np.ndarray = field(default_factory=lambda: np.array([0., 0., 1.]))

    # Mask (0/1 float)
    mask_array: Optional[np.ndarray] = None


@dataclass
class BeamConfig:
    """
    Beam configuration stub matching nanobrag_torch.config.BeamConfig.

    Per docs/nanobrag_api.md:52-58 and docs/config_crosswalk.md:39-53.
    """
    wavelength_A: float

    # Polarization (parity defaults)
    polarization_factor: float = 0.0
    nopolar: bool = False
    polarization_axis: np.ndarray = field(default_factory=lambda: np.array([0., 0., 1.]))
    polarization_fraction: float = 0.999

    # Resolution cutoff
    dmin: float = 0.0


@dataclass
class CrystalConfig:
    """
    Crystal configuration stub matching nanobrag_torch.config.CrystalConfig.

    Per docs/nanobrag_api.md:41-50 and docs/config_crosswalk.md:55-72.
    """
    # Unit cell (Angstroms and degrees)
    cell_a: float
    cell_b: float
    cell_c: float
    cell_alpha: float  # degrees
    cell_beta: float   # degrees
    cell_gamma: float  # degrees

    # MOSFLM A* orientation (1/Angstrom)
    mosflm_a_star: np.ndarray = field(default_factory=lambda: np.array([1., 0., 0.]))
    mosflm_b_star: np.ndarray = field(default_factory=lambda: np.array([0., 1., 0.]))
    mosflm_c_star: np.ndarray = field(default_factory=lambda: np.array([0., 0., 1.]))

    # Misset angles (extrinsic XYZ rotations after MOSFLM injection)
    misset_deg: np.ndarray = field(default_factory=lambda: np.array([0., 0., 0.]))

    # Stills defaults
    phi_steps: int = 1
    osc_range_deg: float = 0.0
    mosaic_domains: int = 1
    mosaic_spread_deg: float = 0.0


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
    - Sample->source vector: -s0/||s0||
    - CUSTOM convention with explicit basis vectors
    - Square pixel guard
    - Mask array conversion to float (1=include, 0=exclude)

    Args:
        panel: dxtbx Panel object
        beam: dxtbx Beam object
        trusted_mask: Optional boolean mask [slow, fast], True=include

    Returns:
        DetectorConfig with geometry, beam center, and mask

    Raises:
        ValueError: If pixels are not square
    """
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
    # (config_crosswalk.md:29)
    fast_mm, slow_mm = panel.get_beam_centre(beam.get_s0())
    beam_center_s = slow_mm
    beam_center_f = fast_mm

    # Basis vectors (config_crosswalk.md:24-26)
    custom_fdet_vector = np.array(panel.get_fast_axis())
    custom_sdet_vector = np.array(panel.get_slow_axis())
    custom_odet_vector = np.array(panel.get_normal())

    # Sample->source beam vector: -s0/||s0|| (config_crosswalk.md:27)
    s0 = np.array(beam.get_s0())
    custom_beam_vector = -s0 / np.linalg.norm(s0)

    # Mask array: convert bool to float (config_crosswalk.md:33)
    mask_array = None
    if trusted_mask is not None:
        mask_array = trusted_mask.astype(np.float32)

    return DetectorConfig(
        distance_mm=distance_mm,
        pixel_size_mm=px_fast_mm,
        spixels=slow_px,
        fpixels=fast_px,
        beam_center_s=beam_center_s,
        beam_center_f=beam_center_f,
        beam_center_source="explicit",
        detector_convention=DetectorConvention.CUSTOM,
        custom_fdet_vector=custom_fdet_vector,
        custom_sdet_vector=custom_sdet_vector,
        custom_odet_vector=custom_odet_vector,
        custom_beam_vector=custom_beam_vector,
        mask_array=mask_array
    )


def create_beam_config(beam) -> BeamConfig:
    """
    Create BeamConfig from dxtbx beam.

    Implements beam mapping per docs/config_crosswalk.md:39-53:
    - Wavelength in Angstroms
    - Polarization factor=0.0 for parity
    - Polarization axis/fraction from metadata or fallback defaults

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
        polarization_axis = np.array(beam.get_polarization_normal())
        polarization_fraction = beam.get_polarization_fraction()
    except (AttributeError, TypeError):
        # Fallback defaults
        polarization_axis = np.array([0.0, 0.0, 1.0])
        polarization_fraction = 0.999

    return BeamConfig(
        wavelength_A=wavelength_A,
        polarization_factor=0.0,  # Parity default
        nopolar=False,
        polarization_axis=polarization_axis,
        polarization_fraction=polarization_fraction,
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
