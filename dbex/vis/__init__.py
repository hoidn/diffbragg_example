"""Visual diagnostics library implementing spec-db-vis.md standards.

This module provides standardized visualization primitives for ROI triptychs
and residual analysis, aligned with the normative requirements in
``docs/spec-db-vis.md``.

Public API:
    - plot_triptych: Standard 3-panel layout [Data | Model | Residual Z-Score]
    - compute_z_scores: Z-score calculation per spec formula (Data-Model)/sqrt(Variance)
"""

from .residuals import compute_z_scores
from .triptych import plot_triptych

__all__ = [
    "plot_triptych",
    "compute_z_scores",
]
