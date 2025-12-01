"""
Tests for RefinementContext and JobContext builders (ARCH-REFINE-001 Phase B.5).

Validates that:
- build_refinement_context copies JobContext extras (asu_map, hkl_indices_grid, halo_mask)
- build_job_context validates sigma_reference_value > 0 per PHYSICS-LOSS-001
- Builders enforce required field contracts per context.idl.md

Spec references:
- docs/architecture/dbex/refinement/context.idl.md
- docs/spec-db-workflow.md §7 (Refinement Protocol Architecture)
- docs/spec-db-core.md §§32-68 (Variance inputs and sigma provenance)
- docs/findings.md REFINE-005/REFINE-010 (HKL metadata propagation)
"""

import pytest
import numpy as np
import torch

from dbex.refinement.context import (
    build_refinement_context,
    build_job_context,
    RefinementContext,
    JobContext,
)


def test_build_refinement_context_copies_job_context_metadata():
    """
    Validate build_refinement_context auto-copies asu_map/hkl_indices_grid/halo_mask from JobContext.

    Acceptance (REFINE-005, REFINE-010, ARCH-REFINE-001 Phase B.3):
    - When job_context is provided with asu_map, builder copies it to RefinementContext.asu_map
    - When job_context.extras contains 'hkl_indices_grid', builder copies to RefinementContext.hkl_indices_grid
    - When job_context.extras contains 'halo_mask', builder copies to RefinementContext.halo_mask
    - Copied asu_map is converted from np.ndarray to torch.Tensor if needed
    - Copied hkl_indices_grid and halo_mask remain np.ndarray
    - Shape validation: asu_map shape must match hkl_grid shape
    """
    # Create minimal mock objects
    class MockRefinementInputs:
        target = np.zeros((1, 10, 10), dtype=np.float32)
        loss_mask = np.ones((1, 10, 10), dtype=bool)
        panel_slices = [(0, (0, 10, 0, 10))]
        trusted_mask = np.ones((1, 10, 10), dtype=bool)
        sigma_readout = np.ones((1, 10, 10), dtype=np.float32) * 3.0

    class MockDetector:
        pass

    class MockBeam:
        pass

    class MockCrystal:
        pass

    class MockDataLoad:
        pass

    class MockConfig:
        pass

    # Create HKL grid and metadata
    hkl_grid = torch.zeros((5, 6, 7), dtype=torch.complex64)
    hkl_metadata = {
        "has_halo": True,
        "nabc_grid": (5, 6, 7),
        "default_F": 0.0,
    }

    # Create JobContext with asu_map and extras containing hkl_indices_grid/halo_mask
    asu_map_np = np.random.randint(0, 10, size=(5, 6, 7), dtype=np.int32)
    hkl_indices_grid_np = np.zeros((5, 6, 7, 3), dtype=np.int32)
    halo_mask_np = np.random.rand(5, 6, 7) > 0.5

    job_context = JobContext(
        cli_args={},
        dataload=MockDataLoad(),
        calibration_metadata=None,
        sigma_provenance="cli_override",
        sigma_reference_value=3.0,
        refinement_config=MockConfig(),
        hkl_metadata=hkl_metadata,
        asu_map=asu_map_np,
        spot_scale_override=1.0,
        hkl_source="refined",
        hkl_path="/fake/path.mtz",
        extras={
            "hkl_indices_grid": hkl_indices_grid_np,
            "halo_mask": halo_mask_np,
        },
    )

    # Build RefinementContext without explicit asu_map/hkl_indices_grid/halo_mask
    ctx = build_refinement_context(
        refinement_inputs=MockRefinementInputs(),
        detector=MockDetector(),
        beam=MockBeam(),
        crystal=MockCrystal(),
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        job_context=job_context,
    )

    # Validate asu_map was copied and converted to torch.Tensor
    assert ctx.asu_map is not None, "asu_map should be copied from job_context"
    assert isinstance(ctx.asu_map, torch.Tensor), "asu_map should be torch.Tensor"
    assert ctx.asu_map.shape == hkl_grid.shape, "asu_map shape must match hkl_grid"
    assert torch.allclose(ctx.asu_map, torch.from_numpy(asu_map_np)), "asu_map values should match"

    # Validate hkl_indices_grid was copied
    assert ctx.hkl_indices_grid is not None, "hkl_indices_grid should be copied from job_context.extras"
    assert isinstance(ctx.hkl_indices_grid, np.ndarray), "hkl_indices_grid should remain np.ndarray"
    assert np.array_equal(ctx.hkl_indices_grid, hkl_indices_grid_np), "hkl_indices_grid values should match"

    # Validate halo_mask was copied
    assert ctx.halo_mask is not None, "halo_mask should be copied from job_context.extras"
    assert isinstance(ctx.halo_mask, np.ndarray), "halo_mask should remain np.ndarray"
    assert np.array_equal(ctx.halo_mask, halo_mask_np), "halo_mask values should match"


