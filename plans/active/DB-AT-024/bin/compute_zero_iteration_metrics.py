#!/usr/bin/env python3
"""
Compute zero-iteration mapping metrics for canonical assets (initiative: DB-AT-024, owner: galph)
Inputs: scaled.mtz, refGeom.expt, refGeom.refl, 747_mask.pkl in repo root
Outputs: metrics JSON (optional) under plans/active/DB-AT-024/reports/<timestamp>/
Repro: python plans/active/DB-AT-024/bin/compute_zero_iteration_metrics.py --artifact-dir <out_dir>
"""

import argparse
import json
import os
import sys
from pathlib import Path
from statistics import median

import numpy as np
import torch

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    prepare_refinement_inputs,
    build_structure_factor_grid,
    create_detector_config,
    create_beam_config,
    create_crystal_config,
)
from nanobrag_torch.simulator import Simulator
from nanobrag_torch.models.detector import Detector
from nanobrag_torch.models.crystal import Crystal

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mtz", default="scaled.mtz", help="Path to MTZ file")
    ap.add_argument("--mtz-col", default="F,SIGF", help="MTZ column selection")
    ap.add_argument("--expt", default="refGeom.expt", help="Path to Experiment list")
    ap.add_argument("--refl", default="refGeom.refl", help="Path to reflection table")
    ap.add_argument("--mask", default="747_mask.pkl", help="Trusted mask pickle")
    ap.add_argument(
        "--artifact-dir",
        default=None,
        help="Optional output directory for metrics JSON (will be created)",
    )
    return ap.parse_args()


def run(args: argparse.Namespace) -> dict:
    os.environ.setdefault("NANOBRAGG_DISABLE_COMPILE", "1")
    repo_root = Path.cwd()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from tests.fixtures.parity_loader import compute_parity_metrics  # pylint: disable=import-error
    dataload_args = argparse.Namespace(
        mtzFile=str(repo_root / args.mtz),
        mtzCol=args.mtz_col,
        exptName=str(repo_root / args.expt),
        exptIdx=0,
        reflName=str(repo_root / args.refl),
        maskFile=str(repo_root / args.mask),
    )
    dl = DataLoad(dataload_args)
    inputs = prepare_refinement_inputs(
        data=dl.data,
        background_image=dl.background_image,
        trusted_mask=dl.trusted_mask,
        bbox=dl.bbox,
        pids=dl.pids,
        detector=dl.detector,
        adu_per_photon=None,
    )

    device = torch.device("cpu")
    hkl_grid, hkl_meta = build_structure_factor_grid(
        indices=dl.F.indices(),
        amplitudes=dl.F.data(),
        device=device,
    )

    bragg = np.zeros_like(inputs.target, dtype=np.float32)
    create_beam_config(dl.beam)  # Ensures beam metadata validated (unused helper cached)
    crystal_cfg = create_crystal_config(dl.crystal, dl.Expt)

    for pid in range(len(dl.detector)):
        det_cfg = create_detector_config(
            panel=dl.detector[pid],
            beam=dl.beam,
            trusted_mask=inputs.trusted_mask[pid],
        )
        if det_cfg.mask_array is not None and not isinstance(det_cfg.mask_array, torch.Tensor):
            det_cfg.mask_array = torch.tensor(det_cfg.mask_array, dtype=torch.float32, device=device)
        detector_model = Detector(det_cfg, device=device)
        crystal_model = Crystal(crystal_cfg)
        crystal_model.hkl_data = hkl_grid
        crystal_model.hkl_metadata = hkl_meta
        simulator = Simulator(detector=detector_model, crystal=crystal_model, device=device)
        panel_output = simulator.run().detach().cpu().numpy().astype(np.float32)
        bragg[pid] = panel_output
        del simulator

    metrics = []
    correlations = []
    localizations = []
    for pid, (x0, x1, y0, y1) in inputs.panel_slices:
        pred = bragg[pid, y0:y1, x0:x1]
        targ = inputs.target[pid, y0:y1, x0:x1]
        mask = inputs.loss_mask[pid, y0:y1, x0:x1]
        roi_metrics = compute_parity_metrics(pred, targ, loss_mask=mask)
        metrics.append(roi_metrics)
        if not np.isnan(roi_metrics.correlation):
            correlations.append(float(roi_metrics.correlation))
        if not np.isnan(roi_metrics.localization):
            localizations.append(float(roi_metrics.localization))

    success_rate = float(np.mean([loc == 1.0 for loc in localizations])) if localizations else float("nan")
    result = {
        "n_roi": len(metrics),
        "corr_median": median(correlations) if correlations else float("nan"),
        "corr_min": float(min(correlations)) if correlations else float("nan"),
        "corr_max": float(max(correlations)) if correlations else float("nan"),
        "localization_mean": float(np.mean(localizations)) if localizations else float("nan"),
        "localization_success_rate": success_rate,
        "global_scale_hint": float(inputs.global_scale_hint) if inputs.global_scale_hint is not None else None,
        "hkl_stats": hkl_meta,
    }
    return result


def main() -> None:
    args = parse_args()
    with torch.no_grad():
        metrics = run(args)
    print(json.dumps(metrics, indent=2))
    if args.artifact_dir:
        out_dir = Path(args.artifact_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "mapping_metrics.json", "w") as fh:
            json.dump(metrics, fh, indent=2)


if __name__ == "__main__":
    main()
