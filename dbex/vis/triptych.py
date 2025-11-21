"""Triptych plotting utilities aligned with ``docs/spec-db-vis.md``.

The spec mandates `(slow, fast)` ordering, sequential intensity colormaps for
data/model, and a diverging residual colormap centred at zero.  The helper
below enforces those rules and writes a standalone PNG artifact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from matplotlib import colors as mcolors
from matplotlib import pyplot as plt

_INTENSITY_CMAP = "cividis"
_RESIDUAL_CMAP = "coolwarm"


def _finite_max(values: np.ndarray) -> float:
    """Return the maximum finite value in ``values`` or zero if none exist."""
    arr = np.asarray(values)
    if arr.size == 0:
        return 0.0
    finite = arr[np.isfinite(arr)]
    return float(finite.max()) if finite.size else 0.0


def _validate_roi(name: str, roi: np.ndarray) -> np.ndarray:
    """Convert the ROI to a 2-D NumPy array and validate shape."""
    arr = np.asarray(roi)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 2-D (slow, fast); got shape {arr.shape}")
    return arr


def plot_triptych(
    data_roi: np.ndarray,
    model_roi: np.ndarray,
    residual_roi: np.ndarray,
    out_path: str | Path,
    *,
    title: Optional[str] = None,
) -> Path:
    """Render a `(Data | Model | Residual)` triptych PNG for a single ROI.

    Args:
        data_roi: Observed ROI slice shaped `(slow, fast)` in detector order.
        model_roi: Model ROI slice shaped `(slow, fast)` matching ``data_roi``.
        residual_roi: Residual (typically Z-score) slice `(slow, fast)`.
        out_path: Destination path for the PNG artifact.
        title: Optional super-title (e.g., ``HKL=120, CC=0.97``).

    Returns:
        The resolved ``Path`` to the written PNG.
    """

    data = _validate_roi("data_roi", data_roi)
    model = _validate_roi("model_roi", model_roi)
    residual = _validate_roi("residual_roi", residual_roi)

    if data.shape != model.shape or data.shape != residual.shape:
        raise ValueError(
            "ROI inputs must share the same `(slow, fast)` shape "
            f"(data={data.shape}, model={model.shape}, residual={residual.shape})"
        )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Shared bounds for intensity panels to respect spec-db-vis.
    max_intensity = max(_finite_max(data), _finite_max(model), 0.0)
    if not np.isfinite(max_intensity) or max_intensity <= 0.0:
        max_intensity = 1.0

    residual_extent = _finite_max(np.abs(residual))
    if residual_extent <= 0.0:
        residual_extent = 1.0

    fig, axes = plt.subplots(1, 3, figsize=(10, 3), constrained_layout=True)
    if title:
        fig.suptitle(title, fontsize=12)

    images = (
        ("Data", data, dict(vmin=0.0, vmax=max_intensity, cmap=_INTENSITY_CMAP)),
        ("Model", model, dict(vmin=0.0, vmax=max_intensity, cmap=_INTENSITY_CMAP)),
        (
            "Residual Z-Score",
            residual,
            dict(
                cmap=_RESIDUAL_CMAP,
                norm=mcolors.TwoSlopeNorm(
                    vmin=-residual_extent, vcenter=0.0, vmax=residual_extent
                ),
            ),
        ),
    )

    for axis, (name, image, kwargs) in zip(axes, images):
        axis.imshow(image, origin="upper", **kwargs)
        axis.set_title(name)
        axis.set_xticks([])
        axis.set_yticks([])

    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path
