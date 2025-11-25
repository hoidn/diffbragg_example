#!/usr/bin/env python3
"""Compare mapping metrics across different HKL/calibration dataset combinations.

This probe compares Stage A mapping contexts built with different HKL sources
(scaled.mtz vs refined_structure_factors.mtz) and calibration configurations
to quantify the effect of HKL/calibration choice on ROI CC and scale ratios.

Usage:
    DBEX_SMOKE_SIGMA_SOURCE=metadata \\
    DBEX_SMOKE_DETECTOR_SIZE=small \\
    DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json \\
    DBEX_SMOKE_HKL_PATH=scaled.mtz \\
    KMP_DUPLICATE_LIB_OK=TRUE \\
    NANOBRAGG_DISABLE_COMPILE=1 \\
    python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py \\
        --out-dir plans/active/TOOLING-VIS-001/reports/<timestamp>/mapping_dataset_metrics \\
        --cases metadata_scaled metadata_refined

Data dependencies (per docs/data_dependency_manifest.md):
    - Reuses build_mapping_stage_a_context with controlled HKL/calibration overrides.
    - DBEX_SMOKE_* env vars configure the baseline fixture (sigma source, detector size).
    - Each case specification provides its own HKL path and calibration config path.
    - No ad-hoc forward code; all mapping contexts flow through the same canonical helper.
"""

import argparse
import json
import os
import sys
from argparse import Namespace
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch

# Add repo root to path
# Script is at <repo>/plans/active/TOOLING-VIS-001/bin/script.py
# So we need 4 parent calls: bin -> TOOLING-VIS-001 -> active -> plans -> repo_root
repo_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from dbex.data_load import DataLoad
from dbex.vis.mapping import build_mapping_stage_a_context


def _pearson_cc(data_roi: np.ndarray, model_roi: np.ndarray, mask_roi: np.ndarray) -> float:
    """Compute masked Pearson correlation for a single ROI."""
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
    """Compute per-ROI Pearson CC between model and target."""
    corrs: List[float] = []
    for pid, bbox in panel_slices:
        x0, x1, y0, y1 = bbox
        roi_mask = loss_mask[int(pid), y0:y1, x0:x1]
        if not np.any(roi_mask):
            continue
        data_roi = target[int(pid), y0:y1, x0:x1]
        model_roi = model[int(pid), y0:y1, x0:x1]
        corrs.append(_pearson_cc(data_roi, model_roi, roi_mask))
    return corrs


def define_cases() -> Dict[str, Dict[str, str]]:
    """Define preset dataset cases with explicit HKL/calibration paths.

    Mirrors the logic from tests/conftest.py::smoke_dataset_paths and refgeom_dataload:
    - Uses DBEX_SMOKE_GEOM_PATH override or defaults to canonical geometry paths
      (refGeom_small.expt for small detector, refGeom.expt otherwise).
    - When sigma_source=metadata, resolves sigma_map_path from DBEX_SMOKE_SIGMA_MAP_PATH
      or defaults to the appropriate cropped/full sigma tiles.
    - Geometry path stays canonical (not swapped to idx-0000_sigma_metadata.expt).

    Returns:
        Dictionary mapping case_name -> {expt, refl, mask, hkls, calibration, sigma_map}
        paths (all absolute or repo-relative). sigma_map is None when not applicable.
    """
    # Use repo root for resolving relative paths
    repo = repo_root

    # Determine detector size and sigma source from env
    detector_size = os.environ.get("DBEX_SMOKE_DETECTOR_SIZE", "small")
    sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "override")

    # Resolve canonical geometry path from env or defaults (per conftest.py:89-96)
    geom_path_override = os.environ.get("DBEX_SMOKE_GEOM_PATH")
    if geom_path_override:
        geom_path = repo / geom_path_override
    elif detector_size == "small":
        geom_path = repo / "sp.proc" / "refGeom_small" / "refGeom_small.expt"
    else:
        geom_path = repo / "refGeom.expt"

    # Resolve reflections and mask paths based on detector size (per conftest.py:98-107)
    if detector_size == "small":
        base = repo / "sp.proc" / "refGeom_small"
        refl_path = base / "refGeom_small.refl"
        mask_path = base / "refGeom_small_mask.pkl"
    else:
        refl_path = repo / "refGeom.refl"
        mask_path = repo / "747_mask.pkl"

    # Resolve sigma-map path when metadata source is requested (per conftest.py:109-130)
    sigma_map_path = None
    if sigma_source == "metadata":
        sigma_map_override = os.environ.get("DBEX_SMOKE_SIGMA_MAP_PATH")
        if sigma_map_override:
            sigma_map_path = repo / sigma_map_override
        else:
            # Default to cropped sigma-map for small detector, full sigma-map otherwise
            if detector_size == "small":
                sigma_map_path = repo / "sp.proc" / "refGeom_small" / "idx-0000_sigma_metadata_small.sigma_tiles.pkl"
            else:
                sigma_map_path = repo / "sp.proc" / "idx-0000_sigma_metadata.sigma_tiles.pkl"

    cases = {
        "metadata_scaled": {
            "expt": str(geom_path),
            "refl": str(refl_path),
            "mask": str(mask_path),
            "hkls": str(repo / "scaled.mtz"),
            "calibration": str(repo / "sp.proc" / "calibration" / "config_torch_smoke.json"),
            "sigma_map": str(sigma_map_path) if sigma_map_path else None,
        },
        "metadata_refined": {
            "expt": str(geom_path),
            "refl": str(refl_path),
            "mask": str(mask_path),
            "hkls": str(repo / "tests" / "fixtures" / "golden_data" / "simple_cubic" / "refined_structure_factors.mtz"),
            "calibration": str(repo / "tests" / "fixtures" / "golden_data" / "simple_cubic" / "config_torch.json"),
            "sigma_map": str(sigma_map_path) if sigma_map_path else None,
        },
    }
    return cases


