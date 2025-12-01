#!/usr/bin/env python3
"""
Probe Stage A telemetry when Stage C is enabled (initiative: ARCH-REFINE-001, owner: galph)

Inputs:
    --detector-size {small,full}
    --sigma-source {cli_override,metadata}
    --roi-sample-fraction <float> (Stage A ROI sampling fraction; default 0.15)
    --stage-a-roi-mode {roi,panel} (Stage A sampling mode; default roi)
    --output <path to JSON summary>
Data deps: sp.proc/refGeom*/ assets, scaled.mtz, refined MTZ + calibration configs from
           docs/data_dependency_manifest.md (refGeom, smoke calibration bundle).
Outputs: JSON under plans/active/ARCH-REFINE-001/reports/<timestamp>/ summarizing Stage A/C telemetry.
Repro: python plans/active/ARCH-REFINE-001/bin/capture_stage_c_stage_a_probe.py --output <path>
"""

import argparse
import json
import os
import sys
from argparse import Namespace
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    build_structure_factor_grid,
    prepare_refinement_inputs,
)
from dbex.nanobrag_refinement import RefinementConfig, run_nanobrag_refinement
from tests.dbex.test_torch_refine_smoke import create_perturbed_geometry


def _repo_root() -> Path:
    return REPO_ROOT


def _resolve_path(env_value: Optional[str], repo_root: Path) -> Optional[Path]:
    if not env_value:
        return None
    env_path = Path(env_value)
    if env_path.is_absolute():
        return env_path
    return (repo_root / env_path).resolve()


def _resolve_dataset_paths(repo_root: Path, detector_size: str) -> Tuple[Path, Path, Path]:
    if detector_size == "small":
        base = repo_root / "sp.proc" / "refGeom_small"
        return (
            base / "refGeom_small.expt",
            base / "refGeom_small.refl",
            base / "refGeom_small_mask.pkl",
        )
    base = repo_root
    return (
        base / "refGeom.expt",
        base / "refGeom.refl",
        base / "747_mask.pkl",
    )


def _resolve_sigma_map(repo_root: Path, detector_size: str, sigma_source: str) -> Optional[Path]:
    if sigma_source != "metadata":
        return None
    override = _resolve_path(os.environ.get("DBEX_SMOKE_SIGMA_MAP_PATH"), repo_root)
    if override:
        return override
    if detector_size == "small":
        return repo_root / "sp.proc" / "refGeom_small" / "idx-0000_sigma_metadata_small.sigma_tiles.pkl"
    return repo_root / "sp.proc" / "idx-0000_sigma_metadata.sigma_tiles.pkl"


def _resolve_calibration(repo_root: Path, detector_size: str) -> Optional[Path]:
    override = _resolve_path(os.environ.get("DBEX_SMOKE_CALIB_PATH"), repo_root)
    if override:
        return override
    if detector_size == "small":
        candidate = repo_root / "sp.proc" / "calibration" / "config_torch_smoke_small.json"
    else:
        candidate = repo_root / "sp.proc" / "calibration" / "config_torch_smoke.json"
    return candidate if candidate.exists() else None


def _resolve_hkl(repo_root: Path, detector_size: str, calib_path: Optional[Path]) -> Tuple[Path, str]:
    override = _resolve_path(os.environ.get("DBEX_SMOKE_HKL_PATH"), repo_root)
    if override:
        # Use intensity vs amplitude columns heuristic
        mtz_col = "F(+),SIGF(+),F(-),SIGF(-)" if "f(" in override.name.lower() else "I(+),SIGI(+),I(-),SIGI(-)"
        return override, mtz_col
    if calib_path:
        if detector_size == "small":
            refined = repo_root / "sp.proc" / "calibration" / "smoke_refined_structure_factors_small.mtz"
        else:
            refined = repo_root / "sp.proc" / "calibration" / "smoke_refined_structure_factors.mtz"
        if refined.exists():
            return refined, "F(+),SIGF(+),F(-),SIGF(-)"
    return repo_root / "scaled.mtz", "I(+),SIGI(+),I(-),SIGI(-)"


def _build_dataload(repo_root: Path, detector_size: str, sigma_source: str) -> DataLoad:
    expt_path, refl_path, mask_path = _resolve_dataset_paths(repo_root, detector_size)
    sigma_map = _resolve_sigma_map(repo_root, detector_size, sigma_source)
    calib_path = _resolve_calibration(repo_root, detector_size)
    hkl_path, mtz_col = _resolve_hkl(repo_root, detector_size, calib_path)

    required = [expt_path, refl_path, mask_path]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing smoke dataset assets: "
            + ", ".join(missing)
            + ". See docs/data_dependency_manifest.md for generation steps."
        )
    if sigma_map and not sigma_map.exists():
        raise FileNotFoundError(
            f"Requested metadata sigma_map but asset is missing: {sigma_map}. "
            "See docs/data_dependency_manifest.md for the crop commands."
        )

    args = Namespace(
        exptName=str(expt_path),
        reflName=str(refl_path),
        exptIdx=0,
        maskFile=str(mask_path),
        mtzFile=str(hkl_path),
        mtzCol=mtz_col,
        sigma_map=str(sigma_map) if sigma_map else None,
        config_path=str(calib_path) if calib_path else None,
        calibration_config_path=str(calib_path) if calib_path else None,
    )
    return DataLoad(args)


