"""
ASU Index Computation Pseudocode for Phase 6 Per-Reflection Mode

This is NOT production code. It is a planning artifact to document the ASU mapping
algorithm design before implementation.

Design: Map HKL grid voxels to unique ASU indices using cctbx symmetry operations.
"""

import torch
import numpy as np
from cctbx import miller
from cctbx.array_family import flex


def compute_hkl_asu_map(
    hkl_grid: np.ndarray,
    crystal_symmetry,  # cctbx.crystal.symmetry object from MTZ
    halo_mask: np.ndarray = None
) -> tuple[torch.Tensor, int]:
    """
    Map each HKL grid voxel to its unique ASU index.

    Args:
        hkl_grid: shape (h_count, k_count, l_count, 3) — Miller indices for each voxel
                  (includes ±1 halo per spec-db-workflow.md:61)
        crystal_symmetry: cctbx.crystal.symmetry object with space group + unit cell
                          (extracted from MTZ via F.crystal_symmetry())
        halo_mask: Optional boolean mask shape (h_count, k_count, l_count) marking
                   halo voxels (True=halo, outside MTZ range). If provided, halo
                   voxels map to ASU index 0 with fixed modifier=1.0.

    Returns:
        hkl_asu_map: torch.Tensor[int64] shape (h_count, k_count, l_count)
                     Values are ASU indices 0..n_asu_unique-1
                     Index 0 is reserved for halo voxels (if halo_mask provided)
        n_asu_unique: Total count of unique ASU reflections (including index 0 for halo)

    Edge Cases:
        - Halo voxels: Map to index 0, which will have fixed modifier=1.0 (non-trainable)
        - Systematic absences: cctbx.miller.set handles these automatically
        - Friedel pairs: Anomalous flag controls whether (+h,+k,+l) and (-h,-k,-l)
                         map to same ASU index
    """
    h_count, k_count, l_count, _ = hkl_grid.shape

    # Step 1: Flatten HKL grid to 1D list of Miller indices
    miller_indices = hkl_grid[..., :3].reshape(-1, 3)  # (n_voxels, 3)

    # Step 2: Convert to cctbx flex array (required by cctbx.miller API)
    miller_indices_flex = flex.miller_index(
        [(int(h), int(k), int(l)) for h, k, l in miller_indices]
    )

    # Step 3: Create cctbx.miller.set from indices + crystal symmetry
    # anomalous_flag=False means Friedel pairs (+h,k,l) and (-h,-k,-l) map to same ASU
    miller_set = miller.set(
        crystal_symmetry=crystal_symmetry,
        indices=miller_indices_flex,
        anomalous_flag=False
    )

    # Step 4: Map to ASU using cctbx symmetry operations
    # This applies space group symmetry and returns equivalent reflections in ASU
    asu_miller_set = miller_set.map_to_asu()
    asu_indices_flex = asu_miller_set.indices()

    # Step 5: Assign unique integer index to each ASU reflection
    # Convert flex array back to numpy for np.unique
    asu_indices_np = np.array(
        [(h, k, l) for h, k, l in asu_indices_flex],
        dtype=np.int32
    )

    # Find unique ASU reflections and inverse mapping
    # unique_asu: (n_unique, 3) array of unique ASU Miller indices
    # inverse_map: (n_voxels,) array mapping each voxel to its unique ASU index
    unique_asu, inverse_map = np.unique(
        asu_indices_np,
        return_inverse=True,
        axis=0
    )

    # Step 6: Handle halo voxels (if mask provided)
    if halo_mask is not None:
        halo_flat = halo_mask.reshape(-1)  # (n_voxels,)

        # Shift all ASU indices up by 1 to reserve index 0 for halo
        inverse_map = inverse_map + 1

        # Set halo voxels to index 0
        inverse_map[halo_flat] = 0

        n_asu_unique = len(unique_asu) + 1  # +1 for halo index 0
    else:
        n_asu_unique = len(unique_asu)

    # Step 7: Reshape inverse_map back to (h_count, k_count, l_count)
    hkl_asu_map = torch.tensor(inverse_map, dtype=torch.int64).reshape(
        h_count, k_count, l_count
    )

    return hkl_asu_map, n_asu_unique


