#!/usr/bin/env python
"""
Probe script for square lattice (Na·Nb·Nc)² scaling validation.

ARCH-SIM-CONSTRUCTION-001: Simulator Construction Convention Alignment
SIM-CONSTR-PARTIALITY-001: SQUARE lattice must emit weights ∝ (Na·Nb·Nc)²

This thin wrapper instantiates nanobrag_torch.Simulator twice:
1. Base case: N_cells=(1,1,1)
2. Scaled case: N_cells=(Na,Nb,Nc)

With a 1×1 detector, single phi/mosaic, and configurable oversample.
Captures intensities, (F_cell·F_latt)², Lorentz/polarization, and observed ratio.

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
    python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py \
      --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z \
      --n-cells 41 29 32 \
      --oversample 13 \
      --phi-count 1 \
      --mosaic-count 1 \
      --spixels 1 \
      --fpixels 1

Outputs:
    - square_lattice_scaling.json: JSON summary with intensities, factors, ratios
    - square_lattice_scaling.md: Markdown report with commentary
    - Console log (capture via tee)
"""

import argparse
import json
from pathlib import Path

import torch

# Import nanobrag_torch owner APIs
from nanobrag_torch.simulator import Simulator
from nanobrag_torch.config import BeamConfig, CrystalConfig, CrystalShape, DetectorConfig
from nanobrag_torch.models.crystal import Crystal
from nanobrag_torch.models.detector import Detector


def run_simulation(na, nb, nc, spixels, fpixels, oversample, phi_steps, mosaic_domains, device="cpu"):
    """
    Run simulator with given N_cells configuration.

    Returns tuple: (total_intensity, debug_stats_dict)
    """
    # Create detector: single pixel or small grid
    detector_config = DetectorConfig(
        distance_mm=100.0,
        pixel_size_mm=0.1,
        spixels=spixels,
        fpixels=fpixels,
        oversample=oversample,
    )

    # Create beam config
    beam_config = BeamConfig()  # defaults: wavelength_A=1.0

    # Create crystal config with SQUARE shape
    crystal_config = CrystalConfig(
        default_F=100.0,  # Constant structure factor
        N_cells=(na, nb, nc),
        shape=CrystalShape.SQUARE,
        phi_steps=phi_steps,
        mosaic_domains=mosaic_domains,
    )

    # Instantiate crystal and detector
    crystal = Crystal(crystal_config, device=device)
    detector = Detector(detector_config, device=device)

    # Create simulator with debug config for partiality stats and trace
    debug_config = {
        'collect_partiality_stats': True,
        'trace_pixel': [0, 0]
    }

    simulator = Simulator(
        crystal=crystal,
        detector=detector,
        crystal_config=crystal_config,
        beam_config=beam_config,
        device=device,
        debug_config=debug_config,
    )

    # Run simulation
    image = simulator.run()
    total_intensity = image.sum().item()

    # Extract debug stats if available
    debug_stats = {}
    # Phase C.31: Extract partiality stats for F_cell, F_latt, F_total^2, intensity_pre_polar
    payload = {}

    # Access partiality_stats directly from simulator._partiality_stats
    if hasattr(simulator, '_partiality_stats') and simulator._partiality_stats is not None:
        pstats = simulator._partiality_stats
        # Phase C.31: Extract key metrics for scaling analysis
        if 'F_cell' in pstats:
            F_cell = pstats['F_cell']
            payload['F_cell'] = float(F_cell.mean().item()) if isinstance(F_cell, torch.Tensor) else F_cell
        if 'f_latt' in pstats:
            f_latt = pstats['f_latt']
            payload['F_latt'] = float(f_latt.mean().item()) if isinstance(f_latt, torch.Tensor) else f_latt
        if 'F_total_squared_pre_lorentz' in pstats:
            F_total_sq = pstats['F_total_squared_pre_lorentz']
            payload['F_total_squared_pre_lorentz'] = float(F_total_sq.mean().item()) if isinstance(F_total_sq, torch.Tensor) else F_total_sq
        if 'intensity_pre_polar' in pstats:
            I_pre_polar = pstats['intensity_pre_polar']
            payload['intensity_pre_polar'] = float(I_pre_polar.mean().item()) if isinstance(I_pre_polar, torch.Tensor) else I_pre_polar

        debug_stats['partiality_stats'] = {
            k: (v.tolist() if isinstance(v, torch.Tensor) else v)
            for k, v in pstats.items()
            if k not in ['delta_h', 'delta_k', 'delta_l', 'F_latt_a', 'F_latt_b', 'F_latt_c']
        }

    if hasattr(simulator, 'debug_stats') and simulator.debug_stats is not None:
        stats = simulator.debug_stats
        if 'trace_pixel' in stats:
            trace = stats['trace_pixel']
            debug_stats['trace_pixel'] = {
                k: (v.tolist() if isinstance(v, torch.Tensor) and v.numel() < 100 else str(v))
                for k, v in trace.items()
            }

    return total_intensity, debug_stats, payload


