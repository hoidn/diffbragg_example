"""
DB-AT-026: UB/A* Round-Trip Test Suite

Validates incremental UB parameterization zero-point invariants per:
- spec-db-core.md:61-62 (Zero-point invariant: U(0)=U₀, B(0)=B₀, A*(0)=A*_mapping)
- spec-db-runtime.md:21-23 (UB/A* round-trip correctness check)
- spec-db-workflow.md:40-43 (Mapping zero-point requirement)

Test Suite:
- Test 1: Orientation zero-point (||U(0) - U₀|| < 1e-12)
- Test 2: Cell zero-point (||B(0) - B₀|| < 1e-12)
- Test 3: Mapping parity (||A*(0) - A*_mapping|| < 1e-6)
- Test 4: Gradient flow validation (all params differentiable)
"""

import pytest
import numpy as np
import torch
from pathlib import Path


@pytest.fixture
def canonical_crystal_baseline():
    """Load refGeom.expt and extract U₀, B₀, A*_mapping, cell_baseline."""
    from dxtbx.model import ExperimentList

    workspace_root = Path(__file__).parent.parent.parent
    expt_path = workspace_root / "refGeom.expt"
    if not expt_path.exists():
        pytest.skip(f"refGeom.expt not found at {expt_path}")

    expt = ExperimentList.from_file(str(expt_path))[0]
    crystal = expt.crystal

    # Baseline matrices from dxtbx
    U_baseline = np.array(crystal.get_U()).reshape(3, 3)
    B_baseline = np.array(crystal.get_B()).reshape(3, 3)
    A_star_mapping = U_baseline @ B_baseline

    # Baseline cell parameters
    cell_baseline = crystal.get_unit_cell().parameters()

    return {
        "U_baseline": U_baseline,
        "B_baseline": B_baseline,
        "A_star_mapping": A_star_mapping,
        "cell_baseline": cell_baseline,
    }


@pytest.mark.acceptance
def test_db_at_026_orientation_zero_point(canonical_crystal_baseline):
    """
    DB-AT-026.1: Validate U(0) = U₀ for identity quaternion.

    Requirement: spec-db-core.md:61
    At the Stage-A zero point (all refinement deltas = 0), implementations
    MUST satisfy: U(0) = U₀.

    Acceptance Criterion:
    ||U(0) - U₀|| < 1e-12 for identity quaternion [1,0,0,0]
    """
    from dbex.nanobrag_bridge import derive_orientation_from_quaternion_delta

    U_baseline = canonical_crystal_baseline["U_baseline"]

    # Zero-point orientation: identity quaternion [w, x, y, z]
    q_delta = torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=torch.float64)

    # Derive U(params) at zero point
    U_params = derive_orientation_from_quaternion_delta(
        q_delta,
        U_baseline=torch.tensor(U_baseline, dtype=torch.float64)
    )

    # Convert to numpy for comparison
    U_params_np = U_params.detach().cpu().numpy()

    # Assert: ||U(0) - U₀|| < 1e-12
    error = np.linalg.norm(U_params_np - U_baseline)
    assert error < 1e-12, (
        f"DB-AT-026.1 FAIL: U(0) must equal U₀ (identity quaternion). "
        f"Error: {error:.3e} (threshold: 1e-12)"
    )

    # Validate orthonormality: U^T @ U = I
    identity = U_params_np.T @ U_params_np
    ortho_error = np.linalg.norm(identity - np.eye(3))
    assert ortho_error < 1e-12, (
        f"DB-AT-026.1 FAIL: U(0) must be orthonormal. "
        f"Orthonormality error: {ortho_error:.3e}"
    )

    # Validate determinant: det(U) = 1 (proper rotation)
    det_U = np.linalg.det(U_params_np)
    assert abs(det_U - 1.0) < 1e-12, (
        f"DB-AT-026.1 FAIL: det(U(0)) must equal 1 (proper rotation). "
        f"det(U): {det_U:.6f}"
    )

    print(f"✓ DB-AT-026.1 PASS: ||U(0)-U₀||={error:.3e}, ortho_error={ortho_error:.3e}, det(U)={det_U:.15f}")


