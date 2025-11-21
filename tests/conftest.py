import os
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass(frozen=True)
class SmokeDatasetPaths:
    label: str
    expt_path: Path
    refl_path: Path
    mask_path: Path


def pytest_addoption(parser):
    parser.addoption(
        "--smoke-detector-size",
        action="store",
        default=None,
        choices=("small", "full"),
        help=(
            "Select detector footprint for Stage smokes. "
            "Defaults to DBEX_SMOKE_DETECTOR_SIZE env var or 'small'."
        ),
    )


def _resolve_smoke_detector_size(pytestconfig) -> str:
    cli_value = pytestconfig.getoption("--smoke-detector-size")
    env_value = os.environ.get("DBEX_SMOKE_DETECTOR_SIZE")
    size = (cli_value or env_value or "small").lower()
    if size not in {"small", "full"}:
        raise pytest.UsageError(
            f"Invalid smoke-detector-size '{size}'. Expected 'small' or 'full'."
        )
    return size


@pytest.fixture(scope="session")
def smoke_detector_size(pytestconfig) -> str:
    return _resolve_smoke_detector_size(pytestconfig)


@pytest.fixture(scope="session")
def smoke_dataset_paths(smoke_detector_size) -> SmokeDatasetPaths:
    repo_root = Path(__file__).resolve().parent.parent
    if smoke_detector_size == "small":
        base = repo_root / "sp.proc" / "refGeom_small"
        dataset = SmokeDatasetPaths(
            label="small",
            expt_path=base / "refGeom_small.expt",
            refl_path=base / "refGeom_small.refl",
            mask_path=base / "refGeom_small_mask.pkl",
        )
    else:
        dataset = SmokeDatasetPaths(
            label="full",
            expt_path=repo_root / "refGeom.expt",
            refl_path=repo_root / "refGeom.refl",
            mask_path=repo_root / "747_mask.pkl",
        )

    missing = [
        str(path)
        for path in (dataset.expt_path, dataset.refl_path, dataset.mask_path)
        if not path.exists()
    ]
    if missing:
        pytest.skip(
            f"Required dataset assets missing for '{dataset.label}' fixture: {missing}. "
            "Run the crop script (plans/active/PERF-SMOKE-DETSIZE/bin/crop_refgeom_to_small.py) "
            "or regenerate refGeom assets."
        )
    return dataset


def pytest_runtest_setup(item):
    detector_size = _resolve_smoke_detector_size(item.config)
    identifiers = " ".join(
        list(item.keywords.keys()) + [item.name, item.nodeid]
    ).lower()
    if "db_at" in identifiers and detector_size != "full":
        raise pytest.UsageError(
            "DB-AT/workflow selectors SHALL assert --smoke-detector-size=full per "
            "docs/spec-db-workflow.md (Stage Smoke Dataset Policy). "
            "Re-run with --smoke-detector-size=full or DBEX_SMOKE_DETECTOR_SIZE=full."
        )
