#!/usr/bin/env python
"""
Debug probe comparing Stage A warm-cache vs reconstruction cold-path simulator raw outputs.

ARCH-SIM-CONSTRUCTION-001 Phase C.2 (evidence collection loop i=452)

Purpose:
    Isolate whether the sqrt(spot_scale) discrepancy originates from:
    1. Simulator construction differences (warm vs cold path embed different scalings)
    2. Post-run scaling application logic (both simulators match, scaling bug)

Strategy:
    - Build simulators via both paths using identical configs
    - Run simulators and compare RAW outputs (before any scaling)
    - Compute ratio to diagnose discrepancy magnitude

Expected outcomes:
    - Ratio ≈ 1.0: Simulators match; bug is in reconstruction scaling application
    - Ratio ≈ sqrt(spot_scale) ≈ 5.57e8: Simulators differ; warm-cache path embeds calibration

Findings Applied:
    - SCALE-002: sqrt(spot_scale) post-run application
    - ARCH-FACTORY-001: Unified factory contract
    - GRADIENT-004: Device/dtype neutrality
"""

import argparse
import json
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
from dbex.refinement.config_factories import create_beam_config, create_crystal_config, create_detector_config
from dbex.refinement.helpers import create_unified_simulator


def load_test_fixture():
    """
    Load refgeom_dataload fixture data following test_stage_a_smoke_parity.py pattern.

    Returns:
        DataLoad object with Expt, bbox, trusted_mask, calibration_path
    """
    # Use same dataset paths as smoke tests (small detector default)
    # Script is at plans/active/.../bin/, so go up 5 levels to reach repo root
    repo_root_path = Path(__file__).parent.parent.parent.parent.parent
    smoke_data_dir = repo_root_path / "sp.proc" / "refGeom_small"

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
        exptName=(smoke_data_dir / "refGeom_small.expt").as_posix(),
        reflName=(smoke_data_dir / "refGeom_small.refl").as_posix(),
        exptIdx=0,
        maskFile=(smoke_data_dir / "refGeom_small_mask.pkl").as_posix(),
        mtzFile=str(repo_root_path / "scaled.mtz"),
        mtzCol="F,SIGF",
        hkl_source_path=str(hkl_source_path),
        calibration_config_path=calibration_config_path,
    )

    # Load via DataLoad
    loader = DataLoad(args)
    return loader


