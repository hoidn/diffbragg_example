"""Unit tests for sigma-map helpers in dbex.data_load."""
import pickle
from types import SimpleNamespace

import numpy as np
import pytest
from dials.array_family import flex
from dxtbx_format_image_ext import ImageDouble, ImageTileDouble
from dxtbx_imageset_ext import ExternalLookupItemDouble

from dbex.data_load import (
    DataLoad,
    _load_external_lookup_sigma_map,
    load_sigma_readout_map,
)


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


def _build_external_lookup_imageset(panel_arrays, attr_name="pedestal", filename="sigma.h5"):
    """Construct a fake imageset.external_lookup payload for testing."""
    item = ExternalLookupItemDouble()
    item.filename = filename
    image_data = ImageDouble()
    for panel_array in panel_arrays:
        flex_panel = flex.double(panel_array.astype(np.float64).ravel())
        flex_panel.reshape(flex.grid(*panel_array.shape))
        image_data.append(ImageTileDouble(flex_panel))
    item.data = image_data
    lookup = SimpleNamespace()
    setattr(lookup, attr_name, item)
    imageset = SimpleNamespace(external_lookup=lookup)
    return imageset


def test_external_lookup_sigma_map_ingestion():
    """Helper ingests external_lookup tiles and DataLoad consumes metadata when CLI map absent."""
    expected_shape = (2, 3, 2)
    panel_arrays = [
        np.full((3, 2), 5.0, dtype=np.float32),
        np.full((3, 2), 4.0, dtype=np.float32),
    ]
    imageset = _build_external_lookup_imageset(panel_arrays, filename="sigma_dark.h5")

    sigma_map, metadata = _load_external_lookup_sigma_map(imageset, expected_shape)
    assert sigma_map.shape == expected_shape
    assert metadata == {
        "lookup_key": "pedestal",
        "filename": "sigma_dark.h5",
        "tile_count": expected_shape[0],
    }

    # Simulate DataLoad sigma-map initialization without invoking heavy I/O paths
    dl = object.__new__(DataLoad)
    dl.args = SimpleNamespace(sigma_map=None)
    dl.data = np.zeros(expected_shape, dtype=np.float32)
    dl.Expt = SimpleNamespace(imageset=imageset)
    dl.sigma_readout_map = None
    dl.sigma_readout_map_source = None
    dl.sigma_readout_map_metadata = None
    dl._initialize_sigma_readout_map()

    assert dl.sigma_readout_map_source == "external_lookup"
    np.testing.assert_allclose(dl.sigma_readout_map, sigma_map)
    assert dl.sigma_readout_map_metadata == metadata


def test_external_lookup_shape_or_value_errors(tmp_path):
    """Metadata helper rejects malformed tiles and CLI assets stay highest priority."""
    expected_shape = (2, 2, 2)

    # Wrong tile count → ValueError
    wrong_tiles_imageset = _build_external_lookup_imageset([
        np.ones((2, 2), dtype=np.float32)
    ])
    with pytest.raises(ValueError, match="tiles"):
        _load_external_lookup_sigma_map(wrong_tiles_imageset, expected_shape)

    # Non-positive entries → ValueError
    bad_values_imageset = _build_external_lookup_imageset([
        np.array([[1.0, 0.0], [1.0, 1.0]], dtype=np.float32),
        np.ones((2, 2), dtype=np.float32),
    ])
    with pytest.raises(ValueError, match="non-positive"):
        _load_external_lookup_sigma_map(bad_values_imageset, expected_shape)

    # CLI assets override metadata when both exist
    cli_map = np.full(expected_shape, 7.5, dtype=np.float32)
    cli_path = tmp_path / "cli_sigma.npy"
    np.save(cli_path, cli_map)

    metadata_imageset = _build_external_lookup_imageset([
        np.full((2, 2), 3.0, dtype=np.float32),
        np.full((2, 2), 3.0, dtype=np.float32),
    ])

    dl = object.__new__(DataLoad)
    dl.args = SimpleNamespace(sigma_map=str(cli_path))
    dl.data = np.zeros(expected_shape, dtype=np.float32)
    dl.Expt = SimpleNamespace(imageset=metadata_imageset)
    dl.sigma_readout_map = None
    dl.sigma_readout_map_source = None
    dl.sigma_readout_map_metadata = None
    dl._initialize_sigma_readout_map()

    assert dl.sigma_readout_map_source == "cli_map"
    np.testing.assert_allclose(dl.sigma_readout_map, cli_map)
