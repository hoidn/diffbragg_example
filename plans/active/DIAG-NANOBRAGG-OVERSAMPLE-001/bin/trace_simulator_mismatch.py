#!/usr/bin/env python
"""
Trace simulator unit mismatch probe for DIAG-UNIT-001 evidence collection.

DIAG-NANOBRAGG-OVERSAMPLE-001 Phase D (2025-12-03)

Purpose:
    Reproduce the crystal/cell unit mismatch showing that nanobrag_torch Crystal
    real-space vectors (stored in meters) and scattering vectors (Å⁻¹) produce
    HKL fractional coordinates ~1e-9 (off by 10¹⁰), causing lookups to fall back
    to default_F=0.

Strategy:
    - Load smoke fixtures via DataLoad + build_mapping_stage_a_context
    - Build Stage A warm cache with RefinementConfig(oversample=3)
    - Toggle trace_pixel + printout on cached simulator
    - Capture stdout with contextlib.redirect_stdout
    - Parse TRACE_PY vectors (scattering, rot_a/b/c, hkl_frac/rounded)
    - Compute derived metrics showing the 1e10 scale error
    - Write simulator_trace.log, simulator_trace_metrics.json, crystal_unit_analysis.md

Findings Applied:
    - DIAG-OVERSAMPLE-001: Keep detector/beam configs identical to Stage A warm cache
    - DIAG-UNIT-001: This script codifies the unit mismatch reproduction
"""

import argparse
import contextlib
import io
import json
import re
import sys
from pathlib import Path

import numpy as np
import torch

# Add repo root to path for dbex imports
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from dbex.data_load import DataLoad
from dbex.vis.mapping import build_mapping_stage_a_context
from dbex.nanobrag_bridge import build_structure_factor_grid
from dbex.refinement.stage_a_utils import _build_stage_a_context
from dbex.refinement.config import RefinementConfig


def load_smoke_fixture(detector_size="small"):
    """
    Load smoke fixture data following canonical paths from data_dependency_manifest.md.

    Args:
        detector_size: "small" or "full"

    Returns:
        DataLoad object with Expt, bbox, trusted_mask, calibration_path
    """
    repo_root_path = Path(__file__).parent.parent.parent.parent.parent

    if detector_size == "small":
        smoke_data_dir = repo_root_path / "sp.proc" / "refGeom_small"
        expt_name = "refGeom_small.expt"
        refl_name = "refGeom_small.refl"
        mask_name = "refGeom_small_mask.pkl"
        calib_path = repo_root_path / "sp.proc" / "calibration" / "config_torch_smoke_small.json"
        refined_mtz = repo_root_path / "sp.proc" / "calibration" / "smoke_refined_structure_factors_small.mtz"
    else:
        smoke_data_dir = repo_root_path / "sp.proc"
        expt_name = "idx-0000_imported.expt"
        refl_name = "idx-0000_indexed.refl"
        mask_name = "idx-0000_mask.pkl"
        calib_path = repo_root_path / "sp.proc" / "calibration" / "config_torch_smoke.json"
        refined_mtz = repo_root_path / "sp.proc" / "calibration" / "smoke_refined_structure_factors.mtz"

    calibration_config_path = str(calib_path) if calib_path.exists() else None

    # Resolve HKL path (refined MTZ when calibration exists, else scaled.mtz)
    scaled_mtz = repo_root_path / "scaled.mtz"
    if refined_mtz.exists():
        hkl_source_path = refined_mtz
    else:
        hkl_source_path = scaled_mtz

    # Build args namespace following refgeom_dataload fixture pattern
    from argparse import Namespace
    args = Namespace(
        exptName=(smoke_data_dir / expt_name).as_posix(),
        reflName=(smoke_data_dir / refl_name).as_posix(),
        exptIdx=0,
        maskFile=(smoke_data_dir / mask_name).as_posix(),
        mtzFile=str(scaled_mtz),
        mtzCol="F,SIGF",
        hkl_source_path=str(hkl_source_path),
        calibration_config_path=calibration_config_path,
    )

    # Load via DataLoad
    loader = DataLoad(args)
    return loader


