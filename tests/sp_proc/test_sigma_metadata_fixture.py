from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from dxtbx.model import ExperimentList

from dbex.data_load import _load_external_lookup_sigma_map


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "sp.proc"
MANIFEST_PATH = FIXTURE_DIR / "sigma_metadata_manifest.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_sigma_metadata_manifest_and_loading() -> None:
    if not MANIFEST_PATH.exists():
        pytest.skip(
            "sigma_metadata_manifest.json missing; run "
            "plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py "
            "with --manifest to generate the metadata fixtures."
        )

    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest.get("sigma_readout_provenance") == "external_lookup", (
        "Sigma manifest must record external_lookup provenance per "
        "PHYSICS-LOSS-005 / docs/spec-db-core.md:32-68."
    )

    files = {
        entry["role"]: entry
        for entry in manifest.get("files", [])
    }
    missing_roles = {"experiment", "sigma_tiles_pickle", "report"} - files.keys()
    assert not missing_roles, (
        f"Manifest missing entries: {sorted(missing_roles)}; "
        "re-run the embedding helper with --manifest."
    )

    for role in ("experiment", "sigma_tiles_pickle", "report"):
        file_entry = files[role]
        path = Path(file_entry["path"])
        assert path.exists(), (
            f"{role} path '{path}' missing; regenerate fixtures via sp.proc/README.md."
        )
        expected_digest = file_entry["sha256"]
        actual_digest = _sha256(path)
        assert actual_digest == expected_digest, (
            f"{role} digest mismatch (manifest={expected_digest}, computed={actual_digest})."
        )

    experiment_path = Path(files["experiment"]["path"])
    experiments = ExperimentList.from_file(str(experiment_path))
    assert len(experiments) > 0, "ExperimentList should contain at least one experiment."
    experiment = experiments[0]
    imageset = getattr(experiment, "imageset", None)
    assert imageset is not None, "Experiment lacks imageset despite manifest claims."

    expected_shape = (
        int(manifest["panel_count"]),
        int(manifest["panel_shape"]["slow"]),
        int(manifest["panel_shape"]["fast"]),
    )
    sigma_tensor, metadata = _load_external_lookup_sigma_map(imageset, expected_shape)
    assert metadata is not None, "Expected metadata dictionary from external_lookup tiles."
    assert sigma_tensor is not None, "External lookup payload did not produce a sigma tensor."
    assert sigma_tensor.shape == expected_shape
    assert np.all(sigma_tensor > 0), "Sigma tensor must be strictly positive per spec-db-core.md:32-68."
    assert metadata.get("lookup_key") in {"pedestal", "dark", "sigma", "sigma_rdout", "readout", "noise"}
    assert metadata.get("tile_count") == expected_shape[0]

    stats = manifest["report"]["stats"]
    np.testing.assert_allclose(
        [np.min(sigma_tensor), np.max(sigma_tensor), np.mean(sigma_tensor), np.std(sigma_tensor)],
        [stats["min"], stats["max"], stats["mean"], stats["std"]],
        rtol=1e-6,
        atol=1e-6,
    )