def build_dataload_for_case(case_spec: Dict[str, str], sigma_source: str = "metadata") -> DataLoad:
    """Build a DataLoad instance for a specific case configuration.

    Args:
        case_spec: dict with keys {expt, refl, mask, hkls, calibration, sigma_map}
        sigma_source: "metadata" or "override" (from DBEX_SMOKE_SIGMA_SOURCE)

    Returns:
        DataLoad instance configured for this case

    Per tests/conftest.py::refgeom_dataload (lines 224-237):
    - When sigma_source=="metadata" and case_spec["sigma_map"] is present,
      pass it through args.sigma_map so DataLoad loads external sigma tiles
      instead of relying on experiment metadata alone.
    - Keep HKL and calibration overrides per case (no swapping experiments).
    """
    # Detect MTZ column labels: refined structure factors use Bijvoet pairs
    hkl_path_obj = Path(case_spec["hkls"])
    if "refined_structure_factors" in hkl_path_obj.name:
        mtz_col = "F(+),SIGF(+),F(-),SIGF(-)"
    else:
        mtz_col = "F,SIGF"

    args = Namespace(
        exptName=case_spec["expt"],
        reflName=case_spec["refl"],
        exptIdx=0,
        maskFile=case_spec["mask"],
        mtzFile=case_spec["hkls"],
        mtzCol=mtz_col,
        procDirName=None,
        dparamFile=None,
        rescale=False,
        rescale_gamma=False,
        use_trusted_mask=True,
        tilt_plane_refine=False,
        # Override HKL and calibration paths per case
        hkl_source_path=case_spec["hkls"],
        calibration_config_path=case_spec["calibration"],
        # Pass sigma_map through when available (per conftest.py:231)
        sigma_map=case_spec.get("sigma_map"),
        config_path=case_spec["calibration"],  # Alias for calibration_config_path
    )

    # Build DataLoad (sigma handling via args.sigma_map when metadata source)
    dataload = DataLoad(args)

    return dataload


