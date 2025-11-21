#!/usr/bin/env python3
"""
Probe Stage C detector microslip improvement against the refGeom dataset
(initiative: TORCH-REFINE-003, owner: galph).

Inputs: repository-root nanobrag assets (refGeom.expt/refl, scaled.mtz, 747_mask.pkl)
Data deps: refGeom.expt, refGeom.refl, scaled.mtz, 747_mask.pkl
Outputs: telem JSON under plans/active/TORCH-REFINE-003/reports/<timestamp>/stage_c_improvement_probe.json
Repro: python plans/active/TORCH-REFINE-003/bin/probe_stage_c_improvement.py --output <path> [--detector-offset-mm 0.25]
"""

import argparse
import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any, Dict

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


def run_probe(detector_offset_mm: float) -> Dict[str, Any]:
    """
    Execute Stage C refinement probe with a deterministic detector offset.

    Returns:
        Dict with Stage A/C metrics and Stage C telemetry summary.
    """
    repo_root = Path(".")
    refl_path = repo_root / "refGeom.refl"

    if not refl_path.exists():
        raise FileNotFoundError(
            f"Required refGeom.refl missing at {refl_path}; "
            "regenerate via README.md instructions before running probe."
        )

    args = Namespace(
        exptName=str(repo_root / "refGeom.expt"),
        reflName=str(refl_path),
        exptIdx=0,
        maskFile=str(repo_root / "747_mask.pkl"),
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
    )

    data_load = DataLoad(args)

    detector = data_load.Expt.detector
    trusted_masks = []
    for pid in range(len(detector)):
        fast_px, slow_px = detector[pid].get_image_size()
        trusted_masks.append(np.ones((slow_px, fast_px), dtype=bool))

    refinement_inputs = prepare_refinement_inputs(
        data=data_load.data,
        background_image=data_load.background_image,
        trusted_mask=trusted_masks,
        bbox=data_load.bbox,
        pids=data_load.pids,
        detector=detector,
        adu_per_photon=None,
    )

    hkl_indices = data_load.F.indices()
    hkl_amplitudes = data_load.F.data()

    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=torch.device("cpu"),
        halo=True,
    )

    baseline_crystal = data_load.Expt.crystal
    baseline_detector = data_load.Expt.detector
    baseline_beam = data_load.Expt.beam

    perturbed_crystal, perturbed_detector, perturbed_beam = create_perturbed_geometry(
        baseline_crystal,
        baseline_detector,
        baseline_beam,
        enable_detector_perturbation=True,
        detector_distance_offset_mm=detector_offset_mm,
    )

    config = RefinementConfig(
        device="cpu",
        dtype=torch.float32,
        history_size=10,
        max_iter=30,
        roi_sample_fraction=0.15,
        full_validation_interval=5,
        min_loss_improvement=0.002,
        enable_hkl_interpolation=True,
        enable_stage_c=True,
        stage_c_min_loss_improvement=0.05,
        stage_c_max_distance_delta_mm=0.5,
    )

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

    stage_a_loss_trace = telemetry_a.loss_trace_full
    stage_c_loss_trace = telemetry_c.loss_trace_full

    stage_a_initial = stage_a_loss_trace[0][1]
    stage_a_final = stage_a_loss_trace[-1][1]
    stage_c_final = stage_c_loss_trace[-1][1]

    stage_a_improvement = (stage_a_initial - stage_a_final) / stage_a_initial
    stage_c_improvement = (stage_a_final - stage_c_final) / stage_a_final

    offsets = [
        float(val["final"]) for _, val in sorted(telemetry_c.param_deltas.items())
    ]
    max_abs_offset = max(abs(o) for o in offsets) if offsets else 0.0

    return {
        "stage_a_improvement_pct": stage_a_improvement * 100.0,
        "stage_c_improvement_pct": stage_c_improvement * 100.0,
        "stage_a_final_loss": float(stage_a_final),
        "stage_c_final_loss": float(stage_c_final),
        "stage_c_iterations": len(telemetry_c.loss_trace_sample),
        "stage_c_status": telemetry_c.status,
        "stage_c_message": telemetry_c.message,
        "max_abs_offset_mm": max_abs_offset,
        "offset_samples_mm": offsets[:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe Stage C detector improvement metrics."
    )
    parser.add_argument(
        "--detector-offset-mm",
        type=float,
        default=0.25,
        help="Alternating detector distance offset applied during create_perturbed_geometry.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to write JSON metrics (will be overwritten).",
    )

    args = parser.parse_args()

    metrics = run_probe(detector_offset_mm=args.detector_offset_mm)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as fh:
        json.dump(metrics, fh, indent=2)

    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
