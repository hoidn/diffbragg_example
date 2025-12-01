"""
RefinementEngine for Protocol-based Refinement (ARCH-REFINE-FLOW-001 Phase A).

Implements the engine skeleton per:
- docs/spec-db-workflow.md:33 (Engine Contract: ordered stages, no hardcoded A→B→C)
- docs/spec-db-tracing.md §2 (telemetry aggregation)

Engine Contract:
- Accepts ordered list of RefinementStage objects
- Executes stages sequentially in order
- Aggregates telemetry into Dict[str, RefinementTelemetry] keyed by stage.name
- Does NOT hardcode Stage A→B→C flow (arbitrary stage sequences allowed)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .stage import RefinementStage, RefinementTelemetry


class RefinementEngine:
    """
    Protocol-based refinement engine executing ordered Stage objects.

    Normative Requirement (spec-db-workflow.md:33):
    "The internal Python API (RefinementEngine or equivalent) SHALL accept
    an ordered list of Stage objects and MUST NOT hardcode the Stage A→B→C flow."

    Usage:
        config = RefinementConfig(...)
        stages = [StageA(...), StageB(...), StageC(...)]
        engine = RefinementEngine(stages=stages, config=config)
        telemetry = engine.run(inputs)  # Returns Dict[str, RefinementTelemetry]

    Attributes:
        stages: Ordered list of RefinementStage objects to execute
        config: RefinementConfig instance (from dbex.nanobrag_refinement)
        _telemetry: Aggregated telemetry dict (populated after run())

    Methods:
        run(inputs): Execute all stages and return aggregated telemetry
        telemetry: Property returning aggregated telemetry dict
    """

    def __init__(self, stages: List[RefinementStage], config: Any):
        """
        Initialize RefinementEngine with ordered stages and config.

        Args:
            stages: Ordered list of RefinementStage objects to execute
                   (e.g., [StageA(), StageB(), StageC()] or custom sequences)
            config: RefinementConfig instance (from dbex.nanobrag_refinement)

        Raises:
            ValueError: If stages list is empty

        Normative Requirements:
        - Engine MUST accept arbitrary stage sequences (not just A→B→C)
        - Engine MUST preserve stage execution order
        """
        if not stages:
            raise ValueError("RefinementEngine requires at least one stage")

        self.stages = stages
        self.config = config
        self._telemetry: Dict[str, RefinementTelemetry] = {}
        # Initialize cache vars for custom attributes (Phase 8 fix #2)
        self._stage_b_mode = None
        self._stage_b_n_asu_unique = None
        self._stage_b_optimizer_type = None
        self._stage_b_asu_modifier_stats = None
        self._stage_c_bragg_full = None  # Final Bragg array from Stage C (Phase A.4)

    def run(
        self,
        inputs: Any,
        telemetry_sink: Optional[Path] = None
    ) -> Dict[str, RefinementTelemetry]:
        """
        Execute all stages in order and aggregate telemetry.

        Args:
            inputs: Dict with required 'context' key (RefinementContext) plus legacy keys
            telemetry_sink: Optional directory for saving stage artifacts

        Returns:
            Dict[str, RefinementTelemetry] keyed by stage.name, containing
            telemetry from each executed stage

        Execution Flow:
        1. Validate 'context' key is present in inputs (ARCH-REFINE-001 Phase B.1)
        2. Configure each stage (call stage.configure(config))
        3. Execute each stage (call stage.run(inputs, telemetry_sink))
        4. Convert returned dict to RefinementTelemetry instance
        5. Aggregate into _telemetry dict keyed by stage.name
        6. Propagate 'context' and prior stage telemetry to next stage via inputs dict
        7. Return aggregated telemetry

        Normative Requirements:
        - Stages MUST execute in the order provided to __init__
        - Engine MUST NOT skip stages or reorder them
        - Telemetry MUST include all fields returned by stage.run()
        - 'context' key MUST be present in inputs (ARCH-REFINE-001 Phase B.1)

        Raises:
            ValueError: If 'context' key is missing from inputs dict
        """
        # ARCH-REFINE-001 Phase B.1: Require 'context' in inputs
        if isinstance(inputs, dict):
            if 'context' not in inputs:
                raise ValueError(
                    "RefinementContext missing from inputs. Per ARCH-REFINE-001 Phase B.1, "
                    "all engine invocations must include a 'context' key with a RefinementContext instance. "
                    "Use dbex.refinement.build_refinement_context to create the context object."
                )
        else:
            # If inputs is not a dict, it's a legacy code path (should not happen post-Phase B.1)
            raise ValueError(
                "Engine.run() requires inputs to be a dict with 'context' key. "
                "Per ARCH-REFINE-001 Phase B.1, legacy non-dict inputs are no longer supported."
            )

        self._telemetry = {}
        enriched_inputs = inputs.copy() if isinstance(inputs, dict) else inputs

        for stage_idx, stage in enumerate(self.stages):
            # Configure stage (optional hook, may be no-op)
            stage.configure(self.config)

            # Enrich inputs with prior stage telemetry (for Stage B/C that depend on Stage A)
            # ARCH-REFINE-001 Phase B.1: 'context' is already present and propagated unchanged
            if stage_idx > 0 and isinstance(enriched_inputs, dict):
                # Add stage_a_telemetry for StageB and StageC (expects dict from StageA.run())
                if (stage.name == "stage_b" or stage.name == "stage_c") and "stage_a" in self._telemetry:
                    # Convert RefinementTelemetry back to dict for StageB/StageC consumption
                    from dataclasses import asdict
                    stage_a_dict = asdict(self._telemetry["stage_a"])
                    enriched_inputs["stage_a_telemetry"] = stage_a_dict
                    # Propagate stage_a_ctx for warm cache support (Phase C2)
                    # This is stored separately from telemetry dict in the previous stage run
                    if hasattr(self, '_stage_a_ctx_cache'):
                        enriched_inputs["stage_a_ctx"] = self._stage_a_ctx_cache

                # Add stage_b_telemetry for StageC if Stage B was run (optional - Stage A→C skip supported)
                if stage.name == "stage_c" and "stage_b" in self._telemetry:
                    stage_b_dict = asdict(self._telemetry["stage_b"])
                    enriched_inputs["stage_b_telemetry"] = stage_b_dict

            # Execute stage and get telemetry dict
            telemetry_dict = stage.run(enriched_inputs, telemetry_sink)

            # Cache stage_a_ctx for propagation to subsequent stages (Phase C2)
            if stage.name == "stage_a" and "stage_a_ctx" in telemetry_dict:
                self._stage_a_ctx_cache = telemetry_dict.pop("stage_a_ctx")

            # Cache shell metadata from Stage B for Bragg reconstruction (Phase C2)
            if stage.name == "stage_b":
                self._stage_b_shell_edges = telemetry_dict.get("shell_edges")
                self._stage_b_shell_indices = telemetry_dict.get("shell_indices")
                self._stage_b_n_shells = telemetry_dict.get("n_shells")
                # Cache custom attributes for per-reflection mode (Phase 8 fix #2)
                self._stage_b_mode = telemetry_dict.get("stage_b_mode")
                self._stage_b_n_asu_unique = telemetry_dict.get("n_asu_unique")
                self._stage_b_optimizer_type = telemetry_dict.get("optimizer_type")
                self._stage_b_asu_modifier_stats = telemetry_dict.get("asu_modifier_stats")

            # Filter out non-RefinementTelemetry fields before conversion
            # stage_a_ctx, shell_edges, shell_indices, n_shells are not RefinementTelemetry fields
            # (stage_type and mode ARE now part of RefinementTelemetry per Phase A4)
            # Phase 7/8: stage_b_mode, n_asu_unique, optimizer_type, asu_modifier_stats are custom attrs
            # Phase A.4: bragg_full is Stage C final output (cached separately, not in RefinementTelemetry)
            excluded_fields = {'stage_a_ctx', 'shell_edges', 'shell_indices', 'n_shells',
                             'stage_b_mode', 'n_asu_unique', 'optimizer_type', 'asu_modifier_stats',
                             'bragg_full'}
            telemetry_core_dict = {k: v for k, v in telemetry_dict.items()
                                  if k not in excluded_fields}

            # Cache Stage C bragg_full for final Bragg reconstruction (Phase A.4)
            if stage.name == "stage_c" and "bragg_full" in telemetry_dict:
                self._stage_c_bragg_full = telemetry_dict["bragg_full"]

            # Convert dict to RefinementTelemetry instance
            # Note: stage.run() returns a dict matching RefinementTelemetry structure
            telemetry = RefinementTelemetry(**telemetry_core_dict)

            # Restore custom attributes to RefinementTelemetry object (Phase 8 fix #2)
            # These were cached above but excluded from the constructor
            if stage.name == "stage_b":
                if self._stage_b_mode is not None:
                    telemetry.stage_b_mode = self._stage_b_mode
                if self._stage_b_n_asu_unique is not None:
                    telemetry.n_asu_unique = self._stage_b_n_asu_unique
                if self._stage_b_optimizer_type is not None:
                    telemetry.optimizer_type = self._stage_b_optimizer_type
                if self._stage_b_asu_modifier_stats is not None:
                    telemetry.asu_modifier_stats = self._stage_b_asu_modifier_stats

            # Aggregate into telemetry dict keyed by stage name
            self._telemetry[stage.name] = telemetry

        return self._telemetry

    @property
    def telemetry(self) -> Dict[str, RefinementTelemetry]:
        """
        Return aggregated telemetry from all executed stages.

        Returns:
            Dict[str, RefinementTelemetry] keyed by stage.name

        Note: Returns empty dict if run() has not been called yet.
        """
        return self._telemetry
