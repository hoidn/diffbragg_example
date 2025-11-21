"""Stage A-specific ROI visualization helpers.

This module builds on top of the generic :mod:`dbex.vis` primitives to emit
spec-db-vis-compliant ROI triptychs for Stage A refinement runs.

Contract:
- Inputs are the canonical ``RefinementInputs`` and per-panel Bragg stacks
  (``bragg_before``, ``bragg_after``) shaped ``[panel, slow, fast]``.
- Each ROI is defined by ``inputs.panel_slices[i] == (pid, (x0, x1, y0, y1))``.
- For each ROI, we slice experiment and model arrays, compute variance using
  the PHYSICS-LOSS variance model, derive Z-score residuals, and call
  :func:`dbex.vis.plot_triptych` to render:

    Data | Model_before | Residual Z_before
    Data | Model_after  | Residual Z_after

The resulting PNGs live alongside a small metadata structure that higher-level
tools (e.g. plan-local scripts under TOOLING-VIS-001) can use to build
summaries without re-deriving any numerics.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np

from dbex.nanobrag_bridge import RefinementInputs
from .residuals import compute_z_scores
from .triptych import plot_triptych


@dataclass
class StageAROITriptych:
    """Metadata for a single Stage A ROI triptych pair."""

    roi_index: int
    panel_id: int
    bbox: Tuple[int, int, int, int]
    cc_before: float
    cc_after: float
    path_before: Path
    path_after: Path


def _compute_pearson_cc(
    data_roi: np.ndarray,
    model_roi: np.ndarray,
    mask_roi: Optional[np.ndarray] = None,
) -> float:
    """Compute a simple Pearson correlation coefficient between ROI slices.

    The inputs are interpreted as `(slow, fast)` arrays. When a mask is
    provided, only masked pixels contribute to the correlation estimate.
    """
    data_arr = np.asarray(data_roi, dtype=np.float64)
    model_arr = np.asarray(model_roi, dtype=np.float64)

    if data_arr.shape != model_arr.shape:
        raise ValueError(
            f"data and model must share shape; got data={data_arr.shape}, "
            f"model={model_arr.shape}"
        )

    if mask_roi is not None:
        mask_arr = np.asarray(mask_roi, dtype=bool)
        if mask_arr.shape != data_arr.shape:
            raise ValueError(
                f"mask must match ROI shape; mask={mask_arr.shape}, "
                f"roi={data_arr.shape}"
            )
        data_vec = data_arr[mask_arr]
        model_vec = model_arr[mask_arr]
    else:
        data_vec = data_arr.ravel()
        model_vec = model_arr.ravel()

    if data_vec.size == 0 or model_vec.size == 0:
        return 0.0

    d0 = data_vec - float(data_vec.mean())
    m0 = model_vec - float(model_vec.mean())
    denom = float(np.linalg.norm(d0) * np.linalg.norm(m0))
    if denom <= 1e-12 or not np.isfinite(denom):
        return 0.0

    corr = float((d0 * m0).sum() / denom)
    if not np.isfinite(corr):
        return 0.0
    return corr


def emit_stage_a_roi_triptychs(
    inputs: RefinementInputs,
    bragg_before: np.ndarray,
    bragg_after: np.ndarray,
    out_dir: str | Path,
    *,
    roi_indices: Optional[Sequence[int]] = None,
    max_rois: int = 16,
    sigma_floor_value: float = 1.0,
) -> List[StageAROITriptych]:
    """Emit per-ROI Stage A triptych PNGs for before/after refinement.

    Args:
        inputs: Canonical :class:`RefinementInputs` instance providing
            ``target``, ``sigma_readout``, ``loss_mask``, and ``panel_slices``.
        bragg_before: Zero-iteration Bragg stack shaped ``[panel, slow, fast]``.
        bragg_after: Post-Stage-A Bragg stack shaped ``[panel, slow, fast]``.
        out_dir: Directory where ROI PNGs will be written.
        roi_indices: Optional explicit list of ROI indices. When omitted,
            the helper uses the first ``max_rois`` ROIs in ``inputs.panel_slices``.
        max_rois: Upper bound on the number of ROIs to visualize.
        sigma_floor_value: Variance floor (sigma_floor) used when building
            variance maps, matching PHYSICS-LOSS semantics.

    Returns:
        List of :class:`StageAROITriptych` records describing generated PNGs.
    """
    target = np.asarray(inputs.target)
    sigma_readout = np.asarray(inputs.sigma_readout)
    loss_mask = np.asarray(inputs.loss_mask, dtype=bool)
    panel_slices = list(inputs.panel_slices)

    bragg_before_arr = np.asarray(bragg_before)
    bragg_after_arr = np.asarray(bragg_after)

    if target.shape != bragg_before_arr.shape or target.shape != bragg_after_arr.shape:
        raise ValueError(
            "Stage A ROI visualization requires matching shapes: "
            f"target={target.shape}, bragg_before={bragg_before_arr.shape}, "
            f"bragg_after={bragg_after_arr.shape}"
        )

    if sigma_readout.shape != target.shape:
        raise ValueError(
            f"sigma_readout shape {sigma_readout.shape} does not match "
            f"target shape {target.shape}"
        )

    if loss_mask.shape != target.shape:
        raise ValueError(
            f"loss_mask shape {loss_mask.shape} does not match "
            f"target shape {target.shape}"
        )

    n_rois = len(panel_slices)
    if n_rois == 0:
        return []

    if roi_indices is None:
        roi_indices = list(range(n_rois))
    else:
        roi_indices = list(roi_indices)

    if max_rois is not None and max_rois >= 0:
        roi_indices = roi_indices[: max_rois]

    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    results: List[StageAROITriptych] = []
    var_floor_sq = float(sigma_floor_value ** 2)

    for roi_index in roi_indices:
        if roi_index < 0 or roi_index >= n_rois:
            raise IndexError(f"ROI index {roi_index} out of range for {n_rois} ROIs")

        panel_id, bbox = panel_slices[roi_index]
        x0, x1, y0, y1 = map(int, bbox)

        data_roi = target[panel_id, y0:y1, x0:x1]
        model_before_roi = bragg_before_arr[panel_id, y0:y1, x0:x1]
        model_after_roi = bragg_after_arr[panel_id, y0:y1, x0:x1]
        sigma_roi = sigma_readout[panel_id, y0:y1, x0:x1]
        mask_roi = loss_mask[panel_id, y0:y1, x0:x1]

        if data_roi.size == 0:
            continue

        # Variance model: V = I_model.detach() + sigma_readout^2
        variance_before = np.maximum(
            model_before_roi.astype(np.float64) + sigma_roi.astype(np.float64) ** 2,
            var_floor_sq,
        )
        variance_after = np.maximum(
            model_after_roi.astype(np.float64) + sigma_roi.astype(np.float64) ** 2,
            var_floor_sq,
        )

        z_before = compute_z_scores(
            data_roi,
            model_before_roi,
            variance=variance_before,
            sigma_floor=sigma_floor_value,
        )
        z_after = compute_z_scores(
            data_roi,
            model_after_roi,
            variance=variance_after,
            sigma_floor=sigma_floor_value,
        )

        # Correlations over valid (loss-mask) pixels
        cc_before = _compute_pearson_cc(data_roi, model_before_roi, mask_roi)
        cc_after = _compute_pearson_cc(data_roi, model_after_roi, mask_roi)

        before_path = out_root / f"roi_{roi_index:04d}_before.png"
        after_path = out_root / f"roi_{roi_index:04d}_after.png"

        title_before = f"ROI {roi_index} (panel {panel_id}) — before (CC={cc_before:.3f})"
        title_after = f"ROI {roi_index} (panel {panel_id}) — after (CC={cc_after:.3f})"

        plot_triptych(
            data_roi,
            model_before_roi,
            z_before,
            out_path=before_path,
            title=title_before,
        )
        plot_triptych(
            data_roi,
            model_after_roi,
            z_after,
            out_path=after_path,
            title=title_after,
        )

        results.append(
            StageAROITriptych(
                roi_index=roi_index,
                panel_id=int(panel_id),
                bbox=(x0, x1, y0, y1),
                cc_before=cc_before,
                cc_after=cc_after,
                path_before=before_path,
                path_after=after_path,
            )
        )

    return results


__all__ = ["StageAROITriptych", "emit_stage_a_roi_triptychs"]