def main():
    parser = argparse.ArgumentParser(description="Compare Stage A vs reconstruction simulator outputs")
    parser.add_argument("--output", type=str, required=True, help="Output JSON path")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu or cuda:0)")
    args = parser.parse_args()

    device_obj = torch.device(args.device)
    device_str = str(device_obj)
    dtype = torch.float32

    print("[ARCH-SIM-CONSTRUCTION-001] Simulator Output Comparison Probe")
    print(f"Device: {device_str}")
    print()

    # ============================================================
    # 1. Load test fixture data
    # ============================================================
    print("[1/5] Loading test fixture data...")
    refgeom_dataload = load_test_fixture()

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

    # Extract calibration metadata
    spot_scale_override = 1.0
    if mapping_context.calibration:
        spot_scale_override = float(mapping_context.calibration.get("spot_scale_override", 1.0))
    sqrt_spot_scale = float(np.sqrt(spot_scale_override))

    baseline_detector = refgeom_dataload.Expt.detector
    baseline_beam = refgeom_dataload.Expt.beam
    baseline_crystal = refgeom_dataload.Expt.crystal
    trusted_mask = refgeom_dataload.trusted_mask

    print(f"  spot_scale_override: {spot_scale_override:.6e}")
    print(f"  sqrt(spot_scale_override): {sqrt_spot_scale:.6e}")
    print(f"  HKL grid shape: {hkl_grid.shape}")
    print(f"  n_panels: {len(baseline_detector)}")
    print()

    # ============================================================
    # 2. Build Stage A warm-cache simulators
    # ============================================================
    print("[2/5] Building Stage A warm-cache simulators...")

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
        calibration_metadata=mapping_context.calibration,
        log_scale_baseline=None,
        apply_calibration_n_cells=True,
    )

    # Extract first panel simulator
    stage_a_simulator = stage_a_ctx.simulators[0]

    # Run Stage A simulator
    bragg_stage_a_raw = stage_a_simulator.run()
    bragg_stage_a_mean = bragg_stage_a_raw.mean().item()
    bragg_stage_a_max = bragg_stage_a_raw.max().item()

    print(f"  Stage A simulator[0] raw output mean: {bragg_stage_a_mean:.6e}")
    print(f"  Stage A simulator[0] raw output max: {bragg_stage_a_max:.6e}")
    print()

    # ============================================================
    # 3. Build reconstruction cold-path simulator
    # ============================================================
    print("[3/5] Building reconstruction cold-path simulator...")

    # Extract first panel
    panel_0 = baseline_detector[0]

    # Build configs (matching reconstruction.py:187-206)
    beam_flux = None
    beam_exposure = None
    beamsize_mm = None
    if mapping_context.calibration:
        beam_flux = mapping_context.calibration.get("beam_flux")
        beam_exposure = mapping_context.calibration.get("beam_exposure")
        beamsize_mm = mapping_context.calibration.get("beamsize_mm")

    beam_config = create_beam_config(baseline_beam, flux=beam_flux, exposure=beam_exposure, beamsize_mm=beamsize_mm)

    # Build crystal config (matching stage_a_utils.py:272 with apply_n_cells=True)
    N_cells = mapping_context.calibration.get("N_cells") if mapping_context.calibration else None
    crystal_config, _ = create_crystal_config(baseline_crystal, None, N_cells=N_cells, apply_n_cells=True)

    detector_config = create_detector_config(panel_0, beam=baseline_beam)

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
        calibration_metadata=mapping_context.calibration,
    )
    simulator_recon.interpolate = False  # Match Stage A

    # Run reconstruction simulator
    bragg_recon_raw = simulator_recon.run()
    bragg_recon_mean = bragg_recon_raw.mean().item()
    bragg_recon_max = bragg_recon_raw.max().item()

    print(f"  Reconstruction simulator raw output mean: {bragg_recon_mean:.6e}")
    print(f"  Reconstruction simulator raw output max: {bragg_recon_max:.6e}")
    print()

    # ============================================================
    # 4. Compare outputs
    # ============================================================
    print("[4/5] Comparing simulator outputs...")

    ratio = bragg_stage_a_mean / bragg_recon_mean if bragg_recon_mean != 0 else float('inf')
    match_within_1pct = abs(ratio - 1.0) < 0.01
    match_sqrt_scale = abs(ratio - sqrt_spot_scale) / sqrt_spot_scale < 0.01 if sqrt_spot_scale > 0 else False

    print(f"  Ratio (Stage A / Reconstruction): {ratio:.6e}")
    print(f"  Match within 1% of 1.0? {match_within_1pct}")
    print(f"  Match within 1% of sqrt(spot_scale)? {match_sqrt_scale}")
    print()

    # ============================================================
    # 5. Save results
    # ============================================================
    print("[5/5] Saving results...")

    results = {
        "bragg_stage_a_mean": bragg_stage_a_mean,
        "bragg_stage_a_max": bragg_stage_a_max,
        "bragg_recon_mean": bragg_recon_mean,
        "bragg_recon_max": bragg_recon_max,
        "ratio": ratio,
        "spot_scale_override": spot_scale_override,
        "sqrt_spot_scale": sqrt_spot_scale,
        "match_within_1pct": match_within_1pct,
        "match_sqrt_scale": match_sqrt_scale,
        "device": device_str,
        "dtype": str(dtype),
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
        f.write("# ARCH-SIM-CONSTRUCTION-001 Simulator Output Comparison Summary\n\n")
        f.write("## Results\n\n")
        f.write(f"- **Stage A warm-cache simulator raw output mean:** `{bragg_stage_a_mean:.6e}`\n")
        f.write(f"- **Reconstruction cold-path simulator raw output mean:** `{bragg_recon_mean:.6e}`\n")
        f.write(f"- **Ratio (Stage A / Reconstruction):** `{ratio:.6e}`\n")
        f.write(f"- **spot_scale_override:** `{spot_scale_override:.6e}`\n")
        f.write(f"- **sqrt(spot_scale_override):** `{sqrt_spot_scale:.6e}`\n\n")

        f.write("## Interpretation\n\n")
        if match_within_1pct:
            f.write("**Verdict: Simulators MATCH (scaling bug)**\n\n")
            f.write("Both simulators produce the same raw output magnitude. The discrepancy observed in ")
            f.write("DB-AT-028/029 is due to incorrect scaling application in reconstruction.py, NOT ")
            f.write("a simulator construction difference.\n\n")
            f.write("**Recommended fix:** Review reconstruction.py scaling logic (lines 226-252). ")
            f.write("The scale_factor application may be incorrect or missing.\n")
        elif match_sqrt_scale:
            f.write("**Verdict: Simulators DIFFER by sqrt(spot_scale) (construction bug)**\n\n")
            f.write("Stage A warm-cache simulators produce outputs that are ~sqrt(spot_scale) times larger ")
            f.write("than reconstruction cold-path simulators. This indicates that _build_stage_a_context ")
            f.write("embeds calibration scaling that create_unified_simulator does not.\n\n")
            f.write("**Recommended fix:** Audit _build_stage_a_context (stage_a_utils.py:177-400) to identify ")
            f.write("where sqrt(spot_scale) is being embedded in the simulator construction. Either:\n")
            f.write("  1. Remove the embedded scaling from Stage A (breaking change), OR\n")
            f.write("  2. Add equivalent scaling to create_unified_simulator factory (spec change).\n")
        else:
            f.write("**Verdict: UNEXPECTED ratio**\n\n")
            f.write(f"The ratio ({ratio:.6e}) does not match 1.0 or sqrt(spot_scale) ({sqrt_spot_scale:.6e}). ")
            f.write("This suggests a more complex issue than simple double/missing sqrt application.\n\n")
            f.write("**Recommended action:** Escalate to architecture review. The discrepancy magnitude ")
            f.write("does not align with the current hypothesis.\n")

    print(f"  Summary written to: {summary_path}")
    print()
    print("[DONE] Simulator comparison complete.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
