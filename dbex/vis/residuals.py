"""Residual and Z-score helpers for visualization per spec-db-vis.md.

These utilities keep residual computation and Z-score scaling aligned with
``docs/spec-db-vis.md`` §19 and the variance-weighted loss semantics. They are
intentionally lightweight and operate on `(slow, fast)` ROI slices.
"""

from __future__ import annotations

import numpy as np


def compute_z_scores(
    data: np.ndarray,
    model: np.ndarray,
    variance: np.ndarray,
    mask: np.ndarray | None = None,
    sigma_floor: float | None = None,
) -> np.ndarray:
    """Compute residual Z-scores per spec-db-vis.md §19.

    Formula: Z = (Data - Model) / sqrt(Variance)

    Masked pixels (mask=False or mask=0) are set to NaN for visualization.

    Numerical stability: Add epsilon=1e-12 to denominator to prevent divide-by-zero.

    Args:
        data: Observed ROI slice shaped ``(slow, fast)`` in detector order.
        model: Model ROI slice shaped ``(slow, fast)`` matching ``data``.
        variance: Variance array (same shape as data/model). Per spec-db-core.md,
                  variance = model + sigma_readout^2 where sigma_readout=5 ADU.
        sigma_floor: Optional variance floor (sigma_floor) in data units. Present
            for convenience/forward-compatibility; callers are expected to apply
            any clamping to ``variance`` before passing it in.
        mask: Optional boolean mask selecting valid pixels. Pixels where mask=False
              or mask=0 are set to NaN in the output.

    Returns:
        Z-score map with same shape as inputs. NaN where masked or variance <= 0.

    Examples:
        >>> data = np.array([[5, 5], [5, 5]], dtype=np.float32)
        >>> model = np.array([[3, 3], [3, 3]], dtype=np.float32)
        >>> variance = np.array([[1, 1], [1, 1]], dtype=np.float32)
        >>> z_scores = compute_z_scores(data, model, variance)
        >>> np.allclose(z_scores, 2.0, rtol=1e-5)
        True
    """
    data_arr = np.asarray(data, dtype=np.float64)
    model_arr = np.asarray(model, dtype=np.float64)
    variance_arr = np.asarray(variance, dtype=np.float64)

    if data_arr.shape != model_arr.shape:
        raise ValueError(
            f"data and model must share shape (slow, fast); "
            f"got data={data_arr.shape}, model={model_arr.shape}"
        )

    if variance_arr.shape != data_arr.shape:
        raise ValueError(
            f"variance must match data/model shape; "
            f"got variance={variance_arr.shape}, data={data_arr.shape}"
        )

    residuals = data_arr - model_arr

    # Numerical stability: add epsilon to prevent divide-by-zero
    std_dev = np.sqrt(variance_arr + 1e-12)

    z_scores = residuals / std_dev

    # Apply masking: set masked pixels to NaN
    if mask is not None:
        mask_arr = np.asarray(mask, dtype=bool)
        if mask_arr.shape != data_arr.shape:
            raise ValueError(
                f"mask must match data shape; "
                f"mask={mask_arr.shape}, data={data_arr.shape}"
            )
        z_scores = z_scores.copy()  # Avoid modifying input if broadcast
        z_scores[~mask_arr] = np.nan

    return z_scores.astype(np.float32)
