"""
Pure crystallographic math functions.

Leaf-node module: imports FROM external dependencies (numpy, torch, nanobrag_torch)
but NOT from dbex.nanobrag_* to avoid circular imports.

Functions in this module provide:
- U-matrix extraction from MOSFLM A* matrices
- Cell parameter manipulations
- Crystallographic coordinate transformations

All functions are device-agnostic and preserve autograd graphs where applicable.

References:
- docs/architecture.md (leaf module policy)
- GEOMETRY-001 (beam/DetectorConfig invariants)
- GEOMETRY-003 (Stage A misset baseline logic)
- ARCH-ENGINE-002 (module-scope dependency declaration)
"""

from __future__ import annotations
from typing import Tuple
import numpy as np

# Optional torch/nanobrag_torch dependencies (ARCH-ENGINE-002)
# Module-scope imports with guarded try/except ensure diagnostics/tests see drift immediately
try:
    import torch
    from nanobrag_torch.config import CrystalConfig as TorchCrystalConfig
    from nanobrag_torch.models.crystal import Crystal as TorchCrystal
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    torch = None  # type: ignore
    TorchCrystalConfig = None  # type: ignore
    TorchCrystal = None  # type: ignore


def _require_torch_crystal() -> None:
    """
    Raise ImportError if torch/nanobrag_torch are unavailable.

    Preserves the same error message as legacy lazy imports for compatibility.
    """
    if not _TORCH_AVAILABLE:
        raise ImportError(
            "derive_u_matrix_from_mosflm_a_star requires nanobrag_torch and torch"
        )


def derive_u_matrix_from_mosflm_a_star(a_star: np.ndarray, cell: Tuple[float, float, float, float, float, float]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract U-matrix from mapping MOSFLM A* without SO(3) projection (GEOMETRY-004, TORCH-GEOMETRY-PARITY-002).

    Computes the orientation matrix U from the relationship A* = U @ B_ideal_reciprocal,
    where B_ideal_reciprocal is derived from the specified unit cell parameters.
    Unlike `derive_robust_misset`, this function does NOT call `proper_rotation()` or
    perform any SO(3) projection, preserving any symmetric strain embedded in the
    mapping MOSFLM A* matrix.

    This helper is required for Phase B (TORCH-GEOMETRY-PARITY-002) to enable direct
    U-matrix parameterization in Stage A refinement, avoiding the 1.37e-3 symmetric
    strain artifact introduced by the cell+misset decomposition path.

    Args:
        a_star: 3×3 MOSFLM A* matrix from dxtbx crystal.get_A() (reshaped).
                Columns are reciprocal basis vectors (a*, b*, c*) in 1/Å.
        cell: Tuple of 6 unit cell parameters (a, b, c, alpha, beta, gamma)
              where a, b, c are in Å and angles are in degrees.

    Returns:
        Tuple of (U_matrix, B_ideal_reciprocal), both 3×3 numpy arrays (dtype=float64).
        U_matrix: Orientation matrix from A* = U @ B_ideal relationship (may have det ≈ 1 ± ε if strain present).
        B_ideal_reciprocal: Ideal reciprocal cell matrix from TorchCrystal computation (same source as U extraction).

    Notes:
        - CONVERGENCE-001 bugfix: Both U and B_ideal are derived from the SAME TorchCrystal computation
          to ensure numerical consistency when reconstructing A* = U @ B_ideal.
        - Prior to this fix, callers independently computed B_ideal via cctbx, causing reconstruction errors
          and catastrophic forward model chi-squared (1.425B vs expected ~990k).

    Raises:
        ValueError: If a_star shape is invalid or B_ideal is singular.

    References:
        - docs/spec-db-workflow.md:39 (Stage A mapping zero-point invariant)
        - plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md:146 (Phase B1)
    """
    # Validate inputs
    a_star = np.asarray(a_star, dtype=np.float64)
    if a_star.shape != (3, 3):
        raise ValueError(
            f"a_star must be a 3×3 array, got shape {a_star.shape}"
        )

    # Extract cell parameters
    a, b, c, alpha, beta, gamma = cell

    # Ensure optional dependencies are available (ARCH-ENGINE-002)
    _require_torch_crystal()

    # Build B_ideal_reciprocal using derive_b_ideal_from_mosflm_a_star logic
    # (recover cell from A*, then build nanobrag_torch B_ideal)
    # For U-matrix extraction, we use the provided cell directly instead of
    # recovering from A*, since the caller provides the authoritative cell.

    # Build B_ideal from the provided cell
    cfg = TorchCrystalConfig(
        cell_a=a,
        cell_b=b,
        cell_c=c,
        cell_alpha=alpha,
        cell_beta=beta,
        cell_gamma=gamma,
        misset_deg=(0.0, 0.0, 0.0),
        mosflm_a_star=None,  # No MOSFLM injection for B_ideal
        mosflm_b_star=None,
        mosflm_c_star=None,
    )
    crystal_nb = TorchCrystal(cfg, device=torch.device("cpu"), dtype=torch.float64)
    geom = crystal_nb.compute_cell_tensors()
    a_star_nb = geom["a_star"].detach().cpu().numpy().reshape(3)
    b_star_nb = geom["b_star"].detach().cpu().numpy().reshape(3)
    c_star_nb = geom["c_star"].detach().cpu().numpy().reshape(3)
    B_ideal_reciprocal = np.column_stack([a_star_nb, b_star_nb, c_star_nb]).astype(np.float64)

    # Compute U = A* @ inv(B_ideal_reciprocal)
    # Do NOT call proper_rotation() or any SO(3) projection
    try:
        B_inv = np.linalg.inv(B_ideal_reciprocal)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            f"B_ideal_reciprocal is singular or ill-conditioned: {exc}"
        ) from exc

    U = a_star @ B_inv

    return U, B_ideal_reciprocal
