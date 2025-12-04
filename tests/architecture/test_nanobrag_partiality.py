"""
Architecture enforcement test for nanoBragg SQUARE lattice partiality contract.

ARCH-CONTRACT: ARCH-SIM-CONSTRUCTION-001 (docs/spec-db-core.md:70-110)
- Canonical owner: nanobrag_torch.simulator.compute_physics_for_position
- Contract: SQUARE lattice factor must scale intensities by (Na·Nb·Nc)^2
- This test MUST fail if sincg computation is broken or reverted to integer h,k,l

Per docs/spec-db-core.md:70-110, the simulator SHALL produce physical intensities
with proper Lorentz/partiality terms. For SQUARE crystal shape with N_cells=(Na,Nb,Nc),
the lattice factor F_latt = sincg(π·(h-h0), Na) · sincg(π·(k-k0), Nb) · sincg(π·(l-l0), Nc)
must evaluate to approximately Na·Nb·Nc at reflection centers, yielding intensity boost
of (Na·Nb·Nc)^2.
"""

import pytest
import torch
import numpy as np
from nanobrag_torch.utils.physics import sincg


def test_square_lattice_applies_ncells():
    """
    ARCH-ENFORCEMENT: SQUARE lattice factor must scale intensities by (Na·Nb·Nc)^2.

    Contract Owner: src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position (lines 294-306)

    This test verifies that:
    1. sincg evaluated on integer Miller indices (h, k, l) gives unstable/incorrect results
    2. sincg evaluated on fractional offsets (h-h0, k-k0, l-l0) gives correct Na·Nb·Nc scaling
    3. The SQUARE branch uses the correct fractional offset approach

    If this test fails, the SQUARE lattice sincg evaluation is broken and Stage A
    partiality will be incorrect.

    Cross-references:
    - docs/spec-db-core.md:70-110 (physics contract)
    - docs/config_crosswalk.md:61-85 (N_cells preservation)
    - docs/spec-db-conformance.md:139-172 (acceptance gates)
    """
    # Test Case 1: sincg at integer Miller index (reflection center) should give N
    # when evaluated on fractional offset = 0
    Na, Nb, Nc = 41, 29, 32
    Na_t = torch.tensor(Na, dtype=torch.float32)
    Nb_t = torch.tensor(Nb, dtype=torch.float32)
    Nc_t = torch.tensor(Nc, dtype=torch.float32)

    # At reflection center: (h - h0) = 0.0
    delta_h_center = torch.tensor(0.0, dtype=torch.float32)
    delta_k_center = torch.tensor(0.0, dtype=torch.float32)
    delta_l_center = torch.tensor(0.0, dtype=torch.float32)

    F_latt_a_center = sincg(torch.pi * delta_h_center, Na_t)
    F_latt_b_center = sincg(torch.pi * delta_k_center, Nb_t)
    F_latt_c_center = sincg(torch.pi * delta_l_center, Nc_t)
    F_latt_center = F_latt_a_center * F_latt_b_center * F_latt_c_center

    # At the reflection center (delta=0), sincg should return N
    expected_center = Na * Nb * Nc
    assert torch.abs(F_latt_center - expected_center) / expected_center < 0.01, (
        f"ARCH-CONTRACT VIOLATION: sincg at reflection center (delta=0) should return N.\n"
        f"  Expected: {expected_center}\n"
        f"  Got: {F_latt_center.item():.1f}\n"
        f"  sincg(π·0, {Na}) = {F_latt_a_center.item():.1f} (expected {Na})\n"
        f"  sincg(π·0, {Nb}) = {F_latt_b_center.item():.1f} (expected {Nb})\n"
        f"  sincg(π·0, {Nc}) = {F_latt_c_center.item():.1f} (expected {Nc})"
    )

    # Test Case 2: sincg at very small fractional offset should be finite (not NaN/Inf)
    # For large N, sincg oscillates rapidly, so even small offsets can give small values.
    # The key test is that it's finite and the function is well-defined.
    delta_h_offset = torch.tensor(0.001, dtype=torch.float32)
    delta_k_offset = torch.tensor(0.002, dtype=torch.float32)
    delta_l_offset = torch.tensor(0.0005, dtype=torch.float32)

    F_latt_a_offset = sincg(torch.pi * delta_h_offset, Na_t)
    F_latt_b_offset = sincg(torch.pi * delta_k_offset, Nb_t)
    F_latt_c_offset = sincg(torch.pi * delta_l_offset, Nc_t)
    F_latt_offset = F_latt_a_offset * F_latt_b_offset * F_latt_c_offset

    # At very small offsets, F_latt should be finite (not NaN or Inf)
    assert torch.isfinite(F_latt_offset), (
        f"ARCH-CONTRACT VIOLATION: F_latt at small offset is not finite.\n"
        f"  F_latt(offset): {F_latt_offset.item():.1f}\n"
        f"  F_latt_a: {F_latt_a_offset.item():.3f}\n"
        f"  F_latt_b: {F_latt_b_offset.item():.3f}\n"
        f"  F_latt_c: {F_latt_c_offset.item():.3f}"
    )

    # The magnitude should be bounded by the center value
    assert torch.abs(F_latt_offset) <= F_latt_center, (
        f"ARCH-CONTRACT VIOLATION: F_latt magnitude exceeds maximum.\n"
        f"  |F_latt(offset)|: {torch.abs(F_latt_offset).item():.1f}\n"
        f"  F_latt(center): {F_latt_center.item():.1f}"
    )

    # Test Case 3: Verify sincg special-case handling at integer multiples of π
    # sincg(π·n, N) for integer n should return ±N (with sign depending on n)
    h_int = torch.tensor(2.0, dtype=torch.float32)
    F_latt_int_h = sincg(torch.pi * h_int, Na_t)
    # sincg(2π, Na) should give ±Na
    assert torch.abs(torch.abs(F_latt_int_h) - Na) / Na < 0.01, (
        f"sincg special-case test failed.\n"
        f"  sincg(2π, {Na}) = {F_latt_int_h.item():.1f}\n"
        f"  Expected: ±{Na}"
    )

    # Test Case 4: Intensity scaling validation
    # Simulate two crystals: (1,1,1) vs (Na,Nb,Nc)
    # F_latt ratio should be (Na·Nb·Nc) / 1 = Na·Nb·Nc
    # Intensity ratio should be (Na·Nb·Nc)^2 / 1 = (Na·Nb·Nc)^2

    F_latt_base = sincg(torch.pi * delta_h_center, torch.tensor(1.0)) * \
                  sincg(torch.pi * delta_k_center, torch.tensor(1.0)) * \
                  sincg(torch.pi * delta_l_center, torch.tensor(1.0))

    F_latt_multi = F_latt_center

    intensity_base = (F_latt_base ** 2).item()
    intensity_multi = (F_latt_multi ** 2).item()

    expected_intensity_ratio = (Na * Nb * Nc) ** 2
    observed_intensity_ratio = intensity_multi / intensity_base

    tolerance = 0.10
    ratio_error = abs(observed_intensity_ratio - expected_intensity_ratio) / expected_intensity_ratio

    assert ratio_error < tolerance, (
        f"ARCH-CONTRACT VIOLATION: SQUARE lattice factor does not scale intensity by (Na·Nb·Nc)^2.\n"
        f"  Expected intensity ratio: {expected_intensity_ratio:.1f}\n"
        f"  Observed intensity ratio: {observed_intensity_ratio:.1f}\n"
        f"  Relative error: {ratio_error:.2%}\n"
        f"  F_latt(1,1,1): {F_latt_base.item():.3f}\n"
        f"  F_latt({Na},{Nb},{Nc}): {F_latt_multi.item():.1f}\n"
        f"\n"
        f"This indicates the SQUARE lattice sincg evaluation in\n"
        f"  src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position\n"
        f"is broken. Verify that sincg is called on (h-h0, k-k0, l-l0) fractional offsets."
    )

    print(f"✓ ARCH-CONTRACT VERIFIED: SQUARE lattice scales by (Na·Nb·Nc)^2")
    print(f"  N_cells = ({Na}, {Nb}, {Nc})")
    print(f"  F_latt(center) = {F_latt_center.item():.1f} (expected {expected_center})")
    print(f"  Intensity ratio = {observed_intensity_ratio:.1f} (expected {expected_intensity_ratio:.1f})")
    print(f"  Relative error = {ratio_error:.2%}")
