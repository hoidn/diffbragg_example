#!/usr/bin/env python3
"""
Diagnose DB_AT_024 zero-iteration scaling gap by comparing per-ROI target and
Bragg intensities (initiative: MAP-SCALE-001, owner: galph).
Inputs: canonical refGeom assets in repo root (scaled.mtz, refGeom.expt, refGeom.refl, 747_mask.pkl)
Data deps: uses DataLoad + nanobrag_bridge helpers (no external downloads).
Outputs: JSON under plans/active/MAP-SCALE-001/reports/<timestamp>/scale_probe.json
Repro: python plans/active/MAP-SCALE-001/bin/compute_mapping_scale_probe.py --artifact-dir <path>
"""

import argparse
import json
from pathlib import Path

import numpy as np

from dbex.data_load import DataLoad
from dbex.refinement.inputs import prepare_refinement_inputs
from dbex.nanobrag_bridge import simulate_forward_once


def compute_roi_stats(bragg, inputs):
    """Return per-ROI statistics including target/bragg means and ratios."""
    roi_rows = []
    ratios = []

    for idx, (pid, (x0, x1, y0, y1)) in enumerate(inputs.panel_slices):
        pred = bragg[pid, y0:y1, x0:x1]
        targ = inputs.target[pid, y0:y1, x0:x1]
        mask = inputs.loss_mask[pid, y0:y1, x0:x1]

        # Use masked pixels only (where loss_mask == True)
        masked_pred = pred[mask]
        masked_targ = targ[mask]

        if masked_pred.size == 0:
            pred_mean = float("nan")
            targ_mean = float("nan")
            ratio = float("nan")
        else:
            pred_mean = float(np.mean(masked_pred))
            targ_mean = float(np.mean(masked_targ))
            ratio = float(targ_mean / pred_mean) if pred_mean != 0 else float("inf")

        roi_rows.append(
            {
                "roi_idx": idx,
                "panel_id": int(pid),
                "pred_mean": pred_mean,
                "targ_mean": targ_mean,
                "ratio_targ_over_pred": ratio,
                "pred_max": float(np.max(masked_pred)) if masked_pred.size else float("nan"),
                "targ_max": float(np.max(masked_targ)) if masked_targ.size else float("nan"),
            }
        )

        if np.isfinite(ratio):
            ratios.append(ratio)

    return roi_rows, ratios


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-dir",
        required=True,
        help="Directory to write scale_probe.json (will be created if missing)",
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

    roi_rows, ratios = compute_roi_stats(bragg=bragg, inputs=inputs)

    pred_mean = float(np.mean(bragg))
    targ_mean = float(np.mean(inputs.target[inputs.loss_mask]))
    global_ratio = float(targ_mean / pred_mean) if pred_mean != 0 else float("inf")

    output = {
        "n_roi": len(roi_rows),
        "bragg_mean": pred_mean,
        "bragg_max": float(np.max(bragg)),
        "target_mean": targ_mean,
        "global_scale_hint": inputs.global_scale_hint,
        "global_ratio": global_ratio,
        "diagnostics": diagnostics,
        "ratio_stats": {
            "median": float(np.median(ratios)) if ratios else float("nan"),
            "min": float(np.min(ratios)) if ratios else float("nan"),
            "max": float(np.max(ratios)) if ratios else float("nan"),
        },
        "roi_rows": roi_rows,
    }

    out_path = artifact_dir / "scale_probe.json"
    with open(out_path, "w") as fh:
        json.dump(output, fh, indent=2)

    print(f"Wrote scale diagnostics to {out_path}")


if __name__ == "__main__":
    main()
