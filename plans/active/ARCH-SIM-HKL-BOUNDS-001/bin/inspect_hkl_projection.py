#!/usr/bin/env python
"""Inspect per-pixel HKL projections (ARCH-SIM-HKL-BOUNDS-001 Phase B.1).

This diagnostic tool reproduces the nanobrag_torch scattering-vector→HKL projection math
for specific pixels (beam center and ±offsets along slow/fast axes) to expose the constant
+30/+40 index shift observed in DIAG-NANOBRAGG-OVERSAMPLE-001 Phase F.

Per plans/active/ARCH-SIM-HKL-BOUNDS-001/implementation.md:87-93, the script:
1. Loads the canonical refGeom smoke fixture via DataLoad
2. Rebuilds Detector/Beam/Crystal configs from the mapping fixture using existing bridge helpers
3. Reproduces the `compute_physics_for_position` scattering-vector math for chosen pixels
4. Emits JSON metrics (fractional HKL values, rounded indices, in-bounds status) and a Markdown summary

The direct-beam pixel should yield (h,k,l)≈(0,0,0) per crystallography conventions, but
diagnostics suggest it currently produces h,k,l ≈ +30/+40 offset from the loaded grid bounds.

Usage:
    NANOBRAGG_DISABLE_COMPILE=1 python inspect_hkl_projection.py \\
        --detector-size small \\
        --out-dir plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T152326Z/

Outputs:
    - <out-dir>/hkl_projection_metrics.json: Per-pixel HKL values and in-bounds status
    - <out-dir>/hkl_projection_summary.md: Human-readable Phase B.1 observations
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

# Push repo root onto sys.path for editable install access
_repo_root = Path(__file__).resolve().parents[4]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from dbex.data_load import DataLoad
from dbex.refinement.config_factories import create_crystal_config, create_detector_config, create_beam_config
from dbex.nanobrag_bridge import build_structure_factor_grid

# Import nanobrag_torch after sys.path adjustment
try:
    from nanobrag_torch.models.crystal import Crystal
    from nanobrag_torch.models.detector import Detector
except ImportError as e:
    print(f"ERROR: nanobrag_torch import failed: {e}", file=sys.stderr)
    print("Ensure nanobrag_torch is installed (editable or via environment).", file=sys.stderr)
    sys.exit(1)


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Inspect per-pixel HKL projections (ARCH-SIM-HKL-BOUNDS-001 Phase B.1)"
    )
    parser.add_argument(
        "--detector-size",
        choices=["small", "full"],
        default="small",
        help="Detector size variant (default: small)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for metrics JSON and summary",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Torch device (default: cpu for deterministic debugging)",
    )
    return parser.parse_args()


def build_dataload_args(detector_size: str) -> SimpleNamespace:
    """Build DataLoad args for canonical refGeom smoke dataset.

    Mirrors the fixture setup from docs/data_dependency_manifest.md:34-54.
    """
    repo_root = Path(__file__).resolve().parents[4]

    if detector_size == "small":
        expt_name = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small.expt"
        refl_name = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small.refl"
        mask_path = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small_mask.pkl"
    else:
        expt_name = repo_root / "sp.proc" / "refGeom.expt"
        refl_name = repo_root / "sp.proc" / "refGeom.refl"
        mask_path = repo_root / "747_mask.pkl"

    mtz_file = repo_root / "scaled.mtz"

    # Validate paths
    for p, label in [
        (expt_name, "experiment"),
        (refl_name, "reflections"),
        (mask_path, "mask"),
        (mtz_file, "MTZ"),
    ]:
        if not p.exists():
            raise FileNotFoundError(f"Missing {label} file: {p}")

    return SimpleNamespace(
        exptName=str(expt_name),
        reflName=str(refl_name),
        maskPath=str(mask_path),
        mtzFile=str(mtz_file),
        mtzCol="F(+),SIGF(+),F(-),SIGF(-)",  # Friedel pair column spec
        exptIdx=0,  # First experiment
        # No N_cells override; let mapping configs determine sizing
        Nabc=None,
    )


def compute_beam_center_pixel(detector_config) -> tuple[int, int]:
    """Compute beam center pixel indices (fast, slow) from detector config.

    Per config_crosswalk.md:29, beam_center_s and beam_center_f are in millimeters.
    Convert to pixel indices by dividing by pixel size.

    Returns:
        (fast_px, slow_px): Beam center pixel indices (rounded to nearest int)
    """
    fast_px = int(round(detector_config.beam_center_f / detector_config.pixel_size_mm))
    slow_px = int(round(detector_config.beam_center_s / detector_config.pixel_size_mm))
    return fast_px, slow_px


def compute_pixel_coords_angstroms(
    slow_px: int,
    fast_px: int,
    detector: Detector,
) -> torch.Tensor:
    """Compute 3D position (in Angstroms) for a given pixel.

    Uses the Detector's get_pixel_coords method to obtain all pixel positions,
    then extracts the specific pixel requested.

    Args:
        slow_px: Slow-axis pixel index
        fast_px: Fast-axis pixel index
        detector: nanobrag_torch Detector instance

    Returns:
        position: Tensor of shape (3,) with 3D coordinates in Angstroms
    """
    # Get all pixel coordinates (shape: [slow, fast, 3])
    # The detector returns coordinates in meters by default
    all_coords_meters = detector.get_pixel_coords()

    # Extract the specific pixel
    pixel_coords_meters = all_coords_meters[slow_px, fast_px, :]  # (3,)

    # Convert meters to Angstroms (1 m = 1e10 Å)
    pixel_coords_angstroms = pixel_coords_meters * 1e10

    return pixel_coords_angstroms


def compute_hkl_for_pixel(
    pixel_coords_angstroms: torch.Tensor,
    crystal: Crystal,
    incident_beam_direction: torch.Tensor,
    wavelength_angstroms: float,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Compute fractional HKL indices for a pixel position.

    Reproduces the scattering-vector math from compute_physics_for_position
    (simulator.py:111-205) for a single pixel.

    Args:
        pixel_coords_angstroms: Pixel position (3,) in Angstroms
        crystal: nanobrag_torch Crystal instance
        incident_beam_direction: Incident beam unit vector (3,)
        wavelength_angstroms: Beam wavelength in Angstroms

    Returns:
        (h, k, l): Fractional Miller indices as tensors
    """
    # Calculate diffracted beam direction (unit vector pointing from sample to pixel)
    pixel_squared_sum = torch.sum(pixel_coords_angstroms * pixel_coords_angstroms)
    pixel_magnitude = torch.sqrt(torch.clamp(pixel_squared_sum, min=1e-12))
    diffracted_beam_unit = pixel_coords_angstroms / pixel_magnitude

    # Scattering vector using crystallographic convention (simulator.py:163-165)
    # q = (diffracted - incident) / wavelength_meters
    # The simulator uses meters for wavelength conversion, giving q in m⁻¹
    wavelength_meters = wavelength_angstroms * 1e-10
    scattering_vector_m_inv = (diffracted_beam_unit - incident_beam_direction) / wavelength_meters

    # Get rotated reciprocal lattice vectors from crystal
    # Per simulator.py:911-913, reciprocal vectors are cached WITHOUT unit conversion,
    # so they remain in Å⁻¹ while real vectors are converted to meters.
    # For zero-point Stage-A with stills (no phi scanning, no mosaicity), these are (1, 1, 3)
    _, (rot_a_star, rot_b_star, rot_c_star) = crystal.get_rotated_real_vectors(crystal.config)
    # Extract the single phi, single mosaic domain vectors (shape: 3, units: Å⁻¹)
    rot_a_star_angstrom_inv = rot_a_star[0, 0, :]  # (3,)
    rot_b_star_angstrom_inv = rot_b_star[0, 0, :]  # (3,)
    rot_c_star_angstrom_inv = rot_c_star[0, 0, :]  # (3,)

    # Convert scattering vector from m⁻¹ to Å⁻¹ to match reciprocal vector units
    # 1 m⁻¹ = 1e-10 Å⁻¹
    scattering_vector_angstrom_inv = scattering_vector_m_inv * 1e-10

    # Project scattering vector onto reciprocal lattice axes to get Miller indices
    # h = q · a*, k = q · b*, l = q · c*
    # Both are in Å⁻¹, so the dot product is dimensionless (Miller index)
    h = torch.dot(scattering_vector_angstrom_inv, rot_a_star_angstrom_inv)
    k = torch.dot(scattering_vector_angstrom_inv, rot_b_star_angstrom_inv)
    l = torch.dot(scattering_vector_angstrom_inv, rot_c_star_angstrom_inv)

    return h, k, l


