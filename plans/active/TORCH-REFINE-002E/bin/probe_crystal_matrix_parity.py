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
from scipy.linalg import logm  # type: ignore

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
    # Extended diagnostics (Phase A0)
    a_star_pathA_eigenvalues: list[float]
    a_star_pathB_eigenvalues: list[float]
    a_star_pathA_singular_values: list[float]
    a_star_pathB_singular_values: list[float]
    log_u_symmetric_norm: float
    log_u_antisymmetric_norm: float
    reciprocal_column_norms: dict[str, dict[str, float]]
    reciprocal_column_angles: dict[str, float]


@dataclass
class PathBVariantSummary:
    """Summary for a single Path-B variant (Phase A2)."""

    variant_name: str
    max_abs_diff: float
    frobenius_norm_diff: float
    det_u_error: float
    u_error_is_rotation: bool
    log_u_symmetric_norm: float
    log_u_antisymmetric_norm: float
    baseline_misset_deg: list[float]


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


def _build_b_ideal_from_cell_params(
    cell_params: tuple[float, float, float, float, float, float],
    device: str = "cpu",
) -> np.ndarray:
    """
    Build a B_ideal matrix from unit cell parameters using nanobrag_torch.

    Args:
        cell_params: Tuple (a, b, c, alpha_deg, beta_deg, gamma_deg).
        device: Torch device string.

    Returns:
        3×3 numpy array with reciprocal vectors (a*, b*, c*) as columns.
    """
    from nanobrag_torch.config import CrystalConfig as TorchCrystalConfig
    from nanobrag_torch.models.crystal import Crystal as TorchCrystal
    import torch

    a, b, c, alpha, beta, gamma = cell_params
    cfg = TorchCrystalConfig(
        cell_a=a,
        cell_b=b,
        cell_c=c,
        cell_alpha=alpha,
        cell_beta=beta,
        cell_gamma=gamma,
        misset_deg=(0.0, 0.0, 0.0),
        mosflm_a_star=None,
        mosflm_b_star=None,
        mosflm_c_star=None,
    )
    crystal_nb = TorchCrystal(cfg, device=torch.device(device), dtype=torch.float64)
    geom = crystal_nb.compute_cell_tensors()
    a_star = geom["a_star"].detach().cpu().numpy().reshape(3)
    b_star = geom["b_star"].detach().cpu().numpy().reshape(3)
    c_star = geom["c_star"].detach().cpu().numpy().reshape(3)
    return np.column_stack([a_star, b_star, c_star]).astype(np.float64)


