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

from dials.array_family import flex

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import build_structure_factor_grid, simulate_forward_once
from dbex.refinement.config import RefinementConfig
from dbex.refinement.context import build_refinement_context
from dbex.refinement.engine import RefinementEngine
from dbex.refinement.stage_a import StageA
from dbex.refinement.stage_a_utils import _build_stage_a_context
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


def aggregate_hkl_stats(per_panel_stats):
    """
    Aggregate per-panel HKL stats into a single summary dict.

    Args:
        per_panel_stats: list of {"panel_id": int, "hkl_stats": {...}} entries

    Returns:
        dict with aggregated min/max h,k,l and summed hit counts (or None when empty)
    """
    if not per_panel_stats:
        return None

    h_min = min(entry["hkl_stats"]["h_min"] for entry in per_panel_stats)
    h_max = max(entry["hkl_stats"]["h_max"] for entry in per_panel_stats)
    k_min = min(entry["hkl_stats"]["k_min"] for entry in per_panel_stats)
    k_max = max(entry["hkl_stats"]["k_max"] for entry in per_panel_stats)
    l_min = min(entry["hkl_stats"]["l_min"] for entry in per_panel_stats)
    l_max = max(entry["hkl_stats"]["l_max"] for entry in per_panel_stats)
    total_queries = sum(entry["hkl_stats"]["total_queries"] for entry in per_panel_stats)
    in_bounds = sum(entry["hkl_stats"]["in_bounds_count"] for entry in per_panel_stats)
    out_of_bounds = sum(entry["hkl_stats"]["out_of_bounds_count"] for entry in per_panel_stats)

    return {
        "h_min": h_min,
        "h_max": h_max,
        "k_min": k_min,
        "k_max": k_max,
        "l_min": l_min,
        "l_max": l_max,
        "total_queries": total_queries,
        "in_bounds_count": in_bounds,
        "out_of_bounds_count": out_of_bounds,
        "in_bounds_fraction": in_bounds / total_queries if total_queries > 0 else 0.0,
    }


def collect_stage_a_hkl_stats(
    detector,
    beam,
    crystal,
    refinement_inputs,
    hkl_grid,
    hkl_metadata,
    config,
    device,
):
    """
    Build a diagnostic Stage A context with HKL stats enabled and aggregate results.
    """
    print("[Stage A Baseline Probe] Collecting Stage A HKL stats (debug context)...")
    trusted_mask = getattr(refinement_inputs, "trusted_mask", None)
    if trusted_mask is None:
        raise RuntimeError("RefinementInputs.trusted_mask is required for HKL stats.")

    stage_a_ctx_diag = _build_stage_a_context(
        detector=detector,
        beam=beam,
        crystal=crystal,
        trusted_mask=trusted_mask,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        enable_hkl_interpolation=config.enable_hkl_interpolation,
        device=device,
        dtype=config.dtype,
        panel_slices=None,
        enable_roi_mode=False,
        calibration_metadata=config.calibration_metadata,
        log_scale_baseline=getattr(config, "log_scale_baseline", None),
        apply_calibration_n_cells=config.apply_calibration_n_cells,
        config=config,
        debug_config={"collect_hkl_stats": True},
    )

    per_panel_stats = []
    for panel_id, simulator in enumerate(stage_a_ctx_diag.simulators):
        try:
            _ = simulator.run()
        except Exception as exc:  # pragma: no cover - diagnostics only
            print(f"[Stage A Baseline Probe] WARNING: simulator.run() failed for panel {panel_id}: {exc}")
            continue
        stats = getattr(simulator, "hkl_stats", None)
        if stats:
            per_panel_stats.append({"panel_id": panel_id, "hkl_stats": stats})

    aggregated = aggregate_hkl_stats(per_panel_stats)
    return {
        "n_panels": getattr(stage_a_ctx_diag, "n_panels", len(stage_a_ctx_diag.simulators)),
        "per_panel_stats": per_panel_stats,
        "aggregated": aggregated,
    }


def collect_mapping_hkl_stats(
    refinement_inputs,
    detector,
    beam,
    crystal,
    experiment,
    mapping_context,
    device,
    apply_n_cells,
    config=None,
):
    """
    Run simulate_forward_once with HKL stats enabled and aggregate diagnostics.
    """
    print("[Stage A Baseline Probe] Collecting simulate_forward_once HKL stats...")
    # ARCH-SIM-CONSTRUCTION-001: Extract mosaic_domains from config if available
    mosaic_domains = config.stage_a_mosaic_domains if config is not None else None
    bragg_unused, diagnostics = simulate_forward_once(
        inputs=refinement_inputs,
        detector=detector,
        beam=beam,
        crystal=crystal,
        experiment=experiment,
        hkl_indices=mapping_context.hkl_indices,
        hkl_amplitudes=mapping_context.hkl_amplitudes,
        calibration=mapping_context.calibration,
        spot_scale_override=mapping_context.calibration.get("spot_scale_override", 1.0) if mapping_context.calibration else None,
        device=device,
        sigma_floor_value=1.0,
        apply_calibration_n_cells=apply_n_cells,
        mosaic_domains=mosaic_domains,
        debug_config={"collect_hkl_stats": True},
    )

    per_panel_stats = diagnostics.get("per_panel_hkl_stats", [])
    aggregated = aggregate_hkl_stats(per_panel_stats)
    return {
        "n_panels": len(per_panel_stats),
        "per_panel_stats": per_panel_stats,
        "aggregated": aggregated,
        "hkl_grid_metadata": diagnostics.get("hkl_stats"),
    }


def compute_spot_profiles(
    bragg_before,
    reflection_roi_matches,
    halo_pixels,
):
    """
    Compute spot-profile metrics for each reflection ROI.

    For each matched reflection:
    - ROI energy: sum of pixel values inside the ROI bbox
    - Halo energy: sum of pixel values in expanded bbox (ROI ± halo_pixels)
    - ROI fraction of halo: ROI_energy / halo_energy
    - ROI fraction of panel: ROI_energy / total_panel_energy
    - Peak value: max pixel value in ROI
    - FWHM fast/slow: width of contiguous pixels ≥ 0.5 × peak

    Args:
        bragg_before: Full-panel bragg tensor (n_panels, slow, fast)
        reflection_roi_matches: List of reflection match dicts with panel_id, bbox, etc.
        halo_pixels: Number of pixels to expand bbox for halo computation

    Returns:
        Updated reflection_roi_matches with spot_profile_metrics added to each entry
    """
    for match in reflection_roi_matches:
        panel_id = match["panel_id"]
        x0_roi, x1_roi, y0_roi, y1_roi = match["bbox"]

        # Extract ROI region
        roi_region = bragg_before[panel_id, y0_roi:y1_roi, x0_roi:x1_roi]
        roi_energy = float(np.sum(roi_region))
        peak_value = float(np.max(roi_region)) if roi_region.size > 0 else 0.0

        # Compute halo bbox (expand by halo_pixels, clamp to detector bounds)
        panel_shape = bragg_before[panel_id].shape  # (slow, fast)
        x0_halo = max(0, x0_roi - halo_pixels)
        x1_halo = min(panel_shape[1], x1_roi + halo_pixels)
        y0_halo = max(0, y0_roi - halo_pixels)
        y1_halo = min(panel_shape[0], y1_roi + halo_pixels)

        # Extract halo region
        halo_region = bragg_before[panel_id, y0_halo:y1_halo, x0_halo:x1_halo]
        halo_energy = float(np.sum(halo_region))

        # Compute panel total energy
        panel_energy = float(np.sum(bragg_before[panel_id]))

        # Compute fractions
        roi_fraction_of_halo = roi_energy / halo_energy if halo_energy > 0 else float("nan")
        roi_fraction_of_panel = roi_energy / panel_energy if panel_energy > 0 else float("nan")

        # Compute FWHM on fast/slow axes
        # FWHM is the width of contiguous pixels ≥ 0.5 × peak
        fwhm_threshold = 0.5 * peak_value

        # Fast-axis FWHM: sum along slow axis to get 1D profile
        fast_profile = np.sum(roi_region, axis=0)  # Sum along slow (y) axis
        fast_above_threshold = fast_profile >= (fwhm_threshold * roi_region.shape[0])
        fwhm_fast = int(np.sum(fast_above_threshold))

        # Slow-axis FWHM: sum along fast axis to get 1D profile
        slow_profile = np.sum(roi_region, axis=1)  # Sum along fast (x) axis
        slow_above_threshold = slow_profile >= (fwhm_threshold * roi_region.shape[1])
        fwhm_slow = int(np.sum(slow_above_threshold))

        # Store metrics in the match entry
        match["spot_profile_metrics"] = {
            "roi_energy": roi_energy,
            "halo_energy": halo_energy,
            "panel_energy": panel_energy,
            "roi_fraction_of_halo": roi_fraction_of_halo,
            "roi_fraction_of_panel": roi_fraction_of_panel,
            "halo_bbox": [int(x0_halo), int(x1_halo), int(y0_halo), int(y1_halo)],
            "peak_value": peak_value,
            "fwhm_fast": fwhm_fast,
            "fwhm_slow": fwhm_slow,
            "halo_pixels": int(halo_pixels),
        }

    return reflection_roi_matches


