"""
Gradcheck tests for U-matrix quaternion parameterization (TORCH-GEOMETRY-PARITY-002 Phase B).

Tests quaternion roundtrip conversion and U-matrix closure gradients to validate
the direct U-matrix parameterization implementation for Stage A refinement.

References:
    - plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md:147-153 (Phase B2, B7)
    - input.md:47-51, 112-121 (roundtrip test spec, gradcheck spec)
"""

import numpy as np
import pytest
import torch


def test_quaternion_roundtrip():
    """
    Test quaternion ↔ matrix roundtrip conversion (Phase B2).

    Validates that matrix_to_quaternion and quaternion_to_matrix are inverse
    operations within numerical precision (<1e-6).

    Per input.md:47-51:
    - Generate random rotation matrix U_0 using scipy
    - Convert U_0 → q → U_1
    - Assert torch.allclose(U_1, U_0, atol=1e-6)

    References:
        - input.md:47-51 (roundtrip validation spec)
        - plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md:148 (Phase B2)
    """
    from scipy.spatial.transform import Rotation
    from dbex.nanobrag_bridge import matrix_to_quaternion, quaternion_to_matrix

    # Generate random rotation matrix using scipy
    R = Rotation.random(random_state=42)
    U_0 = R.as_matrix()

    # Convert U_0 → q → U_1
    q = matrix_to_quaternion(U_0)
    U_1 = quaternion_to_matrix(q)

    # Validate roundtrip
    U_0_torch = torch.tensor(U_0, dtype=torch.float64)
    assert torch.allclose(U_1, U_0_torch, atol=1e-6), (
        f"Quaternion roundtrip failed: max error = {torch.max(torch.abs(U_1 - U_0_torch)).item()}"
    )

    # Validate quaternion is unit norm
    q_norm = torch.norm(q)
    assert torch.allclose(q_norm, torch.tensor(1.0, dtype=torch.float64), atol=1e-8), (
        f"Quaternion not unit norm: ||q|| = {q_norm.item()}"
    )


@pytest.mark.skip(reason="Phase B7 implementation pending - requires minimal synthetic crystal config")
def test_u_matrix_closure_gradcheck():
    """
    Test gradients through U-matrix closure (Phase B7).

    Validates that gradients flow correctly through the quaternion → U → A* path
    using torch.autograd.gradcheck on a minimal synthetic test case.

    Per input.md:112-121:
    - Initialize quaternion q (random or from identity)
    - Compute A* = quaternion_to_matrix(q / ||q||) @ B_ideal_reciprocal
    - Run tiny forward pass (single pixel, single HKL, synthetic target)
    - Compute variance-weighted loss
    - Use torch.autograd.gradcheck to verify gradients w.r.t. q

    Environment:
        Must run with NANOBRAGG_DISABLE_COMPILE=1 per RUNTIME-001.

    References:
        - input.md:112-121 (gradcheck spec)
        - plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md:153 (Phase B7)
    """
    # Placeholder for Phase B7 implementation
    # Will require minimal synthetic crystal config + forward pass setup
    pass
