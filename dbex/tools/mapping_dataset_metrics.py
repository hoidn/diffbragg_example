#!/usr/bin/env python3
"""Mapping dataset metrics comparison tool.

Compare Stage A mapping contexts across different HKL/calibration configurations
to quantify the effect of HKL source and calibration choice on ROI CC and scale ratios.

Ownership: dbex.tools (ARCH-PROBE-FREEZE-001)
Contracts:
- Diagnostic Script Policy (prompts/supervisor.md:272-309)
- Calibration/Data Dependency Manifest (docs/data_dependency_manifest.md:40-140)
- Stage A Telemetry Ownership (docs/architecture/data_telemetry_flow.md:1-180)

Usage:
    DBEX_SMOKE_SIGMA_SOURCE=metadata \\
    DBEX_SMOKE_DETECTOR_SIZE=small \\
    KMP_DUPLICATE_LIB_OK=TRUE \\
    NANOBRAGG_DISABLE_COMPILE=1 \\
    python -m dbex.tools.mapping_dataset_metrics \\
        --out-dir plans/active/ARCH-PROBE-FREEZE-001/reports/<timestamp>/mapping_dataset_metrics \\
        --cases metadata_raw metadata_calibrated \\
        --emit-roi-artifacts --roi-count 16 --default-sigma 3.0 --device cuda:0
"""

import argparse
import json
import os
import sys
from argparse import Namespace
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch

from dbex.calibration.config_variants import (
    materialize_calibration_variant,
    resolve_dataset_paths,
    resolve_hkl_path,
    resolve_smoke_calibration_path,
)
from dbex.data_load import DataLoad
from dbex.vis.mapping import build_mapping_stage_a_context
from dbex.vis.triptych import plot_triptych


def _pearson_cc(data_roi: np.ndarray, model_roi: np.ndarray, mask_roi: np.ndarray) -> float:
    """Compute masked Pearson correlation for a single ROI.

    Args:
        data_roi: Observed data intensities (ny, nx)
        model_roi: Model intensities (ny, nx)
        mask_roi: Boolean mask (ny, nx) with True=include

    Returns:
        Pearson correlation coefficient (-1 to 1), or NaN if mask is empty/invalid
    """
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
    """Compute per-ROI Pearson CC between model and target.

    Args:
        target: Full-detector target intensities (n_panels, slow, fast)
        model: Full-detector model intensities (n_panels, slow, fast)
        loss_mask: Full-detector loss mask (n_panels, slow, fast)
        panel_slices: List of (panel_id, bbox) tuples with bbox=(x0, x1, y0, y1)

    Returns:
        List of correlation coefficients (may contain NaN for empty ROIs)
    """
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