def compute_extended_diagnostics(
    a_star_pathA: np.ndarray,
    a_star_pathB: np.ndarray,
    u_error: np.ndarray,
) -> Dict[str, object]:
    """
    Compute extended diagnostics to decompose the A* gap into rotation vs strain.

    Diagnostics:
    - Eigenvalues of A*_A and A*_B (symmetric part)
    - Singular values of A*_A and A*_B
    - Symmetric/antisymmetric decomposition of logm(U_error)
    - Per-column norms and inter-column angles for reciprocal vectors

    Returns dict with keys matching MatrixParitySummary extended fields.
    """
    # Eigenvalues (use eigvalsh for symmetric part; for full matrix use eig)
    # Since A* matrices are generally not symmetric, use eig for full eigendecomposition
    eigvals_A = np.linalg.eigvals(a_star_pathA)
    eigvals_B = np.linalg.eigvals(a_star_pathB)
    # Sort by magnitude for consistent reporting
    eigvals_A = np.sort(np.abs(eigvals_A))[::-1]
    eigvals_B = np.sort(np.abs(eigvals_B))[::-1]

    # Singular values
    _, svals_A, _ = np.linalg.svd(a_star_pathA)
    _, svals_B, _ = np.linalg.svd(a_star_pathB)

    # Logarithmic map decomposition
    log_u = logm(u_error)
    # Handle potential complex results from logm (should be real for near-rotations)
    if np.iscomplexobj(log_u):
        log_u = np.real(log_u)

    log_u_symmetric = 0.5 * (log_u + log_u.T)
    log_u_antisymmetric = 0.5 * (log_u - log_u.T)

    log_u_symmetric_norm = float(np.linalg.norm(log_u_symmetric))
    log_u_antisymmetric_norm = float(np.linalg.norm(log_u_antisymmetric))

    # Per-column norms for reciprocal vectors a*, b*, c*
    col_norms_A = {
        "a_star": float(np.linalg.norm(a_star_pathA[:, 0])),
        "b_star": float(np.linalg.norm(a_star_pathA[:, 1])),
        "c_star": float(np.linalg.norm(a_star_pathA[:, 2])),
    }
    col_norms_B = {
        "a_star": float(np.linalg.norm(a_star_pathB[:, 0])),
        "b_star": float(np.linalg.norm(a_star_pathB[:, 1])),
        "c_star": float(np.linalg.norm(a_star_pathB[:, 2])),
    }

    # Inter-column angles (in degrees) between corresponding vectors
    def angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
        """Compute angle in degrees between two vectors."""
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        # Clamp to [-1, 1] to handle numerical errors
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        return float(np.degrees(np.arccos(cos_angle)))

    col_angles = {
        "a_star_angle_deg": angle_between(
            a_star_pathA[:, 0], a_star_pathB[:, 0]
        ),
        "b_star_angle_deg": angle_between(
            a_star_pathA[:, 1], a_star_pathB[:, 1]
        ),
        "c_star_angle_deg": angle_between(
            a_star_pathA[:, 2], a_star_pathB[:, 2]
        ),
    }

    return {
        "a_star_pathA_eigenvalues": eigvals_A.tolist(),
        "a_star_pathB_eigenvalues": eigvals_B.tolist(),
        "a_star_pathA_singular_values": svals_A.tolist(),
        "a_star_pathB_singular_values": svals_B.tolist(),
        "log_u_symmetric_norm": log_u_symmetric_norm,
        "log_u_antisymmetric_norm": log_u_antisymmetric_norm,
        "reciprocal_column_norms": {
            "pathA": col_norms_A,
            "pathB": col_norms_B,
        },
        "reciprocal_column_angles": col_angles,
    }


def _compute_path_b_variant_metrics(
    variant_name: str,
    a_star_A: np.ndarray,
    a_star_B: np.ndarray,
    baseline_misset_deg: np.ndarray,
) -> PathBVariantSummary:
    """
    Compute parity metrics for a single Path-B variant.

    Args:
        variant_name: Identifier for this variant (e.g., "PathB_unitcell").
        a_star_A: 3×3 numpy array from Path A (MOSFLM A* injection).
        a_star_B: 3×3 numpy array from Path B variant.
        baseline_misset_deg: Baseline misset angles used for this variant.

    Returns:
        PathBVariantSummary with key metrics.
    """
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
    u_error_is_rotation = bool(abs(det_u - 1.0) < 1e-6 and rot_gap < 1e-6)

    # Symmetric/antisymmetric decomposition of logm(U_error)
    log_u = logm(u_error)
    if np.iscomplexobj(log_u):
        log_u = np.real(log_u)
    log_u_symmetric = 0.5 * (log_u + log_u.T)
    log_u_symmetric_norm = float(np.linalg.norm(log_u_symmetric))
    log_u_antisymmetric = 0.5 * (log_u - log_u.T)
    log_u_antisymmetric_norm = float(np.linalg.norm(log_u_antisymmetric))

    return PathBVariantSummary(
        variant_name=variant_name,
        max_abs_diff=max_abs_diff,
        frobenius_norm_diff=fro_norm,
        det_u_error=det_u,
        u_error_is_rotation=u_error_is_rotation,
        log_u_symmetric_norm=log_u_symmetric_norm,
        log_u_antisymmetric_norm=log_u_antisymmetric_norm,
        baseline_misset_deg=baseline_misset_deg.tolist() if isinstance(baseline_misset_deg, np.ndarray) else list(baseline_misset_deg),
    )


