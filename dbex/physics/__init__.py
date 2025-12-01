"""
Physics-based utilities for diffraction simulation and loss computation.

This package provides gradient-preserving forward simulation and variance-weighted
loss functions for DB-AT-010 gradcheck acceptance testing and production refinement.

Exports:
    - simulate_forward_torch: Forward simulation with gradient preservation (DB-AT-010)
    - compute_masked_mse_loss: Variance-weighted chi-squared loss for gradcheck

References:
    - docs/spec-db-core.md sections 57-68 (variance model)
    - docs/spec-db-workflow.md sections 30-45 (forward helper expectations)
    - PHYSICS-LOSS-001 (shared variance-weighted loss)
"""

from dbex.physics.forward import simulate_forward_torch
from dbex.physics.loss import compute_masked_mse_loss

__all__ = [
    'simulate_forward_torch',
    'compute_masked_mse_loss',
]
