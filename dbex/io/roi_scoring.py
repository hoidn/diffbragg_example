"""ROI scoring helper using Nelder-Mead optimization.

This module decouples ROI analysis (Nelder-Mead + roiCheck scoring) from HDF5
serialization per ARCH-BRIDGE-RESP-001 Phase B. The writer (dbex.io.writer) will
consume the typed payloads produced here instead of running optimization inline.

Spec Compliance:
    - docs/spec-db-core.md §§86-90: Variance model V = max(I_model + sigma_readout^2,
      sigma_floor^2) with provenance for sigma inputs.
    - docs/spec-db-interfaces.md: ROI scoring telemetry (roi_scoring_method, roi_checker).

Design Intent:
    - Keep imports local (no torch at module import time) to satisfy Environment Freeze.
    - Reuse build_roi_payloads_from_arrays to slice ROIs, then run scipy.optimize.minimize
      with roiCheck objective per legacy DiffBragg parity (dbex/io/writer.py:106-110).
    - Populate ROIAnalysisPayload with score, optimal_scale, model, and variance arrays.
    - Optionally accept injected roi_checker and log_fn for testability.

History:
    - 2025-12-02 (ARCH-BRIDGE-RESP-001 Phase B.1): Initial implementation of score_roi_payloads.

See Also:
    - dbex/io/roi_analysis.py: ROITriptych/ROIAnalysisPayload dataclasses.
    - dbex/io/writer.py:106-158: Reference implementation (inline scoring to be replaced).
    - docs/architecture/dbex/io/writer.idl.md: Writer API contract and ROI helper interface.
"""

from typing import Callable, List, Optional, Tuple

import numpy as np

from .roi_analysis import ROIAnalysisPayload, build_roi_payloads_from_arrays

__all__ = ["score_roi_payloads"]


