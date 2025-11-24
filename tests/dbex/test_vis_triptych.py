"""Unit tests for dbex.vis module per input.md Phase A specification.

Tests validate:
1. Triptych layout (3 panels, colormaps per spec-db-vis.md)
2. Z-score calculation formula (Data-Model)/sqrt(Variance)
3. Z-score masking (masked pixels → NaN)
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest

from dbex.vis import compute_z_scores, plot_triptych


def test_triptych_layout():
    """Test 1: Validate 3-panel triptych structure, colormaps per spec.

    Per input.md:136-148 and spec-db-vis.md §7-11, §16-23:
    - 3 panels [Data | Model | Residual Z-Score]
    - Colormaps: viridis (data/model), seismic (residuals)
    - Origin: 'upper' (top-left)
    - Super-title with HKL and CC if provided
    """
    # Synthetic inputs
    data = np.ones((10, 10), dtype=np.float32) * 5.0
    model = np.ones((10, 10), dtype=np.float32) * 3.0
    variance = np.ones((10, 10), dtype=np.float32)

    # Call plot_triptych with HKL and correlation
    fig = plot_triptych(data, model, variance, hkl=(1, 2, 3), correlation=0.95)

    try:
        # Assertion 1: 3 panels
        assert len(fig.axes) == 3, "Triptych must have exactly 3 panels"

        # Assertion 2: Check colormaps
        # Panel 0 (data) and Panel 1 (model) should use 'viridis'
        assert fig.axes[0].images[0].get_cmap().name == 'viridis', "Data panel must use viridis colormap"
        assert fig.axes[1].images[0].get_cmap().name == 'viridis', "Model panel must use viridis colormap"

        # Panel 2 (residuals) should use 'seismic'
        assert fig.axes[2].images[0].get_cmap().name == 'seismic', "Residual panel must use seismic colormap"

        # Assertion 3: Check origin='upper'
        assert fig.axes[0].images[0].origin == 'upper', "Data panel must use origin='upper'"
        assert fig.axes[1].images[0].origin == 'upper', "Model panel must use origin='upper'"
        assert fig.axes[2].images[0].origin == 'upper', "Residual panel must use origin='upper'"

        # Assertion 4: Check super-title contains HKL and CC
        suptitle_text = fig._suptitle.get_text() if fig._suptitle else ""
        assert "HKL (1, 2, 3)" in suptitle_text, "Super-title must contain HKL indices"
        assert "CC = 0.950" in suptitle_text, "Super-title must contain correlation coefficient"

    finally:
        # Cleanup: close figure to prevent memory leak
        plt.close(fig)


def test_z_score_calculation():
    """Test 2: Validate Z-score formula (Data-Model)/sqrt(Variance) with known inputs.

    Per input.md:150-154 and spec-db-vis.md §19:
    - Formula: Z = (Data - Model) / sqrt(Variance)
    - Expected: residual=2, std_dev=1, z=2
    - Edge case: variance=0 → epsilon handling (no divide-by-zero)
    """
    # Known inputs
    data = np.array([[5, 5], [5, 5]], dtype=np.float32)
    model = np.array([[3, 3], [3, 3]], dtype=np.float32)
    variance = np.array([[1, 1], [1, 1]], dtype=np.float32)

    # Call compute_z_scores
    z_scores = compute_z_scores(data, model, variance)

    # Expected: residual = 5-3 = 2, std_dev = sqrt(1) = 1, z = 2/1 = 2
    np.testing.assert_allclose(z_scores, 2.0, rtol=1e-5, err_msg="Z-scores must match expected value")

    # Edge case: variance=0 → epsilon handling (no divide-by-zero error)
    variance_zero = np.array([[0, 0], [0, 0]], dtype=np.float32)
    z_scores_zero = compute_z_scores(data, model, variance_zero)

    # Should not raise divide-by-zero error, and result should be finite
    assert np.all(np.isfinite(z_scores_zero)), "Z-scores with variance=0 must remain finite (epsilon handling)"


def test_z_score_masking():
    """Test 3: Validate masked pixels set to NaN.

    Per input.md:156-164 and spec-db-vis.md §19:
    - Masked pixels (mask=False or mask=0) → NaN
    - Unmasked pixels → valid Z-score
    - Example: residual=2, std=2, z=1 (for unmasked pixels)
    """
    # Inputs
    data = np.ones((5, 5), dtype=np.float32) * 10.0
    model = np.ones((5, 5), dtype=np.float32) * 8.0
    variance = np.ones((5, 5), dtype=np.float32) * 4.0

    # Mask: all True except center pixel (2,2)
    mask = np.ones((5, 5), dtype=bool)
    mask[2, 2] = False  # Center pixel masked

    # Call compute_z_scores with mask
    z_scores = compute_z_scores(data, model, variance, mask=mask)

    # Assertion 1: Masked pixel (2,2) is NaN
    assert np.isnan(z_scores[2, 2]), "Masked pixel must be NaN"

    # Assertion 2: Unmasked pixel (0,0) is valid (not NaN)
    assert not np.isnan(z_scores[0, 0]), "Unmasked pixel must not be NaN"

    # Assertion 3: Unmasked pixel value check
    # residual = 10 - 8 = 2, std_dev = sqrt(4) = 2, z = 2/2 = 1
    assert np.abs(z_scores[0, 0] - 1.0) < 1e-5, "Unmasked pixel Z-score must match expected value (z=1)"
