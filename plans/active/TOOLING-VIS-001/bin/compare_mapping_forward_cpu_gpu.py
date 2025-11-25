#!/usr/bin/env python3
"""
CPU vs CUDA mapping forward T2 probe.

Builds build_mapping_stage_a_context on CPU and CUDA, computes ROI CC/scale ratios
and mean_abs/max_abs diffs between CPU/GPU bragg_zero_iter stacks, and writes JSON + log
under the artifacts path.

Usage:
    export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
    export DBEX_SMOKE_SIGMA_SOURCE=metadata
    export DBEX_SMOKE_DETECTOR_SIZE=small
    export KMP_DUPLICATE_LIB_OK=TRUE
    export NANOBRAGG_DISABLE_COMPILE=1

    python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py \\
        --out-dir plans/active/TOOLING-VIS-001/reports/<timestamp>/mapping_cpu_gpu
"""
import argparse
import json
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


def _masked_roi_corr(data_roi: np.ndarray, model_roi: np.ndarray, mask_roi: np.ndarray) -> float:
    """Compute masked ROI correlation."""
    mask_flat = np.asarray(mask_roi, dtype=bool)
    if not np.any(mask_flat):
        return float("nan")
    data = np.asarray(data_roi, dtype=np.float64)[mask_flat]
    model = np.asarray(model_roi, dtype=np.float64)[mask_flat]
    data_centered = data - data.mean()
    model_centered = model - model.mean()
    denom = np.linalg.norm(data_centered) * np.linalg.norm(model_centered)
    if denom <= 0:
        return float("nan")
    return float(np.dot(data_centered, model_centered) / denom)


def _roi_correlations(
    target: np.ndarray,
    model: np.ndarray,
    loss_mask: np.ndarray,
    panel_slices: List,
) -> List[float]:
    """Compute per-ROI correlations."""
    corrs: List[float] = []
    for pid, bbox in panel_slices:
        x0, x1, y0, y1 = bbox
        roi_mask = loss_mask[int(pid), y0:y1, x0:x1]
        if not np.any(roi_mask):
            continue
        data_roi = target[int(pid), y0:y1, x0:x1]
        model_roi = model[int(pid), y0:y1, x0:x1]
        corrs.append(_masked_roi_corr(data_roi, model_roi, roi_mask))
    return corrs


