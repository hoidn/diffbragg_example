#!/usr/bin/env python3
"""
Evaluate candidate scaling strategies for DB_AT_024 zero-iteration mapping
(initiative: MAP-SCALE-001, owner: galph).
Inputs: canonical refGeom assets (scaled.mtz, refGeom.expt, refGeom.refl, 747_mask.pkl)
Outputs: JSON metrics under plans/active/MAP-SCALE-001/reports/<timestamp>/strategy_<mode>.json
Repro: python plans/active/MAP-SCALE-001/bin/evaluate_mapping_strategy.py --mode mean_ratio --artifact-dir <path>
"""

import argparse
import json
import sys
from pathlib import Path
from statistics import median

import numpy as np

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import prepare_refinement_inputs, simulate_forward_once


def apply_scaling(bragg, inputs, mode: str):
    """Return scaled bragg tensor and applied scale factor."""
    masked_pred = bragg[inputs.loss_mask]
    masked_targ = inputs.target[inputs.loss_mask]

    pred_mean = float(np.mean(masked_pred)) if masked_pred.size else 0.0
    targ_mean = float(np.mean(masked_targ)) if masked_targ.size else 0.0

    if mode == "none":
        scale = 1.0
    elif mode == "global_hint":
        # Use global_scale_hint directly (intended as ADU mean)
        scale = inputs.global_scale_hint if inputs.global_scale_hint else 1.0
    elif mode == "mean_ratio":
        if pred_mean > 0:
            scale = (inputs.global_scale_hint or targ_mean) / pred_mean
        else:
            scale = 1.0
    else:
        raise ValueError(f"Unsupported mode '{mode}'")

    return bragg * scale, scale, pred_mean, targ_mean


def compute_metrics(bragg, inputs):
    """Compute correlation/localization metrics per ROI."""
    from tests.fixtures.parity_loader import compute_parity_metrics

    roi_metrics = []
    correlations = []
    localizations = []

    for pid, (x0, x1, y0, y1) in inputs.panel_slices:
        pred = bragg[pid, y0:y1, x0:x1]
        targ = inputs.target[pid, y0:y1, x0:x1]
        mask = inputs.loss_mask[pid, y0:y1, x0:x1]

        roi_result = compute_parity_metrics(pred, targ, loss_mask=mask)
        roi_metrics.append(roi_result)

        if not np.isnan(roi_result.correlation):
            correlations.append(float(roi_result.correlation))
        if not np.isnan(roi_result.localization):
            localizations.append(float(roi_result.localization))

    summary_metrics = {
        "n_roi": len(roi_metrics),
        "corr_median": median(correlations) if correlations else float("nan"),
        "corr_min": float(min(correlations)) if correlations else float("nan"),
        "corr_max": float(max(correlations)) if correlations else float("nan"),
        "localization_mean": float(np.mean(localizations)) if localizations else float("nan"),
        "localization_success_rate": float(np.mean([loc == 1.0 for loc in localizations])) if localizations else float("nan"),
    }

    return summary_metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["none", "global_hint", "mean_ratio"],
        required=True,
        help="Scaling strategy to evaluate",
    )
    parser.add_argument(
        "--artifact-dir",
        required=True,
        help="Directory to write JSON metrics",
    )
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    repo_root = Path.cwd()
    assets = {
        "mtz": repo_root / "scaled.mtz",
        "expt": repo_root / "refGeom.expt",
        "refl": repo_root / "refGeom.refl",
        "mask": repo_root / "747_mask.pkl",
    }
    missing = [name for name, path in assets.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing canonical assets: {missing}")

    # Ensure repo root on sys.path for tests.* imports
    sys.path.append(str(repo_root))

    dl_args = argparse.Namespace(
        mtzFile=str(assets["mtz"]),
        mtzCol="F,SIGF",
        exptName=str(assets["expt"]),
        exptIdx=0,
        reflName=str(assets["refl"]),
        maskFile=str(assets["mask"]),
    )
    dl = DataLoad(dl_args)

    inputs = prepare_refinement_inputs(
        data=dl.data,
        background_image=dl.background_image,
        trusted_mask=dl.trusted_mask,
        bbox=dl.bbox,
        pids=dl.pids,
        detector=dl.detector,
        adu_per_photon=None,
    )

    bragg, diagnostics = simulate_forward_once(
        inputs=inputs,
        detector=dl.detector,
        beam=dl.beam,
        crystal=dl.crystal,
        experiment=dl.Expt,
        hkl_indices=dl.F.indices(),
        hkl_amplitudes=dl.F.data(),
        spot_scale_override=None,
        device="cpu",
    )

    bragg_scaled, scale_factor, pred_mean, targ_mean = apply_scaling(bragg, inputs, args.mode)
    metrics = compute_metrics(bragg_scaled, inputs)

    output = {
        "mode": args.mode,
        "scale_factor": scale_factor,
        "pred_mean_before": pred_mean,
        "target_mean": targ_mean,
        "metrics": metrics,
        "diagnostics": diagnostics,
    }

    out_path = artifact_dir / f"strategy_{args.mode}.json"
    with open(out_path, "w") as fh:
        json.dump(output, fh, indent=2)

    print(f"Wrote strategy metrics to {out_path}")


if __name__ == "__main__":
    main()
