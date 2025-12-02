"""
HKL utilities for ASU mapping and shell binning (Stage B refinement support).

Provides general-purpose reciprocal space utilities for multi-reflection refinement modes,
extracted from Stage B implementation helpers to enable cross-stage reuse.

References:
- TORCH-REFINE-004 (per-reflection mode)
- docs/spec-db-workflow.md §76-79 (Stage B structure factor modifiers)
- REFINE-005 (cctbx reuse guard for ASU mapping)
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch

# Module-scope logger
logger = logging.getLogger(__name__)


def compute_hkl_shell_lookup(crystal, hkl_metadata: Dict, n_shells: int = 5, device=None, dtype=torch.float32) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Compute per-voxel shell index for resolution-shell structure-factor modifiers (Stage B).

    Creates a 3D tensor mapping each HKL grid voxel to a resolution shell index [0, n_shells-1]
    based on d-spacing (resolution), using the crystal unit cell. This enables Stage B to apply
    differentiable per-shell multipliers to |F| without per-reflection explosion.

    Args:
        crystal: dxtbx Crystal object providing unit-cell parameters for d-spacing calculation
        hkl_metadata: Dict from build_structure_factor_grid with h/k/l_min/max and has_halo
        n_shells: Number of resolution shells (default 5)
        device: torch device for tensor creation (defaults to CPU if None)
        dtype: torch dtype for output tensors

    Returns:
        tuple: (shell_indices, shell_edges)
            - shell_indices: torch.Tensor shape (h_range, k_range, l_range), dtype long,
                            values in [0, n_shells-1] mapping each voxel to its shell
            - shell_edges: torch.Tensor shape (n_shells + 1,), dtype float32,
                          d-spacing boundaries [d_max, ..., d_min] defining shell thresholds

    References:
        - plans/active/TORCH-REFINE-004/implementation.md Phase 1 (shell lookup helper)
        - docs/spec-db-workflow.md:31-34 (Stage B shell modifiers)
        - plans/nanobrag_integration_plan.md:230-233 (per-shell multipliers)

    Note:
        - Requires hkl_metadata["has_halo"]=True for Stage B; fails fast if halo missing
        - d-spacing formula: d = 1 / sqrt( h²/a² + k²/b² + l²/c² ) for orthogonal cells
        - Shell edges are computed from non-zero HKL voxels to avoid wasted shells on halo padding
    """
    if device is None:
        device = torch.device('cpu')

    # Guard: Stage B requires halo-padded grid (REFINE-005)
    if not hkl_metadata.get("has_halo", False):
        raise ValueError(
            "Stage B shell modifiers require halo-padded HKL grid (hkl_metadata['has_halo']=True). "
            "Rebuild structure factor grid with build_structure_factor_grid(..., halo=True)."
        )

    # Extract grid bounds
    h_min, h_max = hkl_metadata["h_min"], hkl_metadata["h_max"]
    k_min, k_max = hkl_metadata["k_min"], hkl_metadata["k_max"]
    l_min, l_max = hkl_metadata["l_min"], hkl_metadata["l_max"]
    h_range = hkl_metadata["h_range"]
    k_range = hkl_metadata["k_range"]
    l_range = hkl_metadata["l_range"]

    # Get unit cell parameters for d-spacing calculation
    cell_params = crystal.get_unit_cell().parameters()  # (a, b, c, alpha, beta, gamma)
    a, b, c = cell_params[0], cell_params[1], cell_params[2]
    # Note: Assumes orthogonal cell for simplicity; generalized formula requires reciprocal metric tensor
    # For monoclinic/triclinic cells, use dxtbx's unit_cell.d(hkl) method per voxel (slower but exact)

    # Build HKL coordinate grids
    h_coords = torch.arange(h_min, h_max + 1, device=device, dtype=dtype)
    k_coords = torch.arange(k_min, k_max + 1, device=device, dtype=dtype)
    l_coords = torch.arange(l_min, l_max + 1, device=device, dtype=dtype)

    # Create 3D meshgrid (broadcasted shape: h_range, k_range, l_range)
    h_grid, k_grid, l_grid = torch.meshgrid(h_coords, k_coords, l_coords, indexing='ij')

    # Compute d-spacing for each HKL voxel (orthogonal approximation)
    # d = 1 / sqrt( (h/a)^2 + (k/b)^2 + (l/c)^2 )
    # Guard against division by zero at origin (000)
    d_star_sq = (h_grid / a) ** 2 + (k_grid / b) ** 2 + (l_grid / c) ** 2
    d_star_sq = torch.clamp(d_star_sq, min=1e-10)  # Prevent 1/0 at origin
    d_spacing = 1.0 / torch.sqrt(d_star_sq)

    # Compute shell edges from non-zero d-spacing distribution
    # Exclude origin and halo padding (filter to data envelope if needed)
    d_nonzero = d_spacing[d_spacing > 1e-8]
    if len(d_nonzero) == 0:
        raise ValueError("All d-spacing values are zero; cannot compute shell edges")

    d_min = float(d_nonzero.min().item())
    d_max = float(d_nonzero.max().item())

    # Shell edges: [d_max, ..., d_min] with n_shells bins
    shell_edges = torch.linspace(d_max, d_min, n_shells + 1, device=device, dtype=dtype)

    # Assign shell index to each voxel via searchsorted
    # searchsorted returns index such that shell_edges[idx-1] <= d < shell_edges[idx]
    # We want shell 0 for highest d-spacing (lowest resolution), shell n_shells-1 for lowest d-spacing (highest resolution)
    shell_indices_flat = torch.searchsorted(shell_edges, d_spacing.flatten(), right=False)
    shell_indices = shell_indices_flat.reshape(h_range, k_range, l_range).long()

    # Clamp to [0, n_shells-1] to handle edge cases at boundaries
    shell_indices = torch.clamp(shell_indices, 0, n_shells - 1)

    return shell_indices, shell_edges


