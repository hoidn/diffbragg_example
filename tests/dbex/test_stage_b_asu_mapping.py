"""
Unit tests for Stage B per-reflection ASU mapping infrastructure (TORCH-REFINE-004 Phase 6).

Tests the compute_hkl_asu_map, initialize_asu_modifiers, and apply_asu_modifiers helper functions
with synthetic space groups to validate:
- P1 space group (no symmetry, all indices unique)
- P432 high-symmetry space group (48-fold reduction)
- Halo voxel handling (map to ASU index 0 with fixed modifier=1.0)
- Friedel pair equivalence ((h,k,l) and (-h,-k,-l) map to same ASU index)

References:
- input.md §Do Now (Phase 6 implementation tasks)
- plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/phase_6_planning_analysis.md §6
- docs/spec-db-workflow.md:59-61 (per-reflection SHALL be default, halo mandatory)
- REFINE-005 (HKL halo mandatory, fixed modifier=1.0)
"""

import numpy as np
import pytest
import torch

from dbex.nanobrag_refinement import (
    apply_asu_modifiers,
    compute_hkl_asu_map,
    initialize_asu_modifiers,
)

# Test fixtures use cctbx to create synthetic space groups
pytest.importorskip("cctbx")
from cctbx import sgtbx
from cctbx.crystal import symmetry


def test_asu_mapping_p1():
    """
    Test ASU mapping for P1 space group (no symmetry, but Friedel pairs fold).

    Expected: Friedel pairs (h,k,l) and (-h,-k,-l) map to same ASU index.
              n_asu_unique ≈ n_voxels / 2 (accounting for Friedel folding).
    """
    # Create synthetic P1 space group (no symmetry)
    sgi = sgtbx.space_group_info('P1')
    unit_cell = (50, 60, 70, 90, 90, 90)  # Orthogonal cell
    symm = symmetry(unit_cell=unit_cell, space_group_info=sgi)

    # Small HKL grid (5x5x5 = 125 voxels)
    h_coords = np.arange(-2, 3, dtype=np.int32)  # -2, -1, 0, 1, 2
    k_coords = np.arange(-2, 3, dtype=np.int32)
    l_coords = np.arange(-2, 3, dtype=np.int32)

    h_grid, k_grid, l_grid = np.meshgrid(h_coords, k_coords, l_coords, indexing='ij')
    hkl_grid = np.stack([h_grid, k_grid, l_grid], axis=-1)  # (5, 5, 5, 3)

    # Compute ASU mapping (no halo mask)
    hkl_asu_map, n_asu_unique = compute_hkl_asu_map(hkl_grid, symm, halo_mask=None)

    # P1 with anomalous_flag=False: Friedel pairs fold
    # 125 voxels → ~63 unique ASU (half + origin)
    n_voxels = 5 * 5 * 5
    # Origin (0,0,0) is unique, others pair: expected = (n_voxels + 1) / 2 ≈ 63
    expected_n_asu = (n_voxels + 1) // 2
    assert abs(n_asu_unique - expected_n_asu) <= 2, \
        f"P1: Expected ~{expected_n_asu} unique ASU (Friedel folding), got {n_asu_unique}"

    # Check hkl_asu_map shape
    assert hkl_asu_map.shape == (5, 5, 5), f"Expected shape (5,5,5), got {hkl_asu_map.shape}"

    # Check all indices are in valid range [0, n_asu_unique-1]
    unique_indices = torch.unique(hkl_asu_map)
    assert len(unique_indices) == n_asu_unique, f"Expected {n_asu_unique} unique indices, got {len(unique_indices)}"
    assert torch.all(unique_indices >= 0) and torch.all(unique_indices < n_asu_unique), \
        f"ASU indices should be in range [0, {n_asu_unique-1}]"


def test_asu_mapping_p432():
    """
    Test ASU mapping for P432 space group (48-fold symmetry).

    Expected: n_asu_unique ≈ n_voxels / 48 (high symmetry reduction).
    """
    # Create synthetic P432 space group (48-fold symmetry)
    sgi = sgtbx.space_group_info('P432')
    unit_cell = (100, 100, 100, 90, 90, 90)  # Cubic cell (required for P432)
    symm = symmetry(unit_cell=unit_cell, space_group_info=sgi)

    # Medium HKL grid (11x11x11 = 1331 voxels)
    h_coords = np.arange(-5, 6, dtype=np.int32)  # -5..5
    k_coords = np.arange(-5, 6, dtype=np.int32)
    l_coords = np.arange(-5, 6, dtype=np.int32)

    h_grid, k_grid, l_grid = np.meshgrid(h_coords, k_coords, l_coords, indexing='ij')
    hkl_grid = np.stack([h_grid, k_grid, l_grid], axis=-1)  # (11, 11, 11, 3)

    # Compute ASU mapping (no halo mask)
    hkl_asu_map, n_asu_unique = compute_hkl_asu_map(hkl_grid, symm, halo_mask=None)

    # P432: Expect ~1/48 of voxels to be unique due to high symmetry
    n_voxels = 11 * 11 * 11
    expected_ratio = 1.0 / 48.0
    # Allow 2.1× tolerance for edge effects and systematic absences
    assert n_asu_unique < n_voxels * expected_ratio * 2.1, \
        f"P432: Expected n_asu < {int(n_voxels * expected_ratio * 2.1)}, got {n_asu_unique}"
    assert n_asu_unique > n_voxels * expected_ratio * 0.5, \
        f"P432: Expected n_asu > {int(n_voxels * expected_ratio * 0.5)}, got {n_asu_unique}"

    # Verify symmetry folding: multiple voxels should map to same ASU index
    unique_indices = torch.unique(hkl_asu_map)
    assert len(unique_indices) == n_asu_unique, \
        f"Expected {n_asu_unique} unique indices, got {len(unique_indices)}"

    # Check that at least some voxels share ASU indices (symmetry folding)
    # Count how many voxels map to the most common ASU index
    max_count = torch.bincount(hkl_asu_map.flatten()).max().item()
    assert max_count > 1, "P432: Expected some ASU indices to have multiple voxels (symmetry folding)"