def score_roi_payloads(
    target: np.ndarray,
    background: np.ndarray,
    bragg: np.ndarray,
    pids: List[int],
    bbox: List[Tuple[int, int, int, int]],
    sigma_readout: float,
    sigma_floor: float,
    roi_checker=None,
    log_fn: Optional[Callable[[int, float], None]] = None,
) -> List[ROIAnalysisPayload]:
    """Score ROIs using Nelder-Mead optimization and populate variance arrays.

    Runs scipy.optimize.minimize with roiCheck objective to find optimal Bragg scale
    per ROI, then computes model (background + optimal_scale * bragg) and variance
    per docs/spec-db-core.md §§86-90. Returns typed ROIAnalysisPayload instances
    suitable for direct consumption by dbex.io.writer.write_torch_outputs.

    Args:
        target: Full-detector target intensities (n_panels, slow, fast) in ADU or photons.
        background: Full-detector background image (n_panels, slow, fast) matching target units.
        bragg: Full-detector simulated Bragg intensities (n_panels, slow, fast) matching target units.
        pids: Panel IDs per ROI (length n_rois).
        bbox: Bounding boxes per ROI (length n_rois), each (x0, x1, y0, y1) with x1/y1 exclusive.
        sigma_readout: Readout noise sigma in target units (ADU or photons). Must be >= 0.
        sigma_floor: Variance floor in target units (ADU or photons). Must be > 0.
        roi_checker: Optional roiCheck instance for scoring. If None, imports score_trainer.roi_check.roiCheck
                     and constructs default instance. Injection enables testing without SciPy.
        log_fn: Optional callable(roi_index: int, score_pct: float) for per-ROI logging.
                If None, prints "roi=%d : score= %.1f" per legacy parity.

    Returns:
        List of ROIAnalysisPayload instances (length n_rois), one per ROI. Each payload contains:
            - triptych: ROITriptych with cropped data/background/bragg arrays
            - score: float in [0, 1] from CHECKER.score(data, model), higher=better
            - optimal_scale: float >= 0 from Nelder-Mead (squared x[0] from minimizer)
            - model: np.ndarray = background + optimal_scale * bragg (same shape as triptych arrays)
            - variance: np.ndarray = max(model + sigma_readout^2, sigma_floor^2) per spec-db-core.md §86-90

    Raises:
        AssertionError: If array shapes are inconsistent, sigma_readout < 0, sigma_floor <= 0,
                        or background contains NaN (enforced by build_roi_payloads_from_arrays).
        ImportError: If score_trainer.roi_check is unavailable and roi_checker=None.

    Notes:
        - Optimization: Minimizes `1 - CHECKER.score(data, bragg_scale**2 * bragg + background)`
          via scipy.optimize.minimize(method="Nelder-Mead", x0=[1]). If minimizer fails,
          falls back to optimal_scale=1.0 per legacy behavior (dbex/io/writer.py:131).
        - Score coercion: Always coerces score to float (TORCH-CLI-004) to guard against
          mocked/non-scalar returns from CHECKER.score().
        - Variance: Computed element-wise per spec-db-core.md §§86-90; enforces sigma_floor
          lower bound to avoid zero/negative variance on dark pixels.
        - Import hygiene: score_trainer import happens inside function (not module-level) to
          satisfy Environment Freeze constraint (no external package imports at import time).

    Example (with real scoring):
        >>> target = np.random.rand(2, 100, 100) * 1000
        >>> background = np.ones((2, 100, 100)) * 50
        >>> bragg = np.random.rand(2, 100, 100) * 200
        >>> pids = [0, 1]
        >>> bbox = [(10, 30, 20, 40), (50, 70, 60, 80)]
        >>> payloads = score_roi_payloads(target, background, bragg, pids, bbox,
        ...                                sigma_readout=3.0, sigma_floor=1.0)
        >>> assert len(payloads) == 2
        >>> assert 0 <= payloads[0].score <= 1
        >>> assert payloads[0].optimal_scale > 0
        >>> assert payloads[0].model.shape == (20, 20)
        >>> assert payloads[0].variance.shape == (20, 20)
        >>> assert np.all(payloads[0].variance > 0)  # Strictly positive per spec

    Example (with injected checker for testing):
        >>> class FakeChecker:
        ...     def score(self, data, model):
        ...         return 0.85  # Deterministic score
        >>> payloads = score_roi_payloads(target, background, bragg, pids, bbox,
        ...                                sigma_readout=3.0, sigma_floor=1.0,
        ...                                roi_checker=FakeChecker())
        >>> assert payloads[0].score == 0.85
    """
    # Validate sigma parameters
    assert sigma_readout >= 0, f"sigma_readout must be >= 0, got {sigma_readout}"
    assert sigma_floor > 0, f"sigma_floor must be > 0, got {sigma_floor}"

    # Import scoring dependencies locally (Environment Freeze: no module-level torch/scipy imports)
    from scipy.optimize import minimize

    # Initialize checker (inject for testing or import default)
    if roi_checker is None:
        from score_trainer import roi_check
        CHECKER = roi_check.roiCheck()
    else:
        CHECKER = roi_checker

    # Build baseline payloads with triptych data (no scoring/variance yet)
    payloads = build_roi_payloads_from_arrays(
        target=target,
        background=background,
        bragg=bragg,
        pids=pids,
        bbox=bbox,
        scores=None,  # Will populate after optimization
        scales=None,  # Will populate after optimization
    )

    # Define Nelder-Mead objective (matches dbex/io/writer.py:106-110)
    def func(x, CHECKER, bragg_im, bg_im, dat_im):
        """Minimize 1 - score(data, bragg_scale^2 * bragg + background)."""
        bragg_scale = x[0]
        score = CHECKER.score(dat_im, bragg_scale**2 * bragg_im + bg_im)
        resid = 1 - score
        return resid

    # Score each ROI and populate payload fields
    for i, payload in enumerate(payloads):
        triptych = payload.triptych
        dat_im = triptych.data
        bg_im = triptych.background
        bragg_im = triptych.bragg

        # Run Nelder-Mead optimization
        min_out = minimize(
            func,
            x0=[1],
            args=(CHECKER, bragg_im, bg_im, dat_im),
            method="Nelder-Mead"
        )

        # Extract optimal scale (fallback to 1.0 on failure per legacy parity)
        if min_out.success:
            optimal_scale = min_out['x'][0]**2
        else:
            optimal_scale = 1.0

        # Compute model and final score
        model = bg_im + optimal_scale * bragg_im
        score = CHECKER.score(dat_im, model)
        # TORCH-CLI-004: Coerce score to float to guard against mocks/non-scalars
        score_float = float(score)

        # Compute variance per spec-db-core.md §§86-90: V = max(I_model + sigma_readout^2, sigma_floor^2)
        variance = model + sigma_readout**2
        variance = np.maximum(variance, sigma_floor**2)

        # Log per-ROI score (legacy format or custom log_fn)
        if log_fn is not None:
            log_fn(i, score_float * 100)
        else:
            print("roi=%d : score= %.1f" % (i, score_float * 100))

        # Update payload with scoring/variance results
        payload.score = score_float
        payload.optimal_scale = optimal_scale
        payload.model = model
        payload.variance = variance

    return payloads