def test_build_refinement_context_explicit_metadata_overrides_job_context():
    """
    Validate explicit asu_map/hkl_indices_grid/halo_mask arguments override job_context.

    Acceptance:
    - When both explicit arguments and job_context are provided, explicit wins
    - Useful for tests that want to inject specific metadata without full JobContext
    """
    class MockRefinementInputs:
        target = np.zeros((1, 10, 10), dtype=np.float32)

    class MockDetector:
        pass

    class MockBeam:
        pass

    class MockCrystal:
        pass

    class MockDataLoad:
        pass

    class MockConfig:
        pass

    hkl_grid = torch.zeros((3, 4, 5), dtype=torch.complex64)
    hkl_metadata = {"has_halo": False, "nabc_grid": (3, 4, 5), "default_F": 0.0}

    # Create JobContext with one set of metadata
    job_asu_map = np.zeros((3, 4, 5), dtype=np.int32)
    job_context = JobContext(
        cli_args={},
        dataload=MockDataLoad(),
        calibration_metadata=None,
        sigma_provenance="metadata",
        sigma_reference_value=2.5,
        refinement_config=MockConfig(),
        hkl_metadata=hkl_metadata,
        asu_map=job_asu_map,
        extras={},
    )

    # Provide explicit asu_map that differs from job_context
    explicit_asu_map = torch.ones((3, 4, 5), dtype=torch.int32)
    ctx = build_refinement_context(
        refinement_inputs=MockRefinementInputs(),
        detector=MockDetector(),
        beam=MockBeam(),
        crystal=MockCrystal(),
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        asu_map=explicit_asu_map,
        job_context=job_context,
    )

    # Validate explicit argument wins
    assert torch.allclose(ctx.asu_map, explicit_asu_map), "Explicit asu_map should override job_context"
    assert not torch.allclose(ctx.asu_map, torch.from_numpy(job_asu_map)), "Should not use job_context asu_map"


def test_build_job_context_rejects_invalid_sigma_reference():
    """
    Validate build_job_context enforces sigma_reference_value > 0 per PHYSICS-LOSS-001.

    Acceptance:
    - sigma_reference_value = 0 raises ValueError
    - sigma_reference_value < 0 raises ValueError
    - Error message references spec-db-core.md variance requirements
    """
    class MockDataLoad:
        pass

    class MockConfig:
        pass

    hkl_metadata = {"has_halo": True, "nabc_grid": (10, 10, 10), "default_F": 0.0}

    # Test sigma_reference_value = 0
    with pytest.raises(ValueError, match="sigma_reference_value must be strictly positive"):
        build_job_context(
            cli_args={},
            dataload=MockDataLoad(),
            calibration_metadata=None,
            sigma_provenance="cli_override",
            sigma_reference_value=0.0,
            refinement_config=MockConfig(),
            hkl_metadata=hkl_metadata,
        )

    # Test sigma_reference_value < 0
    with pytest.raises(ValueError, match="sigma_reference_value must be strictly positive"):
        build_job_context(
            cli_args={},
            dataload=MockDataLoad(),
            calibration_metadata=None,
            sigma_provenance="cli_override",
            sigma_reference_value=-1.5,
            refinement_config=MockConfig(),
            hkl_metadata=hkl_metadata,
        )


