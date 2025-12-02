"""
TDD nucleus test for RefinementEngine (ARCH-REFINE-FLOW-001 Phase A).

Validates that the engine can execute a dummy Stage object and aggregate telemetry
per spec-db-workflow.md:33 (Engine Contract).

Test Specification:
- Test Name: test_engine_executes_mock_stage
- Purpose: Verify RefinementEngine executes dummy Stage and aggregates telemetry
- Expected: Engine.run() executes stage once, returns Dict[str, RefinementTelemetry]
  with stage_type="mock_stage" field
"""

import pytest
from typing import Dict, Any, Optional
from pathlib import Path


def test_engine_executes_mock_stage():
    """
    TDD nucleus: validate RefinementEngine executes mock stage and aggregates telemetry.

    Acceptance (Phase A0):
    - Test PASSES after A1-A2 implementation (RefinementStage protocol + RefinementEngine skeleton)
    - MockStage.run() is called exactly once
    - Engine.telemetry returns Dict with "mock_stage" key
    - RefinementTelemetry includes stage_type="mock_stage" field
    - ARCH-REFINE-001 Phase B.5: Engine requires inputs['context'] (RefinementContext)
    """
    from dbex.refinement import RefinementEngine, RefinementStage, RefinementTelemetry, build_refinement_context
    from dbex.refinement.config import RefinementConfig
    import torch
    import numpy as np

    # Mock inputs (minimal, not real refinement data)
    class MockRefinementInputs:
        """Dummy inputs for testing."""
        target = np.zeros((1, 10, 10), dtype=np.float32)
        loss_mask = np.ones((1, 10, 10), dtype=bool)
        panel_slices = [(0, (0, 10, 0, 10))]
        trusted_mask = np.ones((1, 10, 10), dtype=bool)
        sigma_readout = np.ones((1, 10, 10), dtype=np.float32) * 3.0
        target_representation = "photons"
        global_scale_hint = 1.0

    class MockDetector:
        """Minimal dxtbx Detector mock."""
        pass

    class MockBeam:
        """Minimal dxtbx Beam mock."""
        pass

    class MockCrystal:
        """Minimal dxtbx Crystal mock."""
        pass

    # Build minimal RefinementContext
    hkl_grid = torch.zeros((10, 10, 10), dtype=torch.complex64)
    hkl_metadata = {"has_halo": False, "nabc_grid": (10, 10, 10), "default_F": 0.0}
    ctx = build_refinement_context(
        refinement_inputs=MockRefinementInputs(),
        detector=MockDetector(),
        beam=MockBeam(),
        crystal=MockCrystal(),
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
    )

    # Define MockStage implementing RefinementStage protocol
    class MockStage(RefinementStage):
        """Dummy stage for testing engine contract."""

        @property
        def name(self) -> str:
            return "mock_stage"

        def configure(self, config: RefinementConfig) -> None:
            """Optional configuration (no-op for mock)."""
            pass

        def run(
            self,
            inputs: Any,
            telemetry_sink: Optional[Path] = None
        ) -> Dict[str, Any]:
            """
            Return minimal telemetry dict matching RefinementTelemetry structure.

            Returns only required fields plus stage_type/mode to validate
            the engine can aggregate telemetry from arbitrary stages.
            """
            return {
                # Required RefinementTelemetry fields
                "optimizer": "mock",
                "stage": "mock_stage",
                "history_size": 0,
                "max_iter": 0,
                "tolerance_grad": 0.0,
                "tolerance_change": 0.0,
                "roi_sample_fraction": 0.0,
                "roi_count_sampled": 0,
                "roi_count_total": 0,
                "loss_trace_sample": [],
                "loss_trace_full": [],
                "best_loss_full": (1.0, 0),
                "param_deltas": {},
                "status": "ok",
                "message": "MockStage executed",
                # Phase A4 extensions (optional fields)
                "stage_type": "mock_stage",
                "mode": None,
            }

    # Instantiate engine with mock config
    config = RefinementConfig()
    stages = [MockStage()]
    engine = RefinementEngine(stages=stages, config=config)

    # Execute engine with context in inputs dict (ARCH-REFINE-001 Phase B.1)
    telemetry = engine.run(inputs={'context': ctx})

    # Validate telemetry structure
    assert isinstance(telemetry, dict), "Engine.run() should return Dict[str, RefinementTelemetry]"
    assert "mock_stage" in telemetry, "Telemetry dict should have 'mock_stage' key"

    stage_telemetry = telemetry["mock_stage"]
    assert isinstance(stage_telemetry, RefinementTelemetry), "Telemetry value should be RefinementTelemetry instance"

    # Validate stage_type field exists (A4 requirement)
    assert hasattr(stage_telemetry, "stage_type"), "RefinementTelemetry should have stage_type field"
    assert stage_telemetry.stage_type == "mock_stage", "stage_type should match MockStage identifier"

    # Validate basic telemetry fields
    assert stage_telemetry.stage == "mock_stage", "stage field should match stage name"
    assert stage_telemetry.status == "ok", "MockStage should complete successfully"


def test_engine_requires_context():
    """
    Validate RefinementEngine.run() raises ValueError when 'context' key is missing.

    Acceptance (ARCH-ENGINE-003, spec-db-workflow.md §33):
    - Engine.run() with inputs dict lacking 'context' key raises ValueError
    - Error message references ARCH-REFINE-001 Phase B.1 and build_refinement_context
    """
    from dbex.refinement import RefinementEngine, RefinementStage
    from dbex.refinement.config import RefinementConfig

    # Define minimal MockStage (will never execute due to ValueError)
    class MockStage(RefinementStage):
        @property
        def name(self) -> str:
            return "mock_stage"

        def configure(self, config: RefinementConfig) -> None:
            pass

        def run(self, inputs: Any, telemetry_sink: Optional[Path] = None) -> Dict[str, Any]:
            return {}

    config = RefinementConfig()
    stages = [MockStage()]
    engine = RefinementEngine(stages=stages, config=config)

    # Attempt to run engine without 'context' key
    with pytest.raises(ValueError, match="RefinementContext missing from inputs"):
        engine.run(inputs={})

    # Validate error message mentions ARCH-REFINE-001 and build_refinement_context
    try:
        engine.run(inputs={})
    except ValueError as e:
        assert "ARCH-REFINE-001" in str(e), "Error message should reference ARCH-REFINE-001"
        assert "build_refinement_context" in str(e), "Error message should mention build_refinement_context"
    else:
        pytest.fail("Expected ValueError was not raised")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