def parse_trace_vectors(log_text):
    """
    Parse TRACE_PY vectors from simulator trace log.

    Returns:
        dict with parsed vectors and scalars
    """
    data = {}

    # Parse 3-component vectors
    vec3_patterns = {
        "scattering_vec_A_inv": r"TRACE_PY: scattering_vec_A_inv\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)",
        "rot_a_angstroms": r"TRACE_PY: rot_a_angstroms\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)",
        "rot_b_angstroms": r"TRACE_PY: rot_b_angstroms\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)",
        "rot_c_angstroms": r"TRACE_PY: rot_c_angstroms\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)",
        "hkl_frac": r"TRACE_PY: hkl_frac\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)",
        "hkl_rounded": r"TRACE_PY: hkl_rounded\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)",
    }

    for key, pattern in vec3_patterns.items():
        match = re.search(pattern, log_text)
        if match:
            data[key] = [float(match.group(1)), float(match.group(2)), float(match.group(3))]

    # Parse scalars
    scalar_patterns = {
        "lambda_angstroms": r"TRACE_PY: lambda_angstroms\s+([-\d.e+]+)",
        "F_cell_interpolated": r"TRACE_PY: F_cell_interpolated\s+([-\d.e+]+)",
        "F_cell_nearest": r"TRACE_PY: F_cell_nearest\s+([-\d.e+]+)",
        "oversample_thick": r"TRACE_PY: oversample_thick\s+([-\d.e+]+)",
        "oversample_polar": r"TRACE_PY: oversample_polar\s+([-\d.e+]+)",
        "oversample_omega": r"TRACE_PY: oversample_omega\s+([-\d.e+]+)",
    }

    for key, pattern in scalar_patterns.items():
        match = re.search(pattern, log_text)
        if match:
            data[key] = float(match.group(1))

    return data


