"""
Shared helpers for RefinementStage implementations (ARCH-REFINE-FLOW-001 Phase A).

Centralizes simulator instantiation and Bragg generation logic to avoid duplication
across Stage A/B/C implementations.

Functions:
- create_panel_simulator(...): Instantiate nanobrag_torch.Simulator for a panel
- emit_bragg_frame(...): Generate full-frame Bragg tensor from stage parameters

Normative Requirements:
- Helpers MUST respect device/dtype neutrality (no hardcoded .cuda() or float32)
- Helpers MUST use lazy imports to avoid circular import issues
- Helpers are PLAN-LOCAL for Phase A (not used by existing Stage A/B/C until Phase B-D)

Environment Freeze (POLICY-001):
- Reuse existing tensor factories from dbex.nanobrag_bridge
- No new dependencies imported
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

import torch

if TYPE_CHECKING:
    # Lazy imports to avoid circular dependencies
    # These types are only needed for type hints, not runtime
    from dbex.nanobrag_bridge import DetectorConfig, CrystalConfig


def create_panel_simulator(
    detector_config: "DetectorConfig",
    crystal_config: "CrystalConfig",
    hkl_grid: Any,
    config: Any,
    device: torch.device,
    dtype: torch.dtype
) -> Any:
    """
    Centralize simulator instantiation logic for a single panel.

    Extracted from dbex/nanobrag_refinement.py Stage A panel loop (~800-900)
    to avoid duplication across Stage implementations.

    Args:
        detector_config: DetectorConfig instance for this panel
        crystal_config: CrystalConfig instance with current crystal state
        hkl_grid: HKL grid tensor (from nanobrag_bridge)
        config: RefinementConfig instance
        device: torch.device for tensors
        dtype: torch.dtype for tensors

    Returns:
        nanobrag_torch.Simulator instance configured for this panel

    Normative Requirements:
    - MUST respect device/dtype parameters (no hardcoded .cuda() or float32)
    - MUST use existing tensor factories from dbex.nanobrag_bridge
    - SHOULD enable tricubic interpolation when HKL grid has ±1 halo
      (REFINE-005: Stage B/C MUST enable, Stage A SHOULD enable)

    Phase A Note:
    This helper is PLAN-LOCAL for testing. Existing Stage A/B/C code will
    not use it until Phase B-D refactor.
    """
    # Lazy import to avoid circular dependency
    # nanobrag_torch is a heavy module that should not be imported at module level
    import nanobrag_torch

    # Instantiate simulator with panel detector config
    simulator = nanobrag_torch.Simulator(
        detector_config=detector_config,
        crystal_config=crystal_config,
        hkl_grid=hkl_grid,
        device=device,
        dtype=dtype
    )

    return simulator


def emit_bragg_frame(
    stage_params: Dict[str, torch.Tensor],
    inputs: Any,
    config: Any,
    simulators: List[Any]
) -> torch.Tensor:
    """
    Centralize full-frame Bragg generation from stage parameters.

    Extracted from Stage A/B/C closures to centralize Bragg stitching logic.

    Args:
        stage_params: Dict of parameter tensors (e.g., scale, cell deltas, etc.)
        inputs: RefinementInputs instance
        config: RefinementConfig instance
        simulators: List of nanobrag_torch.Simulator instances (one per panel)

    Returns:
        torch.Tensor of shape [panel, slow, fast] containing stitched Bragg frame

    Normative Requirements:
    - Output tensor MUST have shape [panel, slow, fast] per spec-db-core.md
    - MUST respect device/dtype from simulators (no hardcoded conversions)
    - SHOULD NOT re-derive physics (use production Simulator.forward())

    Phase A Note:
    This helper is PLAN-LOCAL for testing. Existing Stage A/B/C code will
    not use it until Phase B-D refactor.

    Future Extensions (Phase B-D):
    - Stage B: apply per-reflection Fhkl modifiers before forward pass
    - Stage C: update detector distances before forward pass
    """
    # TODO: Implement Bragg stitching logic
    # For Phase A (TDD nucleus), this can be a minimal stub
    # Full implementation will extract logic from dbex/nanobrag_refinement.py
    # Stage A/B/C closures during Phase B-D refactor

    # Placeholder: return zero tensor matching expected shape
    # Real implementation will:
    # 1. Extract panel shapes from simulators
    # 2. Call simulator.forward() for each panel
    # 3. Stitch panels into [panel, slow, fast] tensor
    # 4. Apply stage-specific parameter updates (scale, modifiers, detector offsets)

    raise NotImplementedError(
        "emit_bragg_frame is a Phase A stub. "
        "Full implementation planned for Phase B-D refactor."
    )
