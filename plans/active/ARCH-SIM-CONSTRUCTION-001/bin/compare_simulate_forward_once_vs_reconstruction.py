#!/usr/bin/env python3
"""
ARCH-SIM-CONSTRUCTION-001 Phase C.3 Diagnostic Probe

Compare raw simulator outputs between simulate_forward_once() and reconstruction helper paths
to isolate the 23,400× discrepancy source in DB-AT-028/029.

This probe:
1. Loads the exact DB-AT-028 test configuration
2. Path A: Calls simulate_forward_once() and captures raw+scaled output
3. Path B: Builds a simulator via create_unified_simulator() (cold path) and captures raw+scaled output
4. Compares the outputs at each stage to determine where the discrepancy occurs

Evidence-only probe. No production code modifications.
"""

import json
import sys
from pathlib import Path
import numpy as np
import torch

# Add project root to path
# Script is at plans/active/ARCH-SIM-CONSTRUCTION-001/bin/, so go up 4 levels
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from dbex.nanobrag_bridge import simulate_forward_once, build_structure_factor_grid
from dbex.vis.mapping import build_mapping_stage_a_context
from dbex.refinement.helpers import create_unified_simulator
from dbex.refinement.config_factories import create_detector_config, create_beam_config, create_crystal_config
from dbex.data_load import DataLoad


def load_test_configuration():
    """
    Load the exact configuration from the DB-AT-028 test fixture.

    Returns:
        dict: Configuration containing detector, beam, crystal, HKL grid, calibration, inputs
    """
    print("Loading test configuration (refgeom_dataload fixture equivalent)...")

    # Use same dataset paths as smoke tests (small detector default)
    smoke_data_dir = project_root / "sp.proc" / "refGeom_small"

    # Check for calibration config (smoke default)
    calib_path = project_root / "sp.proc" / "calibration" / "config_torch_smoke.json"
    calibration_config_path = str(calib_path) if calib_path.exists() else None

    # Resolve HKL path (refined MTZ when calibration exists, else scaled.mtz)
    refined_mtz = project_root / "sp.proc" / "calibration" / "smoke_refined_structure_factors.mtz"
    scaled_mtz = project_root / "scaled.mtz"
    if refined_mtz.exists():
        hkl_source_path = refined_mtz
    else:
        hkl_source_path = scaled_mtz

    # Build args namespace following refgeom_dataload fixture pattern
    from argparse import Namespace
    args = Namespace(
        exptName=(smoke_data_dir / "refGeom_small.expt").as_posix(),
        reflName=(smoke_data_dir / "refGeom_small.refl").as_posix(),
        exptIdx=0,
        maskFile=(smoke_data_dir / "refGeom_small_mask.pkl").as_posix(),
        mtzFile=str(project_root / "scaled.mtz"),
        mtzCol="F,SIGF",
        hkl_source_path=str(hkl_source_path),
        calibration_config_path=calibration_config_path,
        force_sigma_readout=3.0,  # Match smoke test default
        device="cpu",
    )

    # Load via DataLoad
    refgeom_dataload = DataLoad(args)

    # Build mapping context (same as stage_a_smoke_result fixture)
    device = "cpu"
    device_obj = torch.device(device)

    mapping_context = build_mapping_stage_a_context(
        refgeom_dataload,
        default_sigma_readout=3.0,
        device=device,
        apply_calibration_n_cells=True,
    )

    # Build HKL grid from mapping context
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=mapping_context.hkl_indices,
        amplitudes=mapping_context.hkl_amplitudes,
        device=device_obj,
        halo=True,
    )

    # Extract calibration metadata
    calibration = mapping_context.calibration or {}
    spot_scale_override = float(calibration.get("spot_scale_override", 1.0))
    sqrt_spot_scale = np.sqrt(spot_scale_override)

    # Use baseline geometry (before perturbation)
    baseline_crystal = refgeom_dataload.Expt.crystal
    baseline_detector = refgeom_dataload.Expt.detector
    baseline_beam = refgeom_dataload.Expt.beam

    print(f"  detector: {len(baseline_detector)} panels")
    print(f"  beam wavelength: {baseline_beam.get_wavelength():.6f} Å")
    print(f"  HKL reflections: {len(mapping_context.hkl_indices)}")
    print(f"  spot_scale_override: {spot_scale_override:.6e}")
    print(f"  sqrt(spot_scale): {sqrt_spot_scale:.6e}")

    return {
        "detector": baseline_detector,
        "beam": baseline_beam,
        "crystal": baseline_crystal,
        "experiment": refgeom_dataload.Expt,
        "hkl_grid": hkl_grid,
        "hkl_metadata": hkl_metadata,
        "hkl_indices": mapping_context.hkl_indices,
        "hkl_amplitudes": mapping_context.hkl_amplitudes,
        "calibration": calibration,
        "spot_scale_override": spot_scale_override,
        "sqrt_spot_scale": sqrt_spot_scale,
        "inputs": mapping_context.inputs,
        "device": device,
    }