def compute_case_metrics(
    case_name: str,
    case_spec: Dict[str, str],
    sigma_source: str,
    default_sigma: float,
    device: str,
) -> Dict:
    """Build mapping context for a case and compute metrics.

    Args:
        case_name: Human-readable case identifier
        case_spec: Dataset paths dict
        sigma_source: "metadata" or "override"
        default_sigma: Fallback sigma value
        device: Device string (e.g., "cpu", "cuda:0")

    Returns:
        Dictionary with per-case metrics plus diagnostics
    """
    print(f"\n=== Building mapping context for case: {case_name} ===")
    print(f"  expt: {case_spec['expt']}")
    print(f"  refl: {case_spec['refl']}")
    print(f"  mask: {case_spec['mask']}")
    print(f"  hkls: {case_spec['hkls']}")
    print(f"  calibration: {case_spec['calibration']}")
    print(f"  sigma_source: {sigma_source}")

    # Build DataLoad for this case
    dataload = build_dataload_for_case(case_spec, sigma_source=sigma_source)

    # Build mapping context reusing canonical helper (TOOLING-VIS-001 requirement)
    mapping_context = build_mapping_stage_a_context(
        dataload,
        default_sigma_readout=default_sigma,
        device=device,
    )

    # Extract inputs and Bragg stack
    inputs = mapping_context.inputs
    bragg_mapping = mapping_context.bragg_zero_iter
    target = inputs.target
    loss_mask = inputs.loss_mask

    # Compute per-ROI correlations
    corrs = _roi_correlations(target, bragg_mapping, loss_mask, inputs.panel_slices)
    valid_corrs = [c for c in corrs if np.isfinite(c)]
    roi_cc_median = float(np.median(valid_corrs)) if valid_corrs else float("nan")

    # Compute masked scale ratio (mean_model / mean_target over loss_mask)
    mean_target_masked = float(np.mean(target[loss_mask]))
    mean_model_masked = float(np.mean(bragg_mapping[loss_mask]))
    scale_ratio_masked = mean_model_masked / mean_target_masked if mean_target_masked > 1e-12 else float("inf")

    # Compute unmasked scale ratio (diagnostic)
    mean_target_unmasked = float(np.mean(target))
    mean_model_unmasked = float(np.mean(bragg_mapping))
    scale_ratio_unmasked = mean_model_unmasked / mean_target_unmasked if mean_target_unmasked > 1e-12 else float("inf")

    # Compute Bragg stack statistics
    bragg_mean = float(np.mean(bragg_mapping))
    bragg_std = float(np.std(bragg_mapping))
    bragg_max = float(np.max(bragg_mapping))

    # Extract calibration metadata from mapping_context
    diagnostics = mapping_context.diagnostics
    hkl_source = diagnostics.get("hkl_source", "unknown")
    hkl_path = diagnostics.get("hkl_path", "unknown")
    hkl_count = len(mapping_context.hkl_indices) if mapping_context.hkl_indices is not None else 0
    calibration_path = diagnostics.get("calibration_path", None)
    sigma_floor_value = float(mapping_context.sigma_floor_value)
    spot_scale_override = float(mapping_context.spot_scale_override) if mapping_context.spot_scale_override is not None else None

    # Compute global_scale_hint (used by Stage A engine)
    global_scale_hint = float(inputs.global_scale_hint) if inputs.global_scale_hint is not None else float("nan")

    print(f"  roi_cc_median: {roi_cc_median:.4f}")
    print(f"  scale_ratio_masked: {scale_ratio_masked:.4f}")
    print(f"  scale_ratio_unmasked: {scale_ratio_unmasked:.4f}")
    print(f"  bragg_mean: {bragg_mean:.2f}")
    print(f"  bragg_std: {bragg_std:.2f}")
    print(f"  bragg_max: {bragg_max:.2f}")
    print(f"  hkl_source: {hkl_source}")
    print(f"  hkl_path: {hkl_path}")
    print(f"  hkl_count: {hkl_count}")
    print(f"  sigma_floor_value: {sigma_floor_value}")
    print(f"  spot_scale_override: {spot_scale_override}")
    print(f"  global_scale_hint: {global_scale_hint}")

    return {
        "case_name": case_name,
        "roi_cc_median": roi_cc_median,
        "scale_ratio_masked": scale_ratio_masked,
        "scale_ratio_unmasked": scale_ratio_unmasked,
        "bragg_mean": bragg_mean,
        "bragg_std": bragg_std,
        "bragg_max": bragg_max,
        "global_scale_hint": global_scale_hint,
        "sigma_floor_value": sigma_floor_value,
        "spot_scale_override": spot_scale_override,
        "calibration_path": calibration_path,
        "hkl_source": hkl_source,
        "hkl_path": hkl_path,
        "hkl_count": hkl_count,
        "n_rois": len(valid_corrs),
        "device": device,
    }


