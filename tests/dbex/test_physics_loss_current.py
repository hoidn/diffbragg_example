"""
Unit tests for physics loss functions in CURRENT location (dbex/nanobrag_refinement.py).

Phase 0 test discipline baseline per ARCH-REFACTOR-001:80-89.
Tests written against CURRENT code before Phase A refactoring to provide safety net.
"""
import numpy as np
import torch
import pytest


@pytest.fixture
def synthetic_loss_tensors():
    """
    Create synthetic target/model/mask tensors for loss function testing.

    Returns tuple of (target, model, mask) as torch.Tensor (5x5 small arrays).
    """
    device = torch.device("cpu")
    dtype = torch.float64

    # 5x5 synthetic data (small for fast testing)
    target = torch.tensor([
        [5.0, 10.0, 3.0, 7.0, 12.0],
        [7.0, 12.0, 8.0, 4.0, 6.0],
        [4.0, 6.0, 9.0, 11.0, 5.0],
        [8.0, 3.0, 10.0, 6.0, 9.0],
        [2.0, 7.0, 5.0, 8.0, 4.0],
    ], device=device, dtype=dtype)

    model = torch.tensor([
        [4.5, 9.5, 3.2, 6.8, 11.8],
        [6.8, 11.8, 7.9, 4.1, 6.1],
        [4.1, 6.1, 8.9, 10.9, 4.9],
        [7.9, 3.1, 9.8, 5.9, 8.8],
        [2.1, 7.2, 5.1, 8.1, 4.2],
    ], device=device, dtype=dtype)

    mask = torch.tensor([
        [1.0, 1.0, 0.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 0.0, 1.0],
        [0.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 0.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 0.0],
    ], device=device, dtype=dtype)

    return target, model, mask


def test_variance_weighted_loss_basic_clamping(synthetic_loss_tensors):
    """
    Test variance clamping: V = max(I_model + sigma², variance_floor).

    Acceptance criteria per ARCH-REFACTOR-001:0.2 and PHYSICS-LOSS-001:
    1. Variance V = max(model + sigma²_readout, sigma²_floor) per pixel
    2. Loss = sum((target - model)² / V * mask) / sum(mask)
    3. Verify chi-squared sum and masked-MSE computation

    References:
    - docs/spec-db-core.md:57-80 (variance definition, sigma_floor clamping)
    - docs/findings.md PHYSICS-LOSS-001 (variance metadata)
    """
    from dbex.nanobrag_refinement import _compute_variance_weighted_loss

    target, model, mask = synthetic_loss_tensors

    # Test parameters
    sigma_readout = 1.0
    variance_floor_value = 2.0

    # Create sigma tensor (constant sigma_readout per pixel)
    sigma_tensor = torch.full_like(target, sigma_readout)
    sigma_floor_sq_tensor = torch.tensor(variance_floor_value ** 2, device=target.device, dtype=target.dtype)

    # Call function under test
    chi_squared_sum, masked_mse, masked_pixels, clamped_pixels = _compute_variance_weighted_loss(
        bragg_tensor=model,
        target_tensor=target,
        loss_mask=mask.bool(),
        sigma_tensor=sigma_tensor,
        sigma_floor_sq_tensor=sigma_floor_sq_tensor,
    )

    # Manual computation for verification
    variance_raw = model.detach() + sigma_readout ** 2  # I_model + sigma²
    variance = torch.maximum(variance_raw, sigma_floor_sq_tensor)  # max(variance_raw, floor²)

    diff = model - target
    squared_error = diff ** 2
    weighted_error = squared_error / variance
    mask_bool = mask.bool()

    # Expected chi-squared sum (masked weighted error)
    expected_chi_sq = torch.where(mask_bool, weighted_error, torch.zeros_like(weighted_error)).sum()

    # Expected masked MSE
    expected_masked_sq_error = torch.where(mask_bool, squared_error, torch.zeros_like(squared_error)).sum()
    expected_masked_pixels = int(mask_bool.sum().item())
    expected_masked_mse = expected_masked_sq_error / expected_masked_pixels if expected_masked_pixels > 0 else expected_masked_sq_error

    # Expected clamped pixels (where variance_raw < variance_floor²)
    expected_clamped_pixels = int(((variance_raw < sigma_floor_sq_tensor) & mask_bool).sum().item())

    # Assertions
    assert masked_pixels == expected_masked_pixels, f"Masked pixel count mismatch: {masked_pixels} != {expected_masked_pixels}"
    assert clamped_pixels == expected_clamped_pixels, f"Clamped pixel count mismatch: {clamped_pixels} != {expected_clamped_pixels}"

    torch.testing.assert_close(
        chi_squared_sum, expected_chi_sq, atol=1e-6, rtol=1e-6,
        msg="Chi-squared sum mismatch"
    )

    torch.testing.assert_close(
        masked_mse, expected_masked_mse, atol=1e-6, rtol=1e-6,
        msg="Masked MSE mismatch"
    )


