"""Residual and Z-score helpers for visualization.

These utilities keep residual computation and Z-score scaling aligned with
``docs/spec-db-vis.md`` and the variance-weighted loss semantics.  They are
intentionally lightweight and operate on `(slow, fast)` ROI slices.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from .triptych import plot_triptych


def compute_z_scores(
    data: np.ndarray,
    model: np.ndarray,
    *,
    variance: Optional[np.ndarray] = None,
    mask: Optional[np.ndarray] = None,
    sigma_floor: float = 1e-6,
) -> np.ndarray:
    """Compute simple Z-score style residuals for a single ROI.

    Args:
        data: Observed ROI slice shaped ``(slow, fast)``.
        model: Model ROI slice shaped ``(slow, fast)``.
        variance: Optional variance array (same shape or broadcastable).
                  When provided, Z = (data - model) / sqrt(max(variance,
                  sigma_floor**2)).
        mask: Optional boolean mask selecting valid pixels when estimating
              a scalar scale from residuals (used when ``variance`` is None).
        sigma_floor: Minimum standard deviation used to avoid division by
                     zero and to keep Z-scores well-conditioned.

    Returns:
        Array of Z-scores with the same shape as ``data``.
    """
    data_arr = np.asarray(data)
    model_arr = np.asarray(model)

    if data_arr.shape != model_arr.shape:
        raise ValueError(
            f"data and model must share shape (slow, fast); "
            f"got data={data_arr.shape}, model={model_arr.shape}"
        )

    residual = data_arr - model_arr

    if variance is not None:
        var_arr = np.asarray(variance)
        # Allow broadcasting but guard against negative values.
        denom = np.sqrt(np.maximum(var_arr, sigma_floor ** 2))
    else:
        if mask is not None:
            mask_arr = np.asarray(mask, dtype=bool)
            if mask_arr.shape != residual.shape:
                raise ValueError(
                    f"mask must match residual shape; "
                    f"mask={mask_arr.shape}, residual={residual.shape}"
                )
            valid = residual[mask_arr]
        else:
            valid = residual.ravel()

        if valid.size == 0:
            sigma = sigma_floor
        else:
            sigma = float(np.std(valid.astype(np.float64)))
            if not np.isfinite(sigma) or sigma <= 0.0:
                sigma = sigma_floor

        denom = sigma

    z = residual / denom
    return z.astype(np.float32, copy=False)


def plot_z_scores(
    data_roi: np.ndarray,
    model_roi: np.ndarray,
    out_path: str | Path,
    *,
    variance_roi: Optional[np.ndarray] = None,
    mask_roi: Optional[np.ndarray] = None,
    title: Optional[str] = None,
) -> Path:
    """Compute Z-scores for an ROI and render a triptych PNG.

    This is a convenience wrapper that combines :func:`compute_z_scores`
    with :func:`plot_triptych`.
    """
    z_roi = compute_z_scores(
        data_roi,
        model_roi,
        variance=variance_roi,
        mask=mask_roi,
    )
    return plot_triptych(
        data_roi,
        model_roi,
        z_roi,
        out_path=out_path,
        title=title,
    )