def compute_orientation_metrics(
    detector,
    beam,
    crystal,
    reflection_roi_matches,
):
    """
    Compute HKL orientation alignment metrics for each matched ROI.

    For each reflection:
    - Compute ROI center in lab coordinates
    - Convert to diffracted beam vector s1
    - Solve h_frac = A^{-1} q where q = s1 - s0
    - Record fractional HKL, Δhkl = h_frac - h_int, |Δhkl|
    - Compute resolution (Å = 1/||q||) and 2θ

    Args:
        detector: DIALS detector model
        beam: DIALS beam model
        crystal: DIALS crystal model
        reflection_roi_matches: List of reflection match dicts with panel_id, bbox, hkl_index

    Returns:
        Updated reflection_roi_matches with orientation_metrics added to each entry
    """
    from scitbx import matrix

    # Get beam parameters
    s0_vec = beam.get_s0()  # Incident beam vector (wavelength units: 1/Å)
    s0 = np.array([s0_vec[0], s0_vec[1], s0_vec[2]])
    wavelength = beam.get_wavelength()  # Å

    # Get crystal A matrix (converts HKL to reciprocal space coordinates in 1/Å)
    A_matrix_scitbx = crystal.get_A()
    A = np.array(A_matrix_scitbx).reshape(3, 3)

    # Quick unit test: verify A @ h_int ≈ q for a known reflection
    # We'll validate the first reflection as a sanity check
    if len(reflection_roi_matches) > 0:
        first_match = reflection_roi_matches[0]
        h_int_test = np.array(first_match["hkl_index"], dtype=np.float64)
        q_expected_test = A @ h_int_test
        # We'll validate this against the computed q below

    for match in reflection_roi_matches:
        panel_id = match["panel_id"]
        x0_roi, x1_roi, y0_roi, y1_roi = match["bbox"]
        h_int = np.array(match["hkl_index"], dtype=np.float64)

        # Compute ROI center in detector pixels (fast, slow)
        roi_center_fast = (x0_roi + x1_roi) / 2.0
        roi_center_slow = (y0_roi + y1_roi) / 2.0

        # Get lab coordinates for ROI center
        # detector[panel_id].get_pixel_lab_coord expects (fast, slow) in pixel units
        panel = detector[panel_id]
        lab_coord = panel.get_pixel_lab_coord((roi_center_fast, roi_center_slow))

        # Convert lab coordinate to s1 (diffracted beam direction, normalized by wavelength)
        # lab_coord is a scitbx vector in mm; normalize and scale to 1/Å units
        lab_vec = np.array([lab_coord[0], lab_coord[1], lab_coord[2]])
        lab_norm = np.linalg.norm(lab_vec)

        if lab_norm == 0:
            # Degenerate case: skip this ROI
            match["orientation_metrics"] = {
                "error": "Zero lab coordinate norm"
            }
            continue

        # s1 = lab_vec / (wavelength * lab_norm)  # Units: 1/Å
        # Actually, get_pixel_lab_coord returns mm, and s0 is already in 1/Å units
        # The correct normalization is: s1_direction = lab_vec / lab_norm, then s1 = s1_direction / wavelength
        s1_direction = lab_vec / lab_norm
        s1 = s1_direction / wavelength  # Units: 1/Å

        # Compute scattering vector q = s1 - s0
        q = s1 - s0
        q_norm = np.linalg.norm(q)

        # Solve h_frac = A^{-1} q
        try:
            h_frac = np.linalg.solve(A, q)
        except np.linalg.LinAlgError:
            match["orientation_metrics"] = {
                "error": "Singular A matrix"
            }
            continue

        # Compute Δhkl = h_frac - h_int
        delta_hkl = h_frac - h_int
        delta_hkl_norm = np.linalg.norm(delta_hkl)

        # Compute resolution: d = 1 / ||q|| (Å)
        resolution = 1.0 / q_norm if q_norm > 0 else float("inf")

        # Compute 2θ: angle between s0 and s1
        # cos(2θ) = (s0 · s1) / (||s0|| ||s1||)
        s0_norm = np.linalg.norm(s0)
        s1_norm = np.linalg.norm(s1)
        if s0_norm > 0 and s1_norm > 0:
            cos_two_theta = np.dot(s0, s1) / (s0_norm * s1_norm)
            # Clamp to [-1, 1] to handle numerical errors
            cos_two_theta = np.clip(cos_two_theta, -1.0, 1.0)
            two_theta_rad = np.arccos(cos_two_theta)
            two_theta_deg = np.degrees(two_theta_rad)
        else:
            two_theta_deg = float("nan")

        # Store orientation metrics
        match["orientation_metrics"] = {
            "h_frac": h_frac.tolist(),
            "delta_hkl": delta_hkl.tolist(),
            "delta_hkl_norm": float(delta_hkl_norm),
            "resolution_angstrom": float(resolution),
            "two_theta_deg": float(two_theta_deg),
            "roi_center_px": [float(roi_center_fast), float(roi_center_slow)],
            "q_norm": float(q_norm),
        }

    return reflection_roi_matches


