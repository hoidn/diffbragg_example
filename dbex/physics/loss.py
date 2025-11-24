"""
Physics-based loss functions for diffraction refinement.

Leaf-node module: imports FROM external dependencies (torch) but NOT from
dbex.nanobrag_* to avoid circular imports.

Functions in this module implement:
- Variance-weighted chi-squared loss per spec-db-core.md
- Masked MSE computations
- Pixel-wise error statistics

All functions preserve autograd graphs and are device-agnostic.
"""

from __future__ import annotations
from typing import Tuple
import torch


def _compute_variance_weighted_loss(
    bragg_tensor: torch.Tensor,
    target_tensor: torch.Tensor,
    loss_mask: torch.Tensor,
    sigma_tensor: torch.Tensor,
    sigma_floor_sq_tensor: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor, int, int]:
    """
    Sum variance-weighted chi-squared + masked-MSE per spec-db-core.md:57-80.

    Returns:
        chi-squared sum, masked-MSE value, masked pixel count, clamp pixel count.
    """
    variance_raw = bragg_tensor.detach() + sigma_tensor ** 2
    variance = torch.maximum(variance_raw, sigma_floor_sq_tensor)

    mask_bool = loss_mask
    masked_pixels = int(mask_bool.sum().item())
    clamped_pixels = int(((variance_raw < sigma_floor_sq_tensor) & mask_bool).sum().item())

    diff = bragg_tensor - target_tensor
    squared_error = diff ** 2
    masked_squared_error = torch.where(mask_bool, squared_error, torch.zeros_like(squared_error))

    weighted_error = squared_error / variance
    masked_weighted_error = torch.where(mask_bool, weighted_error, torch.zeros_like(weighted_error))
    chi_squared_sum = masked_weighted_error.sum()

    if masked_pixels > 0:
        masked_mse_value = masked_squared_error.sum() / masked_pixels
    else:
        masked_mse_value = masked_squared_error.sum()

    return chi_squared_sum, masked_mse_value, masked_pixels, clamped_pixels
