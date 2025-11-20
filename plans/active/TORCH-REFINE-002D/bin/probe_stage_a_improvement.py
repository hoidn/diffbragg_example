#!/usr/bin/env python3
"""
Evaluate Stage A LBFGS improvement for deterministic perturbations (initiative: TORCH-REFINE-002D, owner: galph)
Inputs: --cell-scales (a b c stretch factors), --misset-deg (Z-axis degree misset), optional --max-iter/--roi-sample-fraction/--halo-width
Data deps: refGeom assets (refGeom.expt/refGeom.refl/scaled.mtz), 747_mask.pkl
Outputs: JSON metrics written to --out-json (default: stdout only) under plans/active/TORCH-REFINE-002D/reports/<timestamp>/
Repro: python plans/active/TORCH-REFINE-002D/bin/probe_stage_a_improvement.py --cell-scales 1.05 1.03 1.03 --misset-deg 5.0 --out-json <path>
"""

import argparse
import json
import math
import os
from pathlib import Path
from typing import Tuple

import numpy as np
import torch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe Stage A improvement for deterministic perturbations.")
    parser.add_argument(
        "--cell-scales",
        nargs=3,
        type=float,
        metavar=("SCALE_A", "SCALE_B", "SCALE_C"),
        default=(1.02, 1.01, 1.01),
        help="Multiplicative stretch factors for unit cell a/b/c axes.",
    )
    parser.add_argument(
        "--misset-deg",
        type=float,
        default=1.5,
        help="Z-axis misset angle in degrees applied to the crystal orientation.",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=30,
        help="LBFGS max iterations (mirrors test_stage_a_expansion default).",
    )
    parser.add_argument(
        "--roi-sample-fraction",
        type=float,
        default=0.15,
        help="Fraction of ROIs sampled per LBFGS iteration.",
    )
    parser.add_argument(
        "--halo-width",
        type=int,
        default=1,
        help="HKL halo padding width (0 disables padding, 1=±1, 2=±2, ...).",
    )
    parser.add_argument(
        "--out-json",
        type=str,
        default=None,
        help="Optional path to write JSON metrics. Directory must exist.",
    )
    return parser.parse_args()


def load_refgeom_assets() -> Tuple:
    """Load canonical refGeom dataset assets."""
    from argparse import Namespace
    from dbex.data_load import DataLoad

    repo_root = Path(__file__).resolve().parents[4]
    args = Namespace(
        exptName=str(repo_root / "refGeom.expt"),
        reflName=str(repo_root / "refGeom.refl"),
        exptIdx=0,
        maskFile=str(repo_root / "747_mask.pkl"),
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
    )

    for attr in ("exptName", "reflName", "maskFile", "mtzFile"):
        if not Path(getattr(args, attr)).exists():
            raise FileNotFoundError(f"Missing refGeom asset: {getattr(args, attr)}")

    dataload = DataLoad(args)
    return dataload, dataload.Expt.crystal, dataload.Expt.detector, dataload.Expt.beam


def build_inputs(dataload):
    from dbex.nanobrag_bridge import prepare_refinement_inputs

    detector = dataload.Expt.detector
    trusted_masks = []
    for pid in range(len(detector)):
        panel_shape = detector[pid].get_image_size()
        mask = np.ones(panel_shape[::-1], dtype=bool)
        trusted_masks.append(mask)

    return prepare_refinement_inputs(
        data=dataload.data,
        background_image=dataload.background_image,
        trusted_mask=trusted_masks,
        bbox=dataload.bbox,
        pids=dataload.pids,
        detector=dataload.Expt.detector,
        adu_per_photon=None,
    )


def perturb_crystal(crystal, cell_scales, misset_deg):
    """Return perturbed crystal applying cell stretches and Z-axis misset."""
    from dxtbx.model import Crystal
    from cctbx import uctbx
    from scitbx.matrix import sqr

    scale_a, scale_b, scale_c = cell_scales
    unit_cell = crystal.get_unit_cell().parameters()

    perturbed_crystal = Crystal(
        real_space_a=crystal.get_real_space_vectors()[0],
        real_space_b=crystal.get_real_space_vectors()[1],
        real_space_c=crystal.get_real_space_vectors()[2],
        space_group=crystal.get_space_group(),
    )

    perturbed_uc = uctbx.unit_cell(
        (
            unit_cell[0] * scale_a,
            unit_cell[1] * scale_b,
            unit_cell[2] * scale_c,
            unit_cell[3],
            unit_cell[4],
            unit_cell[5],
        )
    )
    perturbed_crystal.set_unit_cell(perturbed_uc)

    misset_rad = misset_deg * (math.pi / 180.0)
    cos_z = math.cos(misset_rad)
    sin_z = math.sin(misset_rad)
    rotation_z = sqr(
        [
            cos_z,
            -sin_z,
            0.0,
            sin_z,
            cos_z,
            0.0,
            0.0,
            0.0,
            1.0,
        ]
    )

    U = sqr(perturbed_crystal.get_U())
    perturbed_crystal.set_U(rotation_z * U)
    return perturbed_crystal


