"""
Enforcement tests for nanoBragg partiality (lattice weight) contract.

ARCH-SIM-CONSTRUCTION-001: Simulator Construction Convention Alignment
SIM-CONSTR-PARTIALITY-001: SQUARE lattice must emit weights ∝ (Na·Nb·Nc)²

This test enforces the contract from docs/spec-db-core.md:60-140 that the
SQUARE lattice shape must produce lattice weights proportional to (Na·Nb·Nc)²
when evaluated in sufficient precision.
"""

import os
import pytest
import torch

# Set environment variable before importing torch-dependent modules
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# Import nanobrag_torch simulator components
from nanobrag_torch.simulator import Simulator
from nanobrag_torch.config import BeamConfig, CrystalConfig, CrystalShape, DetectorConfig
from nanobrag_torch.models.crystal import Crystal
from nanobrag_torch.models.detector import Detector


@pytest.mark.parametrize("device", ["cpu", "cuda"] if torch.cuda.is_available() else ["cpu"])
def test_square_lattice_applies_ncells(device):
    """
    Test that SQUARE lattice applies (Na·Nb·Nc)² scaling as specified.

    ARCH-CONTRACT: docs/spec-db-core.md:60-140
    Owner: nanobrag_torch.simulator.compute_physics_for_position (SQUARE branch)
    Contract: lattice weights must be proportional to (Na·Nb·Nc)²

    This test:
    1. Runs the simulator with N_cells=(1,1,1) to get base intensity I₁
    2. Runs with N_cells=(Na,Nb,Nc) to get scaled intensity I₂
    3. Verifies that I₂/I₁ ≈ (Na·Nb·Nc)² within 5% tolerance

    The fix in SIM-CONSTR-PARTIALITY-001 ensures fractional HKL deltas are
    computed in float64 before sincg evaluation, preventing underflow.
    """
    # Test parameters
    Na, Nb, Nc = 41, 29, 32
    expected_ratio = (Na * Nb * Nc) ** 2
    # ARCH-SIM-CONSTRUCTION-001 C.35: Tightened tolerance after normalization fix
    tolerance = 0.01  # 1% tolerance (was 5% before fix)

    # Create configs
    detector_config = DetectorConfig(
        distance_mm=100.0,
        pixel_size_mm=0.1,
        spixels=10,
        fpixels=10,
    )

    beam_config = BeamConfig()  # Use defaults (wavelength_A=1.0)

    # Run 1: N_cells=(1,1,1)
    crystal_config_base = CrystalConfig(
        default_F=100.0,  # Constant structure factor
        N_cells=(1, 1, 1),
        shape=CrystalShape.SQUARE,
    )

    crystal_base = Crystal(crystal_config_base, device=device)
    detector = Detector(detector_config, device=device)

    # ARCH-SIM-CONSTRUCTION-001 C.35: Enable partiality stats to capture steps_scalar
    debug_config = {'collect_partiality_stats': True}

    sim_base = Simulator(
        crystal=crystal_base,
        detector=detector,
        crystal_config=crystal_config_base,
        beam_config=beam_config,
        device=device,
        debug_config=debug_config,
    )

    image_base = sim_base.run()
    intensity_base = image_base.sum().item()

    # Extract steps_scalar from partiality stats
    stats_base = sim_base.partiality_stats
    assert stats_base is not None, "Partiality stats should be available"
    steps_scalar_base = stats_base.get('steps_scalar', None)
    assert steps_scalar_base is not None, "steps_scalar must be emitted when collect_partiality_stats=True"

    # Run 2: N_cells=(Na, Nb, Nc)
    crystal_config_scaled = CrystalConfig(
        default_F=100.0,  # Same structure factor
        N_cells=(Na, Nb, Nc),
        shape=CrystalShape.SQUARE,
    )

    crystal_scaled = Crystal(crystal_config_scaled, device=device)

    sim_scaled = Simulator(
        crystal=crystal_scaled,
        detector=detector,
        crystal_config=crystal_config_scaled,
        beam_config=beam_config,
        device=device,
        debug_config=debug_config,
    )

    image_scaled = sim_scaled.run()
    intensity_scaled = image_scaled.sum().item()

    # Extract steps_scalar from partiality stats
    stats_scaled = sim_scaled.partiality_stats
    assert stats_scaled is not None, "Partiality stats should be available"
    steps_scalar_scaled = stats_scaled.get('steps_scalar', None)
    assert steps_scalar_scaled is not None, "steps_scalar must be emitted when collect_partiality_stats=True"

    # ARCH-SIM-CONSTRUCTION-001 C.35: Assert SQUARE lattice normalization excludes oversample²
    # For SQUARE shape, steps_scalar should be sources·phi_steps·mosaic_domains (no oversample²)
    # Default config: sources=1, phi_steps=1, mosaic_domains=1 → steps_scalar should be 1
    expected_steps_scalar_square = 1  # No oversample² for SQUARE
    assert steps_scalar_base == expected_steps_scalar_square, (
        f"SQUARE lattice must use integral normalization: "
        f"expected steps_scalar={expected_steps_scalar_square}, "
        f"observed={steps_scalar_base} (should not include oversample²)"
    )
    assert steps_scalar_scaled == expected_steps_scalar_square, (
        f"SQUARE lattice must use integral normalization: "
        f"expected steps_scalar={expected_steps_scalar_square}, "
        f"observed={steps_scalar_scaled} (should not include oversample²)"
    )

    # Verify ratio
    observed_ratio = intensity_scaled / intensity_base if intensity_base > 0 else 0.0
    relative_error = abs(observed_ratio - expected_ratio) / expected_ratio

    # Assertions
    assert intensity_base > 0, "Base intensity (N_cells=1) must be non-zero"
    assert intensity_scaled > 0, "Scaled intensity must be non-zero"

    assert relative_error < tolerance, (
        f"Lattice weight scaling violation: "
        f"expected ratio={(Na*Nb*Nc)**2:.1f}, "
        f"observed={observed_ratio:.1f}, "
        f"relative_error={relative_error:.2%} (tolerance={tolerance:.0%})"
    )

    # Additional diagnostic: ensure the ratio is in the right ballpark
    # (not off by orders of magnitude due to a completely broken implementation)
    assert 0.8 * expected_ratio < observed_ratio < 1.2 * expected_ratio, (
        f"Ratio far outside expected range: {observed_ratio:.1f} vs {expected_ratio:.1f}"
    )


if __name__ == "__main__":
    # Allow running test standalone for debugging
    pytest.main([__file__, "-v"])
