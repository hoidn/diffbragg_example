#!/usr/bin/env python
"""
Intensity + Calibration Metrics Probe for Simulator Construction Investigation

ARCH-SIM-CONSTRUCTION-001 Phase C.5 (intensity-scale evidence collection loop)

Purpose:
    Compare raw/scaled intensity outputs and calibration input threading across three paths:
    1. Stage A warm-cache simulator (training helper)
    2. Reconstruction cold-path simulator (inference helper)
    3. simulate_forward_once (canonical mapping helper)

Strategy:
    - Build simulators via all three paths using identical smoke fixture
    - Capture per-path calibration inputs (spot_scale_override, log_scale_baseline,
      beam_flux, beam_exposure, beamsize_mm, adu_per_photon)
    - Record raw simulator outputs (before post-run scaling)
    - Record sqrt-spot-scale-adjusted outputs (after SCALE-002 application)
    - Record final scale_factor (exp(log_scale_baseline + delta) for reconstruction)
    - Compute cross-path ratios to pinpoint which scale term is missing

Expected outcomes:
    - If all three paths produce similar raw outputs: scaling bug is in post-run logic
    - If Stage A differs from reconstruction/mapping: warm-cache embeds calibration
    - If reconstruction differs from Stage A+mapping: cold-path factory has construction bug
    - Calibration metrics will show which beam/scale parameters are threaded vs missing

Findings Applied:
    - SCALE-002: sqrt(spot_scale) post-run application
    - ARCH-FACTORY-001: Unified factory contract
    - DIAG-OVERSAMPLE-001: Oversampling must be explicit (oversample=3)
    - ARCH-SIM-HKL-BOUNDS-001: HKL grid alignment (incident beam sign fix)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import torch

# Add repo root to path for dbex imports
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from dbex.data_load import DataLoad
from dbex.vis.mapping import build_mapping_stage_a_context
from dbex.nanobrag_bridge import build_structure_factor_grid, simulate_forward_once
from dbex.refinement.stage_a_utils import _build_stage_a_context
from dbex.refinement.config_factories import create_beam_config, create_crystal_config, create_detector_config
from dbex.refinement.helpers import create_unified_simulator
from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry
from dbex.refinement.inputs import prepare_refinement_inputs


def load_test_fixture(detector_size: str = "small"):
    """
    Load refgeom_dataload fixture data following test_stage_a_smoke_parity.py pattern.

    Args:
        detector_size: "small" or other size variant (default "small")

    Returns:
        DataLoad object with Expt, bbox, trusted_mask, calibration_path
    """
    # Use same dataset paths as smoke tests
    # Script is at plans/active/.../bin/, so go up 5 levels to reach repo root
    # (bin -> ARCH-SIM-CONSTRUCTION-001 -> active -> plans -> diffbragg_example)
    repo_root_path = Path(__file__).parent.parent.parent.parent.parent
    smoke_data_dir = repo_root_path / "sp.proc" / f"refGeom_{detector_size}"

    # Check for calibration config (smoke default)
    calib_path = repo_root_path / "sp.proc" / "calibration" / "config_torch_smoke.json"
    calibration_config_path = str(calib_path) if calib_path.exists() else None

    # Resolve HKL path (refined MTZ when calibration exists, else scaled.mtz)
    refined_mtz = repo_root_path / "sp.proc" / "calibration" / "smoke_refined_structure_factors.mtz"
    scaled_mtz = repo_root_path / "scaled.mtz"
    if refined_mtz.exists():
        hkl_source_path = refined_mtz
    else:
        hkl_source_path = scaled_mtz

    # Build args namespace following refgeom_dataload fixture pattern
    from argparse import Namespace
    args = Namespace(
        exptName=(smoke_data_dir / f"refGeom_{detector_size}.expt").as_posix(),
        reflName=(smoke_data_dir / f"refGeom_{detector_size}.refl").as_posix(),
        exptIdx=0,
        maskFile=(smoke_data_dir / f"refGeom_{detector_size}_mask.pkl").as_posix(),
        mtzFile=str(repo_root_path / "scaled.mtz"),
        mtzCol="F,SIGF",
        hkl_source_path=str(hkl_source_path),
        calibration_config_path=calibration_config_path,
    )

    # Load via DataLoad
    loader = DataLoad(args)
    return loader


def extract_calibration_inputs(calibration: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract all calibration input parameters for telemetry.

    Args:
        calibration: Calibration metadata dict from DataLoad

    Returns:
        Dict with calibration fields (spot_scale_override, beam_flux, beam_exposure,
        beamsize_mm, adu_per_photon, N_cells) where available, else None
    """
    if calibration is None:
        return {
            "spot_scale_override": None,
            "beam_flux": None,
            "beam_exposure": None,
            "beamsize_mm": None,
            "adu_per_photon": None,
            "N_cells": None,
        }

    return {
        "spot_scale_override": calibration.get("spot_scale_override"),
        "beam_flux": calibration.get("beam_flux"),
        "beam_exposure": calibration.get("beam_exposure"),
        "beamsize_mm": calibration.get("beamsize_mm"),
        "adu_per_photon": calibration.get("adu_per_photon"),
        "N_cells": calibration.get("N_cells"),
    }


