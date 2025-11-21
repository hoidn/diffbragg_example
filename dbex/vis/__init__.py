"""Visualization helpers aligned with spec-db-vis standards."""

from .triptych import plot_triptych
from .residuals import compute_z_scores, plot_z_scores
from .stage_a import StageAROITriptych, emit_stage_a_roi_triptychs


def save_triptych(*args, **kwargs):
    """Compatibility wrapper around :func:`plot_triptych`.

    Existing tooling and plans may refer to ``save_triptych``; keep it as
    a thin alias so callers can depend on a stable name while the underlying
    implementation evolves.
    """
    return plot_triptych(*args, **kwargs)


__all__ = [
    "plot_triptych",
    "save_triptych",
    "compute_z_scores",
    "plot_z_scores",
    "StageAROITriptych",
    "emit_stage_a_roi_triptychs",
]
