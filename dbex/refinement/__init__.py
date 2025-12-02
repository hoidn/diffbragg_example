"""
Protocol-based Refinement Engine package (ARCH-REFINE-FLOW-001).

Public API:
- RefinementEngine: Execute ordered list of RefinementStage objects
- RefinementStage: Protocol/interface for stage implementations
- RefinementTelemetry: Extended telemetry schema with stage_type/mode fields

Normative Requirements:
- docs/spec-db-workflow.md:33 (Engine Contract: ordered stages, no hardcoded A→B→C)
- docs/spec-db-tracing.md §2 (telemetry requirements)

Usage:
    from dbex.refinement import RefinementEngine, RefinementStage, RefinementTelemetry
    from dbex.refinement.config import RefinementConfig

    # Define custom stages implementing RefinementStage protocol
    class MyStage(RefinementStage):
        ...

    # Instantiate engine with ordered stages
    config = RefinementConfig(...)
    stages = [MyStage(), ...]
    engine = RefinementEngine(stages=stages, config=config)

    # Execute refinement
    telemetry = engine.run(inputs)  # Dict[str, RefinementTelemetry]
"""

from .context import RefinementContext, build_refinement_context
from .engine import RefinementEngine
from .stage import RefinementStage, RefinementTelemetry
from .stage_a import StageA

__all__ = [
    "RefinementContext",
    "build_refinement_context",
    "RefinementEngine",
    "RefinementStage",
    "RefinementTelemetry",
    "StageA",
]