@pytest.mark.acceptance
def test_db_at_026_cell_zero_point(canonical_crystal_baseline):
    """
    DB-AT-026.2: Validate B(0) = B₀ for zero cell deltas.

    Requirement: spec-db-core.md:61
    At the Stage-A zero point (all refinement deltas = 0), implementations
    MUST satisfy: B(0) = B₀.

    Acceptance Criterion:
    ||B(0) - B₀|| < 1e-12 for zero cell deltas
    """
    from dbex.nanobrag_bridge import derive_B_from_cell_deltas

    B_baseline = canonical_crystal_baseline["B_baseline"]
    cell_baseline = canonical_crystal_baseline["cell_baseline"]

    # Zero-point cell: zero log-length and angle deltas
    delta_log_a = torch.tensor(0.0, dtype=torch.float64)
    delta_log_b = torch.tensor(0.0, dtype=torch.float64)
    delta_log_c = torch.tensor(0.0, dtype=torch.float64)
    delta_alpha_deg = torch.tensor(0.0, dtype=torch.float64)
    delta_beta_deg = torch.tensor(0.0, dtype=torch.float64)
    delta_gamma_deg = torch.tensor(0.0, dtype=torch.float64)

    # Derive B(params) at zero point
    B_params = derive_B_from_cell_deltas(
        delta_log_a, delta_log_b, delta_log_c,
        delta_alpha_deg, delta_beta_deg, delta_gamma_deg,
        cell_baseline=cell_baseline,
        dtype=torch.float64
    )

    # Convert to numpy for comparison
    B_params_np = B_params.detach().cpu().numpy()

    # Assert: ||B(0) - B₀|| < 1e-12
    error = np.linalg.norm(B_params_np - B_baseline)
    assert error < 1e-12, (
        f"DB-AT-026.2 FAIL: B(0) must equal B₀ (zero cell deltas). "
        f"Error: {error:.3e} (threshold: 1e-12)"
    )

    print(f"✓ DB-AT-026.2 PASS: ||B(0)-B₀||={error:.3e}")


@pytest.mark.acceptance
def test_db_at_026_mapping_parity(canonical_crystal_baseline):
    """
    DB-AT-026.3: Validate A*(0) = A*_mapping for zero params.

    Requirements:
    - spec-db-core.md:62: "A*(0) = U₀ @ B₀ = A*_mapping"
    - spec-db-workflow.md:40: mapping zero-point invariant

    Acceptance Criterion:
    ||A*(0) - A*_mapping|| < 1e-6 (spec allows 1e-6 for mapping parity)
    Implementation quality bonus: error < 1e-12
    """
    from dbex.nanobrag_bridge import (
        derive_orientation_from_quaternion_delta,
        derive_B_from_cell_deltas,
    )

    U_baseline = canonical_crystal_baseline["U_baseline"]
    B_baseline = canonical_crystal_baseline["B_baseline"]
    A_star_mapping = canonical_crystal_baseline["A_star_mapping"]
    cell_baseline = canonical_crystal_baseline["cell_baseline"]

    # Zero-point orientation: identity quaternion
    q_delta = torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=torch.float64)
    U_params = derive_orientation_from_quaternion_delta(
        q_delta,
        U_baseline=torch.tensor(U_baseline, dtype=torch.float64)
    )

    # Zero-point cell: zero deltas
    B_params = derive_B_from_cell_deltas(
        delta_log_a=torch.tensor(0.0, dtype=torch.float64),
        delta_log_b=torch.tensor(0.0, dtype=torch.float64),
        delta_log_c=torch.tensor(0.0, dtype=torch.float64),
        delta_alpha_deg=torch.tensor(0.0, dtype=torch.float64),
        delta_beta_deg=torch.tensor(0.0, dtype=torch.float64),
        delta_gamma_deg=torch.tensor(0.0, dtype=torch.float64),
        cell_baseline=cell_baseline,
        dtype=torch.float64
    )

    # Construct A*(0) = U(0) @ B(0)
    A_star_params = U_params @ B_params

    # Convert to numpy
    A_star_params_np = A_star_params.detach().cpu().numpy()

    # Assert: ||A*(0) - A*_mapping|| < 1e-6
    # (spec-db-core.md:62 allows 1e-6 tolerance for mapping parity)
    error = np.linalg.norm(A_star_params_np - A_star_mapping)
    assert error < 1e-6, (
        f"DB-AT-026.3 FAIL: A*(0) must equal A*_mapping (U₀ @ B₀). "
        f"Error: {error:.3e} (threshold: 1e-6)"
    )

    # Bonus: check if implementation achieves tighter tolerance
    if error < 1e-12:
        print(f"✓ DB-AT-026.3 PASS (bonus): ||A*(0)-A*_mapping||={error:.3e} < 1e-12")
    else:
        print(f"✓ DB-AT-026.3 PASS: ||A*(0)-A*_mapping||={error:.3e} < 1e-6")