def test_asu_halo_handling():
    """
    Test halo voxel handling: halo voxels map to ASU index 0 with fixed modifier=1.0.

    Expected:
    - Halo voxels (halo_mask=True) map to ASU index 0
    - Non-halo voxels map to indices 1..n_asu_unique-1
    - modifiers[0].requires_grad == False (halo modifier fixed)
    """
    # Create synthetic P1 space group
    sgi = sgtbx.space_group_info('P1')
    unit_cell = (50, 60, 70, 90, 90, 90)
    symm = symmetry(unit_cell=unit_cell, space_group_info=sgi)

    # Small HKL grid (5x5x5)
    h_coords = np.arange(-2, 3, dtype=np.int32)
    k_coords = np.arange(-2, 3, dtype=np.int32)
    l_coords = np.arange(-2, 3, dtype=np.int32)

    h_grid, k_grid, l_grid = np.meshgrid(h_coords, k_coords, l_coords, indexing='ij')
    hkl_grid = np.stack([h_grid, k_grid, l_grid], axis=-1)  # (5, 5, 5, 3)

    # Create halo mask: mark outer shell as halo (True)
    halo_mask = np.zeros((5, 5, 5), dtype=bool)
    halo_mask[0, :, :] = True  # h=-2 is halo
    halo_mask[-1, :, :] = True  # h=2 is halo
    halo_mask[:, 0, :] = True  # k=-2 is halo
    halo_mask[:, -1, :] = True  # k=2 is halo
    halo_mask[:, :, 0] = True  # l=-2 is halo
    halo_mask[:, :, -1] = True  # l=2 is halo

    n_halo = np.sum(halo_mask)

    # Compute ASU mapping WITH halo mask
    hkl_asu_map, n_asu_unique = compute_hkl_asu_map(hkl_grid, symm, halo_mask=halo_mask)

    # Check that halo voxels map to index 0
    halo_indices = hkl_asu_map[halo_mask]
    assert torch.all(halo_indices == 0), "Halo voxels should map to ASU index 0"

    # Check that non-halo voxels map to indices ≥ 1
    non_halo_indices = hkl_asu_map[~halo_mask]
    assert torch.all(non_halo_indices >= 1), "Non-halo voxels should map to ASU indices ≥ 1"

    # Check n_asu_unique is reasonable (just a sanity check)
    # Core test: halo voxels map to 0, non-halo to ≥1 (already validated above)
    n_voxels = 5 * 5 * 5
    assert 1 < n_asu_unique < n_voxels, \
        f"Expected 1 < n_asu < {n_voxels}, got {n_asu_unique}"

    # Initialize modifiers and check halo gradient handling
    device = torch.device('cpu')
    log_modifiers = initialize_asu_modifiers(n_asu_unique, device, dtype=torch.float32)

    # Check that log_modifiers[0] gradients are zeroed via hook
    assert log_modifiers.requires_grad is True, "log_modifiers should have requires_grad=True"

    # Simulate backward pass to test gradient hook
    # Create a simple loss that would normally give gradient=1.0 for all elements
    loss = log_modifiers.sum()
    loss.backward()

    # Check that gradient for index 0 (halo) was zeroed by hook
    assert log_modifiers.grad[0].item() == 0.0, \
        "Gradient for halo modifier (index 0) should be zeroed by hook"

    # Check that other indices have non-zero gradients (should be 1.0 from sum())
    assert torch.all(log_modifiers.grad[1:] == 1.0), \
        "Non-halo modifiers should have gradient=1.0 from sum()"