def main():
    parser = argparse.ArgumentParser(description="Square lattice scaling probe")
    parser.add_argument("--output-dir", type=str, required=True,
                        help="Output directory for artifacts")
    parser.add_argument("--n-cells", type=int, nargs=3, default=[41, 29, 32],
                        help="N_cells (Na Nb Nc)")
    parser.add_argument("--oversample", type=int, default=13,
                        help="Oversample factor")
    parser.add_argument("--phi-count", type=int, default=1,
                        help="Phi sample count")
    parser.add_argument("--mosaic-count", type=int, default=1,
                        help="Mosaic sample count")
    parser.add_argument("--spixels", type=int, default=1,
                        help="Slow pixels")
    parser.add_argument("--fpixels", type=int, default=1,
                        help="Fast pixels")
    parser.add_argument("--device", type=str, default="cpu",
                        help="Device (cpu/cuda)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    na, nb, nc = args.n_cells
    expected_ratio = (na * nb * nc) ** 2

    print(f"Square lattice scaling probe")
    print(f"=" * 60)
    print(f"N_cells target: ({na}, {nb}, {nc})")
    print(f"Expected ratio: {expected_ratio:,.1f}")
    print(f"Oversample: {args.oversample}")
    print(f"Detector: {args.spixels}×{args.fpixels} pixels")
    print(f"Phi steps: {args.phi_count}, Mosaic domains: {args.mosaic_count}")
    print(f"Device: {args.device}")
    print()

    # Run base case: N_cells=(1,1,1)
    print("Running base case: N_cells=(1,1,1)")
    intensity_base, debug_base, payload_base = run_simulation(
        1, 1, 1,
        args.spixels, args.fpixels,
        args.oversample, args.phi_count, args.mosaic_count,
        args.device
    )
    print(f"  Base intensity: {intensity_base:.6e}")
    if payload_base:
        print(f"  Base payload: F_cell={payload_base.get('F_cell', 'N/A'):.6e}, "
              f"F_latt={payload_base.get('F_latt', 'N/A'):.6e}, "
              f"F_total²={payload_base.get('F_total_squared_pre_lorentz', 'N/A'):.6e}, "
              f"I_pre_polar={payload_base.get('intensity_pre_polar', 'N/A'):.6e}")
    print()

    # Run scaled case: N_cells=(Na,Nb,Nc)
    print(f"Running scaled case: N_cells=({na},{nb},{nc})")
    intensity_scaled, debug_scaled, payload_scaled = run_simulation(
        na, nb, nc,
        args.spixels, args.fpixels,
        args.oversample, args.phi_count, args.mosaic_count,
        args.device
    )
    print(f"  Scaled intensity: {intensity_scaled:.6e}")
    if payload_scaled:
        print(f"  Scaled payload: F_cell={payload_scaled.get('F_cell', 'N/A'):.6e}, "
              f"F_latt={payload_scaled.get('F_latt', 'N/A'):.6e}, "
              f"F_total²={payload_scaled.get('F_total_squared_pre_lorentz', 'N/A'):.6e}, "
              f"I_pre_polar={payload_scaled.get('intensity_pre_polar', 'N/A'):.6e}")
    print()

    # Compute observed ratio
    observed_ratio = intensity_scaled / intensity_base if intensity_base > 0 else 0.0
    relative_error = abs(observed_ratio - expected_ratio) / expected_ratio if expected_ratio > 0 else float('inf')

    # Phase C.31: Compute derived ratios from payload
    # These help bisect where the (Na·Nb·Nc)² scaling is lost
    derived_ratios = {}
    if payload_base and payload_scaled:
        # Ratio of F_latt values (should be Na*Nb*Nc for SQUARE)
        if 'F_latt' in payload_base and 'F_latt' in payload_scaled:
            F_latt_base = payload_base['F_latt']
            F_latt_scaled = payload_scaled['F_latt']
            if F_latt_base > 0:
                derived_ratios['F_latt_ratio'] = F_latt_scaled / F_latt_base
                derived_ratios['F_latt_ratio_expected'] = na * nb * nc

        # Ratio of F_total² pre-Lorentz (should be (Na*Nb*Nc)² for SQUARE)
        if 'F_total_squared_pre_lorentz' in payload_base and 'F_total_squared_pre_lorentz' in payload_scaled:
            F_tot_sq_base = payload_base['F_total_squared_pre_lorentz']
            F_tot_sq_scaled = payload_scaled['F_total_squared_pre_lorentz']
            if F_tot_sq_base > 0:
                derived_ratios['F_total_sq_ratio'] = F_tot_sq_scaled / F_tot_sq_base
                derived_ratios['F_total_sq_ratio_expected'] = (na * nb * nc) ** 2

        # Ratio of intensity_pre_polar (should also be (Na*Nb*Nc)² if Lorentz is consistent)
        if 'intensity_pre_polar' in payload_base and 'intensity_pre_polar' in payload_scaled:
            I_pre_polar_base = payload_base['intensity_pre_polar']
            I_pre_polar_scaled = payload_scaled['intensity_pre_polar']
            if I_pre_polar_base > 0:
                derived_ratios['I_pre_polar_ratio'] = I_pre_polar_scaled / I_pre_polar_base
                derived_ratios['I_pre_polar_ratio_expected'] = (na * nb * nc) ** 2

        # Derived ratio: (I_pre_polar) / (F_cell * F_latt)²
        # This isolates the Lorentz contribution
        for label, payload in [('base', payload_base), ('scaled', payload_scaled)]:
            if 'intensity_pre_polar' in payload and 'F_cell' in payload and 'F_latt' in payload:
                I_pre = payload['intensity_pre_polar']
                F_c = payload['F_cell']
                F_l = payload['F_latt']
                denominator = (F_c * F_l) ** 2
                if denominator > 0:
                    derived_ratios[f'{label}_I_pre_polar_over_F_total_sq'] = I_pre / denominator

    print(f"Results")
    print(f"=" * 60)
    print(f"Expected ratio: {expected_ratio:,.1f}")
    print(f"Observed ratio: {observed_ratio:,.1f}")
    print(f"Relative error: {relative_error:.2%}")
    print(f"Ratio deviation: {observed_ratio / expected_ratio:.6f}x expected")
    if derived_ratios:
        print()
        print("Phase C.31 Derived Ratios:")
        for k, v in derived_ratios.items():
            print(f"  {k}: {v:.6e}")
    print()

    # Prepare JSON output
    results = {
        "n_cells": {"na": na, "nb": nb, "nc": nc},
        "oversample": args.oversample,
        "detector": {"spixels": args.spixels, "fpixels": args.fpixels},
        "phi_steps": args.phi_count,
        "mosaic_domains": args.mosaic_count,
        "device": args.device,
        "intensities": {
            "base": intensity_base,
            "scaled": intensity_scaled
        },
        "ratios": {
            "expected": expected_ratio,
            "observed": observed_ratio,
            "relative_error": relative_error,
            "deviation_factor": observed_ratio / expected_ratio if expected_ratio > 0 else 0.0
        },
        "payload": {
            "base": payload_base,
            "scaled": payload_scaled
        },
        "derived_ratios": derived_ratios,
        "debug_stats": {
            "base": debug_base,
            "scaled": debug_scaled
        }
    }

    # Write JSON
    json_path = output_dir / "square_lattice_scaling.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote JSON: {json_path}")

    # Write Markdown report
    md_path = output_dir / "square_lattice_scaling.md"
    with open(md_path, "w") as f:
        f.write("# Square Lattice Scaling Probe Results\n\n")
        f.write("## Configuration\n\n")
        f.write(f"- **N_cells**: ({na}, {nb}, {nc})\n")
        f.write(f"- **Expected ratio**: {expected_ratio:,.1f}\n")
        f.write(f"- **Oversample**: {args.oversample}\n")
        f.write(f"- **Detector**: {args.spixels}×{args.fpixels} pixels\n")
        f.write(f"- **Phi steps**: {args.phi_count}\n")
        f.write(f"- **Mosaic domains**: {args.mosaic_count}\n")
        f.write(f"- **Device**: {args.device}\n\n")

        f.write("## Intensities\n\n")
        f.write(f"- **Base** (N_cells=1,1,1): {intensity_base:.6e}\n")
        f.write(f"- **Scaled** (N_cells={na},{nb},{nc}): {intensity_scaled:.6e}\n\n")

        f.write("## Scaling Analysis\n\n")
        f.write(f"- **Expected ratio** (Na·Nb·Nc)²: {expected_ratio:,.1f}\n")
        f.write(f"- **Observed ratio**: {observed_ratio:,.1f}\n")
        f.write(f"- **Relative error**: {relative_error:.2%}\n")
        f.write(f"- **Deviation factor**: {observed_ratio / expected_ratio:.6f}x expected\n\n")

        f.write("## Phase C.31 Payload Analysis\n\n")
        if payload_base:
            f.write("### Base Case (N_cells=1,1,1)\n")
            for k, v in payload_base.items():
                f.write(f"- **{k}**: {v:.6e}\n")
            f.write("\n")
        if payload_scaled:
            f.write(f"### Scaled Case (N_cells={na},{nb},{nc})\n")
            for k, v in payload_scaled.items():
                f.write(f"- **{k}**: {v:.6e}\n")
            f.write("\n")

        if derived_ratios:
            f.write("### Derived Ratios\n\n")
            f.write("These ratios help bisect where the (Na·Nb·Nc)² scaling is lost:\n\n")
            for k, v in derived_ratios.items():
                f.write(f"- **{k}**: {v:.6e}\n")
            f.write("\n")

        f.write("## Commentary\n\n")
        if relative_error < 0.05:
            f.write("✅ The observed ratio is within 5% tolerance of the expected (Na·Nb·Nc)² scaling.\n")
        else:
            f.write(f"❌ **Contract violation detected**: The observed ratio deviates by {relative_error:.1%} from expected.\n\n")
            f.write(f"The SQUARE lattice contract (docs/spec-db-core.md:60-140) requires weights ∝ (Na·Nb·Nc)².\n")
            f.write(f"This {observed_ratio / expected_ratio:.6f}x shortfall suggests a bug in the lattice weight computation.\n")

    print(f"Wrote Markdown: {md_path}")
    print()
    print("Probe complete.")


if __name__ == "__main__":
    main()
