"""
Refinement input preparation module (ARCH-BRIDGE-RESP-001 Phase C).

This module provides the RefinementInputs dataclass and prepare_refinement_inputs
helper that was previously in dbex/nanobrag_bridge.py. These are now factored out
to support cleaner architecture separation between bridge orchestration and
refinement data preparation.

Key contracts (preserved from bridge module):
- [panel, slow, fast] ordering (spec-db-core.md:20)
- background-subtracted targets (spec-db-workflow.md:20)
- loss mask: (background >= 0) ∧ trusted_mask (spec-db-core.md:55)
- ADU vs photon calibration policy (ADR-02, spec-db-workflow.md:20)
- Sentinel guards per simtbx_api.md:14
- Square pixel enforcement (config_crosswalk.md:30)

See also:
    docs/config_crosswalk.md — Notation ↔ Config Field Mapping
    docs/spec-db-core.md — Core data structures and ordering contracts
    docs/spec-db-workflow.md — Calibration and masking policies
    docs/simtbx_api.md — Background sentinel semantics
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np


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

    See also:
        docs/config_crosswalk.md (Notation ↔ Config Field Mapping and naming glossaries
        for I_obs, I_model, sigma_readout, and variance tensors).
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
