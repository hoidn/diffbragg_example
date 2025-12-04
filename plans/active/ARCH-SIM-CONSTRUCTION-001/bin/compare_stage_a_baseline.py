#!/usr/bin/env python
"""
Stage A baseline telemetry vs reconstruction verification probe (ARCH-SIM-CONSTRUCTION-001 Phase C.9).

This script reproduces the Stage A smoke fixture, captures telemetry fields
(target_mean_masked, model_mean_masked, log_scale_effective), reconstructs bragg_before
via build_final_bragg_from_stage_a_telemetry(param_state="initial"), and computes
masked/unmasked means plus chi²-per-pixel using the same loss mask.

The goal is to identify the first divergence between Stage A telemetry and the
reconstructed baseline that keeps DB-AT-028/029 at chi²≈2.1e5.

Usage:
    AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \\
    DBEX_SMOKE_SIGMA_SOURCE=cli_override \\
    DBEX_SMOKE_DETECTOR_SIZE=small \\
    KMP_DUPLICATE_LIB_OK=TRUE \\
    NANOBRAGG_DISABLE_COMPILE=1 \\
    python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py \\
        --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T190000Z/stage_a_baseline_probe.json

References:
    - input.md Do Now (2025-12-13T190000Z)
    - plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md Phase C.9
    - docs/spec-db-conformance.md:319-366 (DB-AT-028/029 acceptance thresholds)
"""

import argparse
import json
import os
import sys
from argparse import Namespace
from pathlib import Path

import numpy as np
import torch

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import build_structure_factor_grid
from dbex.refinement.config import RefinementConfig
from dbex.refinement.context import build_refinement_context
from dbex.refinement.engine import RefinementEngine
from dbex.refinement.stage_a import StageA
from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry
from dbex.vis.mapping import build_mapping_stage_a_context


def create_perturbed_geometry(crystal, detector, beam):
    """
    Create deterministically perturbed copies of crystal/detector/beam for Stage A smoke testing.
    Simplified version from test_torch_refine_smoke.py.
    """
    import copy
    from scitbx import matrix

    # Deep copy to avoid mutating baseline
    crystal_perturbed = copy.deepcopy(crystal)
    detector_perturbed = copy.deepcopy(detector)
    beam_perturbed = copy.deepcopy(beam)

    # Perturb unit cell (+2% a-axis, +1% b/c-axes)
    a, b, c, alpha, beta, gamma = crystal_perturbed.get_unit_cell().parameters()
    from cctbx.uctbx import unit_cell
    perturbed_cell = unit_cell((a * 1.02, b * 1.01, c * 1.01, alpha, beta, gamma))
    crystal_perturbed.set_unit_cell(perturbed_cell)

    # Perturb orientation (+1.5° misset along Z-axis)
    U_matrix = matrix.sqr(crystal_perturbed.get_U())
    from math import radians, cos, sin
    angle_rad = radians(1.5)
    Rz = matrix.sqr((cos(angle_rad), -sin(angle_rad), 0,
                     sin(angle_rad),  cos(angle_rad), 0,
                     0, 0, 1))
    U_perturbed = Rz * U_matrix
    crystal_perturbed.set_U(U_perturbed)

    return crystal_perturbed, detector_perturbed, beam_perturbed


def get_refgeom_dataload():
    """
    Load refGeom dataset for refinement tests.
    Replicates refgeom_dataload fixture logic.
    """
    repo_root = Path(__file__).parent.parent.parent.parent.parent

    # Determine detector size from environment variable
    detector_size = os.environ.get("DBEX_SMOKE_DETECTOR_SIZE", "small")

    if detector_size == "small":
        smoke_dir = repo_root / "sp.proc" / "refGeom_small"
        expt_path = smoke_dir / "refGeom_small.expt"
        refl_path = smoke_dir / "refGeom_small.refl"
        mask_path = smoke_dir / "refGeom_small_mask.pkl"
    else:
        # Full detector (default canonical refGeom)
        expt_path = repo_root / "refGeom.expt"
        refl_path = repo_root / "refGeom.refl"
        mask_path = repo_root / "747_mask.pkl"

    # Calibration config path
    calib_source_env = os.environ.get("DBEX_SMOKE_CALIB_PATH")
    calibration_config_path = None
    smoke_calib_default = repo_root / "sp.proc" / "calibration" / "config_torch_smoke.json"
    if calib_source_env is not None:
        if not Path(calib_source_env).is_absolute():
            calibration_config_path = str(repo_root / calib_source_env)
        else:
            calibration_config_path = str(Path(calib_source_env))
    elif smoke_calib_default.exists():
        calibration_config_path = str(smoke_calib_default)

    # HKL source path
    hkl_source_env = os.environ.get("DBEX_SMOKE_HKL_PATH")
    default_refined_mtz = repo_root / "sp.proc" / "calibration" / "smoke_refined_structure_factors.mtz"
    if hkl_source_env is not None:
        if not Path(hkl_source_env).is_absolute():
            hkl_source_path = repo_root / hkl_source_env
        else:
            hkl_source_path = Path(hkl_source_env)
    elif calibration_config_path and default_refined_mtz.exists():
        hkl_source_path = default_refined_mtz
    else:
        hkl_source_path = repo_root / "scaled.mtz"

    args = Namespace(
        exptName=str(expt_path),
        reflName=str(refl_path),
        exptIdx=0,
        maskFile=str(mask_path),
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
        hkl_source_path=str(hkl_source_path),
        calibration_config_path=calibration_config_path,
    )

    return DataLoad(args)


