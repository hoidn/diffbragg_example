#!/usr/bin/env python3
"""
TORCH-REFINE-002E — Crystal Matrix Parity Probe.

Phase A helper to diagnose the geometry branch gap between:
  - Path A: MOSFLM A* injection (mapping geometry used by simulate_forward_once)
  - Path B: Explicit cell + baseline misset parameterization used by Stage A

The script:
  1. Builds a canonical DataLoad on the refGeom assets.
  2. Constructs a nanobrag_torch Crystal via Path A using create_crystal_config
     with MOSFLM A* injection enabled (crystal_overrides=None, misset_deg=[0,0,0]).
  3. Constructs a Crystal via Path B using explicit cell overrides and the current
     baseline misset logic (baseline_misset_deg + delta=0).
  4. Extracts reciprocal matrices A*_A and A*_B from nanobrag_torch via
     Crystal.compute_cell_tensors() and forms:

         U_error = A*_A @ (A*_B)^{-1}

  5. Emits diagnostics (Frobenius norm, max|Δ|, det(U_error)) and writes a JSON
     report under:

       plans/active/TORCH-REFINE-002E/reports/<timestamp>/crystal_matrix_parity.json

Exit criterion (Phase A):
  - max|A*_A - A*_B| <= 1e-6 and U_error ~ Identity (rotation-only gap below
    floating point noise) after the TORCH-REFINE-002E fixes land.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class MatrixParitySummary:
    """Summary statistics for A* matrix parity."""

    max_abs_diff: float
    frobenius_norm_diff: float
    det_u_error: float
    u_error_is_rotation: bool


def _build_dataload() -> "DataLoad":
    """Construct a DataLoad on canonical refGeom or refined fixtures."""
    from dbex.data_load import DataLoad  # type: ignore

    fixtures_root = (
        REPO_ROOT / "tests" / "fixtures" / "golden_data" / "simple_cubic"
    )
    refined_expt = fixtures_root / "refined.expt"
    refined_refl = fixtures_root / "refined.refl"

    legacy_expt = REPO_ROOT / "refGeom.expt"
    legacy_refl = REPO_ROOT / "refGeom.refl"

    if refined_expt.exists() and refined_refl.exists():
        expt = refined_expt
        refl = refined_refl
    else:
        expt = legacy_expt
        refl = legacy_refl

    mtz = REPO_ROOT / "scaled.mtz"
    mask = REPO_ROOT / "747_mask.pkl"

    args = argparse.Namespace(
        exptName=str(expt),
        reflName=str(refl),
        exptIdx=0,
        mtzFile=str(mtz),
        mtzCol="F,SIGF",
        maskFile=str(mask),
    )
    return DataLoad(args)


def _compute_a_star_matrix(crystal_nb) -> np.ndarray:
    """Extract A* (a*,b*,c* as columns) from a nanobrag_torch Crystal."""
    geom = crystal_nb.compute_cell_tensors()
    a_star = geom["a_star"].detach().cpu().numpy().reshape(3)
    b_star = geom["b_star"].detach().cpu().numpy().reshape(3)
    c_star = geom["c_star"].detach().cpu().numpy().reshape(3)
    return np.column_stack([a_star, b_star, c_star]).astype(np.float64)


def run_probe(device: str = "cpu") -> Dict[str, object]:
    """Run the parity probe and return the payload."""
    from dbex.nanobrag_bridge import create_crystal_config, compute_baseline_misset_deg
    from nanobrag_torch.models.crystal import Crystal as TorchCrystal  # type: ignore
    import torch  # type: ignore

    dataload = _build_dataload()
    crystal = dataload.crystal
    experiment = dataload.Expt

    # Path A: MOSFLM A* injection (mapping geometry: simulate_forward_once)
    crystal_cfg_A, _ = create_crystal_config(
        crystal,
        experiment,
        N_cells=None,
        apply_n_cells=False,
        crystal_overrides=None,
        misset_deg_override=None,
    )
    crystal_nb_A = TorchCrystal(
        crystal_cfg_A, beam_config=None, device=torch.device(device)
    )
    a_star_A = _compute_a_star_matrix(crystal_nb_A)

    # Path B: explicit cell + baseline misset (Stage A parameterization at zero deltas)
    # Baseline misset in XYZ Euler degrees, aligned to nanobrag's internal B_ideal.
    # Use the mapping-aligned robust derivation (baseline_crystal=None) so that
    # the zero-parameter Stage A geometry is defined as B_ideal rotated to match
    # the DB-AT-024 mapping orientation.
    baseline_misset_deg = compute_baseline_misset_deg(
        crystal,
        None,
        device=torch.device(device),
        dtype=torch.float64,
    )

    cell_params = crystal.get_unit_cell().parameters()
    import torch as _torch  # type: ignore

    crystal_overrides = {
        "cell_a": _torch.tensor(cell_params[0], dtype=_torch.float64),
        "cell_b": _torch.tensor(cell_params[1], dtype=_torch.float64),
        "cell_c": _torch.tensor(cell_params[2], dtype=_torch.float64),
        "cell_alpha": _torch.tensor(cell_params[3], dtype=_torch.float64),
        "cell_beta": _torch.tensor(cell_params[4], dtype=_torch.float64),
        "cell_gamma": _torch.tensor(cell_params[5], dtype=_torch.float64),
    }

    crystal_cfg_B, _ = create_crystal_config(
        crystal,
        experiment,
        N_cells=None,
        apply_n_cells=False,
        crystal_overrides=crystal_overrides,
        misset_deg_override=baseline_misset_deg,
    )
    crystal_nb_B = TorchCrystal(
        crystal_cfg_B, beam_config=None, device=torch.device(device)
    )
    a_star_B = _compute_a_star_matrix(crystal_nb_B)

    # Compute parity metrics
    diff = a_star_A - a_star_B
    max_abs_diff = float(np.max(np.abs(diff)))
    fro_norm = float(np.linalg.norm(diff))

    try:
        a_star_B_inv = np.linalg.inv(a_star_B)
    except np.linalg.LinAlgError:
        a_star_B_inv = np.linalg.pinv(a_star_B)

    u_error = a_star_A @ a_star_B_inv
    det_u = float(np.linalg.det(u_error))
    u_u, _, u_vt = np.linalg.svd(u_error)
    r_proj = u_u @ u_vt
    rot_gap = float(np.linalg.norm(u_error - r_proj))
    u_error_is_rotation = bool(
        abs(det_u - 1.0) < 1e-6 and rot_gap < 1e-6
    )

    summary = MatrixParitySummary(
        max_abs_diff=max_abs_diff,
        frobenius_norm_diff=fro_norm,
        det_u_error=det_u,
        u_error_is_rotation=u_error_is_rotation,
    )

    payload: Dict[str, object] = {
        "summary": asdict(summary),
        "a_star_path_A": a_star_A.tolist(),
        "a_star_path_B": a_star_B.tolist(),
        "u_error": u_error.tolist(),
        "rot_gap_norm": rot_gap,
    }
    return payload


def _default_output_dir() -> Path:
    """Create a timestamped reports directory for this probe."""
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_root = (
        REPO_ROOT
        / "plans"
        / "active"
        / "TORCH-REFINE-002E"
        / "reports"
        / timestamp
    )
    out_root.mkdir(parents=True, exist_ok=True)
    return out_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Probe parity between MOSFLM A* and explicit cell + baseline misset."
    )
    parser.add_argument(
        "--device",
        default=os.environ.get("DBEX_PROBE_DEVICE", "cpu"),
        help="Torch device string (default: cpu).",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default=None,
        help="Optional output directory for JSON report. "
        "Defaults to a timestamped directory under "
        "plans/active/TORCH-REFINE-002E/reports/.",
    )

    args = parser.parse_args(argv)

    try:
        payload = run_probe(device=args.device)
    except Exception as exc:  # pragma: no cover - diagnostic helper
        print(f"[probe_crystal_matrix_parity] ERROR: {exc}")
        return 1

    out_dir = Path(args.out_dir) if args.out_dir is not None else _default_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "crystal_matrix_parity.json"
    out_path.write_text(json.dumps(payload, indent=2))

    summary = payload.get("summary", {})
    print(
        "[probe_crystal_matrix_parity] max_abs_diff={max_abs_diff:.3e}, "
        "fro_norm={frobenius_norm_diff:.3e}, det(U_error)={det_u_error:.6f}, "
        "u_error_is_rotation={u_error_is_rotation}".format(**summary)
    )
    print(f"[probe_crystal_matrix_parity] wrote report to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
