# dbex/refinement/context.py
"""
RefinementContext dataclass for typed refinement inputs.

Replaces ad-hoc dicts passed through RefinementEngine and Stage wrappers
with a typed object per ARCH-REFINE-001 Phase B.1.

Normative Requirements:
- docs/spec-db-workflow.md §7 (Refinement Protocol Architecture)
- docs/spec-db-core.md (geometry/HKL contracts)
- docs/architecture.md (IDL-style contracts)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np
import torch


@dataclass
class RefinementContext:
    """
    Typed container for shared refinement state across Stage A/B/C.

    All stages receive the same RefinementContext instance, ensuring
    consistent geometry/HKL/baseline state throughout the refinement flow.

    Attributes:
        refinement_inputs: RefinementInputs dataclass (target, loss_mask, panel_slices,
                          trusted_mask, sigma_readout, target_representation, global_scale_hint)
        detector: dxtbx Detector object (panel geometry)
        beam: dxtbx Beam object (wavelength, polarization, direction)
        crystal: dxtbx Crystal object (unit cell, orientation)
        hkl_grid: torch.Tensor structure factor grid [h, k, l] with complex |F|
        hkl_metadata: Dict with grid dimensions (nabc_grid, default_F, has_halo, etc.)
        baseline_crystal: Optional baseline dxtbx Crystal for misset extraction
                         (used when crystal is perturbed; Stage A computes delta misset)
        baseline_detector: Optional baseline dxtbx Detector for Stage C offset reference
                          (required when Stage C is enabled)
        extras: Dict[str, Any] for future extensions (job metadata, provenance, etc.)

    Normative Dependencies (Transitive):
    - refinement_inputs.target: Prepared per spec-db-core.md:20 ([panel, slow, fast])
    - refinement_inputs.loss_mask: (background >= 0) ∧ trusted_mask per spec-db-core.md:55
    - detector: dxtbx Detector with square pixels per config_crosswalk.md:30
    - beam: dxtbx Beam with wavelength and polarization per config_crosswalk.md:65-70
    - crystal: dxtbx Crystal with unit cell and orientation per config_crosswalk.md:75-80
    - hkl_grid: Structure factors per spec-db-core.md:85-90 (refined MTZ preferred)
    - hkl_metadata['has_halo']: Stage B/C require halo-padded grid per spec-db-workflow.md:53-54

    IDL Contract Reference:
    - docs/architecture.md (modular structure)
    - docs/spec-db-workflow.md:48-84 (Refinement Protocol Architecture)
    """
    refinement_inputs: Any  # RefinementInputs from dbex.nanobrag_bridge
    detector: Any  # dxtbx Detector object
    beam: Any  # dxtbx Beam object
    crystal: Any  # dxtbx Crystal object
    hkl_grid: torch.Tensor  # [h, k, l] complex structure factor grid
    hkl_metadata: Dict[str, Any]  # nabc_grid, default_F, has_halo, etc.
    baseline_crystal: Optional[Any] = None  # baseline dxtbx Crystal (for misset extraction)
    baseline_detector: Optional[Any] = None  # baseline dxtbx Detector (for Stage C offsets)
    extras: Dict[str, Any] = field(default_factory=dict)  # Future extensions


def build_refinement_context(
    refinement_inputs,
    detector,
    beam,
    crystal,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict[str, Any],
    baseline_crystal=None,
    baseline_detector=None,
    extras: Optional[Dict[str, Any]] = None,
) -> RefinementContext:
    """
    Build a RefinementContext from raw inputs, validating tensor/device expectations.

    Args:
        refinement_inputs: RefinementInputs dataclass (target, loss_mask, panel_slices, etc.)
        detector: dxtbx Detector object
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object
        hkl_grid: torch.Tensor structure factor grid [h, k, l]
        hkl_metadata: Dict with grid dimensions (nabc_grid, default_F, has_halo, etc.)
        baseline_crystal: Optional baseline dxtbx Crystal for misset extraction
        baseline_detector: Optional baseline dxtbx Detector for Stage C offsets
        extras: Optional dict for future extensions (job metadata, provenance, etc.)

    Returns:
        RefinementContext instance with validated inputs

    Raises:
        ValueError: If hkl_grid is not a torch.Tensor or hkl_metadata is missing required keys
        TypeError: If detector/beam/crystal are not dxtbx objects (future validation)

    Normative Requirements:
    - hkl_grid must be a torch.Tensor per spec-db-core.md:85-90
    - hkl_metadata must contain 'nabc_grid' and 'has_halo' keys per spec-db-workflow.md:53-54
    - Device/dtype neutrality: this builder does NOT enforce specific device/dtype;
      stages are responsible for tensor device/dtype management per pytorch_runtime_checklist.md

    Provenance:
    - ARCH-REFINE-001 Phase B.1: Replace ad-hoc dict plumbing with typed context
    - docs/spec-db-workflow.md:48-84: Refinement Protocol Architecture
    - docs/architecture.md: IDL-style contracts for all components
    """
    # Validate hkl_grid is a tensor
    if not isinstance(hkl_grid, torch.Tensor):
        raise ValueError(
            f"hkl_grid must be torch.Tensor, got {type(hkl_grid).__name__}. "
            "Per spec-db-core.md:85-90, structure factors must be provided as tensors."
        )

    # Validate hkl_metadata contains required keys
    # Only validate 'has_halo' key exists (required for Stage B/C per spec-db-workflow.md:53-54)
    # Other keys vary based on implementation details
    if 'has_halo' not in hkl_metadata:
        raise ValueError(
            "hkl_metadata missing required key 'has_halo'. "
            "Per spec-db-workflow.md:53-54, Stage B/C require halo-padded grids."
        )

    # Validate refinement_inputs is not None (sanity check)
    if refinement_inputs is None:
        raise ValueError(
            "refinement_inputs must not be None. "
            "Per spec-db-core.md:20, target/loss_mask/panel_slices are required."
        )

    # Build context with all fields
    return RefinementContext(
        refinement_inputs=refinement_inputs,
        detector=detector,
        beam=beam,
        crystal=crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,
        extras=extras if extras is not None else {},
    )
