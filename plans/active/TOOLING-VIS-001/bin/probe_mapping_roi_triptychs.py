#!/usr/bin/env python3
"""
T2 Probe: Per-ROI Mapping Diagnostics for Stage A Alignment

Loads the metadata-sigma smoke dataset (respecting DBEX_SMOKE_* env + optional --mtz-path),
computes per-ROI correlation/MSE/scale stats, and writes:
  - roi_metrics.json (sorted list of ROI stats)
  - roi_histogram.json (bin counts for correlation/MSE/scale)
  - N lowest-correlation ROIs as PNG/NPZ triptychs using dbex.vis.triptych

This probe helps diagnose whether Stage A's negative ROI correlations stem from
geometric misregistration or structural mismatch before touching physics.

Usage:
    export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
    export DBEX_SMOKE_SIGMA_SOURCE=metadata
    export DBEX_SMOKE_DETECTOR_SIZE=small

    python plans/active/TOOLING-VIS-001/bin/probe_mapping_roi_triptychs.py \\
        --roi-count 16 \\
        --out-dir plans/active/TOOLING-VIS-001/reports/<timestamp>/roi_diagnostics
"""
import argparse
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch

# Add repo root to path for imports
# Script is in plans/active/TOOLING-VIS-001/bin/, so go up 4 levels to repo root
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from dbex.data_load import DataLoad
from dbex.vis.mapping import build_mapping_stage_a_context
from dbex.vis.triptych import plot_triptych


def _compute_roi_metrics(
    data_roi: np.ndarray,
    model_roi: np.ndarray,
    mask_roi: np.ndarray,
) -> Dict:
    """
    Compute per-ROI correlation, MSE, and scale statistics.

    Args:
        data_roi: Target data ROI (slow, fast) [ADU]
        model_roi: Model Bragg ROI (slow, fast) [ADU]
        mask_roi: Loss mask ROI (slow, fast) [bool]

    Returns:
        Dictionary with correlation, mse, scale, masked_pixel_count.
    """
    mask_flat = np.asarray(mask_roi, dtype=bool)
    masked_pixels = int(np.sum(mask_flat))

    if masked_pixels == 0:
        return {
            "correlation": float("nan"),
            "mse": float("nan"),
            "scale": float("nan"),
            "masked_pixel_count": 0,
        }

    data = np.asarray(data_roi, dtype=np.float64)[mask_flat]
    model = np.asarray(model_roi, dtype=np.float64)[mask_flat]

    # Correlation
    data_centered = data - data.mean()
    model_centered = model - model.mean()
    denom = np.linalg.norm(data_centered) * np.linalg.norm(model_centered)
    if denom <= 0:
        corr = float("nan")
    else:
        corr = float(np.dot(data_centered, model_centered) / denom)

    # MSE
    mse = float(np.mean((data - model) ** 2))

    # Scale (closed-form: scale = sum(data * model) / sum(model * model))
    num = np.sum(data * model)
    den = np.sum(model * model)
    if den > 1e-12:
        scale = float(num / den)
    else:
        scale = float("nan")

    return {
        "correlation": corr,
        "mse": mse,
        "scale": scale,
        "masked_pixel_count": masked_pixels,
    }