def initialize_asu_modifiers(n_asu_unique: int, device: torch.device) -> torch.nn.Parameter:
    """
    Initialize per-reflection ASU modifiers as trainable parameters.

    Args:
        n_asu_unique: Total count of unique ASU reflections (from compute_hkl_asu_map)
        device: torch device (cpu or cuda)

    Returns:
        asu_modifiers: nn.Parameter shape (n_asu_unique,) initialized near 1.0
                       Index 0 (halo) will be fixed at 1.0 (non-trainable)

    Parameterization:
        - Use log-space: modifiers = exp(log_modifiers) to enforce positivity
        - Initialize log_modifiers ≈ 0 so modifiers start near 1.0
        - Clamp log_modifiers to [-3, 3] → modifiers in [0.05, 20.1] range
    """
    # Initialize log-space parameters near 0 (modifiers ≈ 1.0)
    log_modifiers = torch.zeros(n_asu_unique, dtype=torch.float32, device=device)

    # Add small random noise for symmetry breaking
    log_modifiers += torch.randn_like(log_modifiers) * 0.01

    # Fix index 0 (halo) at log(1.0) = 0 permanently
    log_modifiers[0] = 0.0

    return torch.nn.Parameter(log_modifiers, requires_grad=True)


def apply_asu_modifiers(
    hkl_grid_base: torch.Tensor,
    hkl_asu_map: torch.Tensor,
    log_modifiers: torch.nn.Parameter,
    modifier_clamp: tuple[float, float] = (-3.0, 3.0)
) -> torch.Tensor:
    """
    Apply per-reflection ASU modifiers to HKL grid structure factors.

    Args:
        hkl_grid_base: Base structure factor grid shape (h_count, k_count, l_count)
        hkl_asu_map: ASU index map shape (h_count, k_count, l_count) [int64]
        log_modifiers: Log-space modifiers nn.Parameter shape (n_asu_unique,)
        modifier_clamp: (min, max) clamp range for log_modifiers

    Returns:
        hkl_grid_modified: Modified structure factor grid same shape as hkl_grid_base

    Implementation:
        hkl_grid_modified[i,j,k] = hkl_grid_base[i,j,k] * exp(clamp(log_modifiers[asu_map[i,j,k]]))
    """
    # Clamp log-modifiers to prevent extreme values
    log_modifiers_clamped = torch.clamp(log_modifiers, *modifier_clamp)

    # Convert to linear space: modifiers = exp(log_modifiers)
    modifiers = torch.exp(log_modifiers_clamped)

    # Broadcast modifiers to HKL grid via ASU index lookup
    # modifiers[hkl_asu_map] has shape (h_count, k_count, l_count)
    modifier_grid = modifiers[hkl_asu_map]

    # Apply element-wise multiplication
    hkl_grid_modified = hkl_grid_base * modifier_grid

    return hkl_grid_modified


# Example usage (NOT executed, just documentation):
"""
# In Stage B setup (one-time cost):
hkl_asu_map, n_asu_unique = compute_hkl_asu_map(
    hkl_grid=stage_a_ctx.hkl_grid_np,
    crystal_symmetry=F.crystal_symmetry(),  # From MTZ
    halo_mask=stage_a_ctx.halo_mask  # Optional
)
log_modifiers = initialize_asu_modifiers(n_asu_unique, device=device)

# In LBFGS closure (per iteration):
hkl_grid_modified = apply_asu_modifiers(
    hkl_grid_base=stage_a_ctx.hkl_grid,  # From Stage A
    hkl_asu_map=hkl_asu_map,
    log_modifiers=log_modifiers,
    modifier_clamp=config.stage_b_modifier_clamp
)

# Compute loss with modified structure factors
bragg_tensor = forward_model(crystal_overrides={"hkl_grid": hkl_grid_modified})
loss = compute_variance_weighted_loss(bragg_tensor, target, variance)
"""