def define_cases(out_dir: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """Define preset dataset cases with explicit HKL/calibration paths.

    Mirrors the logic from tests/conftest.py::smoke_dataset_paths and refgeom_dataload.
    Uses dbex.calibration.config_variants helpers to resolve paths per env vars.

    Args:
        out_dir: Output directory for materialized calibration variants (optional).
                 If provided, calibration variant cases will materialize modified configs.

    Returns:
        Dictionary mapping case_name -> {expt, refl, mask, hkls, calibration, sigma_map,
        calibration_variant} paths (all absolute or repo-relative). sigma_map is None
        when not applicable. calibration_variant describes any modifications applied.

    Contract: Calibration/Data Dependency Manifest (docs/data_dependency_manifest.md:40-140)
    """
    # Determine detector size and sigma source from env
    detector_size = os.environ.get("DBEX_SMOKE_DETECTOR_SIZE", "small")

    # Resolve dataset paths via canonical helper
    dataset_paths = resolve_dataset_paths(detector_size=detector_size)
    geom_path = dataset_paths["geom_path"]
    refl_path = dataset_paths["refl_path"]
    mask_path = dataset_paths["mask_path"]
    sigma_map_path = dataset_paths["sigma_map_path"]
    sigma_source = dataset_paths["sigma_source"]

    # Resolve smoke calibration path
    smoke_calib_path = resolve_smoke_calibration_path(detector_size=detector_size)

    # Helper: resolve HKL path based on calibration presence
    def resolve_hkl_for_calibration(calibration_path: Optional[str]) -> str:
        return resolve_hkl_path(detector_size=detector_size, calibration_path=calibration_path)

    cases = {
        # Metadata-sigma cases: use external sigma tiles when DBEX_SMOKE_SIGMA_SOURCE=metadata
        "metadata_raw": {
            "expt": geom_path,
            "refl": refl_path,
            "mask": mask_path,
            "hkls": resolve_hkl_for_calibration(None),  # No calibration → scaled.mtz
            "calibration": None,
            "sigma_map": sigma_map_path,
            "sigma_source": "metadata",
        },
        "metadata_calibrated": {
            "expt": geom_path,
            "refl": refl_path,
            "mask": mask_path,
            "hkls": resolve_hkl_for_calibration(smoke_calib_path) if smoke_calib_path else resolve_hkl_for_calibration(None),
            "calibration": smoke_calib_path,
            "sigma_map": sigma_map_path,
            "sigma_source": "metadata",
        },
        # CLI-override cases: explicitly drop sigma_map to use default_sigma CLI override
        "cli_raw": {
            "expt": geom_path,
            "refl": refl_path,
            "mask": mask_path,
            "hkls": resolve_hkl_for_calibration(None),
            "calibration": None,
            "sigma_map": None,
            "sigma_source": "cli_override",
        },
        "cli_calibrated": {
            "expt": geom_path,
            "refl": refl_path,
            "mask": mask_path,
            "hkls": resolve_hkl_for_calibration(smoke_calib_path) if smoke_calib_path else resolve_hkl_for_calibration(None),
            "calibration": smoke_calib_path,
            "sigma_map": None,
            "sigma_source": "cli_override",
        },
        # Legacy aliases for backward compatibility
        "scaled_raw": {
            "expt": geom_path,
            "refl": refl_path,
            "mask": mask_path,
            "hkls": resolve_hkl_for_calibration(None),
            "calibration": None,
            "sigma_map": sigma_map_path,
            "sigma_source": sigma_source,
        },
        "scaled_calibrated": {
            "expt": geom_path,
            "refl": refl_path,
            "mask": mask_path,
            "hkls": resolve_hkl_for_calibration(smoke_calib_path) if smoke_calib_path else resolve_hkl_for_calibration(None),
            "calibration": smoke_calib_path,
            "sigma_map": sigma_map_path,
            "sigma_source": sigma_source,
        },
    }

    # Calibration variant cases (require out_dir for materialization)
    if out_dir is not None and smoke_calib_path and Path(smoke_calib_path).exists():
        # metadata_calibrated_drop_ncells: keep original spot_scale, remove N_cells only
        variant_calib_drop_ncells = materialize_calibration_variant(
            base_config_path=smoke_calib_path,
            variant_name="metadata_calibrated_drop_ncells",
            out_dir=out_dir,
            spot_scale_override=None,
            drop_n_cells=True,
        )
        cases["metadata_calibrated_drop_ncells"] = {
            "expt": geom_path,
            "refl": refl_path,
            "mask": mask_path,
            "hkls": resolve_hkl_for_calibration(smoke_calib_path),
            "calibration": variant_calib_drop_ncells,
            "sigma_map": sigma_map_path,
            "sigma_source": "metadata",
            "calibration_variant": "N_cells removed (spot_scale retained)",
        }

        # metadata_calibrated_spot1: force spot_scale_override to 1.0
        variant_calib_spot1 = materialize_calibration_variant(
            base_config_path=smoke_calib_path,
            variant_name="metadata_calibrated_spot1",
            out_dir=out_dir,
            spot_scale_override=1.0,
            drop_n_cells=False,
        )
        cases["metadata_calibrated_spot1"] = {
            "expt": geom_path,
            "refl": refl_path,
            "mask": mask_path,
            "hkls": resolve_hkl_for_calibration(smoke_calib_path),
            "calibration": variant_calib_spot1,
            "sigma_map": sigma_map_path,
            "sigma_source": "metadata",
            "calibration_variant": "spot_scale_override=1.0",
        }

        # metadata_calibrated_spot1_drop_ncells: force spot_scale to 1.0 AND remove N_cells
        variant_calib_spot1_no_ncells = materialize_calibration_variant(
            base_config_path=smoke_calib_path,
            variant_name="metadata_calibrated_spot1_drop_ncells",
            out_dir=out_dir,
            spot_scale_override=1.0,
            drop_n_cells=True,
        )
        cases["metadata_calibrated_spot1_drop_ncells"] = {
            "expt": geom_path,
            "refl": refl_path,
            "mask": mask_path,
            "hkls": resolve_hkl_for_calibration(smoke_calib_path),
            "calibration": variant_calib_spot1_no_ncells,
            "sigma_map": sigma_map_path,
            "sigma_source": "metadata",
            "calibration_variant": "spot_scale_override=1.0, N_cells removed",
        }

    return cases


def build_dataload_for_case(case_spec: Dict[str, str], case_name: str = "") -> DataLoad:
    """Build a DataLoad instance for a specific case configuration.

    Args:
        case_spec: dict with keys {expt, refl, mask, hkls, calibration, sigma_map, sigma_source}
        case_name: Name of the case (used to determine apply_calibration_n_cells)

    Returns:
        DataLoad instance configured for this case

    Per tests/conftest.py::refgeom_dataload (lines 224-237):
    - When case_spec["sigma_source"]=="metadata" and case_spec["sigma_map"] is present,
      pass it through args.sigma_map so DataLoad loads external sigma tiles.
    - When case_spec["sigma_source"]=="cli_override", sigma_map is None so DataLoad
      will rely on the default_sigma CLI override passed to compute_case_metrics.
    - Keep HKL and calibration overrides per case.

    Contract: DataLoad sigma handling (docs/data_dependency_manifest.md:69-77)
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
        hkl_source_path=case_spec["hkls"],
        calibration_config_path=case_spec["calibration"],
        sigma_map=case_spec.get("sigma_map"),
        config_path=case_spec["calibration"],  # Alias for calibration_config_path
    )

    dataload = DataLoad(args)

    # Determine apply_calibration_n_cells from case spec or name
    calibration_variant = case_spec.get("calibration_variant", "")
    if "N_cells removed" in calibration_variant or "drop_ncells" in case_name.lower():
        dataload.apply_calibration_n_cells = False
    else:
        dataload.apply_calibration_n_cells = True

    return dataload


def compute_case_metrics(
    case_name: str,
    case_spec: Dict[str, str],
    default_sigma: float,
    device: str,
    emit_roi_artifacts: bool = False,
    roi_count: int = 16,
    roi_artifacts_dir: Optional[Path] = None,
) -> Dict:
    """Build mapping context for a case and compute metrics.

    Args:
        case_name: Human-readable case identifier
        case_spec: Dataset paths dict (includes sigma_source)
        default_sigma: Fallback sigma value (ADU)
        device: Device string (e.g., "cpu", "cuda:0")
        emit_roi_artifacts: If True, emit PNG+NPZ for lowest-correlation ROIs
        roi_count: Number of ROIs to emit (default 16)
        roi_artifacts_dir: Directory for ROI artifacts (required if emit_roi_artifacts=True)

    Returns:
        Dictionary with per-case metrics plus diagnostics

    Contract: Stage A Telemetry Ownership (docs/architecture/data_telemetry_flow.md:1-42)
    """
    sigma_source = case_spec.get("sigma_source", "metadata")

    print(f"\n=== Building mapping context for case: {case_name} ===")
    print(f"  expt: {case_spec['expt']}")
    print(f"  refl: {case_spec['refl']}")
    print(f"  mask: {case_spec['mask']}")
    print(f"  hkls: {case_spec['hkls']}")
    print(f"  calibration: {case_spec['calibration']}")
    print(f"  sigma_source: {sigma_source}")
    print(f"  sigma_map: {case_spec.get('sigma_map', 'None')}")

    # Build DataLoad for this case
    dataload = build_dataload_for_case(case_spec, case_name=case_name)
    apply_n_cells = getattr(dataload, 'apply_calibration_n_cells', True)

    # Build mapping context reusing canonical helper
    mapping_context = build_mapping_stage_a_context(
        dataload,
        default_sigma_readout=default_sigma,
        device=device,
        apply_calibration_n_cells=apply_n_cells,
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

    # Extract HKL telemetry
    hkl_telemetry = diagnostics.get("hkl_telemetry", {})

    # Extract sigma provenance
    sigma_readout_map_source = getattr(dataload, "sigma_readout_map_source", "unknown")
    sigma_map_path_used = case_spec.get("sigma_map")

    # Compute global_scale_hint
    global_scale_hint = float(inputs.global_scale_hint) if inputs.global_scale_hint is not None else float("nan")

    # Extract calibration variant info
    calibration_variant = case_spec.get("calibration_variant", None)
    derived_calibration_path = case_spec["calibration"]

    # Extract N_cells telemetry
    n_cells_applied = diagnostics.get("n_cells_applied", None)
    n_cells_suppression_reason = diagnostics.get("n_cells_suppression_reason", None)

    print(f"  roi_cc_median: {roi_cc_median:.4f}")
    print(f"  scale_ratio_masked: {scale_ratio_masked:.4f}")
    print(f"  scale_ratio_unmasked: {scale_ratio_unmasked:.4f}")
    print(f"  mean_target_masked: {mean_target_masked:.2f}")
    print(f"  mean_model_masked: {mean_model_masked:.2f}")
    print(f"  bragg_mean: {bragg_mean:.2f}")
    print(f"  bragg_std: {bragg_std:.2f}")
    print(f"  bragg_max: {bragg_max:.2f}")
    print(f"  hkl_source: {hkl_source}")
    print(f"  hkl_path: {hkl_path}")
    print(f"  hkl_count: {hkl_count}")
    print(f"  sigma_floor_value: {sigma_floor_value}")
    print(f"  sigma_readout_map_source: {sigma_readout_map_source}")
    print(f"  spot_scale_override: {spot_scale_override}")
    print(f"  global_scale_hint: {global_scale_hint}")
    print(f"  n_cells_applied: {n_cells_applied}")
    print(f"  n_cells_suppression_reason: {n_cells_suppression_reason}")

    # Emit ROI artifacts if requested
    if emit_roi_artifacts and roi_artifacts_dir is not None:
        roi_artifacts_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n  Emitting ROI artifacts to {roi_artifacts_dir}...")

        # Compute per-ROI metrics for artifact selection
        roi_metrics_list = []
        for roi_idx, (pid, bbox) in enumerate(inputs.panel_slices):
            x0, x1, y0, y1 = bbox
            data_roi = target[int(pid), y0:y1, x0:x1]
            model_roi = bragg_mapping[int(pid), y0:y1, x0:x1]
            roi_mask = loss_mask[int(pid), y0:y1, x0:x1]

            if not np.any(roi_mask):
                corr = float("nan")
            else:
                corr = _pearson_cc(data_roi, model_roi, roi_mask)

            roi_metrics_list.append({
                "roi_idx": roi_idx,
                "panel_id": int(pid),
                "bbox": [int(x0), int(x1), int(y0), int(y1)],
                "correlation": corr,
            })

        # Sort by correlation (lowest first, NaN at end)
        def sort_key(x):
            c = x["correlation"]
            return (np.isnan(c), c if not np.isnan(c) else float("inf"))

        roi_metrics_list.sort(key=sort_key)

        # Emit artifacts for N lowest-correlation ROIs
        n_emit = min(roi_count, len(roi_metrics_list))
        print(f"  Emitting {n_emit} lowest-correlation ROIs...")

        for i, roi_info in enumerate(roi_metrics_list[:n_emit]):
            roi_idx = roi_info["roi_idx"]
            pid = roi_info["panel_id"]
            x0, x1, y0, y1 = roi_info["bbox"]
            corr = roi_info["correlation"]

            data_roi = target[pid, y0:y1, x0:x1]
            model_roi = bragg_mapping[pid, y0:y1, x0:x1]
            roi_mask = loss_mask[pid, y0:y1, x0:x1]

            # Compute variance (per spec-db-core.md: V = I_model + sigma_readout^2, clamped to sigma_floor^2)
            variance_roi = np.maximum(
                model_roi + default_sigma ** 2,
                sigma_floor_value ** 2
            )

            # Compute residual
            residual_roi = data_roi - model_roi

            # Save NPZ
            npz_path = roi_artifacts_dir / f"roi_{roi_idx:04d}_corr_{corr:.3f}.npz"
            np.savez(
                npz_path,
                data=data_roi,
                model=model_roi,
                residual=residual_roi,
                variance=variance_roi,
                mask=roi_mask,
                correlation=corr,
                panel_id=pid,
                bbox=[x0, x1, y0, y1],
            )

            # Generate PNG triptych
            png_path = roi_artifacts_dir / f"roi_{roi_idx:04d}_corr_{corr:.3f}.png"
            try:
                plot_triptych(
                    data=data_roi,
                    model=model_roi,
                    variance=variance_roi,
                    hkl=None,
                    correlation=corr,
                    filename=str(png_path),
                )
                print(f"    [{i+1:2d}/{n_emit}] ROI {roi_idx:4d}: corr={corr:7.3f} -> {png_path.name}")
            except Exception as e:
                print(f"    WARNING: Failed to generate triptych for ROI {roi_idx}: {e}")

        print(f"  ROI artifacts emission complete.")

    # Assemble metrics dict
    metrics = {
        "case_name": case_name,
        "roi_cc_median": roi_cc_median,
        "scale_ratio_masked": scale_ratio_masked,
        "scale_ratio_unmasked": scale_ratio_unmasked,
        "mean_target_masked": mean_target_masked,
        "mean_model_masked": mean_model_masked,
        "mean_target_unmasked": mean_target_unmasked,
        "mean_model_unmasked": mean_model_unmasked,
        "bragg_mean": bragg_mean,
        "bragg_std": bragg_std,
        "bragg_max": bragg_max,
        "global_scale_hint": global_scale_hint,
        "sigma_floor_value": sigma_floor_value,
        "spot_scale_override": spot_scale_override,
        "calibration_path": calibration_path,
        "derived_calibration_path": derived_calibration_path,
        "hkl_source": hkl_source,
        "hkl_path": hkl_path,
        "hkl_count": hkl_count,
        "hkl_telemetry": hkl_telemetry,
        "sigma_source": sigma_source,
        "sigma_readout_map_source": sigma_readout_map_source,
        "sigma_map_path": sigma_map_path_used,
        "n_cells_applied": n_cells_applied,
        "n_cells_suppression_reason": n_cells_suppression_reason,
        "n_rois": len(valid_corrs),
        "device": device,
    }

    if calibration_variant:
        metrics["calibration_variant"] = calibration_variant

    return metrics


def compute_diffs(base_metrics: Dict, other_metrics: Dict) -> Dict:
    """Compute difference metrics between two cases.

    Args:
        base_metrics: Metrics dict for the base case
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


def run_mapping_dataset_metrics(
    cases: List[str],
    *,
    out_dir: Path,
    default_sigma: float = 3.0,
    device: str = "cuda:0",
    emit_roi_artifacts: bool = False,
    roi_count: int = 16,
) -> Dict:
    """Importable runner for mapping dataset metrics comparison.

    Args:
        cases: List of case names to compare
        out_dir: Output directory for metrics JSON and logs
        default_sigma: Fallback sigma_readout value (default: 3.0 ADU)
        device: Device for mapping forward computation (default: cuda:0)
        emit_roi_artifacts: If True, emit PNG+NPZ for lowest-correlation ROIs
        roi_count: Number of lowest-correlation ROIs to emit (default: 16)

    Returns:
        Dictionary with "cases" (list of metrics dicts) and "diffs" (list of diff dicts)

    Purpose: Provides importable interface for tests/scripts without subprocess spawning
    """
    # Create output directory
    out_dir.mkdir(parents=True, exist_ok=True)

    # Get sigma source from env
    sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "override")

    # Define available cases (pass out_dir so calibration variants can be materialized)
    available_cases = define_cases(out_dir=out_dir)

    # Validate requested cases
    for case_name in cases:
        if case_name not in available_cases:
            raise ValueError(f"Unknown case '{case_name}'. Available: {list(available_cases.keys())}")

    print(f"Running mapping dataset metrics comparison")
    print(f"Cases: {cases}")
    print(f"Output directory: {out_dir}")
    print(f"Device: {device}")
    print(f"Sigma source: {sigma_source}")
    print(f"Default sigma: {default_sigma} ADU")

    # Compute metrics for each case
    case_metrics = []
    for case_name in cases:
        case_spec = available_cases[case_name]

        # Prepare ROI artifacts directory if emission is requested
        roi_artifacts_dir = None
        if emit_roi_artifacts:
            roi_artifacts_dir = out_dir / case_name / "roi_diagnostics"

        metrics = compute_case_metrics(
            case_name=case_name,
            case_spec=case_spec,
            default_sigma=default_sigma,
            device=device,
            emit_roi_artifacts=emit_roi_artifacts,
            roi_count=roi_count,
            roi_artifacts_dir=roi_artifacts_dir,
        )
        case_metrics.append(metrics)

    # Compute diffs if multiple cases
    diffs = []
    if len(case_metrics) > 1:
        base = case_metrics[0]
        for other in case_metrics[1:]:
            diff = compute_diffs(base, other)
            diffs.append(diff)

    # Assemble final output
    output = {
        "cases": case_metrics,
        "diffs": diffs,
    }

    # Write JSON
    json_path = out_dir / "mapping_dataset_metrics.json"
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
    return output


def main():
    """CLI entry point for mapping dataset metrics comparison."""
    parser = argparse.ArgumentParser(
        description="Compare mapping dataset metrics across HKL/calibration configurations"
    )
    parser.add_argument(
        "--cases",
        nargs="+",
        required=True,
        help="List of case names to compare (e.g., metadata_raw metadata_calibrated)",
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
    parser.add_argument(
        "--emit-roi-artifacts",
        action="store_true",
        help="Emit per-case ROI stacks (data/model/residual PNG+NPZ) for inspection",
    )
    parser.add_argument(
        "--roi-count",
        type=int,
        default=16,
        help="Number of lowest-correlation ROIs to emit as PNG/NPZ artifacts (default: 16)",
    )

    args = parser.parse_args()

    # Run the comparison using the importable runner
    run_mapping_dataset_metrics(
        cases=args.cases,
        out_dir=args.out_dir,
        default_sigma=args.default_sigma,
        device=args.device,
        emit_roi_artifacts=args.emit_roi_artifacts,
        roi_count=args.roi_count,
    )


if __name__ == "__main__":
    main()
