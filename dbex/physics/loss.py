"""
Physics-based loss functions for diffraction refinement.

Leaf-node module: imports FROM external dependencies (torch) but NOT from
dbex.nanobrag_* to avoid circular imports.

Functions in this module implement:
- Variance-weighted chi-squared loss per spec-db-core.md/spec-db-workflow.md
  (see also docs/config_crosswalk.md “Arrays and loss” mapping).
- Masked MSE computations
- Pixel-wise error statistics

All functions preserve autograd graphs and are device-agnostic.
"""

from __future__ import annotations
from typing import Optional, Tuple
import torch


def _compute_variance_weighted_loss(
    bragg_tensor: torch.Tensor,
    target_tensor: torch.Tensor,
    loss_mask: torch.Tensor,
    sigma_tensor: torch.Tensor,
    sigma_floor_sq_tensor: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, int, int]:
    """
    Sum variance-weighted chi-squared + masked-MSE per spec-db-core.md:57-80
    and the Loss section in docs/spec-db-workflow.md.

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


def compute_masked_mse_loss(
    prediction: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    sigma_readout: Optional[torch.Tensor] = None
) -> torch.Tensor:
    """
    Compute variance-weighted chi-squared loss for gradient-based optimization.

    Implements spec-db-core.md:57-68 variance model when sigma_readout is provided:
    - Variance: V = I_model.detach() + sigma_readout^2 (Poisson + readout noise)
    - Loss: Sum((I_model - I_obs)^2 / V) over masked pixels
    - Detached denominator implements IRLS (prevents "attraction to zero")

    When sigma_readout is None, falls back to masked MSE (legacy behavior).

    Args:
        prediction: Predicted Bragg intensities [panel, slow, fast], torch.Tensor
        target: Target intensities [panel, slow, fast], torch.Tensor
        mask: Loss mask [panel, slow, fast], torch.Tensor with dtype bool or numeric
        sigma_readout: Optional readout noise [panel, slow, fast], torch.Tensor in target units.
                      When provided, computes variance-weighted chi-squared loss per spec-db-core.md.
                      When None, falls back to masked MSE (legacy).

    Returns:
        loss: Scalar tensor with variance-weighted chi-squared (or MSE if sigma_readout=None)

    Raises:
        ValueError: If shapes don't match or mask has no valid pixels

    Notes:
        - Preserves gradient graph (no .detach() or numpy conversions except variance term)
        - Respects SCALE-002: target/prediction must have same post-simulation scaling
        - Returns scalar tensor suitable for torch.autograd.gradcheck
        - Mask expected to be boolean or numeric (0/1); numeric values treated as weights
        - PHYSICS-LOSS-001: Variance-weighted loss is the normative path per spec-db-core.md:57
        - Reuses shared validation/clamp logic from _compute_variance_weighted_loss
        - TEST-ONLY: Do not call from production LBFGS closures (DB-AT-010 gradcheck only)

    References:
        - docs/spec-db-core.md §§57-68 (variance model)
        - docs/spec-db-workflow.md §§30-45 (forward helper + telemetry expectations)
        - PHYSICS-LOSS-001 (shared variance-weighted loss)
    """
    # Validate shapes
    if prediction.shape != target.shape:
        raise ValueError(
            f"Shape mismatch: prediction {prediction.shape} vs target {target.shape}"
        )
    if mask.shape != prediction.shape:
        raise ValueError(
            f"Mask shape {mask.shape} doesn't match prediction shape {prediction.shape}"
        )
    if sigma_readout is not None and sigma_readout.shape != prediction.shape:
        raise ValueError(
            f"sigma_readout shape {sigma_readout.shape} doesn't match prediction shape {prediction.shape}"
        )

    # Ensure mask is boolean
    if mask.dtype != torch.bool:
        mask = mask.bool()

    # Check for valid mask pixels
    n_valid = mask.sum()
    if n_valid == 0:
        raise ValueError("Loss mask contains no valid pixels")

    # Compute squared error numerator
    squared_error = (prediction - target) ** 2

    if sigma_readout is not None:
        # Variance-weighted chi-squared loss (spec-db-core.md:57-68)
        # Variance = I_model.detach() + sigma_readout^2 (Poisson + readout noise in quadrature)
        # Detach denominator to prevent "attraction to zero" (IRLS approach)
        variance = torch.clamp(prediction.detach() + sigma_readout**2, min=1e-12)

        # Chi-squared: Sum((I_model - I_obs)^2 / V) over masked pixels
        weighted_squared_error = squared_error / variance
        masked_weighted_error = torch.where(mask, weighted_squared_error, torch.zeros_like(weighted_squared_error))

        # Sum over valid pixels (chi-squared is a sum, not a mean)
        loss = masked_weighted_error.sum()
    else:
        # Legacy MSE fallback (when sigma_readout not provided)
        masked_squared_error = torch.where(mask, squared_error, torch.zeros_like(squared_error))

        # Mean over valid pixels
        loss = masked_squared_error.sum() / n_valid.to(prediction.dtype)

    return loss
