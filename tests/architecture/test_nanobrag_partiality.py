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
    tolerance = 0.05  # 5% tolerance

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

    sim_base = Simulator(
        crystal=crystal_base,
        detector=detector,
        crystal_config=crystal_config_base,
        beam_config=beam_config,
        device=device,
    )

    image_base = sim_base.run()
    intensity_base = image_base.sum().item()

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
    )

    image_scaled = sim_scaled.run()
    intensity_scaled = image_scaled.sum().item()

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