def compute_derived_metrics(trace_data):
    """
    Compute derived metrics showing the unit mismatch.

    Args:
        trace_data: parsed trace vectors dict

    Returns:
        dict with derived metrics
    """
    metrics = {}

    # Scattering vector magnitude (reported as Å⁻¹ but actually m⁻¹)
    if "scattering_vec_A_inv" in trace_data:
        q_vec = np.array(trace_data["scattering_vec_A_inv"])
        metrics["scattering_vec_norm"] = float(np.linalg.norm(q_vec))

    # Real-space vector magnitudes (reported as Å but actually meters)
    for abc in ["a", "b", "c"]:
        key = f"rot_{abc}_angstroms"
        if key in trace_data:
            vec = np.array(trace_data[key])
            metrics[f"rot_{abc}_norm"] = float(np.linalg.norm(vec))

    # HKL fractional coordinates (raw from trace)
    if "hkl_frac" in trace_data:
        hkl_raw = np.array(trace_data["hkl_frac"])
        metrics["hkl_frac_raw"] = hkl_raw.tolist()
        metrics["hkl_frac_raw_mean"] = float(np.mean(np.abs(hkl_raw)))

        # Corrected HKL (if we multiply by 1e10 to fix unit mismatch)
        hkl_corrected = hkl_raw * 1e10
        metrics["hkl_frac_corrected"] = hkl_corrected.tolist()
        metrics["hkl_frac_corrected_mean"] = float(np.mean(np.abs(hkl_corrected)))

    # Dot product analysis (example: q · a)
    if "scattering_vec_A_inv" in trace_data and "rot_a_angstroms" in trace_data:
        q_vec = np.array(trace_data["scattering_vec_A_inv"])
        a_vec = np.array(trace_data["rot_a_angstroms"])

        # Raw dot product (mixing m⁻¹ and m)
        dot_raw = float(np.dot(q_vec, a_vec))
        metrics["dot_q_a_raw"] = dot_raw

        # Corrected dot product (if a_vec was in Å as labeled)
        dot_corrected = dot_raw * 1e10
        metrics["dot_q_a_corrected"] = dot_corrected

    # Add context: the mismatch factor
    metrics["unit_mismatch_factor"] = 1e10
    metrics["explanation"] = "HKL fractional coords are ~1e-9 because scattering vectors are in m^-1 while crystal vectors are in m (both labeled as Angstrom units)"

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Trace simulator unit mismatch for DIAG-UNIT-001")
    parser.add_argument("--detector-size", type=str, default="small", choices=["small", "full"],
                        help="Detector size (small or full)")
    parser.add_argument("--trace-fast", type=int, default=0, help="Fast pixel coordinate to trace")
    parser.add_argument("--trace-slow", type=int, default=0, help="Slow pixel coordinate to trace")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu or cuda:0)")
    parser.add_argument("--out-dir", type=str, required=True, help="Output directory for artifacts")
    args = parser.parse_args()

    device_obj = torch.device(args.device)
    device_str = str(device_obj)
    dtype = torch.float32

    # Create output directory
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[DIAG-NANOBRAGG-OVERSAMPLE-001] Simulator Unit Mismatch Trace")
    print(f"Detector size: {args.detector_size}")
    print(f"Trace pixel: [fast={args.trace_fast}, slow={args.trace_slow}]")
    print(f"Device: {device_str}")
    print(f"Output: {out_dir}")
    print()

    # ============================================================
    # 1. Load smoke fixture
    # ============================================================
    print("[1/5] Loading smoke fixture...")
    dataload = load_smoke_fixture(detector_size=args.detector_size)

    # Build mapping context
    mapping_context = build_mapping_stage_a_context(
        dataload,
        default_sigma_readout=3.0,
        device=device_str,
        apply_calibration_n_cells=True,
    )

    # Extract HKL grid
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=mapping_context.hkl_indices,
        amplitudes=mapping_context.hkl_amplitudes,
        device=device_obj,
        halo=True,
    )

    baseline_detector = dataload.Expt.detector
    baseline_beam = dataload.Expt.beam
    baseline_crystal = dataload.Expt.crystal
    trusted_mask = dataload.trusted_mask

    print(f"  HKL grid shape: {hkl_grid.shape}")
    print(f"  n_panels: {len(baseline_detector)}")
    print()

    # ============================================================
    # 2. Build Stage A warm cache
    # ============================================================
    print("[2/5] Building Stage A warm cache (oversample=3)...")

    # Use RefinementConfig with oversample=3
    refinement_config = RefinementConfig(oversample=3)

    # Panel mode (empty panel_slices)
    panel_slices = []

    stage_a_ctx = _build_stage_a_context(
        detector=baseline_detector,
        beam=baseline_beam,
        crystal=baseline_crystal,
        trusted_mask=trusted_mask,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        enable_hkl_interpolation=False,
        device=device_obj,
        dtype=dtype,
        panel_slices=panel_slices,
        enable_roi_mode=False,
        calibration_metadata=mapping_context.calibration,
        log_scale_baseline=None,
        apply_calibration_n_cells=True,
        config=refinement_config,
    )

    # Get first panel simulator
    simulator = stage_a_ctx.simulators[0]
    print(f"  Simulator cached, oversample setting: {refinement_config.oversample}")
    print()

    # ============================================================
    # 3. Toggle trace diagnostics
    # ============================================================
    print("[3/5] Toggling trace_pixel + printout...")

    # Update simulator debug config
    simulator.printout = True
    simulator.trace_pixel = [args.trace_slow, args.trace_fast]

    print(f"  trace_pixel: {simulator.trace_pixel}")
    print(f"  printout: {simulator.printout}")
    print()

    # ============================================================
    # 4. Run simulator with stdout capture
    # ============================================================
    print("[4/5] Running simulator and capturing trace...")

    # Capture stdout
    stdout_capture = io.StringIO()
    with contextlib.redirect_stdout(stdout_capture):
        bragg_output = simulator.run()

    trace_log = stdout_capture.getvalue()

    # Write raw trace log
    trace_log_path = out_dir / "simulator_trace.log"
    with open(trace_log_path, 'w') as f:
        f.write(trace_log)

    print(f"  Trace log written to: {trace_log_path}")
    print(f"  Bragg output shape: {bragg_output.shape}")
    print(f"  Bragg mean: {bragg_output.mean().item():.6e}")
    print()

    # ============================================================
    # 5. Parse and emit metrics
    # ============================================================
    print("[5/5] Parsing trace vectors and computing metrics...")

    # Parse TRACE_PY vectors
    trace_data = parse_trace_vectors(trace_log)

    # Compute derived metrics
    derived_metrics = compute_derived_metrics(trace_data)

    # Combine into full metrics dict
    metrics = {
        "trace_pixel": {
            "fast": args.trace_fast,
            "slow": args.trace_slow,
        },
        "detector_size": args.detector_size,
        "device": device_str,
        "trace_vectors": trace_data,
        "derived_metrics": derived_metrics,
    }

    # Write metrics JSON
    metrics_path = out_dir / "simulator_trace_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"  Metrics written to: {metrics_path}")
    print()

    # ============================================================
    # 6. Write crystal unit analysis summary
    # ============================================================
    analysis_path = out_dir / "crystal_unit_analysis.md"
    with open(analysis_path, 'w') as f:
        f.write("# Crystal Unit Mismatch Analysis — DIAG-UNIT-001\n\n")
        f.write("## Summary\n\n")
        f.write("This trace demonstrates that `nanobrag_torch.Crystal` real-space vectors ")
        f.write("(rot_a/b/c) are stored in meters while being labeled as Ångströms, and ")
        f.write("scattering vectors are in m⁻¹ while labeled as Å⁻¹. When these are dotted ")
        f.write("together in `compute_physics_for_position`, the HKL fractional coordinates ")
        f.write("come out at ~1e-9 (off by 10¹⁰), causing all lookups to fall outside the ")
        f.write("HKL grid and default to F=0.\n\n")

        f.write("## Evidence\n\n")

        if "scattering_vec_norm" in derived_metrics:
            f.write(f"- **Scattering vector magnitude:** `{derived_metrics['scattering_vec_norm']:.3e}` ")
            f.write("(labeled as Å⁻¹ but clearly m⁻¹ given magnitude ~5.8×10⁹)\n")

        if "rot_a_norm" in derived_metrics:
            f.write(f"- **rot_a magnitude:** `{derived_metrics['rot_a_norm']:.3e}` ")
            f.write("(labeled as Å but clearly m given magnitude ~3×10⁻⁹)\n")

        if "hkl_frac_raw_mean" in derived_metrics:
            f.write(f"- **HKL fractional coords (raw):** mean `{derived_metrics['hkl_frac_raw_mean']:.3e}` ")
            f.write("(should be O(1) for typical Miller indices)\n")

        if "hkl_frac_corrected_mean" in derived_metrics:
            f.write(f"- **HKL fractional coords (corrected × 1e10):** mean `{derived_metrics['hkl_frac_corrected_mean']:.3e}` ")
            f.write("(now in reasonable range)\n")

        f.write("\n## Specification Reference\n\n")
        f.write("Per `docs/spec-db-core.md:14`:\n\n")
        f.write("> Crystal: Å and degrees; convert to meters only for geometry-physics dot products.\n\n")
        f.write("The current implementation violates this by storing crystal vectors in meters ")
        f.write("from the start, rather than converting only at dot-product time.\n\n")

        f.write("## Artifact Paths\n\n")
        # Convert to absolute paths first for relative_to to work
        trace_log_abs = trace_log_path.resolve()
        metrics_abs = metrics_path.resolve()
        analysis_abs = analysis_path.resolve()
        repo_root_abs = Path(repo_root).resolve()

        f.write(f"- Trace log: `{trace_log_abs.relative_to(repo_root_abs)}`\n")
        f.write(f"- Metrics JSON: `{metrics_abs.relative_to(repo_root_abs)}`\n")
        f.write(f"- This analysis: `{analysis_abs.relative_to(repo_root_abs)}`\n")

    print(f"  Analysis written to: {analysis_path}")
    print()
    print("[DONE] Trace complete. See artifacts in:", out_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
