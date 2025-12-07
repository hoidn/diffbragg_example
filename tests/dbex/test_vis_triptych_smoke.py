from __future__ import annotations

from pathlib import Path

import numpy as np

from dbex.vis import plot_triptych, compute_z_scores


def test_triptych_from_roi_slice(tmp_path: Path) -> None:
    """Smoke test for plot_triptych function (renders data/model/z-score triptych)."""
    rng = np.random.default_rng(42)

    data_roi = rng.normal(loc=100.0, scale=5.0, size=(16, 16)).astype(np.float32)
    model_roi = data_roi * 0.95
    # Compute variance per spec-db-core.md (variance = model + sigma_readout^2)
    sigma_readout_sq = 5.0 ** 2  # ADU
    variance_roi = model_roi + sigma_readout_sq

    out_file = tmp_path / "triptych.png"
    plot_triptych(
        data_roi,
        model_roi,
        variance_roi,
        filename=out_file,
    )

    assert out_file.exists(), "plot_triptych must write an artifact"
    assert out_file.stat().st_size > 0, "PNG artifact should not be empty"


def test_compute_z_scores_array_output() -> None:
    """Smoke test for compute_z_scores function (returns z-score array, does not render)."""
    rng = np.random.default_rng(7)

    data_roi = rng.normal(loc=50.0, scale=3.0, size=(8, 8)).astype(np.float32)
    model_roi = data_roi * 0.9
    # Compute variance per spec-db-core.md
    sigma_readout_sq = 5.0 ** 2  # ADU
    variance_roi = model_roi + sigma_readout_sq

    z_scores = compute_z_scores(
        data_roi,
        model_roi,
        variance_roi,
    )

    # Validate z-score array properties
    assert z_scores.shape == data_roi.shape, "Z-scores must match input data shape"
    assert not np.all(np.isnan(z_scores)), "Z-scores should contain valid values"