@pytest.mark.acceptance
def test_db_at_026_gradient_flow(canonical_crystal_baseline):
    """
    DB-AT-026.4: Validate A*(params) is differentiable w.r.t. all parameters.

    Requirement: spec-db-runtime.md:13 (differentiability)
    All parameterizations SHALL preserve PyTorch autograd graph flow.

    Acceptance Criterion:
    - All parameters have non-None gradients after backward pass
    - Gradient magnitudes are finite (not NaN/inf)
    """
    from dbex.nanobrag_bridge import (
        derive_orientation_from_quaternion_delta,
        derive_B_from_cell_deltas,
    )

    U_baseline = canonical_crystal_baseline["U_baseline"]
    cell_baseline = canonical_crystal_baseline["cell_baseline"]

    # Trainable parameters (small non-zero for gradient test)
    q_delta = torch.tensor([1.0, 0.001, 0.002, 0.003], dtype=torch.float64, requires_grad=True)
    delta_log_a = torch.tensor(0.001, dtype=torch.float64, requires_grad=True)
    delta_log_b = torch.tensor(0.002, dtype=torch.float64, requires_grad=True)
    delta_log_c = torch.tensor(0.003, dtype=torch.float64, requires_grad=True)
    delta_alpha_deg = torch.tensor(0.1, dtype=torch.float64, requires_grad=True)  # degrees
    delta_beta_deg = torch.tensor(0.2, dtype=torch.float64, requires_grad=True)
    delta_gamma_deg = torch.tensor(0.3, dtype=torch.float64, requires_grad=True)

    # Derive U and B
    U_params = derive_orientation_from_quaternion_delta(
        q_delta,
        U_baseline=torch.tensor(U_baseline, dtype=torch.float64)
    )

    B_params = derive_B_from_cell_deltas(
        delta_log_a, delta_log_b, delta_log_c,
        delta_alpha_deg, delta_beta_deg, delta_gamma_deg,
        cell_baseline=cell_baseline,
        dtype=torch.float64
    )

    # Construct A*
    A_star = U_params @ B_params

    # Dummy loss (sum of all elements)
    loss = A_star.sum()

    # Backpropagate
    loss.backward()

    # Validate quaternion gradients
    assert q_delta.grad is not None, (
        "DB-AT-026.4 FAIL: Quaternion q_delta must have gradients"
    )
    assert torch.all(torch.isfinite(q_delta.grad)), (
        f"DB-AT-026.4 FAIL: Quaternion gradients must be finite. "
        f"grad={q_delta.grad}"
    )
    q_grad_norm = q_delta.grad.norm().item()
    assert q_grad_norm > 0, (
        f"DB-AT-026.4 FAIL: Quaternion gradients must be non-zero. "
        f"grad_norm={q_grad_norm}"
    )

    # Validate cell length gradients
    for name, param in [("delta_log_a", delta_log_a), ("delta_log_b", delta_log_b), ("delta_log_c", delta_log_c)]:
        assert param.grad is not None, (
            f"DB-AT-026.4 FAIL: {name} must have gradients"
        )
        assert torch.isfinite(param.grad).all(), (
            f"DB-AT-026.4 FAIL: {name} gradient must be finite. grad={param.grad}"
        )

    # Validate cell angle gradients
    for name, param in [("delta_alpha_deg", delta_alpha_deg), ("delta_beta_deg", delta_beta_deg), ("delta_gamma_deg", delta_gamma_deg)]:
        assert param.grad is not None, (
            f"DB-AT-026.4 FAIL: {name} must have gradients"
        )
        assert torch.isfinite(param.grad).all(), (
            f"DB-AT-026.4 FAIL: {name} gradient must be finite. grad={param.grad}"
        )

    print(f"✓ DB-AT-026.4 PASS: All gradients exist and are finite. "
          f"q_grad_norm={q_grad_norm:.3e}, "
          f"δlog_a.grad={delta_log_a.grad.item():.3e}, "
          f"Δα.grad={delta_alpha_deg.grad.item():.3e}")