def main():
    parser = argparse.ArgumentParser(
        description="Stage A baseline telemetry verification probe"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output JSON path for probe results",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0" if torch.cuda.is_available() else "cpu",
        help="Device for computation (default: cuda:0 if available, else cpu)",
    )
    args = parser.parse_args()

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Stage A Baseline Probe] Starting probe (device={args.device})")
    print(f"[Stage A Baseline Probe] Output will be saved to: {args.output}")

    # Build fixture data (replicating stage_a_smoke_result fixture logic)
    device_obj = torch.device(args.device)
    device = str(device_obj)

    # Get data dependencies (same as fixture)
    refgeom_dataload = get_refgeom_dataload()
    smoke_sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "metadata")

    # Extract apply_calibration_n_cells from fixture (default True)
    apply_n_cells = getattr(refgeom_dataload, 'apply_calibration_n_cells', True)

    # Build mapping context for unified HKL/calibration/inputs
    mapping_context = build_mapping_stage_a_context(
        refgeom_dataload,
        default_sigma_readout=3.0,
        device=device,
        apply_calibration_n_cells=apply_n_cells,
    )

    # Use mapping_context.inputs directly
    refinement_inputs = mapping_context.inputs

    # Extract HKL grid from the mapping context's original indices/amplitudes
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=mapping_context.hkl_indices,
        amplitudes=mapping_context.hkl_amplitudes,
        device=device_obj,
        halo=True,
    )

    # Extract calibration metadata
    spot_scale_override_val = 1.0
    if mapping_context.calibration:
        spot_scale_override_val = float(mapping_context.calibration.get("spot_scale_override", 1.0))

    baseline_crystal = refgeom_dataload.Expt.crystal
    baseline_detector = refgeom_dataload.Expt.detector
    baseline_beam = refgeom_dataload.Expt.beam

    perturbed_crystal, perturbed_detector, perturbed_beam = create_perturbed_geometry(
        baseline_crystal, baseline_detector, baseline_beam
    )

    config = RefinementConfig(
        device=device,
        dtype=torch.float32,
        history_size=10,
        max_iter=20,
        roi_sample_fraction=0.15,
        full_validation_interval=5,
        enable_hkl_interpolation=False,  # DB-AT-028/029 require nearest-neighbor HKL sampling
        enable_stage_b=False,
        enable_stage_c=False,
        calibration_metadata=mapping_context.calibration,
        sigma_readout_provenance=(
            "external_lookup" if smoke_sigma_source == "metadata" else "cli_override"
        ),
        apply_calibration_n_cells=apply_n_cells,
    )

    # Build refinement context and run Stage A
    refinement_context = build_refinement_context(
        refinement_inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,
    )
    stages = [StageA()]
    engine = RefinementEngine(stages, config=config)

    print("[Stage A Baseline Probe] Running RefinementEngine with Stage A...")
    telemetry_dict = engine.run({"context": refinement_context})

    # ARCH-SIM-CONSTRUCTION-001 Phase C.9: Extract artifacts for warm cache access
    # Use defensive lookup per input.md requirement (fallback when artifacts missing)
    stage_a_artifacts = getattr(engine, "_artifacts", {}).get("stage_a")
    bragg_full_cached = None
    stage_a_ctx_cached = None
    if stage_a_artifacts:
        bragg_full_cached = stage_a_artifacts.bragg_full
        stage_a_ctx_cached = stage_a_artifacts.stage_a_ctx

    telemetry = telemetry_dict["stage_a"]
    print("[Stage A Baseline Probe] Stage A complete, extracting telemetry and artifacts...")
    if stage_a_artifacts:
        print("[Stage A Baseline Probe] Warm cache path: stage_a_artifacts available, reusing cached Bragg stack")
    else:
        print("[Stage A Baseline Probe] Cold fallback path: stage_a_artifacts missing, will reconstruct from telemetry")

    # Extract telemetry fields of interest
    param_deltas = telemetry.param_deltas if hasattr(telemetry, 'param_deltas') else {}
    log_scale_entry = param_deltas.get("log_scale", {})
    log_scale_baseline_entry = param_deltas.get("log_scale_baseline", {})
    log_scale_effective_entry = param_deltas.get("log_scale_effective", {})

    # ARCH-SIM-CONSTRUCTION-001 Phase C.9: Extract masked means from top-level telemetry fields
    # These fields should be populated by Stage A telemetry instrumentation (Phase C.7)
    target_mean_masked_telem = float("nan")
    model_mean_masked_telem = float("nan")
    if hasattr(telemetry, 'target_mean_masked'):
        target_mean_masked_telem = float(telemetry.target_mean_masked) if telemetry.target_mean_masked is not None else float("nan")
    if hasattr(telemetry, 'model_mean_masked'):
        model_mean_masked_telem = float(telemetry.model_mean_masked) if telemetry.model_mean_masked is not None else float("nan")

    # Fallback: try to extract from log_scale_effective dict (legacy path for older telemetry)
    if not np.isfinite(target_mean_masked_telem):
        target_mean_masked_telem = log_scale_effective_entry.get("target_mean_masked", float("nan"))
    if not np.isfinite(model_mean_masked_telem):
        model_mean_masked_telem = log_scale_effective_entry.get("model_mean_masked", float("nan"))

    # Extract scale_factor and related fields from log_scale_effective dict
    log_scale_baseline_value_telem = log_scale_effective_entry.get("log_scale_baseline_value", float("nan"))
    log_scale_delta_clamped_telem = log_scale_effective_entry.get("log_scale_delta_clamped", float("nan"))
    log_scale_clamped_value_telem = log_scale_effective_entry.get("log_scale_clamped_value", float("nan"))
    scale_factor_telem = log_scale_effective_entry.get("scale_factor", float("nan"))

    # Reconstruct bragg_before from initial telemetry parameters
    # ARCH-SIM-CONSTRUCTION-001 Phase C.9: Use stage_a_ctx from artifacts when available (warm cache)
    # Thread the cached context if available; otherwise fall back to cold reconstruction
    if stage_a_ctx_cached:
        print("[Stage A Baseline Probe] Reconstructing bragg_before from initial telemetry with warm cache...")
    else:
        print("[Stage A Baseline Probe] Reconstructing bragg_before from initial telemetry (cold path, no cached context)...")

    bragg_before = build_final_bragg_from_stage_a_telemetry(
        telemetry_a=telemetry,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        inputs=refinement_inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=device_obj,
        dtype=config.dtype,
        stage_a_ctx=stage_a_ctx_cached,  # Use cached context if available, else None triggers cold path
        baseline_crystal=baseline_crystal,
        param_state="initial",  # Use initial telemetry params for zero-iteration baseline
    )

    # Compute masked/unmasked means from reconstructed bragg_before
    loss_mask_np = refinement_inputs.loss_mask.astype(bool)
    target_np = refinement_inputs.target

    # Masked means from reconstructed bragg_before
    bragg_before_masked = bragg_before[loss_mask_np]
    target_masked = target_np[loss_mask_np]

    bragg_before_mean_masked = float(np.mean(bragg_before_masked)) if bragg_before_masked.size > 0 else float("nan")
    target_mean_masked_reconstructed = float(np.mean(target_masked)) if target_masked.size > 0 else float("nan")

    # Unmasked means
    bragg_before_mean_unmasked = float(np.mean(bragg_before))
    target_mean_unmasked = float(np.mean(target_np))

    # Compute chi²-per-pixel initial (same computation as DB-AT-028)
    # chi²/pixel = sum((target - model)² / variance) / n_pixels
    # For initial computation, we use the reconstructed bragg_before as the model
    residual_masked = target_masked - bragg_before_masked
    # Variance floor from telemetry or default
    variance_floor_value = telemetry.variance_floor_value if hasattr(telemetry, 'variance_floor_value') else 1.0
    variance_masked = np.maximum(bragg_before_masked, variance_floor_value)
    chi_squared_initial = float(np.sum(residual_masked ** 2 / variance_masked))
    n_masked_pixels = int(np.count_nonzero(loss_mask_np))
    chi_squared_per_pixel_initial = chi_squared_initial / n_masked_pixels if n_masked_pixels > 0 else float("nan")

    # Compute log_scale_effective from telemetry
    log_scale_baseline = log_scale_baseline_entry.get("final", 0.0) if isinstance(log_scale_baseline_entry, dict) else 0.0
    log_scale_init = log_scale_entry.get("initial", 0.0) if isinstance(log_scale_entry, dict) else 0.0
    log_scale_effective_init = log_scale_baseline + log_scale_init if log_scale_baseline is not None else log_scale_init

    # Extract mask metadata from telemetry (ARCH-SIM-CONSTRUCTION-001 C.10)
    telemetry_mask_metadata = None
    if hasattr(telemetry, 'mask_metadata') and telemetry.mask_metadata is not None:
        telemetry_mask_metadata = telemetry.mask_metadata

    # Compute reconstruction mask metadata
    reconstruction_mask_metadata = None
    mask_checksum_match = None
    if refinement_inputs.loss_mask is not None:
        import hashlib
        loss_mask_pixel_count = int(np.count_nonzero(refinement_inputs.loss_mask))
        mask_array = np.ascontiguousarray(refinement_inputs.loss_mask, dtype=np.uint8)
        mask_checksum = hashlib.sha1(mask_array).hexdigest()

        reconstruction_mask_metadata = {
            'loss_mask_pixel_count': loss_mask_pixel_count,
            'mask_checksum': mask_checksum,
        }

        # Check if checksums match
        if telemetry_mask_metadata is not None:
            telem_checksum = telemetry_mask_metadata.get('mask_checksum')
            if telem_checksum is not None:
                mask_checksum_match = (telem_checksum == mask_checksum)

    # Build output payload
    output = {
        "probe_metadata": {
            "timestamp": "2025-12-13T190000Z",
            "initiative": "ARCH-SIM-CONSTRUCTION-001",
            "phase": "C.9",
            "purpose": "Capture Stage A telemetry vs reconstructed bragg_before baselines",
            "device": device,
            "apply_calibration_n_cells": apply_n_cells,
            "spot_scale_override": spot_scale_override_val,
            "warm_cache_available": stage_a_artifacts is not None,
            "stage_a_ctx_used": stage_a_ctx_cached is not None,
            "bragg_full_cached_available": bragg_full_cached is not None,
        },
        "telemetry_fields": {
            "target_mean_masked": target_mean_masked_telem,
            "model_mean_masked": model_mean_masked_telem,
            "log_scale_baseline_value": log_scale_baseline_value_telem,
            "log_scale_delta_clamped": log_scale_delta_clamped_telem,
            "log_scale_clamped_value": log_scale_clamped_value_telem,
            "scale_factor": scale_factor_telem,
            "log_scale_effective_initial": float(log_scale_effective_init),
            "variance_floor_value": float(variance_floor_value),
        },
        "reconstructed_bragg_before": {
            "mean_masked": bragg_before_mean_masked,
            "mean_unmasked": bragg_before_mean_unmasked,
            "target_mean_masked": target_mean_masked_reconstructed,
            "target_mean_unmasked": target_mean_unmasked,
            "chi_squared_per_pixel_initial": chi_squared_per_pixel_initial,
            "n_masked_pixels": n_masked_pixels,
        },
        "comparison": {
            "target_mean_masked_match": abs(target_mean_masked_telem - target_mean_masked_reconstructed) < 1e-6 if np.isfinite(target_mean_masked_telem) and np.isfinite(target_mean_masked_reconstructed) else False,
            "target_mean_masked_delta": float(target_mean_masked_telem - target_mean_masked_reconstructed) if np.isfinite(target_mean_masked_telem) and np.isfinite(target_mean_masked_reconstructed) else float("nan"),
            "model_mean_masked_vs_reconstructed_delta": float(model_mean_masked_telem - bragg_before_mean_masked) if np.isfinite(model_mean_masked_telem) and np.isfinite(bragg_before_mean_masked) else float("nan"),
            "model_mean_masked_vs_reconstructed_ratio": float(model_mean_masked_telem / bragg_before_mean_masked) if np.isfinite(model_mean_masked_telem) and np.isfinite(bragg_before_mean_masked) and bragg_before_mean_masked != 0 else float("nan"),
        },
        "db_at_thresholds": {
            "DB_AT_028_chi_squared_per_pixel_threshold": 1e2,
            "DB_AT_028_chi_squared_per_pixel_actual": chi_squared_per_pixel_initial,
            "DB_AT_028_pass": chi_squared_per_pixel_initial <= 1e2 if np.isfinite(chi_squared_per_pixel_initial) else False,
        },
        "mask_metadata": {
            "telemetry": telemetry_mask_metadata,
            "reconstruction": reconstruction_mask_metadata,
            "checksum_match": mask_checksum_match,
        },
    }

    # Write JSON output
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"[Stage A Baseline Probe] Results written to {args.output}")

    # Print summary table to stdout
    print("\n" + "=" * 80)
    print("Stage A Baseline Telemetry vs Reconstruction Comparison")
    print("=" * 80)
    print(f"{'Metric':<50} {'Telemetry':<15} {'Reconstructed':<15}")
    print("-" * 80)
    print(f"{'target_mean_masked':<50} {target_mean_masked_telem:<15.6e} {target_mean_masked_reconstructed:<15.6e}")
    print(f"{'model_mean_masked':<50} {model_mean_masked_telem:<15.6e} {bragg_before_mean_masked:<15.6e}")
    print(f"{'log_scale_baseline_value':<50} {log_scale_baseline_value_telem:<15.6f} {'N/A':<15}")
    print(f"{'log_scale_delta_clamped':<50} {log_scale_delta_clamped_telem:<15.6f} {'N/A':<15}")
    print(f"{'log_scale_effective_initial':<50} {log_scale_effective_init:<15.6f} {'N/A':<15}")
    print(f"{'scale_factor':<50} {scale_factor_telem:<15.6e} {'N/A':<15}")
    print(f"{'chi²/pixel (initial)':<50} {'N/A':<15} {chi_squared_per_pixel_initial:<15.6e}")
    print("-" * 80)
    print(f"{'DB-AT-028 threshold (chi²/pixel ≤ 1e2)':<50} {'Threshold: 1e2':<30}")
    print(f"{'DB-AT-028 status':<50} {'PASS' if output['db_at_thresholds']['DB_AT_028_pass'] else 'FAIL':<30}")
    print("=" * 80)

    # Print divergence analysis
    print("\nDivergence Analysis:")
    print("-" * 80)
    if np.isfinite(output["comparison"]["target_mean_masked_delta"]):
        print(f"  target_mean_masked delta: {output['comparison']['target_mean_masked_delta']:.6e}")
    if np.isfinite(output["comparison"]["model_mean_masked_vs_reconstructed_delta"]):
        print(f"  model_mean_masked delta: {output['comparison']['model_mean_masked_vs_reconstructed_delta']:.6e}")
        if np.isfinite(output["comparison"]["model_mean_masked_vs_reconstructed_ratio"]):
            print(f"  model_mean_masked ratio: {output['comparison']['model_mean_masked_vs_reconstructed_ratio']:.6f}")
    print("=" * 80)

    # Print mask parity table (ARCH-SIM-CONSTRUCTION-001 C.10)
    print("\nMask Provenance Comparison:")
    print("-" * 80)
    if telemetry_mask_metadata and reconstruction_mask_metadata:
        telem_checksum = telemetry_mask_metadata.get('mask_checksum', 'N/A')
        telem_pixel_count = telemetry_mask_metadata.get('loss_mask_pixel_count', 'N/A')
        recon_checksum = reconstruction_mask_metadata.get('mask_checksum', 'N/A')
        recon_pixel_count = reconstruction_mask_metadata.get('loss_mask_pixel_count', 'N/A')

        print(f"  {'Source':<20} {'Pixel Count':<15} {'Checksum (SHA1)':<50}")
        print(f"  {'-'*20} {'-'*15} {'-'*50}")
        print(f"  {'Telemetry':<20} {telem_pixel_count:<15} {telem_checksum:<50}")
        print(f"  {'Reconstruction':<20} {recon_pixel_count:<15} {recon_checksum:<50}")
        print(f"  {'-'*20} {'-'*15} {'-'*50}")

        if mask_checksum_match is not None:
            status_str = "PASS" if mask_checksum_match else "FAIL"
            print(f"  Mask Checksum Match: {status_str}")
        else:
            print(f"  Mask Checksum Match: UNKNOWN (telemetry missing checksum)")
    else:
        print(f"  Mask metadata not available (telemetry or reconstruction missing)")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
