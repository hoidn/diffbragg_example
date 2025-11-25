#!/usr/bin/env python3
"""Stage A Mapping Parity Probe CLI (DB-AT-028/029 diagnostics).

Runs Stage A engine on the smoke fixture, reconstructs bragg_before/after via
_build_final_bragg_from_stage_a_telemetry, and computes parity vs a mapping
forward stack with identical HKL/calibration. Emits JSON metrics with
log_scale_effective, scale ratios, ROI CCs, and HKL source provenance.

Usage:
    python plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py \\
        --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T034523Z/parity_probe \\
        --device cpu \\
        --sigma-source metadata

Environment:
    DBEX_SMOKE_SIGMA_SOURCE: sigma readout provenance ("metadata" or other, default: metadata)
    DBEX_SMOKE_DETECTOR_SIZE: detector size ("full" or "small", default: small)
    KMP_DUPLICATE_LIB_OK: Set to TRUE to avoid OpenMP conflicts
    NANOBRAGG_DISABLE_COMPILE: Set to 1 to disable torch.compile for reproducibility

Initiative: TOOLING-VIS-001 Phase D.D
Owner: Ralph (2025-11-25)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import List

import numpy as np
import torch


def _compute_pearson_cc(
    data_roi: np.ndarray,
    model_roi: np.ndarray,
    mask_roi: np.ndarray,
) -> float:
    """Compute Pearson correlation coefficient between ROI slices."""
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
        corrs.append(_compute_pearson_cc(data_roi, model_roi, roi_mask))
    return corrs


def main():
    """Main entry point for Stage A mapping parity probe CLI."""
    # Add repo root to sys.path for test imports
    repo_root = Path(__file__).resolve().parents[4]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    parser = argparse.ArgumentParser(
        description="Stage A Mapping Parity Probe (DB-AT-028/029 diagnostics)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for parity_metrics.json",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device string (default: cpu)",
    )
    parser.add_argument(
        "--sigma-source",
        type=str,
        default=None,
        help="Sigma readout provenance (default: from DBEX_SMOKE_SIGMA_SOURCE env, else 'metadata')",
    )

    args = parser.parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine sigma source
    sigma_source = args.sigma_source
    if sigma_source is None:
        sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "metadata")

    detector_size = os.environ.get("DBEX_SMOKE_DETECTOR_SIZE", "small")

    print(f"Output directory: {out_dir.resolve()}")
    print(f"Device: {args.device}")
    print(f"Sigma source: {sigma_source}")
    print(f"Detector size: {detector_size}")
    print("")

    # Import dependencies (lazy to avoid overhead when --help is used)
    from dbex.nanobrag_bridge import (
        build_structure_factor_grid,
        load_calibration_metadata,
        load_refined_mtz,
        prepare_refinement_inputs,
        simulate_forward_once,
    )
    from dbex.nanobrag_refinement import (
        RefinementConfig,
        _build_final_bragg_from_stage_a_telemetry,
        run_nanobrag_refinement,
    )
    from dbex.tools.stage_a_adam import build_dataload

    # Determine paths (repo_root already set above)
    golden_dir = repo_root / "tests" / "fixtures" / "golden_data" / "simple_cubic"
    calibration_path = golden_dir / "config_torch.json"

    print(f"Repository root: {repo_root}")

    # Build DataLoad for canonical assets
    dataload = build_dataload(repo_root)
    baseline_crystal = dataload.Expt.crystal
    baseline_detector = dataload.Expt.detector
    baseline_beam = dataload.Expt.beam

    # Load calibration metadata
    calibration_metadata = None
    if calibration_path.exists():
        try:
            calibration_metadata = load_calibration_metadata(calibration_path)
            print(f"Loaded calibration metadata from {calibration_path}")
        except Exception as exc:
            print(f"Warning: Failed to load calibration metadata: {exc}")
            calibration_metadata = None

    # Build HKL grid with refined MTZ if available
    hkl_source = "scaled.mtz"
    device_obj = torch.device("cuda:0" if torch.cuda.is_available() and args.device != "cpu" else "cpu")

    if calibration_metadata:
        refined_mtz_path = golden_dir / "refined_structure_factors.mtz"
        if refined_mtz_path.exists():
            try:
                refined_indices, refined_amplitudes = load_refined_mtz(refined_mtz_path)
                hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
                    indices=refined_indices,
                    amplitudes=refined_amplitudes,
                    device=device_obj,
                    halo=True,
                )
                hkl_source = "refined_structure_factors.mtz"
                print(f"Using refined HKL from {refined_mtz_path}")
            except Exception as exc:
                print(f"Warning: Failed to load refined MTZ: {exc}")
                hkl_grid = dataload.hkl_grid
                hkl_metadata = dataload.hkl_metadata
        else:
            hkl_grid = dataload.hkl_grid
            hkl_metadata = dataload.hkl_metadata
    else:
        hkl_grid = dataload.hkl_grid
        hkl_metadata = dataload.hkl_metadata

    # Build RefinementInputs using Stage A smoke fixture approach
    from tests.dbex.test_torch_refine_smoke import create_perturbed_geometry

    perturbed_crystal, perturbed_detector, perturbed_beam = create_perturbed_geometry(
        baseline_crystal, baseline_detector, baseline_beam
    )

    # Build trusted mask per panel (same pattern as test_torch_refine_smoke.py:238-265)
    detector = dataload.Expt.detector
    n_panels = len(detector)
    trusted_masks = []
    for i in range(n_panels):
        panel = detector[i]
        panel_size = panel.get_image_size()
        panel_shape = (panel_size[1], panel_size[0])  # (slow, fast)
        trusted_mask = np.ones(panel_shape, dtype=bool)
        try:
            untrusted = panel.get_mask()
            if untrusted is not None and len(untrusted) > 0:
                for rect in untrusted:
                    x0, x1, y0, y1 = rect
                    trusted_mask[y0:y1, x0:x1] = False
        except Exception:
            pass  # No untrusted regions
        trusted_masks.append(trusted_mask)

    # Resolve sigma_readout
    if sigma_source == "metadata":
        try:
            sigma_readout_array = dataload.Expt.imageset.external_lookup.sigma_readout.data
        except AttributeError:
            sigma_readout_array = np.full_like(dataload.data, 3.0, dtype=np.float32)
    else:
        sigma_readout_array = np.full_like(dataload.data, 3.0, dtype=np.float32)

    refinement_inputs = prepare_refinement_inputs(
        data=dataload.data,
        background_image=dataload.background_image,
        trusted_mask=trusted_masks,
        bbox=dataload.bbox,
        pids=dataload.pids,
        detector=detector,
        sigma_readout=sigma_readout_array,
    )

    # Run Stage A engine with use_engine_delegation=True (nearest-neighbor HKL)
    config = RefinementConfig(
        device=str(device_obj),
        dtype=torch.float32,
        history_size=10,
        max_iter=20,
        roi_sample_fraction=0.15,
        full_validation_interval=5,
        enable_hkl_interpolation=False,  # DB-AT-028/029 require nearest-neighbor HKL
        enable_stage_b=False,
        enable_stage_c=False,
        calibration_metadata=calibration_metadata or None,
        sigma_readout_provenance=(
            "external_lookup" if sigma_source == "metadata" else "cli_override"
        ),
    )

    print("Running Stage A engine (nearest-neighbor HKL)...")
    bragg_final, telemetry_dict = run_nanobrag_refinement(
        inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,
        use_engine_delegation=True,
    )
    telemetry = telemetry_dict["A"]

    # Reconstruct bragg_before/after
    print("Reconstructing bragg_before/after from Stage A telemetry...")
    bragg_before = _build_final_bragg_from_stage_a_telemetry(
        telemetry,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        inputs=refinement_inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=device_obj,
        dtype=config.dtype,
        param_state="initial",
        baseline_crystal=baseline_crystal,
    )
    bragg_after = _build_final_bragg_from_stage_a_telemetry(
        telemetry,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        inputs=refinement_inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=device_obj,
        dtype=config.dtype,
        param_state="final",
        baseline_crystal=baseline_crystal,
    )

    # Note: mapping forward pass comparison is deferred; this probe focuses on
    # Stage A engine diagnostics per input.md Phase D.D

    # Compute log_scale_effective
    log_scale_entry = telemetry.param_deltas.get("log_scale", {})
    log_scale_baseline_entry = telemetry.param_deltas.get("log_scale_baseline", {})

    log_scale_baseline = log_scale_baseline_entry.get("final") if isinstance(log_scale_baseline_entry, dict) else 0.0
    log_scale_init = log_scale_entry.get("initial") if isinstance(log_scale_entry, dict) else 0.0
    log_scale_final = log_scale_entry.get("final") if isinstance(log_scale_entry, dict) else 0.0

    log_scale_effective_init = log_scale_baseline + log_scale_init if log_scale_baseline is not None else log_scale_init
    log_scale_effective_final = log_scale_baseline + log_scale_final if log_scale_baseline is not None else log_scale_final

    # Compute statistics
    target = refinement_inputs.target
    loss_mask = refinement_inputs.loss_mask
    panel_slices = refinement_inputs.panel_slices

    # Bragg statistics
    bragg_before_mean = float(np.mean(bragg_before))
    bragg_after_mean = float(np.mean(bragg_after))

    # Scale ratios
    mean_target = float(np.mean(target[loss_mask]))
    scale_ratio_before = bragg_before_mean / mean_target if mean_target > 0 else float("inf")
    scale_ratio_after = bragg_after_mean / mean_target if mean_target > 0 else float("inf")

    # ROI correlations
    corrs_before = _roi_correlations(target, bragg_before, loss_mask, panel_slices)
    corrs_after = _roi_correlations(target, bragg_after, loss_mask, panel_slices)

    valid_before = [c for c in corrs_before if np.isfinite(c)]
    valid_after = [c for c in corrs_after if np.isfinite(c)]

    roi_cc_median_before = float(median(valid_before)) if valid_before else float("nan")
    roi_cc_median_after = float(median(valid_after)) if valid_after else float("nan")

    # Chi-squared
    chi_trace = telemetry.chi_squared_trace_full or []
    chi2_initial = chi_trace[0][1] if chi_trace else float("nan")
    chi2_final = chi_trace[-1][1] if chi_trace else float("nan")
    masked_pixels = telemetry.variance_floor_masked_pixels or int(np.count_nonzero(loss_mask))

    chi2_per_pixel_initial = chi2_initial / masked_pixels if masked_pixels > 0 else float("nan")
    chi2_per_pixel_final = chi2_final / masked_pixels if masked_pixels > 0 else float("nan")

    # Build metrics JSON
    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device": str(device_obj),
        "sigma_source": sigma_source,
        "detector_size": detector_size,
        "hkl_source": hkl_source,
        "enable_hkl_interpolation": False,
        "log_scale_baseline": log_scale_baseline,
        "log_scale_init": log_scale_init,
        "log_scale_final": log_scale_final,
        "log_scale_effective_init": log_scale_effective_init,
        "log_scale_effective_final": log_scale_effective_final,
        "chi2_initial": chi2_initial,
        "chi2_final": chi2_final,
        "chi2_per_pixel_initial": chi2_per_pixel_initial,
        "chi2_per_pixel_final": chi2_per_pixel_final,
        "variance_floor_masked_pixels": int(masked_pixels),
        "variance_floor_clamp_fraction": telemetry.variance_floor_clamp_fraction or 0.0,
        "bragg_before_mean": bragg_before_mean,
        "bragg_after_mean": bragg_after_mean,
        "scale_ratio_before": scale_ratio_before,
        "scale_ratio_after": scale_ratio_after,
        "roi_cc_median_before": roi_cc_median_before,
        "roi_cc_median_after": roi_cc_median_after,
        "n_rois": len(valid_before),
    }

    # Write metrics JSON
    json_path = out_dir / "parity_metrics.json"
    with json_path.open("w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Wrote: {json_path.resolve()}")
    print("")

    # Print summary
    print("=== Stage A Parity Metrics ===")
    print(f"HKL source: {hkl_source}")
    print(f"log_scale_effective (init): {log_scale_effective_init:.6f}")
    print(f"log_scale_effective (final): {log_scale_effective_final:.6f}")
    print(f"chi²/pixel (init): {chi2_per_pixel_initial:.3e}")
    print(f"chi²/pixel (final): {chi2_per_pixel_final:.3e}")
    print(f"ROI CC median (before): {roi_cc_median_before:.4f}")
    print(f"ROI CC median (after): {roi_cc_median_after:.4f}")
    print(f"Scale ratio (before): {scale_ratio_before:.3e}")
    print(f"Scale ratio (after): {scale_ratio_after:.3e}")
    print("")

    sys.exit(0)


if __name__ == "__main__":
    main()
