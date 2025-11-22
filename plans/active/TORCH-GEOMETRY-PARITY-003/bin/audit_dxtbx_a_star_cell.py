#!/usr/bin/env python3
"""
Audit dxtbx A*/cell relationship to investigate det(U)≠1 (initiative: TORCH-GEOMETRY-PARITY-003, owner: galph)

Inputs: --expt <path to DIALS experiment JSON>
Outputs: dxtbx_a_star_cell_audit.json under --out
Repro: python plans/active/TORCH-GEOMETRY-PARITY-003/bin/audit_dxtbx_a_star_cell.py --expt sp.proc/refGeom.expt --out <artifacts>/dxtbx_a_star_cell_audit.json

Purpose:
  Extract dxtbx A* and unit cell, compute B_ideal via cctbx, derive U from A* @ inv(B_ideal),
  and validate the crystallographic decomposition identity. Investigate why det(U)≠1 by computing
  isotropic scale factor and checking dxtbx API consistency.

Exit:
  - JSON report with all metrics
  - Console summary of det(U), isotropic scale, and identity validation
"""
import argparse
import json
import numpy as np
from dxtbx.model import ExperimentList
from cctbx import uctbx


def main():
    ap = argparse.ArgumentParser(description="Audit dxtbx A*/cell for det(U)≠1 investigation")
    ap.add_argument('--expt', required=True, help='Path to DIALS experiment file')
    ap.add_argument('--out', required=True, help='Output JSON path')
    args = ap.parse_args()

    # Load experiment
    experiments = ExperimentList.from_file(args.expt, check_format=False)
    crystal = experiments[0].crystal

    # Extract A* (reshape from 9-element tuple to 3x3)
    A_star_tuple = crystal.get_A()
    A_star = np.array(A_star_tuple).reshape(3, 3)

    # Extract unit cell
    cell = crystal.get_unit_cell()
    a, b, c, alpha_deg, beta_deg, gamma_deg = cell.parameters()

    # Compute B_ideal using cctbx
    cctbx_cell = uctbx.unit_cell((a, b, c, alpha_deg, beta_deg, gamma_deg))
    B_ideal_flat = np.array(cctbx_cell.fractionalization_matrix())
    B_ideal = B_ideal_flat.reshape(3, 3).T  # Transpose to match MOSFLM convention

    # Derive U from A* and B_ideal
    U_from_dxtbx = A_star @ np.linalg.inv(B_ideal)

    # Compute determinants
    det_A = float(np.linalg.det(A_star))
    det_B = float(np.linalg.det(B_ideal))
    det_U = float(np.linalg.det(U_from_dxtbx))

    # Isotropic scale (cube root of det)
    s_isotropic = det_U ** (1.0 / 3.0)

    # Validate identity: A* ≈ U @ B_ideal
    A_star_reconstructed = U_from_dxtbx @ B_ideal
    max_abs_diff = float(np.max(np.abs(A_star - A_star_reconstructed)))

    # Check for crystal.get_B() API
    has_get_B = hasattr(crystal, 'get_B')
    B_dxtbx_match = None
    if has_get_B:
        B_dxtbx_tuple = crystal.get_B()
        B_dxtbx = np.array(B_dxtbx_tuple).reshape(3, 3)
        B_dxtbx_match = float(np.max(np.abs(B_ideal - B_dxtbx)))

    # Assemble report
    report = {
        "experiment_path": args.expt,
        "cell_parameters": {
            "a": float(a),
            "b": float(b),
            "c": float(c),
            "alpha_deg": float(alpha_deg),
            "beta_deg": float(beta_deg),
            "gamma_deg": float(gamma_deg)
        },
        "det_A_star": det_A,
        "det_B_ideal": det_B,
        "det_U_from_dxtbx": det_U,
        "isotropic_scale_factor": s_isotropic,
        "volume_offset_percent": 100.0 * (det_U - 1.0),
        "A_star_identity_max_abs_diff": max_abs_diff,
        "dxtbx_has_get_B": has_get_B,
        "B_dxtbx_vs_B_ideal_max_diff": B_dxtbx_match
    }

    with open(args.out, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"dxtbx audit complete. det(U)={det_U:.6f}, isotropic_scale={s_isotropic:.6f}")
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()