def run_path_a_simulate_forward_once(config):
    """
    Path A: Call simulate_forward_once() with the test config.

    NOTE: simulate_forward_once() already applies sqrt(spot_scale) internally at line 1435,
    so the returned bragg is scaled. We also capture the raw output before sqrt scaling
    by dividing by sqrt_spot_scale (lines 1442-1444).

    Returns:
        dict: {"raw_mean": float, "raw_max": float, "scaled_mean": float, "scaled_max": float}
    """
    print("\n=== Path A: simulate_forward_once() ===")

    bragg, diagnostics = simulate_forward_once(
        inputs=config["inputs"],
        detector=config["detector"],
        beam=config["beam"],
        crystal=config["crystal"],
        experiment=config["experiment"],
        hkl_indices=config["hkl_indices"],
        hkl_amplitudes=config["hkl_amplitudes"],
        spot_scale_override=config["spot_scale_override"],
        calibration=config["calibration"],
        device=config["device"],
    )

    # The returned bragg is ALREADY scaled by sqrt(spot_scale)
    # To get raw output, divide by sqrt(spot_scale)
    sqrt_spot_scale = config["sqrt_spot_scale"]
    bragg_raw = bragg / sqrt_spot_scale if sqrt_spot_scale != 0.0 else bragg

    raw_mean = float(bragg_raw.mean())
    raw_max = float(bragg_raw.max())
    scaled_mean = float(bragg.mean())
    scaled_max = float(bragg.max())

    print(f"  Raw output (before sqrt): mean={raw_mean:.6e}, max={raw_max:.6e}")
    print(f"  Scaled output (after sqrt): mean={scaled_mean:.6e}, max={scaled_max:.6e}")
    print(f"  Scaling factor applied: {sqrt_spot_scale:.6e}")

    return {
        "raw_mean": raw_mean,
        "raw_max": raw_max,
        "scaled_mean": scaled_mean,
        "scaled_max": scaled_max,
    }