def compute_hkl_asu_map(
    hkl_grid: np.ndarray,
    crystal_symmetry,
    halo_mask: Optional[np.ndarray] = None
) -> Tuple[Optional[torch.Tensor], int]:
    """
    Map each HKL grid voxel to its unique ASU (asymmetric unit) index.

    Uses cctbx.miller symmetry operations to fold Miller indices into the asymmetric
    unit, enabling per-reflection Fhkl modifiers parameterized by unique ASU indices.

    Args:
        hkl_grid: shape (h_count, k_count, l_count, 3) — Miller indices for each voxel
                  (includes ±1 halo per spec-db-workflow.md:61)
        crystal_symmetry: cctbx.crystal.symmetry object with space group + unit cell
                          (extracted from MTZ via F.crystal_symmetry())
        halo_mask: Optional boolean mask shape (h_count, k_count, l_count) marking
                   halo voxels (True=halo, outside MTZ range). If provided, halo
                   voxels map to ASU index 0 with fixed modifier=1.0.

    Returns:
        tuple: (hkl_asu_map, n_asu_unique)
            - hkl_asu_map: torch.Tensor[int64] shape (h_count, k_count, l_count)
                          Values are ASU indices 0..n_asu_unique-1
                          Index 0 is reserved for halo voxels (if halo_mask provided)
                          Returns None on failure (triggers shell mode fallback)
            - n_asu_unique: Total count of unique ASU reflections (including index 0 for halo)
                           Returns 0 on failure

    Edge Cases:
        - Halo voxels: Map to index 0, which will have fixed modifier=1.0 (non-trainable)
        - Systematic absences: cctbx.miller.set handles these automatically
        - Friedel pairs: anomalous_flag=False means (h,k,l) and (-h,-k,-l) map to same ASU
        - Symmetry failures: Wrap cctbx calls in try/except, return (None, 0) on failure

    References:
        - plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/asu_pseudocode.py
        - docs/spec-db-workflow.md:59-61 (per-reflection SHALL be default, halo mandatory)
        - POLICY-001 (Environment Freeze, lazy imports)
        - ARCH-ENGINE-002 (lazy imports for optional dependencies)
    """
    try:
        # Lazy import cctbx (ARCH-ENGINE-002: allows module to load without cctbx)
        from cctbx import miller
        from cctbx.array_family import flex
    except ImportError as e:
        # cctbx not available, fallback to shell mode per spec:60
        logger.warning(f"cctbx.miller import failed: {e}. Falling back to shell mode.")
        return None, 0

    try:
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

    except Exception as e:
        # ASU mapping failed, fallback to shell mode per spec:60
        logger.warning(f"ASU mapping failed: {e}. Falling back to shell mode.")
        return None, 0


