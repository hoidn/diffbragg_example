"""
RefinementStage protocol and RefinementTelemetry schema (ARCH-REFINE-FLOW-001 Phase A).

Defines the Stage interface for Protocol-based Refinement Engine per:
- docs/spec-db-workflow.md:33 (Engine Contract: accepts ordered list of Stages)
- docs/spec-db-tracing.md §2 (telemetry requirements)

Stage Contract:
- name: str property identifying the stage
- configure(config): optional configuration hook
- run(inputs, telemetry_sink): execute stage and return telemetry dict

RefinementTelemetry Extensions (A4):
- stage_type: str — Stage identifier (e.g., "stage_a", "stage_b", "mock_stage")
- mode: Optional[str] — Stage mode variant (e.g., "shell_modifiers", "parity")
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from dbex.refinement.interfaces import StageResult as CollectorStageResult


class RefinementStage(Protocol):
    """
    Protocol for refinement stages in the Protocol-based Refinement Engine.

    Stages must implement:
    - name: str property or attribute identifying the stage
    - configure(config): optional configuration hook (can be no-op)
    - run(inputs, telemetry_sink): execute stage and return telemetry dict

    Normative Requirement (spec-db-workflow.md:33):
    "RefinementEngine SHALL accept an ordered list of Stage objects and
    MUST NOT hardcode the Stage A→B→C flow."

    Circular Import Mitigation:
    This module MUST NOT import heavy simulator modules (nanobrag_torch,
    dbex.nanobrag_bridge) at module load time. Use TYPE_CHECKING imports
    or lazy imports inside methods if needed.
    """

    @property
    def name(self) -> str:
        """Stage identifier (e.g., 'stage_a', 'stage_b', 'stage_c', 'mock_stage')."""
        ...

    def configure(self, config: Any) -> None:
        """
        Optional configuration hook.

        Args:
            config: RefinementConfig instance (from dbex.nanobrag_refinement)

        Implementations may use this to validate/pre-process config before run().
        No-op is acceptable.
        """
        ...

    def run(
        self,
        inputs: Any,
        telemetry_sink: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Execute stage and return telemetry dict.

        Args:
            inputs: RefinementInputs instance (from dbex.nanobrag_refinement)
            telemetry_sink: Optional path for saving intermediate artifacts

        Returns:
            Dict[str, Any] matching RefinementTelemetry structure (will be
            converted to RefinementTelemetry by engine). Must include:
            - stage_type: str (new A4 field)
            - mode: Optional[str] (new A4 field)
            - All existing RefinementTelemetry fields (chi_squared, masked_mse,
              optimizer, stage, history_size, etc.)

        Normative Requirements:
        - Stages MUST return telemetry dicts that include stage_type field
        - Stages SHOULD NOT modify inputs in-place (copy if needed)
        - Stages MUST respect device/dtype neutrality (no hardcoded .cuda())
        """
        ...


