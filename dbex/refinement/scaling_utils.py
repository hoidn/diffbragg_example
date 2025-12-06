"""
Canonical scaling utilities for post-simulation Bragg intensities.

This module provides the single source of truth for applying spot_scale_override
to simulator outputs, implementing ARCH-CONTRACT-002.

Architecture Contracts:
- ARCH-CONTRACT-002: Post-Run Scaling Pattern
  Owner API: apply_sqrt_spot_scale(bragg, calibration_metadata)
  Responsibility: Apply sqrt(spot_scale_override) to raw simulator outputs
  Consumers:
    - dbex/refinement/stage_a.py:442-443 (Phase B.3 will refactor)
    - dbex/refinement/reconstruction.py:203-208 (Phase B.4 will refactor)
    - dbex/vis/mapping.py (simulate_forward_once path)

Findings Applied:
- SCALE-002 (docs/findings.md:39): DiffBragg spot_scale_override re-applied as sqrt factor
- SCALE-008 (docs/findings.md:42): Stage A warm-cache baseline authority
- SCALE-009 (docs/findings.md:43): Reconstruction scaling provenance

Design Constraints:
- numpy-only (no torch imports) to avoid circular dependencies
- Handles None calibration_metadata gracefully (scale = 1.0)
- Preserves input shape (panel mode vs single-panel)
- Fails fast on invalid spot_scale_override values (negative/NaN/Inf)

Phase: B.1 (Canonical API Authoring)
Initiative: ARCH-IMPL-CONFORMANCE-001
"""

import numpy as np
from typing import Optional


def apply_sqrt_spot_scale(
    bragg: np.ndarray,
    calibration_metadata: Optional[dict],
) -> np.ndarray:
    """
    Apply sqrt(spot_scale_override) to raw Bragg simulator outputs.

    This is the canonical owner API for ARCH-CONTRACT-002, implementing the
    post-simulation scaling pattern required for DiffBragg compatibility.

    The spot_scale_override parameter from DiffBragg represents the square of
    the intensity scaling factor. To correctly scale simulated Bragg intensities,
    we apply the square root of this value.

    Args:
        bragg: Raw Bragg intensities from simulator, shape [n_panels, slow, fast]
               or [slow, fast]. Units: ADU (arbitrary detector units).
        calibration_metadata: Optional dict containing 'spot_scale_override' key.
                             If None or key missing, scale = 1.0 (no-op).

    Returns:
        Scaled Bragg intensities with same shape as input. If spot_scale_override
        is present and > 0, returns bragg * sqrt(spot_scale_override), otherwise
        returns bragg unchanged.

    Raises:
        ValueError: If spot_scale_override is present but negative, NaN, or Inf.

    Examples:
        >>> bragg = np.array([[100.0, 200.0], [300.0, 400.0]])
        >>>
        >>> # No metadata -> no scaling
        >>> result = apply_sqrt_spot_scale(bragg, None)
        >>> np.allclose(result, bragg)
        True
        >>>
        >>> # With spot_scale_override
        >>> metadata = {'spot_scale_override': 3.2e17}
        >>> result = apply_sqrt_spot_scale(bragg, metadata)
        >>> expected_scale = np.sqrt(3.2e17)  # ~5.66e8
        >>> np.allclose(result, bragg * expected_scale)
        True

    References:
        - docs/findings.md:39 (SCALE-002)
        - docs/findings.md:43 (SCALE-009)
        - docs/architecture/calibration_scaling.md:14
    """
    # Extract spot_scale_override, defaulting to None
    spot_scale_override = None
    if calibration_metadata is not None:
        spot_scale_override = calibration_metadata.get('spot_scale_override')

    # Validate and compute sqrt scaling factor
    if spot_scale_override is not None:
        # Validate: no NaN/Inf allowed
        if not np.isfinite(spot_scale_override):
            raise ValueError(
                f"spot_scale_override must be finite, got {spot_scale_override}"
            )
        if spot_scale_override < 0:
            raise ValueError(
                f"spot_scale_override must be non-negative, got {spot_scale_override}"
            )

        # Apply scaling if override > 0, else identity
        if spot_scale_override > 0:
            sqrt_spot_scale = float(np.sqrt(spot_scale_override))
        else:
            # Override is exactly zero -> identity scaling
            sqrt_spot_scale = 1.0
    else:
        # No override provided -> identity scaling
        sqrt_spot_scale = 1.0

    # Apply scaling (shape-preserving)
    return bragg * sqrt_spot_scale
