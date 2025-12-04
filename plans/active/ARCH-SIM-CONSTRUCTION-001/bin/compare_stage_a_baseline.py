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
    Replicates refgeom_dataload fixture logic with detector-size aware HKL resolution.

    Mirrors tests/conftest.py:177-309 logic for calibration + HKL path resolution:
    - Honours DBEX_SMOKE_CALIB_PATH and DBEX_SMOKE_HKL_PATH env overrides
    - Defaults to detector-size-specific calibration and refined MTZ when calibration metadata exists
    - Falls back to scaled.mtz with I(+),SIGI(+),I(-),SIGI(-) columns when no calibration present
    - Returns resolved mtz_file and mtz_col for telemetry capture
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

    # Resolve calibration path: detector-size aware defaults, with override taking precedence
    # (mirrors tests/conftest.py:210-226)
    calib_path_override = os.environ.get("DBEX_SMOKE_CALIB_PATH")
    calibration_config_path = None
    if calib_path_override:
        if not Path(calib_path_override).is_absolute():
            calibration_config_path = str(repo_root / calib_path_override)
        else:
            calibration_config_path = str(Path(calib_path_override))
    elif detector_size == "small":
        # Small-detector default
        default_smoke_calib_small = repo_root / "sp.proc" / "calibration" / "config_torch_smoke_small.json"
        if default_smoke_calib_small.exists():
            calibration_config_path = str(default_smoke_calib_small)
    else:
        # Full-detector default
        default_smoke_calib = repo_root / "sp.proc" / "calibration" / "config_torch_smoke.json"
        if default_smoke_calib.exists():
            calibration_config_path = str(default_smoke_calib)

    # Resolve HKL path from env or default to detector-size-specific refined MTZ when calibration exists
    # (mirrors tests/conftest.py:228-251)
    hkl_path_override = os.environ.get("DBEX_SMOKE_HKL_PATH")
    if hkl_path_override:
        hkl_path = repo_root / hkl_path_override
        # Infer MTZ column type from filename or default to intensities
        mtz_col = "F(+),SIGF(+),F(-),SIGF(-)" if "refined" in str(hkl_path_override).lower() else "I(+),SIGI(+),I(-),SIGI(-)"
    elif calibration_config_path:
        # When calibration metadata is present, default to detector-size-specific refined MTZ
        if detector_size == "small":
            default_refined_mtz = repo_root / "sp.proc" / "calibration" / "smoke_refined_structure_factors_small.mtz"
        else:
            default_refined_mtz = repo_root / "sp.proc" / "calibration" / "smoke_refined_structure_factors.mtz"

        if default_refined_mtz.exists():
            hkl_path = default_refined_mtz
            mtz_col = "F(+),SIGF(+),F(-),SIGF(-)"  # Refined MTZ uses F columns
        else:
            # Fallback to raw scaled MTZ if refined MTZ is missing
            hkl_path = repo_root / "scaled.mtz"
            mtz_col = "I(+),SIGI(+),I(-),SIGI(-)"
    else:
        hkl_path = repo_root / "scaled.mtz"
        mtz_col = "I(+),SIGI(+),I(-),SIGI(-)"  # Raw MTZ uses I columns

    args = Namespace(
        exptName=str(expt_path),
        reflName=str(refl_path),
        exptIdx=0,
        maskFile=str(mask_path),
        mtzFile=str(hkl_path),
        mtzCol=mtz_col,
        calibration_config_path=calibration_config_path,
    )

    # Store resolved paths for telemetry metadata
    args.resolved_mtz_file = str(hkl_path)
    args.resolved_mtz_col = mtz_col

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
    parser.add_argument(
        "--geometry-mode",
        type=str,
        choices=["perturbed", "baseline"],
        default="perturbed",
        help="Geometry mode: 'perturbed' applies smoke perturbations (default), 'baseline' uses mapping geometry without perturbation",
    )
    args = parser.parse_args()

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Stage A Baseline Probe] Starting probe (device={args.device})")
    print(f"[Stage A Baseline Probe] Geometry mode: {args.geometry_mode}")
    print(f"[Stage A Baseline Probe] Output will be saved to: {args.output}")

    # Build fixture data (replicating stage_a_smoke_result fixture logic)
    device_obj = torch.device(args.device)
    device = str(device_obj)

    # Get data dependencies (same as fixture)
    refgeom_dataload = get_refgeom_dataload()
    smoke_sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "metadata")

    # Extract resolved HKL/calibration paths from the dataload args for telemetry
    resolved_mtz_file = getattr(refgeom_dataload.args, 'resolved_mtz_file', 'unknown')
    resolved_mtz_col = getattr(refgeom_dataload.args, 'resolved_mtz_col', 'unknown')
    resolved_calibration_config_path = refgeom_dataload.args.calibration_config_path

    # Print console summary of chosen HKL/calibration paths
    print(f"[Stage A Baseline Probe] HKL source: {resolved_mtz_file}")
    print(f"[Stage A Baseline Probe] MTZ columns: {resolved_mtz_col}")
    print(f"[Stage A Baseline Probe] Calibration config: {resolved_calibration_config_path if resolved_calibration_config_path else 'None'}")

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

    # Select geometry based on mode
    if args.geometry_mode == "baseline":
        # Use unperturbed baseline geometry for Stage A
        refinement_crystal = baseline_crystal
        refinement_detector = baseline_detector
        refinement_beam = baseline_beam
    else:
        # Apply perturbations for Stage A smoke testing
        refinement_crystal, refinement_detector, refinement_beam = create_perturbed_geometry(
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
        detector=refinement_detector,
        beam=refinement_beam,
        crystal=refinement_crystal,
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
        detector=refinement_detector,
        beam=refinement_beam,
        crystal=refinement_crystal,
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

    # ARCH-SIM-CONSTRUCTION-001 Phase C.11: Compute Stage A vs mapping parity metrics (DB-AT-027)
    # mapping_context.bragg_zero_iter is the mapping forward model output
    # bragg_before is the Stage A zero-iteration reconstruction
    # These should match within numerical noise per DB-AT-027 (§265-285)
    mapping_bragg = mapping_context.bragg_zero_iter

    # Compute per-ROI Pearson correlations for Stage A vs mapping vs target
    def _compute_pearson_cc(arr1, arr2, mask):
        """Compute Pearson correlation between arr1 and arr2 over masked pixels."""
        mask_flat = mask.astype(bool).flatten()
        if not np.any(mask_flat):
            return float("nan")
        a1 = arr1.flatten()[mask_flat].astype(np.float64)
        a2 = arr2.flatten()[mask_flat].astype(np.float64)
        a1_centered = a1 - a1.mean()
        a2_centered = a2 - a2.mean()
        denom = np.linalg.norm(a1_centered) * np.linalg.norm(a2_centered)
        if denom <= 0:
            return float("nan")
        return float(np.dot(a1_centered, a2_centered) / denom)

    mapping_vs_target_roi_cc = []
    stagea_vs_target_roi_cc = []
    stagea_vs_mapping_roi_cc = []

    for pid, bbox in refinement_inputs.panel_slices:
        x0, x1, y0, y1 = bbox
        roi_mask = loss_mask_np[int(pid), y0:y1, x0:x1]
        if not np.any(roi_mask):
            continue

        target_roi = target_np[int(pid), y0:y1, x0:x1]
        mapping_roi = mapping_bragg[int(pid), y0:y1, x0:x1]
        stagea_roi = bragg_before[int(pid), y0:y1, x0:x1]

        mapping_vs_target_roi_cc.append(_compute_pearson_cc(mapping_roi, target_roi, roi_mask))
        stagea_vs_target_roi_cc.append(_compute_pearson_cc(stagea_roi, target_roi, roi_mask))
        stagea_vs_mapping_roi_cc.append(_compute_pearson_cc(stagea_roi, mapping_roi, roi_mask))

    # Filter out NaN values for percentile computation
    valid_mapping_vs_target = [c for c in mapping_vs_target_roi_cc if np.isfinite(c)]
    valid_stagea_vs_target = [c for c in stagea_vs_target_roi_cc if np.isfinite(c)]
    valid_stagea_vs_mapping = [c for c in stagea_vs_mapping_roi_cc if np.isfinite(c)]

    # Compute percentiles for ROI correlations
    import statistics
    roi_cc_stats = {
        "mapping_vs_target": {
            "median": float(statistics.median(valid_mapping_vs_target)) if valid_mapping_vs_target else float("nan"),
            "p25": float(np.percentile(valid_mapping_vs_target, 25)) if valid_mapping_vs_target else float("nan"),
            "p75": float(np.percentile(valid_mapping_vs_target, 75)) if valid_mapping_vs_target else float("nan"),
            "min": float(min(valid_mapping_vs_target)) if valid_mapping_vs_target else float("nan"),
            "max": float(max(valid_mapping_vs_target)) if valid_mapping_vs_target else float("nan"),
        },
        "stagea_vs_target": {
            "median": float(statistics.median(valid_stagea_vs_target)) if valid_stagea_vs_target else float("nan"),
            "p25": float(np.percentile(valid_stagea_vs_target, 25)) if valid_stagea_vs_target else float("nan"),
            "p75": float(np.percentile(valid_stagea_vs_target, 75)) if valid_stagea_vs_target else float("nan"),
            "min": float(min(valid_stagea_vs_target)) if valid_stagea_vs_target else float("nan"),
            "max": float(max(valid_stagea_vs_target)) if valid_stagea_vs_target else float("nan"),
        },
        "stagea_vs_mapping": {
            "median": float(statistics.median(valid_stagea_vs_mapping)) if valid_stagea_vs_mapping else float("nan"),
            "p25": float(np.percentile(valid_stagea_vs_mapping, 25)) if valid_stagea_vs_mapping else float("nan"),
            "p75": float(np.percentile(valid_stagea_vs_mapping, 75)) if valid_stagea_vs_mapping else float("nan"),
            "min": float(min(valid_stagea_vs_mapping)) if valid_stagea_vs_mapping else float("nan"),
            "max": float(max(valid_stagea_vs_mapping)) if valid_stagea_vs_mapping else float("nan"),
        },
    }

    # Compute global masked/unmasked means for mapping vs Stage A
    mapping_masked = mapping_bragg[loss_mask_np]
    mapping_mean_masked = float(np.mean(mapping_masked)) if mapping_masked.size > 0 else float("nan")
    mapping_mean_unmasked = float(np.mean(mapping_bragg))

    # Compute max|Δ| and RMSE between Stage A and mapping
    stagea_vs_mapping_diff = bragg_before - mapping_bragg
    stagea_vs_mapping_diff_masked = stagea_vs_mapping_diff[loss_mask_np]

    max_abs_diff_masked = float(np.max(np.abs(stagea_vs_mapping_diff_masked))) if stagea_vs_mapping_diff_masked.size > 0 else float("nan")
    max_abs_diff_unmasked = float(np.max(np.abs(stagea_vs_mapping_diff)))
    rmse_masked = float(np.sqrt(np.mean(stagea_vs_mapping_diff_masked ** 2))) if stagea_vs_mapping_diff_masked.size > 0 else float("nan")
    rmse_unmasked = float(np.sqrt(np.mean(stagea_vs_mapping_diff ** 2)))

    # Compute chi²/pixel for mapping vs target (DB-AT-027 requirement)
    residual_mapping_masked = target_masked - mapping_masked
    variance_mapping_masked = np.maximum(mapping_masked, variance_floor_value)
    chi_squared_mapping = float(np.sum(residual_mapping_masked ** 2 / variance_mapping_masked))
    chi_squared_per_pixel_mapping = chi_squared_mapping / n_masked_pixels if n_masked_pixels > 0 else float("nan")

    # Check DB-AT-027 parity warnings (only normative when geometry_mode is baseline)
    # Per spec §280: max_abs_diff should be O(1) ADU for float precision, not O(1e2)
    # Per spec §279-281: ROI CC should be > 0.99 for zero-point equivalence
    # When geometry_mode is perturbed, emit comparison data but tag as non-normative
    mapping_parity_warnings = []
    if args.geometry_mode == "baseline":
        # Normative parity checks: expected differences should be minimal
        if np.isfinite(roi_cc_stats["stagea_vs_mapping"]["median"]) and roi_cc_stats["stagea_vs_mapping"]["median"] < 0.99:
            mapping_parity_warnings.append(f"Stage A vs mapping median ROI CC ({roi_cc_stats['stagea_vs_mapping']['median']:.4f}) < 0.99 (DB-AT-027 zero-point equivalence)")
        if np.isfinite(max_abs_diff_masked) and max_abs_diff_masked > 1.0:
            mapping_parity_warnings.append(f"Stage A vs mapping max|Δ| ({max_abs_diff_masked:.3e} ADU) > 1.0 ADU (DB-AT-027 forward-model equality)")
        if np.isfinite(chi_squared_per_pixel_mapping) and np.isfinite(chi_squared_per_pixel_initial):
            chi2_ratio = abs(chi_squared_per_pixel_initial - chi_squared_per_pixel_mapping) / chi_squared_per_pixel_mapping if chi_squared_per_pixel_mapping > 0 else float("inf")
            if chi2_ratio > 1e-3:
                mapping_parity_warnings.append(f"Stage A vs mapping chi²/pixel relative diff ({chi2_ratio:.3e}) > 1e-3 (DB-AT-027 variance-weighted loss equality)")
    else:
        # Perturbed mode: differences are expected and non-normative
        mapping_parity_warnings.append(f"[NON-NORMATIVE] Geometry mode is '{args.geometry_mode}' — Stage A vs mapping differences are expected due to deliberate perturbation")

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

    # Extract mapping diagnostic fields (ARCH-SIM-CONSTRUCTION-001 masked-mean scaling)
    mapping_diagnostics = mapping_context.diagnostics if mapping_context.diagnostics else {}
    mapping_target_mean_masked = mapping_diagnostics.get("target_mean_masked")
    mapping_bragg_mean_masked = mapping_diagnostics.get("bragg_mean_masked")
    mapping_masked_mean_ratio = mapping_diagnostics.get("masked_mean_ratio")
    mapping_log_scale_baseline_source = mapping_diagnostics.get("log_scale_baseline_source")
    mapping_scale_adjustment_skipped = mapping_diagnostics.get("mapping_scale_adjustment_skipped", False)
    mapping_scale_skip_reason = mapping_diagnostics.get("mapping_scale_skip_reason")

    # Build output payload
    output = {
        "probe_metadata": {
            "timestamp": "2025-12-15T010000Z",
            "initiative": "ARCH-SIM-CONSTRUCTION-001",
            "phase": "C.11",
            "purpose": "Capture Stage A telemetry vs reconstructed bragg_before baselines with mapping parity metrics (DB-AT-027)",
            "geometry_mode": args.geometry_mode,
            "device": device,
            "apply_calibration_n_cells": apply_n_cells,
            "spot_scale_override": spot_scale_override_val,
            "warm_cache_available": stage_a_artifacts is not None,
            "stage_a_ctx_used": stage_a_ctx_cached is not None,
            "bragg_full_cached_available": bragg_full_cached is not None,
            "mtz_file": resolved_mtz_file,
            "mtz_col": resolved_mtz_col,
            "calibration_config_path": resolved_calibration_config_path if resolved_calibration_config_path else None,
        },
        "mapping_diagnostics": {
            "target_mean_masked": mapping_target_mean_masked,
            "bragg_mean_masked": mapping_bragg_mean_masked,
            "masked_mean_ratio": mapping_masked_mean_ratio,
            "log_scale_baseline_source": mapping_log_scale_baseline_source,
            "scale_adjustment_skipped": mapping_scale_adjustment_skipped,
            "scale_skip_reason": mapping_scale_skip_reason,
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
        "mapping_comparison": {
            "mapping_mean_masked": mapping_mean_masked,
            "mapping_mean_unmasked": mapping_mean_unmasked,
            "stagea_vs_mapping_max_abs_diff_masked": max_abs_diff_masked,
            "stagea_vs_mapping_max_abs_diff_unmasked": max_abs_diff_unmasked,
            "stagea_vs_mapping_rmse_masked": rmse_masked,
            "stagea_vs_mapping_rmse_unmasked": rmse_unmasked,
            "chi_squared_per_pixel_mapping": chi_squared_per_pixel_mapping,
            "chi_squared_per_pixel_stagea": chi_squared_per_pixel_initial,
            "chi_squared_per_pixel_relative_diff": chi2_ratio if np.isfinite(chi_squared_per_pixel_mapping) and np.isfinite(chi_squared_per_pixel_initial) else float("nan"),
            "roi_cc_stats": roi_cc_stats,
            "n_rois_analyzed": len(valid_stagea_vs_mapping),
            "warnings": mapping_parity_warnings,
        },
        "db_at_thresholds": {
            "DB_AT_027_stagea_vs_mapping_median_roi_cc_threshold": 0.99,
            "DB_AT_027_stagea_vs_mapping_median_roi_cc_actual": roi_cc_stats["stagea_vs_mapping"]["median"],
            "DB_AT_027_stagea_vs_mapping_max_abs_diff_threshold_adu": 1.0,
            "DB_AT_027_stagea_vs_mapping_max_abs_diff_actual_adu": max_abs_diff_masked,
            "DB_AT_027_chi2_relative_diff_threshold": 1e-3,
            "DB_AT_027_chi2_relative_diff_actual": chi2_ratio if np.isfinite(chi_squared_per_pixel_mapping) and np.isfinite(chi_squared_per_pixel_initial) else float("nan"),
            "DB_AT_027_pass": (args.geometry_mode == "baseline" and len(mapping_parity_warnings) == 0) or (args.geometry_mode == "perturbed"),
            "DB_AT_027_normative": args.geometry_mode == "baseline",
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

    # Print mapping diagnostics (ARCH-SIM-CONSTRUCTION-001 masked-mean scaling)
    print("\nMapping Baseline Diagnostics (ARCH-SIM-CONSTRUCTION-001):")
    print("=" * 80)
    if not mapping_scale_adjustment_skipped:
        print(f"{'Mapping masked-mean scaling applied':<50} {'YES':<30}")
        if mapping_target_mean_masked is not None:
            print(f"  {'Target mean (masked)':<48} {mapping_target_mean_masked:<30.6e}")
        if mapping_bragg_mean_masked is not None:
            print(f"  {'Bragg mean before scaling (masked)':<48} {mapping_bragg_mean_masked:<30.6e}")
        if mapping_masked_mean_ratio is not None:
            print(f"  {'Masked mean ratio (target/bragg)':<48} {mapping_masked_mean_ratio:<30.6e}")
        if mapping_log_scale_baseline_source:
            print(f"  {'Log-scale baseline source':<48} {mapping_log_scale_baseline_source:<30}")
    else:
        print(f"{'Mapping masked-mean scaling skipped':<50} {'YES':<30}")
        if mapping_scale_skip_reason:
            print(f"  {'Reason':<48} {mapping_scale_skip_reason:<30}")
    print("=" * 80)

    # Print mapping parity comparison (ARCH-SIM-CONSTRUCTION-001 C.11, DB-AT-027)
    print("\nMapping Parity Comparison (DB-AT-027):")
    print("=" * 80)
    print(f"{'Metric':<50} {'Mapping':<15} {'Stage A':<15} {'Status':<10}")
    print("-" * 80)
    print(f"{'Mean (masked) [ADU]':<50} {mapping_mean_masked:<15.6e} {bragg_before_mean_masked:<15.6e} {'':<10}")
    print(f"{'Mean (unmasked) [ADU]':<50} {mapping_mean_unmasked:<15.6e} {bragg_before_mean_unmasked:<15.6e} {'':<10}")
    print(f"{'Chi²/pixel vs target':<50} {chi_squared_per_pixel_mapping:<15.6e} {chi_squared_per_pixel_initial:<15.6e} {'':<10}")
    print("-" * 80)
    print(f"{'Max|Δ| (masked) [ADU]':<50} {'':<15} {max_abs_diff_masked:<15.6e} {'PASS' if max_abs_diff_masked <= 1.0 else 'FAIL':<10}")
    print(f"{'RMSE (masked) [ADU]':<50} {'':<15} {rmse_masked:<15.6e} {'':<10}")
    print(f"{'Chi²/pixel relative diff':<50} {'':<15} {chi2_ratio if np.isfinite(chi2_ratio) else float('nan'):<15.6e} {'PASS' if np.isfinite(chi2_ratio) and chi2_ratio <= 1e-3 else 'FAIL':<10}")
    print("-" * 80)
    print(f"{'ROI Correlations (n={len(valid_stagea_vs_mapping)})':<50} {'':<15} {'':<15} {'':<10}")
    print(f"  {'Mapping vs Target (median)':<48} {roi_cc_stats['mapping_vs_target']['median']:<15.4f} {'':<15} {'':<10}")
    print(f"  {'Stage A vs Target (median)':<48} {roi_cc_stats['stagea_vs_target']['median']:<15.4f} {'':<15} {'':<10}")
    print(f"  {'Stage A vs Mapping (median)':<48} {roi_cc_stats['stagea_vs_mapping']['median']:<15.4f} {'':<15} {'PASS' if roi_cc_stats['stagea_vs_mapping']['median'] >= 0.99 else 'FAIL':<10}")
    print(f"  {'Stage A vs Mapping (min/max)':<48} {roi_cc_stats['stagea_vs_mapping']['min']:<7.4f} / {roi_cc_stats['stagea_vs_mapping']['max']:<7.4f} {'':<15} {'':<10}")
    print("-" * 80)
    db_at_027_status = "PASS" if len(mapping_parity_warnings) == 0 else "FAIL"
    print(f"{'DB-AT-027 overall status':<50} {'':<15} {'':<15} {db_at_027_status:<10}")
    print("=" * 80)

    # Print warnings if any
    if mapping_parity_warnings:
        print("\nDB-AT-027 Parity Warnings:")
        print("-" * 80)
        for warning in mapping_parity_warnings:
            print(f"  - {warning}")
        print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