def test_variance_weighted_loss_zero_mask():
    """
    Test safe handling of zero mask (all pixels masked out).

    Edge case: mask=0 everywhere should return 0.0 for chi-squared (or handle safely).
    """
    from dbex.nanobrag_refinement import _compute_variance_weighted_loss

    device = torch.device("cpu")
    dtype = torch.float64

    # 3x3 tensors with zero mask
    target = torch.ones((3, 3), device=device, dtype=dtype) * 10.0
    model = torch.ones((3, 3), device=device, dtype=dtype) * 5.0
    mask = torch.zeros((3, 3), device=device, dtype=dtype)  # All masked out

    sigma_tensor = torch.full_like(target, 1.0)
    sigma_floor_sq_tensor = torch.tensor(4.0, device=device, dtype=dtype)

    chi_squared_sum, masked_mse, masked_pixels, clamped_pixels = _compute_variance_weighted_loss(
        bragg_tensor=model,
        target_tensor=target,
        loss_mask=mask.bool(),
        sigma_tensor=sigma_tensor,
        sigma_floor_sq_tensor=sigma_floor_sq_tensor,
    )

    # Expected: all counts zero, chi-squared sum zero, masked_mse = sum(0) / 0 = 0 (per function logic)
    assert masked_pixels == 0, "Masked pixels should be 0 when mask is all zeros"
    assert clamped_pixels == 0, "Clamped pixels should be 0 when mask is all zeros"
    torch.testing.assert_close(chi_squared_sum, torch.tensor(0.0, device=device, dtype=dtype), msg="Chi-squared should be 0 with zero mask")
    # masked_mse behavior: function returns sum(0) when masked_pixels=0
    torch.testing.assert_close(masked_mse, torch.tensor(0.0, device=device, dtype=dtype), msg="Masked MSE should be 0 with zero mask")


