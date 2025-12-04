"""Calibration configuration variant materialization.

This module provides helpers for loading base calibration configs (config_torch.json)
and generating derived variants with modifications (spot_scale_override, N_cells removal).

Ownership: dbex.calibration (ARCH-PROBE-FREEZE-001)
Contract: Calibration/Data Dependency Manifest (docs/data_dependency_manifest.md:40-140)
"""

import json
import os
from pathlib import Path
from typing import Optional


def materialize_calibration_variant(
    base_config_path: str,
    variant_name: str,
    out_dir: Path,
    spot_scale_override: Optional[float] = None,
    drop_n_cells: bool = False,
) -> str:
    """Generate a modified calibration config for a specific variant.

    Reads a base config_torch.json file, applies optional modifications
    (spot_scale_override, N_cells removal), and writes the variant to a
    calibration_variants subdirectory under out_dir.

    Args:
        base_config_path: Path to the base config_torch.json file
        variant_name: Name of the variant (used in output filename)
        out_dir: Directory where variant config will be written
        spot_scale_override: If provided, replace crystal.scale_override with this value
        drop_n_cells: If True, remove crystal.N_cells from the config

    Returns:
        Path to the materialized variant config file (absolute string path)

    Per input.md requirements:
    - Rewrite config_torch_smoke.json into per-variant copies
    - Store derived configs under report dir before building DataLoad
    - spot_scale forced to 1 for spot1 variants
    - optional N_cells removal for drop_ncells variants

    Contract: Calibration Config Schema (docs/data_dependency_manifest.md:79-84)
    - Fields: spot_scale_override, sigma_floor, beam_flux, beam_exposure, beamsize_mm, N_cells
    - All modifications preserve other fields
    """
    # Read base config
    with open(base_config_path, "r") as f:
        config = json.load(f)

    # Apply spot_scale_override modification if requested
    if spot_scale_override is not None:
        if "crystal" not in config:
            config["crystal"] = {}
        config["crystal"]["scale_override"] = spot_scale_override
        print(f"  Variant '{variant_name}': forcing spot_scale_override={spot_scale_override}")

    # Apply N_cells removal if requested
    if drop_n_cells:
        if "crystal" in config and "N_cells" in config["crystal"]:
            removed_value = config["crystal"].pop("N_cells")
            print(f"  Variant '{variant_name}': removed N_cells={removed_value}")

    # Write variant config to calibration_variants subdir
    variant_dir = out_dir / "calibration_variants"
    variant_dir.mkdir(parents=True, exist_ok=True)
    variant_config_path = variant_dir / f"{variant_name}.json"

    with open(variant_config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"  Variant '{variant_name}': materialized to {variant_config_path}")
    return str(variant_config_path)


def resolve_dataset_paths(detector_size: str = "small") -> dict:
    """Resolve canonical dataset paths based on detector size.

    Mirrors logic from tests/conftest.py::smoke_dataset_paths (lines 89-130).

    Args:
        detector_size: "small" or "full" (default: "small")

    Returns:
        Dictionary with keys: geom_path, refl_path, mask_path, sigma_map_path (Optional)

    Contract: Stage A Telemetry Ownership (docs/architecture/data_telemetry_flow.md:1-180)
    - Geometry path stays canonical (not swapped to idx-0000_sigma_metadata.expt)
    - Sigma map path resolves based on DBEX_SMOKE_SIGMA_SOURCE env var
    """
    # Determine repo root (assuming this file is at dbex/calibration/config_variants.py)
    repo_root = Path(__file__).parent.parent.parent

    # Resolve canonical geometry path from env or defaults (per conftest.py:89-96)
    geom_path_override = os.environ.get("DBEX_SMOKE_GEOM_PATH")
    if geom_path_override:
        geom_path = repo_root / geom_path_override
    elif detector_size == "small":
        geom_path = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small.expt"
    else:
        geom_path = repo_root / "refGeom.expt"

    # Resolve reflections and mask paths based on detector size (per conftest.py:98-107)
    if detector_size == "small":
        base = repo_root / "sp.proc" / "refGeom_small"
        refl_path = base / "refGeom_small.refl"
        mask_path = base / "refGeom_small_mask.pkl"
    else:
        refl_path = repo_root / "refGeom.refl"
        mask_path = repo_root / "747_mask.pkl"

    # Resolve sigma-map path when metadata source is requested (per conftest.py:109-130)
    sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "override")
    sigma_map_path = None
    if sigma_source == "metadata":
        sigma_map_override = os.environ.get("DBEX_SMOKE_SIGMA_MAP_PATH")
        if sigma_map_override:
            sigma_map_path = repo_root / sigma_map_override
        else:
            # Default to cropped sigma-map for small detector, full sigma-map otherwise
            if detector_size == "small":
                sigma_map_path = repo_root / "sp.proc" / "refGeom_small" / "idx-0000_sigma_metadata_small.sigma_tiles.pkl"
            else:
                sigma_map_path = repo_root / "sp.proc" / "idx-0000_sigma_metadata.sigma_tiles.pkl"

    return {
        "geom_path": str(geom_path),
        "refl_path": str(refl_path),
        "mask_path": str(mask_path),
        "sigma_map_path": str(sigma_map_path) if sigma_map_path else None,
        "sigma_source": sigma_source,
    }