def compute_diffs(base_metrics: Dict, other_metrics: Dict) -> Dict:
    """Compute difference metrics between two cases.

    Args:
        base_metrics: Metrics dict for the base case (e.g., metadata_scaled)
        other_metrics: Metrics dict for the comparison case

    Returns:
        Dictionary with delta_ fields for numeric metrics
    """
    numeric_keys = [
        "roi_cc_median",
        "scale_ratio_masked",
        "scale_ratio_unmasked",
        "bragg_mean",
        "bragg_std",
        "bragg_max",
        "global_scale_hint",
        "sigma_floor_value",
    ]

    diffs = {
        "base_case": base_metrics["case_name"],
        "comparison_case": other_metrics["case_name"],
    }

    for key in numeric_keys:
        base_val = base_metrics.get(key, float("nan"))
        other_val = other_metrics.get(key, float("nan"))
        if np.isfinite(base_val) and np.isfinite(other_val):
            diffs[f"delta_{key}"] = float(other_val - base_val)
            if base_val != 0:
                diffs[f"relative_{key}"] = float((other_val - base_val) / base_val)
            else:
                diffs[f"relative_{key}"] = float("inf") if other_val != 0 else 0.0
        else:
            diffs[f"delta_{key}"] = float("nan")
            diffs[f"relative_{key}"] = float("nan")

    return diffs


def main():
    parser = argparse.ArgumentParser(
        description="Compare mapping dataset metrics across HKL/calibration configurations"
    )
    parser.add_argument(
        "--cases",
        nargs="+",
        required=True,
        help="List of case names to compare (e.g., metadata_scaled metadata_refined)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for metrics JSON and logs",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0" if torch.cuda.is_available() else "cpu",
        help="Device for mapping forward computation (default: cuda:0 if available, else cpu)",
    )
    parser.add_argument(
        "--default-sigma",
        type=float,
        default=3.0,
        help="Default sigma_readout value when external tiles unavailable (default: 3.0 ADU)",
    )

    args = parser.parse_args()

    # Create output directory
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Get sigma source from env
    sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "override")

    # Define available cases
    available_cases = define_cases()

    # Validate requested cases
    for case_name in args.cases:
        if case_name not in available_cases:
            print(f"ERROR: Unknown case '{case_name}'. Available: {list(available_cases.keys())}", file=sys.stderr)
            sys.exit(1)

    print(f"Running mapping dataset metrics comparison")
    print(f"Cases: {args.cases}")
    print(f"Output directory: {args.out_dir}")
    print(f"Device: {args.device}")
    print(f"Sigma source: {sigma_source}")
    print(f"Default sigma: {args.default_sigma} ADU")

    # Compute metrics for each case
    case_metrics = []
    for case_name in args.cases:
        case_spec = available_cases[case_name]
        metrics = compute_case_metrics(
            case_name=case_name,
            case_spec=case_spec,
            sigma_source=sigma_source,
            default_sigma=args.default_sigma,
            device=args.device,
        )
        case_metrics.append(metrics)

    # Compute diffs if multiple cases
    diffs = []
    if len(case_metrics) > 1:
        base = case_metrics[0]
        for other in case_metrics[1:]:
            diff = compute_diffs(base, other)
            diffs.append(diff)

    # Assemble final JSON
    output = {
        "cases": case_metrics,
        "diffs": diffs,
    }

    # Write JSON
    json_path = args.out_dir / "mapping_dataset_metrics.json"
    with json_path.open("w") as f:
        json.dump(output, f, indent=2)

    print(f"\n=== Metrics written to {json_path} ===")
    print(f"Summary:")
    for metrics in case_metrics:
        print(f"  {metrics['case_name']}:")
        print(f"    roi_cc_median: {metrics['roi_cc_median']:.4f}")
        print(f"    scale_ratio_masked: {metrics['scale_ratio_masked']:.4f}")
        print(f"    bragg_mean: {metrics['bragg_mean']:.2f}")

    if diffs:
        print(f"\nDeltas vs {case_metrics[0]['case_name']}:")
        for diff in diffs:
            print(f"  {diff['comparison_case']}:")
            print(f"    delta_roi_cc_median: {diff['delta_roi_cc_median']:.4f}")
            print(f"    delta_scale_ratio_masked: {diff['delta_scale_ratio_masked']:.4f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
