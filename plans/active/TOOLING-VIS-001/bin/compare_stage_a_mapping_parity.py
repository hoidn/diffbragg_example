#!/usr/bin/env python3
"""Stage A Mapping Parity Probe CLI (DB-AT-028/029 diagnostics).

Runs Stage A engine on the smoke fixture, reconstructs bragg_before/after via
build_final_bragg_from_stage_a_telemetry, and computes parity vs a mapping
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

    cli_args = parser.parse_args()
    out_dir = cli_args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine sigma source
    sigma_source = cli_args.sigma_source
    if sigma_source is None:
        sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "metadata")

    detector_size = os.environ.get("DBEX_SMOKE_DETECTOR_SIZE", "small")

    print(f"Output directory: {out_dir.resolve()}")
    print(f"Device: {cli_args.device}")
    print(f"Sigma source: {sigma_source}")
    print(f"Detector size: {detector_size}")
    print("")

    # Import dependencies (lazy to avoid overhead when --help is used)
    from argparse import Namespace

    from dbex.data_load import DataLoad
    from dbex.nanobrag_bridge import (
        build_structure_factor_grid,
    )
    from dbex.nanobrag_refinement import (
        RefinementConfig,
        build_final_bragg_from_stage_a_telemetry,
        run_nanobrag_refinement,
    )
    from dbex.vis.mapping import (
        build_mapping_stage_a_context,
        emit_mapping_context_diagnostics,
    )

    # Determine paths (repo_root already set above)
    print(f"Repository root: {repo_root}")

    # Build DataLoad from SMOKE DATASET matching tests/conftest.py::smoke_dataset_paths logic
    sp_proc = repo_root / "sp.proc"

    # Honor DBEX_SMOKE_SIGMA_SOURCE and DBEX_SMOKE_DETECTOR_SIZE per conftest.py
    # Note: metadata + small → full detector with metadata expt (per conftest.py:106-112)
    if sigma_source == "metadata":
        expt_path = sp_proc / "idx-0000_sigma_metadata.expt"
        refl_path = repo_root / "refGeom.refl"
        mask_path = repo_root / "747_mask.pkl"
    else:
        if detector_size == "full":
            expt_path = repo_root / "refGeom.expt"
            refl_path = repo_root / "refGeom.refl"
            mask_path = repo_root / "747_mask.pkl"
        else:
            sp_proc_small = sp_proc / "refGeom_small"
            expt_path = sp_proc_small / "refGeom_small.expt"
            refl_path = sp_proc_small / "refGeom_small.refl"
            mask_path = sp_proc_small / "refGeom_small_mask.pkl"

    print(f"Smoke dataset expt: {expt_path}")
    print(f"Smoke dataset refl: {refl_path}")
    print(f"Smoke dataset mask: {mask_path}")
    print("")

    args = Namespace(
        exptName=str(expt_path),
        reflName=str(refl_path),
        exptIdx=0,
        maskFile=str(mask_path),
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
    )
    dataload = DataLoad(args)

    # Resolve device
    device_obj = torch.device("cuda:0" if torch.cuda.is_available() and cli_args.device != "cpu" else "cpu")

    # Build mapping context for unified HKL/calibration/inputs
    print("Building mapping context via build_mapping_stage_a_context...")
    mapping_context = build_mapping_stage_a_context(
        dataload,
        default_sigma_readout=3.0,
        device=str(device_obj),
    )

    # Emit mapping context diagnostics BEFORE any assertions (TOOLING-VIS-001 requirement)
    mapping_context_path = out_dir / "mapping_context_probe.json"
    print(f"Emitting mapping context diagnostics to {mapping_context_path}...")
    emit_mapping_context_diagnostics(
        mapping_context=mapping_context,
        dataload=dataload,
        output_path=mapping_context_path,
        bragg_model=mapping_context.bragg_zero_iter,
        stage_name="probe",
    )
    print(f"Wrote: {mapping_context_path.resolve()}")

    # Extract HKL grid from the mapping context's original indices/amplitudes
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=mapping_context.hkl_indices,
        amplitudes=mapping_context.hkl_amplitudes,
        device=device_obj,
        halo=True,
    )

    # Determine HKL source from mapping context diagnostics
    hkl_source = mapping_context.diagnostics.get("hkl_source", "scaled.mtz")
    hkl_path = mapping_context.diagnostics.get("hkl_path", "scaled.mtz")

    print(f"HKL source: {hkl_source}")
    print(f"HKL path: {hkl_path}")

    # Use the mapping context's RefinementInputs directly
    refinement_inputs = mapping_context.inputs

    baseline_crystal = dataload.Expt.crystal
    baseline_detector = dataload.Expt.detector
    baseline_beam = dataload.Expt.beam

    # Build perturbed geometry for Stage A engine
    from tests.dbex.test_torch_refine_smoke import create_perturbed_geometry

    perturbed_crystal, perturbed_detector, perturbed_beam = create_perturbed_geometry(
        baseline_crystal, baseline_detector, baseline_beam
    )

    # Run Stage A RefinementEngine (nearest-neighbor HKL)
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
        calibration_metadata=mapping_context.calibration,
        sigma_readout_provenance=(
            "external_lookup" if sigma_source == "metadata" else "cli_override"
        ),
    )

    print("Running Stage A RefinementEngine (nearest-neighbor HKL)...")
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
    )
    telemetry = telemetry_dict["A"]

    # Reconstruct bragg_before/after
    print("Reconstructing bragg_before/after from Stage A telemetry...")
    bragg_before = build_final_bragg_from_stage_a_telemetry(
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
    bragg_after = build_final_bragg_from_stage_a_telemetry(
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

    # Compute log_scale_effective and gather statistics first
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

    # Use mapping context's bragg_zero_iter for parity comparison
    print("Using mapping context bragg_zero_iter for parity comparison...")
    try:
        bragg_mapping = mapping_context.bragg_zero_iter

        # Compute mapping ROI correlations
        corrs_mapping = _roi_correlations(target, bragg_mapping, loss_mask, panel_slices)
        valid_mapping = [c for c in corrs_mapping if np.isfinite(c)]
        roi_cc_median_mapping = float(median(valid_mapping)) if valid_mapping else float("nan")

        # Compute mapping scale ratio
        bragg_mapping_mean = float(np.mean(bragg_mapping))
        scale_ratio_mapping = bragg_mapping_mean / mean_target if mean_target > 0 else float("inf")

        mapping_forward_success = True
        print(f"Mapping forward ROI CC median: {roi_cc_median_mapping:.4f}")
        print(f"Mapping forward scale ratio: {scale_ratio_mapping:.3e}")
    except Exception as exc:
        print(f"Warning: Mapping forward pass failed: {exc}")
        roi_cc_median_mapping = float("nan")
        scale_ratio_mapping = float("nan")
        mapping_forward_success = False

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
        "mapping_forward_success": mapping_forward_success,
        "roi_cc_median_mapping": roi_cc_median_mapping,
        "scale_ratio_mapping": scale_ratio_mapping,
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
    if mapping_forward_success:
        print("=== Mapping Forward Parity ===")
        print(f"ROI CC median (mapping): {roi_cc_median_mapping:.4f}")
        print(f"Scale ratio (mapping): {scale_ratio_mapping:.3e}")
        print("")

    sys.exit(0)


if __name__ == "__main__":
    main()