def resolve_smoke_calibration_path(detector_size: str = "small") -> Optional[str]:
    """Resolve smoke calibration config path based on detector size.

    Per TOOLING-VIS-001 Phase D.D and docs/data_dependency_manifest.md:42-54.

    Args:
        detector_size: "small" or "full" (default: "small")

    Returns:
        Absolute path to smoke calibration config, or None if override/missing

    Contract: Calibration/Data Dependency Manifest (docs/data_dependency_manifest.md:40-84)
    - Override: DBEX_SMOKE_CALIB_PATH takes precedence
    - Small detector: sp.proc/calibration/config_torch_smoke_small.json
    - Full detector: sp.proc/calibration/config_torch_smoke.json
    """
    repo_root = Path(__file__).parent.parent.parent

    # Override takes precedence
    calib_override = os.environ.get("DBEX_SMOKE_CALIB_PATH")
    if calib_override:
        calib_path = Path(calib_override)
        return str(calib_path) if calib_path.is_absolute() else str(repo_root / calib_path)

    # Detector-size-specific defaults
    if detector_size == "small":
        smoke_calib_path = repo_root / "sp.proc" / "calibration" / "config_torch_smoke_small.json"
    else:
        smoke_calib_path = repo_root / "sp.proc" / "calibration" / "config_torch_smoke.json"

    return str(smoke_calib_path) if smoke_calib_path.exists() else None


def resolve_hkl_path(detector_size: str = "small", calibration_path: Optional[str] = None) -> str:
    """Resolve HKL (MTZ) path based on detector size and calibration presence.

    Per TOOLING-VIS-001 Phase D and docs/data_dependency_manifest.md:86-102.

    Args:
        detector_size: "small" or "full" (default: "small")
        calibration_path: Path to calibration config; if provided, prefers refined MTZ

    Returns:
        Absolute path to MTZ file (scaled.mtz or refined structure factors)

    Contract: Refined Structure Factors (docs/data_dependency_manifest.md:86-102)
    - Override: DBEX_SMOKE_HKL_PATH takes precedence
    - With calibration + small detector: smoke_refined_structure_factors_small.mtz
    - With calibration + full detector: smoke_refined_structure_factors.mtz
    - Without calibration: scaled.mtz
    """
    repo_root = Path(__file__).parent.parent.parent

    # Override takes precedence
    hkl_override = os.environ.get("DBEX_SMOKE_HKL_PATH")
    if hkl_override:
        hkl_path = Path(hkl_override)
        return str(hkl_path) if hkl_path.is_absolute() else str(repo_root / hkl_path)

    # Select detector-size-specific refined MTZ when calibration is enabled
    if calibration_path:
        if detector_size == "small":
            default_refined_mtz = repo_root / "sp.proc" / "calibration" / "smoke_refined_structure_factors_small.mtz"
        else:
            default_refined_mtz = repo_root / "sp.proc" / "calibration" / "smoke_refined_structure_factors.mtz"

        if default_refined_mtz.exists():
            return str(default_refined_mtz)

    # Fallback to scaled.mtz
    return str(repo_root / "scaled.mtz")
