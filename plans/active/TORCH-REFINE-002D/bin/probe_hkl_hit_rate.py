#!/usr/bin/env python
"""
HKL Hit-Rate Probe for Stage A Perturbation Analysis

Purpose:
    Quantify the HKL grid coverage gap when applying the REFINE-004 perturbation
    (cell stretch + orientation misset) to canonical refGeom geometry.

    This probe loads the refGeom assets, applies `create_perturbed_geometry`,
    projects original Miller indices through both baseline and perturbed A* matrices,
    and emits JSON metrics covering:
    - Baseline HKL ranges and bounds from the original MTZ grid
    - Perturbed HKL ranges after transforming indices through the new A* matrix
    - In-bounds fraction (how many perturbed indices still fit within the baseline grid)
    - Max deviation and outlier counts

Strategy:
    1. Load refGeom experiment/reflections/MTZ via `dbex.data_load.DataLoad`
    2. Extract baseline Miller indices and A* matrix from the original crystal
    3. Apply `create_perturbed_geometry` to introduce deterministic miscalibration
    4. Extract perturbed A* and compute the basis change matrix B→P (A*_perturbed / A*_baseline)
    5. Project baseline Miller indices through the change-of-basis to get "perturbed" fractional HKL
    6. Compare perturbed HKL ranges to baseline grid bounds (from MTZ envelope)
    7. Emit JSON with baseline/perturbed range stats, hit-rate fraction, and deviation metrics

Constraints (per input.md Pitfalls):
    - Keep computations device-neutral (numpy/cctbx only, no torch tensors)
    - Do not mutate production HKL grids or commit regenerated artifacts
    - Guard against missing refGeom assets (fail with clear error)
    - Ensure JSON includes both baseline and perturbed ranges plus in-bounds fraction
    - Document any anomalies (e.g., non-integer HKL projections) in output

Findings Applied:
    - REFINE-004: Dataset too well calibrated; perturbation helper must remain test-only
    - REFINE-005: HKL grid from baseline crystal causes 0% hit rate when geometry is perturbed
    - REFINE-003: Orientation overrides must use quaternion-to-U construction
    - GRADIENT-001: Avoid .item()/.detach() in production paths (probe is analysis-only, OK here)

References:
    - plans/active/TORCH-REFINE-002D/implementation.md
    - plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/blocked.md
    - docs/fix_plan.md:60-70 (TORCH-REFINE-002D exit criteria)
    - tests/dbex/test_torch_refine_smoke.py:63-138 (create_perturbed_geometry)
"""

import argparse
import json
import sys
import numpy as np
from pathlib import Path


def load_refgeom_assets():
    """Load canonical refGeom experiment/reflections/MTZ using dbex.data_load.

    Returns:
        tuple: (DataLoad instance, crystal, detector, beam) from refGeom fixtures

    Raises:
        FileNotFoundError: If refGeom assets are missing
        ImportError: If required modules are unavailable
    """
    # Import here to avoid polluting module namespace and to defer import errors
    try:
        from dbex.data_load import DataLoad
    except ImportError as e:
        raise ImportError(
            f"Cannot import dbex.data_load: {e}. "
            "Ensure the dbex package is available in PYTHONPATH."
        )

    # Define canonical refGeom paths
    # These paths match the fixtures used by test_stage_a_expansion
    # Per test_torch_refine_smoke.py:46-57, refGeom assets are at repo root (not tests/fixtures/)
    # Script location: plans/active/TORCH-REFINE-002D/bin/probe_hkl_hit_rate.py
    # Need to go up 4 levels: bin/ -> TORCH-REFINE-002D/ -> active/ -> plans/ -> repo root
    workspace_root = Path(__file__).resolve().parents[4]
    expt_path = workspace_root / "refGeom.expt"
    refl_path = workspace_root / "refGeom.refl"
    mtz_path = workspace_root / "scaled.mtz"

    # Guard against missing assets
    for path in [expt_path, refl_path, mtz_path]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing refGeom asset: {path}. "
                "Probe requires canonical fixtures; do not regenerate datasets."
            )

    # Mimic the DataLoad construction used in test_stage_a_expansion (test_torch_refine_smoke.py:51-58)
    class Args:
        def __init__(self):
            self.mtzFile = str(mtz_path)
            self.mtzCol = "F,SIGF"  # Per test_torch_refine_smoke.py:57
            self.exptName = str(expt_path)
            self.exptIdx = 0
            self.reflName = str(refl_path)

    args = Args()
    dataload = DataLoad(args)

    # Extract geometry objects
    crystal = dataload.Expt.crystal
    detector = dataload.Expt.detector
    beam = dataload.Expt.beam

    return dataload, crystal, detector, beam


