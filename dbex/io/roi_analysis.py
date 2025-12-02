"""ROI analysis payload definitions for writer/bridge responsibility split.

This module defines typed containers for Region-of-Interest (ROI) analysis artifacts
that decouple ROI scoring (Nelder-Mead optimization) from HDF5 serialization in
`dbex.io.writer`. Prior to ARCH-BRIDGE-RESP-001, the writer performed scoring inline;
this module establishes the seam so scoring can move to a dedicated helper in Phase B.

Spec Compliance:
    - docs/spec-db-core.md §§20-48: ROI bbox semantics, array ordering [panel, slow, fast],
      variance model V = max(I_model + sigma_readout^2, sigma_floor^2).
    - docs/spec-db-interfaces.md: HDF5 schema (/data/roiN, /model/roiN, /bragg/roiN,
      /bg/roiN, /variance/roiN, /score) and per-ROI telemetry provenance.

Design Intent:
    - Keep dataclasses numpy-compatible (no torch tensors) for h5py serialization boundary.
    - Provide a packaging helper (`build_roi_payloads_from_arrays`) that consolidates
      existing arrays without mutating them or running optimization (scoring deferred to
      future helper in ARCH-BRIDGE-RESP-001 Phase B).
    - Include docstrings citing normative spec clauses so downstream consumers understand
      the data contract and variance semantics.

History:
    - 2025-12-02 (ARCH-BRIDGE-RESP-001 Phase A.2): Initial scaffold as part of writer/bridge
      responsibility split. No behavior change in this loop; new types are unused until
      Phase B wiring.

See Also:
    - docs/architecture/dbex/io/writer.idl.md: Writer API contract and ROI payload interface.
    - docs/data_dependency_manifest.md: Dependency manifest entry for ROI helper inputs/outputs.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

__all__ = [
    "ROITriptych",
    "ROIAnalysisPayload",
    "build_roi_payloads_from_arrays",
]


@dataclass
class ROITriptych:
    """ROI data triptych: observed data, background, and simulated Bragg per ROI.

    Captures the three fundamental arrays required for ROI scoring and variance modeling
    per docs/spec-db-core.md §§20-48. All arrays are numpy (not torch) to support h5py
    serialization without device/dtype conversions at the writer boundary.

    Attributes:
        panel_id: DIALS detector panel ID (0-indexed) for this ROI.
        bbox: Bounding box (x0, x1, y0, y1) with x1/y1 exclusive; sliced as
              img[pid, y0:y1, x0:x1] per spec-db-core.md §26.
        data: Observed target intensities cropped to bbox (shape: (ny, nx)).
        background: Background image cropped to bbox (shape: (ny, nx)).
        bragg: Simulated Bragg intensities cropped to bbox (shape: (ny, nx)).

    Notes:
        - All intensity arrays are in the same units (ADU or photons) as the refinement
          loss target per docs/spec-db-core.md §§23-24 (unit mode normative).
        - Background SHALL NOT contain NaN values (assertion enforced by writer and bridge).
        - Shape consistency: data.shape == background.shape == bragg.shape.

    Example:
        >>> triptych = ROITriptych(
        ...     panel_id=0,
        ...     bbox=(10, 30, 20, 40),  # x0=10, x1=30, y0=20, y1=40
        ...     data=np.random.rand(20, 20),
        ...     background=np.zeros((20, 20)),
        ...     bragg=np.random.rand(20, 20),
        ... )
        >>> assert triptych.data.shape == (20, 20)  # (y1-y0, x1-x0)
    """

    panel_id: int
    bbox: Tuple[int, int, int, int]  # (x0, x1, y0, y1)
    data: np.ndarray  # shape: (ny, nx)
    background: np.ndarray  # shape: (ny, nx)
    bragg: np.ndarray  # shape: (ny, nx)


@dataclass
class ROIAnalysisPayload:
    """Per-ROI analysis result: triptych, score, optimal scale, and variance metadata.

    Encapsulates the outputs of ROI scoring (Nelder-Mead optimization via score_trainer.roi_check)
    plus variance arrays computed per spec-db-core.md §§86-90. This typed payload replaces the
    prior inline scoring/variance loops in `write_torch_outputs`, allowing the writer to focus
    solely on HDF5 serialization (ARCH-BRIDGE-RESP-001 Phase B).

    Attributes:
        triptych: ROITriptych containing cropped data/background/bragg arrays and metadata.
        score: Per-ROI quality metric from CHECKER.score() (range: 0-1, higher=better).
                May be None if scoring is skipped or optimization fails.
        optimal_scale: Bragg intensity scale factor from Nelder-Mead (scalar >= 0).
                       Model image = background + optimal_scale * bragg.
                       Defaults to 1.0 if optimization fails or is skipped.
        variance: Variance array V = max(I_model + sigma_readout^2, sigma_floor^2)
                  per spec-db-core.md §§86-90, in target units (ADU or photons).
                  Shape matches triptych arrays (ny, nx). May be None if variance
                  computation is deferred.
        model: Optimized model image (background + optimal_scale * bragg) used for
               variance computation. Shape matches triptych arrays. May be None if
               model is computed inline during serialization.

    Notes:
        - Variance semantics: V must be strictly positive and finite on trusted pixels
          (zero/NaN sigma is non-compliant per spec-db-core.md §38).
        - Score provenance: Computed via `score_trainer.roi_check.roiCheck.score(data, model)`;
          higher scores indicate better agreement between data and model.
        - Optimal scale: Derived from minimizing `1 - CHECKER.score()` over Bragg scale
          parameter (Nelder-Mead method="Nelder-Mead").

    Example:
        >>> triptych = ROITriptych(0, (10, 30, 20, 40), data, bg, bragg)
        >>> variance = np.maximum(model + sigma_readout**2, sigma_floor**2)
        >>> payload = ROIAnalysisPayload(
        ...     triptych=triptych,
        ...     score=0.85,
        ...     optimal_scale=1.23,
        ...     variance=variance,
        ...     model=bg + 1.23 * bragg,
        ... )
    """

    triptych: ROITriptych
    score: Optional[float]
    optimal_scale: float
    variance: Optional[np.ndarray]  # shape: (ny, nx)
    model: Optional[np.ndarray]  # shape: (ny, nx)


def build_roi_payloads_from_arrays(
    target: np.ndarray,
    background: np.ndarray,
    bragg: np.ndarray,
    pids: List[int],
    bbox: List[Tuple[int, int, int, int]],
    scores: Optional[List[float]] = None,
    scales: Optional[List[float]] = None,
) -> List[ROIAnalysisPayload]:
    """Package existing ROI arrays into typed payloads without mutating or optimizing.

    Helper for transitioning from inline writer scoring to typed ROI analysis payloads.
    This function performs only array slicing and dataclass construction; it does NOT
    run Nelder-Mead optimization or compute variance. Scoring and variance computation
    will migrate to a dedicated analysis helper in ARCH-BRIDGE-RESP-001 Phase B.

    Args:
        target: Full-detector target intensities (n_panels, slow, fast) in ADU or photons.
        background: Full-detector background image (n_panels, slow, fast) matching target units.
        bragg: Full-detector simulated Bragg intensities (n_panels, slow, fast) matching target units.
        pids: Panel IDs per ROI (length n_rois).
        bbox: Bounding boxes per ROI (length n_rois), each (x0, x1, y0, y1) with x1/y1 exclusive.
        scores: Optional pre-computed per-ROI scores (length n_rois). If None, all payloads
                have score=None (scoring deferred).
        scales: Optional pre-computed optimal Bragg scales (length n_rois). If None, defaults
                to 1.0 for all ROIs (no optimization applied).

    Returns:
        List of ROIAnalysisPayload instances (length n_rois), one per ROI. Each payload
        contains a triptych with cropped arrays and optional score/scale metadata.
        Variance and model fields are set to None (computed downstream).

    Raises:
        AssertionError: If array shapes are inconsistent, bbox indices are out of bounds,
                        or scores/scales lengths don't match pids/bbox.

    Notes:
        - This helper is numpy-only (no torch imports) to avoid device management at the
          writer boundary (see dbex/io/writer.py DIAGNOSTICS-001 compliance).
        - Background arrays SHALL NOT contain NaN; caller must validate upstream
          (enforced by dbex/nanobrag_bridge.py per PHYSICS-LOSS-001).
        - Array ordering: [panel, slow, fast] per docs/spec-db-core.md §21.
        - Future wiring: ROI scoring helper (Phase B) will call this function after
          running Nelder-Mead, then populate score/variance fields before passing to writer.

    Example:
        >>> target = np.random.rand(2, 100, 100)
        >>> background = np.zeros((2, 100, 100))
        >>> bragg = np.random.rand(2, 100, 100)
        >>> pids = [0, 1]
        >>> bbox = [(10, 30, 20, 40), (50, 70, 60, 80)]
        >>> payloads = build_roi_payloads_from_arrays(target, background, bragg, pids, bbox)
        >>> assert len(payloads) == 2
        >>> assert payloads[0].triptych.data.shape == (20, 20)  # (y1-y0, x1-x0)
        >>> assert payloads[0].score is None  # No scoring performed
        >>> assert payloads[0].optimal_scale == 1.0  # Default scale
    """
    assert target.shape == background.shape == bragg.shape, (
        f"Array shape mismatch: target={target.shape}, bg={background.shape}, bragg={bragg.shape}"
    )
    assert len(pids) == len(bbox), f"pids length ({len(pids)}) != bbox length ({len(bbox)})"
    if scores is not None:
        assert len(scores) == len(pids), f"scores length ({len(scores)}) != pids length ({len(pids)})"
    if scales is not None:
        assert len(scales) == len(pids), f"scales length ({len(scales)}) != pids length ({len(pids)})"

    payloads = []
    for i, (pid, (x0, x1, y0, y1)) in enumerate(zip(pids, bbox)):
        # Slice arrays per spec-db-core.md §26: img[pid, y0:y1, x0:x1]
        data_crop = target[pid, y0:y1, x0:x1]
        bg_crop = background[pid, y0:y1, x0:x1]
        bragg_crop = bragg[pid, y0:y1, x0:x1]

        # Validate background (no NaN allowed per PHYSICS-LOSS-001)
        assert not np.any(np.isnan(bg_crop)), (
            f"ROI {i} (panel {pid}, bbox {(x0, x1, y0, y1)}): background contains NaN"
        )

        triptych = ROITriptych(
            panel_id=pid,
            bbox=(x0, x1, y0, y1),
            data=data_crop,
            background=bg_crop,
            bragg=bragg_crop,
        )

        score_val = scores[i] if scores is not None else None
        scale_val = scales[i] if scales is not None else 1.0

        payload = ROIAnalysisPayload(
            triptych=triptych,
            score=score_val,
            optimal_scale=scale_val,
            variance=None,  # Deferred to future ROI scoring helper
            model=None,     # Deferred to future ROI scoring helper
        )
        payloads.append(payload)

    return payloads