def compute_roi_diagnostics(
    dataload: DataLoad,
    default_sigma_readout: float,
    sigma_source: str,
    device: str = "cpu",
    roi_count: int = 16,
) -> Dict:
    """
    Build mapping context, compute per-ROI metrics, and prepare triptych data.

    Args:
        dataload: DataLoad instance with experiment/reflection/MTZ data.
        default_sigma_readout: Default sigma readout value (ADU).
        sigma_source: Provenance label for sigma ('metadata' or 'cli_override').
        device: Device for mapping context (cpu or cuda:0).
        roi_count: Number of lowest-correlation ROIs to save as triptychs.

    Returns:
        Dictionary with:
          - roi_metrics: sorted list of per-ROI stats (lowest correlation first)
          - roi_histogram: bin counts for correlation/MSE/scale
          - triptych_rois: list of (roi_idx, data, model, variance, hkl, corr) for lowest-corr ROIs
          - error: error message if build fails, else None
    """
    result = {
        "error": None,
        "sigma_source": sigma_source,
        "device": device,
        "roi_count_requested": roi_count,
        "roi_metrics": [],
        "roi_histogram": {},
        "triptych_rois": [],
    }

    # Build mapping context
    print(f"Building mapping context on {device}...")
    try:
        mapping_context = build_mapping_stage_a_context(
            dataload,
            default_sigma_readout=default_sigma_readout,
            device=device,
        )

        bragg_zero = mapping_context.bragg_zero_iter
        inputs = mapping_context.inputs

        print(f"Mapping context built: {len(inputs.panel_slices)} ROIs")
        print(f"  Target shape: {inputs.target.shape}")
        print(f"  Bragg shape: {bragg_zero.shape}")
        print(f"  Loss mask pixels: {int(inputs.loss_mask.sum())}")

    except Exception as e:
        result["error"] = f"Mapping context build failed: {e}"
        print(f"ERROR: {result['error']}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        return result

    # Compute per-ROI metrics
    print("Computing per-ROI metrics...")
    roi_metrics_list = []
    for roi_idx, (pid, bbox) in enumerate(inputs.panel_slices):
        x0, x1, y0, y1 = bbox
        data_roi = inputs.target[int(pid), y0:y1, x0:x1]
        model_roi = bragg_zero[int(pid), y0:y1, x0:x1]
        mask_roi = inputs.loss_mask[int(pid), y0:y1, x0:x1]

        metrics = _compute_roi_metrics(data_roi, model_roi, mask_roi)

        roi_metrics_list.append({
            "roi_idx": roi_idx,
            "panel_id": int(pid),
            "bbox": [int(x0), int(x1), int(y0), int(y1)],
            "correlation": metrics["correlation"],
            "mse": metrics["mse"],
            "scale": metrics["scale"],
            "masked_pixel_count": metrics["masked_pixel_count"],
        })

    # Sort by correlation (lowest first, NaN at end)
    def sort_key(x):
        c = x["correlation"]
        return (np.isnan(c), c if not np.isnan(c) else float("inf"))

    roi_metrics_list.sort(key=sort_key)
    result["roi_metrics"] = roi_metrics_list

    # Compute histograms
    print("Computing histograms...")
    valid_corrs = [m["correlation"] for m in roi_metrics_list if np.isfinite(m["correlation"])]
    valid_mses = [m["mse"] for m in roi_metrics_list if np.isfinite(m["mse"])]
    valid_scales = [m["scale"] for m in roi_metrics_list if np.isfinite(m["scale"])]

    if valid_corrs:
        corr_hist, corr_bins = np.histogram(valid_corrs, bins=20, range=(-1.0, 1.0))
        result["roi_histogram"]["correlation_counts"] = corr_hist.tolist()
        result["roi_histogram"]["correlation_bins"] = corr_bins.tolist()
    else:
        result["roi_histogram"]["correlation_counts"] = []
        result["roi_histogram"]["correlation_bins"] = []

    if valid_mses:
        mse_hist, mse_bins = np.histogram(valid_mses, bins=20)
        result["roi_histogram"]["mse_counts"] = mse_hist.tolist()
        result["roi_histogram"]["mse_bins"] = mse_bins.tolist()
    else:
        result["roi_histogram"]["mse_counts"] = []
        result["roi_histogram"]["mse_bins"] = []

    if valid_scales:
        scale_hist, scale_bins = np.histogram(valid_scales, bins=20, range=(0.0, 5.0))
        result["roi_histogram"]["scale_counts"] = scale_hist.tolist()
        result["roi_histogram"]["scale_bins"] = scale_bins.tolist()
    else:
        result["roi_histogram"]["scale_counts"] = []
        result["roi_histogram"]["scale_bins"] = []

    # Prepare triptych data for lowest-correlation ROIs
    print(f"Preparing triptych data for {roi_count} lowest-correlation ROIs...")
    triptych_rois = []
    for m in roi_metrics_list[:roi_count]:
        roi_idx = m["roi_idx"]
        pid = m["panel_id"]
        x0, x1, y0, y1 = m["bbox"]

        data_roi = inputs.target[pid, y0:y1, x0:x1]
        model_roi = bragg_zero[pid, y0:y1, x0:x1]
        mask_roi = inputs.loss_mask[pid, y0:y1, x0:x1]

        # Compute variance (per spec-db-core.md: V = I_model + sigma_readout^2, clamped to sigma_floor^2)
        sigma_floor = mapping_context.sigma_floor_value
        variance_roi = np.maximum(
            model_roi + default_sigma_readout ** 2,
            sigma_floor ** 2
        )

        triptych_rois.append({
            "roi_idx": roi_idx,
            "panel_id": pid,
            "bbox": m["bbox"],
            "data": data_roi,
            "model": model_roi,
            "variance": variance_roi,
            "mask": mask_roi,
            "correlation": m["correlation"],
            "mse": m["mse"],
            "scale": m["scale"],
        })

    result["triptych_rois"] = triptych_rois

    # Summary stats
    result["summary"] = {
        "n_rois": len(roi_metrics_list),
        "correlation_median": float(np.median(valid_corrs)) if valid_corrs else float("nan"),
        "correlation_min": float(np.min(valid_corrs)) if valid_corrs else float("nan"),
        "correlation_max": float(np.max(valid_corrs)) if valid_corrs else float("nan"),
        "mse_median": float(np.median(valid_mses)) if valid_mses else float("nan"),
        "scale_median": float(np.median(valid_scales)) if valid_scales else float("nan"),
        "spot_scale_override": float(mapping_context.calibration.get("spot_scale_override", 1.0)) if mapping_context.calibration else 1.0,
        "sigma_floor_value": float(sigma_floor),
        "hkl_source": mapping_context.diagnostics.get("hkl_telemetry", {}).get("hkl_source", "unknown"),
        "hkl_path": mapping_context.diagnostics.get("hkl_telemetry", {}).get("hkl_path", "unknown"),
        "hkl_count": len(mapping_context.hkl_indices) if hasattr(mapping_context, 'hkl_indices') else 0,
    }

    print(f"Summary: n_rois={result['summary']['n_rois']}, "
          f"corr_median={result['summary']['correlation_median']:.6f}, "
          f"corr_min={result['summary']['correlation_min']:.6f}, "
          f"corr_max={result['summary']['correlation_max']:.6f}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Per-ROI mapping diagnostics for Stage A alignment"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for JSON + triptychs",
    )
    parser.add_argument(
        "--roi-count",
        type=int,
        default=16,
        help="Number of lowest-correlation ROIs to save as triptychs (default: 16)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device for mapping context (cpu or cuda:0, default: cpu)",
    )
    parser.add_argument(
        "--sigma",
        type=float,
        default=3.0,
        help="Default sigma_readout value (ADU, default: 3.0)",
    )
    parser.add_argument(
        "--mtz-path",
        type=str,
        default=None,
        help="Path to MTZ file (default: scaled.mtz or DBEX_SMOKE_HKL_PATH if set); resolved relative to repo root",
    )

    args = parser.parse_args()

    # Create output directory
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Determine dataset paths from environment
    smoke_sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "cli_override")
    smoke_detector_size = os.environ.get("DBEX_SMOKE_DETECTOR_SIZE", "small")

    # Resolve HKL path with priority: CLI > DBEX_SMOKE_HKL_PATH > scaled.mtz
    if args.mtz_path is not None:
        hkl_path_arg = args.mtz_path
    else:
        hkl_path_arg = os.environ.get("DBEX_SMOKE_HKL_PATH", "scaled.mtz")

    # Resolve relative to repo root
    if not Path(hkl_path_arg).is_absolute():
        hkl_path = repo_root / hkl_path_arg
    else:
        hkl_path = Path(hkl_path_arg)

    # DataLoad always uses scaled.mtz for experimental data
    mtz_path = repo_root / "scaled.mtz"

    print(f"Configuration:")
    print(f"  smoke_sigma_source: {smoke_sigma_source}")
    print(f"  smoke_detector_size: {smoke_detector_size}")
    print(f"  default_sigma_readout: {args.sigma}")
    print(f"  hkl_source_path: {hkl_path}")
    print(f"  dataload_mtz_path: {mtz_path}")
    print(f"  device: {args.device}")
    print(f"  roi_count: {args.roi_count}")
    print(f"  out_dir: {args.out_dir}")
    print()

    # Build DataLoad
    if smoke_detector_size == "small":
        base = repo_root / "sp.proc" / "refGeom_small"
        expt_path = base / "refGeom_small.expt"
        refl_path = base / "refGeom_small.refl"
        mask_path = base / "refGeom_small_mask.pkl"
    else:
        expt_path = repo_root / "refGeom.expt"
        refl_path = repo_root / "refGeom.refl"
        mask_path = repo_root / "747_mask.pkl"

    # Handle metadata sigma source
    if smoke_sigma_source == "metadata":
        metadata_expt = repo_root / "sp.proc" / "idx-0000_sigma_metadata.expt"
        metadata_tiles = metadata_expt.with_suffix(".sigma_tiles.pkl")
        if metadata_expt.exists() and metadata_tiles.exists():
            expt_path = metadata_expt
            refl_path = repo_root / "refGeom.refl"
            mask_path = repo_root / "747_mask.pkl"
            print(f"Using metadata sigma source: {metadata_expt}")
        else:
            print(f"WARNING: metadata sigma source requested but assets missing:")
            print(f"  {metadata_expt} exists: {metadata_expt.exists()}")
            print(f"  {metadata_tiles} exists: {metadata_tiles.exists()}")
            print(f"Bailing out per Pitfalls To Avoid (no dataset switching).")
            sys.exit(1)

    print(f"Loading data from:")
    print(f"  expt: {expt_path}")
    print(f"  refl: {refl_path}")
    print(f"  mask: {mask_path}")
    print(f"  mtz: {mtz_path}")
    print()

    # Create DataLoad
    class Args:
        def __init__(self):
            self.exptFile = str(expt_path)
            self.exptName = str(expt_path)
            self.exptIdx = 0
            self.reflFile = str(refl_path)
            self.reflName = str(refl_path)
            self.maskFile = str(mask_path)
            self.mtzFile = str(mtz_path)
            self.mtzCol = "F,SIGF"
            self.imageIdx = 0
            self.spot_scale_override = None
            # Store HKL source path separately for mapping context
            self.hkl_source_path = str(hkl_path)

    dataload_args = Args()
    dataload = DataLoad(dataload_args)

    # Compute ROI diagnostics
    print("="*60)
    diagnostics = compute_roi_diagnostics(
        dataload,
        default_sigma_readout=args.sigma,
        sigma_source=smoke_sigma_source,
        device=args.device,
        roi_count=args.roi_count,
    )
    print("="*60)
    print()

    if diagnostics["error"]:
        print(f"ERROR: {diagnostics['error']}")
        sys.exit(1)

    # Write roi_metrics.json
    roi_metrics_path = args.out_dir / "roi_metrics.json"
    roi_metrics_output = {
        "sigma_source": diagnostics["sigma_source"],
        "device": diagnostics["device"],
        "roi_count_requested": diagnostics["roi_count_requested"],
        "summary": diagnostics["summary"],
        "roi_metrics": diagnostics["roi_metrics"],
    }
    with open(roi_metrics_path, "w") as f:
        json.dump(roi_metrics_output, f, indent=2)
    print(f"Wrote roi_metrics.json to {roi_metrics_path}")

    # Write roi_histogram.json
    roi_histogram_path = args.out_dir / "roi_histogram.json"
    with open(roi_histogram_path, "w") as f:
        json.dump(diagnostics["roi_histogram"], f, indent=2)
    print(f"Wrote roi_histogram.json to {roi_histogram_path}")

    # Generate triptychs for lowest-correlation ROIs
    print(f"Generating {len(diagnostics['triptych_rois'])} triptychs...")
    for i, roi_data in enumerate(diagnostics["triptych_rois"]):
        roi_idx = roi_data["roi_idx"]
        corr = roi_data["correlation"]

        # Save NPZ
        npz_path = args.out_dir / f"roi_{roi_idx:04d}_corr_{corr:.3f}.npz"
        np.savez(
            npz_path,
            data=roi_data["data"],
            model=roi_data["model"],
            variance=roi_data["variance"],
            mask=roi_data["mask"],
            correlation=corr,
            mse=roi_data["mse"],
            scale=roi_data["scale"],
            panel_id=roi_data["panel_id"],
            bbox=roi_data["bbox"],
        )

        # Generate PNG triptych
        png_path = args.out_dir / f"roi_{roi_idx:04d}_corr_{corr:.3f}.png"
        try:
            plot_triptych(
                data=roi_data["data"],
                model=roi_data["model"],
                variance=roi_data["variance"],
                hkl=None,  # HKL not available in this probe
                correlation=corr,
                filename=str(png_path),
            )
            print(f"  [{i+1:2d}/{len(diagnostics['triptych_rois'])}] ROI {roi_idx:4d}: corr={corr:7.3f} -> {png_path.name}")
        except Exception as e:
            print(f"  WARNING: Failed to generate triptych for ROI {roi_idx}: {e}")

    print()
    print("Summary:")
    print(f"  Sigma source: {diagnostics['sigma_source']}")
    print(f"  Device: {diagnostics['device']}")
    print(f"  ROI count: {diagnostics['summary']['n_rois']}")
    print(f"  Correlation median: {diagnostics['summary']['correlation_median']:.6f}")
    print(f"  Correlation range: [{diagnostics['summary']['correlation_min']:.6f}, {diagnostics['summary']['correlation_max']:.6f}]")
    print(f"  MSE median: {diagnostics['summary']['mse_median']:.4e}")
    print(f"  Scale median: {diagnostics['summary']['scale_median']:.4e}")
    print(f"  HKL source: {diagnostics['summary']['hkl_source']}")
    print(f"  HKL path: {diagnostics['summary']['hkl_path']}")
    print(f"  HKL count: {diagnostics['summary']['hkl_count']}")
    print(f"  Spot scale override: {diagnostics['summary']['spot_scale_override']:.4e}")
    print()
    print("Probe complete.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
