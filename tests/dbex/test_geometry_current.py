"""
Unit tests for geometry functions in CURRENT location (dbex/nanobrag_bridge.py).

Phase 0 test discipline baseline per ARCH-REFACTOR-001:80-89.
Tests written against CURRENT code before Phase A refactoring to provide safety net.
"""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation


@pytest.fixture
def synthetic_ub_system():
    """
    Create synthetic U (orthogonal) and B_ideal (from cell) for roundtrip testing.

    Returns tuple of (U, B_ideal, cell, A_star) where:
    - U: 3x3 orthogonal matrix with det(U) = +1
    - B_ideal: 3x3 upper triangular reciprocal basis from nanobrag_torch
    - cell: (a, b, c, alpha, beta, gamma) in Angstroms and degrees
    - A_star: U @ B_ideal (MOSFLM convention)
    """
    # Use realistic crystal cell parameters (monoclinic, similar to refGeom.expt)
    cell = (78.9, 79.4, 38.7, 90.0, 90.2, 90.0)  # a, b, c, alpha, beta, gamma

    # Create random orthogonal U matrix with det(U) = +1
    # Use scipy.spatial.transform.Rotation for guaranteed SO(3) matrix
    random_euler = np.array([45.0, 30.0, 60.0])  # degrees
    rot = Rotation.from_euler('xyz', random_euler, degrees=True)
    U = rot.as_matrix()

    # Verify U is proper rotation (orthogonal + det=1)
    assert np.allclose(U.T @ U, np.eye(3), atol=1e-12), "U not orthogonal"
    det_u = np.linalg.det(U)
    assert np.isclose(det_u, 1.0, atol=1e-12), f"det(U) = {det_u}, expected 1.0"

    # Compute B_ideal using nanobrag_torch (same as derive_u_matrix_from_mosflm_a_star)
    from nanobrag_torch.config import CrystalConfig as TorchCrystalConfig
    from nanobrag_torch.models.crystal import Crystal as TorchCrystal
    import torch

    a, b, c, alpha, beta, gamma = cell
    cfg = TorchCrystalConfig(
        cell_a=a, cell_b=b, cell_c=c,
        cell_alpha=alpha, cell_beta=beta, cell_gamma=gamma,
        misset_deg=(0.0, 0.0, 0.0),
        mosflm_a_star=None, mosflm_b_star=None, mosflm_c_star=None,
    )
    crystal_nb = TorchCrystal(cfg, device=torch.device("cpu"), dtype=torch.float64)
    geom = crystal_nb.compute_cell_tensors()
    a_star_nb = geom["a_star"].detach().cpu().numpy().reshape(3)
    b_star_nb = geom["b_star"].detach().cpu().numpy().reshape(3)
    c_star_nb = geom["c_star"].detach().cpu().numpy().reshape(3)
    B_ideal = np.column_stack([a_star_nb, b_star_nb, c_star_nb]).astype(np.float64)

    # Construct A* = U @ B_ideal
    A_star = U @ B_ideal

    return U, B_ideal, cell, A_star


def test_derive_u_matrix_roundtrip(synthetic_ub_system):
    """
    Test derive_u_matrix_from_mosflm_a_star roundtrip: A* → (U, B_ideal) → A*.

    Acceptance criteria per ARCH-REFACTOR-001:0.1 and GEOMETRY-003:
    1. U_derived is orthogonal: U.T @ U ≈ I within 1e-6
    2. det(U_derived) ≈ ±1 within 1e-6 (proper rotation, may have strain)
    3. A* reconstruction: U_derived @ B_ideal_derived ≈ A* within 1e-6

    References:
    - docs/spec-db-workflow.md:39 (Stage A mapping zero-point invariant)
    - docs/config_crosswalk.md (MOSFLM A* = U @ B_ideal)
    - docs/findings.md GEOMETRY-003 (B_ideal convention)
    """
    from dbex.nanobrag_bridge import derive_u_matrix_from_mosflm_a_star

    U_expected, B_ideal_expected, cell, A_star = synthetic_ub_system

    # Call function under test
    U_derived, B_ideal_derived = derive_u_matrix_from_mosflm_a_star(A_star, cell)

    # Assertion 1: U_derived is orthogonal (U.T @ U ≈ I)
    U_T_U = U_derived.T @ U_derived
    np.testing.assert_allclose(
        U_T_U, np.eye(3), atol=1e-6,
        err_msg="U_derived is not orthogonal (U.T @ U != I)"
    )

    # Assertion 2: det(U_derived) ≈ ±1 (proper rotation or reflection)
    det_u_derived = np.linalg.det(U_derived)
    assert (
        np.isclose(det_u_derived, 1.0, atol=1e-6) or
        np.isclose(det_u_derived, -1.0, atol=1e-6)
    ), f"det(U_derived) = {det_u_derived}, expected ±1"

    # Assertion 3: A* reconstruction (U_derived @ B_ideal_derived ≈ A*)
    A_star_reconstructed = U_derived @ B_ideal_derived
    np.testing.assert_allclose(
        A_star_reconstructed, A_star, atol=1e-6,
        err_msg="A* reconstruction failed (U @ B_ideal != A*)"
    )

    # Additional check: B_ideal consistency (derived B_ideal should match expected)
    # NOTE: B_ideal is computed from cell params, so should be identical
    np.testing.assert_allclose(
        B_ideal_derived, B_ideal_expected, atol=1e-12,
        err_msg="B_ideal_derived does not match expected B_ideal from cell params"
    )


def test_derive_u_matrix_edge_case_identity():
    """
    Test derive_u_matrix with identity orientation (U = I).

    Edge case: When U = I, A* = B_ideal exactly, so derived U should be I.
    """
    from dbex.nanobrag_bridge import derive_u_matrix_from_mosflm_a_star

    # Simple cubic cell (a=b=c=10 Å, all angles 90°)
    cell = (10.0, 10.0, 10.0, 90.0, 90.0, 90.0)

    # Compute B_ideal for this cell
    from nanobrag_torch.config import CrystalConfig as TorchCrystalConfig
    from nanobrag_torch.models.crystal import Crystal as TorchCrystal
    import torch

    a, b, c, alpha, beta, gamma = cell
    cfg = TorchCrystalConfig(
        cell_a=a, cell_b=b, cell_c=c,
        cell_alpha=alpha, cell_beta=beta, cell_gamma=gamma,
        misset_deg=(0.0, 0.0, 0.0),
        mosflm_a_star=None, mosflm_b_star=None, mosflm_c_star=None,
    )
    crystal_nb = TorchCrystal(cfg, device=torch.device("cpu"), dtype=torch.float64)
    geom = crystal_nb.compute_cell_tensors()
    a_star_nb = geom["a_star"].detach().cpu().numpy().reshape(3)
    b_star_nb = geom["b_star"].detach().cpu().numpy().reshape(3)
    c_star_nb = geom["c_star"].detach().cpu().numpy().reshape(3)
    B_ideal = np.column_stack([a_star_nb, b_star_nb, c_star_nb]).astype(np.float64)

    # A* = I @ B_ideal = B_ideal
    A_star = B_ideal.copy()

    # Derive U
    U_derived, B_ideal_derived = derive_u_matrix_from_mosflm_a_star(A_star, cell)

    # U should be identity
    np.testing.assert_allclose(
        U_derived, np.eye(3), atol=1e-6,
        err_msg="U_derived should be identity when A* = B_ideal"
    )