def compute_cpu_gpu_mapping_metrics(
    dataload: DataLoad,
    default_sigma_readout: float = 3.0,
    sigma_source: str = "cli_override",
) -> Dict:
    """
    Build mapping contexts on CPU and CUDA, compare bragg_zero_iter stacks.

    Args:
        dataload: DataLoad instance with experiment/reflection/MTZ data.
        default_sigma_readout: Default sigma readout value (ADU).
        sigma_source: Provenance label for sigma ('metadata' or 'cli_override').

    Returns:
        Dictionary with CPU/GPU metrics, ROI CC/scale ratios, and bragg diffs.
    """
    result = {
        "cuda_available": torch.cuda.is_available(),
        "error": None,
        "sigma_source": sigma_source,
        "cpu_metrics": {},
        "gpu_metrics": {},
        "parity_metrics": {},
    }

    # Build CPU context
    print("Building CPU mapping context...")
    try:
        cpu_context = build_mapping_stage_a_context(
            dataload,
            default_sigma_readout=default_sigma_readout,
            device="cpu",
        )

        cpu_bragg = cpu_context.bragg_zero_iter
        cpu_inputs = cpu_context.inputs

        # Compute CPU ROI correlations
        cpu_corrs = _roi_correlations(
            cpu_inputs.target,
            cpu_bragg,
            cpu_inputs.loss_mask,
            cpu_inputs.panel_slices,
        )
        valid_cpu_corrs = [c for c in cpu_corrs if np.isfinite(c)]

        # Compute CPU scale ratios (masked and unmasked)
        cpu_mask = cpu_inputs.loss_mask
        cpu_mean_target_masked = float(np.mean(cpu_inputs.target[cpu_mask]))
        cpu_mean_bragg_masked = float(np.mean(cpu_bragg[cpu_mask]))
        cpu_scale_ratio_masked = cpu_mean_bragg_masked / cpu_mean_target_masked if cpu_mean_target_masked > 1e-12 else float("nan")

        cpu_mean_target_unmasked = float(np.mean(cpu_inputs.target))
        cpu_mean_bragg_unmasked = float(np.mean(cpu_bragg))
        cpu_scale_ratio_unmasked = cpu_mean_bragg_unmasked / cpu_mean_target_unmasked if cpu_mean_target_unmasked > 1e-12 else float("nan")

        # Count HKL reflections from mapping context
        cpu_hkl_count = len(cpu_context.hkl_indices) if hasattr(cpu_context, 'hkl_indices') else 0

        result["cpu_metrics"] = {
            "roi_cc_median": float(np.median(valid_cpu_corrs)) if valid_cpu_corrs else float("nan"),
            "roi_cc_count": len(valid_cpu_corrs),
            "scale_ratio_masked": cpu_scale_ratio_masked,
            "scale_ratio_unmasked": cpu_scale_ratio_unmasked,
            "log_scale_baseline": float(cpu_context.diagnostics.get("log_scale_baseline", 0.0)),
            "global_scale_hint": float(cpu_inputs.global_scale_hint),
            "sigma_floor_value": float(cpu_context.sigma_floor_value),
            "bragg_mean": float(np.mean(cpu_bragg)),
            "bragg_std": float(np.std(cpu_bragg)),
            "bragg_max": float(np.max(cpu_bragg)),
            "spot_scale_override": float(cpu_context.calibration.get("spot_scale_override", 1.0)) if cpu_context.calibration else 1.0,
            "hkl_source": cpu_context.diagnostics.get("hkl_telemetry", {}).get("hkl_source", "unknown"),
            "hkl_path": cpu_context.diagnostics.get("hkl_telemetry", {}).get("hkl_path", "unknown"),
            "hkl_count": cpu_hkl_count,
        }
        print(f"CPU metrics: ROI CC median={result['cpu_metrics']['roi_cc_median']:.6f}, "
              f"scale_ratio_masked={result['cpu_metrics']['scale_ratio_masked']:.4e}, "
              f"scale_ratio_unmasked={result['cpu_metrics']['scale_ratio_unmasked']:.4e}")

    except Exception as e:
        result["error"] = f"CPU context build failed: {e}"
        print(f"ERROR: {result['error']}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        return result

    # Check CUDA availability
    if not torch.cuda.is_available():
        result["error"] = "CUDA not available"
        print(f"WARNING: {result['error']} - skipping GPU comparison")
        return result

    # Build CUDA context
    print("Building CUDA mapping context...")
    try:
        gpu_context = build_mapping_stage_a_context(
            dataload,
            default_sigma_readout=default_sigma_readout,
            device="cuda:0",
        )

        gpu_bragg = gpu_context.bragg_zero_iter
        gpu_inputs = gpu_context.inputs

        # Compute GPU ROI correlations
        gpu_corrs = _roi_correlations(
            gpu_inputs.target,
            gpu_bragg,
            gpu_inputs.loss_mask,
            gpu_inputs.panel_slices,
        )
        valid_gpu_corrs = [c for c in gpu_corrs if np.isfinite(c)]

        # Compute GPU scale ratios (masked and unmasked)
        gpu_mask = gpu_inputs.loss_mask
        gpu_mean_target_masked = float(np.mean(gpu_inputs.target[gpu_mask]))
        gpu_mean_bragg_masked = float(np.mean(gpu_bragg[gpu_mask]))
        gpu_scale_ratio_masked = gpu_mean_bragg_masked / gpu_mean_target_masked if gpu_mean_target_masked > 1e-12 else float("nan")

        gpu_mean_target_unmasked = float(np.mean(gpu_inputs.target))
        gpu_mean_bragg_unmasked = float(np.mean(gpu_bragg))
        gpu_scale_ratio_unmasked = gpu_mean_bragg_unmasked / gpu_mean_target_unmasked if gpu_mean_target_unmasked > 1e-12 else float("nan")

        # Count HKL reflections from mapping context
        gpu_hkl_count = len(gpu_context.hkl_indices) if hasattr(gpu_context, 'hkl_indices') else 0

        result["gpu_metrics"] = {
            "roi_cc_median": float(np.median(valid_gpu_corrs)) if valid_gpu_corrs else float("nan"),
            "roi_cc_count": len(valid_gpu_corrs),
            "scale_ratio_masked": gpu_scale_ratio_masked,
            "scale_ratio_unmasked": gpu_scale_ratio_unmasked,
            "log_scale_baseline": float(gpu_context.diagnostics.get("log_scale_baseline", 0.0)),
            "global_scale_hint": float(gpu_inputs.global_scale_hint),
            "sigma_floor_value": float(gpu_context.sigma_floor_value),
            "bragg_mean": float(np.mean(gpu_bragg)),
            "bragg_std": float(np.std(gpu_bragg)),
            "bragg_max": float(np.max(gpu_bragg)),
            "spot_scale_override": float(gpu_context.calibration.get("spot_scale_override", 1.0)) if gpu_context.calibration else 1.0,
            "hkl_source": gpu_context.diagnostics.get("hkl_telemetry", {}).get("hkl_source", "unknown"),
            "hkl_path": gpu_context.diagnostics.get("hkl_telemetry", {}).get("hkl_path", "unknown"),
            "hkl_count": gpu_hkl_count,
        }
        print(f"GPU metrics: ROI CC median={result['gpu_metrics']['roi_cc_median']:.6f}, "
              f"scale_ratio_masked={result['gpu_metrics']['scale_ratio_masked']:.4e}, "
              f"scale_ratio_unmasked={result['gpu_metrics']['scale_ratio_unmasked']:.4e}")

    except Exception as e:
        result["error"] = f"GPU context build failed: {e}"
        print(f"ERROR: {result['error']}")
        return result

    # Compute CPU vs GPU parity metrics
    print("Computing CPU vs GPU parity metrics...")
    try:
        # Bragg diff metrics
        diff = cpu_bragg - gpu_bragg
        mean_abs_diff = float(np.mean(np.abs(diff)))
        max_abs_diff = float(np.max(np.abs(diff)))

        # ROI CC comparison
        roi_cc_diff = abs(result["cpu_metrics"]["roi_cc_median"] - result["gpu_metrics"]["roi_cc_median"])

        # Scale ratio comparison (masked)
        scale_ratio_cpu_masked = result["cpu_metrics"]["scale_ratio_masked"]
        scale_ratio_gpu_masked = result["gpu_metrics"]["scale_ratio_masked"]
        if np.isfinite(scale_ratio_cpu_masked) and np.isfinite(scale_ratio_gpu_masked) and scale_ratio_cpu_masked > 1e-12:
            scale_ratio_masked_rel_diff = abs(scale_ratio_cpu_masked - scale_ratio_gpu_masked) / scale_ratio_cpu_masked
        else:
            scale_ratio_masked_rel_diff = float("nan")

        # Scale ratio comparison (unmasked)
        scale_ratio_cpu_unmasked = result["cpu_metrics"]["scale_ratio_unmasked"]
        scale_ratio_gpu_unmasked = result["gpu_metrics"]["scale_ratio_unmasked"]
        if np.isfinite(scale_ratio_cpu_unmasked) and np.isfinite(scale_ratio_gpu_unmasked) and scale_ratio_cpu_unmasked > 1e-12:
            scale_ratio_unmasked_rel_diff = abs(scale_ratio_cpu_unmasked - scale_ratio_gpu_unmasked) / scale_ratio_cpu_unmasked
        else:
            scale_ratio_unmasked_rel_diff = float("nan")

        result["parity_metrics"] = {
            "bragg_mean_abs_diff": mean_abs_diff,
            "bragg_max_abs_diff": max_abs_diff,
            "roi_cc_median_diff": roi_cc_diff,
            "scale_ratio_masked_rel_diff": scale_ratio_masked_rel_diff,
            "scale_ratio_unmasked_rel_diff": scale_ratio_unmasked_rel_diff,
            "log_scale_baseline_match": (
                result["cpu_metrics"]["log_scale_baseline"] == result["gpu_metrics"]["log_scale_baseline"]
            ),
        }
        print(f"Parity metrics: mean_abs_diff={mean_abs_diff:.4e}, max_abs_diff={max_abs_diff:.4e}, "
              f"roi_cc_diff={roi_cc_diff:.6f}, scale_ratio_masked_rel_diff={scale_ratio_masked_rel_diff:.4e}")

    except Exception as e:
        result["error"] = f"Parity computation failed: {e}"
        print(f"ERROR: {result['error']}")
        return result

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Compare mapping forward pass on CPU vs CUDA"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for JSON + log",
    )
    parser.add_argument(
        "--sigma",
        type=float,
        default=3.0,
        help="Default sigma_readout value (ADU)",
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
    import os
    smoke_sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "cli_override")
    smoke_detector_size = os.environ.get("DBEX_SMOKE_DETECTOR_SIZE", "small")

    # Resolve HKL path with priority: CLI > DBEX_SMOKE_HKL_PATH > scaled.mtz
    # This determines which HKL source to use (scaled or refined)
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
        else:
            print(f"WARNING: metadata sigma source requested but assets missing, falling back to cli_override")
            smoke_sigma_source = "cli_override"

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
            self.mtzCol = "F,SIGF"  # DataLoad always uses scaled.mtz
            self.imageIdx = 0
            self.spot_scale_override = None
            # Store HKL source path separately for mapping context
            self.hkl_source_path = str(hkl_path)

    dataload_args = Args()
    dataload = DataLoad(dataload_args)

    # Compute metrics
    print("="*60)
    metrics = compute_cpu_gpu_mapping_metrics(
        dataload,
        default_sigma_readout=args.sigma,
        sigma_source=smoke_sigma_source,
    )
    print("="*60)
    print()

    # Write JSON
    json_path = args.out_dir / "mapping_forward_cpu_gpu.json"
    with open(json_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Wrote JSON to {json_path}")

    # Print summary
    print()
    print("Summary:")
    print(f"  Sigma source: {metrics.get('sigma_source', 'unknown')}")
    print(f"  CUDA available: {metrics['cuda_available']}")
    if metrics["error"]:
        print(f"  Error: {metrics['error']}")
        sys.exit(1)

    if metrics["cpu_metrics"]:
        print(f"  CPU ROI CC median: {metrics['cpu_metrics']['roi_cc_median']:.6f}")
        print(f"  CPU scale ratio (masked): {metrics['cpu_metrics']['scale_ratio_masked']:.4e}")
        print(f"  CPU scale ratio (unmasked): {metrics['cpu_metrics']['scale_ratio_unmasked']:.4e}")
        print(f"  CPU spot_scale_override: {metrics['cpu_metrics']['spot_scale_override']:.4e}")
        print(f"  CPU HKL source: {metrics['cpu_metrics']['hkl_source']}")
        print(f"  CPU HKL path: {metrics['cpu_metrics']['hkl_path']}")
        print(f"  CPU HKL count: {metrics['cpu_metrics']['hkl_count']}")

    if metrics["gpu_metrics"]:
        print(f"  GPU ROI CC median: {metrics['gpu_metrics']['roi_cc_median']:.6f}")
        print(f"  GPU scale ratio (masked): {metrics['gpu_metrics']['scale_ratio_masked']:.4e}")
        print(f"  GPU scale ratio (unmasked): {metrics['gpu_metrics']['scale_ratio_unmasked']:.4e}")
        print(f"  GPU spot_scale_override: {metrics['gpu_metrics']['spot_scale_override']:.4e}")
        print(f"  GPU HKL source: {metrics['gpu_metrics']['hkl_source']}")
        print(f"  GPU HKL path: {metrics['gpu_metrics']['hkl_path']}")
        print(f"  GPU HKL count: {metrics['gpu_metrics']['hkl_count']}")

    if metrics["parity_metrics"]:
        print(f"  Bragg mean_abs_diff: {metrics['parity_metrics']['bragg_mean_abs_diff']:.4e}")
        print(f"  Bragg max_abs_diff: {metrics['parity_metrics']['bragg_max_abs_diff']:.4e}")
        print(f"  ROI CC median diff: {metrics['parity_metrics']['roi_cc_median_diff']:.6f}")
        print(f"  Scale ratio (masked) rel diff: {metrics['parity_metrics']['scale_ratio_masked_rel_diff']:.4e}")
        print(f"  Scale ratio (unmasked) rel diff: {metrics['parity_metrics']['scale_ratio_unmasked_rel_diff']:.4e}")

    print()
    print("Probe complete.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
