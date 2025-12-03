#!/usr/bin/env python
"""
Probe script for Stage-A scale alignment diagnostics.

This Tier-2 diagnostic script mimics the Stage-A smoke fixture setup to capture
masked/unmasked mean intensities, scale hints, and telemetry log-scale values
for both the zero-iteration mapping forward helper and reconstruction helper.

Purpose:
    Identify why DB-AT-028/029 still fail after the mask fix by comparing:
    - Raw simulator outputs (masked vs unmasked)
    - RefinementInputs.global_scale_hint
    - Telemetry log-scale values
    - Zero-iteration Bragg stack statistics

Usage:
    AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
    DBEX_SMOKE_DETECTOR_SIZE=small \
    DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
    KMP_DUPLICATE_LIB_OK=TRUE \
    NANOBRAGG_DISABLE_COMPILE=1 \
    python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_stage_a_scale_alignment.py \
      --detector-size small \
      --calibration-config sp.proc/calibration/config_torch_smoke_small.json \
      --device cpu \
      --out-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T010000Z/scale_probe

Outputs:
    - stage_a_scale_alignment.json: JSON summary with masked/unmasked means, scale ratios, telemetry
    - scale_probe_summary.md: Markdown summary of findings
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

# Add repo root to path for dbex imports
repo_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(repo_root))


def create_perturbed_geometry(crystal, detector, beam, seed=42, enable_detector_perturbation=False, detector_distance_offset_mm=0.25):
    """
    Create deterministically perturbed copies of crystal/detector/beam for Stage A/C smoke testing.

    Inlined from tests.dbex.test_torch_refine_smoke to avoid import issues.
    """
    from dxtbx.model import Crystal
    from cctbx import uctbx
    from scitbx.matrix import sqr
    import math

    # Extract baseline cell parameters
    base_cell = crystal.get_unit_cell().parameters()  # (a, b, c, alpha, beta, gamma)

    # Apply deterministic cell stretch
    perturbed_a = base_cell[0] * 1.02  # +2% on a-axis
    perturbed_b = base_cell[1] * 1.01  # +1% on b-axis
    perturbed_c = base_cell[2] * 1.01  # +1% on c-axis
    perturbed_alpha = base_cell[3]  # unchanged
    perturbed_beta = base_cell[4]   # unchanged
    perturbed_gamma = base_cell[5]  # unchanged

    # Create new crystal with perturbed cell
    perturbed_crystal = Crystal(
        real_space_a=crystal.get_real_space_vectors()[0],
        real_space_b=crystal.get_real_space_vectors()[1],
        real_space_c=crystal.get_real_space_vectors()[2],
        space_group=crystal.get_space_group()
    )

    # Set perturbed unit cell
    perturbed_uc = uctbx.unit_cell((perturbed_a, perturbed_b, perturbed_c,
                                     perturbed_alpha, perturbed_beta, perturbed_gamma))
    perturbed_crystal.set_unit_cell(perturbed_uc)

    # Apply small Z-axis rotation (+1.5° misorientation)
    misset_z_deg = 1.5
    misset_z_rad = misset_z_deg * (math.pi / 180.0)

    # Rotation matrix around Z-axis: R_z(θ)
    cos_z = math.cos(misset_z_rad)
    sin_z = math.sin(misset_z_rad)
    rotation_z = sqr([
        cos_z, -sin_z, 0.0,
        sin_z,  cos_z, 0.0,
        0.0,    0.0,   1.0
    ])

    # Apply rotation to U matrix
    U_tuple = perturbed_crystal.get_U()
    U = sqr(U_tuple)  # Convert to 3x3 matrix
    U_perturbed = rotation_z * U
    perturbed_crystal.set_U(U_perturbed)

    # Return perturbed crystal, original detector (no perturbation needed for this probe), and beam
    return perturbed_crystal, detector, beam


def main():
    parser = argparse.ArgumentParser(description="Stage-A scale alignment probe")
    parser.add_argument("--detector-size", choices=["small", "full"], default="small",
                        help="Detector size (small or full)")
    parser.add_argument("--calibration-config", type=str, required=True,
                        help="Path to calibration config (relative to repo root)")
    parser.add_argument("--device", type=str, default="cpu",
                        help="Torch device (cpu or cuda)")
    parser.add_argument("--out-dir", type=str, required=True,
                        help="Output directory for artifacts")
    args = parser.parse_args()

    # Resolve repo root
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    print(f"Repo root: {repo_root}")

    # Setup paths
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    calib_path = repo_root / args.calibration_config
    if not calib_path.exists():
        print(f"ERROR: Calibration config not found: {calib_path}")
        sys.exit(1)

    print(f"Loading calibration config: {calib_path}")

    # Import here to avoid early failures
    from argparse import Namespace
    from dbex.data_load import DataLoad
    from dbex.vis.mapping import build_mapping_stage_a_context
    from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry

    # Build smoke dataset paths (mirrors test_torch_refine_smoke.py fixture)
    if args.detector_size == "small":
        base = repo_root / "sp.proc" / "refGeom_small"
        expt_path = base / "refGeom_small.expt"
        refl_path = base / "refGeom_small.refl"
        mask_path = base / "refGeom_small_mask.pkl"
    else:
        expt_path = repo_root / "refGeom.expt"
        refl_path = repo_root / "refGeom.refl"
        mask_path = repo_root / "747_mask.pkl"

    # Check paths exist
    for p in [expt_path, refl_path, mask_path]:
        if not p.exists():
            print(f"ERROR: Required file not found: {p}")
            sys.exit(1)

    # Resolve HKL path (use refined MTZ when calibration exists)
    default_refined_mtz = repo_root / "sp.proc" / "calibration" / "smoke_refined_structure_factors.mtz"
    hkl_source_path = default_refined_mtz if default_refined_mtz.exists() else repo_root / "scaled.mtz"

    print(f"Experiment: {expt_path}")
    print(f"Reflections: {refl_path}")
    print(f"Mask: {mask_path}")
    print(f"HKL source: {hkl_source_path}")

    # Build DataLoad args (mirrors refgeom_dataload fixture)
    dataload_args = Namespace(
        exptName=str(expt_path),
        reflName=str(refl_path),
        exptIdx=0,
        maskFile=str(mask_path),
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
        hkl_source_path=str(hkl_source_path),
        calibration_config_path=str(calib_path),
    )

    print("\n=== Loading dataset via DataLoad ===")
    dataload = DataLoad(dataload_args)
    print(f"Loaded {dataload.data.shape[0]} panels")

    # Build mapping context (zero-iteration forward helper)
    print("\n=== Building mapping Stage-A context ===")
    mapping_ctx = build_mapping_stage_a_context(
        dataload,
        default_sigma_readout=3.0,
        device=args.device,
        apply_calibration_n_cells=True,
    )

    print(f"Mapping context built:")
    print(f"  - Inputs.global_scale_hint: {mapping_ctx.inputs.global_scale_hint}")
    print(f"  - Bragg stack shape: {mapping_ctx.bragg_zero_iter.shape}")
    print(f"  - sigma_floor_value: {mapping_ctx.sigma_floor_value}")

    # Compute masked and unmasked means for mapping path
    # bragg_zero_iter is numpy array already
    bragg_mapping = mapping_ctx.bragg_zero_iter
    # trusted_mask needs to be converted to numpy if it's a tensor
    trusted_mask = mapping_ctx.inputs.trusted_mask
    if hasattr(trusted_mask, 'cpu'):
        trusted_mask = trusted_mask.cpu().numpy()
    else:
        trusted_mask = np.asarray(trusted_mask)

    # Masked mean (only trusted pixels)
    bragg_mapping_masked_pixels = bragg_mapping[trusted_mask]
    bragg_mapping_masked_mean = float(np.mean(bragg_mapping_masked_pixels))
    bragg_mapping_masked_max = float(np.max(bragg_mapping_masked_pixels))

    # Unmasked mean (all pixels)
    bragg_mapping_unmasked_mean = float(np.mean(bragg_mapping))
    bragg_mapping_unmasked_max = float(np.max(bragg_mapping))

    print(f"\nMapping Bragg statistics:")
    print(f"  - Masked mean: {bragg_mapping_masked_mean:.4e} ADU")
    print(f"  - Masked max: {bragg_mapping_masked_max:.4e} ADU")
    print(f"  - Unmasked mean: {bragg_mapping_unmasked_mean:.4e} ADU")
    print(f"  - Unmasked max: {bragg_mapping_unmasked_max:.4e} ADU")
    print(f"  - Mask coverage: {np.sum(trusted_mask) / trusted_mask.size * 100:.1f}%")

    # Load calibration metadata to get spot_scale_override and log_scale_baseline
    with open(calib_path) as f:
        calib_config = json.load(f)

    # Handle nested config structure (new format)
    if "crystal" in calib_config:
        spot_scale_override = calib_config.get("crystal", {}).get("scale_override")
        N_cells = calib_config.get("crystal", {}).get("N_cells")
        log_scale_baseline = calib_config.get("crystal", {}).get("log_scale_baseline")
    else:
        # Fallback to flat structure (old format)
        spot_scale_override = calib_config.get("spot_scale_override")
        N_cells = calib_config.get("N_cells")
        log_scale_baseline = calib_config.get("log_scale_baseline")

    if "beam" in calib_config:
        beam_flux = calib_config.get("beam", {}).get("flux")
        beam_exposure = calib_config.get("beam", {}).get("exposure")
        beamsize_mm = calib_config.get("beam", {}).get("beamsize_mm")
    else:
        beam_flux = calib_config.get("beam_flux")
        beam_exposure = calib_config.get("beam_exposure")
        beamsize_mm = calib_config.get("beamsize_mm")

    print(f"\nCalibration metadata:")
    print(f"  - spot_scale_override: {spot_scale_override:.4e}" if spot_scale_override else "  - spot_scale_override: None")
    print(f"  - log_scale_baseline: {log_scale_baseline:.4f}" if log_scale_baseline else "  - log_scale_baseline: None")
    print(f"  - N_cells: {N_cells}")
    print(f"  - beam_flux: {beam_flux:.4e}" if beam_flux else "  - beam_flux: None")
    print(f"  - beam_exposure: {beam_exposure:.4f}" if beam_exposure else "  - beam_exposure: None")
    print(f"  - beamsize_mm: {beamsize_mm:.4f}" if beamsize_mm else "  - beamsize_mm: None")

    # Compute expected scale factors
    if spot_scale_override:
        sqrt_spot_scale = float(np.sqrt(spot_scale_override))
        print(f"  - sqrt(spot_scale_override): {sqrt_spot_scale:.4e}")
    else:
        sqrt_spot_scale = None

    if log_scale_baseline:
        scale_factor = float(np.exp(log_scale_baseline))
        print(f"  - exp(log_scale_baseline): {scale_factor:.4e}")
    else:
        scale_factor = None

    # Note: Full reconstruction path comparison would require complex setup.
    # For this diagnostic probe, we focus on mapping path outputs and calibration metadata.
    # The compare_simulator_outputs.py script handles the full reconstruction comparison.
    print("\n=== Reconstruction path comparison ===")
    print("Skipped in this probe - see compare_simulator_outputs.py for full reconstruction path analysis.")

    # Set placeholder values for JSON output
    bragg_recon_masked_mean = None
    bragg_recon_masked_max = None
    bragg_recon_unmasked_mean = None
    bragg_recon_unmasked_max = None
    mapping_recon_ratio_masked = None
    mapping_recon_ratio_unmasked = None

    # Build JSON summary
    summary = {
        "detector_size": args.detector_size,
        "calibration_config": str(calib_path),
        "device": args.device,
        "hkl_source": str(hkl_source_path),
        "calibration_metadata": {
            "spot_scale_override": spot_scale_override,
            "log_scale_baseline": log_scale_baseline,
            "N_cells": N_cells,
            "beam_flux": beam_flux,
            "beam_exposure": beam_exposure,
            "beamsize_mm": beamsize_mm,
            "sqrt_spot_scale": sqrt_spot_scale,
            "scale_factor": scale_factor,
        },
        "mapping_path": {
            "global_scale_hint": float(mapping_ctx.inputs.global_scale_hint),
            "bragg_masked_mean": bragg_mapping_masked_mean,
            "bragg_masked_max": bragg_mapping_masked_max,
            "bragg_unmasked_mean": bragg_mapping_unmasked_mean,
            "bragg_unmasked_max": bragg_mapping_unmasked_max,
            "sigma_floor_value": float(mapping_ctx.sigma_floor_value),
        },
        "reconstruction_path": {
            "bragg_masked_mean": bragg_recon_masked_mean,
            "bragg_masked_max": bragg_recon_masked_max,
            "bragg_unmasked_mean": bragg_recon_unmasked_mean,
            "bragg_unmasked_max": bragg_recon_unmasked_max,
        },
        "ratios": {
            "mapping_reconstruction_masked": mapping_recon_ratio_masked,
            "mapping_reconstruction_unmasked": mapping_recon_ratio_unmasked,
        },
        "mask_statistics": {
            "total_pixels": int(trusted_mask.size),
            "trusted_pixels": int(np.sum(trusted_mask)),
            "coverage_fraction": float(np.sum(trusted_mask) / trusted_mask.size),
        },
    }

    # Write JSON
    json_path = out_dir / "stage_a_scale_alignment.json"
    with open(json_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\n=== Wrote JSON summary: {json_path} ===")

    # Write Markdown summary
    md_path = out_dir / "scale_probe_summary.md"
    with open(md_path, 'w') as f:
        f.write("# Stage-A Scale Alignment Probe\n\n")
        f.write(f"**Detector size:** {args.detector_size}\n")
        f.write(f"**Calibration config:** `{args.calibration_config}`\n")
        f.write(f"**Device:** {args.device}\n")
        f.write(f"**HKL source:** `{hkl_source_path.name}`\n\n")

        f.write("## Calibration Metadata\n\n")
        f.write(f"- `spot_scale_override`: {spot_scale_override:.4e}\n" if spot_scale_override else "- `spot_scale_override`: None\n")
        f.write(f"- `log_scale_baseline`: {log_scale_baseline:.4f}\n" if log_scale_baseline else "- `log_scale_baseline`: None\n")
        f.write(f"- `N_cells`: {N_cells}\n")
        f.write(f"- `sqrt(spot_scale)`: {sqrt_spot_scale:.4e}\n" if sqrt_spot_scale else "- `sqrt(spot_scale)`: None\n")
        f.write(f"- `exp(log_scale_baseline)`: {scale_factor:.4e}\n\n" if scale_factor else "- `exp(log_scale_baseline)`: None\n\n")

        f.write("## Mapping Path (Zero-Iteration Forward Helper)\n\n")
        f.write(f"- **global_scale_hint**: {mapping_ctx.inputs.global_scale_hint:.4e}\n")
        f.write(f"- **Masked mean**: {bragg_mapping_masked_mean:.4e} ADU\n")
        f.write(f"- **Masked max**: {bragg_mapping_masked_max:.4e} ADU\n")
        f.write(f"- **Unmasked mean**: {bragg_mapping_unmasked_mean:.4e} ADU\n")
        f.write(f"- **Unmasked max**: {bragg_mapping_unmasked_max:.4e} ADU\n\n")

        f.write("## Reconstruction Path (Cold-Path Helper)\n\n")
        if bragg_recon_masked_mean is not None:
            f.write(f"- **Masked mean**: {bragg_recon_masked_mean:.4e} ADU\n")
            f.write(f"- **Masked max**: {bragg_recon_masked_max:.4e} ADU\n")
            f.write(f"- **Unmasked mean**: {bragg_recon_unmasked_mean:.4e} ADU\n")
            f.write(f"- **Unmasked max**: {bragg_recon_unmasked_max:.4e} ADU\n\n")
        else:
            f.write("*Skipped - see compare_simulator_outputs.py for full reconstruction analysis*\n\n")

        f.write("## Scale Alignment Ratios\n\n")
        if mapping_recon_ratio_masked is not None:
            f.write(f"- **Mapping/Reconstruction (masked)**: {mapping_recon_ratio_masked:.6f}\n")
            f.write(f"- **Mapping/Reconstruction (unmasked)**: {mapping_recon_ratio_unmasked:.6f}\n\n")
        else:
            f.write("*Not computed in this probe*\n\n")

        f.write("## Interpretation\n\n")
        if mapping_recon_ratio_masked is not None and abs(mapping_recon_ratio_masked - 1.0) < 0.02:
            f.write("✅ **PASS**: Mapping and reconstruction paths produce aligned masked means (within 2%).\n")
        elif mapping_recon_ratio_masked is not None:
            f.write(f"❌ **FAIL**: Mapping and reconstruction masked means diverge by {abs(mapping_recon_ratio_masked - 1.0) * 100:.1f}%.\n")
            if mapping_recon_ratio_masked < 0.9:
                f.write("   - Reconstruction outputs are systematically higher than mapping.\n")
            elif mapping_recon_ratio_masked > 1.1:
                f.write("   - Reconstruction outputs are systematically lower than mapping.\n")
        else:
            f.write("*Reconstruction comparison not performed - this probe focuses on mapping path diagnostics and calibration metadata.*\n")

        f.write("\n---\n")
        f.write(f"Artifacts: `{json_path.name}`\n")

    print(f"=== Wrote Markdown summary: {md_path} ===")
    print(f"\n=== Probe complete ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())
