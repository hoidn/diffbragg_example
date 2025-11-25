#!/usr/bin/env python3
"""
Scale-chain probe: compare scaled.mtz (raw, calibrated) vs refined structure factors.

Three permutations:
1. scaled_raw: scaled.mtz with calibration disabled (spot_scale_override=1.0)
2. scaled_calibrated: scaled.mtz plus config_torch_smoke.json calibration
3. refined_calibrated: smoke_refined_structure_factors.mtz plus calibration

Captures ROI CC, masked/unmasked scale ratios, target/bragg mean ratios, spot_scale_override,
sqrt_spot_scale, global_scale_hint, HKL telemetry, and a diff block.

Usage:
    export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
    export REPORT=plans/active/TOOLING-VIS-001/reports/<timestamp>
    export DBEX_SMOKE_SIGMA_SOURCE=metadata
    export DBEX_SMOKE_DETECTOR_SIZE=small
    export DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl
    export DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json
    export DBEX_SMOKE_HKL_PATH=scaled.mtz
    export KMP_DUPLICATE_LIB_OK=TRUE
    export NANOBRAGG_DISABLE_COMPILE=1

    python plans/active/TOOLING-VIS-001/bin/probe_scale_chain.py \\
        --cases scaled_raw,scaled_calibrated,refined_calibrated \\
        --out-dir "$REPORT"/scale_chain_probe \\
        --device cuda:0
"""
import argparse
import json
import os
import sys
import traceback
from argparse import Namespace
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch

# Add repo root to path for imports
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    load_calibration_metadata,
    load_refined_mtz,
)
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