def _build_refinement_inputs(dataload: DataLoad, sigma_source: str):
    detector = dataload.Expt.detector
    trusted_masks = []
    for pid in range(len(detector)):
        slow, fast = detector[pid].get_image_size()[1], detector[pid].get_image_size()[0]
        trusted_masks.append(np.ones((slow, fast), dtype=bool))
    if sigma_source == "metadata":
        if getattr(dataload, "sigma_readout_map", None) is None:
            raise RuntimeError(
                "Requested metadata sigma source but DataLoad lacks sigma_readout_map "
                "(see docs/data_dependency_manifest.md)."
            )
        sigma_readout = np.asarray(dataload.sigma_readout_map, dtype=np.float32)
    else:
        sigma_readout = np.full_like(dataload.data, 3.0, dtype=np.float32)
    return prepare_refinement_inputs(
        data=dataload.data,
        background_image=dataload.background_image,
        trusted_mask=trusted_masks,
        bbox=dataload.bbox,
        pids=dataload.pids,
        detector=dataload.Expt.detector,
        adu_per_photon=None,
        sigma_readout=sigma_readout,
    )


def _build_hkl_grid(dataload: DataLoad):
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=dataload.F.indices(),
        amplitudes=dataload.F.data(),
        device=torch.device("cuda:0"),
        halo=True,
    )
    return hkl_grid, hkl_metadata


def _run_probe(
    detector_size: str,
    sigma_source: str,
    roi_sample_fraction: float,
    stage_a_roi_mode: str,
) -> dict:
    repo_root = _repo_root()
    dataload = _build_dataload(repo_root, detector_size, sigma_source)
    refinement_inputs = _build_refinement_inputs(dataload, sigma_source)
    hkl_grid, hkl_metadata = _build_hkl_grid(dataload)

    baseline_crystal = dataload.Expt.crystal
    baseline_detector = dataload.Expt.detector
    baseline_beam = dataload.Expt.beam

    perturbed_crystal, perturbed_detector, perturbed_beam = create_perturbed_geometry(
        baseline_crystal,
        baseline_detector,
        baseline_beam,
        enable_detector_perturbation=True,
        detector_distance_offset_mm=0.25,
    )

    config = RefinementConfig(
        device="cuda:0",
        dtype=torch.float32,
        history_size=10,
        max_iter=30,
        roi_sample_fraction=roi_sample_fraction,
        enable_stage_a_roi_mode=(stage_a_roi_mode == "roi"),
        full_validation_interval=5,
        min_loss_improvement=0.0,
        enable_hkl_interpolation=True,
        enable_stage_c=True,
        stage_c_min_loss_improvement=0.0,
        stage_c_max_distance_delta_mm=0.5,
        sigma_readout_provenance="external_lookup" if sigma_source == "metadata" else "cli_override",
    )

    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("NANOBRAGG_DISABLE_COMPILE", "1")

    _, telemetry = run_nanobrag_refinement(
        inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,
    )

    telemetry_a = telemetry["A"]
    telemetry_c = telemetry["C"]

    def _extract_stage_payload(stage):
        loss_trace = stage.loss_trace_full or []
        initial = float(loss_trace[0][1]) if loss_trace else None
        final = float(loss_trace[-1][1]) if loss_trace else None
        improvement = None
        if initial and final:
            improvement = (initial - final) / initial
        return {
            "status": stage.status,
            "message": stage.message,
            "roi_mode": getattr(stage, "roi_mode", None),
            "roi_count_total": stage.roi_count_total,
            "roi_count_sampled": stage.roi_count_sampled,
            "initial_loss": initial,
            "final_loss": final,
            "improvement_fraction": improvement,
            "chi_squared_trace": stage.chi_squared_trace_full,
            "param_deltas": stage.param_deltas,
        }

    result = {
        "detector_size": detector_size,
        "sigma_source": sigma_source,
        "roi_sample_fraction": roi_sample_fraction,
        "stage_a_roi_mode": stage_a_roi_mode,
        "stage_a": _extract_stage_payload(telemetry_a),
        "stage_c": _extract_stage_payload(telemetry_c),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture Stage A telemetry with Stage C enabled.")
    parser.add_argument(
        "--detector-size",
        choices=("small", "full"),
        default="small",
        help="Detector footprint for smoke assets (default: small).",
    )
    parser.add_argument(
        "--sigma-source",
        choices=("cli_override", "metadata"),
        default="cli_override",
        help="Sigma sourcing strategy (default: cli_override).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write JSON summary.",
    )
    parser.add_argument(
        "--roi-sample-fraction",
        type=float,
        default=0.15,
        help="Stage A ROI sampling fraction (default: 0.15).",
    )
    parser.add_argument(
        "--stage-a-roi-mode",
        choices=("roi", "panel"),
        default="roi",
        help="Stage A sampling mode (default: roi).",
    )
    args = parser.parse_args()

    summary = _run_probe(
        args.detector_size,
        args.sigma_source,
        args.roi_sample_fraction,
        args.stage_a_roi_mode,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2))
    print(f"Wrote Stage A/C telemetry summary to {output_path}")


if __name__ == "__main__":
    main()
