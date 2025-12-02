#!/usr/bin/env python3
"""
Compare zero-iteration simulator outputs against the canonical `bragg_torch.npy`
baseline (initiative: MAP-SCALE-001, owner: galph).
Inputs: scale probe JSON (per `compute_mapping_scale_probe.py`) and canonical fixtures.
Data deps: canonical refGeom assets in repo root; golden fixtures under tests/fixtures/.
Outputs: `golden_comparison.json` under artifact directory with ratio diagnostics.
Repro: python plans/active/MAP-SCALE-001/bin/compare_simulator_to_golden.py \
           --scale-probe plans/active/MAP-SCALE-001/reports/<ts>/scale_probe.json \
           --artifact-dir plans/active/MAP-SCALE-001/reports/<ts>
"""

import argparse
import json
import math
from pathlib import Path
from typing import List, Optional

import numpy as np

from dbex.data_load import DataLoad
from dbex.refinement.inputs import prepare_refinement_inputs


def summarize(values: List[float]) -> dict:
    """Return basic summary stats ignoring NaN/inf."""
    finite = [float(v) for v in values if math.isfinite(v)]
    if not finite:
        return {"median": float("nan"), "min": float("nan"), "max": float("nan"), "count": 0}
    arr = np.array(finite, dtype=np.float64)
    return {
        "median": float(np.median(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "count": int(arr.size),
    }


def locate_panel_metrics(repo_root: Path) -> Optional[Path]:
    """Return the most recent torch panel metrics JSON if available."""
    candidates = sorted(
        repo_root.glob(
            "plans/active/NANOBRAG-GOLDEN-001/reports/*/golden_dataset/torch/panel_metrics.json"
        )
    )
    return candidates[-1] if candidates else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--scale-probe",
        required=True,
        help="Path to scale_probe.json produced by compute_mapping_scale_probe.py",
    )
    ap.add_argument(
        "--artifact-dir",
        required=True,
        help="Directory to write golden_comparison.json",
    )
    ap.add_argument(
        "--fixtures-root",
        default="tests/fixtures/golden_data/simple_cubic",
        help="Directory containing canonical bragg_torch.npy",
    )
    args = ap.parse_args()

    repo_root = Path.cwd()
    scale_probe_path = (repo_root / args.scale_probe).resolve()
    if not scale_probe_path.exists():
        raise FileNotFoundError(f"Scale probe JSON not found: {scale_probe_path}")

    with open(scale_probe_path, "r") as fh:
        scale_probe = json.load(fh)

    roi_rows = scale_probe.get("roi_rows", [])
    if not roi_rows:
        raise ValueError(f"No ROI rows present in {scale_probe_path}")

    fixtures_root = (repo_root / args.fixtures_root).resolve()
    golden_path = fixtures_root / "bragg_torch.npy"
    if not golden_path.exists():
        raise FileNotFoundError(f"Golden bragg tensor not found: {golden_path}")
    golden = np.load(golden_path)

    panel_metrics_path = locate_panel_metrics(repo_root)
    post_sim_scale = None
    spot_scale_override = None
    if panel_metrics_path:
        with open(panel_metrics_path, "r") as fh:
            panel_metrics = json.load(fh)
        if panel_metrics:
            post_sim_scale = float(panel_metrics[0].get("post_sim_scale_factor", float("nan")))
            if math.isfinite(post_sim_scale):
                spot_scale_override = float(post_sim_scale**2)

    assets = {
        "mtz": repo_root / "scaled.mtz",
        "expt": repo_root / "refGeom.expt",
        "refl": repo_root / "refGeom.refl",
        "mask": repo_root / "747_mask.pkl",
    }
    missing_assets = [name for name, path in assets.items() if not path.exists()]
    if missing_assets:
        raise FileNotFoundError(f"Missing canonical assets: {missing_assets}")

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

    comparison_rows = []
    ratios_golden_over_pred = []
    ratios_target_over_golden = []
    ratios_pred_over_golden_raw = []

    for idx, (panel_id, (x0, x1, y0, y1)) in enumerate(inputs.panel_slices):
        roi_info = roi_rows[idx]
        mask = inputs.loss_mask[panel_id, y0:y1, x0:x1]

        golden_roi = golden[panel_id, y0:y1, x0:x1]
        golden_masked = golden_roi[mask]
        golden_mean = float(np.mean(golden_masked)) if golden_masked.size else float("nan")
        golden_max = float(np.max(golden_masked)) if golden_masked.size else float("nan")

        target_roi = inputs.target[panel_id, y0:y1, x0:x1]
        target_masked = target_roi[mask]
        target_mean = float(np.mean(target_masked)) if target_masked.size else float("nan")

        pred_mean = float(roi_info.get("pred_mean", float("nan")))
        if math.isfinite(pred_mean) and pred_mean != 0.0:
            ratio_golden_pred = float(golden_mean / pred_mean)
        else:
            ratio_golden_pred = float("inf")

        if math.isfinite(golden_mean) and golden_mean != 0.0:
            ratio_target_golden = float(target_mean / golden_mean)
        else:
            ratio_target_golden = float("inf")

        ratios_golden_over_pred.append(ratio_golden_pred)
        ratios_target_over_golden.append(ratio_target_golden)

        golden_raw_mean = float(golden_mean / post_sim_scale) if post_sim_scale else float("nan")

        if math.isfinite(golden_raw_mean) and golden_raw_mean != 0.0:
            ratio_pred_over_golden_raw = float(pred_mean / golden_raw_mean)
        else:
            ratio_pred_over_golden_raw = float("inf")
        ratios_pred_over_golden_raw.append(ratio_pred_over_golden_raw)

        comparison_rows.append(
            {
                "roi_idx": int(roi_info.get("roi_idx", idx)),
                "panel_id": int(roi_info.get("panel_id", panel_id)),
                "loss_pixels": int(mask.sum()),
                "pred_mean": pred_mean,
                "target_mean": target_mean,
                "golden_mean": golden_mean,
                "golden_max": golden_max,
                "ratio_target_over_pred": float(roi_info.get("ratio_targ_over_pred", float("nan"))),
                "ratio_golden_over_pred": ratio_golden_pred,
                "ratio_target_over_golden": ratio_target_golden,
                "ratio_pred_over_golden_raw": ratio_pred_over_golden_raw,
            }
        )

    artifact_dir = (repo_root / args.artifact_dir).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)

    golden_masked = golden[inputs.loss_mask]
    target_masked = inputs.target[inputs.loss_mask]
    golden_masked_mean = float(golden_masked.mean()) if golden_masked.size else float("nan")
    target_masked_mean = float(target_masked.mean()) if target_masked.size else float("nan")
    global_metrics = {
        "target_mean_masked": target_masked_mean,
        "golden_mean_masked": golden_masked_mean,
        "target_over_golden_global": float(target_masked_mean / golden_masked_mean)
        if golden_masked.size and golden_masked_mean != 0.0
        else float("inf"),
    }
    if post_sim_scale and golden_masked.size:
        golden_raw_mean_masked = golden_masked_mean / post_sim_scale
        global_metrics["golden_raw_mean_masked"] = float(golden_raw_mean_masked)
        global_metrics["target_over_golden_raw_global"] = float(
            target_masked_mean / golden_raw_mean_masked if golden_raw_mean_masked != 0.0 else float("inf")
        )

    output = {
        "scale_probe_path": str(scale_probe_path.relative_to(repo_root)),
        "fixtures_root": str(fixtures_root.relative_to(repo_root)),
        "panel_metrics_path": (
            str(panel_metrics_path.relative_to(repo_root)) if panel_metrics_path else None
        ),
        "post_sim_scale_factor": post_sim_scale,
        "spot_scale_override": spot_scale_override,
        "scale_probe_global_ratio": float(scale_probe.get("global_ratio", float("nan"))),
        "global_metrics": global_metrics,
        "ratio_stats": {
            "golden_over_zero_iter": summarize(ratios_golden_over_pred),
            "target_over_golden": summarize(ratios_target_over_golden),
            "zero_iter_over_golden_raw": summarize(ratios_pred_over_golden_raw),
        },
        "comparison_rows": comparison_rows,
    }

    out_path = artifact_dir / "golden_comparison.json"
    with open(out_path, "w") as fh:
        json.dump(output, fh, indent=2)

    print(f"Wrote comparison metrics to {out_path}")


if __name__ == "__main__":
    main()
