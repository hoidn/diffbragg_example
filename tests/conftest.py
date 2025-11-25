import os
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pytest


@dataclass(frozen=True)
class SmokeDatasetPaths:
    label: str
    expt_path: Path
    refl_path: Path
    mask_path: Path
    sigma_map_path: Path = None  # Optional: path to external sigma tiles pickle


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
    parser.addoption(
        "--smoke-sigma-source",
        action="store",
        default=None,
        choices=("cli_override", "metadata"),
        help=(
            "Select sigma_readout source for Stage smokes. Defaults to "
            "DBEX_SMOKE_SIGMA_SOURCE env var or 'cli_override'."
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


def _resolve_smoke_sigma_source(pytestconfig) -> str:
    cli_value = pytestconfig.getoption("--smoke-sigma-source")
    env_value = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE")
    source = (cli_value or env_value or "cli_override").lower()
    if source not in {"cli_override", "metadata"}:
        raise pytest.UsageError(
            f"Invalid smoke-sigma-source '{source}'. Expected 'cli_override' or 'metadata'."
        )
    return source


@pytest.fixture(scope="session")
def smoke_detector_size(pytestconfig) -> str:
    return _resolve_smoke_detector_size(pytestconfig)


@pytest.fixture(scope="session")
def smoke_sigma_source(pytestconfig) -> str:
    return _resolve_smoke_sigma_source(pytestconfig)


@pytest.fixture(scope="session")
def smoke_dataset_paths(smoke_detector_size, smoke_sigma_source) -> SmokeDatasetPaths:
    """Resolve smoke dataset paths for geometry, reflections, mask, and optional sigma tiles.

    This fixture now decouples geometry sourcing from sigma sourcing per TOOLING-VIS-001.
    Environment overrides:
        - DBEX_SMOKE_GEOM_PATH: canonical geometry experiment file (defaults to refGeom.expt or refGeom_small.expt)
        - DBEX_SMOKE_SIGMA_MAP_PATH: external sigma tiles pickle (used when smoke_sigma_source=="metadata")

    When smoke_sigma_source=="metadata", the fixture resolves the sigma-map path from env or
    defaults to sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl, validates it exists, and stashes
    it on the dataclass. The geometry path remains the canonical refGeom experiment.
    """
    repo_root = Path(__file__).resolve().parent.parent

    # Resolve canonical geometry path from env or defaults
    geom_path_override = os.environ.get("DBEX_SMOKE_GEOM_PATH")
    if geom_path_override:
        geom_path = repo_root / geom_path_override
    elif smoke_detector_size == "small":
        geom_path = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small.expt"
    else:
        geom_path = repo_root / "refGeom.expt"

    # Resolve reflections and mask paths based on detector size
    if smoke_detector_size == "small":
        base = repo_root / "sp.proc" / "refGeom_small"
        refl_path = base / "refGeom_small.refl"
        mask_path = base / "refGeom_small_mask.pkl"
        label = "small"
    else:
        refl_path = repo_root / "refGeom.refl"
        mask_path = repo_root / "747_mask.pkl"
        label = "full"

    # Resolve sigma-map path when metadata source is requested
    sigma_map_path = None
    if smoke_sigma_source == "metadata":
        sigma_map_override = os.environ.get("DBEX_SMOKE_SIGMA_MAP_PATH")
        if sigma_map_override:
            sigma_map_path = repo_root / sigma_map_override
        else:
            sigma_map_path = repo_root / "sp.proc" / "idx-0000_sigma_metadata.sigma_tiles.pkl"

        # Validate sigma-map exists
        if not sigma_map_path.exists():
            pytest.skip(
                f"Metadata sigma source requested but sigma-map pickle is missing: {sigma_map_path}. "
                "Run plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py "
                "with --sigma-value/--sigma-map to regenerate."
            )

    dataset = SmokeDatasetPaths(
        label=label,
        expt_path=geom_path,
        refl_path=refl_path,
        mask_path=mask_path,
        sigma_map_path=sigma_map_path,
    )

    # Validate required assets exist
    required_paths = [dataset.expt_path, dataset.refl_path, dataset.mask_path]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        pytest.skip(
            f"Required dataset assets missing for '{dataset.label}' fixture: {missing}. "
            "Run the crop script (plans/active/PERF-SMOKE-DETSIZE/bin/crop_refgeom_to_small.py) "
            "or regenerate refGeom assets."
        )

    return dataset


def _compute_rotation_angle(U1: np.ndarray, U2: np.ndarray) -> float:
    """Compute rotation angle (in degrees) between two orientation matrices.

    Uses the formula: angle = arccos((trace(U1^T @ U2) - 1) / 2)
    which gives the geodesic distance on SO(3).

    Adapted from plans/active/TOOLING-VIS-001/bin/compare_geometry_zero_points.py:139-151.
    """
    R = U1.T @ U2
    trace_val = np.trace(R)
    # Clamp to avoid numerical issues with arccos
    cos_angle = (trace_val - 1.0) / 2.0
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle_rad = np.arccos(cos_angle)
    return float(np.degrees(angle_rad))


@pytest.fixture(scope="session")
def refgeom_dataload(smoke_dataset_paths, smoke_sigma_source):
    """Load DataLoad from canonical geometry with optional sigma-map and geometry override.

    This fixture decouples sigma sourcing from geometry per TOOLING-VIS-001 Phase D requirements.
    It loads the canonical experiment from DBEX_SMOKE_GEOM_PATH (or defaults), then:
      1. Computes the rotation angle between the loaded experiment's U-matrix and the canonical U.
      2. If the angle exceeds 5e-4 rad (~0.03°) OR any detector origin differs, overrides
         DataLoad.Expt, .detector, .beam, .crystal with deep copies from the canonical geometry.
      3. Records the resolved geometry_path and rotation_delta_deg in DataLoad.geometry_metadata
         for diagnostics/telemetry.

    When smoke_sigma_source=="metadata", the sigma-map path is passed through args.sigma_map
    instead of swapping the experiment file.

    Data dependencies (per docs/data_dependency_manifest.md):
        - dbex.data_load.DataLoad (expt/refl/mask/HKL/sigma-map)
        - dxtbx.model.ExperimentList (geometry extraction)
    """
    from argparse import Namespace

    from dbex.data_load import DataLoad
    from dxtbx.model import ExperimentList

    repo_root = Path(__file__).resolve().parent.parent

    # Resolve HKL path from env or default
    hkl_path_override = os.environ.get("DBEX_SMOKE_HKL_PATH")
    if hkl_path_override:
        hkl_path = repo_root / hkl_path_override
    else:
        hkl_path = repo_root / "scaled.mtz"

    # Resolve calibration path from env or default
    calib_path_override = os.environ.get("DBEX_SMOKE_CALIB_PATH")
    if calib_path_override:
        calib_path = repo_root / calib_path_override
    else:
        calib_path = None

    # Build DataLoad args
    args = Namespace(
        exptName=str(smoke_dataset_paths.expt_path),
        reflName=str(smoke_dataset_paths.refl_path),
        maskFile=str(smoke_dataset_paths.mask_path),
        mtzFile=str(hkl_path),
        mtzCol="I(+),SIGI(+),I(-),SIGI(-)",  # Corrected MTZ column format per scaled.mtz structure
        exptIdx=0,
        sigma_map=str(smoke_dataset_paths.sigma_map_path) if smoke_dataset_paths.sigma_map_path else None,
        config_path=str(calib_path) if calib_path else None,
    )

    # Instantiate DataLoad
    dataload = DataLoad(args)

    # Load the canonical experiment to check for geometry drift
    canonical_experiments = ExperimentList.from_file(str(smoke_dataset_paths.expt_path), check_format=False)
    if len(canonical_experiments) == 0:
        pytest.skip(f"No experiments found in canonical geometry file: {smoke_dataset_paths.expt_path}")

    canonical_expt = canonical_experiments[0]
    canonical_crystal = canonical_expt.crystal
    canonical_detector = canonical_expt.detector
    canonical_beam = canonical_expt.beam

    # Compute rotation angle between DataLoad U-matrix and canonical U-matrix
    dataload_U = np.array(dataload.Expt.crystal.get_U(), dtype=np.float64).reshape(3, 3)
    canonical_U = np.array(canonical_crystal.get_U(), dtype=np.float64).reshape(3, 3)
    rotation_delta_deg = _compute_rotation_angle(dataload_U, canonical_U)

    # Check detector origin drift (compare panel 0 origins)
    dataload_origin = np.array(dataload.Expt.detector[0].get_origin(), dtype=np.float64)
    canonical_origin = np.array(canonical_detector[0].get_origin(), dtype=np.float64)
    origin_delta_mm = float(np.linalg.norm(dataload_origin - canonical_origin))

    # Override geometry if rotation exceeds 5e-4 rad (~0.0286°) or detector origin differs
    rotation_threshold_deg = np.degrees(5e-4)  # ~0.0286°
    geometry_overridden = False
    if rotation_delta_deg > rotation_threshold_deg or origin_delta_mm > 1e-6:
        # Override with canonical geometry (deep copy to avoid mutation)
        dataload.Expt = deepcopy(canonical_expt)
        dataload.detector = deepcopy(canonical_detector)
        dataload.beam = deepcopy(canonical_beam)
        dataload.crystal = deepcopy(canonical_crystal)
        geometry_overridden = True

    # Record geometry metadata for diagnostics
    dataload.geometry_metadata = {
        "geometry_path": str(smoke_dataset_paths.expt_path),
        "rotation_delta_deg": rotation_delta_deg,
        "origin_delta_mm": origin_delta_mm,
        "geometry_overridden": geometry_overridden,
        "canonical_source": "DBEX_SMOKE_GEOM_PATH" if os.environ.get("DBEX_SMOKE_GEOM_PATH") else "default",
    }

    return dataload


def pytest_runtest_setup(item):
    detector_size = _resolve_smoke_detector_size(item.config)
    identifiers = " ".join(
        list(item.keywords.keys()) + [item.name, item.nodeid]
    ).lower()
    if (
        "db_at" in identifiers
        and detector_size != "full"
        and "db_at_028" not in identifiers
        and "db_at_029" not in identifiers
    ):
        raise pytest.UsageError(
            "DB-AT/workflow selectors SHALL assert --smoke-detector-size=full per "
            "docs/spec-db-workflow.md (Stage Smoke Dataset Policy). "
            "Re-run with --smoke-detector-size=full or DBEX_SMOKE_DETECTOR_SIZE=full."
        )