def run_path_b_reconstruction_helper(config):
    """
    Path B: Build a simulator using create_unified_simulator() (cold path)
    and capture raw and scaled outputs.

    This replicates the reconstruction helper pattern:
    1. Build simulator via factory
    2. Run simulator to get raw output
    3. Apply sqrt(spot_scale) manually
    4. Apply scale_factor = exp(log_scale_baseline + delta) as reconstruction does

    Returns:
        dict: {
            "raw_mean": float, "raw_max": float,
            "after_sqrt_mean": float, "after_sqrt_max": float,
            "after_scalefactor_mean": float, "after_scalefactor_max": float,
            "log_scale_baseline": float, "scale_factor": float
        }
    """
    print("\n=== Path B: Reconstruction Helper (Cold Path) ===")

    # Use first panel only for comparison
    detector = config["detector"]
    beam = config["beam"]
    crystal = config["crystal"]
    panel = detector[0]

    # Create configs
    detector_config = create_detector_config(
        panel=panel,
        beam=beam,
        trusted_mask=config["inputs"].trusted_mask[0]
    )

    beam_config = create_beam_config(
        beam=beam,
        flux=config["calibration"].get("beam_flux"),
        exposure=config["calibration"].get("exposure_s"),
        beamsize_mm=config["calibration"].get("beamsize_mm"),
    )

    crystal_config, _ = create_crystal_config(crystal=crystal, experiment=config["experiment"])

    # Build simulator via factory (cold path)
    simulator, _, sqrt_scale_value, _ = create_unified_simulator(
        detector_config=detector_config,
        crystal_config=crystal_config,
        beam_config=beam_config,
        hkl_grid=config["hkl_grid"],
        hkl_metadata=config["hkl_metadata"],
        mask_array=detector_config.mask_array,
        spot_scale_override=config["spot_scale_override"],
        device=config["device"],
        dtype=torch.float32,
        calibration_metadata=config["calibration"],
    )

    print(f"  Factory returned sqrt_scale_value: {sqrt_scale_value:.6e}")

    # Run simulator to get raw output
    bragg_panel_torch = simulator.run()
    bragg_panel = bragg_panel_torch.cpu().detach().numpy().astype(np.float32)

    raw_mean = float(bragg_panel.mean())
    raw_max = float(bragg_panel.max())

    print(f"  Raw simulator output: mean={raw_mean:.6e}, max={raw_max:.6e}")

    # Apply sqrt(spot_scale) manually (matching simulate_forward_once pattern)
    bragg_after_sqrt = bragg_panel * sqrt_scale_value
    after_sqrt_mean = float(bragg_after_sqrt.mean())
    after_sqrt_max = float(bragg_after_sqrt.max())

    print(f"  After sqrt multiplication: mean={after_sqrt_mean:.6e}, max={after_sqrt_max:.6e}")

    # Now apply scale_factor as reconstruction helper does
    # log_scale_baseline = log(sqrt(spot_scale_override)) per Priority 2 path
    spot_scale_override = config["spot_scale_override"]
    log_scale_baseline = np.log(np.sqrt(spot_scale_override))

    # For this probe, assume delta=0 (no refinement adjustment)
    delta = 0.0
    scale_factor = np.exp(log_scale_baseline + delta)

    print(f"  log_scale_baseline = log(sqrt(spot_scale)): {log_scale_baseline:.6f}")
    print(f"  scale_factor = exp(log_scale_baseline): {scale_factor:.6e}")

    # Apply scale_factor to raw output (as reconstruction helper does)
    bragg_after_scalefactor = bragg_panel * scale_factor
    after_scalefactor_mean = float(bragg_after_scalefactor.mean())
    after_scalefactor_max = float(bragg_after_scalefactor.max())

    print(f"  After scale_factor multiplication: mean={after_scalefactor_mean:.6e}, max={after_scalefactor_max:.6e}")

    return {
        "raw_mean": raw_mean,
        "raw_max": raw_max,
        "after_sqrt_mean": after_sqrt_mean,
        "after_sqrt_max": after_sqrt_max,
        "after_scalefactor_mean": after_scalefactor_mean,
        "after_scalefactor_max": after_scalefactor_max,
        "log_scale_baseline": float(log_scale_baseline),
        "scale_factor": float(scale_factor),
        "sqrt_scale_value": float(sqrt_scale_value),
    }