def initialize_asu_modifiers(
    n_asu_unique: int,
    device: torch.device,
    dtype: torch.dtype = torch.float32
) -> torch.nn.Parameter:
    """
    Initialize per-reflection ASU modifiers as trainable parameters.

    Args:
        n_asu_unique: Total count of unique ASU reflections (from compute_hkl_asu_map)
        device: torch device (cpu or cuda)
        dtype: torch dtype for parameters (default float32)

    Returns:
        log_modifiers: nn.Parameter shape (n_asu_unique,) initialized near 0
                      (linear-space modifiers ≈ 1.0)
                      Index 0 (halo) has requires_grad=False if n_asu_unique > 1

    Parameterization:
        - Use log-space: modifiers = exp(log_modifiers) to enforce positivity
        - Initialize log_modifiers ≈ 0 so modifiers start near 1.0
        - Index 0 (halo) is fixed at log(1.0) = 0.0 with requires_grad=False
        - Clamping applied in apply_asu_modifiers to [-3, 3] → modifiers in [0.05, 20.1]

    References:
        - plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/asu_pseudocode.py
        - docs/spec-db-workflow.md:61 (halo handling mandatory)
        - REFINE-005 (HKL halo mandatory, fixed modifier=1.0)
    """
    # Initialize log-space parameters near 0 (modifiers ≈ 1.0)
    log_modifiers = torch.zeros(n_asu_unique, dtype=dtype, device=device)

    # Fix index 0 (halo) at log(1.0) = 0.0 permanently if n_asu > 1
    if n_asu_unique > 1:
        # Create parameter with requires_grad=True for indices 1..n_asu_unique-1
        # Index 0 will be non-trainable
        param = torch.nn.Parameter(log_modifiers, requires_grad=True)
        # Register a hook to zero out gradients for index 0
        def zero_halo_grad(grad):
            # Clone to avoid in-place modification issues
            grad_modified = grad.clone()
            grad_modified[0] = 0.0
            return grad_modified
        param.register_hook(zero_halo_grad)
        return param
    else:
        # Edge case: single ASU index (halo only or P1 with 1 reflection)
        return torch.nn.Parameter(log_modifiers, requires_grad=False)


def apply_asu_modifiers(
    hkl_grid_base: torch.Tensor,
    log_modifiers: torch.nn.Parameter,
    hkl_asu_map: torch.Tensor,
    modifier_clamp: Tuple[float, float] = (-3.0, 3.0)
) -> torch.Tensor:
    """
    Apply per-reflection ASU modifiers to HKL grid structure factors.

    Args:
        hkl_grid_base: Base structure factor grid shape (h_count, k_count, l_count)
        log_modifiers: Log-space modifiers nn.Parameter shape (n_asu_unique,)
        hkl_asu_map: ASU index map shape (h_count, k_count, l_count) [int64]
        modifier_clamp: (min, max) clamp range for log_modifiers (default [-3, 3])

    Returns:
        hkl_grid_modified: Modified structure factor grid same shape as hkl_grid_base

    Implementation:
        hkl_grid_modified[i,j,k] = hkl_grid_base[i,j,k] * exp(clamp(log_modifiers[asu_map[i,j,k]]))

    References:
        - plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/asu_pseudocode.py
        - docs/spec-db-workflow.md:59 (per-reflection modifiers)
        - SCALE-001 (modifiers applied post-interpolation to HKL grid)
    """
    # Clamp log-modifiers to prevent extreme values
    log_modifiers_clamped = torch.clamp(log_modifiers, modifier_clamp[0], modifier_clamp[1])

    # Convert to linear space: modifiers = exp(log_modifiers)
    modifiers = torch.exp(log_modifiers_clamped)

    # Broadcast modifiers to HKL grid via ASU index lookup
    # modifiers[hkl_asu_map] has shape (h_count, k_count, l_count)
    modifier_grid = modifiers[hkl_asu_map]

    # Apply element-wise multiplication
    hkl_grid_modified = hkl_grid_base * modifier_grid

    return hkl_grid_modified