def create_perturbed_geometry(crystal, detector, beam, seed=42):
    """
    Apply deterministic perturbations to crystal geometry for Stage A analysis.

    This is the same helper used in test_stage_a_expansion (test_torch_refine_smoke.py:63-138),
    reproduced here for standalone probe usage.

    Perturbations (test-only, per REFINE-004):
    - Unit cell: +2% stretch on a-axis, +1% on b/c-axes
    - Orientation: +1.5° misset along Z-axis
    - Detector: unchanged
    - Beam: unchanged

    Args:
        crystal: dxtbx Crystal object
        detector: dxtbx Detector object (pass-through)
        beam: dxtbx Beam object (pass-through)
        seed: Random seed for reproducibility (currently unused)

    Returns:
        tuple: (perturbed_crystal, detector, beam)

    References:
        - tests/dbex/test_torch_refine_smoke.py:63-138
        - docs/fix_plan.md REFINE-004
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
    U = sqr(U_tuple)
    U_perturbed = rotation_z * U
    perturbed_crystal.set_U(U_perturbed)

    return perturbed_crystal, detector, beam


def compute_hkl_metrics(dataload, crystal_baseline, crystal_perturbed):
    """
    Compute HKL coverage metrics for baseline and perturbed geometries.

    Strategy:
        1. Extract baseline Miller indices from MTZ (dataload.F.indices())
        2. Build baseline A* matrix from crystal_baseline.get_A()
        3. Build perturbed A* matrix from crystal_perturbed.get_A()
        4. Compute change-of-basis matrix: A*_perturbed @ inv(A*_baseline)
        5. Project baseline Miller indices through COB to get perturbed fractional HKL
        6. Compare perturbed HKL ranges to baseline grid bounds
        7. Emit statistics: ranges, in-bounds fraction, max deviation

    Args:
        dataload: DataLoad instance with MTZ structure factors
        crystal_baseline: Original dxtbx Crystal
        crystal_perturbed: Perturbed dxtbx Crystal from create_perturbed_geometry

    Returns:
        dict: JSON-serializable metrics with keys:
            - baseline_hkl_ranges: {h: [min, max], k: [...], l: [...]}
            - perturbed_hkl_ranges: (same structure for projected indices)
            - in_bounds_fraction: fraction of perturbed indices within baseline grid
            - max_deviation: max |perturbed - baseline| across all axes
            - total_reflections: number of Miller indices analyzed
            - anomalies: list of notable issues (non-integer HKL, outliers, etc.)
    """
    # Extract baseline Miller indices from MTZ
    baseline_hkls = np.array(dataload.F.indices(), dtype=np.float64)  # (N, 3)
    n_reflections = len(baseline_hkls)

    # Compute baseline HKL grid bounds from MTZ envelope
    h_min_base, h_max_base = int(baseline_hkls[:, 0].min()), int(baseline_hkls[:, 0].max())
    k_min_base, k_max_base = int(baseline_hkls[:, 1].min()), int(baseline_hkls[:, 1].max())
    l_min_base, l_max_base = int(baseline_hkls[:, 2].min()), int(baseline_hkls[:, 2].max())

    # Extract A* matrices (dxtbx returns 9-element tuple, row-major per DXTBX-001)
    A_baseline_tuple = crystal_baseline.get_A()
    A_perturbed_tuple = crystal_perturbed.get_A()

    # Reshape to 3x3 numpy arrays (row-major → column vectors per MOSFLM convention)
    A_baseline = np.array(A_baseline_tuple).reshape(3, 3)
    A_perturbed = np.array(A_perturbed_tuple).reshape(3, 3)

    # Compute change-of-basis matrix: A*_perturbed @ inv(A*_baseline)
    # This transforms Miller indices from baseline basis to perturbed basis
    A_baseline_inv = np.linalg.inv(A_baseline)
    COB_matrix = A_perturbed @ A_baseline_inv

    # Project baseline Miller indices through COB to get perturbed HKL
    # hkl_perturbed = COB_matrix @ hkl_baseline^T
    perturbed_hkls = (COB_matrix @ baseline_hkls.T).T  # (N, 3)

    # Compute perturbed HKL ranges (may be fractional)
    h_min_pert, h_max_pert = perturbed_hkls[:, 0].min(), perturbed_hkls[:, 0].max()
    k_min_pert, k_max_pert = perturbed_hkls[:, 1].min(), perturbed_hkls[:, 1].max()
    l_min_pert, l_max_pert = perturbed_hkls[:, 2].min(), perturbed_hkls[:, 2].max()

    # Check in-bounds status: perturbed indices within baseline grid bounds
    in_bounds_h = (perturbed_hkls[:, 0] >= h_min_base) & (perturbed_hkls[:, 0] <= h_max_base)
    in_bounds_k = (perturbed_hkls[:, 1] >= k_min_base) & (perturbed_hkls[:, 1] <= k_max_base)
    in_bounds_l = (perturbed_hkls[:, 2] >= l_min_base) & (perturbed_hkls[:, 2] <= l_max_base)
    in_bounds_mask = in_bounds_h & in_bounds_k & in_bounds_l
    in_bounds_count = in_bounds_mask.sum()
    in_bounds_fraction = in_bounds_count / n_reflections

    # Compute max deviation (per-axis and overall)
    deltas = np.abs(perturbed_hkls - baseline_hkls)
    max_delta_h = deltas[:, 0].max()
    max_delta_k = deltas[:, 1].max()
    max_delta_l = deltas[:, 2].max()
    max_deviation = deltas.max()

    # Check for non-integer perturbed HKL (anomaly flag)
    perturbed_hkls_rounded = np.round(perturbed_hkls)
    non_integer_mask = np.abs(perturbed_hkls - perturbed_hkls_rounded) > 1e-6
    non_integer_count = non_integer_mask.any(axis=1).sum()

    anomalies = []
    if non_integer_count > 0:
        anomalies.append(
            f"{non_integer_count}/{n_reflections} perturbed HKL indices are non-integer "
            f"(max fractional part: {np.abs(perturbed_hkls - perturbed_hkls_rounded).max():.6f})"
        )
    if in_bounds_fraction < 0.95:
        anomalies.append(
            f"Only {in_bounds_fraction:.1%} of perturbed indices stay within baseline grid "
            f"(threshold: ≥95% per exit criteria)"
        )

    # Assemble metrics dict
    metrics = {
        "baseline_hkl_ranges": {
            "h": [int(h_min_base), int(h_max_base)],
            "k": [int(k_min_base), int(k_max_base)],
            "l": [int(l_min_base), int(l_max_base)]
        },
        "perturbed_hkl_ranges": {
            "h": [float(h_min_pert), float(h_max_pert)],
            "k": [float(k_min_pert), float(k_max_pert)],
            "l": [float(l_min_pert), float(l_max_pert)]
        },
        "in_bounds_fraction": float(in_bounds_fraction),
        "in_bounds_count": int(in_bounds_count),
        "total_reflections": int(n_reflections),
        "max_deviation": {
            "overall": float(max_deviation),
            "h": float(max_delta_h),
            "k": float(max_delta_k),
            "l": float(max_delta_l)
        },
        "non_integer_count": int(non_integer_count),
        "anomalies": anomalies,
        "perturbation_parameters": {
            "cell_stretch_pct": {"a": 2.0, "b": 1.0, "c": 1.0},
            "orientation_misset_deg": {"z_axis": 1.5}
        }
    }

    return metrics


def main():
    """Main entry point for HKL hit-rate probe."""
    parser = argparse.ArgumentParser(
        description="Probe HKL grid coverage for Stage A perturbation analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--out",
        type=str,
        required=True,
        help="Output JSON file path for metrics (e.g., hkl_probe.json)"
    )

    args = parser.parse_args()

    try:
        # Phase 1: Load refGeom assets
        print("Loading refGeom assets...", file=sys.stderr)
        dataload, crystal_baseline, detector, beam = load_refgeom_assets()
        print(f"  ✓ Loaded {len(dataload.F.indices())} reflections from MTZ", file=sys.stderr)

        # Phase 2: Apply perturbation
        print("Applying REFINE-004 perturbation...", file=sys.stderr)
        crystal_perturbed, _, _ = create_perturbed_geometry(crystal_baseline, detector, beam)
        print("  ✓ Perturbed crystal geometry (cell + orientation)", file=sys.stderr)

        # Phase 3: Compute metrics
        print("Computing HKL coverage metrics...", file=sys.stderr)
        metrics = compute_hkl_metrics(dataload, crystal_baseline, crystal_perturbed)
        print(f"  ✓ In-bounds fraction: {metrics['in_bounds_fraction']:.1%}", file=sys.stderr)

        # Phase 4: Emit JSON
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"\n✓ Metrics written to: {out_path}", file=sys.stderr)

        # Print summary to stderr
        print("\n=== HKL Coverage Summary ===", file=sys.stderr)
        print(f"Total reflections: {metrics['total_reflections']}", file=sys.stderr)
        print(f"Baseline grid: h={metrics['baseline_hkl_ranges']['h']}, "
              f"k={metrics['baseline_hkl_ranges']['k']}, "
              f"l={metrics['baseline_hkl_ranges']['l']}", file=sys.stderr)
        print(f"Perturbed range: h={metrics['perturbed_hkl_ranges']['h']}, "
              f"k={metrics['perturbed_hkl_ranges']['k']}, "
              f"l={metrics['perturbed_hkl_ranges']['l']}", file=sys.stderr)
        print(f"In-bounds: {metrics['in_bounds_count']}/{metrics['total_reflections']} "
              f"({metrics['in_bounds_fraction']:.1%})", file=sys.stderr)
        print(f"Max deviation: {metrics['max_deviation']['overall']:.3f}", file=sys.stderr)

        if metrics['anomalies']:
            print("\nAnomalies detected:", file=sys.stderr)
            for anomaly in metrics['anomalies']:
                print(f"  • {anomaly}", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