def run_stage_a_path(
    refgeom_dataload: DataLoad,
    mapping_context,
    hkl_grid,
    hkl_metadata,
    device_obj,
    dtype,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Run Stage A warm-cache path simulator and extract raw/scaled outputs.

    Returns:
        bragg_raw: Raw simulator output (first panel only)
        metrics: Dict with raw_mean, raw_max, sqrt_spot_scale, calibration_inputs
    """
    calibration = mapping_context.calibration
    spot_scale_override = 1.0
    if calibration:
        spot_scale_override = float(calibration.get("spot_scale_override", 1.0))
    sqrt_spot_scale = float(np.sqrt(spot_scale_override))
    log_scale_baseline = float(np.log(sqrt_spot_scale)) if sqrt_spot_scale > 0 else 0.0

    baseline_detector = refgeom_dataload.Expt.detector
    baseline_beam = refgeom_dataload.Expt.beam
    baseline_crystal = refgeom_dataload.Expt.crystal
    trusted_mask = refgeom_dataload.trusted_mask

    # Compute panel slices (empty list = panel mode, not ROI mode)
    panel_slices = []

    # Build Stage A context (replicating stage_a.py warm cache construction)
    stage_a_ctx = _build_stage_a_context(
        detector=baseline_detector,
        beam=baseline_beam,
        crystal=baseline_crystal,
        trusted_mask=trusted_mask,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        enable_hkl_interpolation=False,  # Nearest-neighbor per DB-AT-028
        device=device_obj,
        dtype=dtype,
        panel_slices=panel_slices,
        enable_roi_mode=False,
        calibration_metadata=calibration,
        log_scale_baseline=log_scale_baseline,
        apply_calibration_n_cells=True,
    )

    # Extract first panel simulator
    stage_a_simulator = stage_a_ctx.simulators[0]

    # Run Stage A simulator
    bragg_raw_tensor = stage_a_simulator.run()
    bragg_raw = bragg_raw_tensor.cpu().detach().numpy()

    # Compute post-sqrt-scaling output (Stage A applies sqrt_spot_scale post-run)
    bragg_scaled = bragg_raw * sqrt_spot_scale

    metrics = {
        "raw_mean": float(bragg_raw.mean()),
        "raw_max": float(bragg_raw.max()),
        "scaled_mean": float(bragg_scaled.mean()),
        "scaled_max": float(bragg_scaled.max()),
        "sqrt_spot_scale": sqrt_spot_scale,
        "log_scale_baseline": log_scale_baseline,
        "calibration_inputs": extract_calibration_inputs(calibration),
    }

    return bragg_raw, metrics


def run_reconstruction_path(
    refgeom_dataload: DataLoad,
    mapping_context,
    hkl_grid,
    hkl_metadata,
    device_obj,
    dtype,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Run reconstruction cold-path simulator and extract raw/scaled outputs plus scale_factor.

    Returns:
        bragg_raw: Raw simulator output (first panel only)
        metrics: Dict with raw_mean, raw_max, sqrt_spot_scale, scale_factor, calibration_inputs
    """
    calibration = mapping_context.calibration
    spot_scale_override = 1.0
    if calibration:
        spot_scale_override = float(calibration.get("spot_scale_override", 1.0))
    sqrt_spot_scale = float(np.sqrt(spot_scale_override))
    log_scale_baseline = float(np.log(sqrt_spot_scale)) if sqrt_spot_scale > 0 else 0.0

    baseline_detector = refgeom_dataload.Expt.detector
    baseline_beam = refgeom_dataload.Expt.beam

    # Extract first panel
    panel_0 = baseline_detector[0]

    # Build configs (matching reconstruction.py:187-206)
    beam_flux = None
    beam_exposure = None
    beamsize_mm = None
    if calibration:
        beam_flux = calibration.get("beam_flux")
        beam_exposure = calibration.get("beam_exposure")
        beamsize_mm = calibration.get("beamsize_mm")

    beam_config = create_beam_config(baseline_beam, flux=beam_flux, exposure=beam_exposure, beamsize_mm=beamsize_mm)

    # Build crystal config (matching stage_a_utils.py:272 with apply_n_cells=True)
    N_cells = calibration.get("N_cells") if calibration else None
    baseline_crystal = refgeom_dataload.Expt.crystal
    crystal_config, _ = create_crystal_config(baseline_crystal, None, N_cells=N_cells, apply_n_cells=True)

    detector_config = create_detector_config(panel_0, beam=baseline_beam, oversample=3)

    # Build simulator via unified factory
    simulator_recon, normalized_mask, sqrt_scale_from_factory, metadata = create_unified_simulator(
        detector_config=detector_config,
        crystal_config=crystal_config,
        beam_config=beam_config,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        mask_array=None,
        spot_scale_override=spot_scale_override,
        device=device_obj,
        dtype=dtype,
        calibration_metadata=calibration,
    )
    simulator_recon.interpolate = False  # Match Stage A

    # Run reconstruction simulator
    bragg_raw_tensor = simulator_recon.run()
    bragg_raw = bragg_raw_tensor.cpu().detach().numpy()

    # Compute scale_factor (reconstruction applies exp(log_scale_baseline + delta))
    # For this probe, delta=0 (no training), so scale_factor = exp(log_scale_baseline)
    scale_factor = np.exp(log_scale_baseline) if log_scale_baseline is not None else 1.0

    # Compute post-scale output (reconstruction applies scale_factor, NOT sqrt_spot_scale)
    bragg_scaled = bragg_raw * scale_factor

    metrics = {
        "raw_mean": float(bragg_raw.mean()),
        "raw_max": float(bragg_raw.max()),
        "scaled_mean": float(bragg_scaled.mean()),
        "scaled_max": float(bragg_scaled.max()),
        "sqrt_spot_scale": sqrt_spot_scale,
        "log_scale_baseline": log_scale_baseline,
        "scale_factor": float(scale_factor),
        "calibration_inputs": extract_calibration_inputs(calibration),
    }

    return bragg_raw, metrics


def run_simulate_forward_once_path(
    refgeom_dataload: DataLoad,
    mapping_context,
    device_obj,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Run simulate_forward_once canonical mapping helper and extract raw/scaled outputs.

    Returns:
        bragg_raw: Raw simulator output (before SCALE-002, first panel only)
        metrics: Dict with raw_mean, raw_max, sqrt_spot_scale, calibration_inputs
    """
    calibration = mapping_context.calibration
    spot_scale_override = 1.0
    if calibration:
        spot_scale_override = float(calibration.get("spot_scale_override", 1.0))
    sqrt_spot_scale = float(np.sqrt(spot_scale_override))

    # Use the already-prepared refinement inputs from mapping_context
    inputs = mapping_context.inputs

    # Run simulate_forward_once
    bragg_scaled_full, diagnostics = simulate_forward_once(
        inputs=inputs,
        detector=refgeom_dataload.Expt.detector,
        beam=refgeom_dataload.Expt.beam,
        crystal=refgeom_dataload.Expt.crystal,
        experiment=refgeom_dataload.Expt,
        hkl_indices=mapping_context.hkl_indices,
        hkl_amplitudes=mapping_context.hkl_amplitudes,
        spot_scale_override=spot_scale_override,
        calibration=calibration,
        device=device_obj,
        apply_calibration_n_cells=True,
    )

    # Extract first panel (simulate_forward_once returns full [panel, slow, fast] array)
    bragg_scaled = bragg_scaled_full[0]

    # Reverse SCALE-002 application to get raw output
    bragg_raw = bragg_scaled / sqrt_spot_scale if sqrt_spot_scale != 0 else bragg_scaled

    metrics = {
        "raw_mean": float(bragg_raw.mean()),
        "raw_max": float(bragg_raw.max()),
        "scaled_mean": float(bragg_scaled.mean()),
        "scaled_max": float(bragg_scaled.max()),
        "sqrt_spot_scale": sqrt_spot_scale,
        "calibration_inputs": extract_calibration_inputs(calibration),
        "diagnostics": {
            "masked_mse": diagnostics.get("masked_mse"),
            "chi_squared": diagnostics.get("chi_squared"),
        },
    }

    return bragg_raw, metrics


def compute_cross_path_ratios(
    stage_a_metrics: Dict[str, Any],
    reconstruction_metrics: Dict[str, Any],
    simulate_forward_once_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute cross-path ratios to identify discrepancies.

    Returns:
        Dict with pairwise raw/scaled ratios and interpretation flags
    """
    # Raw output ratios (before any post-run scaling)
    stage_a_raw = stage_a_metrics["raw_mean"]
    recon_raw = reconstruction_metrics["raw_mean"]
    mapping_raw = simulate_forward_once_metrics["raw_mean"]

    # Scaled output ratios (after post-run scaling)
    stage_a_scaled = stage_a_metrics["scaled_mean"]
    recon_scaled = reconstruction_metrics["scaled_mean"]
    mapping_scaled = simulate_forward_once_metrics["scaled_mean"]

    # Avoid division by zero
    def safe_ratio(a, b):
        return float(a / b) if b != 0 else float('inf')

    ratios = {
        "raw_output_ratios": {
            "stage_a_vs_reconstruction": safe_ratio(stage_a_raw, recon_raw),
            "stage_a_vs_mapping": safe_ratio(stage_a_raw, mapping_raw),
            "reconstruction_vs_mapping": safe_ratio(recon_raw, mapping_raw),
        },
        "scaled_output_ratios": {
            "stage_a_vs_reconstruction": safe_ratio(stage_a_scaled, recon_scaled),
            "stage_a_vs_mapping": safe_ratio(stage_a_scaled, mapping_scaled),
            "reconstruction_vs_mapping": safe_ratio(recon_scaled, mapping_scaled),
        },
        "interpretation": {
            "all_raw_match_within_10pct": (
                abs(safe_ratio(stage_a_raw, recon_raw) - 1.0) < 0.1
                and abs(safe_ratio(stage_a_raw, mapping_raw) - 1.0) < 0.1
                and abs(safe_ratio(recon_raw, mapping_raw) - 1.0) < 0.1
            ),
            "reconstruction_diverges_from_others": (
                abs(safe_ratio(stage_a_raw, mapping_raw) - 1.0) < 0.1
                and abs(safe_ratio(recon_raw, mapping_raw) - 1.0) > 0.1
            ),
        },
    }

    return ratios


def main():
    parser = argparse.ArgumentParser(description="Compare Stage A vs reconstruction vs simulate_forward_once outputs")
    parser.add_argument("--output", type=str, required=True, help="Output JSON path")
    parser.add_argument("--detector-size", type=str, default="small", help="Detector size variant (small, medium, large)")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu or cuda:0)")
    args = parser.parse_args()

    device_obj = torch.device(args.device)
    device_str = str(device_obj)
    dtype = torch.float32

    print("[ARCH-SIM-CONSTRUCTION-001] Intensity + Calibration Metrics Probe")
    print(f"Detector size: {args.detector_size}")
    print(f"Device: {device_str}")
    print()

    # ============================================================
    # 1. Load test fixture data
    # ============================================================
    print("[1/6] Loading test fixture data...")
    refgeom_dataload = load_test_fixture(args.detector_size)

    # Build mapping context to get HKL/calibration/inputs aligned
    mapping_context = build_mapping_stage_a_context(
        refgeom_dataload,
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

    print(f"  HKL grid shape: {hkl_grid.shape}")
    print(f"  n_panels: {len(refgeom_dataload.Expt.detector)}")
    if mapping_context.calibration:
        print(f"  Calibration loaded: {len(mapping_context.calibration)} keys")
    else:
        print("  Calibration: None")
    print()

    # ============================================================
    # 2. Run Stage A warm-cache path
    # ============================================================
    print("[2/6] Running Stage A warm-cache simulator...")
    bragg_stage_a_raw, stage_a_metrics = run_stage_a_path(
        refgeom_dataload,
        mapping_context,
        hkl_grid,
        hkl_metadata,
        device_obj,
        dtype,
    )
    print(f"  Raw output mean: {stage_a_metrics['raw_mean']:.6e}")
    print(f"  Scaled output mean: {stage_a_metrics['scaled_mean']:.6e}")
    print(f"  sqrt(spot_scale): {stage_a_metrics['sqrt_spot_scale']:.6e}")
    print(f"  log_scale_baseline: {stage_a_metrics['log_scale_baseline']:.6f}")
    print()

    # ============================================================
    # 3. Run reconstruction cold-path
    # ============================================================
    print("[3/6] Running reconstruction cold-path simulator...")
    bragg_recon_raw, reconstruction_metrics = run_reconstruction_path(
        refgeom_dataload,
        mapping_context,
        hkl_grid,
        hkl_metadata,
        device_obj,
        dtype,
    )
    print(f"  Raw output mean: {reconstruction_metrics['raw_mean']:.6e}")
    print(f"  Scaled output mean: {reconstruction_metrics['scaled_mean']:.6e}")
    print(f"  scale_factor (exp(log_scale_baseline)): {reconstruction_metrics['scale_factor']:.6e}")
    print(f"  sqrt(spot_scale): {reconstruction_metrics['sqrt_spot_scale']:.6e}")
    print()

    # ============================================================
    # 4. Run simulate_forward_once canonical mapping path
    # ============================================================
    print("[4/6] Running simulate_forward_once canonical mapping path...")
    bragg_mapping_raw, mapping_metrics = run_simulate_forward_once_path(
        refgeom_dataload,
        mapping_context,
        device_obj,
    )
    print(f"  Raw output mean: {mapping_metrics['raw_mean']:.6e}")
    print(f"  Scaled output mean: {mapping_metrics['scaled_mean']:.6e}")
    print(f"  sqrt(spot_scale): {mapping_metrics['sqrt_spot_scale']:.6e}")
    print()

    # ============================================================
    # 5. Compute cross-path ratios
    # ============================================================
    print("[5/6] Computing cross-path ratios...")
    ratios = compute_cross_path_ratios(
        stage_a_metrics,
        reconstruction_metrics,
        mapping_metrics,
    )
    print(f"  Raw stage_a/recon: {ratios['raw_output_ratios']['stage_a_vs_reconstruction']:.6e}")
    print(f"  Raw stage_a/mapping: {ratios['raw_output_ratios']['stage_a_vs_mapping']:.6e}")
    print(f"  Raw recon/mapping: {ratios['raw_output_ratios']['reconstruction_vs_mapping']:.6e}")
    print(f"  All raw outputs match within 10%? {ratios['interpretation']['all_raw_match_within_10pct']}")
    print()

    # ============================================================
    # 6. Save results
    # ============================================================
    print("[6/6] Saving results...")

    results = {
        "stage_a": stage_a_metrics,
        "reconstruction": reconstruction_metrics,
        "simulate_forward_once": mapping_metrics,
        "cross_path_ratios": ratios,
        "device": device_str,
        "dtype": str(dtype),
        "detector_size": args.detector_size,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"  Results saved to: {output_path}")
    print()

    # Write summary interpretation
    summary_path = output_path.parent / "summary.md"
    with open(summary_path, 'w') as f:
        f.write("# ARCH-SIM-CONSTRUCTION-001 Intensity + Calibration Metrics Summary\n\n")
        f.write("## Per-Path Results\n\n")
        f.write("### Stage A Warm-Cache Path\n\n")
        f.write(f"- **Raw output mean:** `{stage_a_metrics['raw_mean']:.6e}`\n")
        f.write(f"- **Scaled output mean:** `{stage_a_metrics['scaled_mean']:.6e}`\n")
        f.write(f"- **sqrt(spot_scale):** `{stage_a_metrics['sqrt_spot_scale']:.6e}`\n")
        f.write(f"- **log_scale_baseline:** `{stage_a_metrics['log_scale_baseline']:.6f}`\n")
        f.write(f"- **beam_flux:** `{stage_a_metrics['calibration_inputs']['beam_flux']}`\n")
        f.write(f"- **beam_exposure:** `{stage_a_metrics['calibration_inputs']['beam_exposure']}`\n")
        f.write(f"- **beamsize_mm:** `{stage_a_metrics['calibration_inputs']['beamsize_mm']}`\n\n")

        f.write("### Reconstruction Cold-Path\n\n")
        f.write(f"- **Raw output mean:** `{reconstruction_metrics['raw_mean']:.6e}`\n")
        f.write(f"- **Scaled output mean:** `{reconstruction_metrics['scaled_mean']:.6e}`\n")
        f.write(f"- **scale_factor (exp(log_scale_baseline)):** `{reconstruction_metrics['scale_factor']:.6e}`\n")
        f.write(f"- **sqrt(spot_scale):** `{reconstruction_metrics['sqrt_spot_scale']:.6e}`\n")
        f.write(f"- **log_scale_baseline:** `{reconstruction_metrics['log_scale_baseline']:.6f}`\n")
        f.write(f"- **beam_flux:** `{reconstruction_metrics['calibration_inputs']['beam_flux']}`\n")
        f.write(f"- **beam_exposure:** `{reconstruction_metrics['calibration_inputs']['beam_exposure']}`\n")
        f.write(f"- **beamsize_mm:** `{reconstruction_metrics['calibration_inputs']['beamsize_mm']}`\n\n")

        f.write("### simulate_forward_once Mapping Path\n\n")
        f.write(f"- **Raw output mean:** `{mapping_metrics['raw_mean']:.6e}`\n")
        f.write(f"- **Scaled output mean:** `{mapping_metrics['scaled_mean']:.6e}`\n")
        f.write(f"- **sqrt(spot_scale):** `{mapping_metrics['sqrt_spot_scale']:.6e}`\n")
        f.write(f"- **beam_flux:** `{mapping_metrics['calibration_inputs']['beam_flux']}`\n")
        f.write(f"- **beam_exposure:** `{mapping_metrics['calibration_inputs']['beam_exposure']}`\n")
        f.write(f"- **beamsize_mm:** `{mapping_metrics['calibration_inputs']['beamsize_mm']}`\n\n")

        f.write("## Cross-Path Ratios\n\n")
        f.write("### Raw Output Ratios (before post-run scaling)\n\n")
        f.write(f"- **Stage A / Reconstruction:** `{ratios['raw_output_ratios']['stage_a_vs_reconstruction']:.6e}`\n")
        f.write(f"- **Stage A / Mapping:** `{ratios['raw_output_ratios']['stage_a_vs_mapping']:.6e}`\n")
        f.write(f"- **Reconstruction / Mapping:** `{ratios['raw_output_ratios']['reconstruction_vs_mapping']:.6e}`\n\n")

        f.write("### Scaled Output Ratios (after post-run scaling)\n\n")
        f.write(f"- **Stage A / Reconstruction:** `{ratios['scaled_output_ratios']['stage_a_vs_reconstruction']:.6e}`\n")
        f.write(f"- **Stage A / Mapping:** `{ratios['scaled_output_ratios']['stage_a_vs_mapping']:.6e}`\n")
        f.write(f"- **Reconstruction / Mapping:** `{ratios['scaled_output_ratios']['reconstruction_vs_mapping']:.6e}`\n\n")

        f.write("## Interpretation\n\n")

        if ratios['interpretation']['all_raw_match_within_10pct']:
            f.write("**Verdict: All paths produce MATCHING raw outputs (within 10%)**\n\n")
            f.write("The simulator construction is consistent across all three paths. ")
            f.write("Any discrepancy in DB-AT-028/029 tests is due to post-run scaling logic ")
            f.write("(sqrt_spot_scale vs scale_factor application) or scale_factor derivation.\n\n")
            f.write("**Recommended next steps:**\n")
            f.write("1. Verify reconstruction applies correct post-run scaling (scale_factor = exp(log_scale_baseline) should equal sqrt(spot_scale) at zero delta)\n")
            f.write("2. Trace log_scale_baseline derivation in Stage A telemetry to confirm it equals log(sqrt(spot_scale))\n")
            f.write("3. If reconstruction scale_factor != sqrt(spot_scale), investigate telemetry extraction in reconstruction.py:215-247\n")
        elif ratios['interpretation']['reconstruction_diverges_from_others']:
            f.write("**Verdict: Reconstruction path DIVERGES from Stage A + Mapping**\n\n")
            f.write("Stage A and simulate_forward_once produce matching raw outputs, but reconstruction ")
            f.write("cold-path produces different magnitude. This indicates a simulator construction difference ")
            f.write("in create_unified_simulator factory when called from reconstruction helpers.\n\n")
            f.write("**Recommended next steps:**\n")
            f.write("1. Audit reconstruction.py:187-217 config construction (beam_config, crystal_config, detector_config)\n")
            f.write("2. Compare calibration metadata threading (beam_flux, beam_exposure, beamsize_mm, N_cells)\n")
            f.write("3. Verify spot_scale_override is passed correctly to create_unified_simulator\n")
            f.write("4. Check for oversample mismatch (should be 3 for all paths)\n")
        else:
            f.write("**Verdict: COMPLEX discrepancy pattern**\n\n")
            f.write("Raw output ratios do not fit simple match/diverge patterns. ")
            f.write("This suggests multiple overlapping issues (scaling + construction) or ")
            f.write("unexpected interactions between calibration parameters.\n\n")
            f.write("**Recommended next steps:**\n")
            f.write("1. Review calibration_inputs section above to identify missing/mismatched beam parameters\n")
            f.write("2. Add debug instrumentation to capture intermediate scaling values in all three paths\n")
            f.write("3. Escalate to architecture review with full metrics JSON for detailed analysis\n")

    print(f"  Summary written to: {summary_path}")
    print()
    print("[DONE] Intensity + calibration metrics comparison complete.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