def compare_results(path_a, path_b, config):
    """
    Compare the results and determine where the discrepancy occurs.

    Returns:
        dict: Comparison metrics and verdict
    """
    print("\n=== Comparison ===")

    # Compare raw outputs
    raw_ratio = path_a["raw_mean"] / path_b["raw_mean"] if path_b["raw_mean"] != 0 else float('inf')
    print(f"  Raw output ratio (A/B): {raw_ratio:.2f}")

    # Compare scaled outputs
    scaled_ratio = path_a["scaled_mean"] / path_b["after_sqrt_mean"] if path_b["after_sqrt_mean"] != 0 else float('inf')
    print(f"  Scaled output ratio (A after sqrt / B after sqrt): {scaled_ratio:.2f}")

    # Compare reconstruction scale_factor approach
    # Path A scaled = raw * sqrt(spot_scale)
    # Path B with scale_factor = raw * exp(log_scale_baseline) = raw * sqrt(spot_scale)
    # These SHOULD be identical if everything is correct

    scalefactor_vs_sqrt_ratio = path_b["after_scalefactor_mean"] / path_b["after_sqrt_mean"] if path_b["after_sqrt_mean"] != 0 else float('inf')
    print(f"  scale_factor vs sqrt ratio (B): {scalefactor_vs_sqrt_ratio:.2f}")

    # Determine verdict
    verdict_lines = []

    if abs(raw_ratio - 1.0) > 0.5:
        verdict_lines.append(f"⚠️  RAW SIMULATOR OUTPUTS DIFFER by {raw_ratio:.2f}×")
        verdict_lines.append("   → Simulators are constructed differently (config/calibration mismatch)")
    else:
        verdict_lines.append(f"✓  Raw simulator outputs MATCH within {abs(raw_ratio - 1.0)*100:.1f}%")

    if abs(scaled_ratio - 1.0) > 0.5:
        verdict_lines.append(f"⚠️  SCALED OUTPUTS DIFFER by {scaled_ratio:.2f}×")
        verdict_lines.append("   → Post-run scaling logic differs between paths")
    else:
        verdict_lines.append(f"✓  Scaled outputs MATCH within {abs(scaled_ratio - 1.0)*100:.1f}%")

    if abs(scalefactor_vs_sqrt_ratio - 1.0) > 0.01:
        verdict_lines.append(f"⚠️  scale_factor ≠ sqrt(spot_scale) (ratio={scalefactor_vs_sqrt_ratio:.6f})")
        verdict_lines.append("   → log_scale_baseline derivation may not equal log(sqrt(spot_scale))")
    else:
        verdict_lines.append(f"✓  scale_factor = sqrt(spot_scale) (ratio={scalefactor_vs_sqrt_ratio:.6f})")

    # Check if bragg_before (0.239) vs bragg_after (1.025e-05) discrepancy is explained
    # Expected: bragg_before should match path_a["scaled_mean"]
    # bragg_after should match path_b["after_scalefactor_mean"]

    bragg_before_expected = 0.239  # From DB-AT-028 metrics
    bragg_after_expected = 1.025e-05  # From DB-AT-028 metrics

    path_a_vs_before = path_a["scaled_mean"] / bragg_before_expected if bragg_before_expected != 0 else float('inf')
    path_b_vs_after = path_b["after_scalefactor_mean"] / bragg_after_expected if bragg_after_expected != 0 else float('inf')

    print(f"\n  Path A (simulate_forward_once) vs bragg_before (0.239): {path_a_vs_before:.2f}×")
    print(f"  Path B (reconstruction) vs bragg_after (1.025e-05): {path_b_vs_after:.2f}×")

    if abs(path_a_vs_before - 1.0) < 0.2 and abs(path_b_vs_after - 1.0) < 0.2:
        verdict_lines.append(f"\n✓  BOTH PATHS REPRODUCE EXPECTED OUTPUTS")
        verdict_lines.append(f"   Path A matches bragg_before within {abs(path_a_vs_before-1.0)*100:.1f}%")
        verdict_lines.append(f"   Path B matches bragg_after within {abs(path_b_vs_after-1.0)*100:.1f}%")
        verdict_lines.append(f"   → The 23,400× discrepancy is due to scale_factor NOT including sqrt(spot_scale)")

    verdict = "\n".join(verdict_lines)
    print(f"\n{verdict}")

    return {
        "raw_ratio": raw_ratio,
        "scaled_ratio": scaled_ratio,
        "scalefactor_vs_sqrt_ratio": scalefactor_vs_sqrt_ratio,
        "path_a_vs_bragg_before": path_a_vs_before,
        "path_b_vs_bragg_after": path_b_vs_after,
        "verdict": verdict,
    }


