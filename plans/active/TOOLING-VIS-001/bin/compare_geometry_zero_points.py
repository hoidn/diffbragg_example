#!/usr/bin/env python3
"""Compare geometry zero-points across experiment cases to quantify drift.

This T2 analysis script loads named experiment cases (default: refgeom.expt,
sp.proc/idx-0000_refined.expt, tests/fixtures/golden_data/simple_cubic/refined.expt),
extracts unit cells, U/B/A* matrices, detector distance/beam center/axes, and beam
vectors via dxtbx, then emits both per-case metrics and pairwise deltas vs the base
case into <artifacts>/geometry_deltas/geometry_deltas.json so we can see how far
the canonical geometry has drifted.

Usage:
    AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \\
    DBEX_SMOKE_SIGMA_SOURCE=metadata \\
    DBEX_SMOKE_DETECTOR_SIZE=small \\
    DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json \\
    DBEX_SMOKE_HKL_PATH=scaled.mtz \\
    KMP_DUPLICATE_LIB_OK=TRUE \\
    NANOBRAGG_DISABLE_COMPILE=1 \\
    python plans/active/TOOLING-VIS-001/bin/compare_geometry_zero_points.py \\
        --cases refgeom idx_refined golden_refined \\
        --out-dir plans/active/TOOLING-VIS-001/reports/<timestamp>/geometry_deltas

Data dependencies (per docs/data_dependency_manifest.md):
    - Reads experiment files via dxtbx (ExperimentList.from_file).
    - No DBEX helpers or simulation code; pure geometry extraction.
    - Canonical cases: refGeom.expt (baseline), idx-0000_refined.expt (sp.proc),
      tests/fixtures/golden_data/simple_cubic/refined.expt (golden).
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

import numpy as np

# Add repo root to path
# Script is at <repo>/plans/active/TOOLING-VIS-001/bin/script.py
# So we need 4 parent calls: bin -> TOOLING-VIS-001 -> active -> plans -> repo_root
repo_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

# Import dxtbx after path is set
from dxtbx.model import ExperimentList


def extract_geometry(expt_path: str) -> Dict[str, Any]:
    """Extract geometry parameters from an experiment file.

    Returns dict with:
        - unit_cell: {a, b, c, alpha, beta, gamma} in Angstrom/degrees
        - U_matrix: flattened 3x3 orientation matrix
        - B_matrix: flattened 3x3 from unit cell
        - A_star_matrix: flattened 3x3 (U @ B)
        - detector: {distance_mm, beam_center_fast_mm, beam_center_slow_mm,
                     normal, fast_axis, slow_axis}
        - beam: {direction, wavelength_angstrom}
    """
    experiments = ExperimentList.from_file(expt_path, check_format=False)
    if len(experiments) == 0:
        raise ValueError(f"No experiments found in {expt_path}")

    expt = experiments[0]
    crystal = expt.crystal
    detector = expt.detector
    beam = expt.beam

    # Extract unit cell parameters
    uc = crystal.get_unit_cell()
    unit_cell = {
        "a": float(uc.parameters()[0]),
        "b": float(uc.parameters()[1]),
        "c": float(uc.parameters()[2]),
        "alpha": float(uc.parameters()[3]),
        "beta": float(uc.parameters()[4]),
        "gamma": float(uc.parameters()[5]),
    }

    # Extract U matrix (orientation) - dxtbx returns as flat (9,) array
    U_flat = np.array(crystal.get_U(), dtype=np.float64)
    U = U_flat.reshape(3, 3)

    # Extract B matrix (reciprocal metric tensor from unit cell) - also flat (9,)
    B_flat = np.array(crystal.get_B(), dtype=np.float64)
    B = B_flat.reshape(3, 3)

    # Compute A* = U @ B
    A_star = U @ B

    # Extract detector geometry (panel 0)
    panel = detector[0]
    origin = panel.get_origin()
    fast = panel.get_fast_axis()
    slow = panel.get_slow_axis()
    normal = panel.get_normal()

    # Beam center in fast/slow coordinates (mm)
    # The beam center is where the beam intersects the detector
    beam_dir = np.array(beam.get_s0(), dtype=np.float64)
    beam_dir = beam_dir / np.linalg.norm(beam_dir)  # normalize

    # Distance from sample to detector origin
    distance_mm = float(np.linalg.norm(origin))

    # Project beam onto detector plane to get beam center
    # For simplicity, we use the origin as reference (assumes beam hits near origin)
    # A more accurate calculation would ray-trace beam_dir to detector plane
    beam_center_fast = float(np.dot(origin, fast))
    beam_center_slow = float(np.dot(origin, slow))

    detector_geom = {
        "distance_mm": distance_mm,
        "beam_center_fast_mm": beam_center_fast,
        "beam_center_slow_mm": beam_center_slow,
        "normal": [float(x) for x in normal],
        "fast_axis": [float(x) for x in fast],
        "slow_axis": [float(x) for x in slow],
    }

    # Extract beam
    beam_s0 = beam.get_s0()
    beam_geom = {
        "direction": [float(x) for x in beam_s0],
        "wavelength_angstrom": float(beam.get_wavelength()),
    }

    return {
        "unit_cell": unit_cell,
        "U_matrix": U.flatten().tolist(),
        "B_matrix": B.flatten().tolist(),
        "A_star_matrix": A_star.flatten().tolist(),
        "detector": detector_geom,
        "beam": beam_geom,
    }


def compute_rotation_angle(U1: np.ndarray, U2: np.ndarray) -> float:
    """Compute rotation angle (in degrees) between two orientation matrices.

    Uses the formula: angle = arccos((trace(U1^T @ U2) - 1) / 2)
    which gives the geodesic distance on SO(3).
    """
    R = U1.T @ U2
    trace_val = np.trace(R)
    # Clamp to avoid numerical issues with arccos
    cos_angle = (trace_val - 1.0) / 2.0
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle_rad = np.arccos(cos_angle)
    return float(np.degrees(angle_rad))


def compute_deltas(base_geom: Dict[str, Any], case_geom: Dict[str, Any]) -> Dict[str, Any]:
    """Compute pairwise deltas between case and base geometry.

    Returns:
        - unit_cell_deltas: absolute differences for a,b,c,alpha,beta,gamma
        - U_rotation_angle_deg: rotation angle between U matrices
        - A_star_frobenius: Frobenius norm of (A* - A*_base)
        - detector_distance_delta_mm: difference in detector distance
        - beam_center_shift_mm: Euclidean distance in fast/slow plane
        - beam_direction_dot: dot product of beam directions (should be ~1)
    """
    base_uc = base_geom["unit_cell"]
    case_uc = case_geom["unit_cell"]

    unit_cell_deltas = {
        "a_delta": abs(case_uc["a"] - base_uc["a"]),
        "b_delta": abs(case_uc["b"] - base_uc["b"]),
        "c_delta": abs(case_uc["c"] - base_uc["c"]),
        "alpha_delta": abs(case_uc["alpha"] - base_uc["alpha"]),
        "beta_delta": abs(case_uc["beta"] - base_uc["beta"]),
        "gamma_delta": abs(case_uc["gamma"] - base_uc["gamma"]),
    }

    # U matrix rotation angle
    base_U = np.array(base_geom["U_matrix"], dtype=np.float64).reshape(3, 3)
    case_U = np.array(case_geom["U_matrix"], dtype=np.float64).reshape(3, 3)
    rotation_angle = compute_rotation_angle(base_U, case_U)

    # A* Frobenius norm
    base_Astar = np.array(base_geom["A_star_matrix"], dtype=np.float64).reshape(3, 3)
    case_Astar = np.array(case_geom["A_star_matrix"], dtype=np.float64).reshape(3, 3)
    astar_frobenius = float(np.linalg.norm(case_Astar - base_Astar, ord='fro'))

    # Detector deltas
    base_det = base_geom["detector"]
    case_det = case_geom["detector"]

    distance_delta = abs(case_det["distance_mm"] - base_det["distance_mm"])

    beam_center_delta_fast = case_det["beam_center_fast_mm"] - base_det["beam_center_fast_mm"]
    beam_center_delta_slow = case_det["beam_center_slow_mm"] - base_det["beam_center_slow_mm"]
    beam_center_shift = float(np.sqrt(beam_center_delta_fast**2 + beam_center_delta_slow**2))

    # Panel normal dot product (should be ~1 if same orientation)
    base_normal = np.array(base_det["normal"], dtype=np.float64)
    case_normal = np.array(case_det["normal"], dtype=np.float64)
    normal_dot = float(np.dot(base_normal, case_normal))

    # Beam direction dot product
    base_beam = np.array(base_geom["beam"]["direction"], dtype=np.float64)
    case_beam = np.array(case_geom["beam"]["direction"], dtype=np.float64)
    # Normalize to handle potential magnitude differences
    base_beam_norm = base_beam / np.linalg.norm(base_beam)
    case_beam_norm = case_beam / np.linalg.norm(case_beam)
    beam_dot = float(np.dot(base_beam_norm, case_beam_norm))

    return {
        "unit_cell_deltas": unit_cell_deltas,
        "U_rotation_angle_deg": rotation_angle,
        "A_star_frobenius_norm": astar_frobenius,
        "detector_distance_delta_mm": distance_delta,
        "beam_center_shift_mm": beam_center_shift,
        "panel_normal_dot": normal_dot,
        "beam_direction_dot": beam_dot,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compare geometry zero-points across experiment cases"
    )
    parser.add_argument(
        "--cases",
        nargs="+",
        default=["refgeom", "idx_refined", "golden_refined"],
        help="Case names to compare (default: refgeom idx_refined golden_refined)",
    )
    parser.add_argument(
        "--base-case",
        default="refgeom",
        help="Base case name for delta computation (default: refgeom)",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Output directory for geometry_deltas.json and summary.md",
    )
    args = parser.parse_args()

    # Define case name to file path mapping
    case_paths = {
        "refgeom": "refGeom.expt",
        "idx_refined": "sp.proc/idx-0000_refined.expt",
        "golden_refined": "tests/fixtures/golden_data/simple_cubic/refined.expt",
    }

    # Create output directory
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Extract geometry for all cases
    print(f"Extracting geometry from {len(args.cases)} cases...")
    geometries = {}
    for case in args.cases:
        if case not in case_paths:
            print(f"Warning: Unknown case '{case}', skipping", file=sys.stderr)
            continue

        path = case_paths[case]
        if not Path(path).exists():
            print(f"Warning: Experiment file '{path}' not found, skipping case '{case}'", file=sys.stderr)
            continue

        try:
            print(f"  Loading {case} from {path}...")
            geometries[case] = extract_geometry(path)
            print(f"    Unit cell: a={geometries[case]['unit_cell']['a']:.4f} Å")
        except Exception as e:
            print(f"Error loading {case} from {path}: {e}", file=sys.stderr)
            continue

    if not geometries:
        print("Error: No geometries could be loaded", file=sys.stderr)
        return 1

    # Check that base case exists
    if args.base_case not in geometries:
        print(f"Error: Base case '{args.base_case}' not found in loaded geometries", file=sys.stderr)
        return 1

    # Compute deltas vs base case
    print(f"\nComputing deltas vs base case '{args.base_case}'...")
    deltas = {}
    for case in geometries:
        if case == args.base_case:
            continue
        print(f"  {case} vs {args.base_case}...")
        deltas[case] = compute_deltas(geometries[args.base_case], geometries[case])

    # Assemble output JSON
    output = {
        "base_case": args.base_case,
        "cases": list(geometries.keys()),
        "geometries": geometries,
        "deltas": deltas,
    }

    # Write JSON
    json_path = out_dir / "geometry_deltas.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote geometry deltas to {json_path}")

    # Write markdown summary
    summary_path = out_dir / "summary.md"
    with open(summary_path, "w") as f:
        f.write("# Geometry Zero-Point Comparison\n\n")
        f.write(f"**Base case:** `{args.base_case}`\n\n")
        f.write(f"**Cases compared:** {', '.join(geometries.keys())}\n\n")

        f.write("## Per-Case Geometry\n\n")
        for case in geometries:
            geom = geometries[case]
            uc = geom["unit_cell"]
            f.write(f"### {case}\n\n")
            f.write(f"- **Unit cell:** a={uc['a']:.4f} Å, b={uc['b']:.4f} Å, c={uc['c']:.4f} Å, ")
            f.write(f"α={uc['alpha']:.2f}°, β={uc['beta']:.2f}°, γ={uc['gamma']:.2f}°\n")
            f.write(f"- **Detector distance:** {geom['detector']['distance_mm']:.2f} mm\n")
            f.write(f"- **Beam center:** fast={geom['detector']['beam_center_fast_mm']:.2f} mm, ")
            f.write(f"slow={geom['detector']['beam_center_slow_mm']:.2f} mm\n")
            f.write(f"- **Wavelength:** {geom['beam']['wavelength_angstrom']:.6f} Å\n\n")

        f.write("## Deltas vs Base Case\n\n")
        for case in deltas:
            delta = deltas[case]
            f.write(f"### {case} − {args.base_case}\n\n")

            uc_delta = delta["unit_cell_deltas"]
            f.write(f"- **Unit cell deltas:** Δa={uc_delta['a_delta']:.4f} Å, ")
            f.write(f"Δb={uc_delta['b_delta']:.4f} Å, Δc={uc_delta['c_delta']:.4f} Å, ")
            f.write(f"Δα={uc_delta['alpha_delta']:.3f}°, Δβ={uc_delta['beta_delta']:.3f}°, ")
            f.write(f"Δγ={uc_delta['gamma_delta']:.3f}°\n")

            f.write(f"- **U rotation angle:** {delta['U_rotation_angle_deg']:.4f}°\n")
            f.write(f"- **A* Frobenius norm:** {delta['A_star_frobenius_norm']:.6e}\n")
            f.write(f"- **Detector distance delta:** {delta['detector_distance_delta_mm']:.3f} mm\n")
            f.write(f"- **Beam center shift:** {delta['beam_center_shift_mm']:.3f} mm\n")
            f.write(f"- **Panel normal dot product:** {delta['panel_normal_dot']:.6f}\n")
            f.write(f"- **Beam direction dot product:** {delta['beam_direction_dot']:.6f}\n\n")

        f.write("## Interpretation\n\n")
        f.write("- **U rotation angle** shows orientation drift between experiments.\n")
        f.write("- **A* Frobenius norm** quantifies total reciprocal lattice drift.\n")
        f.write("- **Beam center shift** and **detector distance delta** show physical detector movements.\n")
        f.write("- Dot products near 1.0 indicate parallel directions (good alignment).\n")

    print(f"Wrote summary to {summary_path}")

    # Print summary to console
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for case in deltas:
        delta = deltas[case]
        print(f"\n{case} vs {args.base_case}:")
        print(f"  U rotation:        {delta['U_rotation_angle_deg']:8.4f}°")
        print(f"  A* Frobenius:      {delta['A_star_frobenius_norm']:12.6e}")
        print(f"  Detector shift:    {delta['detector_distance_delta_mm']:8.3f} mm")
        print(f"  Beam center shift: {delta['beam_center_shift_mm']:8.3f} mm")

    return 0


if __name__ == "__main__":
    sys.exit(main())