@dataclass
class RefinementTelemetry:
    """
    Telemetry captured during refinement (extended for Protocol-based Engine).

    For multi-stage refinement (Stage A + Stage B + Stage C), this structure
    represents a single stage. The RefinementEngine aggregates multiple telemetry
    objects into Dict[str, RefinementTelemetry] keyed by stage.name.

    Phase A Extensions (ARCH-REFINE-FLOW-001 A4):
    - stage_type: str — Identifies which stage produced this telemetry
    - mode: Optional[str] — Stage mode variant (e.g., "shell_modifiers" for
      Stage B, "parity" for future per-reflection, etc.)

    Backward Compatibility:
    - All existing fields from nanobrag_refinement.RefinementTelemetry preserved
    - to_dict() method includes all existing + new fields
    - HDF5 writers and test assertions use to_dict() for serialization

    Normative Requirements:
    - PHYSICS-LOSS-001: Tracks chi_squared (variance-weighted loss) and
      masked_mse (legacy metric)
    - PHYSICS-LOSS-002: Variance floor telemetry (sigma_floor^2, clamp fraction)
    - PHYSICS-LOSS-003: Canonical Stage A snapshot propagated downstream
    """

    # Original RefinementTelemetry fields (from dbex.nanobrag_refinement)
    optimizer: str
    stage: str
    history_size: int
    max_iter: int
    tolerance_grad: float
    tolerance_change: float
    roi_sample_fraction: float
    roi_count_sampled: int
    roi_count_total: int
    loss_trace_sample: List[float]  # Deprecated: chi_squared_trace_sample preferred
    loss_trace_full: List[Tuple[int, float]]  # Deprecated: chi_squared_trace_full preferred
    best_loss_full: Tuple[float, int]  # Deprecated: chi_squared_best preferred
    param_deltas: Dict[str, float]
    status: str  # "ok" | "early_stop" | "rollback" | "error"
    message: str

    # PERF-WARM-SIM-001: Performance counters
    perf_counters: Optional[Dict[str, Any]] = None

    # PHYSICS-LOSS-001: Dual loss metrics
    chi_squared_trace_sample: Optional[List[float]] = None
    chi_squared_trace_full: Optional[List[Tuple[int, float]]] = None
    chi_squared_best: Optional[Tuple[float, int]] = None
    masked_mse_trace_sample: Optional[List[float]] = None
    masked_mse_trace_full: Optional[List[Tuple[int, float]]] = None
    masked_mse_best: Optional[Tuple[float, int]] = None
    sigma_readout_provenance: Optional[str] = None
    sigma_readout_reference_value: Optional[float] = None

    # PHYSICS-LOSS-002: Variance floor telemetry
    variance_floor_value: Optional[float] = None
    variance_floor_clamp_fraction: Optional[float] = None
    variance_floor_masked_pixels: Optional[int] = None
    variance_floor_clamped_pixels: Optional[int] = None

    # SCALE-008 / TOOLING-VIS-001: Mapping-aware log-scale baseline telemetry
    log_scale_baseline_source: Optional[str] = None
    spot_scale_override_adjustment_factor: Optional[float] = None
    # TOOLING-VIS-001 Phase D.E: Masked-mean telemetry for Stage A baseline derivation
    target_mean_masked: Optional[float] = None
    model_mean_masked: Optional[float] = None

    # ARCH-SIM-CONSTRUCTION-001 C.10: Mask provenance metadata
    mask_metadata: Optional[Dict[str, Any]] = None

    # PHYSICS-LOSS-003: Canonical Stage A metadata
    canonical_stage_label: Optional[str] = None
    canonical_chi_squared: Optional[float] = None
    canonical_chi_squared_iteration: Optional[int] = None
    canonical_roi_count: Optional[int] = None
    canonical_detector_distances_mm: Optional[List[float]] = None
    roi_mode: Optional[str] = None

    # ARCH-REFINE-FLOW-001 Phase A4: Stage identification fields
    stage_type: Optional[str] = None  # e.g., "stage_a", "stage_b", "stage_c", "mock_stage"
    mode: Optional[str] = None  # e.g., "shell_modifiers", "parity", "incremental_ub"

    # ARCH-REFINE-FLOW-001 Phase E: Engine delegation telemetry
    engine_protocol: Optional[str] = None  # e.g., "A→B→C", "A-only", "A→B"
    stage_modes: Optional[Dict[str, str]] = None  # e.g., {"B": "shell", "C": "detector_offsets"}

    # ARCH-REFACTOR-001 Phase B: Schema versioning for future compatibility
    telemetry_version: str = "1.0"

    # ARCH-TELEMETRY-001 Phase C.2: Optional typed StageResult from collector
    # This field carries the collector-emitted StageResult (with StageATelemetry/StageBTelemetry/StageCTelemetry)
    # and is NOT serialized via to_dict() — it's for internal plumbing only so writer can consume typed payloads
    stage_result: Optional['CollectorStageResult'] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize telemetry to dict for HDF5 export and test assertions.

        Returns all fields including new stage_type/mode fields.
        Backward compatible: existing consumers read from dict form.
        """
        result = {
            # Core fields
            "optimizer": self.optimizer,
            "stage": self.stage,
            "history_size": self.history_size,
            "max_iter": self.max_iter,
            "tolerance_grad": self.tolerance_grad,
            "tolerance_change": self.tolerance_change,
            "roi_sample_fraction": self.roi_sample_fraction,
            "roi_count_sampled": self.roi_count_sampled,
            "roi_count_total": self.roi_count_total,
            "loss_trace_sample": self.loss_trace_sample,
            "loss_trace_full": self.loss_trace_full,
            "best_loss_full": self.best_loss_full,
            "param_deltas": self.param_deltas,
            "status": self.status,
            "message": self.message,
        }

        # Optional fields (include if not None)
        if self.perf_counters is not None:
            result["perf_counters"] = self.perf_counters
        if self.chi_squared_trace_sample is not None:
            result["chi_squared_trace_sample"] = self.chi_squared_trace_sample
        if self.chi_squared_trace_full is not None:
            result["chi_squared_trace_full"] = self.chi_squared_trace_full
        if self.chi_squared_best is not None:
            result["chi_squared_best"] = self.chi_squared_best
        if self.masked_mse_trace_sample is not None:
            result["masked_mse_trace_sample"] = self.masked_mse_trace_sample
        if self.masked_mse_trace_full is not None:
            result["masked_mse_trace_full"] = self.masked_mse_trace_full
        if self.masked_mse_best is not None:
            result["masked_mse_best"] = self.masked_mse_best
        if self.sigma_readout_provenance is not None:
            result["sigma_readout_provenance"] = self.sigma_readout_provenance
        if self.sigma_readout_reference_value is not None:
            result["sigma_readout_reference_value"] = self.sigma_readout_reference_value
        if self.variance_floor_value is not None:
            result["variance_floor_value"] = self.variance_floor_value
        if self.variance_floor_clamp_fraction is not None:
            result["variance_floor_clamp_fraction"] = self.variance_floor_clamp_fraction
        if self.variance_floor_masked_pixels is not None:
            result["variance_floor_masked_pixels"] = self.variance_floor_masked_pixels
        if self.variance_floor_clamped_pixels is not None:
            result["variance_floor_clamped_pixels"] = self.variance_floor_clamped_pixels
        if self.canonical_stage_label is not None:
            result["canonical_stage_label"] = self.canonical_stage_label
        if self.canonical_chi_squared is not None:
            result["canonical_chi_squared"] = self.canonical_chi_squared
        if self.canonical_chi_squared_iteration is not None:
            result["canonical_chi_squared_iteration"] = self.canonical_chi_squared_iteration
        if self.canonical_roi_count is not None:
            result["canonical_roi_count"] = self.canonical_roi_count
        if self.canonical_detector_distances_mm is not None:
            result["canonical_detector_distances_mm"] = self.canonical_detector_distances_mm
        if self.roi_mode is not None:
            result["roi_mode"] = self.roi_mode
        if self.log_scale_baseline_source is not None:
            result["log_scale_baseline_source"] = self.log_scale_baseline_source
        if self.spot_scale_override_adjustment_factor is not None:
            result["spot_scale_override_adjustment_factor"] = self.spot_scale_override_adjustment_factor
        if self.target_mean_masked is not None:
            result["target_mean_masked"] = self.target_mean_masked
        if self.model_mean_masked is not None:
            result["model_mean_masked"] = self.model_mean_masked
        if self.mask_metadata is not None:
            result["mask_metadata"] = self.mask_metadata

        # Phase A4 extensions
        if self.stage_type is not None:
            result["stage_type"] = self.stage_type
        if self.mode is not None:
            result["mode"] = self.mode

        # Phase E extensions
        if self.engine_protocol is not None:
            result["engine_protocol"] = self.engine_protocol
        if self.stage_modes is not None:
            result["stage_modes"] = self.stage_modes

        return result


@dataclass
class StageResult:
    """
    Container for stage outputs: telemetry + optional artifacts.

    Per ARCH-STAGE-CONTEXT-001 Phase B.1:
    - Stages return StageResult instead of raw dicts
    - Engine unpacks telemetry (RefinementTelemetry) and artifacts (stage-specific)
    - Telemetry is converted from dict (backward compat) or used directly if already typed
    - Artifacts (StageAArtifacts, StageBArtifacts, StageCArtifacts) cached per stage

    Attributes:
        telemetry: RefinementTelemetry instance or dict (converted to RefinementTelemetry by engine)
        artifacts: Optional stage-specific artifact object (StageAArtifacts, StageBArtifacts, or StageCArtifacts)

    Usage:
        # Stage A
        return StageResult(
            telemetry=telemetry_dict,  # or RefinementTelemetry instance
            artifacts=StageAArtifacts(stage_a_ctx=ctx, context_schema_version="v1")
        )

        # Stage B
        return StageResult(
            telemetry=telemetry_dict,
            artifacts=StageBArtifacts(
                shell_edges=edges, shell_indices=indices, n_shells=n,
                stage_b_baseline_rel_diff=rel_diff, ...
            )
        )

        # Stage C
        return StageResult(
            telemetry=telemetry_dict,
            artifacts=StageCArtifacts(bragg_full=bragg_array)
        )

    Normative Requirements:
    - Telemetry must be either dict or RefinementTelemetry instance
    - Artifacts type should match stage (A→StageAArtifacts, B→StageBArtifacts, C→StageCArtifacts)
    - Engine validates telemetry dict contains required fields when converting
    """
    telemetry: Union[Dict[str, Any], RefinementTelemetry]
    artifacts: Optional[Any] = None  # StageAArtifacts | StageBArtifacts | StageCArtifacts (avoid circular import)
