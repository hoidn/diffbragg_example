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
from typing import Any, Dict, List, Optional, Union

from .stage import RefinementStage, RefinementTelemetry, StageResult


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
        # ARCH-STAGE-CONTEXT-001 Phase B.1: Unified artifacts storage
        self._artifacts: Dict[str, Any] = {}  # Replaces stage-specific caches

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
        self._artifacts = {}  # Reset artifacts for new run
        enriched_inputs = inputs.copy() if isinstance(inputs, dict) else inputs

        for stage_idx, stage in enumerate(self.stages):
            # Configure stage (optional hook, may be no-op)
            stage.configure(self.config)

            # Enrich inputs with prior stage telemetry + artifacts (for Stage B/C that depend on Stage A)
            # ARCH-REFINE-001 Phase B.1: 'context' is already present and propagated unchanged
            if stage_idx > 0 and isinstance(enriched_inputs, dict):
                # Add stage_a_telemetry for StageB and StageC (expects dict from StageA.run())
                if (stage.name == "stage_b" or stage.name == "stage_c") and "stage_a" in self._telemetry:
                    # Convert RefinementTelemetry back to dict for StageB/StageC consumption
                    from dataclasses import asdict
                    stage_a_dict = asdict(self._telemetry["stage_a"])
                    enriched_inputs["stage_a_telemetry"] = stage_a_dict

                    # ARCH-STAGE-CONTEXT-001 Phase B.1: Propagate stage_a_ctx from artifacts
                    if "stage_a" in self._artifacts and self._artifacts["stage_a"] is not None:
                        enriched_inputs["stage_a_ctx"] = self._artifacts["stage_a"].stage_a_ctx

                # Add stage_b_telemetry for StageC if Stage B was run (optional - Stage A→C skip supported)
                if stage.name == "stage_c" and "stage_b" in self._telemetry:
                    stage_b_dict = asdict(self._telemetry["stage_b"])
                    enriched_inputs["stage_b_telemetry"] = stage_b_dict

            # Execute stage and get result (StageResult or legacy dict for backward compat)
            stage_output = stage.run(enriched_inputs, telemetry_sink)

            # ARCH-STAGE-CONTEXT-001 Phase B.1: Handle StageResult vs legacy dict
            if isinstance(stage_output, StageResult):
                # New path: unpack telemetry and artifacts
                telemetry_data = stage_output.telemetry
                artifacts = stage_output.artifacts

                # Cache artifacts keyed by stage name
                if artifacts is not None:
                    self._artifacts[stage.name] = artifacts

                # Convert telemetry to dict if it's already a RefinementTelemetry instance
                if isinstance(telemetry_data, RefinementTelemetry):
                    from dataclasses import asdict
                    telemetry_dict = asdict(telemetry_data)
                else:
                    telemetry_dict = telemetry_data
            else:
                # Legacy path: treat as dict (backward compatibility for tests/mocks)
                telemetry_dict = stage_output
                artifacts = None

            # Convert dict to RefinementTelemetry instance
            # Note: stage.run() returns a dict matching RefinementTelemetry structure
            # ARCH-STAGE-CONTEXT-001 Phase B.4: No longer filter out baseline fields;
            # writer now sources these from artifacts instead of telemetry
            telemetry = RefinementTelemetry(**telemetry_dict)

            # ARCH-STAGE-CONTEXT-001 Phase B.1: Restore Stage B custom attributes from artifacts to telemetry
            # These are not core RefinementTelemetry fields but are expected by tests
            # Phase B.4: Removed baseline parity diagnostics rebinding; writer now sources these from artifacts
            if stage.name == "stage_b" and artifacts is not None:
                if hasattr(artifacts, 'stage_b_mode') and artifacts.stage_b_mode is not None:
                    telemetry.stage_b_mode = artifacts.stage_b_mode
                if hasattr(artifacts, 'n_asu_unique') and artifacts.n_asu_unique is not None:
                    telemetry.n_asu_unique = artifacts.n_asu_unique
                if hasattr(artifacts, 'optimizer_type') and artifacts.optimizer_type is not None:
                    telemetry.optimizer_type = artifacts.optimizer_type
                if hasattr(artifacts, 'asu_modifier_stats') and artifacts.asu_modifier_stats is not None:
                    telemetry.asu_modifier_stats = artifacts.asu_modifier_stats

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

    @property
    def artifacts(self) -> Dict[str, Any]:
        """
        Return artifacts from all executed stages (ARCH-STAGE-CONTEXT-001 Phase B.1).

        Returns:
            Dict[str, StageAArtifacts|StageBArtifacts|StageCArtifacts] keyed by stage.name

        Usage:
            # After engine.run()
            stage_a_ctx = engine.artifacts["stage_a"].stage_a_ctx  # Warm cache
            shell_edges = engine.artifacts["stage_b"].shell_edges  # Shell metadata
            bragg_full = engine.artifacts["stage_c"].bragg_full  # Final Bragg tensor

        Note:
        - Returns empty dict if run() has not been called yet
        - Stages that return no artifacts (or None) will not have entries
        """
        return self._artifacts
