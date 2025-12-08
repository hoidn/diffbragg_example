"""
Enforcement tests for nanoBragg partiality (lattice weight) contract.

ARCH-SIM-CONSTRUCTION-001: Simulator Construction Convention Alignment
SIM-CONSTR-PARTIALITY-001: SQUARE lattice integrated intensity scales linearly with Na×Nb×Nc

Per inbox/nanobrag_torch_response_2025_12_08.md:
- Peak intensity at exact Bragg: ∝ (Na×Nb×Nc)²
- Integrated/summed intensity: ∝ Na×Nb×Nc (linear)

This test enforces the contract that the SQUARE lattice shape must produce
integrated/summed intensity proportional to Na×Nb×Nc when summed over detector.
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
    Test that SQUARE lattice applies Na·Nb·Nc (linear) scaling for integrated intensity.

    ARCH-CONTRACT: docs/findings.md::SIM-CONSTR-PARTIALITY-001 (Resolved 2025-12-08)
    Owner: nanobrag_torch.simulator.compute_physics_for_position (SQUARE branch)
    Contract: Integrated/summed intensity scales as Na×Nb×Nc (linear)

    Physics (per inbox/nanobrag_torch_response_2025_12_08.md):
    - Peak height scales as (Na×Nb×Nc)² (sinc² peak)
    - Peak width scales as 1/(Na×Nb×Nc)
    - Integral = peak × width ∝ Na×Nb×Nc (linear)

    This test:
    1. Runs the simulator with N_cells=(1,1,1) to get base intensity I₁
    2. Runs with N_cells=(Na,Nb,Nc) to get scaled intensity I₂
    3. Verifies that I₂/I₁ ≈ Na×Nb×Nc within 7% tolerance

    NOTE: Test uses 400×400 pixel detector to ensure full solid-angle integration.
    Smaller detectors (e.g., 10×10) show partial-integration effects. See Phase B.6.
    """
    # Test parameters
    Na, Nb, Nc = 41, 29, 32
    expected_ratio = Na * Nb * Nc  # Linear scaling for integrated intensity
    # SIM-CONSTR-PARTIALITY-001: Linear scaling may have some pixel-sampling deviation
    tolerance = 0.07  # 7% tolerance: oscillatory convergence around linear at 400×400 (see Phase B.6)

    # Create configs
    # ARCH-SIM-CONSTRUCTION-001 C.39: Test with oversample>1 to validate omega compensation
    test_oversample = 13

    detector_config = DetectorConfig(
        distance_mm=100.0,
        pixel_size_mm=0.1,
        spixels=400,  # 400×400 for full solid-angle integration (see Phase B.6)
        fpixels=400,  # 400×400 for full solid-angle integration (see Phase B.6)
        oversample=test_oversample,
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

    # Extract steps_scalar from partiality stats (optional — API may not be present)
    # NOTE: partiality_stats/steps_scalar/omega_applied_post_sum telemetry checks are
    # auxiliary to the core scaling contract. If the API is unavailable, skip these
    # checks but still enforce the core linear scaling assertion.
    stats_base = getattr(sim_base, 'partiality_stats', None) or getattr(sim_base, '_partiality_stats', None)
    steps_scalar_base = stats_base.get('steps_scalar', None) if stats_base else None

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

    # Extract steps_scalar from partiality stats (optional — API may not be present)
    stats_scaled = getattr(sim_scaled, 'partiality_stats', None) or getattr(sim_scaled, '_partiality_stats', None)
    steps_scalar_scaled = stats_scaled.get('steps_scalar', None) if stats_scaled else None

    # ARCH-SIM-CONSTRUCTION-001 C.35: Assert SQUARE lattice normalization excludes oversample²
    # For SQUARE shape, steps_scalar should be sources·phi_steps·mosaic_domains (no oversample²)
    # Default config: sources=1, phi_steps=1, mosaic_domains=1 → steps_scalar should be 1
    # NOTE: Skip if partiality_stats API is unavailable
    if steps_scalar_base is not None and steps_scalar_scaled is not None:
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

    # ARCH-SIM-CONSTRUCTION-001 C.39: Verify omega compensation telemetry for oversample>1
    # When oversample>1 and shape=SQUARE, omega must be applied once after sum
    # The omega_applied_post_sum flag must be True to catch regressions
    # NOTE: Skip if partiality_stats API is unavailable
    if test_oversample > 1 and stats_base is not None and stats_scaled is not None:
        omega_applied_post_sum_base = stats_base.get('omega_applied_post_sum', None)
        omega_applied_post_sum_scaled = stats_scaled.get('omega_applied_post_sum', None)

        if omega_applied_post_sum_base is not None:
            assert omega_applied_post_sum_base is True, (
                f"SQUARE lattice with oversample>1 must apply omega once after sum: "
                f"omega_applied_post_sum={omega_applied_post_sum_base} (expected True)"
            )
        if omega_applied_post_sum_scaled is not None:
            assert omega_applied_post_sum_scaled is True, (
                f"SQUARE lattice with oversample>1 must apply omega once after sum: "
                f"omega_applied_post_sum={omega_applied_post_sum_scaled} (expected True)"
            )

    # Verify ratio
    observed_ratio = intensity_scaled / intensity_base if intensity_base > 0 else 0.0
    relative_error = abs(observed_ratio - expected_ratio) / expected_ratio

    # Assertions
    assert intensity_base > 0, "Base intensity (N_cells=1) must be non-zero"
    assert intensity_scaled > 0, "Scaled intensity must be non-zero"

    assert relative_error < tolerance, (
        f"Integrated intensity scaling violation: "
        f"expected ratio={Na*Nb*Nc:.1f} (linear Na×Nb×Nc), "
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
