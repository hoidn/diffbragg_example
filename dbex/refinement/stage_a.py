# dbex/refinement/stage_a.py
"""
Stage A implementation for Protocol-based Refinement Engine.

Wraps existing LBFGS closure logic from run_nanobrag_refinement into a RefinementStage class
per docs/spec-db-workflow.md §7 (Refinement Protocol Architecture) and
ARCH-REFINE-FLOW-001 Phase B.

Stage A optimizes:
- log_scale: global intensity scale (ADU mode)
- log_cell_*_delta: unit cell length perturbations (a/b/c)
- angle_*_raw: unit cell angle perturbations (alpha/beta/gamma)
- orientation_vec: crystal misorientation (3-vector → quaternion → XYZ Euler)

Supports multiple parameterization modes (config.use_incremental_ub, config.use_u_matrix_parameterization).
"""

from pathlib import Path
from typing import Any, Dict, Optional
import numpy as np

# Lazy imports for heavy modules (prevent circular imports)
def _lazy_import_refinement():
    """Lazy import nanobrag_refinement to avoid circular dependencies."""
    from dbex import nanobrag_refinement
    return nanobrag_refinement


class StageA:
    """
    Stage A: Global scale + full crystal refinement (LBFGS).

    Implements RefinementStage protocol per spec-db-workflow.md:33.
    Wraps existing inline LBFGS closure logic from run_nanobrag_refinement.

    Attributes:
        _name: Stage identifier ("stage_a")
        _config: Optional RefinementConfig (set via configure())
    """

    def __init__(self):
        """Initialize Stage A with default name."""
        self._name = "stage_a"
        self._config = None

    @property
    def name(self) -> str:
        """Stage identifier for telemetry aggregation."""
        return self._name

    def configure(self, config: Any) -> None:
        """
        Configure stage with refinement config.

        Args:
            config: RefinementConfig instance with device, dtype, optimizer params,
                   warm-cache flags, ROI sampling, incremental UB mode, etc.
        """
        self._config = config

    def run(
        self,
        inputs: Any,
        telemetry_sink: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Execute Stage A LBFGS refinement and return telemetry dict.

        Args:
            inputs: Dict with keys:
                - 'refinement_inputs': RefinementInputs (target, loss_mask, panel_slices, etc.)
                - 'detector': dxtbx Detector object
                - 'beam': dxtbx Beam object
                - 'crystal': dxtbx Crystal object
                - 'hkl_grid': torch.Tensor structure factor grid
                - 'hkl_metadata': dict with grid dimensions
                - 'baseline_crystal': Optional baseline dxtbx Crystal for misset extraction
                - 'baseline_detector': Optional baseline dxtbx Detector for Stage C telemetry
            telemetry_sink: Optional path for telemetry output (unused by this implementation,
                           telemetry returned via dict instead)

        Returns:
            Telemetry dict with all required RefinementTelemetry fields plus:
            - stage_type: "stage_a"
            - mode: None (or "incremental_ub"/"u_matrix" if those modes are enabled)

        Raises:
            RuntimeError: If simulator fails or gradients are NaN/Inf
            ValueError: If config not set via configure()
        """
        if self._config is None:
            raise ValueError("StageA not configured. Call configure(config) before run().")

        # Delegate to existing inline logic in run_nanobrag_refinement
        # Import lazily to avoid circular imports
        nanobrag_refinement = _lazy_import_refinement()

        # Extract inputs
        refinement_inputs = inputs['refinement_inputs']
        detector = inputs['detector']
        beam = inputs['beam']
        crystal = inputs['crystal']
        hkl_grid = inputs['hkl_grid']
        hkl_metadata = inputs['hkl_metadata']
        baseline_crystal = inputs.get('baseline_crystal', None)
        baseline_detector = inputs.get('baseline_detector', None)

        # Call existing run_nanobrag_refinement (which contains Stage A inline logic)
        # This returns (bragg_refined, telemetry_dict) where telemetry_dict["A"] contains Stage A telemetry
        bragg_refined, telemetry_dict = nanobrag_refinement.run_nanobrag_refinement(
            inputs=refinement_inputs,
            detector=detector,
            beam=beam,
            crystal=crystal,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            config=self._config,
            baseline_crystal=baseline_crystal,
            baseline_detector=baseline_detector
        )

        # Extract Stage A telemetry
        if "A" not in telemetry_dict:
            raise RuntimeError("Stage A telemetry missing from run_nanobrag_refinement output")

        stage_a_telemetry_obj = telemetry_dict["A"]

        # Convert RefinementTelemetry instance to dict for engine aggregation
        telemetry_output = stage_a_telemetry_obj.to_dict()

        # Add stage_type and mode fields (Phase A4 schema extension)
        telemetry_output["stage_type"] = "stage_a"

        # Determine mode based on config flags
        if self._config.use_incremental_ub:
            telemetry_output["mode"] = "incremental_ub"
        elif self._config.use_u_matrix_parameterization:
            telemetry_output["mode"] = "u_matrix"
        else:
            telemetry_output["mode"] = None  # Default cell+misset path

        return telemetry_output