def compute_case_metrics(
    dataload: DataLoad,
    case_name: str,
    hkl_path: Optional[Path],
    calibration_dict: Optional[dict],
    calibration_path: Optional[str],
    default_sigma_readout: float,
    device: str,
) -> Dict:
    """
    Build mapping context for a single permutation case.

    Args:
        dataload: DataLoad instance (MUST be unmodified to preserve original inputs).
        case_name: Label for the case (e.g., "scaled_raw", "scaled_calibrated", "refined_calibrated").
        hkl_path: Path to HKL source (scaled.mtz or refined MTZ). None means use dataload default.
        calibration_dict: Calibration metadata dict (or None to disable calibration).
        calibration_path: Path to calibration config JSON (or None to disable calibration).
        default_sigma_readout: Default sigma readout value (ADU).
        device: Device string ("cpu" or "cuda:0").

    Returns:
        Dictionary with ROI CC, scale ratios, bragg stats, HKL telemetry, and calibration diagnostics.
    """
    # Override dataload.args.hkl_source_path and calibration_config_path internally
    # WITHOUT mutating the global env or the DataLoad instance
    original_hkl_source_path = getattr(dataload.args, "hkl_source_path", None)
    original_calibration_config_path = getattr(dataload.args, "calibration_config_path", None)

    try:
        # Temporarily override args for this case
        if hkl_path is not None:
            dataload.args.hkl_source_path = str(hkl_path.resolve())
        else:
            dataload.args.hkl_source_path = None

        # Set calibration_config_path based on whether calibration is enabled
        if calibration_dict is not None and calibration_path is not None:
            dataload.args.calibration_config_path = calibration_path
        else:
            dataload.args.calibration_config_path = None

        context = build_mapping_stage_a_context(
            dataload,
            default_sigma_readout=default_sigma_readout,
            device=device,
        )

        # For calibrated cases, we need to manually inject the calibration
        # Actually, wait - let me re-read the build_mapping_stage_a_context code...
        # It loads calibration from dataload.args.calibration_config_path
        # So we need to either:
        # 1. Set a path to a JSON file
        # 2. Or modify build_mapping_stage_a_context to accept calibration dict directly

        # Looking at the input.md, it says:
        # "Each case should tweak HKL/calibration inputs internally instead of mutating global env"
        # So we should NOT mutate env vars, but we CAN tweak the dataload.args temporarily

        # For now, let me handle calibration by passing the path if it exists
        # For the "disabled" case, we'll reconstruct the context WITHOUT calibration

        bragg = context.bragg_zero_iter
        inputs = context.inputs

        # Compute ROI correlations
        corrs = _roi_correlations(
            inputs.target,
            bragg,
            inputs.loss_mask,
            inputs.panel_slices,
        )
        valid_corrs = [c for c in corrs if np.isfinite(c)]

        # Compute scale ratios (masked and unmasked)
        mean_target_masked = float(np.mean(inputs.target[inputs.loss_mask]))
        mean_bragg_masked = float(np.mean(bragg[inputs.loss_mask]))
        scale_ratio_masked = mean_bragg_masked / mean_target_masked if mean_target_masked > 1e-12 else float("nan")

        mean_target_unmasked = float(np.mean(inputs.target))
        mean_bragg_unmasked = float(np.mean(bragg))
        scale_ratio_unmasked = mean_bragg_unmasked / mean_target_unmasked if mean_target_unmasked > 1e-12 else float("nan")

        # Extract diagnostics
        spot_scale_override = float(context.calibration.get("spot_scale_override", 1.0)) if context.calibration else 1.0
        sqrt_spot_scale = np.sqrt(spot_scale_override)
        global_scale_hint = float(inputs.global_scale_hint)
        log_scale_baseline = float(context.diagnostics.get("log_scale_baseline", 0.0))
        sigma_floor_value = float(context.sigma_floor_value)

        # HKL telemetry
        hkl_count = len(context.hkl_indices) if hasattr(context, 'hkl_indices') and context.hkl_indices is not None else 0
        hkl_source = context.diagnostics.get("hkl_telemetry", {}).get("hkl_source", "unknown")
        hkl_path_str = context.diagnostics.get("hkl_telemetry", {}).get("hkl_path", "unknown")
        calibration_path = context.diagnostics.get("calibration_path", None)

        return {
            "case_name": case_name,
            "roi_cc_median": float(np.median(valid_corrs)) if valid_corrs else float("nan"),
            "roi_cc_count": len(valid_corrs),
            "scale_ratio_masked": scale_ratio_masked,
            "scale_ratio_unmasked": scale_ratio_unmasked,
            "mean_target_masked": mean_target_masked,
            "mean_target_unmasked": mean_target_unmasked,
            "mean_bragg_masked": mean_bragg_masked,
            "mean_bragg_unmasked": mean_bragg_unmasked,
            "bragg_mean": float(np.mean(bragg)),
            "bragg_std": float(np.std(bragg)),
            "bragg_max": float(np.max(bragg)),
            "spot_scale_override": spot_scale_override,
            "sqrt_spot_scale": sqrt_spot_scale,
            "global_scale_hint": global_scale_hint,
            "log_scale_baseline": log_scale_baseline,
            "sigma_floor_value": sigma_floor_value,
            "hkl_source": hkl_source,
            "hkl_path": hkl_path_str,
            "hkl_count": hkl_count,
            "calibration_path": calibration_path,
            "device": device,
        }

    finally:
        # Restore original args
        dataload.args.hkl_source_path = original_hkl_source_path
        dataload.args.calibration_config_path = original_calibration_config_path