def main():
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device(args.device)

    # Load canonical mapping fixture
    print(f"Loading {args.detector_size}-detector refGeom fixture...")
    dataload_args = build_dataload_args(args.detector_size)
    dataload = DataLoad(dataload_args)

    # Extract dxtbx objects
    detector = dataload.Expt.detector
    panel = detector[0]  # Single panel
    beam = dataload.Expt.beam
    crystal_dxtbx = dataload.Expt.crystal

    # Create nanobrag_torch configs using bridge helpers
    print("Building nanobrag_torch configs via bridge factories...")
    detector_config = create_detector_config(
        panel=panel,
        beam=beam,
        trusted_mask=dataload.trusted_mask[0],  # First panel
        roi_bbox=None,  # Use full detector
        oversample=1,  # No oversampling for diagnostics
    )

    beam_config = create_beam_config(beam=beam)

    crystal_config, _ = create_crystal_config(
        crystal=crystal_dxtbx,
        experiment=dataload.Expt,
        N_cells=None,  # Use default
    )

    # Build structure factor grid
    print("Building structure factor grid...")
    hkl_indices = np.array(dataload.F.indices())
    hkl_amplitudes = np.array(dataload.F.data())
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device,
        halo=False,
    )

    # Instantiate nanobrag_torch models
    print("Instantiating nanobrag_torch Detector and Crystal...")
    detector = Detector(detector_config, device=device)
    crystal = Crystal(crystal_config, beam_config=beam_config, device=device)

    # Load structure factors into crystal
    crystal.hkl_data = hkl_grid
    crystal.hkl_metadata = hkl_metadata

    # Compute beam center pixel
    beam_center_fast_px, beam_center_slow_px = compute_beam_center_pixel(detector_config)
    print(f"Beam center pixel (fast, slow): ({beam_center_fast_px}, {beam_center_slow_px})")

    # Define test pixels: beam center + offsets along slow/fast axes
    # Use ±64 pixel offsets per input.md:10
    offset = 64
    test_pixels = [
        ("direct_beam", beam_center_slow_px, beam_center_fast_px),
        ("plus_slow", beam_center_slow_px + offset, beam_center_fast_px),
        ("minus_slow", beam_center_slow_px - offset, beam_center_fast_px),
        ("plus_fast", beam_center_slow_px, beam_center_fast_px + offset),
        ("minus_fast", beam_center_slow_px, beam_center_fast_px - offset),
    ]

    # Incident beam direction (sample→source, unit vector)
    # Per config_crosswalk.md:13, beam vector is sample→source (normalized -s0)
    s0 = beam.get_s0()
    incident_beam_direction = -torch.tensor([s0[0], s0[1], s0[2]], dtype=torch.float32, device=device)
    incident_beam_direction = incident_beam_direction / torch.norm(incident_beam_direction)

    wavelength_angstroms = beam_config.wavelength_A

    # Get HKL metadata bounds from crystal
    hkl_metadata = crystal.hkl_metadata
    if hkl_metadata is None:
        print("WARNING: Crystal.hkl_metadata is None; cannot check in-bounds status", file=sys.stderr)
        hkl_bounds = None
    else:
        hkl_bounds = {
            'h': (hkl_metadata['h_min'], hkl_metadata['h_max']),
            'k': (hkl_metadata['k_min'], hkl_metadata['k_max']),
            'l': (hkl_metadata['l_min'], hkl_metadata['l_max']),
        }
        print(f"Structure factor grid bounds: h∈{hkl_bounds['h']}, k∈{hkl_bounds['k']}, l∈{hkl_bounds['l']}")

    # Compute HKL projections for each test pixel
    results = []
    print("\nComputing HKL projections for test pixels...")
    for label, slow_px, fast_px in test_pixels:
        # Compute 3D position
        pixel_coords = compute_pixel_coords_angstroms(slow_px, fast_px, detector)

        # Compute fractional HKL
        h_frac, k_frac, l_frac = compute_hkl_for_pixel(
            pixel_coords,
            crystal,
            incident_beam_direction,
            wavelength_angstroms,
        )

        # Round to nearest integer
        h_round = int(torch.round(h_frac).item())
        k_round = int(torch.round(k_frac).item())
        l_round = int(torch.round(l_frac).item())

        # Check in-bounds status
        if hkl_bounds is not None:
            h_in = hkl_bounds['h'][0] <= h_round <= hkl_bounds['h'][1]
            k_in = hkl_bounds['k'][0] <= k_round <= hkl_bounds['k'][1]
            l_in = hkl_bounds['l'][0] <= l_round <= hkl_bounds['l'][1]
            all_in = h_in and k_in and l_in
        else:
            h_in = k_in = l_in = all_in = None

        result = {
            'label': label,
            'pixel': {'slow': slow_px, 'fast': fast_px},
            'hkl_fractional': {
                'h': float(h_frac.item()),
                'k': float(k_frac.item()),
                'l': float(l_frac.item()),
            },
            'hkl_rounded': {
                'h': h_round,
                'k': k_round,
                'l': l_round,
            },
            'in_bounds': {
                'h': h_in,
                'k': k_in,
                'l': l_in,
                'all': all_in,
            },
        }
        results.append(result)

        in_status = "IN BOUNDS" if all_in else "OUT OF BOUNDS" if all_in is not None else "UNKNOWN"
        print(f"  {label:15s} | px=({slow_px:4d},{fast_px:4d}) | "
              f"HKL=({h_frac:8.3f},{k_frac:8.3f},{l_frac:8.3f}) → "
              f"({h_round:4d},{k_round:4d},{l_round:4d}) | {in_status}")

    # Write JSON metrics
    metrics_path = args.out_dir / "hkl_projection_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump({
            'detector_size': args.detector_size,
            'beam_center_pixel': {'fast': beam_center_fast_px, 'slow': beam_center_slow_px},
            'hkl_grid_bounds': hkl_bounds,
            'test_pixels': results,
        }, f, indent=2)
    print(f"\nWrote metrics: {metrics_path}")

    # Write Markdown summary
    summary_path = args.out_dir / "hkl_projection_summary.md"
    with open(summary_path, 'w') as f:
        f.write("# HKL Projection Inspection (ARCH-SIM-HKL-BOUNDS-001 Phase B.1)\n\n")
        f.write(f"**Dataset**: refGeom {args.detector_size}-detector smoke fixture\n\n")
        f.write(f"**Beam center pixel**: (fast={beam_center_fast_px}, slow={beam_center_slow_px})\n\n")

        if hkl_bounds is not None:
            f.write("## Structure Factor Grid Bounds\n\n")
            f.write(f"- h ∈ [{hkl_bounds['h'][0]}, {hkl_bounds['h'][1]}]\n")
            f.write(f"- k ∈ [{hkl_bounds['k'][0]}, {hkl_bounds['k'][1]}]\n")
            f.write(f"- l ∈ [{hkl_bounds['l'][0]}, {hkl_bounds['l'][1]}]\n\n")

        f.write("## Per-Pixel HKL Projections\n\n")
        f.write("| Label | Pixel (slow, fast) | HKL (fractional) | HKL (rounded) | In Bounds? |\n")
        f.write("|-------|-------------------|------------------|---------------|------------|\n")
        for r in results:
            label = r['label']
            slow, fast = r['pixel']['slow'], r['pixel']['fast']
            h_f, k_f, l_f = r['hkl_fractional']['h'], r['hkl_fractional']['k'], r['hkl_fractional']['l']
            h_r, k_r, l_r = r['hkl_rounded']['h'], r['hkl_rounded']['k'], r['hkl_rounded']['l']
            all_in = r['in_bounds']['all']
            in_status = "✓" if all_in else "✗" if all_in is not None else "?"
            f.write(f"| {label:15s} | ({slow:4d}, {fast:4d}) | "
                   f"({h_f:7.2f}, {k_f:7.2f}, {l_f:7.2f}) | "
                   f"({h_r:4d}, {k_r:4d}, {l_r:4d}) | {in_status} |\n")

        f.write("\n## Phase B.1 Observations\n\n")

        # Compute offsets from direct beam to grid center
        direct_beam_result = results[0]
        h_db = direct_beam_result['hkl_rounded']['h']
        k_db = direct_beam_result['hkl_rounded']['k']
        l_db = direct_beam_result['hkl_rounded']['l']

        f.write(f"1. **Direct-beam pixel HKL**: The pixel at the computed beam center yields "
               f"HKL=({h_db}, {k_db}, {l_db}), which should be ≈(0,0,0) per crystallographic "
               f"conventions (zero scattering vector for direct beam).\n\n")

        if hkl_bounds is not None:
            grid_center_h = (hkl_bounds['h'][0] + hkl_bounds['h'][1]) / 2
            grid_center_k = (hkl_bounds['k'][0] + hkl_bounds['k'][1]) / 2
            grid_center_l = (hkl_bounds['l'][0] + hkl_bounds['l'][1]) / 2

            offset_h = h_db - 0  # Expected to be 0
            offset_k = k_db - 0
            offset_l = l_db - 0

            f.write(f"2. **Grid center vs direct beam**: The loaded structure-factor grid is centered at "
                   f"({grid_center_h:.1f}, {grid_center_k:.1f}, {grid_center_l:.1f}). "
                   f"The direct-beam HKL is offset by ({offset_h:+d}, {offset_k:+d}, {offset_l:+d}) from (0,0,0).\n\n")

            f.write("3. **Systematic offset hypothesis**: If all test pixels are consistently shifted by the same "
                   "amount relative to the grid bounds, this suggests a reciprocal-space alignment bug in the "
                   "crystal orientation or structure-factor grid indexing conventions.\n\n")

        f.write("4. **Next steps**: Cross-reference these per-pixel projections against the HKL stats from "
               "DIAG-NANOBRAGG-OVERSAMPLE-001 to confirm the offset pattern. If the direct-beam offset matches "
               "the 0% coverage ranges, the fix likely involves correcting the crystal rotation or grid indexing.\n\n")

        repo_root = Path(__file__).resolve().parents[4]
        try:
            out_dir_rel = args.out_dir.relative_to(repo_root)
            script_rel = Path(__file__).relative_to(repo_root)
        except ValueError:
            out_dir_rel = args.out_dir
            script_rel = Path(__file__)

        f.write(f"**Artifacts**: {out_dir_rel}\n")
        f.write(f"**CLI**: `NANOBRAGG_DISABLE_COMPILE=1 python {script_rel} "
               f"--detector-size {args.detector_size} --out-dir {out_dir_rel}`\n")

    print(f"Wrote summary: {summary_path}")
    print("\nPhase B.1 complete.")


if __name__ == "__main__":
    main()
