"""Visualization helpers aligned with spec-db-vis standards."""

from .triptych import plot_triptych
from .residuals import compute_z_scores, plot_z_scores
from .stage_a import StageAROITriptych, emit_stage_a_roi_triptychs
from .mapping import (
    MappingRefinementConfig,
    MappingRefinementResult,
    MappingStageAContext,
    build_mapping_stage_a_context,
    refine_on_mapping_model,
)


def save_triptych(*args, **kwargs):
    """Compatibility wrapper around :func:`plot_triptych`."""
    return plot_triptych(*args, **kwargs)


__all__ = [
    "plot_triptych",
    "save_triptych",
    "compute_z_scores",
    "plot_z_scores",
    "StageAROITriptych",
    "emit_stage_a_roi_triptychs",
    "MappingStageAContext",
    "MappingRefinementConfig",
    "MappingRefinementResult",
    "build_mapping_stage_a_context",
    "refine_on_mapping_model",
]