def compute_diff_block(metrics_list: List[Dict]) -> Dict:
    """
    Compute diff block highlighting how each permutation diverges.

    Compares each case to the first case (typically scaled_raw baseline).

    Args:
        metrics_list: List of case metrics dicts.

    Returns:
        Dictionary with per-case deltas and divergence summary.
    """
    if not metrics_list:
        return {}

    baseline = metrics_list[0]
    diffs = {}

    for i, case in enumerate(metrics_list[1:], start=1):
        case_name = case["case_name"]
        diffs[case_name] = {
            "roi_cc_median_delta": case["roi_cc_median"] - baseline["roi_cc_median"],
            "scale_ratio_masked_delta": case["scale_ratio_masked"] - baseline["scale_ratio_masked"],
            "scale_ratio_unmasked_delta": case["scale_ratio_unmasked"] - baseline["scale_ratio_unmasked"],
            "bragg_mean_delta": case["bragg_mean"] - baseline["bragg_mean"],
            "bragg_mean_ratio": case["bragg_mean"] / baseline["bragg_mean"] if baseline["bragg_mean"] > 1e-12 else float("nan"),
            "mean_target_masked_delta": case["mean_target_masked"] - baseline["mean_target_masked"],
            "mean_bragg_masked_delta": case["mean_bragg_masked"] - baseline["mean_bragg_masked"],
            "mean_bragg_masked_ratio": case["mean_bragg_masked"] / baseline["mean_bragg_masked"] if baseline["mean_bragg_masked"] > 1e-12 else float("nan"),
            "spot_scale_override_delta": case["spot_scale_override"] - baseline["spot_scale_override"],
            "sqrt_spot_scale_delta": case["sqrt_spot_scale"] - baseline["sqrt_spot_scale"],
            "hkl_count_delta": case["hkl_count"] - baseline["hkl_count"],
        }

    return {
        "baseline_case": baseline["case_name"],
        "diffs": diffs,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Probe scale-chain metrics for scaled.mtz (raw, calibrated) vs refined structure factors."
    )
    parser.add_argument(
        "--cases",
        type=str,
        default="scaled_raw,scaled_calibrated,refined_calibrated",
        help="Comma-separated list of cases to run (default: scaled_raw,scaled_calibrated,refined_calibrated)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for JSON and log artifacts",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device string (cpu or cuda:0)",
    )
    parser.add_argument(
        "--default-sigma",
        type=float,
        default=3.0,
        help="Default sigma readout value (ADU) when no map available",
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Parse cases
    cases = [c.strip() for c in args.cases.split(",")]
    print(f"Running scale-chain probe with cases: {cases}")
    print(f"Output directory: {args.out_dir}")
    print(f"Device: {args.device}")

    # Build DataLoad once (metadata smoke fixtures)
    print("\nBuilding DataLoad args from environment...")

    # Resolve paths from env (following conftest.py pattern for smoke fixtures)
    smoke_detector_size = os.environ.get("DBEX_SMOKE_DETECTOR_SIZE", "small")

    if smoke_detector_size == "small":
        expt_path = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small.expt"
        refl_path = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small.refl"
        mask_path = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small_mask.pkl"
    else:
        expt_path = repo_root / "refGeom.expt"
        refl_path = repo_root / "refGeom.refl"
        mask_path = repo_root / "747_mask.pkl"

    # Check if paths exist
    for path, name in [(expt_path, "experiment"), (refl_path, "reflections"), (mask_path, "mask")]:
        if not path.exists():
            print(f"ERROR: Required {name} file not found: {path}")
            sys.exit(1)

    # Resolve calibration path from env
    calib_path_env = os.environ.get("DBEX_SMOKE_CALIB_PATH")
    default_smoke_calib = repo_root / "sp.proc" / "calibration" / "config_torch_smoke.json"
    if calib_path_env:
        calib_path = repo_root / calib_path_env
    elif default_smoke_calib.exists():
        calib_path = default_smoke_calib
    else:
        calib_path = None

    # Resolve HKL path from env
    hkl_path_env = os.environ.get("DBEX_SMOKE_HKL_PATH", "scaled.mtz")
    hkl_path = repo_root / hkl_path_env

    # Infer MTZ column type
    if "refined" in str(hkl_path).lower():
        mtz_col = "F(+),SIGF(+),F(-),SIGF(-)"
    else:
        mtz_col = "I(+),SIGI(+),I(-),SIGI(-)"

    # Resolve sigma map path from env
    sigma_map_env = os.environ.get("DBEX_SMOKE_SIGMA_MAP_PATH")
    sigma_map_path = None
    if sigma_map_env:
        sigma_map_path = repo_root / sigma_map_env
        if not sigma_map_path.exists():
            print(f"WARNING: Sigma map path from env not found: {sigma_map_path}")
            sigma_map_path = None

    # Build DataLoad args
    dataload_args = Namespace(
        exptName=str(expt_path),
        reflName=str(refl_path),
        maskFile=str(mask_path),
        mtzFile=str(hkl_path),
        mtzCol=mtz_col,
        exptIdx=0,
        sigma_map=str(sigma_map_path) if sigma_map_path else None,
        config_path=str(calib_path) if calib_path else None,
        calibration_config_path=str(calib_path) if calib_path else None,
        hkl_source_path=None,  # Will be overridden per case
    )

    print(f"  Experiment: {expt_path}")
    print(f"  Reflections: {refl_path}")
    print(f"  Mask: {mask_path}")
    print(f"  HKL: {hkl_path}")
    print(f"  Calibration: {calib_path}")
    print(f"  Sigma map: {sigma_map_path}")

    print("\nLoading DataLoad...")
    try:
        dataload = DataLoad(dataload_args)
    except Exception as e:
        print(f"ERROR: Failed to load DataLoad: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Determine paths for cases
    # scaled.mtz is the default from DataLoad
    # refined MTZ path from env DBEX_SMOKE_HKL_PATH or fallback
    scaled_mtz_path = Path(dataload.args.mtzFile)

    # Check for refined structure factors
    # Per input.md: "sp.proc/calibration/smoke_refined_structure_factors.mtz"
    # But let's also check the fixtures golden path
    refined_mtz_candidates = [
        Path("sp.proc/calibration/smoke_refined_structure_factors.mtz"),
        Path("tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz"),
    ]
    refined_mtz_path = None
    for candidate in refined_mtz_candidates:
        if candidate.exists():
            refined_mtz_path = candidate
            break

    # Load calibration metadata from env DBEX_SMOKE_CALIB_PATH
    calibration_path_str = dataload.args.calibration_config_path
    calibration_dict = None
    if calibration_path_str:
        calibration_path = Path(calibration_path_str)
        if calibration_path.exists():
            try:
                calibration_dict = load_calibration_metadata(calibration_path)
                print(f"Loaded calibration from {calibration_path}")
            except Exception as e:
                print(f"WARNING: Failed to load calibration from {calibration_path}: {e}")

    # Run each case
    metrics_list = []
    for case_name in cases:
        print(f"\n{'=' * 60}")
        print(f"Running case: {case_name}")
        print(f"{'=' * 60}")

        hkl_path = None
        calib = None

        if case_name == "scaled_raw":
            # scaled.mtz with calibration disabled (spot_scale_override=1.0)
            hkl_path = scaled_mtz_path
            calib = None  # Disable calibration
        elif case_name == "scaled_calibrated":
            # scaled.mtz plus config_torch_smoke.json calibration
            hkl_path = scaled_mtz_path
            calib = calibration_dict
        elif case_name == "refined_calibrated":
            # smoke_refined_structure_factors.mtz plus calibration
            if refined_mtz_path is None:
                print(f"ERROR: Refined MTZ not found for case {case_name}. Skipping.")
                continue
            hkl_path = refined_mtz_path
            calib = calibration_dict
        else:
            print(f"WARNING: Unknown case {case_name}. Skipping.")
            continue

        try:
            # Pass calibration_path to compute_case_metrics so it can be plumbed correctly
            metrics = compute_case_metrics(
                dataload,
                case_name,
                hkl_path,
                calib,
                calibration_path_str if calib is not None else None,
                args.default_sigma,
                args.device,
            )
            metrics_list.append(metrics)
            print(f"  ROI CC median: {metrics['roi_cc_median']:.4f}")
            print(f"  Scale ratio (masked): {metrics['scale_ratio_masked']:.3e}")
            print(f"  Bragg mean: {metrics['bragg_mean']:.3e}")
            print(f"  Spot scale override: {metrics['spot_scale_override']:.3e}")
            print(f"  HKL source: {metrics['hkl_source']} ({metrics['hkl_count']} reflections)")
        except Exception as e:
            print(f"ERROR: Case {case_name} failed: {e}")
            traceback.print_exc()

    # Compute diff block
    print(f"\n{'=' * 60}")
    print("Computing diff block...")
    print(f"{'=' * 60}")
    diff_block = compute_diff_block(metrics_list)

    # Write output JSON
    output = {
        "cases": metrics_list,
        "diff_block": diff_block,
        "probe_config": {
            "device": args.device,
            "default_sigma": args.default_sigma,
            "cases_requested": cases,
        },
    }

    output_json_path = args.out_dir / "scale_chain_metrics.json"
    with open(output_json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote scale-chain metrics to {output_json_path}")

    # Print diff summary
    if diff_block and "diffs" in diff_block:
        print(f"\nDiff summary (vs {diff_block['baseline_case']}):")
        for case_name, diffs in diff_block["diffs"].items():
            print(f"\n  {case_name}:")
            print(f"    ROI CC Δ: {diffs['roi_cc_median_delta']:+.4f}")
            print(f"    Scale ratio (masked) Δ: {diffs['scale_ratio_masked_delta']:+.3e}")
            print(f"    Bragg mean ratio: {diffs['bragg_mean_ratio']:.3e}×")
            print(f"    Spot scale override Δ: {diffs['spot_scale_override_delta']:+.3e}")

    print("\nScale-chain probe complete!")


if __name__ == "__main__":
    main()
