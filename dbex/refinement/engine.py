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

    def run(
        self,
        inputs: Any,
        telemetry_sink: Optional[Path] = None
    ) -> Dict[str, RefinementTelemetry]:
        """
        Execute all stages in order and aggregate telemetry.

        Args:
            inputs: RefinementInputs instance (from dbex.nanobrag_refinement)
            telemetry_sink: Optional directory for saving stage artifacts

        Returns:
            Dict[str, RefinementTelemetry] keyed by stage.name, containing
            telemetry from each executed stage

        Execution Flow:
        1. Configure each stage (call stage.configure(config))
        2. Execute each stage (call stage.run(inputs, telemetry_sink))
        3. Convert returned dict to RefinementTelemetry instance
        4. Aggregate into _telemetry dict keyed by stage.name
        5. Return aggregated telemetry

        Normative Requirements:
        - Stages MUST execute in the order provided to __init__
        - Engine MUST NOT skip stages or reorder them
        - Telemetry MUST include all fields returned by stage.run()
        """
        self._telemetry = {}

        for stage in self.stages:
            # Configure stage (optional hook, may be no-op)
            stage.configure(self.config)

            # Execute stage and get telemetry dict
            telemetry_dict = stage.run(inputs, telemetry_sink)

            # Convert dict to RefinementTelemetry instance
            # Note: stage.run() returns a dict matching RefinementTelemetry structure
            telemetry = RefinementTelemetry(**telemetry_dict)

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
