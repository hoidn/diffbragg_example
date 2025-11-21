"""
Unit tests for dbex.data_load.load_sigma_readout_map helper.

These tests exercise the calibrated sigma-map ingestion path introduced for
PHYSICS-LOSS-001 so calibrated detector noise tensors can bypass the CLI scalar.
"""
import pickle

import numpy as np
import pytest
from dials.array_family import flex

from dbex.data_load import load_sigma_readout_map


def _save_sigma_payload(path, fmt, data):
    """Utility to write sigma map payloads in various supported formats."""
    if fmt == "npy":
        np.save(path, data)
    elif fmt == "npz_single":
        np.savez(path, data)
    elif fmt == "npz_named":
        np.savez(path, sigma=data, extra=data * 2)
    elif fmt == "pkl_tuple":
        panels = []
        for panel in data:
            panel_flex = flex.double(panel.astype(np.float64).ravel())
            panel_flex.reshape(flex.grid(*panel.shape))
            panels.append(panel_flex)
        with open(path, "wb") as fh:
            pickle.dump(tuple(panels), fh)
    else:
        raise AssertionError(f"Unsupported test fixture format: {fmt}")


@pytest.mark.parametrize(
    "fmt",
    ["npy", "npz_single", "npz_named", "pkl_tuple"],
)
def test_sigma_map_loader_formats(tmp_path, fmt):
    """PHYSICS-LOSS-001: loader accepts .npy/.npz and pickled flex tuples."""
    expected_shape = (2, 3, 4)
    data = (np.arange(np.prod(expected_shape), dtype=np.float32) + 1).reshape(expected_shape)
    path = tmp_path / f"sigma_{fmt}"
    if fmt.startswith("np"):
        path = path.with_suffix(f".{fmt.split('_')[0]}")
    else:
        path = path.with_suffix(".pkl")

    _save_sigma_payload(path, fmt, data)

    loaded = load_sigma_readout_map(str(path), expected_shape)
    assert loaded.shape == expected_shape
    assert loaded.dtype == np.float32
    np.testing.assert_allclose(loaded, data)


def test_sigma_map_loader_shape_mismatch(tmp_path):
    """Loader raises ValueError when payload shape differs from detector shape."""
    expected_shape = (2, 3, 4)
    bad_shape_data = np.ones((1, 3, 4), dtype=np.float32)
    path = tmp_path / "sigma_bad.npy"
    np.save(path, bad_shape_data)

    with pytest.raises(ValueError, match="shape"):
        load_sigma_readout_map(str(path), expected_shape)


def test_sigma_map_loader_rejects_non_positive(tmp_path):
    """spec-db-core.md:32-34 forbid zero/negative readout noise values."""
    expected_shape = (1, 2, 2)
    non_positive = np.array(
        [[[0.0, 1.0],
          [1.0, -0.5]]],
        dtype=np.float32,
    )
    path = tmp_path / "sigma_non_positive.npy"
    np.save(path, non_positive)

    with pytest.raises(ValueError, match="non-positive"):
        load_sigma_readout_map(str(path), expected_shape)
