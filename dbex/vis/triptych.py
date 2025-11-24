"""Triptych plotting utilities aligned with ``docs/spec-db-vis.md``.

The spec mandates `(slow, fast)` ordering (§7-11), sequential intensity colormaps for
data/model (§20-22 viridis), and a diverging residual colormap centered at zero
(§20-22 seismic). The helper below enforces those rules and writes a standalone PNG artifact.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .residuals import compute_z_scores


def plot_triptych(
    data: np.ndarray,
    model: np.ndarray,
    variance: np.ndarray,
    hkl: tuple | None = None,
    correlation: float | None = None,
    filename: str | None = None,
) -> plt.Figure | None:
    """Render standard ROI triptych per spec-db-vis.md.

    Layout: [Observed Data | Model Prediction | Residual Z-Score]

    Colormaps (spec-db-vis.md §20-22):
    - Data/Model: 'viridis' (perceptually uniform), shared vmin=0, vmax=max(data, model)
    - Residuals: 'seismic' (diverging), centered at 0, vmin=-5, vmax=5

    Annotation: Super-title "HKL (h,k,l) | CC = {corr:.3f}" if hkl/correlation provided.

    Coordinate system (spec-db-vis.md §7-11):
    - (slow, fast) matrix coordinates
    - Origin (0,0) top-left
    - Fast axis horizontal, Slow axis vertical
    - Use origin='upper' in imshow

    Args:
        data: Observed intensity ROI slice shaped ``(slow, fast)`` [ADU].
        model: Model prediction ROI slice shaped ``(slow, fast)`` [ADU].
        variance: Variance map ROI slice shaped ``(slow, fast)`` [ADU²].
                  Per spec-db-core.md: variance = model + sigma_readout^2.
        hkl: Optional (h, k, l) Miller indices tuple for annotation.
        correlation: Optional ROI correlation coefficient [0,1] for annotation.
        filename: Optional PNG output path. If provided, saves figure and returns None.
                  If None, returns figure handle for interactive use.

    Returns:
        matplotlib.figure.Figure if filename is None, else None.

    Examples:
        >>> import numpy as np
        >>> data = np.ones((10, 10)) * 5.0
        >>> model = np.ones((10, 10)) * 3.0
        >>> variance = np.ones((10, 10))
        >>> fig = plot_triptych(data, model, variance, hkl=(1,2,3), correlation=0.95)
        >>> len(fig.axes)
        3
        >>> plt.close(fig)
    """
    # Validate inputs
    data_arr = np.asarray(data, dtype=np.float32)
    model_arr = np.asarray(model, dtype=np.float32)
    variance_arr = np.asarray(variance, dtype=np.float32)

    if data_arr.ndim != 2:
        raise ValueError(f"data must be 2-D (slow, fast); got shape {data_arr.shape}")
    if model_arr.shape != data_arr.shape:
        raise ValueError(
            f"model must match data shape; got model={model_arr.shape}, data={data_arr.shape}"
        )
    if variance_arr.shape != data_arr.shape:
        raise ValueError(
            f"variance must match data shape; got variance={variance_arr.shape}, data={data_arr.shape}"
        )

    # Compute Z-scores for residual panel
    z_scores = compute_z_scores(data_arr, model_arr, variance_arr)

    # Shared colormap range for data/model (spec: vmin=0, vmax=max(data, model))
    vmax_shared = float(max(np.nanmax(data_arr), np.nanmax(model_arr)))
    if not np.isfinite(vmax_shared) or vmax_shared <= 0.0:
        vmax_shared = 1.0

    # Create figure with 3 panels
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), constrained_layout=True)

    # Panel 0: Data (viridis, origin='upper')
    axes[0].imshow(data_arr, cmap='viridis', origin='upper', vmin=0, vmax=vmax_shared)
    axes[0].set_title("Data")
    axes[0].set_xticks([])
    axes[0].set_yticks([])

    # Panel 1: Model (viridis, origin='upper', shared vmax with data)
    axes[1].imshow(model_arr, cmap='viridis', origin='upper', vmin=0, vmax=vmax_shared)
    axes[1].set_title("Model")
    axes[1].set_xticks([])
    axes[1].set_yticks([])

    # Panel 2: Residual Z-Score (seismic, diverging, centered at 0, vmin=-5 vmax=5)
    axes[2].imshow(z_scores, cmap='seismic', origin='upper', vmin=-5, vmax=5)
    axes[2].set_title("Residual Z-Score")
    axes[2].set_xticks([])
    axes[2].set_yticks([])

    # Super-title with HKL/CC if provided
    if hkl is not None or correlation is not None:
        title_parts = []
        if hkl is not None:
            h, k, l = hkl
            title_parts.append(f"HKL ({h}, {k}, {l})")
        if correlation is not None:
            title_parts.append(f"CC = {correlation:.3f}")
        fig.suptitle(" | ".join(title_parts), fontsize=12)

    # Save or return
    if filename is not None:
        out_path = Path(filename)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return None
    else:
        return fig