def run_probe(device: str = "cpu") -> Dict[str, object]:
    """
    Run the parity probe with Phase A2 baseline B_ideal variants.

    Builds three crystal configs:
    - Path A: MOSFLM A* injection (mapping zero point)
    - Path B (unitcell): Explicit cell + baseline misset using dxtbx unit cell B_ideal
    - Path B (recovered): Explicit cell + baseline misset using recovered cell from MOSFLM A*

    Returns a JSON payload with side-by-side comparison of both Path-B variants.
    """
    from dbex.nanobrag_bridge import (
        create_crystal_config,
        compute_baseline_misset_deg,
        derive_robust_misset,
        recover_cell_from_a_star,
        derive_b_ideal_from_mosflm_a_star,
    )
    from nanobrag_torch.models.crystal import Crystal as TorchCrystal
    import torch

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

    # Path B (unitcell): Explicit cell + baseline misset using dxtbx unit cell B_ideal
    baseline_misset_unitcell = compute_baseline_misset_deg(
        crystal,
        None,
        device=torch.device(device),
        dtype=torch.float64,
    )
    if isinstance(baseline_misset_unitcell, torch.Tensor):
        baseline_misset_unitcell_np = baseline_misset_unitcell.detach().cpu().numpy()
    else:
        baseline_misset_unitcell_np = np.asarray(baseline_misset_unitcell, dtype=np.float64)

    cell_params = crystal.get_unit_cell().parameters()
    crystal_overrides_unitcell = {
        "cell_a": torch.tensor(cell_params[0], dtype=torch.float64),
        "cell_b": torch.tensor(cell_params[1], dtype=torch.float64),
        "cell_c": torch.tensor(cell_params[2], dtype=torch.float64),
        "cell_alpha": torch.tensor(cell_params[3], dtype=torch.float64),
        "cell_beta": torch.tensor(cell_params[4], dtype=torch.float64),
        "cell_gamma": torch.tensor(cell_params[5], dtype=torch.float64),
    }

    crystal_cfg_B_unitcell, _ = create_crystal_config(
        crystal,
        experiment,
        N_cells=None,
        apply_n_cells=False,
        crystal_overrides=crystal_overrides_unitcell,
        misset_deg_override=baseline_misset_unitcell,
    )
    crystal_nb_B_unitcell = TorchCrystal(
        crystal_cfg_B_unitcell, beam_config=None, device=torch.device(device)
    )
    a_star_B_unitcell = _compute_a_star_matrix(crystal_nb_B_unitcell)

    # Path B (recovered): Recover cell from MOSFLM A* and build alternative B_ideal
    recovered_cell_params = recover_cell_from_a_star(a_star_A)
    b_ideal_recovered = _build_b_ideal_from_cell_params(recovered_cell_params, device=device)

    # Derive misset using the recovered B_ideal
    baseline_misset_recovered = derive_robust_misset(
        crystal,
        crystal_nanobrag_default=None,
        device=torch.device(device),
        dtype=torch.float64,
        b_ideal_override=b_ideal_recovered,
    )
    if isinstance(baseline_misset_recovered, torch.Tensor):
        baseline_misset_recovered_np = baseline_misset_recovered.detach().cpu().numpy()
    else:
        baseline_misset_recovered_np = np.asarray(baseline_misset_recovered, dtype=np.float64)

    # Build crystal config with recovered cell params
    crystal_overrides_recovered = {
        "cell_a": torch.tensor(recovered_cell_params[0], dtype=torch.float64),
        "cell_b": torch.tensor(recovered_cell_params[1], dtype=torch.float64),
        "cell_c": torch.tensor(recovered_cell_params[2], dtype=torch.float64),
        "cell_alpha": torch.tensor(recovered_cell_params[3], dtype=torch.float64),
        "cell_beta": torch.tensor(recovered_cell_params[4], dtype=torch.float64),
        "cell_gamma": torch.tensor(recovered_cell_params[5], dtype=torch.float64),
    }

    crystal_cfg_B_recovered, _ = create_crystal_config(
        crystal,
        experiment,
        N_cells=None,
        apply_n_cells=False,
        crystal_overrides=crystal_overrides_recovered,
        misset_deg_override=baseline_misset_recovered,
    )
    crystal_nb_B_recovered = TorchCrystal(
        crystal_cfg_B_recovered, beam_config=None, device=torch.device(device)
    )
    a_star_B_recovered = _compute_a_star_matrix(crystal_nb_B_recovered)

    # Compute metrics for both Path-B variants
    variant_unitcell = _compute_path_b_variant_metrics(
        "PathB_unitcell",
        a_star_A,
        a_star_B_unitcell,
        baseline_misset_unitcell_np,
    )
    variant_recovered = _compute_path_b_variant_metrics(
        "PathB_recovered",
        a_star_A,
        a_star_B_recovered,
        baseline_misset_recovered_np,
    )

    # Path B (mapping_aligned): Use use_mapping_b_ideal=True per Phase C1 Branch G
    baseline_misset_mapping = derive_robust_misset(
        crystal,
        crystal_nanobrag_default=None,
        device=torch.device(device),
        dtype=torch.float64,
        use_mapping_b_ideal=True,
    )
    if isinstance(baseline_misset_mapping, torch.Tensor):
        baseline_misset_mapping_np = baseline_misset_mapping.detach().cpu().numpy()
    else:
        baseline_misset_mapping_np = np.asarray(baseline_misset_mapping, dtype=np.float64)

    # CRITICAL: Use the RECOVERED cell params for the explicit cell overrides
    # when using mapping-aligned baseline misset. The mapping A* encodes an effective
    # cell that differs slightly from the dxtbx unit cell. Using the recovered cell
    # ensures the explicit cell+misset path matches the mapping path.
    recovered_cell_params_for_mapping = recover_cell_from_a_star(a_star_A)
    crystal_overrides_mapping = {
        "cell_a": torch.tensor(recovered_cell_params_for_mapping[0], dtype=torch.float64),
        "cell_b": torch.tensor(recovered_cell_params_for_mapping[1], dtype=torch.float64),
        "cell_c": torch.tensor(recovered_cell_params_for_mapping[2], dtype=torch.float64),
        "cell_alpha": torch.tensor(recovered_cell_params_for_mapping[3], dtype=torch.float64),
        "cell_beta": torch.tensor(recovered_cell_params_for_mapping[4], dtype=torch.float64),
        "cell_gamma": torch.tensor(recovered_cell_params_for_mapping[5], dtype=torch.float64),
    }
    crystal_cfg_B_mapping, _ = create_crystal_config(
        crystal,
        experiment,
        N_cells=None,
        apply_n_cells=False,
        crystal_overrides=crystal_overrides_mapping,
        misset_deg_override=baseline_misset_mapping,
    )
    crystal_nb_B_mapping = TorchCrystal(
        crystal_cfg_B_mapping, beam_config=None, device=torch.device(device)
    )
    a_star_B_mapping = _compute_a_star_matrix(crystal_nb_B_mapping)

    variant_mapping = _compute_path_b_variant_metrics(
        "PathB_mapping_aligned",
        a_star_A,
        a_star_B_mapping,
        baseline_misset_mapping_np,
    )

    # Also compute the full extended diagnostics for the unitcell variant (legacy output)
    diff = a_star_A - a_star_B_unitcell
    max_abs_diff = float(np.max(np.abs(diff)))
    fro_norm = float(np.linalg.norm(diff))

    try:
        a_star_B_inv = np.linalg.inv(a_star_B_unitcell)
    except np.linalg.LinAlgError:
        a_star_B_inv = np.linalg.pinv(a_star_B_unitcell)

    u_error = a_star_A @ a_star_B_inv
    det_u = float(np.linalg.det(u_error))
    u_u, _, u_vt = np.linalg.svd(u_error)
    r_proj = u_u @ u_vt
    rot_gap = float(np.linalg.norm(u_error - r_proj))
    u_error_is_rotation = bool(abs(det_u - 1.0) < 1e-6 and rot_gap < 1e-6)

    # Compute extended diagnostics for the unitcell variant
    extended = compute_extended_diagnostics(a_star_A, a_star_B_unitcell, u_error)

    summary = MatrixParitySummary(
        max_abs_diff=max_abs_diff,
        frobenius_norm_diff=fro_norm,
        det_u_error=det_u,
        u_error_is_rotation=u_error_is_rotation,
        a_star_pathA_eigenvalues=extended["a_star_pathA_eigenvalues"],
        a_star_pathB_eigenvalues=extended["a_star_pathB_eigenvalues"],
        a_star_pathA_singular_values=extended["a_star_pathA_singular_values"],
        a_star_pathB_singular_values=extended["a_star_pathB_singular_values"],
        log_u_symmetric_norm=extended["log_u_symmetric_norm"],
        log_u_antisymmetric_norm=extended["log_u_antisymmetric_norm"],
        reciprocal_column_norms=extended["reciprocal_column_norms"],
        reciprocal_column_angles=extended["reciprocal_column_angles"],
    )

    payload: Dict[str, object] = {
        "summary": asdict(summary),  # Legacy format (PathB_unitcell)
        "a_star_path_A": a_star_A.tolist(),
        "a_star_path_B": a_star_B_unitcell.tolist(),  # Legacy unitcell variant
        "u_error": u_error.tolist(),
        "rot_gap_norm": rot_gap,
        # Phase A2 additions:
        "path_B_unitcell": asdict(variant_unitcell),
        "path_B_recovered": asdict(variant_recovered),
        # Phase C1 Branch G addition:
        "path_B_mapping_aligned": asdict(variant_mapping),
        "recovered_cell_params": {
            "a": recovered_cell_params[0],
            "b": recovered_cell_params[1],
            "c": recovered_cell_params[2],
            "alpha_deg": recovered_cell_params[3],
            "beta_deg": recovered_cell_params[4],
            "gamma_deg": recovered_cell_params[5],
        },
        "dxtbx_cell_params": {
            "a": cell_params[0],
            "b": cell_params[1],
            "c": cell_params[2],
            "alpha_deg": cell_params[3],
            "beta_deg": cell_params[4],
            "gamma_deg": cell_params[5],
        },
    }
    return payload


