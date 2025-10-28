"""
Bridge module to prepare DataLoad outputs for nanobrag_torch simulator.

This module provides helpers to convert DIALS/simtbx data structures into
torch-compatible tensors aligned with spec-db-core.md contracts:
- [panel, slow, fast] ordering
- background-subtracted targets
- trusted mask polarity (True=include, 1=include in torch)
- per-panel slicing information
"""

from dataclasses import dataclass
from typing import List, Tuple
import numpy as np


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