def test_build_job_context_rejects_empty_sigma_provenance():
    """
    Validate build_job_context enforces non-empty sigma_provenance per PHYSICS-LOSS-001.

    Acceptance:
    - Empty string raises ValueError
    - Whitespace-only string raises ValueError
    - Error message references PHYSICS-LOSS-001
    """
    class MockDataLoad:
        pass

    class MockConfig:
        pass

    hkl_metadata = {"has_halo": True, "nabc_grid": (10, 10, 10), "default_F": 0.0}

    # Test empty string
    with pytest.raises(ValueError, match="sigma_provenance must be non-empty"):
        build_job_context(
            cli_args={},
            dataload=MockDataLoad(),
            calibration_metadata=None,
            sigma_provenance="",
            sigma_reference_value=3.0,
            refinement_config=MockConfig(),
            hkl_metadata=hkl_metadata,
        )

    # Test whitespace-only string
    with pytest.raises(ValueError, match="sigma_provenance must be non-empty"):
        build_job_context(
            cli_args={},
            dataload=MockDataLoad(),
            calibration_metadata=None,
            sigma_provenance="   ",
            sigma_reference_value=3.0,
            refinement_config=MockConfig(),
            hkl_metadata=hkl_metadata,
        )


def test_build_job_context_validates_hkl_metadata_has_halo():
    """
    Validate build_job_context requires hkl_metadata['has_halo'] per spec-db-workflow.md:53-54.

    Acceptance:
    - Missing 'has_halo' key raises ValueError
    - Error message references spec-db-workflow.md
    """
    class MockDataLoad:
        pass

    class MockConfig:
        pass

    # hkl_metadata missing 'has_halo' key
    incomplete_hkl_metadata = {"nabc_grid": (10, 10, 10), "default_F": 0.0}

    with pytest.raises(ValueError, match="hkl_metadata missing required key 'has_halo'"):
        build_job_context(
            cli_args={},
            dataload=MockDataLoad(),
            calibration_metadata=None,
            sigma_provenance="cli_override",
            sigma_reference_value=3.0,
            refinement_config=MockConfig(),
            hkl_metadata=incomplete_hkl_metadata,
        )


def test_build_job_context_accepts_valid_inputs():
    """
    Validate build_job_context succeeds with all valid inputs.

    Acceptance:
    - Returns JobContext instance
    - All fields match inputs
    - No exceptions raised
    """
    class MockDataLoad:
        pass

    class MockConfig:
        pass

    cli_args = {"experiment": "/fake/path.expt"}
    dataload = MockDataLoad()
    calibration_metadata = {"spot_scale_override": 1.5}
    sigma_provenance = "calibrated_map"
    sigma_reference_value = 2.8
    refinement_config = MockConfig()
    hkl_metadata = {"has_halo": True, "nabc_grid": (10, 10, 10), "default_F": 0.0}
    asu_map = np.random.randint(0, 100, size=(10, 10, 10), dtype=np.int32)
    spot_scale_override = 1.2
    hkl_source = "refined"
    hkl_path = "/fake/mtz.mtz"

    job_ctx = build_job_context(
        cli_args=cli_args,
        dataload=dataload,
        calibration_metadata=calibration_metadata,
        sigma_provenance=sigma_provenance,
        sigma_reference_value=sigma_reference_value,
        refinement_config=refinement_config,
        hkl_metadata=hkl_metadata,
        asu_map=asu_map,
        spot_scale_override=spot_scale_override,
        hkl_source=hkl_source,
        hkl_path=hkl_path,
    )

    assert isinstance(job_ctx, JobContext), "Should return JobContext instance"
    assert job_ctx.cli_args == cli_args
    assert job_ctx.dataload is dataload
    assert job_ctx.calibration_metadata == calibration_metadata
    assert job_ctx.sigma_provenance == sigma_provenance
    assert job_ctx.sigma_reference_value == sigma_reference_value
    assert job_ctx.refinement_config is refinement_config
    assert job_ctx.hkl_metadata == hkl_metadata
    assert np.array_equal(job_ctx.asu_map, asu_map)
    assert job_ctx.spot_scale_override == spot_scale_override
    assert job_ctx.hkl_source == hkl_source
    assert job_ctx.hkl_path == hkl_path


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