def _default_output_dir() -> Path:
    """Create a timestamped reports directory for this probe."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
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
    path_b_unitcell = payload.get("path_B_unitcell", {})
    path_b_recovered = payload.get("path_B_recovered", {})
    path_b_mapping = payload.get("path_B_mapping_aligned", {})

    print("[probe_crystal_matrix_parity] Legacy summary (PathB_unitcell):")
    print(
        "  max_abs_diff={max_abs_diff:.3e}, "
        "fro_norm={frobenius_norm_diff:.3e}, det(U_error)={det_u_error:.6f}, "
        "u_error_is_rotation={u_error_is_rotation}".format(**summary)
    )
    print("\n[probe_crystal_matrix_parity] Phase A2/C1 Comparison:")
    print(
        f"  PathB_unitcell:       log_u_symmetric_norm={path_b_unitcell.get('log_u_symmetric_norm', 0):.3e}, "
        f"max_abs_diff={path_b_unitcell.get('max_abs_diff', 0):.3e}"
    )
    print(
        f"  PathB_recovered:      log_u_symmetric_norm={path_b_recovered.get('log_u_symmetric_norm', 0):.3e}, "
        f"max_abs_diff={path_b_recovered.get('max_abs_diff', 0):.3e}"
    )
    print(
        f"  PathB_mapping_aligned: log_u_symmetric_norm={path_b_mapping.get('log_u_symmetric_norm', 0):.3e}, "
        f"max_abs_diff={path_b_mapping.get('max_abs_diff', 0):.3e}"
    )
    print(f"\n[probe_crystal_matrix_parity] wrote report to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
