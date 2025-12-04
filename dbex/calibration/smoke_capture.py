"""
Smoke calibration capture helpers.

This module provides reusable functions to capture calibration metadata from smoke
datasets using DiffBragg refinement. Extracted from shadow pipeline script per
ARCH-PROBE-FREEZE-001 to establish canonical owner APIs for calibration bundle emission.

Owner: dbex.calibration (docs/architecture/calibration_scaling.md)
Contract: docs/data_dependency_manifest.md:86-103

Applied Findings:
- STAGEA-001 (Calibration provenance): Owner modules emit DiffBragg bundles
- SCALE-004 (HKL/calibration precedence): Canonical generation commands
- Diagnostic Script Policy (prompts/supervisor.md:272-309): Business logic lives in owner APIs
"""

import sys
import json
import hashlib
import logging
import datetime
import subprocess
import numpy as np
from pathlib import Path
from argparse import Namespace
from copy import deepcopy

from libtbx.phil import parse
from simtbx.command_line.hopper import phil_scope
from simtbx.diffBragg import hopper_utils
from scitbx.array_family import flex

from dbex.data_load import DataLoad


def compute_sha256(file_path: Path) -> str:
    """
    Compute SHA256 checksum for a file.

    Args:
        file_path: Path to file

    Returns:
        Hexadecimal SHA256 digest
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def to_native(obj):
    """
    Recursively convert numpy/torch types to native Python types for JSON serialization.

    Args:
        obj: Object to convert (can be nested dict/list/array)

    Returns:
        Native Python object
    """
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return [to_native(x) for x in obj.tolist()]
    elif isinstance(obj, dict):
        return {key: to_native(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [to_native(item) for item in obj]
    else:
        return obj


def capture_calibration_metadata(
    expt_path: Path,
    refl_path: Path,
    mtz_path: Path,
    mask_path: Path,
    out_config_path: Path,
    manifest_path: Path,
    *,
    refined_mtz_out_path: Path = None,
    num_macro: int = 3,
    repo_root: Path = None,
    logger=None
):
    """
    Capture calibration metadata from smoke dataset using DiffBragg refinement.

    This function implements the DiffBragg macro-cycle refinement workflow to extract
    calibration parameters (spot_scale_override, beam flux/exposure/beamsize_mm, N_cells)
    and emit a calibration config JSON plus manifest with SHA256 checksums.

    Contract: docs/data_dependency_manifest.md:86-103
    Owner: dbex.calibration (ARCH-PROBE-FREEZE-001)

    Args:
        expt_path: Path to experiment file (e.g., sp.proc/idx-0000_sigma_metadata.expt)
        refl_path: Path to reflections file (e.g., refGeom.refl)
        mtz_path: Path to structure factors MTZ (e.g., scaled.mtz)
        mask_path: Path to trusted mask (e.g., 747_mask.pkl)
        out_config_path: Output path for config_torch_smoke.json
        manifest_path: Output path for manifest JSON
        refined_mtz_out_path: Optional output path for DiffBragg-refined structure factors MTZ
        num_macro: Number of refinement macro cycles (default 3)
        repo_root: Repository root path (defaults to CWD)
        logger: Logger instance (defaults to module logger)

    Returns:
        dict: Calibration metadata config

    Raises:
        Exception: If DataLoad ingestion or refinement fails
    """
    if logger is None:
        logger = logging.getLogger("dbex.calibration.smoke_capture")

    if repo_root is None:
        repo_root = Path.cwd()

    logger.info("=== Smoke Calibration Capture ===")
    logger.info(f"Experiment: {expt_path}")
    logger.info(f"Reflections: {refl_path}")
    logger.info(f"MTZ: {mtz_path}")
    logger.info(f"Mask: {mask_path}")

    # Load data via DataLoad
    logger.info("Loading data via DataLoad...")
    args = Namespace(
        mtzFile=str(mtz_path),
        mtzCol="F,SIGF",
        exptName=str(expt_path),
        exptIdx=0,
        reflName=str(refl_path),
        maskFile=str(mask_path),
    )

    try:
        dl = DataLoad(args)
        logger.info(f"Loaded {len(dl.Refs)} reflections from {refl_path}")
    except Exception as e:
        logger.error(f"Failed to load DataLoad: {e}")
        raise

    # Run DiffBragg refinement to extract calibration parameters
    logger.info("Starting DiffBragg refinement to extract calibration metadata...")
    xtal_refine_phil = repo_root / "dbex" / "dbconfig" / "xtal_refine.phil"
    fhkl_refine_phil = repo_root / "dbex" / "dbconfig" / "fhkl_refine.phil"
    params = phil_scope.fetch(sources=[parse(Path(xtal_refine_phil).read_text())]).extract()
    params_fhkl = phil_scope.fetch(sources=[parse(Path(fhkl_refine_phil).read_text())]).extract()

    for prm in (params, params_fhkl):
        prm.simulator.structure_factors.mtz_name = str(mtz_path)
        prm.simulator.structure_factors.mtz_column = args.mtzCol
        prm.roi.hotpixel_mask = str(mask_path)

    Expt = deepcopy(dl.Expt)
    Famps = dl.F.data().as_numpy_array()
    Finds = dl.F.indices()
    FMap = {h: amp for h, amp in zip(Finds, Famps)}
    devId = 0
    mdl_parm = None
    SIM_fhkl = None

    for cycle in range(num_macro):
        logger.info(f"Refinement macro cycle {cycle+1}/{num_macro}...")
        ref_out = hopper_utils.refine(Expt, dl.Refs, params, return_modeler=True, free_mem=True, gpu_device=devId)
        Expt, _, Modeler, SIM, x = ref_out
        mdl_parm = hopper_utils.get_param_from_x(x, Modeler, as_dict=True)

        for prm in (params, params_fhkl):
            prm.init.Nabc = mdl_parm["Na"], mdl_parm["Nb"], mdl_parm["Nc"]
            prm.init.Ndef = mdl_parm["Nd"], mdl_parm["Ne"], mdl_parm["Nf"]
            prm.init.G = mdl_parm["scale"]

        ref_out_fhkl = hopper_utils.refine(Expt, dl.Refs, params_fhkl, return_modeler=True, free_mem=True, gpu_device=devId)
        _, _, Modeler_fhkl, SIM_fhkl, x_hkl = ref_out_fhkl

        Fidx_to_asu = {i: hkl for hkl, i in SIM_fhkl.asu_map_int.items()}
        refined = np.where(SIM_fhkl.Fhkl_scales != 1)[0]
        new_amps = {}
        for i in refined:
            asu = Fidx_to_asu[i]
            if asu in FMap:
                scale = SIM_fhkl.Fhkl_scales[i]
                new_amp = np.sqrt(scale) * FMap[asu]
                new_amps[asu] = new_amp

        for i_hkl, hkl in enumerate(Finds):
            if hkl in new_amps:
                Famps[i_hkl] = new_amps[hkl]

        # Convert Famps back to flex.double for customized_copy
        Famps_flex = flex.double(Famps)
        Fopt = dl.F.customized_copy(data=Famps_flex)
        Fopt.as_mtz_dataset(column_root_label="F").mtz_object().write(str(repo_root / "_temp.mtz"))

        for prm in (params, params_fhkl):
            prm.simulator.structure_factors.mtz_name = str(repo_root / "_temp.mtz")
            prm.simulator.structure_factors.mtz_column = "F(+),SIGF(+),F(-),SIGF(-)"

        FMap = {h: amp for h, amp in zip(Fopt.indices(), Fopt.data())}
        params.filter_during_refinement.enable = False
        params_fhkl.filter_during_refinement.enable = False

        mdl_parm = hopper_utils.get_param_from_x(x_hkl, Modeler_fhkl, as_dict=True)

    logger.info("Refinement converged. Extracting calibration metadata...")

    # Extract calibration parameters
    spot_scale_override = float(mdl_parm["scale"])
    beam_flux = float(SIM_fhkl.D.flux)
    beam_exposure = 1.0  # Fixed for stills
    beamsize_mm = float(SIM_fhkl.D.beamsize_mm)
    N_cells = [int(mdl_parm["Na"]), int(mdl_parm["Nb"]), int(mdl_parm["Nc"])]

    logger.info(f"Extracted calibration:")
    logger.info(f"  spot_scale_override: {spot_scale_override:.6e}")
    logger.info(f"  beam_flux: {beam_flux:.6e}")
    logger.info(f"  beam_exposure: {beam_exposure}")
    logger.info(f"  beamsize_mm: {beamsize_mm}")
    logger.info(f"  N_cells: {N_cells}")

    # Build calibration config with DiffBragg-style nested schema
    # Per nanobrag_bridge.py:1602-1675, load_calibration_metadata expects:
    # - crystal.scale_override (required)
    # - beam.flux, beam.exposure (required)
    # - beam.beamsize_mm (optional)
    # - crystal.N_cells (optional)
    calibration_config = {
        "metadata": {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "experiment_source": str(expt_path),
            "reflection_source": str(refl_path),
            "mtz_source": str(mtz_path),
            "mask_source": str(mask_path),
            "num_macro_cycles": num_macro,
            "n_reflections": len(dl.Refs),
        },
        "device": "cpu",  # Device placeholder; actual device determined at runtime
        "beam": {
            "flux": beam_flux,
            "exposure": beam_exposure,
            "beamsize_mm": beamsize_mm,
        },
        "crystal": {
            "scale_override": spot_scale_override,
            "N_cells": N_cells,
        },
    }

    # Ensure output directory exists
    out_config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write calibration config
    with open(out_config_path, "w") as fh:
        json.dump(to_native(calibration_config), fh, indent=2)
    logger.info(f"Calibration config written to: {out_config_path}")

    # Compute SHA256 checksum
    config_sha256 = compute_sha256(out_config_path)
    logger.info(f"Config SHA256: {config_sha256[:16]}...")

    # Build manifest
    generator_command = " ".join(sys.argv)

    try:
        git_rev = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True
        ).strip()
    except Exception as e:
        logger.warning(f"Could not get git revision: {e}")
        git_rev = "unknown"

    manifest_data = {
        "dataset_name": "smoke_calibration",
        "generation_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "generator_command": generator_command,
        "git_revision": git_rev,
        "files": {
            "calibration_config": {
                "filename": out_config_path.name,
                "path": str(out_config_path),
                "sha256": config_sha256,
                "size_bytes": int(out_config_path.stat().st_size),
            }
        },
        "inputs": {
            "experiment": str(expt_path),
            "reflections": str(refl_path),
            "mtz": str(mtz_path),
            "mask": str(mask_path),
        },
        "calibration": {
            "crystal": {
                "scale_override": spot_scale_override,
                "N_cells": N_cells,
            },
            "beam": {
                "flux": beam_flux,
                "exposure": beam_exposure,
                "beamsize_mm": beamsize_mm,
            },
        }
    }

    # Ensure manifest directory exists
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    # Write manifest
    with open(manifest_path, "w") as fh:
        json.dump(to_native(manifest_data), fh, indent=2)
    logger.info(f"Manifest written to: {manifest_path}")

    # Copy refined MTZ to output path if requested
    temp_mtz_path = repo_root / "_temp.mtz"
    if refined_mtz_out_path and temp_mtz_path.exists():
        logger.info(f"Persisting refined structure factors to: {refined_mtz_out_path}")
        refined_mtz_out_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(temp_mtz_path, refined_mtz_out_path)

        # Compute SHA256 for refined MTZ
        refined_mtz_sha256 = compute_sha256(refined_mtz_out_path)
        logger.info(f"Refined MTZ SHA256: {refined_mtz_sha256[:16]}...")

        # Add refined MTZ entry to manifest
        manifest_data["files"]["refined_structure_factors"] = {
            "filename": refined_mtz_out_path.name,
            "path": str(refined_mtz_out_path),
            "sha256": refined_mtz_sha256,
            "size_bytes": int(refined_mtz_out_path.stat().st_size),
        }

    # Compute manifest self-checksum
    manifest_sha256 = compute_sha256(manifest_path)
    manifest_data["manifest_sha256"] = manifest_sha256

    # Rewrite manifest with self-checksum
    with open(manifest_path, "w") as fh:
        json.dump(to_native(manifest_data), fh, indent=2)
    logger.info(f"Manifest SHA256: {manifest_sha256[:16]}...")

    # Clean up temp files
    if temp_mtz_path.exists():
        temp_mtz_path.unlink()
        logger.info("Cleaned up temporary _temp.mtz")

    logger.info("=== Calibration Capture Complete ===")
    return calibration_config