def test_variance_weighted_loss_zero_variance_floor():
    """
    Test with zero variance_floor (no clamping).

    When variance_floor=0, V = model + sigma² (no clamping applied).
    """
    from dbex.nanobrag_refinement import _compute_variance_weighted_loss

    device = torch.device("cpu")
    dtype = torch.float64

    # 3x3 tensors
    target = torch.tensor([[5.0, 10.0, 3.0], [7.0, 12.0, 8.0], [4.0, 6.0, 9.0]], device=device, dtype=dtype)
    model = torch.tensor([[4.5, 9.5, 3.2], [6.8, 11.8, 7.9], [4.1, 6.1, 8.9]], device=device, dtype=dtype)
    mask = torch.tensor([[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]], device=device, dtype=dtype)

    sigma_tensor = torch.full_like(target, 1.0)
    sigma_floor_sq_tensor = torch.tensor(0.0, device=device, dtype=dtype)  # No clamping

    chi_squared_sum, masked_mse, masked_pixels, clamped_pixels = _compute_variance_weighted_loss(
        bragg_tensor=model,
        target_tensor=target,
        loss_mask=mask.bool(),
        sigma_tensor=sigma_tensor,
        sigma_floor_sq_tensor=sigma_floor_sq_tensor,
    )

    # Manual computation (no clamping)
    variance = model.detach() + sigma_tensor ** 2  # No max() since floor=0
    diff = model - target
    squared_error = diff ** 2
    weighted_error = squared_error / variance

    expected_chi_sq = weighted_error.sum()
    expected_masked_mse = squared_error.sum() / 9  # All 9 pixels masked

    # All pixels should be unclamped (variance_raw >= 0.0 always)
    expected_clamped_pixels = 0

    assert masked_pixels == 9, "All pixels should be masked"
    assert clamped_pixels == expected_clamped_pixels, f"No pixels should be clamped with variance_floor=0"

    torch.testing.assert_close(chi_squared_sum, expected_chi_sq, atol=1e-6, rtol=1e-6, msg="Chi-squared mismatch with zero variance_floor")
    torch.testing.assert_close(masked_mse, expected_masked_mse, atol=1e-6, rtol=1e-6, msg="Masked MSE mismatch with zero variance_floor")


def test_variance_weighted_loss_negative_model():
    """
    Test with negative model values (variance clamping should still apply).

    Edge case: model can be negative (unphysical but should not break variance computation).
    Variance V = max(model + sigma², variance_floor) should still clamp correctly.
    """
    from dbex.nanobrag_refinement import _compute_variance_weighted_loss

    device = torch.device("cpu")
    dtype = torch.float64

    # 3x3 tensors with negative model values
    target = torch.tensor([[5.0, 10.0, 3.0], [7.0, 12.0, 8.0], [4.0, 6.0, 9.0]], device=device, dtype=dtype)
    model = torch.tensor([[-1.0, 0.5, -0.5], [1.0, 2.0, 1.5], [0.8, 1.2, 1.8]], device=device, dtype=dtype)  # Some negative
    mask = torch.tensor([[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]], device=device, dtype=dtype)

    sigma_tensor = torch.full_like(target, 1.0)
    variance_floor_value = 2.0
    sigma_floor_sq_tensor = torch.tensor(variance_floor_value ** 2, device=device, dtype=dtype)

    chi_squared_sum, masked_mse, masked_pixels, clamped_pixels = _compute_variance_weighted_loss(
        bragg_tensor=model,
        target_tensor=target,
        loss_mask=mask.bool(),
        sigma_tensor=sigma_tensor,
        sigma_floor_sq_tensor=sigma_floor_sq_tensor,
    )

    # Manual computation
    variance_raw = model.detach() + sigma_tensor ** 2  # Can be negative + 1 = still small or negative
    variance = torch.maximum(variance_raw, sigma_floor_sq_tensor)  # Clamping should dominate

    # Count clamped pixels (where variance_raw < variance_floor²)
    expected_clamped_pixels = int((variance_raw < sigma_floor_sq_tensor).sum().item())

    diff = model - target
    squared_error = diff ** 2
    weighted_error = squared_error / variance
    expected_chi_sq = weighted_error.sum()
    expected_masked_mse = squared_error.sum() / 9

    assert masked_pixels == 9, "All pixels should be masked"
    # With model in [-1, 2], model + 1 in [0, 3], floor²=4, expect most pixels clamped
    assert clamped_pixels >= 6, f"Most pixels should be clamped with small model values and variance_floor=2"

    torch.testing.assert_close(chi_squared_sum, expected_chi_sq, atol=1e-6, rtol=1e-6, msg="Chi-squared mismatch with negative model")
    torch.testing.assert_close(masked_mse, expected_masked_mse, atol=1e-6, rtol=1e-6, msg="Masked MSE mismatch with negative model")
