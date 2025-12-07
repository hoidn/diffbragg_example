from __future__ import annotations

from pathlib import Path

import numpy as np

from dbex.vis import plot_triptych, compute_z_scores


def test_plot_triptych_smoke(tmp_path: Path) -> None:
    rng = np.random.default_rng(42)

    data_stack = rng.normal(loc=100.0, scale=5.0, size=(1, 16, 16)).astype(np.float32)
    model_stack = data_stack * 0.95
    # Basic Z-score style residual.
    residual_stack = (data_stack - model_stack) / 2.0

    out_file = tmp_path / "triptych.png"
    result_path = plot_triptych(
        data_stack[0],
        model_stack[0],
        residual_stack[0],
        out_path=out_file,
        title="HKL=(1,2,3) CC=0.99",
    )

    assert result_path.exists(), "plot_triptych must write an artifact"
    assert result_path.stat().st_size > 0, "PNG artifact should not be empty"


def test_plot_z_scores_smoke(tmp_path: Path) -> None:
    rng = np.random.default_rng(7)

    data_roi = rng.normal(loc=50.0, scale=3.0, size=(8, 8)).astype(np.float32)
    model_roi = data_roi * 0.9

    out_file = tmp_path / "triptych_z.png"
    result_path = compute_z_scores(
        data_roi,
        model_roi,
        out_path=out_file,
        title="Z-score residuals",
    )

    assert result_path.exists(), "compute_z_scores must write an artifact"
    assert result_path.stat().st_size > 0, "Z-score PNG artifact should not be empty"