def main():
    """Run the diagnostic probe."""
    print("="*80)
    print("ARCH-SIM-CONSTRUCTION-001 Phase C.3 Diagnostic Probe")
    print("Compare simulate_forward_once() vs reconstruction helper paths")
    print("="*80)

    # Load configuration
    config = load_test_configuration()

    # Run Path A
    path_a = run_path_a_simulate_forward_once(config)

    # Run Path B
    path_b = run_path_b_reconstruction_helper(config)

    # Compare
    comparison = compare_results(path_a, path_b, config)

    # Build output JSON
    output = {
        "spot_scale_override": config["spot_scale_override"],
        "sqrt_spot_scale": config["sqrt_spot_scale"],
        "log_scale_baseline": path_b["log_scale_baseline"],
        "path_a_raw_mean": path_a["raw_mean"],
        "path_a_raw_max": path_a["raw_max"],
        "path_a_scaled_mean": path_a["scaled_mean"],
        "path_a_scaled_max": path_a["scaled_max"],
        "path_b_raw_mean": path_b["raw_mean"],
        "path_b_raw_max": path_b["raw_max"],
        "path_b_scaled_mean": path_b["after_sqrt_mean"],
        "path_b_scaled_max": path_b["after_sqrt_max"],
        "path_b_scalefactor_mean": path_b["after_scalefactor_mean"],
        "path_b_scalefactor_max": path_b["after_scalefactor_max"],
        "raw_ratio": comparison["raw_ratio"],
        "scaled_ratio": comparison["scaled_ratio"],
        "scalefactor_vs_sqrt_ratio": comparison["scalefactor_vs_sqrt_ratio"],
        "verdict": comparison["verdict"],
    }

    # Write JSON
    artifacts_dir = project_root / "plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T220000Z"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    json_path = artifacts_dir / "simulation_comparison.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Results written to {json_path}")

    # Write summary
    summary_path = artifacts_dir / "summary.md"
    with open(summary_path, "w") as f:
        f.write("# ARCH-SIM-CONSTRUCTION-001 Phase C.3 Probe Results\n\n")
        f.write("## Configuration\n\n")
        f.write(f"- `spot_scale_override`: {config['spot_scale_override']:.6e}\n")
        f.write(f"- `sqrt(spot_scale)`: {config['sqrt_spot_scale']:.6e}\n")
        f.write(f"- `log_scale_baseline`: {path_b['log_scale_baseline']:.6f}\n\n")
        f.write("## Path A: simulate_forward_once()\n\n")
        f.write(f"- Raw output (before sqrt): mean={path_a['raw_mean']:.6e}, max={path_a['raw_max']:.6e}\n")
        f.write(f"- Scaled output (after sqrt): mean={path_a['scaled_mean']:.6e}, max={path_a['scaled_max']:.6e}\n\n")
        f.write("## Path B: Reconstruction Helper (Cold Path)\n\n")
        f.write(f"- Raw simulator output: mean={path_b['raw_mean']:.6e}, max={path_b['raw_max']:.6e}\n")
        f.write(f"- After sqrt multiplication: mean={path_b['after_sqrt_mean']:.6e}, max={path_b['after_sqrt_max']:.6e}\n")
        f.write(f"- After scale_factor: mean={path_b['after_scalefactor_mean']:.6e}, max={path_b['after_scalefactor_max']:.6e}\n\n")
        f.write("## Comparison\n\n")
        f.write(f"- Raw output ratio (A/B): {comparison['raw_ratio']:.2f}\n")
        f.write(f"- Scaled output ratio (A/B): {comparison['scaled_ratio']:.2f}\n")
        f.write(f"- scale_factor vs sqrt ratio: {comparison['scalefactor_vs_sqrt_ratio']:.6f}\n\n")
        f.write("## Verdict\n\n")
        f.write(f"{comparison['verdict']}\n\n")
        f.write("## Recommended Fix\n\n")

        # Determine recommended fix based on results
        if abs(comparison["scalefactor_vs_sqrt_ratio"] - 1.0) < 0.01:
            f.write("Since `scale_factor = exp(log_scale_baseline)` already equals `sqrt(spot_scale)`, ")
            f.write("the reconstruction helper should:\n\n")
            f.write("1. **NOT** multiply by `sqrt(spot_scale)` separately (would cause double application)\n")
            f.write("2. Use `bragg_scaled = bragg_panel * scale_factor` only\n\n")
            f.write("The current code at `dbex/refinement/reconstruction.py:239` should keep only `scale_factor` ")
            f.write("and remove any explicit `* sqrt_spot_scale` multiplication.\n")
        else:
            f.write("⚠️  `scale_factor` does NOT equal `sqrt(spot_scale)`. Further investigation needed.\n")

    print(f"✓ Summary written to {summary_path}")
    print("\n" + "="*80)
    print("Probe complete. Review artifacts for analysis.")
    print("="*80)


if __name__ == "__main__":
    main()