def main():
    args = parse_args()

    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("NANOBRAGG_DISABLE_COMPILE", "1")

    dataload, baseline_crystal, detector, beam = load_refgeom_assets()
    refinement_inputs = build_inputs(dataload)

    from dbex.nanobrag_bridge import build_structure_factor_grid
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=dataload.F.indices(),
        amplitudes=dataload.F.data(),
        device=torch.device("cpu"),
        halo=args.halo_width > 0,
    )

    if args.halo_width > 1:
        import torch.nn.functional as F

        pad_width = args.halo_width - 1
        pad = (pad_width, pad_width, pad_width, pad_width, pad_width, pad_width)
        hkl_grid = F.pad(hkl_grid, pad)
        hkl_metadata["h_min"] -= pad_width
        hkl_metadata["h_max"] += pad_width
        hkl_metadata["k_min"] -= pad_width
        hkl_metadata["k_max"] += pad_width
        hkl_metadata["l_min"] -= pad_width
        hkl_metadata["l_max"] += pad_width
        hkl_metadata["h_range"] = int(hkl_grid.shape[0])
        hkl_metadata["k_range"] = int(hkl_grid.shape[1])
        hkl_metadata["l_range"] = int(hkl_grid.shape[2])
        hkl_metadata["has_halo"] = True
        hkl_metadata["halo_width"] = args.halo_width

    from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig

    config = RefinementConfig(
        device="cpu",
        dtype=torch.float32,
        history_size=10,
        max_iter=args.max_iter,
        roi_sample_fraction=args.roi_sample_fraction,
        full_validation_interval=5,
        min_loss_improvement=0.05,
        enable_hkl_interpolation=True,
    )

    perturbed_crystal = perturb_crystal(baseline_crystal, args.cell_scales, args.misset_deg)

    bragg, telemetry = run_nanobrag_refinement(
        inputs=refinement_inputs,
        detector=detector,
        beam=beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        baseline_crystal=baseline_crystal,
    )

    initial_loss = telemetry.loss_trace_full[0][1]
    final_loss = telemetry.loss_trace_full[-1][1]
    improvement = (initial_loss - final_loss) / initial_loss

    metrics = {
        "cell_scales": list(args.cell_scales),
        "misset_deg": args.misset_deg,
        "max_iter": args.max_iter,
        "roi_sample_fraction": args.roi_sample_fraction,
        "iterations": len(telemetry.loss_trace_sample),
        "status": telemetry.status,
        "initial_loss": initial_loss,
        "final_loss": final_loss,
        "improvement_fraction": improvement,
        "improvement_percent": improvement * 100.0,
        "misset_initial": telemetry.param_deltas["misset_xyz_deg"]["initial"],
        "misset_final": telemetry.param_deltas["misset_xyz_deg"]["final"],
        "orientation_norm": telemetry.param_deltas["orientation_vec"]["norm"],
        "hkl_in_range_fraction": hkl_metadata.get("in_range_fraction"),
        "hkl_bounds": {
            "h_min": hkl_metadata.get("h_min"),
            "h_max": hkl_metadata.get("h_max"),
            "k_min": hkl_metadata.get("k_min"),
            "k_max": hkl_metadata.get("k_max"),
            "l_min": hkl_metadata.get("l_min"),
            "l_max": hkl_metadata.get("l_max"),
            "has_halo": hkl_metadata.get("has_halo"),
            "halo_width": hkl_metadata.get("halo_width", 1 if args.halo_width > 0 else 0),
        },
    }

    metrics_json = json.dumps(metrics, indent=2)
    print(metrics_json)

    if args.out_json:
        out_path = Path(args.out_json)
        out_path.write_text(metrics_json + "\n", encoding="utf-8")

    # Touch output to silence unused variable warnings
    _ = bragg  # Bragg array not used further; returned for parity with test harness


if __name__ == "__main__":
    main()