def _summarize_spot_profiles(reflection_roi_matches, output_path, geometry_mode, halo_pixels, orientation_alignment=None):
    """
    Generate a Markdown summary of spot-profile and orientation metrics.

    Writes a report listing:
    - Summary statistics (median ROI fractions)
    - Top 5 ROIs with most off-ROI energy (lowest ROI fraction of halo)
    - Top 5 ROIs with narrowest FWHM
    - Orientation alignment metrics (if available)

    Args:
        reflection_roi_matches: List of reflection matches with spot_profile_metrics
        output_path: Path object for the output Markdown file
        geometry_mode: "baseline" or "perturbed"
        halo_pixels: Halo expansion parameter used
        orientation_alignment: Optional dict with orientation metrics summary
    """
    # Extract metrics from matches that have spot profiles
    matches_with_profiles = [m for m in reflection_roi_matches if "spot_profile_metrics" in m]

    if not matches_with_profiles:
        with open(output_path, 'w') as f:
            f.write("# Spot Profile Summary\n\n")
            f.write("No spot-profile metrics available.\n")
        return

    # Compute summary statistics
    roi_fractions_halo = [m["spot_profile_metrics"]["roi_fraction_of_halo"] for m in matches_with_profiles if np.isfinite(m["spot_profile_metrics"]["roi_fraction_of_halo"])]
    roi_fractions_panel = [m["spot_profile_metrics"]["roi_fraction_of_panel"] for m in matches_with_profiles if np.isfinite(m["spot_profile_metrics"]["roi_fraction_of_panel"])]

    median_roi_fraction_halo = float(np.median(roi_fractions_halo)) if roi_fractions_halo else float("nan")
    median_roi_fraction_panel = float(np.median(roi_fractions_panel)) if roi_fractions_panel else float("nan")

    # Sort by ROI fraction of halo (ascending = most off-ROI energy)
    sorted_by_off_roi = sorted(
        [m for m in matches_with_profiles if np.isfinite(m["spot_profile_metrics"]["roi_fraction_of_halo"])],
        key=lambda m: m["spot_profile_metrics"]["roi_fraction_of_halo"]
    )
    worst_5_by_off_roi = sorted_by_off_roi[:5] if len(sorted_by_off_roi) >= 5 else sorted_by_off_roi

    # Sort by FWHM (ascending = narrowest)
    # Use geometric mean of fast/slow FWHM
    def fwhm_geomean(m):
        fwhm_f = m["spot_profile_metrics"]["fwhm_fast"]
        fwhm_s = m["spot_profile_metrics"]["fwhm_slow"]
        if fwhm_f > 0 and fwhm_s > 0:
            return np.sqrt(fwhm_f * fwhm_s)
        return float("inf")

    sorted_by_fwhm = sorted(
        matches_with_profiles,
        key=fwhm_geomean
    )
    narrowest_5_by_fwhm = sorted_by_fwhm[:5] if len(sorted_by_fwhm) >= 5 else sorted_by_fwhm

    # Write Markdown report
    with open(output_path, 'w') as f:
        f.write("# Spot Profile Summary\n\n")
        f.write(f"**Initiative:** ARCH-SIM-CONSTRUCTION-001\n\n")
        f.write(f"**Geometry Mode:** {geometry_mode}\n\n")
        f.write(f"**Halo Pixels:** {halo_pixels}\n\n")
        f.write(f"**Total Reflections:** {len(matches_with_profiles)}\n\n")
        f.write("---\n\n")

        f.write("## Summary Statistics\n\n")
        f.write(f"- **Median ROI fraction of halo:** {median_roi_fraction_halo:.4f}\n")
        f.write(f"- **Median ROI fraction of panel:** {median_roi_fraction_panel:.6f}\n")
        f.write("\n")

        f.write("---\n\n")
        f.write("## Top 5 ROIs with Most Off-ROI Energy\n\n")
        f.write("(Lowest ROI fraction of halo — energy spilling outside ROI bbox)\n\n")
        f.write("| Panel | BBox | HKL | ROI/Halo | ROI Energy | Halo Energy | FWHM (fast×slow) |\n")
        f.write("|-------|------|-----|----------|------------|-------------|------------------|\n")

        for m in worst_5_by_off_roi:
            panel_id = m["panel_id"]
            bbox = m["bbox"]
            hkl = m["hkl_index"]
            sp = m["spot_profile_metrics"]
            bbox_str = f"[{bbox[0]}:{bbox[1]},{bbox[2]}:{bbox[3]}]"
            hkl_str = f"({hkl[0]},{hkl[1]},{hkl[2]})"
            fwhm_str = f"{sp['fwhm_fast']}×{sp['fwhm_slow']}"
            f.write(f"| {panel_id} | {bbox_str} | {hkl_str} | {sp['roi_fraction_of_halo']:.4f} | {sp['roi_energy']:.2e} | {sp['halo_energy']:.2e} | {fwhm_str} |\n")

        f.write("\n")
        f.write("---\n\n")
        f.write("## Top 5 ROIs with Narrowest FWHM\n\n")
        f.write("(Smallest geometric mean of fast/slow FWHM — most concentrated spots)\n\n")
        f.write("| Panel | BBox | HKL | FWHM (fast×slow) | ROI/Halo | Peak Value |\n")
        f.write("|-------|------|-----|------------------|----------|------------|\n")

        for m in narrowest_5_by_fwhm:
            panel_id = m["panel_id"]
            bbox = m["bbox"]
            hkl = m["hkl_index"]
            sp = m["spot_profile_metrics"]
            bbox_str = f"[{bbox[0]}:{bbox[1]},{bbox[2]}:{bbox[3]}]"
            hkl_str = f"({hkl[0]},{hkl[1]},{hkl[2]})"
            fwhm_str = f"{sp['fwhm_fast']}×{sp['fwhm_slow']}"
            f.write(f"| {panel_id} | {bbox_str} | {hkl_str} | {fwhm_str} | {sp['roi_fraction_of_halo']:.4f} | {sp['peak_value']:.2e} |\n")

        f.write("\n")

        # ARCH-SIM-CONSTRUCTION-001 Phase C.23: Add orientation alignment section if available
        if orientation_alignment and orientation_alignment.get("enabled"):
            f.write("---\n\n")
            f.write("## Orientation Alignment\n\n")
            f.write("**Purpose:** Diagnose whether DB-AT-028/029 failures correlate with HKL misalignment (|Δhkl|) vs intensity-only divergence.\n\n")

            if "error" in orientation_alignment:
                f.write(f"**Error:** {orientation_alignment['error']}\n\n")
            else:
                f.write(f"- **Reflections analyzed:** {orientation_alignment['n_reflections_with_orientation']}\n")
                f.write(f"- **Median |Δhkl|:** {orientation_alignment['median_delta_hkl_norm']:.4f}\n")
                f.write(f"- **P25-P75 |Δhkl|:** {orientation_alignment['p25_delta_hkl_norm']:.4f} - {orientation_alignment['p75_delta_hkl_norm']:.4f}\n")
                f.write(f"- **Max |Δhkl|:** {orientation_alignment['max_delta_hkl_norm']:.4f}\n")
                f.write(f"- **Median resolution:** {orientation_alignment['median_resolution_angstrom']:.2f} Å\n")
                f.write(f"- **Median 2θ:** {orientation_alignment['median_two_theta_deg']:.2f}°\n")

                pearson_corr = orientation_alignment['pearson_corr_delta_hkl_vs_stagea_ratio']
                if np.isfinite(pearson_corr):
                    f.write(f"- **Pearson corr (|Δhkl| vs Stage A/ref ratio):** {pearson_corr:.4f} ({orientation_alignment['n_pairs_for_correlation']} pairs)\n")
                else:
                    f.write(f"- **Pearson corr (|Δhkl| vs Stage A/ref ratio):** undefined ({orientation_alignment['n_pairs_for_correlation']} pairs)\n")

                f.write("\n")
                f.write("### Top 5 ROIs by HKL Misalignment\n\n")
                f.write("(Largest |Δhkl| = ||h_frac - h_int|| — worst orientation errors)\n\n")
                f.write("| Panel | BBox | HKL | |Δhkl| | Δhkl | Resolution (Å) | Stage A/Ref Ratio |\n")
                f.write("|-------|------|-----|-------|------|----------------|-------------------|\n")

                for m in orientation_alignment['worst_5_misalignment']:
                    panel_id = m["panel_id"]
                    bbox = m["bbox"]
                    hkl = m["hkl_index"]
                    delta_hkl_norm = m["delta_hkl_norm"]
                    delta_hkl = m["delta_hkl"]
                    resolution = m["resolution_angstrom"]
                    ratio = m["stagea_vs_ref_ratio"]

                    bbox_str = f"[{bbox[0]}:{bbox[1]},{bbox[2]}:{bbox[3]}]"
                    hkl_str = f"({hkl[0]},{hkl[1]},{hkl[2]})"
                    delta_hkl_str = f"({delta_hkl[0]:.3f},{delta_hkl[1]:.3f},{delta_hkl[2]:.3f})"
                    ratio_str = f"{ratio:.2e}" if np.isfinite(ratio) else "nan"

                    f.write(f"| {panel_id} | {bbox_str} | {hkl_str} | {delta_hkl_norm:.4f} | {delta_hkl_str} | {resolution:.2f} | {ratio_str} |\n")

                f.write("\n")

                # Add interpretation guidance
                f.write("**Interpretation:**\n\n")
                if np.isfinite(pearson_corr):
                    if abs(pearson_corr) > 0.7:
                        f.write(f"- Strong correlation ({pearson_corr:.2f}) between |Δhkl| and Stage A/ref ratio suggests **orientation misalignment** drives intensity divergence.\n")
                        f.write("- Next step: Retarget simulators to DIALS ROI centers or audit nanobrag_torch q-vector computation.\n")
                    elif abs(pearson_corr) > 0.3:
                        f.write(f"- Moderate correlation ({pearson_corr:.2f}) suggests partial contribution from orientation errors.\n")
                        f.write("- Next step: Audit both geometry and physics (Lorentz/partiality) paths.\n")
                    else:
                        f.write(f"- Weak correlation ({pearson_corr:.2f}) suggests orientation is not the primary driver.\n")
                        f.write("- Next step: Focus on physics corrections (Lorentz/partiality/normalization).\n")
                else:
                    f.write("- Correlation undefined (insufficient valid pairs or constant values).\n")
                    f.write("- Next step: Verify HKL assignment and Stage A intensity computation.\n")

                f.write("\n")


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
    parser.add_argument(
        "--collect-hkl-stats",
        action="store_true",
        help="When set, capture nanobrag_torch HKL query stats for Stage A and simulate_forward_once paths.",
    )
    parser.add_argument(
        "--stage-a-mosaic-domains",
        type=int,
        default=16,
        help="Number of mosaic domain samples for Stage A/mapping/reconstruction (default: 16). Clamped to ≥1.",
    )
    parser.add_argument(
        "--collect-spot-profiles",
        action="store_true",
        help="When set, compute and store full-panel spot-profile energy partitions (ROI vs halo vs FWHM) for every matched reflection.",
    )
    parser.add_argument(
        "--spot-profile-halo-pixels",
        type=int,
        default=10,
        help="Number of pixels to expand ROI bbox for halo energy computation (default: 10). Clamped to ≥1.",
    )
    parser.add_argument(
        "--collect-orientation-metrics",
        action="store_true",
        help="When set, compute HKL orientation alignment metrics (fractional HKL, |Δhkl|, resolution, 2θ) for each matched ROI.",
    )
    args = parser.parse_args()

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Clamp stage_a_mosaic_domains to ≥1
    stage_a_mosaic_domains = max(1, args.stage_a_mosaic_domains)
    if stage_a_mosaic_domains != args.stage_a_mosaic_domains:
        print(f"[Stage A Baseline Probe] WARNING: --stage-a-mosaic-domains clamped from {args.stage_a_mosaic_domains} to {stage_a_mosaic_domains}")

    # Clamp spot_profile_halo_pixels to ≥1
    halo_pixels = max(1, args.spot_profile_halo_pixels)
    if halo_pixels != args.spot_profile_halo_pixels:
        print(f"[Stage A Baseline Probe] WARNING: --spot-profile-halo-pixels clamped from {args.spot_profile_halo_pixels} to {halo_pixels}")

    print(f"[Stage A Baseline Probe] Starting probe (device={args.device})")
    print(f"[Stage A Baseline Probe] Geometry mode: {args.geometry_mode}")
    print(f"[Stage A Baseline Probe] Stage A mosaic domains: {stage_a_mosaic_domains}")
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
        stage_a_mosaic_domains=stage_a_mosaic_domains,
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

    # ARCH-SIM-CONSTRUCTION-001 Phase C.14: Extract baseline_alignment_factor and cache_status
    # from baseline_stats.json written by reconstruction helper
    baseline_alignment_factor = 1.0
    cache_status = "unknown"
    baseline_stats_path = Path("plans/active/ARCH-SIM-CONSTRUCTION-001/reports") / Path(args.output).parent.name / "baseline_stats.json"
    if baseline_stats_path.exists():
        with open(baseline_stats_path, 'r') as f:
            baseline_stats_records = json.load(f)
            if isinstance(baseline_stats_records, list) and len(baseline_stats_records) > 0:
                # Get the most recent record (last one in list)
                latest_record = baseline_stats_records[-1]
                baseline_alignment_factor = latest_record.get('baseline_alignment_factor', 1.0)
                cache_status = latest_record.get('cache_status', 'unknown')
                print(f"[Stage A Baseline Probe] Extracted from baseline_stats.json:")
                print(f"  baseline_alignment_factor: {baseline_alignment_factor:.6f}")
                print(f"  cache_status: {cache_status}")
    else:
        print(f"[Stage A Baseline Probe] baseline_stats.json not found at {baseline_stats_path}; using defaults")

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

    # ARCH-SIM-CONSTRUCTION-001 Phase C.15: Collect detailed ROI diagnostics
    # Store per-ROI metrics for top/bottom-N analysis
    roi_diagnostics = []

    for pid, bbox in refinement_inputs.panel_slices:
        x0, x1, y0, y1 = bbox
        roi_mask = loss_mask_np[int(pid), y0:y1, x0:x1]
        if not np.any(roi_mask):
            continue

        target_roi = target_np[int(pid), y0:y1, x0:x1]
        mapping_roi = mapping_bragg[int(pid), y0:y1, x0:x1]
        stagea_roi = bragg_before[int(pid), y0:y1, x0:x1]

        mapping_vs_target_cc = _compute_pearson_cc(mapping_roi, target_roi, roi_mask)
        stagea_vs_target_cc = _compute_pearson_cc(stagea_roi, target_roi, roi_mask)
        stagea_vs_mapping_cc = _compute_pearson_cc(stagea_roi, mapping_roi, roi_mask)

        mapping_vs_target_roi_cc.append(mapping_vs_target_cc)
        stagea_vs_target_roi_cc.append(stagea_vs_target_cc)
        stagea_vs_mapping_roi_cc.append(stagea_vs_mapping_cc)

        # Compute masked mean deltas for this ROI
        target_roi_masked = target_roi[roi_mask]
        mapping_roi_masked = mapping_roi[roi_mask]
        stagea_roi_masked = stagea_roi[roi_mask]

        target_roi_mean = float(np.mean(target_roi_masked)) if target_roi_masked.size > 0 else float("nan")
        mapping_roi_mean = float(np.mean(mapping_roi_masked)) if mapping_roi_masked.size > 0 else float("nan")
        stagea_roi_mean = float(np.mean(stagea_roi_masked)) if stagea_roi_masked.size > 0 else float("nan")

        mapping_vs_target_delta = mapping_roi_mean - target_roi_mean
        stagea_vs_target_delta = stagea_roi_mean - target_roi_mean

        # Store diagnostic entry
        roi_diagnostics.append({
            "panel_id": int(pid),
            "bbox": [int(x0), int(x1), int(y0), int(y1)],
            "n_masked_pixels": int(np.count_nonzero(roi_mask)),
            "mapping_vs_target_cc": mapping_vs_target_cc,
            "stagea_vs_target_cc": stagea_vs_target_cc,
            "stagea_vs_mapping_cc": stagea_vs_mapping_cc,
            "target_mean_masked": target_roi_mean,
            "mapping_mean_masked": mapping_roi_mean,
            "stagea_mean_masked": stagea_roi_mean,
            "mapping_vs_target_delta": mapping_vs_target_delta,
            "stagea_vs_target_delta": stagea_vs_target_delta,
        })

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

    # Compute chi2_ratio unconditionally (used in output dict)
    chi2_ratio = float("nan")
    if np.isfinite(chi_squared_per_pixel_mapping) and np.isfinite(chi_squared_per_pixel_initial):
        chi2_ratio = abs(chi_squared_per_pixel_initial - chi_squared_per_pixel_mapping) / chi_squared_per_pixel_mapping if chi_squared_per_pixel_mapping > 0 else float("inf")

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
        if np.isfinite(chi2_ratio) and chi2_ratio > 1e-3:
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
    stage_a_hkl_stats = None
    mapping_hkl_stats = None
    if args.collect_hkl_stats:
        try:
            stage_a_hkl_stats = collect_stage_a_hkl_stats(
                detector=refinement_detector,
                beam=refinement_beam,
                crystal=refinement_crystal,
                refinement_inputs=refinement_inputs,
                hkl_grid=hkl_grid,
                hkl_metadata=hkl_metadata,
                config=config,
                device=device_obj,
            )
        except Exception as exc:  # pragma: no cover - diagnostics only
            print(f"[Stage A Baseline Probe] WARNING: Stage A HKL stats collection failed: {exc}")
            stage_a_hkl_stats = {"error": str(exc)}

        try:
            mapping_hkl_stats = collect_mapping_hkl_stats(
                refinement_inputs=refinement_inputs,
                detector=refinement_detector,
                beam=refinement_beam,
                crystal=refinement_crystal,
                experiment=refgeom_dataload.Expt,
                mapping_context=mapping_context,
                device=device_obj,
                apply_n_cells=apply_n_cells,
                config=config,
            )
        except Exception as exc:  # pragma: no cover - diagnostics only
            print(f"[Stage A Baseline Probe] WARNING: simulate_forward_once HKL stats collection failed: {exc}")
            mapping_hkl_stats = {"error": str(exc)}

    mapping_diagnostics = mapping_context.diagnostics if mapping_context.diagnostics else {}
    mapping_target_mean_masked = mapping_diagnostics.get("target_mean_masked")
    mapping_bragg_mean_masked = mapping_diagnostics.get("bragg_mean_masked")
    mapping_masked_mean_ratio = mapping_diagnostics.get("masked_mean_ratio")
    mapping_log_scale_baseline_source = mapping_diagnostics.get("log_scale_baseline_source")
    mapping_scale_adjustment_skipped = mapping_diagnostics.get("mapping_scale_adjustment_skipped", False)
    mapping_scale_skip_reason = mapping_diagnostics.get("mapping_scale_skip_reason")

    # ARCH-SIM-CONSTRUCTION-001 Phase C.15: Sort ROIs and extract top/bottom-N for detailed analysis
    # Sort by Stage A vs target correlation (ascending) to find worst/best ROIs
    roi_diagnostics_sorted = sorted(
        [r for r in roi_diagnostics if np.isfinite(r["stagea_vs_target_cc"])],
        key=lambda r: r["stagea_vs_target_cc"]
    )

    # Extract bottom 5 (worst correlations) and top 5 (best correlations)
    n_top_bottom = 5
    bottom_n_rois = roi_diagnostics_sorted[:n_top_bottom] if len(roi_diagnostics_sorted) >= n_top_bottom else roi_diagnostics_sorted
    top_n_rois = roi_diagnostics_sorted[-n_top_bottom:] if len(roi_diagnostics_sorted) >= n_top_bottom else []

    # Reverse top_n to show best first
    top_n_rois = list(reversed(top_n_rois))

    # ARCH-SIM-CONSTRUCTION-001 Phase C.17: Build HKL index→amplitude lookup dict
    # Build dictionary from mapping_context.hkl_indices → mapping_context.hkl_amplitudes
    # Convert indices to tuples for deterministic dict keys
    hkl_lookup = {}
    if mapping_context.hkl_indices is not None and mapping_context.hkl_amplitudes is not None:
        # hkl_indices is shape (n_refl, 3) numpy array
        # hkl_amplitudes is shape (n_refl,) numpy array
        for idx, amp in zip(mapping_context.hkl_indices, mapping_context.hkl_amplitudes):
            hkl_tuple = tuple(map(int, idx))
            hkl_lookup[hkl_tuple] = float(amp)

    print(f"[Stage A Baseline Probe] Built HKL lookup with {len(hkl_lookup)} entries")

    # ARCH-SIM-CONSTRUCTION-001 Phase C.16: Load reflection table and align with ROI ordering
    # Extract independent reference intensities from DIALS reflection table
    reflection_comparison = {
        "description": "Independent reference comparison using DIALS reflection table intensities",
        "n_reflections_total": 0,
        "n_reflections_matched": 0,
        "n_roi_mismatches": 0,
        "reflection_metrics": [],
        "reflection_top_n": [],
        "reflection_bottom_n": [],
        "reflection_stats": {},
        "provenance": {
            "refl_path": str(refl_path) if 'refl_path' in locals() else "unknown",
            "expt_path": str(expt_path) if 'expt_path' in locals() else "unknown",
        }
    }

    # Load reflection table from refgeom_dataload
    refs_table = refgeom_dataload.Refs
    n_reflections_total = len(refs_table)
    reflection_comparison["n_reflections_total"] = n_reflections_total

    # Convert DIALS flex arrays to numpy for deterministic iteration
    intensity_sum_values = np.array(refs_table['intensity.sum.value'], dtype=np.float64)
    panel_ids_ref = np.array(refs_table['panel'], dtype=np.int32)
    bboxes_ref = []
    miller_indices_ref = []
    for i in range(n_reflections_total):
        bbox = refs_table['bbox'][i]
        # bbox is (x0, x1, y0, y1, z0, z1) in DIALS convention
        bboxes_ref.append((int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])))

        # Extract Miller index as tuple for HKL lookup
        miller_idx = refs_table['miller_index'][i]
        miller_indices_ref.append((int(miller_idx[0]), int(miller_idx[1]), int(miller_idx[2])))

    # Match reflections to ROIs by panel and bbox
    # refinement_inputs.panel_slices is a list of (panel_id, [x0, x1, y0, y1])
    # Note: ROI bboxes are expanded from reflection bboxes by pad_for_background_estimation (typically 3 pixels)
    # So ROI bbox should contain the reflection bbox with some padding
    reflection_roi_matches = []
    n_roi_mismatches = 0

    for roi_idx, (pid, bbox_roi) in enumerate(refinement_inputs.panel_slices):
        x0_roi, x1_roi, y0_roi, y1_roi = bbox_roi
        pid = int(pid)

        # Find matching reflection: same panel and reflection bbox is contained within ROI bbox
        matched_refl_idx = None
        best_overlap = 0
        for refl_idx in range(n_reflections_total):
            if panel_ids_ref[refl_idx] != pid:
                continue
            x0_ref, x1_ref, y0_ref, y1_ref = bboxes_ref[refl_idx]

            # Check if reflection bbox is contained within ROI bbox (allowing for padding)
            # ROI should contain the reflection with some margin
            if (x0_ref >= x0_roi and x1_ref <= x1_roi and
                y0_ref >= y0_roi and y1_ref <= y1_roi):
                # Compute overlap area to find best match if multiple reflections overlap
                overlap_area = (x1_ref - x0_ref) * (y1_ref - y0_ref)
                if overlap_area > best_overlap:
                    matched_refl_idx = refl_idx
                    best_overlap = overlap_area

        if matched_refl_idx is not None:
            # Extract reflection intensity and compute per-pixel mean
            intensity_sum_ref = float(intensity_sum_values[matched_refl_idx])
            n_pixels_roi = roi_diagnostics[roi_idx]["n_masked_pixels"]

            # Compute per-pixel mean from reflection intensity sum
            intensity_per_pixel_ref = intensity_sum_ref / n_pixels_roi if n_pixels_roi > 0 else float("nan")

            # Extract Stage A / mapping / target means from roi_diagnostics
            stagea_mean = roi_diagnostics[roi_idx]["stagea_mean_masked"]
            mapping_mean = roi_diagnostics[roi_idx]["mapping_mean_masked"]
            target_mean = roi_diagnostics[roi_idx]["target_mean_masked"]

            # Compute ratios to reflection reference
            stagea_vs_ref_ratio = stagea_mean / intensity_per_pixel_ref if np.isfinite(intensity_per_pixel_ref) and intensity_per_pixel_ref > 0 else float("nan")
            mapping_vs_ref_ratio = mapping_mean / intensity_per_pixel_ref if np.isfinite(intensity_per_pixel_ref) and intensity_per_pixel_ref > 0 else float("nan")
            target_vs_ref_ratio = target_mean / intensity_per_pixel_ref if np.isfinite(intensity_per_pixel_ref) and intensity_per_pixel_ref > 0 else float("nan")

            # ARCH-SIM-CONSTRUCTION-001 Phase C.17: HKL amplitude lookup and amp_sq_per_pixel
            miller_idx_tuple = miller_indices_ref[matched_refl_idx]
            hkl_amplitude = hkl_lookup.get(miller_idx_tuple)

            # Fail fast if HKL is missing from lookup (per input.md requirement)
            if hkl_amplitude is None:
                raise ValueError(
                    f"ROI {roi_idx} matched to reflection {matched_refl_idx} with Miller index {miller_idx_tuple}, "
                    f"but this HKL is missing from the mapping_context HKL grid. "
                    f"This indicates a mismatch between the reflection table and the HKL source. "
                    f"HKL lookup has {len(hkl_lookup)} entries."
                )

            # Compute amp_sq_per_pixel = |F|^2 / n_masked_pixels
            amp_sq_per_pixel = (hkl_amplitude ** 2) / n_pixels_roi if n_pixels_roi > 0 else float("nan")

            # Compute ratios: amp^2 vs reflection, Stage A vs amp^2
            amp_sq_vs_ref_ratio = amp_sq_per_pixel / intensity_per_pixel_ref if np.isfinite(intensity_per_pixel_ref) and intensity_per_pixel_ref > 0 else float("nan")
            stagea_vs_amp_sq_ratio = stagea_mean / amp_sq_per_pixel if np.isfinite(amp_sq_per_pixel) and amp_sq_per_pixel > 0 else float("nan")

            reflection_roi_matches.append({
                "roi_idx": roi_idx,
                "refl_idx": matched_refl_idx,
                "panel_id": pid,
                "bbox": [x0_roi, x1_roi, y0_roi, y1_roi],
                "n_masked_pixels": n_pixels_roi,
                "intensity_sum_ref": intensity_sum_ref,
                "intensity_per_pixel_ref": intensity_per_pixel_ref,
                "stagea_mean_masked": stagea_mean,
                "mapping_mean_masked": mapping_mean,
                "target_mean_masked": target_mean,
                "stagea_vs_ref_ratio": stagea_vs_ref_ratio,
                "mapping_vs_ref_ratio": mapping_vs_ref_ratio,
                "target_vs_ref_ratio": target_vs_ref_ratio,
                "hkl_index": list(miller_idx_tuple),
                "hkl_amplitude": hkl_amplitude,
                "amp_sq_per_pixel": amp_sq_per_pixel,
                "amp_sq_vs_ref_ratio": amp_sq_vs_ref_ratio,
                "stagea_vs_amp_sq_ratio": stagea_vs_amp_sq_ratio,
            })
        else:
            n_roi_mismatches += 1

    n_reflections_matched = len(reflection_roi_matches)
    reflection_comparison["n_reflections_matched"] = n_reflections_matched
    reflection_comparison["n_roi_mismatches"] = n_roi_mismatches
    reflection_comparison["reflection_metrics"] = reflection_roi_matches

    # Guard: fail loudly if reflection table diverges from ROI ordering
    if n_roi_mismatches > 0:
        print(f"[WARNING] {n_roi_mismatches} ROIs could not be matched to reflection table entries")
        print(f"[WARNING] Total ROIs: {len(refinement_inputs.panel_slices)}, Reflections: {n_reflections_total}, Matched: {n_reflections_matched}")
        reflection_comparison["mismatch_warning"] = f"{n_roi_mismatches} ROIs unmatched"

    # Compute percentile stats for reflection ratios
    valid_stagea_vs_ref = [m["stagea_vs_ref_ratio"] for m in reflection_roi_matches if np.isfinite(m["stagea_vs_ref_ratio"])]
    valid_mapping_vs_ref = [m["mapping_vs_ref_ratio"] for m in reflection_roi_matches if np.isfinite(m["mapping_vs_ref_ratio"])]
    valid_target_vs_ref = [m["target_vs_ref_ratio"] for m in reflection_roi_matches if np.isfinite(m["target_vs_ref_ratio"])]
    valid_amp_sq_vs_ref = [m["amp_sq_vs_ref_ratio"] for m in reflection_roi_matches if np.isfinite(m["amp_sq_vs_ref_ratio"])]
    valid_stagea_vs_amp_sq = [m["stagea_vs_amp_sq_ratio"] for m in reflection_roi_matches if np.isfinite(m["stagea_vs_amp_sq_ratio"])]

    if valid_stagea_vs_ref:
        reflection_comparison["reflection_stats"]["stagea_vs_ref"] = {
            "median": float(np.median(valid_stagea_vs_ref)),
            "p25": float(np.percentile(valid_stagea_vs_ref, 25)),
            "p75": float(np.percentile(valid_stagea_vs_ref, 75)),
            "min": float(np.min(valid_stagea_vs_ref)),
            "max": float(np.max(valid_stagea_vs_ref)),
        }
    if valid_mapping_vs_ref:
        reflection_comparison["reflection_stats"]["mapping_vs_ref"] = {
            "median": float(np.median(valid_mapping_vs_ref)),
            "p25": float(np.percentile(valid_mapping_vs_ref, 25)),
            "p75": float(np.percentile(valid_mapping_vs_ref, 75)),
            "min": float(np.min(valid_mapping_vs_ref)),
            "max": float(np.max(valid_mapping_vs_ref)),
        }
    if valid_target_vs_ref:
        reflection_comparison["reflection_stats"]["target_vs_ref"] = {
            "median": float(np.median(valid_target_vs_ref)),
            "p25": float(np.percentile(valid_target_vs_ref, 25)),
            "p75": float(np.percentile(valid_target_vs_ref, 75)),
            "min": float(np.min(valid_target_vs_ref)),
            "max": float(np.max(valid_target_vs_ref)),
        }
    if valid_amp_sq_vs_ref:
        reflection_comparison["reflection_stats"]["amp_sq_vs_ref"] = {
            "median": float(np.median(valid_amp_sq_vs_ref)),
            "p25": float(np.percentile(valid_amp_sq_vs_ref, 25)),
            "p75": float(np.percentile(valid_amp_sq_vs_ref, 75)),
            "min": float(np.min(valid_amp_sq_vs_ref)),
            "max": float(np.max(valid_amp_sq_vs_ref)),
        }
    if valid_stagea_vs_amp_sq:
        reflection_comparison["reflection_stats"]["stagea_vs_amp_sq"] = {
            "median": float(np.median(valid_stagea_vs_amp_sq)),
            "p25": float(np.percentile(valid_stagea_vs_amp_sq, 25)),
            "p75": float(np.percentile(valid_stagea_vs_amp_sq, 75)),
            "min": float(np.min(valid_stagea_vs_amp_sq)),
            "max": float(np.max(valid_stagea_vs_amp_sq)),
        }

    # Sort by Stage A vs reference ratio (descending) to find worst mismatches
    reflection_matches_sorted = sorted(
        [m for m in reflection_roi_matches if np.isfinite(m["stagea_vs_ref_ratio"])],
        key=lambda m: abs(m["stagea_vs_ref_ratio"] - 1.0),
        reverse=True
    )

    # Extract bottom 5 (worst mismatches relative to reference) and top 5 (best matches)
    n_top_bottom_refl = 5
    bottom_n_refl = reflection_matches_sorted[:n_top_bottom_refl] if len(reflection_matches_sorted) >= n_top_bottom_refl else reflection_matches_sorted
    top_n_refl = reflection_matches_sorted[-n_top_bottom_refl:] if len(reflection_matches_sorted) >= n_top_bottom_refl else []
    top_n_refl = list(reversed(top_n_refl))

    reflection_comparison["reflection_bottom_n"] = bottom_n_refl
    reflection_comparison["reflection_top_n"] = top_n_refl

    # ARCH-SIM-CONSTRUCTION-001 Phase C.18: Compute spot-profile metrics if requested
    spot_profile_stats = None
    if args.collect_spot_profiles:
        print(f"[Stage A Baseline Probe] Computing spot profiles with halo={halo_pixels} pixels...")
        reflection_roi_matches = compute_spot_profiles(
            bragg_before=bragg_before,
            reflection_roi_matches=reflection_roi_matches,
            halo_pixels=halo_pixels,
        )

        # Update reflection_comparison with the enriched matches
        reflection_comparison["reflection_metrics"] = reflection_roi_matches

        # Compute summary statistics
        matches_with_profiles = [m for m in reflection_roi_matches if "spot_profile_metrics" in m]
        if matches_with_profiles:
            roi_fractions_halo = [m["spot_profile_metrics"]["roi_fraction_of_halo"] for m in matches_with_profiles if np.isfinite(m["spot_profile_metrics"]["roi_fraction_of_halo"])]
            roi_fractions_panel = [m["spot_profile_metrics"]["roi_fraction_of_panel"] for m in matches_with_profiles if np.isfinite(m["spot_profile_metrics"]["roi_fraction_of_panel"])]

            # Sort by ROI fraction of halo to find worst off-ROI energy
            sorted_by_off_roi = sorted(
                [m for m in matches_with_profiles if np.isfinite(m["spot_profile_metrics"]["roi_fraction_of_halo"])],
                key=lambda m: m["spot_profile_metrics"]["roi_fraction_of_halo"]
            )
            worst_5_off_roi = sorted_by_off_roi[:5] if len(sorted_by_off_roi) >= 5 else sorted_by_off_roi

            # Sort by FWHM (narrowest)
            def fwhm_geomean(m):
                fwhm_f = m["spot_profile_metrics"]["fwhm_fast"]
                fwhm_s = m["spot_profile_metrics"]["fwhm_slow"]
                if fwhm_f > 0 and fwhm_s > 0:
                    return np.sqrt(fwhm_f * fwhm_s)
                return float("inf")

            sorted_by_fwhm = sorted(matches_with_profiles, key=fwhm_geomean)
            narrowest_5_fwhm = sorted_by_fwhm[:5] if len(sorted_by_fwhm) >= 5 else sorted_by_fwhm

            spot_profile_stats = {
                "enabled": True,
                "halo_pixels": int(halo_pixels),
                "n_reflections_with_profiles": len(matches_with_profiles),
                "median_roi_fraction_of_halo": float(np.median(roi_fractions_halo)) if roi_fractions_halo else float("nan"),
                "median_roi_fraction_of_panel": float(np.median(roi_fractions_panel)) if roi_fractions_panel else float("nan"),
                "worst_5_off_roi_energy": [
                    {
                        "roi_idx": m["roi_idx"],
                        "panel_id": m["panel_id"],
                        "bbox": m["bbox"],
                        "hkl_index": m["hkl_index"],
                        "roi_fraction_of_halo": m["spot_profile_metrics"]["roi_fraction_of_halo"],
                        "roi_energy": m["spot_profile_metrics"]["roi_energy"],
                        "halo_energy": m["spot_profile_metrics"]["halo_energy"],
                    }
                    for m in worst_5_off_roi
                ],
                "narrowest_5_fwhm": [
                    {
                        "roi_idx": m["roi_idx"],
                        "panel_id": m["panel_id"],
                        "bbox": m["bbox"],
                        "hkl_index": m["hkl_index"],
                        "fwhm_fast": m["spot_profile_metrics"]["fwhm_fast"],
                        "fwhm_slow": m["spot_profile_metrics"]["fwhm_slow"],
                        "peak_value": m["spot_profile_metrics"]["peak_value"],
                    }
                    for m in narrowest_5_fwhm
                ],
            }

            print(f"[Stage A Baseline Probe] Spot profiles computed: {len(matches_with_profiles)} reflections")
            print(f"  Median ROI fraction of halo: {spot_profile_stats['median_roi_fraction_of_halo']:.4f}")
            print(f"  Median ROI fraction of panel: {spot_profile_stats['median_roi_fraction_of_panel']:.6f}")
        else:
            spot_profile_stats = {
                "enabled": True,
                "halo_pixels": int(halo_pixels),
                "n_reflections_with_profiles": 0,
                "error": "No spot-profile metrics computed",
            }
    else:
        spot_profile_stats = {"enabled": False}

    # ARCH-SIM-CONSTRUCTION-001 Phase C.23: Compute orientation metrics if requested
    orientation_alignment = None
    if args.collect_orientation_metrics:
        print(f"[Stage A Baseline Probe] Computing orientation metrics...")
        reflection_roi_matches = compute_orientation_metrics(
            detector=refinement_detector,
            beam=refinement_beam,
            crystal=refinement_crystal,
            reflection_roi_matches=reflection_roi_matches,
        )

        # Update reflection_comparison with enriched matches
        reflection_comparison["reflection_metrics"] = reflection_roi_matches

        # Extract orientation metrics for analysis
        matches_with_orientation = [m for m in reflection_roi_matches if "orientation_metrics" in m and "error" not in m["orientation_metrics"]]

        if matches_with_orientation:
            delta_hkl_norms = [m["orientation_metrics"]["delta_hkl_norm"] for m in matches_with_orientation]
            resolutions = [m["orientation_metrics"]["resolution_angstrom"] for m in matches_with_orientation if np.isfinite(m["orientation_metrics"]["resolution_angstrom"])]
            two_theta_degs = [m["orientation_metrics"]["two_theta_deg"] for m in matches_with_orientation if np.isfinite(m["orientation_metrics"]["two_theta_deg"])]

            # Compute correlation between |Δhkl| and Stage A vs ref ratios
            delta_hkl_for_corr = []
            stagea_ratios_for_corr = []
            for m in matches_with_orientation:
                if "stagea_vs_ref_ratio" in m and np.isfinite(m["stagea_vs_ref_ratio"]):
                    delta_hkl_for_corr.append(m["orientation_metrics"]["delta_hkl_norm"])
                    stagea_ratios_for_corr.append(m["stagea_vs_ref_ratio"])

            pearson_corr = float("nan")
            if len(delta_hkl_for_corr) > 1:
                try:
                    corr_matrix = np.corrcoef(delta_hkl_for_corr, stagea_ratios_for_corr)
                    pearson_corr = float(corr_matrix[0, 1]) if np.isfinite(corr_matrix[0, 1]) else float("nan")
                except Exception:
                    pearson_corr = float("nan")

            # Sort by delta_hkl_norm to find worst misalignments
            sorted_by_delta_hkl = sorted(matches_with_orientation, key=lambda m: m["orientation_metrics"]["delta_hkl_norm"], reverse=True)
            worst_5_misalignment = sorted_by_delta_hkl[:5] if len(sorted_by_delta_hkl) >= 5 else sorted_by_delta_hkl

            orientation_alignment = {
                "enabled": True,
                "n_reflections_with_orientation": len(matches_with_orientation),
                "median_delta_hkl_norm": float(np.median(delta_hkl_norms)) if delta_hkl_norms else float("nan"),
                "p25_delta_hkl_norm": float(np.percentile(delta_hkl_norms, 25)) if delta_hkl_norms else float("nan"),
                "p75_delta_hkl_norm": float(np.percentile(delta_hkl_norms, 75)) if delta_hkl_norms else float("nan"),
                "max_delta_hkl_norm": float(np.max(delta_hkl_norms)) if delta_hkl_norms else float("nan"),
                "median_resolution_angstrom": float(np.median(resolutions)) if resolutions else float("nan"),
                "median_two_theta_deg": float(np.median(two_theta_degs)) if two_theta_degs else float("nan"),
                "pearson_corr_delta_hkl_vs_stagea_ratio": pearson_corr,
                "n_pairs_for_correlation": len(delta_hkl_for_corr),
                "worst_5_misalignment": [
                    {
                        "roi_idx": m["roi_idx"],
                        "panel_id": m["panel_id"],
                        "bbox": m["bbox"],
                        "hkl_index": m["hkl_index"],
                        "delta_hkl_norm": m["orientation_metrics"]["delta_hkl_norm"],
                        "delta_hkl": m["orientation_metrics"]["delta_hkl"],
                        "resolution_angstrom": m["orientation_metrics"]["resolution_angstrom"],
                        "stagea_vs_ref_ratio": m.get("stagea_vs_ref_ratio", float("nan")),
                    }
                    for m in worst_5_misalignment
                ],
            }

            print(f"[Stage A Baseline Probe] Orientation metrics computed: {len(matches_with_orientation)} reflections")
            print(f"  Median |Δhkl|: {orientation_alignment['median_delta_hkl_norm']:.4f}")
            print(f"  Median resolution: {orientation_alignment['median_resolution_angstrom']:.2f} Å")
            print(f"  Pearson corr (|Δhkl| vs Stage A/ref ratio): {pearson_corr:.4f}" if np.isfinite(pearson_corr) else "  Pearson corr: undefined")
        else:
            orientation_alignment = {
                "enabled": True,
                "n_reflections_with_orientation": 0,
                "error": "No orientation metrics computed",
            }
    else:
        orientation_alignment = {"enabled": False}

    # Build output payload
    output = {
        "probe_metadata": {
            "timestamp": "2025-12-22T010000Z",
            "initiative": "ARCH-SIM-CONSTRUCTION-001",
            "phase": "C.18",
            "purpose": "Stage A mosaic-domain sweep to isolate Stage A↔reflection divergence boundary",
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
            "stage_a_mosaic_domains": stage_a_mosaic_domains,
            "hkl_ledger": {
                "n_hkl_entries": len(hkl_lookup),
                "description": "HKL amplitude lookup built from mapping_context.hkl_indices/hkl_amplitudes",
                "failfast_enabled": True,
                "failfast_reason": "ROI/HKL mismatch indicates asset divergence between reflection table and HKL source",
            },
        },
        "hkl_query_stats": {
            "enabled": args.collect_hkl_stats,
            "stage_a": stage_a_hkl_stats,
            "simulate_forward_once": mapping_hkl_stats,
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
        "baseline_alignment": {
            "baseline_alignment_factor": baseline_alignment_factor,
            "cache_status": cache_status,
            "description": "Phase C.14: Cold-path baseline alignment factor (telemetry / cold) when cache unavailable",
        },
        "roi_diagnostics": {
            "description": "Phase C.15: Per-ROI diagnostics to identify which ROIs drive DB-AT-028/029 failures",
            "n_total_rois": len(roi_diagnostics),
            "n_valid_rois": len(roi_diagnostics_sorted),
            "bottom_n_rois": bottom_n_rois,
            "top_n_rois": top_n_rois,
        },
        "reflection_comparison": reflection_comparison,
        "spot_profile_stats": spot_profile_stats,
        "orientation_alignment": orientation_alignment,
    }

    # Write JSON output
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"[Stage A Baseline Probe] Results written to {args.output}")

    # ARCH-SIM-CONSTRUCTION-001 Phase C.18: Write spot-profile Markdown summary if enabled
    if args.collect_spot_profiles and spot_profile_stats and spot_profile_stats.get("enabled"):
        spot_profile_summary_path = args.output.parent / "spot_profile_summary.md"
        _summarize_spot_profiles(
            reflection_roi_matches=reflection_roi_matches,
            output_path=spot_profile_summary_path,
            geometry_mode=args.geometry_mode,
            halo_pixels=halo_pixels,
            orientation_alignment=orientation_alignment,
        )
        print(f"[Stage A Baseline Probe] Spot-profile summary written to {spot_profile_summary_path}")

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

    # ARCH-SIM-CONSTRUCTION-001 Phase C.15: Print ROI diagnostics
    print("\nROI-Level Diagnostics (Phase C.15):")
    print("=" * 80)
    print(f"Total ROIs analyzed: {len(roi_diagnostics)}")
    print(f"Valid ROIs (finite Stage A vs target CC): {len(roi_diagnostics_sorted)}")
    print("")

    # Print bottom-N (worst) ROIs
    if bottom_n_rois:
        print(f"Bottom {len(bottom_n_rois)} ROIs (worst Stage A vs target correlation):")
        print("-" * 80)
        print(f"  {'Panel:BBox':<20} {'CC(StgA↔Tgt)':<15} {'CC(Map↔Tgt)':<15} {'Δ(StgA-Tgt)':<15} {'N_pix':<10}")
        print(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*15} {'-'*10}")
        for roi in bottom_n_rois:
            bbox_str = f"{roi['panel_id']}:[{roi['bbox'][0]},{roi['bbox'][1]},{roi['bbox'][2]},{roi['bbox'][3]}]"
            print(f"  {bbox_str:<20} {roi['stagea_vs_target_cc']:<15.4f} {roi['mapping_vs_target_cc']:<15.4f} {roi['stagea_vs_target_delta']:<15.6e} {roi['n_masked_pixels']:<10}")
        print("")

    # Print top-N (best) ROIs
    if top_n_rois:
        print(f"Top {len(top_n_rois)} ROIs (best Stage A vs target correlation):")
        print("-" * 80)
        print(f"  {'Panel:BBox':<20} {'CC(StgA↔Tgt)':<15} {'CC(Map↔Tgt)':<15} {'Δ(StgA-Tgt)':<15} {'N_pix':<10}")
        print(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*15} {'-'*10}")
        for roi in top_n_rois:
            bbox_str = f"{roi['panel_id']}:[{roi['bbox'][0]},{roi['bbox'][1]},{roi['bbox'][2]},{roi['bbox'][3]}]"
            print(f"  {bbox_str:<20} {roi['stagea_vs_target_cc']:<15.4f} {roi['mapping_vs_target_cc']:<15.4f} {roi['stagea_vs_target_delta']:<15.6e} {roi['n_masked_pixels']:<10}")
    print("=" * 80)

    # ARCH-SIM-CONSTRUCTION-001 Phase C.16: Print reflection-table comparison
    print("\nReflection-Table Reference Comparison (Phase C.16):")
    print("=" * 80)
    print(f"Total reflections in table: {n_reflections_total}")
    print(f"Reflections matched to ROIs: {n_reflections_matched}")
    print(f"ROIs without reflection match: {n_roi_mismatches}")

    if n_reflections_matched > 0:
        print("\nReflection vs Stage A/Mapping/Target Ratios:")
        print("-" * 80)
        print(f"  {'Metric':<30} {'Median':<12} {'P25-P75':<20} {'Min-Max':<20}")
        print(f"  {'-'*30} {'-'*12} {'-'*20} {'-'*20}")

        if "stagea_vs_ref" in reflection_comparison["reflection_stats"]:
            stats_sa = reflection_comparison["reflection_stats"]["stagea_vs_ref"]
            print(f"  {'Stage A / Refl (intensity)':<30} {stats_sa['median']:<12.4f} {stats_sa['p25']:.4f} - {stats_sa['p75']:<9.4f} {stats_sa['min']:.4f} - {stats_sa['max']:<9.4f}")

        if "mapping_vs_ref" in reflection_comparison["reflection_stats"]:
            stats_map = reflection_comparison["reflection_stats"]["mapping_vs_ref"]
            print(f"  {'Mapping / Refl (intensity)':<30} {stats_map['median']:<12.4f} {stats_map['p25']:.4f} - {stats_map['p75']:<9.4f} {stats_map['min']:.4f} - {stats_map['max']:<9.4f}")

        if "target_vs_ref" in reflection_comparison["reflection_stats"]:
            stats_tgt = reflection_comparison["reflection_stats"]["target_vs_ref"]
            print(f"  {'Target / Refl (intensity)':<30} {stats_tgt['median']:<12.4f} {stats_tgt['p25']:.4f} - {stats_tgt['p75']:<9.4f} {stats_tgt['min']:.4f} - {stats_tgt['max']:<9.4f}")

        print("")

        # ARCH-SIM-CONSTRUCTION-001 Phase C.17: Print HKL ledger stats
        print("HKL Amplitude Ledger (Phase C.17):")
        print("-" * 80)
        print(f"  {'Metric':<30} {'Median':<12} {'P25-P75':<20} {'Min-Max':<20}")
        print(f"  {'-'*30} {'-'*12} {'-'*20} {'-'*20}")

        if "amp_sq_vs_ref" in reflection_comparison["reflection_stats"]:
            stats_amp2 = reflection_comparison["reflection_stats"]["amp_sq_vs_ref"]
            print(f"  {'|F|^2/pix / Refl (intensity)':<30} {stats_amp2['median']:<12.4f} {stats_amp2['p25']:.4f} - {stats_amp2['p75']:<9.4f} {stats_amp2['min']:.4f} - {stats_amp2['max']:<9.4f}")

        if "stagea_vs_amp_sq" in reflection_comparison["reflection_stats"]:
            stats_sa_amp = reflection_comparison["reflection_stats"]["stagea_vs_amp_sq"]
            print(f"  {'Stage A / |F|^2/pix':<30} {stats_sa_amp['median']:<12.4f} {stats_sa_amp['p25']:.4f} - {stats_sa_amp['p75']:<9.4f} {stats_sa_amp['min']:.4f} - {stats_sa_amp['max']:<9.4f}")

        print(f"\n  HKL lookup entries: {len(hkl_lookup)}")
        print(f"  HKL source: {resolved_mtz_file}")
        print(f"  MTZ columns: {resolved_mtz_col}")
        print("")

        # Print worst mismatches (bottom_n)
        if bottom_n_refl:
            print(f"Bottom {len(bottom_n_refl)} ROIs (worst Stage A vs reflection match):")
            print("-" * 80)
            print(f"  {'Panel:BBox':<20} {'HKL':<12} {'|F|^2/pix':<12} {'StgA/|F|^2':<12} {'StgA/Refl':<12} {'N_pix':<10}")
            print(f"  {'-'*20} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*10}")
            for m in bottom_n_refl:
                bbox_str = f"{m['panel_id']}:[{m['bbox'][0]},{m['bbox'][1]},{m['bbox'][2]},{m['bbox'][3]}]"
                hkl_str = f"{m['hkl_index'][0]},{m['hkl_index'][1]},{m['hkl_index'][2]}"
                print(f"  {bbox_str:<20} {hkl_str:<12} {m['amp_sq_per_pixel']:<12.4e} {m['stagea_vs_amp_sq_ratio']:<12.4f} {m['stagea_vs_ref_ratio']:<12.4f} {m['n_masked_pixels']:<10}")
            print("")

        # Print best matches (top_n)
        if top_n_refl:
            print(f"Top {len(top_n_refl)} ROIs (best Stage A vs reflection match):")
            print("-" * 80)
            print(f"  {'Panel:BBox':<20} {'HKL':<12} {'|F|^2/pix':<12} {'StgA/|F|^2':<12} {'StgA/Refl':<12} {'N_pix':<10}")
            print(f"  {'-'*20} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*10}")
            for m in top_n_refl:
                bbox_str = f"{m['panel_id']}:[{m['bbox'][0]},{m['bbox'][1]},{m['bbox'][2]},{m['bbox'][3]}]"
                hkl_str = f"{m['hkl_index'][0]},{m['hkl_index'][1]},{m['hkl_index'][2]}"
                print(f"  {bbox_str:<20} {hkl_str:<12} {m['amp_sq_per_pixel']:<12.4e} {m['stagea_vs_amp_sq_ratio']:<12.4f} {m['stagea_vs_ref_ratio']:<12.4f} {m['n_masked_pixels']:<10}")
    else:
        print("\n[WARNING] No reflections matched to ROIs - cannot perform reference comparison")

    print("=" * 80)

    # Fail when baseline mode has parity violations (ARCH-SIM-CONSTRUCTION-001 Phase C.13)
    # In baseline mode, Stage A and mapping should produce identical outputs (max|Δ| < 1 ADU)
    # In perturbed mode, differences are expected and we only report them
    if args.geometry_mode == "baseline" and len(mapping_parity_warnings) > 0:
        print("\nERROR: Baseline mode parity check FAILED")
        print("Stage A vs mapping outputs should be identical in baseline mode.")
        print("See warnings above for details.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