def test_asu_friedel_pairs():
    """
    Test Friedel pair equivalence: (h,k,l) and (-h,-k,-l) map to same ASU index.

    Expected: anomalous_flag=False means Friedel pairs map to same ASU index.
    """
    # Create synthetic P21 space group (2-fold symmetry)
    sgi = sgtbx.space_group_info('P21')
    unit_cell = (50, 60, 70, 90, 110, 90)  # Monoclinic cell
    symm = symmetry(unit_cell=unit_cell, space_group_info=sgi)

    # Create HKL grid with Friedel pairs
    # Pairs: (1,2,3) and (-1,-2,-3), (2,1,3) and (-2,-1,-3)
    hkl_indices = np.array([
        [1, 2, 3],
        [-1, -2, -3],  # Friedel pair of (1,2,3)
        [2, 1, 3],
        [-2, -1, -3],  # Friedel pair of (2,1,3)
        [0, 0, 1],
        [0, 0, -1],  # Friedel pair of (0,0,1)
    ], dtype=np.int32)

    # Reshape to (6,1,1,3) to match expected shape
    hkl_grid = hkl_indices.reshape(6, 1, 1, 3)

    # Compute ASU mapping (no halo mask, anomalous_flag=False)
    hkl_asu_map, n_asu_unique = compute_hkl_asu_map(hkl_grid, symm, halo_mask=None)

    # Extract ASU indices for each reflection
    asu_indices = hkl_asu_map.flatten()

    # Check Friedel pair equivalence
    assert asu_indices[0] == asu_indices[1], \
        f"Friedel pairs (1,2,3) and (-1,-2,-3) should map to same ASU index, got {asu_indices[0]} vs {asu_indices[1]}"
    assert asu_indices[2] == asu_indices[3], \
        f"Friedel pairs (2,1,3) and (-2,-1,-3) should map to same ASU index, got {asu_indices[2]} vs {asu_indices[3]}"
    assert asu_indices[4] == asu_indices[5], \
        f"Friedel pairs (0,0,1) and (0,0,-1) should map to same ASU index, got {asu_indices[4]} vs {asu_indices[5]}"

    # Check that n_asu_unique accounts for Friedel folding
    # 6 reflections → ~3 unique ASU indices (accounting for Friedel + P21 symmetry)
    assert n_asu_unique <= 4, f"Expected ≤4 unique ASU indices (Friedel + P21 symmetry), got {n_asu_unique}"


def test_apply_asu_modifiers():
    """
    Test apply_asu_modifiers: modifiers are correctly broadcast and applied to HKL grid.

    Expected:
    - modifiers = exp(log_modifiers) applied element-wise to hkl_grid_base
    - Clamping enforced on log_modifiers
    """
    # Create synthetic HKL ASU map and modifiers
    device = torch.device('cpu')
    dtype = torch.float32

    # Small HKL grid (3x3x3)
    hkl_grid_base = torch.ones((3, 3, 3), dtype=dtype, device=device) * 100.0  # All voxels = 100

    # ASU map: 3x3x3 grid maps to 3 unique ASU indices
    hkl_asu_map = torch.tensor([
        [[0, 0, 0], [1, 1, 1], [2, 2, 2]],
        [[0, 0, 0], [1, 1, 1], [2, 2, 2]],
        [[0, 0, 0], [1, 1, 1], [2, 2, 2]],
    ], dtype=torch.int64, device=device)

    n_asu_unique = 3

    # Initialize log_modifiers: [0, log(2), log(0.5)] → modifiers = [1.0, 2.0, 0.5]
    log_modifiers = torch.tensor([0.0, np.log(2.0), np.log(0.5)], dtype=dtype, device=device)
    log_modifiers = torch.nn.Parameter(log_modifiers, requires_grad=True)

    # Apply modifiers
    hkl_grid_modified = apply_asu_modifiers(
        hkl_grid_base, log_modifiers, hkl_asu_map, modifier_clamp=(-3.0, 3.0)
    )

    # Check modified values
    # ASU index 0: modifier=1.0 → 100 * 1.0 = 100
    # ASU index 1: modifier=2.0 → 100 * 2.0 = 200
    # ASU index 2: modifier=0.5 → 100 * 0.5 = 50
    assert torch.allclose(hkl_grid_modified[0, 0, 0], torch.tensor(100.0)), \
        f"Expected 100, got {hkl_grid_modified[0, 0, 0].item()}"
    assert torch.allclose(hkl_grid_modified[0, 1, 0], torch.tensor(200.0)), \
        f"Expected 200, got {hkl_grid_modified[0, 1, 0].item()}"
    assert torch.allclose(hkl_grid_modified[0, 2, 0], torch.tensor(50.0)), \
        f"Expected 50, got {hkl_grid_modified[0, 2, 0].item()}"

    # Test clamping: extreme log_modifiers should be clamped
    log_modifiers_extreme = torch.tensor([0.0, 5.0, -5.0], dtype=dtype, device=device)  # Outside [-3, 3]
    log_modifiers_extreme = torch.nn.Parameter(log_modifiers_extreme, requires_grad=True)

    hkl_grid_clamped = apply_asu_modifiers(
        hkl_grid_base, log_modifiers_extreme, hkl_asu_map, modifier_clamp=(-3.0, 3.0)
    )

    # Clamped: log(5.0) → 3.0 → exp(3.0) ≈ 20.1
    # Clamped: log(-5.0) → -3.0 → exp(-3.0) ≈ 0.05
    assert hkl_grid_clamped[0, 1, 0] < 100 * 25, "Extreme positive log_modifier should be clamped"
    assert hkl_grid_clamped[0, 2, 0] > 100 * 0.04, "Extreme negative log_modifier should be clamped"
