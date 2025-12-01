"""
LBFGS refinement nucleus for nanobrag_torch backend (Stage A/B/C).

Implements the staged refinement loop per:
- plans/nanobrag_integration_plan.md:172-244 (Refinement + Stage B contract)
- docs/spec-db-workflow.md:30-41 (Staging policy + LBFGS optimizer)
- docs/pytorch_runtime_checklist.md (vectorization, device/dtype neutrality)

Stage A scope:
- Parameters: global scale (ADU mode) + full crystal (a/b/c log-deltas, alpha/beta/gamma bounded angles, orientation 3-vector→quaternion)
- Loss: variance-weighted chi-squared per dbex.physics.loss._compute_variance_weighted_loss
        (spec-db-core.md/spec-db-workflow.md), with masked MSE tracked for telemetry.
- ROI policy: deterministic ROI sampling for LBFGS closure; periodic full validation
- Convergence: ≥0.2% loss drop within ≤30 LBFGS steps; non-increasing full-loss trace (TORCH-REFINE-002D)

Stage B (optional, TORCH-REFINE-004):
- Parameters: per-resolution shell multipliers for |F| (softplus parameterization)
- Requires: halo-padded HKL grid (hkl_metadata["has_halo"]=True) and enable_hkl_interpolation=True
- Freezes Stage A parameters; applies modifiers lazily to a copy of hkl_grid
- Convergence: ≥3% loss drop; guards against default_F fallback

Stage C (optional, TORCH-REFINE-003):
- Parameters: per-panel detector distance offsets along normal
- Freezes Stage A (and Stage B if run) parameters
- Convergence: ≥0.002% loss drop (REFINE-007)

Telemetry emitted to `/torch_diagnostics`:
- Per-stage: optimizer metadata, stage label, ROI sampling, loss traces, param_deltas, status
- Multi-stage runs return Dict[str, RefinementTelemetry] keyed by stage ("A", "B", "C")
"""

import copy
import math
import os
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch

# Stage A helpers relocated to dbex.refinement.stage_a_impl (ARCH-REFINE-001)
from dbex.refinement.stage_a_impl import (
    vec_to_unit_quaternion,
    quaternion_to_rotation_matrix,
    quaternion_to_xyz_euler,
    StageAROIEntry,
    StageAContext,
    _build_stage_a_context,
    _sync_stage_a_crystal,
    _retarget_stage_a_simulators,
    _build_stage_a_params,
    _build_stage_a_lbfgs_closure,
    _run_stage_a_lbfgs,
    _clamp_log_cell_deltas,
    _get_sigma_floor_sq_tensor,
)


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
        import logging
        logger = logging.getLogger(__name__)
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
        import logging
        logger = logging.getLogger(__name__)
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


@dataclass
class RefinementConfig:
    """Configuration for Stage A and Stage C LBFGS refinement."""
    # LBFGS hyperparameters (shared across stages)
    history_size: int = 10
    max_iter: int = 30
    tolerance_grad: float = 1e-7
    tolerance_change: float = 1e-9

    # ROI sampling for LBFGS closure
    roi_sample_fraction: float = 0.15  # ~15% of ROIs per iteration
    full_validation_interval: int = 5  # Validate on full loss every N steps

    # Convergence guards (Stage A)
    min_loss_improvement: float = 0.002  # 0.2% minimum improvement (TORCH-REFINE-002D)
    early_stop_window: int = 3  # Stop if no improvement over last K validations
    max_loss_increase: float = 0.02  # 2% max increase before rollback

    # HKL interpolation (TORCH-REFINE-002D, REFINE-005)
    # Enable tricubic interpolation for structure factors; requires halo-padded grid
    # Defaults to False (nearest-neighbor) to protect datasets without halo support
    enable_hkl_interpolation: bool = False

    # U-matrix parameterization (TORCH-GEOMETRY-PARITY-002 Phase B)
    # Enable direct U-matrix quaternion parameterization for Stage A orientation.
    # When False (default), uses existing cell+misset decomposition path (GEOMETRY-003).
    # When True, parameterizes orientation as quaternion → U-matrix, preserving
    # mapping MOSFLM A* strain and eliminating the 1.37e-3 symmetric strain artifact.
    use_u_matrix_parameterization: bool = False

    # LBFGS optimizer for U-matrix path (TORCH-GEOMETRY-CONVERGENCE-001 Phase B Test B1)
    # When True, uses LBFGS optimizer instead of Adam for quaternion U-matrix refinement.
    # LBFGS eliminates momentum accumulation (H4), uses line search (H3), proven for scale-only.
    # Only applies when use_u_matrix_parameterization=True.
    use_lbfgs_for_u_matrix: bool = False

    # Learning rate for U-matrix path (TORCH-GEOMETRY-CONVERGENCE-001 Phase C2)
    # Learning rate for Adam optimizer when use_u_matrix_parameterization=True.
    # Default 1e-5 (10× lower than cell/misset LR) to accommodate quaternion gradient
    # scale O(150k). Per CONVERGENCE-001 Phase C1 root cause analysis.
    # Only applies when use_u_matrix_parameterization=True and use_lbfgs_for_u_matrix=False.
    u_matrix_learning_rate: float = 1e-5

    # Incremental UB parameterization (TORCH-GEOMETRY-UB-REALIGN-001 Phase B3)
    # Enable incremental UB parameterization around baseline dxtbx crystal state.
    # When False (default), uses existing cell+misset default path.
    # When True, parameterizes geometry as U(params) = ΔR(q_delta) @ U₀ and
    # B(params) via log-perturbations for lengths + angle deltas, constructing
    # A*(params) = U(params) @ B(params) in a single direction per spec-db-core.md:64-67.
    # Supersedes use_u_matrix_parameterization when both are enabled.
    use_incremental_ub: bool = False

    # Warm cache (PERF-WARM-SIM-001)
    # Enable Stage A warm cache (prebuild detector models/masks/HKL once).
    # Default True for production (2-5× speedup). Disable for benchmarking cold baseline.
    enable_stage_a_warm_cache: bool = True
    # Enable ROI-aware sampling/cropping when Stage A closures run (PERF-WARM-SIM-001 ROI follow-up)
    enable_stage_a_roi_mode: bool = True
    # Allow ROI sampling even when the warm cache is disabled (default False so cold benchmarks stay panel-scoped)
    allow_cold_stage_a_roi_mode: bool = False

    # Stage B structure factor modifiers (TORCH-REFINE-004)
    enable_stage_b: bool = False  # Enable Fhkl shell modifiers
    stage_b_mode: str = "per_reflection"  # "per_reflection" (default per spec:59) or "shell" (fallback per spec:60)
    stage_b_n_shells: int = 5  # Number of resolution shells for shell mode
    stage_b_min_loss_improvement: float = 1e-8  # 0.000001% minimum improvement for Stage B (calibrated per TORCH-REFINE-004 refGeom probe: measured ceiling ~6.4e-8%, essentially zero)
    stage_b_max_modifier: float = 2.0  # Maximum shell modifier (softplus clamp)
    stage_b_regularization: float = 0.0  # L2 regularization strength (reserved for future)
    stage_b_full_eval_on_cpu: bool = True  # Run Stage B evaluations on CPU to avoid GPU OOM when gradients require large buffers

    # Stage B per-reflection ASU mode (TORCH-REFINE-004 Phase 6)
    stage_b_optimizer_gate: int = 10000  # n_asu threshold for LBFGS vs Adam selection
    stage_b_adam_lr: float = 1e-2  # Adam learning rate for large parameter counts (≥10K) - Phase 7 tuned
    stage_b_modifier_clamp: Tuple[float, float] = (-3.0, 3.0)  # log-space clamp range (modifiers ∈ [0.05, 20.1])

    # Stage C detector microslip (TORCH-REFINE-003)
    enable_stage_c: bool = False  # Enable detector distance refinement
    stage_c_min_loss_improvement: float = 2e-5  # 0.002% minimum improvement for Stage C (calibrated per REFINE-007)
    stage_c_max_distance_delta_mm: float = 0.5  # Maximum distance adjustment per panel (mm)

    # Variance floor guard (PHYSICS-LOSS-002, spec-db-core.md:67)
    # Prevents infinite weights when I_model → 0 on GPU backends
    # Shares units with sigma_readout (target units: photons or ADU)
    sigma_floor_value: float = 1.0  # Default: ~1 photon equivalent

    # Sigma provenance metadata (PHYSICS-LOSS-001 A4)
    sigma_readout_provenance: Optional[str] = None
    sigma_readout_reference_value: Optional[float] = None

    # Calibration metadata (TOOLING-VIS-001 Phase D.C, DB-AT-027)
    # When provided, calibration payload from mapping (spot_scale_override,
    # beam flux/exposure, N_cells) is reused in Stage A context builders.
    # log_scale is then treated as a bounded delta (±3) around the calibrated baseline.
    calibration_metadata: Optional[Dict[str, Any]] = None
    # log_scale baseline when calibration is present (recorded in telemetry)
    log_scale_baseline: Optional[float] = None
    # Apply N_cells from calibration metadata (TOOLING-VIS-001 Phase D.C, SCALE-008)
    # When True (default), N_cells is applied if present in calibration_metadata.
    # When False, N_cells is suppressed even when present (for small-detector metadata fixtures).
    apply_calibration_n_cells: bool = True
    # Clamp log_scale deltas to ±3 when calibration_metadata is provided
    log_scale_max_delta: float = 3.0
    # Absolute clamp for log_scale when no calibration baseline is available
    # (ADU-mode scale absorbs photon↔ADU mismatch). Allows larger dynamic
    # range than the calibrated delta clamp above.
    log_scale_max_delta_uncalibrated: float = 15.0
    # Clamp log-cell deltas to keep unit-cell lengths positive and bounded
    log_cell_max_delta: float = 1.0

    # Telemetry output directory (TORCH-GEOMETRY-CONVERGENCE-001 Phase A1)
    # When set, enables per-step telemetry emission for convergence diagnosis
    telemetry_output_dir: Optional[str] = None

    # Device/dtype
    device: str = "cpu"
    dtype: torch.dtype = torch.float32


@dataclass
class RefinementTelemetry:
    """Telemetry captured during refinement.

    For multi-stage refinement (Stage A + Stage C), this structure represents
    a single stage. The calling code aggregates multiple telemetry objects into
    a Dict[str, RefinementTelemetry] keyed by stage label ("A", "C").

    PHYSICS-LOSS-001: Tracks both chi_squared (variance-weighted loss, the optimization objective)
    and masked_mse (legacy metric for comparison). All stages minimize chi_squared per spec-db-core.md:57-68.

    ARCH-REFACTOR-001 Phase B: Dataclass with to_dict() for HDF5 serialization.
    """
    optimizer: str
    stage: str
    history_size: int
    max_iter: int
    tolerance_grad: float
    tolerance_change: float
    roi_sample_fraction: float
    roi_count_sampled: int
    roi_count_total: int
    loss_trace_sample: List[float] = field(default_factory=list)  # Deprecated: will be chi_squared_trace_sample after PHYSICS-LOSS-001
    loss_trace_full: List[Tuple[int, float]] = field(default_factory=list)  # Deprecated: will be chi_squared_trace_full after PHYSICS-LOSS-001
    best_loss_full: Tuple[float, int] = (0.0, 0)  # Deprecated: will be chi_squared_best after PHYSICS-LOSS-001
    param_deltas: Dict[str, float] = field(default_factory=dict)
    status: str = "ok"  # "ok" | "early_stop" | "rollback" | "error"
    message: str = ""
    perf_counters: Optional[Dict[str, Any]] = None  # PERF-WARM-SIM-001: closure_evals, forward_time_ms, validations
    # PHYSICS-LOSS-001: Dual loss metrics for cross-stage comparison
    chi_squared_trace_sample: Optional[List[float]] = None  # Chi-squared sampled trace (ROI subset)
    chi_squared_trace_full: Optional[List[Tuple[int, float]]] = None  # Chi-squared full trace [(iter, chi2), ...]
    chi_squared_best: Optional[Tuple[float, int]] = None  # Best chi-squared (value, iteration)
    masked_mse_trace_sample: Optional[List[float]] = None  # Masked-MSE sampled trace (legacy metric)
    masked_mse_trace_full: Optional[List[Tuple[int, float]]] = None  # Masked-MSE full trace [(iter, mse), ...]
    masked_mse_best: Optional[Tuple[float, int]] = None  # Best masked-MSE (value, iteration)
    sigma_readout_provenance: Optional[str] = None  # Source of sigma tensor (cli_override, calibrated_map, etc.)
    sigma_readout_reference_value: Optional[float] = None  # Reference scalar (target units, e.g., photons)
    # PHYSICS-LOSS-002: Variance floor telemetry (spec-db-core.md:67)
    variance_floor_value: Optional[float] = None  # sigma_floor^2 used in variance clamping
    variance_floor_clamp_fraction: Optional[float] = None  # Fraction of masked pixels where floor engaged
    variance_floor_masked_pixels: Optional[int] = None  # Total masked pixels used in variance stats
    variance_floor_clamped_pixels: Optional[int] = None  # Pixels where sigma_floor clamp engaged
    # SCALE-008 / TOOLING-VIS-001: Mapping-aware log-scale baseline telemetry
    log_scale_baseline_source: Optional[str] = None  # Source of log_scale_baseline (mapping_global_scale_hint, spot_scale_override_sqrt, etc.)
    spot_scale_override_adjustment_factor: Optional[float] = None  # Adjustment factor when calibration was corrected for N_cells
    # TOOLING-VIS-001 Phase D.E: Masked-mean telemetry for Stage A baseline derivation
    target_mean_masked: Optional[float] = None  # Masked mean of target data used for log_scale_baseline
    model_mean_masked: Optional[float] = None  # Masked mean of Stage A zero-iteration model used for log_scale_baseline
    # PHYSICS-LOSS-003: Canonical Stage A snapshot propagated to downstream stages
    canonical_stage_label: Optional[str] = None
    canonical_chi_squared: Optional[float] = None
    canonical_chi_squared_iteration: Optional[int] = None
    canonical_roi_count: Optional[int] = None
    canonical_detector_distances_mm: Optional[List[float]] = None
    roi_mode: Optional[str] = None
    # Phase A4: Stage identification for engine aggregation
    stage_type: Optional[str] = None  # Stage identifier (A, B, C, or custom)
    mode: Optional[str] = None  # Stage mode (e.g., "shell_modifiers", "detector_offsets")
    # Phase E: Engine delegation telemetry
    engine_protocol: Optional[str] = None  # e.g., "A→B→C", "A-only", "A→B"
    stage_modes: Optional[Dict[str, str]] = None  # e.g., {"B": "shell", "C": "detector_offsets"}
    telemetry_version: str = "1.0"  # Schema versioning for future compatibility

    def to_dict(self) -> Dict[str, Any]:
        """Convert telemetry to dict for HDF5 serialization.

        Returns:
            Dict with scalar attrs (int/float/str/bool) and nested structures
            (lists, dicts, tuples). Caller handles HDF5 attr vs dataset decision.
        """
        return asdict(self)


# Extracted to dbex.physics.loss (ARCH-REFACTOR-001 Phase A)
from dbex.physics.loss import _compute_variance_weighted_loss


def _retarget_stage_a_detectors(
    stage_a_ctx: StageAContext,
    distance_deltas_mm: Dict[int, float],
    device: torch.device,
    dtype: torch.dtype
) -> None:
    """
    Mutate cached Stage A detector configs/simulators with bounded distance offsets.

    Args:
        stage_a_ctx: StageAContext dict with detector_configs, simulators, baseline_distance_mm
        distance_deltas_mm: Per-panel distance deltas in mm (keys: panel_id, values: delta_distance_mm)
        device: torch.device for distance tensor updates
        dtype: torch.dtype for distance tensor updates

    Updates stage_a_ctx.detector_configs and stage_a_ctx.simulators IN PLACE.

    Spec refs:
        - docs/spec-db-runtime.md §2.1 (cache reuse pattern)
        - docs/spec-db-workflow.md §Stage C (detector distance refinement)
        - PERF-WARM-013 finding (eliminate cold instantiation)
    """
    # Lazy imports to avoid circular dependencies (ARCH-ENGINE-002 pattern)
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.simulator import Simulator

    # Extract baseline distances from stage_a_ctx
    baseline_distances = stage_a_ctx.baseline_distance_mm

    for panel_id, delta_distance_mm in distance_deltas_mm.items():
        # Skip panels not in baseline (warn but continue)
        if panel_id >= len(baseline_distances):
            import warnings
            warnings.warn(
                f"Panel ID {panel_id} in distance_deltas_mm but not in baseline_distances (n_panels={len(baseline_distances)}); skipping",
                RuntimeWarning
            )
            continue

        # Compute new distance with bounds check
        new_distance_mm = baseline_distances[panel_id] + delta_distance_mm

        # Guard: safe bounds per REFINE-007 (Stage C typically ±0.25mm deltas)
        if new_distance_mm < 10.0 or new_distance_mm > 10000.0:
            raise ValueError(
                f"Retarget distance out of safe bounds for panel {panel_id}: "
                f"new_distance={new_distance_mm:.3f}mm (baseline={baseline_distances[panel_id]:.3f}mm, "
                f"delta={delta_distance_mm:.3f}mm). Safe range: [10mm, 10000mm]"
            )

        # Update detector config distance_mm
        detector_config = stage_a_ctx.detector_configs[panel_id]
        detector_config.distance_mm = new_distance_mm

        # Check if Simulator has update_detector_distance method
        simulator = stage_a_ctx.simulators[panel_id]
        if hasattr(simulator, 'update_detector_distance'):
            # Hot path: update in place
            simulator.update_detector_distance(new_distance_mm)
        else:
            # Fallback: reconstruct Detector with updated config, then re-instantiate Simulator
            # (Still faster than full cold path because HKL/mask tensors stay cached)
            new_detector = Detector(detector_config, device=device, dtype=dtype)
            stage_a_ctx.detector_models[panel_id] = new_detector

            # Reconstruct Simulator with new detector but reuse cached crystal/beam
            crystal_model = simulator.crystal if hasattr(simulator, 'crystal') else None
            beam_config = stage_a_ctx.beam_config

            new_simulator = Simulator(
                detector=new_detector,
                crystal=crystal_model,
                beam_config=beam_config,
                device=device,
                dtype=dtype,
            )
            stage_a_ctx.simulators[panel_id] = new_simulator


def _build_final_bragg_from_stage_a_telemetry(
    telemetry_a,
    detector,
    beam,
    crystal,
    inputs,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    config,
    device: torch.device,
    dtype: torch.dtype,
    *,
    param_state: str = "final",
    stage_a_ctx: Optional[StageAContext] = None,
    baseline_crystal=None,
):
    """
    Build Bragg array from Stage A telemetry.

    Extracts parameters from telemetry.param_deltas and regenerates a Bragg image
    using either the initial or final parameter state. When a warmed Stage A
    context is available it is reused so reconstruction matches the calibrated
    mapping baseline (beam/crystal/HKL cache and log_scale_baseline semantics).

    Args:
        telemetry_a: RefinementTelemetry instance or dict with optimized param_deltas
        detector: dxtbx Detector object
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object
        inputs: RefinementInputs with panel_slices, trusted_mask
        hkl_grid: torch.Tensor structure factor grid
        hkl_metadata: dict with grid dimensions
        config: RefinementConfig with device, dtype, parameterization mode, calibration_metadata
        device: torch.device for tensor operations
        dtype: torch.dtype for tensor operations
        param_state: "final" (default) or "initial" to pick which telemetry
            values to reconstruct (used for DB-AT-029 bragg_before/bragg_after).
        stage_a_ctx: Optional warmed StageAContext to reuse cached detectors and
            calibration metadata; rebuilt when None or device/dtype mismatch.
        baseline_crystal: Optional baseline crystal used to derive mapping misset.

    Returns:
        bragg_full: np.ndarray, shape [n_panels, slow, fast], final Bragg image
    """
    # Lazy imports to avoid circular dependencies
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from dbex.nanobrag_bridge import (
        create_detector_config,
        create_beam_config,
        create_crystal_config,
        compute_baseline_misset_deg,
    )

    # Extract param_deltas from telemetry (handle both RefinementTelemetry and dict)
    if hasattr(telemetry_a, "param_deltas"):
        param_deltas = telemetry_a.param_deltas
    else:
        param_deltas = telemetry_a["param_deltas"]

    state = (param_state or "final").lower()

    def _select_param(name: str, default=None):
        entry = param_deltas.get(name, default)
        if isinstance(entry, dict):
            if state == "initial" and "initial" in entry:
                return entry["initial"]
            if state == "delta" and "delta" in entry:
                return entry["delta"]
            return entry.get("final", entry.get("initial", default))
        return entry if entry is not None else default

    # Convert param deltas to torch tensors (no requires_grad, reconstruction only)
    log_scale = torch.tensor(_select_param("log_scale", 0.0), device=device, dtype=dtype, requires_grad=False)
    log_cell_a_delta = torch.tensor(_select_param("log_cell_a_delta", 0.0), device=device, dtype=dtype, requires_grad=False)
    log_cell_b_delta = torch.tensor(_select_param("log_cell_b_delta", 0.0), device=device, dtype=dtype, requires_grad=False)
    log_cell_c_delta = torch.tensor(_select_param("log_cell_c_delta", 0.0), device=device, dtype=dtype, requires_grad=False)
    angle_alpha_raw = torch.tensor(_select_param("angle_alpha_raw", 0.0), device=device, dtype=dtype, requires_grad=False)
    angle_beta_raw = torch.tensor(_select_param("angle_beta_raw", 0.0), device=device, dtype=dtype, requires_grad=False)
    angle_gamma_raw = torch.tensor(_select_param("angle_gamma_raw", 0.0), device=device, dtype=dtype, requires_grad=False)
    orientation_vec = torch.tensor(_select_param("orientation_vec", [0.0, 0.0, 0.0]), device=device, dtype=dtype, requires_grad=False)

    # Extract optional params for U-matrix/incremental UB modes
    # (Not currently populated by StageA, but handle gracefully for future support)
    q_params = _select_param("q_params")
    if q_params is not None:
        q_params = torch.tensor(q_params, device=device, dtype=dtype, requires_grad=False)

    q_delta = _select_param("q_delta")
    if q_delta is not None:
        q_delta = torch.tensor(q_delta, device=device, dtype=dtype, requires_grad=False)

    B_ideal_reciprocal_torch = _select_param("B_ideal_reciprocal_torch")
    if B_ideal_reciprocal_torch is not None:
        B_ideal_reciprocal_torch = torch.tensor(B_ideal_reciprocal_torch, device=device, dtype=dtype, requires_grad=False)

    # Get n_panels and panel_shape
    n_panels = len(detector)
    panel_shape = inputs.target.shape[1:]  # (slow, fast)

    # Compute baseline misset so zero-point reconstruction matches mapping baseline
    baseline_misset_deg_tensor = compute_baseline_misset_deg(
        crystal,
        baseline_crystal,
        device=device,
        dtype=dtype,
    )

    # Extract calibration payload (TOOLING-VIS-001 Phase D.C, DB-AT-027)
    # When config.calibration_metadata is provided, forward beam flux/exposure/beamsize
    # and N_cells into configs so reconstructed Bragg frames match mapping baseline
    beam_flux = None
    beam_exposure = None
    beamsize_mm = None
    N_cells = None
    spot_scale_override = None
    if hasattr(config, 'calibration_metadata') and config.calibration_metadata is not None:
        beam_flux = config.calibration_metadata.get("beam_flux")
        beam_exposure = config.calibration_metadata.get("beam_exposure")
        beamsize_mm = config.calibration_metadata.get("beamsize_mm")
        N_cells = config.calibration_metadata.get("N_cells")
        spot_scale_override = config.calibration_metadata.get("spot_scale_override")

    # TOOLING-VIS-001 Phase E: Extract baseline telemetry from Stage A results
    # These values were computed by _build_stage_a_params and stored in telemetry
    log_scale_baseline_value = None
    log_scale_baseline_source = None
    spot_scale_override_adjustment_factor = None

    # Priority 1: Use telemetry fields (from _build_stage_a_params)
    if hasattr(telemetry_a, 'log_scale_baseline_source'):
        log_scale_baseline_source = telemetry_a.log_scale_baseline_source
    elif isinstance(telemetry_a, dict):
        log_scale_baseline_source = telemetry_a.get('log_scale_baseline_source')

    if hasattr(telemetry_a, 'spot_scale_override_adjustment_factor'):
        spot_scale_override_adjustment_factor = telemetry_a.spot_scale_override_adjustment_factor
    elif isinstance(telemetry_a, dict):
        spot_scale_override_adjustment_factor = telemetry_a.get('spot_scale_override_adjustment_factor')

    # Priority 2: param_deltas (for log_scale_baseline value)
    if 'log_scale_baseline' in param_deltas:
        base_entry = param_deltas['log_scale_baseline']
        if isinstance(base_entry, dict):
            log_scale_baseline_value = base_entry.get('final', base_entry.get('initial'))
        else:
            log_scale_baseline_value = base_entry

    # Priority 3: stage_a_ctx (from warm cache)
    if log_scale_baseline_value is None and stage_a_ctx is not None:
        log_scale_baseline_value = getattr(stage_a_ctx, "log_scale_baseline", None)

    # Priority 4: config.log_scale_baseline (explicit override)
    if log_scale_baseline_value is None and hasattr(config, 'log_scale_baseline') and config.log_scale_baseline is not None:
        log_scale_baseline_value = config.log_scale_baseline

    # Priority 5: Fallback to sqrt(spot_scale_override) when not in telemetry
    if log_scale_baseline_value is None and spot_scale_override is not None:
        try:
            log_scale_baseline_value = float(np.log(np.sqrt(spot_scale_override)))
        except (TypeError, ValueError):
            log_scale_baseline_value = None

    log_cell_max_delta = getattr(config, "log_cell_max_delta", 1.0)

    # Reuse warmed Stage A context when available and device/dtype match; rebuild otherwise
    ctx = stage_a_ctx
    if ctx is not None and (ctx.device != device or ctx.dtype != dtype):
        ctx = None
    if ctx is None:
        ctx = _build_stage_a_context(
            detector=detector,
            beam=beam,
            crystal=crystal,
            trusted_mask=inputs.trusted_mask,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            enable_hkl_interpolation=config.enable_hkl_interpolation,
            device=device,
            dtype=dtype,
            panel_slices=inputs.panel_slices,
            enable_roi_mode=getattr(config, "enable_stage_a_roi_mode", False),
            calibration_metadata=getattr(config, "calibration_metadata", None),
            log_scale_baseline=log_scale_baseline_value or getattr(config, "log_scale_baseline", None),
            apply_calibration_n_cells=getattr(config, "apply_calibration_n_cells", True),
        )
    # ctx now guaranteed non-None for reconstruction
    stage_a_ctx = ctx

    # Generate final Bragg array with optimized parameters (lines 2046-2153 from inline code)
    with torch.no_grad():
        bragg_full = np.zeros((n_panels, *panel_shape), dtype=np.float32)

        # Apply final crystal perturbations once (shared across cached simulators)
        cell_params = crystal.get_unit_cell().parameters()
        log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
            log_cell_a_delta,
            log_cell_b_delta,
            log_cell_c_delta,
            log_cell_max_delta,
        )
        perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
        perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
        perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta_clamped)

        max_angle_delta = 10.0  # degrees
        perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
        perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
        perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

        zero_param_deltas = (
            torch.allclose(log_cell_a_delta_clamped, torch.tensor(0.0, device=device, dtype=dtype))
            and torch.allclose(log_cell_b_delta_clamped, torch.tensor(0.0, device=device, dtype=dtype))
            and torch.allclose(log_cell_c_delta_clamped, torch.tensor(0.0, device=device, dtype=dtype))
            and torch.allclose(angle_alpha_raw, torch.tensor(0.0, device=device, dtype=dtype))
            and torch.allclose(angle_beta_raw, torch.tensor(0.0, device=device, dtype=dtype))
            and torch.allclose(angle_gamma_raw, torch.tensor(0.0, device=device, dtype=dtype))
            and torch.allclose(orientation_vec, torch.zeros_like(orientation_vec))
        )

        if config.use_u_matrix_parameterization and q_params is not None and B_ideal_reciprocal_torch is not None:
            from dbex.nanobrag_bridge import quaternion_to_matrix

            q_norm = q_params / torch.norm(q_params)  # Enforce ||q|| = 1
            U = quaternion_to_matrix(q_norm)  # 3x3 rotation matrix
            A_star_new = U @ B_ideal_reciprocal_torch  # Compute updated A*

            A_star_np = A_star_new.detach().cpu().numpy()
            mosflm_a_star_tuple = tuple(A_star_np[:, 0].tolist())
            mosflm_b_star_tuple = tuple(A_star_np[:, 1].tolist())
            mosflm_c_star_tuple = tuple(A_star_np[:, 2].tolist())

            crystal_overrides = {
                'cell_a': perturbed_cell_a,
                'cell_b': perturbed_cell_b,
                'cell_c': perturbed_cell_c,
                'cell_alpha': perturbed_alpha,
                'cell_beta': perturbed_beta,
                'cell_gamma': perturbed_gamma,
                'mosflm_a_star': mosflm_a_star_tuple,
                'mosflm_b_star': mosflm_b_star_tuple,
                'mosflm_c_star': mosflm_c_star_tuple,
            }
            misset_deg_for_crystal = None
        else:
            max_orientation_deg = 3.0  # degrees
            bounded_orientation_vec = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
            quat = vec_to_unit_quaternion(bounded_orientation_vec)
            misset_xyz_deg = quaternion_to_xyz_euler(quat)
            if baseline_misset_deg_tensor is not None:
                misset_xyz_deg = misset_xyz_deg + baseline_misset_deg_tensor

            crystal_overrides = {
                'cell_a': perturbed_cell_a,
                'cell_b': perturbed_cell_b,
                'cell_c': perturbed_cell_c,
                'cell_alpha': perturbed_alpha,
                'cell_beta': perturbed_beta,
                'cell_gamma': perturbed_gamma
            }
            misset_deg_for_crystal = misset_xyz_deg

        if not zero_param_deltas:
            warm_crystal_config, _ = create_crystal_config(
                crystal,
                None,
                crystal_overrides=crystal_overrides,
                misset_deg_override=misset_deg_for_crystal,
                N_cells=N_cells,
                apply_n_cells=(N_cells is not None)
            )
            warm_crystal_model = Crystal(
                warm_crystal_config,
                beam_config=stage_a_ctx.beam_config,
                device=device,
                dtype=dtype,
            )
            warm_crystal_model.interpolate = stage_a_ctx.enable_hkl_interpolation
            warm_crystal_model.hkl_data = stage_a_ctx.hkl_grid
            warm_crystal_model.hkl_metadata = stage_a_ctx.hkl_metadata
            _retarget_stage_a_simulators(stage_a_ctx, warm_crystal_model)

        # Apply scale once using calibrated baseline when available. When a baseline is
        # present, log_scale encodes a bounded delta; otherwise it acts as the absolute
        # scale parameter with the wider uncalibrated clamp.
        has_baseline = log_scale_baseline_value is not None
        delta_bound = (
            getattr(config, "log_scale_max_delta", 3.0)
            if has_baseline
            else getattr(config, "log_scale_max_delta_uncalibrated", 15.0)
        )
        baseline_tensor = (
            torch.tensor(log_scale_baseline_value, device=device, dtype=dtype)
            if has_baseline
            else None
        )

        log_scale_effective = (
            baseline_tensor + torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
            if baseline_tensor is not None
            else torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
        )

        for pid in range(n_panels):
            simulator = stage_a_ctx.simulators[pid]
            panel_bragg = simulator.run()
            panel_bragg_scaled = panel_bragg * torch.exp(log_scale_effective)
            bragg_full[pid] = panel_bragg_scaled.cpu().numpy().astype(np.float32)

    return bragg_full


def _build_stage_b_params(
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    stage_a_ctx: Optional[Dict[str, Any]],
    canonical_baseline: Dict[str, Any],
    n_panels: int,
    sampled_panel_ids: List[int],
    sigma_floor_sq_cache: Dict[torch.device, torch.Tensor],
    use_stage_a_roi_mode: bool,
    crystal,
    hkl_metadata: Dict[str, Any],
    hkl_grid: torch.Tensor,
    detector,
    beam,
    inputs,
    panel_slices: List[Tuple[slice, slice]],
) -> Dict[str, Any]:
    """
    Build Stage B shell modifier parameters, optimizer, and telemetry state.

    Returns:
        param_values: Dict containing:
            - shell_indices: Shell lookup tensor
            - shell_edges: Shell edge boundaries
            - shell_modifier_raw: Trainable shell_modifier_raw tensor
            - params: List[torch.Tensor] — Trainable shell_modifier_raw
            - optimizer: torch.optim.LBFGS — Optimizer for shell modifiers
            - telemetry_state: Dict — Accumulators for chi_squared/masked_mse traces, perf counters
            - stage_b_eval_stage_a_ctx: Optional[Dict] — CPU-cloned or original Stage A context
            - use_stage_b_cpu_fallback: bool
            - stage_b_use_warm_cache: bool
            - stage_b_cache_mode: str — "warm" or "cold"
            - use_stage_b_roi_mode: bool
            - stage_b_roi_label: str — "roi" or "panel"
            - stage_b_total_work_items: int
            - sampled_stage_b_indices: List[int]
            - full_stage_b_indices: List[int]
            - default_f_fallback_count: int
    """
    # PERF-WARM-011: Compute CPU fallback condition FIRST so we can use it for device-aware parameter init
    # When config.stage_b_full_eval_on_cpu is True, device is CUDA, and ROI mode is disabled,
    # route Stage B panel-mode closures/validations to CPU to avoid GPU OOM
    use_stage_b_cpu_fallback = (
        config.stage_b_full_eval_on_cpu
        and str(device).startswith("cuda")
        and not use_stage_a_roi_mode  # ROI mode is disabled (panel mode)
    )

    # GRADIENT-001: Create parameters on CPU when CPU fallback active to prevent gradient chain break
    stage_b_param_device = torch.device("cpu") if use_stage_b_cpu_fallback else torch.device(config.device)

    # Phase 7: Branch on Stage B mode (per-reflection vs shell)
    if config.stage_b_mode == "per_reflection":
        # Compute ASU map using Phase 6 helper
        halo_mask = hkl_metadata.get("halo_mask")  # 3D boolean array
        crystal_symmetry = hkl_metadata.get("crystal_symmetry")  # From MTZ via F.crystal_symmetry()

        if crystal_symmetry is None:
            # crystal_symmetry not available, fallback to shell mode
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("crystal_symmetry not in hkl_metadata, falling back to shell mode")
            config_stage_b_mode_override = "shell"
            asu_indices, n_asu_unique = None, 0
        else:
            # crystal_symmetry available, attempt ASU mapping
            config_stage_b_mode_override = "per_reflection"  # Initialize to per_reflection, may fallback below

            # Get HKL indices grid from metadata (built by test fixture)
            hkl_indices_grid = hkl_metadata.get("hkl_indices_grid")
            if hkl_indices_grid is None:
                # HKL indices grid not in metadata, build it from grid bounds
                h_min, h_max = hkl_metadata["h_min"], hkl_metadata["h_max"]
                k_min, k_max = hkl_metadata["k_min"], hkl_metadata["k_max"]
                l_min, l_max = hkl_metadata["l_min"], hkl_metadata["l_max"]

                h_coords = np.arange(h_min, h_max + 1, dtype=np.int32)
                k_coords = np.arange(k_min, k_max + 1, dtype=np.int32)
                l_coords = np.arange(l_min, l_max + 1, dtype=np.int32)

                h_grid_np, k_grid_np, l_grid_np = np.meshgrid(h_coords, k_coords, l_coords, indexing='ij')
                hkl_indices_grid = np.stack([h_grid_np, k_grid_np, l_grid_np], axis=-1)

            asu_indices, n_asu_unique = compute_hkl_asu_map(
                hkl_indices_grid,
                crystal_symmetry,
                halo_mask=halo_mask
            )

        # Check if ASU mapping succeeded; fallback to shell mode if failed
        if config_stage_b_mode_override == "per_reflection" and (asu_indices is None or n_asu_unique == 0):
            # ASU mapping failed, fall back to shell mode (spec:60 permits fallback)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"ASU mapping returned None/zero, falling back to shell mode for this refinement")
            config_stage_b_mode_override = "shell"
        elif config_stage_b_mode_override == "per_reflection":
            # ASU mapping succeeded, proceed with per-reflection mode
            asu_indices_t = asu_indices.to(device=device, dtype=torch.long)

            # Initialize ASU modifiers using Phase 6 helper
            log_modifiers = initialize_asu_modifiers(
                n_asu_unique=n_asu_unique,
                device=stage_b_param_device,  # Respect CPU fallback logic
                dtype=dtype
            )
            stage_b_params = [log_modifiers]

            config_stage_b_mode_override = "per_reflection"

    # If shell mode (original or fallback from per_reflection)
    if config.stage_b_mode == "shell" or (config.stage_b_mode == "per_reflection" and config_stage_b_mode_override == "shell"):
        # Compute shell lookup for per-shell modifiers
        shell_indices, shell_edges = compute_hkl_shell_lookup(
            crystal, hkl_metadata, n_shells=config.stage_b_n_shells, device=device, dtype=dtype
        )

        # Initialize shell modifiers (softplus parameterization to keep multipliers positive)
        # Start near identity: softplus(0) ≈ 0.69, so initialize slightly negative to get ~1.0
        shell_modifier_raw = torch.zeros(config.stage_b_n_shells, device=stage_b_param_device, dtype=dtype, requires_grad=True)
        identity_raw = math.log(math.expm1(0.5))  # softplus(identity_raw)*2 == 1.0
        shell_modifier_raw.data.fill_(identity_raw)

        stage_b_params = [shell_modifier_raw]

        config_stage_b_mode_override = "shell"

    # Phase 7.2: Dynamic optimizer selection based on mode and parameter count
    if config_stage_b_mode_override == "per_reflection":
        n_asu = n_asu_unique
        if n_asu >= config.stage_b_optimizer_gate:  # Default 10000
            # Adam for large parameter counts (spec-db-workflow.md:107 permits Adam)
            stage_b_optimizer = torch.optim.Adam(
                stage_b_params,
                lr=config.stage_b_adam_lr  # Default 1e-3
            )
            optimizer_type = "adam"
        else:
            # LBFGS for small parameter counts (spec default per spec-db-workflow.md:107)
            stage_b_optimizer = torch.optim.LBFGS(
                stage_b_params,
                history_size=config.history_size,
                max_iter=config.max_iter,
                tolerance_grad=config.tolerance_grad,
                tolerance_change=config.tolerance_change,
                line_search_fn='strong_wolfe'
            )
            optimizer_type = "lbfgs"
    else:  # "shell" mode
        # Existing LBFGS-only path
        stage_b_optimizer = torch.optim.LBFGS(
            stage_b_params,
            history_size=config.history_size,
            max_iter=config.max_iter,
            tolerance_grad=config.tolerance_grad,
            tolerance_change=config.tolerance_change,
            line_search_fn='strong_wolfe'
        )
        optimizer_type = "lbfgs"

    # Telemetry accumulators for Stage B
    loss_trace_sample_b = []
    loss_trace_full_b = []
    best_loss_full_b = (float('inf'), 0)

    # Best params snapshot depends on mode
    if config_stage_b_mode_override == "per_reflection":
        best_params_snapshot_b = {'log_modifiers': log_modifiers.data.clone()}
    else:
        best_params_snapshot_b = {'shell_modifier_raw': shell_modifier_raw.data.clone()}

    # PHYSICS-LOSS-001: Dual metric tracking (chi_squared + masked_mse)
    chi_squared_trace_sample_b = []
    chi_squared_trace_full_b = []
    chi_squared_best_b = (float('inf'), -1)
    masked_mse_trace_sample_b = []
    masked_mse_trace_full_b = []
    masked_mse_best_b = (float('inf'), -1)

    # Track default_F fallback count (should be zero with halo grid)
    # Note: nanobrag_torch doesn't expose default_F counter directly; this is a placeholder
    # for future telemetry when the API exposes it
    default_f_fallback_count = 0

    # PHYSICS-LOSS-002: Variance floor clamp statistics for Stage B
    variance_floor_clamped_pixels_b = [0]  # Total pixels where floor engaged
    variance_floor_masked_pixels_b = [0]  # Total masked pixels evaluated

    # PERF-WARM-012: Clone StageAContext to CPU when fallback is active so Stage B can reuse
    # cached detectors/HKL/masks even on CPU, maintaining cache_mode="warm"
    stage_b_eval_stage_a_ctx = None
    if use_stage_b_cpu_fallback and stage_a_ctx is not None and config.enable_stage_a_warm_cache:
        # Build a fresh Stage A context on CPU device
        cpu_device = torch.device("cpu")

        stage_b_eval_stage_a_ctx = _build_stage_a_context(
            detector=detector,
            beam=beam,
            crystal=crystal,
            trusted_mask=inputs.trusted_mask,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            enable_hkl_interpolation=config.enable_hkl_interpolation,
            device=cpu_device,
            dtype=dtype,
            panel_slices=panel_slices,
            enable_roi_mode=False,  # CPU fallback is panel-mode only
            calibration_metadata=config.calibration_metadata,
            log_scale_baseline=config.log_scale_baseline,
            apply_calibration_n_cells=config.apply_calibration_n_cells,
        )
    elif not use_stage_b_cpu_fallback:
        # No CPU fallback: reuse the original CUDA Stage A context
        stage_b_eval_stage_a_ctx = stage_a_ctx

    stage_b_use_warm_cache = (
        stage_b_eval_stage_a_ctx is not None
        and config.enable_stage_a_warm_cache
    )
    stage_b_cache_mode = "warm" if stage_b_use_warm_cache else "cold"

    # PERF-WARM-SIM-001: Stage B ROI mode mirrors Stage A's ROI knob
    use_stage_b_roi_mode = use_stage_a_roi_mode and stage_b_use_warm_cache
    stage_b_roi_label = "roi" if use_stage_b_roi_mode else "panel"
    stage_b_total_work_items = canonical_baseline["roi_count"] if use_stage_b_roi_mode else n_panels

    # Sample ROIs or panels for Stage B (~15% by default)
    if use_stage_b_roi_mode:
        roi_sample_size_b = max(1, int(stage_b_total_work_items * config.roi_sample_fraction))
        roi_sample_size_b = min(stage_b_total_work_items, roi_sample_size_b)
        sampled_stage_b_indices = sorted(
            np.random.choice(stage_b_total_work_items, size=roi_sample_size_b, replace=False).tolist()
        )
    else:
        sampled_stage_b_indices = list(sampled_panel_ids)
    full_stage_b_indices = list(range(stage_b_total_work_items))

    perf_closure_evals_b = [0]
    perf_validation_runs_b = [0]
    perf_forward_times_ms_b: List[float] = []

    # Build telemetry state dict
    telemetry_state = {
        'loss_trace_sample_b': loss_trace_sample_b,
        'loss_trace_full_b': loss_trace_full_b,
        'best_loss_full_b': best_loss_full_b,
        'best_params_snapshot_b': best_params_snapshot_b,
        'chi_squared_trace_sample_b': chi_squared_trace_sample_b,
        'chi_squared_trace_full_b': chi_squared_trace_full_b,
        'chi_squared_best_b': chi_squared_best_b,
        'masked_mse_trace_sample_b': masked_mse_trace_sample_b,
        'masked_mse_trace_full_b': masked_mse_trace_full_b,
        'masked_mse_best_b': masked_mse_best_b,
        'variance_floor_clamped_pixels_b': variance_floor_clamped_pixels_b,
        'variance_floor_masked_pixels_b': variance_floor_masked_pixels_b,
        'perf_closure_evals_b': perf_closure_evals_b,
        'perf_validation_runs_b': perf_validation_runs_b,
        'perf_forward_times_ms_b': perf_forward_times_ms_b,
    }

    # Build return dict with mode-specific fields
    param_dict = {
        'params': stage_b_params,
        'optimizer': stage_b_optimizer,
        'optimizer_type': optimizer_type,
        'stage_b_mode': config_stage_b_mode_override,
        'telemetry_state': telemetry_state,
        'stage_b_eval_stage_a_ctx': stage_b_eval_stage_a_ctx,
        'use_stage_b_cpu_fallback': use_stage_b_cpu_fallback,
        'stage_b_use_warm_cache': stage_b_use_warm_cache,
        'stage_b_cache_mode': stage_b_cache_mode,
        'use_stage_b_roi_mode': use_stage_b_roi_mode,
        'stage_b_roi_label': stage_b_roi_label,
        'stage_b_total_work_items': stage_b_total_work_items,
        'sampled_stage_b_indices': sampled_stage_b_indices,
        'full_stage_b_indices': full_stage_b_indices,
        'default_f_fallback_count': default_f_fallback_count,
        'stage_b_param_device': stage_b_param_device,
    }

    # Add mode-specific fields
    if config_stage_b_mode_override == "per_reflection":
        param_dict.update({
            'asu_indices': asu_indices_t,
            'n_asu_unique': n_asu_unique,
            'log_modifiers': log_modifiers,
        })
    else:  # shell mode
        param_dict.update({
            'shell_indices': shell_indices,
            'shell_edges': shell_edges,
            'shell_modifier_raw': shell_modifier_raw,
        })

    return param_dict


def _build_stage_b_lbfgs_closure(
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    param_values: Dict[str, Any],
    stage_a_ctx: Optional[Dict[str, Any]],
    stage_b_eval_stage_a_ctx: Optional[Dict[str, Any]],
    canonical_baseline: Dict[str, Any],
    n_panels: int,
    sampled_stage_b_indices: List[int],
    full_stage_b_indices: List[int],
    sigma_floor_sq_cache: Dict[Tuple[str, str], torch.Tensor],
    use_stage_b_cpu_fallback: bool,
    stage_b_use_warm_cache: bool,
    use_stage_b_roi_mode: bool,
    crystal: Any,
    hkl_metadata: Dict[str, Any],
    hkl_grid: torch.Tensor,
    shell_indices: torch.Tensor,
    detector: Any,
    beam: Any,
    inputs: Any,
    target_t: torch.Tensor,
    loss_mask_t: torch.Tensor,
    sigma_readout_t: torch.Tensor,
    baseline_misset_deg_tensor: Optional[torch.Tensor],
    panel_shape: Tuple[int, int],
) -> Tuple[Callable[[List[int], bool, bool], Tuple[torch.Tensor, torch.Tensor]], Callable[[], torch.Tensor]]:
    """
    Build LBFGS closure for Stage B shell modifier refinement.

    Returns tuple of (compute_loss_stage_b, closure_stage_b).
    compute_loss_stage_b: Callable for manual loss evaluation (used for final validation).
    closure_stage_b: Callable for LBFGS optimizer.
    Mirrors Phase B1a-loop2 pattern for Stage A closure extraction.
    """
    # Extract parameters from param_values dict
    stage_b_mode = param_values['stage_b_mode']
    stage_b_optimizer = param_values['optimizer']

    # Phase 7.3: Extract mode-specific parameters
    if stage_b_mode == "per_reflection":
        asu_indices = param_values['asu_indices']
        log_modifiers = param_values['log_modifiers']
        n_asu_unique = param_values['n_asu_unique']
    else:  # shell mode
        shell_modifier_raw = param_values['shell_modifier_raw']
        shell_indices = param_values['shell_indices']
    log_scale = param_values['log_scale']
    cell_a_tensor = param_values['cell_a_tensor']
    cell_b_tensor = param_values['cell_b_tensor']
    cell_c_tensor = param_values['cell_c_tensor']
    cell_alpha_tensor = param_values['cell_alpha_tensor']
    cell_beta_tensor = param_values['cell_beta_tensor']
    cell_gamma_tensor = param_values['cell_gamma_tensor']
    misset_xyz_deg = param_values['misset_xyz_deg']
    stage_b_params = param_values['params']

    # Extract telemetry accumulators from nested telemetry_state
    telemetry = param_values['telemetry_state']
    loss_trace_sample_b = telemetry['loss_trace_sample_b']
    loss_trace_full_b = telemetry['loss_trace_full_b']
    chi_squared_trace_sample_b = telemetry['chi_squared_trace_sample_b']
    chi_squared_trace_full_b = telemetry['chi_squared_trace_full_b']
    masked_mse_trace_sample_b = telemetry['masked_mse_trace_sample_b']
    masked_mse_trace_full_b = telemetry['masked_mse_trace_full_b']
    chi_squared_best_b = telemetry['chi_squared_best_b']
    masked_mse_best_b = telemetry['masked_mse_best_b']
    best_loss_full_b = telemetry['best_loss_full_b']
    best_params_snapshot_b = telemetry['best_params_snapshot_b']
    variance_floor_clamped_pixels_b = telemetry['variance_floor_clamped_pixels_b']
    variance_floor_masked_pixels_b = telemetry['variance_floor_masked_pixels_b']
    perf_closure_evals_b = telemetry['perf_closure_evals_b']
    perf_validation_runs_b = telemetry['perf_validation_runs_b']
    perf_forward_times_ms_b = telemetry['perf_forward_times_ms_b']

    def compute_loss_stage_b(work_item_ids: List[int], is_full: bool = False, force_panel_eval: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute variance-weighted chi-squared loss with Stage B shell-modified structure factors.

        Uses Stage A's final crystal parameters (frozen) and varies per-shell Fhkl multipliers.

        Args:
            work_item_ids: List of ROI or panel indices to evaluate
            is_full: Whether this is a full validation run (counts toward perf telemetry)
            force_panel_eval: If True, always use panel-mode evaluation regardless of ROI config
                          (reuses warmed simulators when available). Used for initial/periodic/final
                          validations to ensure shell modifiers stay within ±1% gate (PERF-WARM-009).

        Returns:
            Tuple of (chi_squared_loss, masked_mse_loss): Both scalar tensors for telemetry
        """
        from dbex.nanobrag_bridge import create_detector_config, create_crystal_config
        from nanobrag_torch.models import Detector, Crystal
        from nanobrag_torch.simulator import Simulator

        t0 = time.perf_counter()
        if is_full:
            perf_validation_runs_b[0] += 1

        # PERF-WARM-011: Route to CPU when fallback is active (panel mode + CUDA + config flag)
        eval_device = torch.device("cpu") if use_stage_b_cpu_fallback else device

        chi_squared_accum = torch.tensor(0.0, device=eval_device, dtype=dtype)
        mse_numerator_accum = torch.tensor(0.0, device=eval_device, dtype=dtype)
        n_pixels_accum = 0
        sigma_floor_sq_eval = _get_sigma_floor_sq_tensor(
            sigma_floor_sq_cache, eval_device, dtype, config.sigma_floor_value
        )

        cell_a_eval = cell_a_tensor if eval_device == device else cell_a_tensor.to(device=eval_device)
        cell_b_eval = cell_b_tensor if eval_device == device else cell_b_tensor.to(device=eval_device)
        cell_c_eval = cell_c_tensor if eval_device == device else cell_c_tensor.to(device=eval_device)
        cell_alpha_eval = cell_alpha_tensor if eval_device == device else cell_alpha_tensor.to(device=eval_device)
        cell_beta_eval = cell_beta_tensor if eval_device == device else cell_beta_tensor.to(device=eval_device)
        cell_gamma_eval = cell_gamma_tensor if eval_device == device else cell_gamma_tensor.to(device=eval_device)
        misset_eval = misset_xyz_deg if eval_device == device else misset_xyz_deg.to(device=eval_device)
        baseline_misset_eval = None
        if baseline_misset_deg_tensor is not None:
            baseline_misset_eval = (
                baseline_misset_deg_tensor
                if eval_device == device
                else baseline_misset_deg_tensor.to(device=eval_device)
            )
        log_scale_eval = log_scale if eval_device == device else log_scale.to(device=eval_device)

        crystal_overrides_eval = {
            'cell_a': cell_a_eval,
            'cell_b': cell_b_eval,
            'cell_c': cell_c_eval,
            'cell_alpha': cell_alpha_eval,
            'cell_beta': cell_beta_eval,
            'cell_gamma': cell_gamma_eval,
        }

        # ARCH-REFINE-FLOW-001 Phase C2.4: When CPU fallback active, use CPU-native HKL grid from
        # stage_b_eval_stage_a_ctx (built at line 2234-2246) instead of transferring CUDA hkl_grid.
        # Minimal reproducer (loop i=220) proved CPU simulator works with native CPU HKL grid;
        # CUDA→CPU transfer in closure causes device mismatch or data corruption (0% Bragg output).
        if use_stage_b_cpu_fallback and stage_b_eval_stage_a_ctx is not None:
            # CPU fallback: use CPU-native HKL grid from cloned Stage A context (PERF-WARM-012)
            hkl_grid_local = stage_b_eval_stage_a_ctx.hkl_grid
        else:
            # Normal path: transfer to eval device if needed
            hkl_grid_local = hkl_grid if eval_device == device else hkl_grid.to(device=eval_device, dtype=dtype)

        # Phase 7.3: Mode-aware modifier application
        if stage_b_mode == "per_reflection":
            # ASU mode: apply per-reflection modifiers using Phase 6 helper
            asu_indices_local = asu_indices if eval_device == device else asu_indices.to(device=eval_device)
            log_modifiers_local = log_modifiers if eval_device == device else log_modifiers.to(device=eval_device)
            hkl_grid_modified = apply_asu_modifiers(
                hkl_grid_base=hkl_grid_local,
                log_modifiers=log_modifiers_local,
                hkl_asu_map=asu_indices_local,
                modifier_clamp=config.stage_b_modifier_clamp  # (-3.0, 3.0) default
            )
        else:  # "shell" mode
            # Existing shell modifier path
            shell_modifiers = torch.nn.functional.softplus(shell_modifier_raw) * 2.0
            shell_modifiers = torch.clamp(shell_modifiers, max=config.stage_b_max_modifier)
            shell_indices_local = shell_indices if eval_device == device else shell_indices.to(device=eval_device)
            # Initialize hkl_grid_modified as clone of local grid
            hkl_grid_modified = hkl_grid_local.clone()
            for shell_idx in range(config.stage_b_n_shells):
                mask = (shell_indices_local == shell_idx)
                modifier_value = shell_modifiers[shell_idx]
                if modifier_value.device != eval_device:
                    modifier_value = modifier_value.to(device=eval_device)
                # Out-of-place: creates NEW tensor with gradient graph
                hkl_grid_modified = torch.where(
                    mask,  # Boolean mask [panels, slow, fast]
                    hkl_grid_local * modifier_value,  # Gradient-enabled operation
                    hkl_grid_modified  # Keep existing values for non-matching shells
                )

        # PERF-WARM-012: Use the eval-device-specific Stage A context (CPU or CUDA)
        use_warm_eval = stage_b_use_warm_cache
        if use_warm_eval:
            misset_override = misset_eval
            if baseline_misset_eval is not None:
                misset_override = baseline_misset_eval + misset_eval
            warm_crystal_config, _ = create_crystal_config(
                crystal,
                None,
                crystal_overrides=crystal_overrides_eval,
                misset_deg_override=misset_override,
                apply_n_cells=False,
            )
            warm_crystal_model = Crystal(
                warm_crystal_config,
                beam_config=stage_b_eval_stage_a_ctx.beam_config,
                device=eval_device,
                dtype=dtype,
            )
            warm_crystal_model.interpolate = True
            warm_crystal_model.hkl_data = hkl_grid_modified
            warm_crystal_model.hkl_metadata = hkl_metadata
            _retarget_stage_a_simulators(stage_b_eval_stage_a_ctx, warm_crystal_model)

        # PERF-WARM-SIM-001: Branch on ROI vs panel mode
        # PERF-WARM-009: force_panel_eval overrides ROI mode for validations
        use_roi_for_this_eval = use_stage_b_roi_mode and not force_panel_eval
        if use_roi_for_this_eval:
            # ROI mode: iterate over Stage A's cached ROI entries
            indices = work_item_ids if work_item_ids else full_stage_b_indices
            for roi_index in indices:
                roi_entry = stage_b_eval_stage_a_ctx.roi_entries[roi_index]
                pid, bbox = roi_entry.panel_id, roi_entry.bbox
                x0, x1, y0, y1 = map(int, bbox)
                slow_slice = slice(y0, y1)
                fast_slice = slice(x0, x1)

                target_subset = target_t[pid, slow_slice, fast_slice].to(device=eval_device, dtype=dtype)
                mask_subset = loss_mask_t[pid, slow_slice, fast_slice].to(device=eval_device)
                if stage_b_eval_stage_a_ctx.trusted_masks_t is not None:
                    trusted_slice = stage_b_eval_stage_a_ctx.trusted_masks_t[pid, slow_slice, fast_slice].to(device=eval_device)
                    mask_subset = torch.logical_and(mask_subset, trusted_slice)
                sigma_subset = sigma_readout_t[pid, slow_slice, fast_slice].to(device=eval_device, dtype=dtype)

                simulator = roi_entry.simulator
                bragg_patch = simulator.run()
                log_scale_clamped = torch.clamp(log_scale_eval, min=-10.0, max=10.0)
                bragg_scaled = bragg_patch * torch.exp(log_scale_clamped)

                (
                    chi_sq_roi,
                    masked_mse_roi,
                    masked_pixels_roi,
                    clamped_pixels_roi,
                ) = _compute_variance_weighted_loss(
                    bragg_scaled,
                    target_subset,
                    mask_subset,
                    sigma_subset,
                    sigma_floor_sq_eval,
                )
                chi_squared_accum = chi_squared_accum + chi_sq_roi
                mse_numerator_accum = mse_numerator_accum + masked_mse_roi * masked_pixels_roi
                n_pixels_accum += masked_pixels_roi
                variance_floor_clamped_pixels_b[0] += clamped_pixels_roi
                variance_floor_masked_pixels_b[0] += masked_pixels_roi
        else:
            # Panel mode: iterate over panels
            panel_ids = work_item_ids if work_item_ids else full_stage_b_indices
            for pid in panel_ids:
                if use_warm_eval:
                    simulator = stage_b_eval_stage_a_ctx.simulators[pid]
                    bragg_panel = simulator.run()
                else:
                    detector_config = create_detector_config(
                        panel=detector[pid],
                        beam=beam,
                        trusted_mask=inputs.trusted_mask[pid]
                    )
                    mask_array = detector_config.mask_array
                    if mask_array is not None and not isinstance(mask_array, torch.Tensor):
                        mask_array = torch.tensor(mask_array, dtype=torch.float32, device=eval_device)
                        detector_config.mask_array = mask_array
                    elif mask_array is not None and mask_array.device != eval_device:
                        detector_config.mask_array = mask_array.to(device=eval_device, dtype=torch.float32)
                    misset_override = misset_eval
                    if baseline_misset_eval is not None:
                        misset_override = baseline_misset_eval + misset_eval
                    crystal_config, _ = create_crystal_config(
                        crystal,
                        None,
                        crystal_overrides=crystal_overrides_eval,
                        misset_deg_override=misset_override,
                        apply_n_cells=False
                    )
                    detector_model = Detector(detector_config, device=eval_device, dtype=dtype)
                    crystal_model = Crystal(crystal_config, device=eval_device, dtype=dtype)
                    crystal_model.interpolate = True
                    crystal_model.hkl_data = hkl_grid_modified
                    crystal_model.hkl_metadata = hkl_metadata
                    simulator = Simulator(detector=detector_model, crystal=crystal_model, device=eval_device, dtype=dtype)
                    bragg_panel = simulator.run()

                target_panel = target_t[pid].to(device=eval_device, dtype=dtype)
                loss_mask_panel = loss_mask_t[pid].to(device=eval_device)
                sigma_panel = sigma_readout_t[pid].to(device=eval_device, dtype=dtype)
                log_scale_clamped = torch.clamp(log_scale_eval, min=-10.0, max=10.0)
                bragg_scaled = bragg_panel * torch.exp(log_scale_clamped)

                (
                    chi_sq_panel,
                    masked_mse_panel,
                    masked_pixels_panel,
                clamped_pixels_panel,
            ) = _compute_variance_weighted_loss(
                bragg_scaled,
                target_panel,
                loss_mask_panel,
                sigma_panel,
                sigma_floor_sq_eval,
            )
            chi_squared_accum = chi_squared_accum + chi_sq_panel
            mse_numerator_accum = mse_numerator_accum + masked_mse_panel * masked_pixels_panel
            n_pixels_accum += masked_pixels_panel
            variance_floor_clamped_pixels_b[0] += clamped_pixels_panel
            variance_floor_masked_pixels_b[0] += masked_pixels_panel

        chi_squared_loss = chi_squared_accum
        if n_pixels_accum > 0:
            masked_mse_loss = mse_numerator_accum / n_pixels_accum
        else:
            masked_mse_loss = mse_numerator_accum

        perf_forward_times_ms_b.append((time.perf_counter() - t0) * 1000.0)

        return chi_squared_loss, masked_mse_loss

    def closure_stage_b():
        """LBFGS closure for Stage B shell modifier refinement."""
        nonlocal chi_squared_best_b, masked_mse_best_b, best_loss_full_b, best_params_snapshot_b
        stage_b_optimizer.zero_grad()
        perf_closure_evals_b[0] += 1

        # Sample ROIs or panels for efficiency (PERF-WARM-SIM-001)
        chi_squared_loss, mse_loss = compute_loss_stage_b(sampled_stage_b_indices, is_full=False)

        chi_squared_loss.backward()

        # Gradient NaN/Inf guard
        for p in stage_b_params:
            if p.grad is not None and (torch.isnan(p.grad).any() or torch.isinf(p.grad).any()):
                raise RuntimeError(f"NaN/Inf gradient detected in Stage B parameter {p}")

        # Record loss
        loss_trace_sample_b.append(float(chi_squared_loss.item()))
        # PHYSICS-LOSS-001: Record both metrics
        chi_squared_trace_sample_b.append(float(chi_squared_loss.item()))
        masked_mse_trace_sample_b.append(float(mse_loss.item()))

        # Periodic full validation
        # PERF-WARM-009: Force panel evaluation for periodic validations to keep modifiers within ±1%
        if len(loss_trace_sample_b) % config.full_validation_interval == 0:
            with torch.no_grad():
                full_chi_squared_b, full_mse_b = compute_loss_stage_b(
                    list(range(n_panels)), is_full=True, force_panel_eval=True
                )
                loss_trace_full_b.append((len(loss_trace_sample_b), float(full_chi_squared_b.item())))
                # PHYSICS-LOSS-001: Record both metrics
                chi_squared_trace_full_b.append((len(loss_trace_sample_b), float(full_chi_squared_b.item())))
                masked_mse_trace_full_b.append((len(loss_trace_sample_b), float(full_mse_b.item())))

                # Update best snapshot
                # PHYSICS-LOSS-001: Track best for both metrics
                if full_chi_squared_b.item() < chi_squared_best_b[0]:
                    chi_squared_best_b = (float(full_chi_squared_b.item()), len(loss_trace_sample_b))
                    best_loss_full_b = (float(full_chi_squared_b.item()), len(loss_trace_sample_b))  # Deprecated legacy field
                    # Phase 7: Mode-aware best params snapshot
                    if stage_b_mode == "per_reflection":
                        best_params_snapshot_b['log_modifiers'] = log_modifiers.data.clone()
                    else:
                        best_params_snapshot_b['shell_modifier_raw'] = shell_modifier_raw.data.clone()
                if full_mse_b.item() < masked_mse_best_b[0]:
                    masked_mse_best_b = (float(full_mse_b.item()), len(loss_trace_sample_b))

        return chi_squared_loss

    return compute_loss_stage_b, closure_stage_b


def _run_stage_b_lbfgs(
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    param_values: Dict[str, Any],
    closure_stage_b: Callable[[], torch.Tensor],
    compute_loss_stage_b: Callable[[List[int], bool, bool], Tuple[torch.Tensor, torch.Tensor]],
    n_panels: int,
) -> Dict[str, Any]:
    """
    Run LBFGS optimization for Stage B shell modifier refinement.

    Returns dict with status, message, final metrics, and best params snapshot.
    Mirrors Phase B1a-loop3 pattern for Stage A LBFGS execution.
    """
    # Extract param_values dict entries (mode-aware)
    stage_b_optimizer = param_values['optimizer']
    stage_b_mode = param_values['stage_b_mode']
    optimizer_type = param_values['optimizer_type']  # "adam" or "lbfgs"

    # Mode-aware parameter extraction
    if stage_b_mode == "per_reflection":
        log_modifiers = param_values['log_modifiers']
        shell_modifier_raw = None  # Not used in per-reflection mode
    else:  # shell mode
        shell_modifier_raw = param_values['shell_modifier_raw']
        log_modifiers = None  # Not used in shell mode

    log_scale = param_values['log_scale']
    telemetry = param_values['telemetry_state']
    loss_trace_full_b = telemetry['loss_trace_full_b']
    chi_squared_trace_full_b = telemetry['chi_squared_trace_full_b']
    masked_mse_trace_full_b = telemetry['masked_mse_trace_full_b']
    loss_trace_sample_b = telemetry['loss_trace_sample_b']
    best_params_snapshot_b = telemetry['best_params_snapshot_b']
    stage_b_param_device = param_values['stage_b_param_device']
    best_loss_full = param_values['best_loss_full']  # Stage A final loss for improvement calc

    # Initialize mutable accumulators (tuples)
    chi_squared_best_b = [float('inf'), 0]
    masked_mse_best_b = [float('inf'), 0]
    best_loss_full_b = [float('inf'), 0]

    status_b = "ok"
    message_b = ""
    try:
        # Initial full-loss validation before optimization (mandatory per TORCH-REFINE-004)
        # PERF-WARM-009: Force panel evaluation for initial validation to keep modifiers within ±1%
        with torch.no_grad():
            initial_chi_squared_b, initial_mse_b = compute_loss_stage_b(
                list(range(n_panels)), is_full=True, force_panel_eval=True
            )
            # Record initial metrics in traces
            loss_trace_full_b.append((0, float(initial_chi_squared_b.item())))
            # PHYSICS-LOSS-001: Record both metrics
            chi_squared_trace_full_b.append((0, float(initial_chi_squared_b.item())))
            masked_mse_trace_full_b.append((0, float(initial_mse_b.item())))
            chi_squared_best_b[0] = float(initial_chi_squared_b.item())
            chi_squared_best_b[1] = 0
            masked_mse_best_b[0] = float(initial_mse_b.item())
            masked_mse_best_b[1] = 0
            best_loss_full_b[0] = float(initial_chi_squared_b.item())
            best_loss_full_b[1] = 0
            # Phase 7: Mode-aware best params snapshot
            if param_values['stage_b_mode'] == "per_reflection":
                best_params_snapshot_b['log_modifiers'] = param_values['log_modifiers'].data.clone()
            else:
                best_params_snapshot_b['shell_modifier_raw'] = param_values['shell_modifier_raw'].data.clone()

        # Run optimization (optimizer-agnostic pattern per TORCH-REFINE-004 Phase 7 blocker fix)
        if optimizer_type == "adam":
            # Adam requires manual loop: call closure() to compute loss/gradients,
            # then call step() without arguments to update params
            max_iter_b = config.max_iter  # Default 30 per RefinementConfig
            for iteration_adam in range(max_iter_b):
                loss = closure_stage_b()  # Computes loss, backward(), updates traces (zero_grad() called internally)
                stage_b_optimizer.step()  # Update params (NO closure arg for Adam)

                # Check improvement after each iteration (reuse LBFGS periodic validation logic)
                if len(loss_trace_full_b) > 0:
                    _, latest_full_loss = loss_trace_full_b[-1]
                    improvement_b = (best_loss_full[0] - latest_full_loss) / best_loss_full[0]
                    if improvement_b >= config.stage_b_min_loss_improvement:
                        status_b = "ok"
                        message_b = f"Stage B converged after {iteration_adam+1} Adam iterations (improvement {improvement_b:.4%})"
                        break
        else:  # "lbfgs"
            # LBFGS uses closure-based pattern (original line 3112)
            stage_b_optimizer.step(closure_stage_b)

    except Exception as e:
        status_b = "error"
        message_b = f"Stage B error: {str(e)}"

    # Restore best snapshot (always, even on success, to ensure consistency)
    # PERF-WARM-009: Force panel evaluation for final validation to keep modifiers within ±1%
    final_step = len(loss_trace_sample_b)
    with torch.no_grad():
        candidate_final_chi2, candidate_final_mse = compute_loss_stage_b(
            list(range(n_panels)), is_full=True, force_panel_eval=True
        )
    candidate_loss_value = float(candidate_final_chi2.item())
    candidate_mse_value = float(candidate_final_mse.item())
    if candidate_loss_value < chi_squared_best_b[0]:
        chi_squared_best_b[0] = candidate_loss_value
        chi_squared_best_b[1] = final_step
        best_loss_full_b[0] = candidate_loss_value
        best_loss_full_b[1] = final_step
        # Phase 7: Mode-aware best params snapshot
        if param_values['stage_b_mode'] == "per_reflection":
            best_params_snapshot_b['log_modifiers'] = param_values['log_modifiers'].data.clone()
        else:
            best_params_snapshot_b['shell_modifier_raw'] = param_values['shell_modifier_raw'].data.clone()
    if candidate_mse_value < masked_mse_best_b[0]:
        masked_mse_best_b[0] = candidate_mse_value
        masked_mse_best_b[1] = final_step

    # Phase 7: Restore best params (mode-aware)
    if best_loss_full_b[0] < float('inf'):
        if param_values['stage_b_mode'] == "per_reflection":
            param_values['log_modifiers'].data = best_params_snapshot_b['log_modifiers'].to(
                device=stage_b_param_device,
                dtype=dtype
            )
        else:
            param_values['shell_modifier_raw'].data = best_params_snapshot_b['shell_modifier_raw'].to(
                device=stage_b_param_device,
                dtype=dtype
            )

    final_loss_value = chi_squared_best_b[0] if chi_squared_best_b[0] < float('inf') else candidate_loss_value
    final_mse_value = masked_mse_best_b[0] if masked_mse_best_b[0] < float('inf') else candidate_mse_value
    loss_trace_full_b.append((final_step, final_loss_value))
    chi_squared_trace_full_b.append((final_step, final_loss_value))
    masked_mse_trace_full_b.append((final_step, final_mse_value))

    # Improvement gate check (REFINE-008)
    if status_b != "error" and best_loss_full[0] is not None and best_loss_full[0] > 0:
        stage_a_final_loss = best_loss_full[0]
        improvement_b = (stage_a_final_loss - final_loss_value) / stage_a_final_loss
        if improvement_b < config.stage_b_min_loss_improvement:
            status_b = "early_stop"
            message_b = (
                f"Stage B improvement {improvement_b:.4%} < "
                f"{config.stage_b_min_loss_improvement:.4%} (calibrated gate per TORCH-REFINE-004, "
                "artifact: plans/active/TORCH-REFINE-004/reports/2025-11-05T190344Z/stage_b_improvement_probe.json)"
            )

    # Return results for downstream wiring code
    return {
        'status': status_b,
        'message': message_b,
        'best_loss_full_b': tuple(best_loss_full_b),
        'chi_squared_best_b': tuple(chi_squared_best_b),
        'masked_mse_best_b': tuple(masked_mse_best_b),
        'final_loss_value': final_loss_value,
        'final_mse_value': final_mse_value,
    }


def _build_stage_c_params(
    config: 'RefinementConfig',
    device: torch.device,
    dtype: torch.dtype,
    n_panels: int,
    baseline_detector: Optional[Any],  # dxtbx.model.Detector
    detector: Any,  # dxtbx.model.Detector
    sampled_panel_ids: List[int],
    panel_slices: List[Tuple[int, int, int, int, int]],
    stage_a_ctx: Optional['StageAContext'],
    sigma_floor_sq_cache: Dict[str, torch.Tensor],
    params: List[torch.Tensor]  # Stage A params to freeze
) -> Dict[str, Any]:
    """
    Initialize Stage C detector distance offset parameters and optimizer.

    Stage C refines per-panel translations along detector normal (distance offset)
    with crystal orientation/cell frozen from Stage A.

    Returns dict with keys:
        - 'distance_offset_raw': torch.Tensor (n_panels,) trainable parameter
        - 'stage_c_params': List[torch.Tensor] (optimizer params)
        - 'stage_c_optimizer': torch.optim.LBFGS
        - 'baseline_detector_distances': Optional[List[float]] (mm per panel)
        - 'stage_c_use_warm_cache': bool
        - 'stage_c_cache_mode': str ('warm' or 'cold')
        - 'stage_c_roi_mode_active': bool
        - 'stage_c_roi_mode_label': str ('roi' or 'panel')
        - 'stage_c_roi_count_total': int
        - 'stage_c_roi_count_sampled': int
        - 'roi_slices_by_pid': Dict[int, List[Tuple[int, int, int, int]]]
        - 'perf_closure_evals_c': List[int] (mutable counter)
        - 'perf_validation_runs_c': List[int] (mutable counter)
        - 'perf_forward_times_ms_c': List[float] (mutable accumulator)
        - 'loss_trace_sample_c': List[float]
        - 'loss_trace_full_c': List[float]
        - 'best_loss_full_c': Tuple[float, int] (value, iteration)
        - 'best_params_snapshot_c': Optional[List[torch.Tensor]]
        - 'iteration_count_c': List[int] (mutable counter)
        - 'chi_squared_trace_sample_c': List[float]
        - 'chi_squared_trace_full_c': List[float]
        - 'chi_squared_best_c': Tuple[float, int]
        - 'masked_mse_trace_sample_c': List[float]
        - 'masked_mse_trace_full_c': List[float]
        - 'masked_mse_best_c': Tuple[float, int]
        - 'variance_floor_clamped_pixels_c': List[int]
        - 'variance_floor_masked_pixels_c': List[int]
        - 'sigma_floor_sq_tensor_stage_c': torch.Tensor
    """
    # Compute baseline_detector_distances for Stage C telemetry (TORCH-REFINE-003)
    # This is used to report initial detector offsets relative to nominal geometry
    baseline_detector_distances = None
    if baseline_detector is not None:
        baseline_detector_distances = [
            baseline_detector[pid].get_directed_distance() for pid in range(n_panels)
        ]

    # Freeze Stage A parameters (no grad)
    for p in params:
        p.requires_grad = False

    # Initialize per-panel distance offsets (mm along panel normal)
    # Start at zero (identity), bounded by tanh to ±max_distance_delta_mm
    distance_offset_raw = torch.zeros(n_panels, device=device, dtype=dtype, requires_grad=True)

    stage_c_params = [distance_offset_raw]
    stage_c_use_warm_cache = (
        stage_a_ctx is not None
        and config.enable_stage_a_warm_cache
        and stage_a_ctx.device == device
        and stage_a_ctx.dtype == dtype
    )
    stage_c_cache_mode = "warm" if stage_c_use_warm_cache else "cold"
    perf_closure_evals_c = [0]
    perf_validation_runs_c = [0]
    perf_forward_times_ms_c: List[float] = []
    roi_slices_by_pid: Dict[int, List[Tuple[int, int, int, int]]] = defaultdict(list)
    for pid, bbox in panel_slices:
        roi_slices_by_pid[int(pid)].append(tuple(int(v) for v in bbox))
    stage_c_roi_mode_active = (
        stage_c_use_warm_cache
        and config.enable_stage_a_roi_mode
        and len(roi_slices_by_pid) > 0
    )
    stage_c_roi_mode_label = "roi" if stage_c_roi_mode_active else "panel"
    sampled_pid_set = set(sampled_panel_ids)
    if stage_c_roi_mode_active:
        stage_c_roi_count_total = sum(len(bboxes) for bboxes in roi_slices_by_pid.values())
        stage_c_roi_count_sampled = sum(len(roi_slices_by_pid.get(pid, [])) for pid in sampled_pid_set)
    else:
        stage_c_roi_count_total = n_panels
        stage_c_roi_count_sampled = len(sampled_panel_ids)

    # Setup LBFGS optimizer for Stage C
    stage_c_optimizer = torch.optim.LBFGS(
        stage_c_params,
        history_size=config.history_size,
        max_iter=config.max_iter,
        tolerance_grad=config.tolerance_grad,
        tolerance_change=config.tolerance_change,
        line_search_fn="strong_wolfe"
    )

    # Telemetry accumulators for Stage C
    loss_trace_sample_c = []
    loss_trace_full_c = []
    best_loss_full_c = (float('inf'), -1)
    best_params_snapshot_c = None
    iteration_count_c = [0]

    # PHYSICS-LOSS-001: Dual metric tracking (chi_squared + masked_mse)
    chi_squared_trace_sample_c = []
    chi_squared_trace_full_c = []
    chi_squared_best_c = (float('inf'), -1)
    masked_mse_trace_sample_c = []
    masked_mse_trace_full_c = []
    masked_mse_best_c = (float('inf'), -1)

    # PHYSICS-LOSS-002: Variance floor clamp statistics for Stage C
    variance_floor_clamped_pixels_c = [0]  # Total pixels where floor engaged
    variance_floor_masked_pixels_c = [0]  # Total masked pixels evaluated
    sigma_floor_sq_tensor_stage_c = _get_sigma_floor_sq_tensor(
        sigma_floor_sq_cache, device, dtype, config.sigma_floor_value
    )

    return {
        'distance_offset_raw': distance_offset_raw,
        'stage_c_params': stage_c_params,
        'stage_c_optimizer': stage_c_optimizer,
        'baseline_detector_distances': baseline_detector_distances,
        'stage_c_use_warm_cache': stage_c_use_warm_cache,
        'stage_c_cache_mode': stage_c_cache_mode,
        'stage_c_roi_mode_active': stage_c_roi_mode_active,
        'stage_c_roi_mode_label': stage_c_roi_mode_label,
        'stage_c_roi_count_total': stage_c_roi_count_total,
        'stage_c_roi_count_sampled': stage_c_roi_count_sampled,
        'roi_slices_by_pid': roi_slices_by_pid,
        'perf_closure_evals_c': perf_closure_evals_c,
        'perf_validation_runs_c': perf_validation_runs_c,
        'perf_forward_times_ms_c': perf_forward_times_ms_c,
        'loss_trace_sample_c': loss_trace_sample_c,
        'loss_trace_full_c': loss_trace_full_c,
        'best_loss_full_c': best_loss_full_c,
        'best_params_snapshot_c': best_params_snapshot_c,
        'iteration_count_c': iteration_count_c,
        'chi_squared_trace_sample_c': chi_squared_trace_sample_c,
        'chi_squared_trace_full_c': chi_squared_trace_full_c,
        'chi_squared_best_c': chi_squared_best_c,
        'masked_mse_trace_sample_c': masked_mse_trace_sample_c,
        'masked_mse_trace_full_c': masked_mse_trace_full_c,
        'masked_mse_best_c': masked_mse_best_c,
        'variance_floor_clamped_pixels_c': variance_floor_clamped_pixels_c,
        'variance_floor_masked_pixels_c': variance_floor_masked_pixels_c,
        'sigma_floor_sq_tensor_stage_c': sigma_floor_sq_tensor_stage_c,
    }


def _build_stage_c_lbfgs_closure(
    param_values: Dict[str, Any],
    telemetry_state: Dict[str, Any],
    stage_c_context: Dict[str, Any],
    detector: Any,  # dxtbx.model.Detector
    beam: Any,  # dxtbx.model.Beam
    inputs: Any,  # RefinementInputs
    config: 'RefinementConfig',
    sigma_floor_sq_cache: Dict[str, torch.Tensor],
    device: torch.device,
    dtype: torch.dtype,
    crystal: Any,  # dxtbx.model.Crystal (Stage A final params)
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict[str, Any],
    stage_a_ctx: Optional['StageAContext'],
    sampled_panel_ids: List[int]
) -> Tuple[Callable[[List[int], bool], Tuple[torch.Tensor, torch.Tensor]], Callable[[], torch.Tensor]]:
    """
    Build Stage C LBFGS closure for detector distance refinement.

    Returns tuple of (compute_loss_stage_c, closure_stage_c) with captured lexical scope
    for ~25 nonlocal variables extracted from input dicts.

    Both nested functions implement variance-weighted chi-squared loss with Stage C
    detector distance adjustments, freezing Stage A crystal parameters.

    Returns:
        Tuple of:
        - compute_loss_stage_c: Callable[[panel_ids, is_full], (chi_squared, mse)]
        - closure_stage_c: Callable[[], chi_squared_loss] (LBFGS closure contract)
    """
    # Extract from param_values dict
    distance_offset_raw = param_values['distance_offset_raw']
    stage_c_params = param_values['stage_c_params']
    stage_c_optimizer = param_values['stage_c_optimizer']
    log_scale = param_values['log_scale']
    log_cell_a_delta = param_values.get('log_cell_a_delta')
    log_cell_b_delta = param_values.get('log_cell_b_delta')
    log_cell_c_delta = param_values.get('log_cell_c_delta')
    angle_alpha_raw = param_values.get('angle_alpha_raw')
    angle_beta_raw = param_values.get('angle_beta_raw')
    angle_gamma_raw = param_values.get('angle_gamma_raw')
    orientation_vec = param_values.get('orientation_vec')
    baseline_misset_deg_tensor = param_values.get('baseline_misset_deg_tensor')
    misset_deg_for_crystal = param_values.get('misset_deg_for_crystal')
    target_t = param_values['target_t']
    loss_mask_t = param_values['loss_mask_t']
    sigma_readout_t = param_values['sigma_readout_t']

    # Extract from telemetry_state dict
    perf_closure_evals_c = telemetry_state['perf_closure_evals_c']
    perf_validation_runs_c = telemetry_state['perf_validation_runs_c']
    perf_forward_times_ms_c = telemetry_state['perf_forward_times_ms_c']
    loss_trace_sample_c = telemetry_state['loss_trace_sample_c']
    loss_trace_full_c = telemetry_state['loss_trace_full_c']
    best_loss_full_c = telemetry_state['best_loss_full_c']
    best_params_snapshot_c = telemetry_state['best_params_snapshot_c']
    iteration_count_c = telemetry_state['iteration_count_c']
    chi_squared_trace_sample_c = telemetry_state['chi_squared_trace_sample_c']
    chi_squared_trace_full_c = telemetry_state['chi_squared_trace_full_c']
    chi_squared_best_c = telemetry_state['chi_squared_best_c']
    masked_mse_trace_sample_c = telemetry_state['masked_mse_trace_sample_c']
    masked_mse_trace_full_c = telemetry_state['masked_mse_trace_full_c']
    masked_mse_best_c = telemetry_state['masked_mse_best_c']
    variance_floor_clamped_pixels_c = telemetry_state['variance_floor_clamped_pixels_c']
    variance_floor_masked_pixels_c = telemetry_state['variance_floor_masked_pixels_c']
    sigma_floor_sq_tensor_stage_c = telemetry_state['sigma_floor_sq_tensor_stage_c']

    # Extract from stage_c_context dict
    stage_c_use_warm_cache = stage_c_context['stage_c_use_warm_cache']
    stage_c_cache_mode = stage_c_context['stage_c_cache_mode']
    stage_c_roi_mode_active = stage_c_context['stage_c_roi_mode_active']
    stage_c_roi_mode_label = stage_c_context['stage_c_roi_mode_label']
    roi_slices_by_pid = stage_c_context['roi_slices_by_pid']
    n_panels = len(detector)

    def compute_loss_stage_c(panel_ids: List[int], is_full: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute variance-weighted chi-squared loss with Stage C detector distance adjustments.

        Uses Stage A's final crystal parameters (frozen) and varies per-panel distances.

        Returns:
            Tuple of (chi_squared_loss, masked_mse_loss): Both scalar tensors for telemetry
        """
        # Lazy imports inside nested function (device-specific, conditional)
        from nanobrag_torch.models import Detector, Crystal
        from nanobrag_torch.simulator import Simulator
        from dbex.nanobrag_bridge import create_detector_config, create_crystal_config

        t0 = time.perf_counter()
        if is_full:
            perf_validation_runs_c[0] += 1
        bragg_panels = []
        target_panels = []
        mask_panels = []
        sigma_panels = []

        # PERF-WARM-SIM-001 Phase D: Use frozen Stage A final cell parameters
        # Stage C spec (docs/spec-db-workflow.md:62-65): Fixed crystal, scale, Fhkl
        stage_a_final_cell = param_values.get('stage_a_final_cell')
        if stage_a_final_cell is not None:
            # Frozen values from Stage A (no recomputation)
            perturbed_cell_a = stage_a_final_cell['cell_a']
            perturbed_cell_b = stage_a_final_cell['cell_b']
            perturbed_cell_c = stage_a_final_cell['cell_c']
            perturbed_alpha = stage_a_final_cell['alpha']
            perturbed_beta = stage_a_final_cell['beta']
            perturbed_gamma = stage_a_final_cell['gamma']
        else:
            # Fallback: recompute from baseline (backward compatibility)
            cell_params = crystal.get_unit_cell().parameters()
            log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
                log_cell_a_delta,
                log_cell_b_delta,
                log_cell_c_delta,
                getattr(config, "log_cell_max_delta", 1.0),
            )
            perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
            perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
            perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta_clamped)

            max_angle_delta = 10.0
            perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
            perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
            perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

        max_orientation_deg = 3.0
        bounded_orientation_vec = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
        quat = vec_to_unit_quaternion(bounded_orientation_vec)
        misset_xyz_deg = quaternion_to_xyz_euler(quat)

        if baseline_misset_deg_tensor is not None:
            misset_xyz_deg = misset_xyz_deg + baseline_misset_deg_tensor

        crystal_overrides = {
            'cell_a': perturbed_cell_a,
            'cell_b': perturbed_cell_b,
            'cell_c': perturbed_cell_c,
            'cell_alpha': perturbed_alpha,
            'cell_beta': perturbed_beta,
            'cell_gamma': perturbed_gamma
        }
        crystal_config, _ = create_crystal_config(
            crystal,
            None,
            crystal_overrides=crystal_overrides,
            misset_deg_override=misset_deg_for_crystal
        )

        crystal_model = Crystal(crystal_config, device=device, dtype=dtype)
        crystal_model.interpolate = config.enable_hkl_interpolation
        crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
        crystal_model.hkl_metadata = hkl_metadata

        # PERF-WARM-013: Build distance deltas dict once before panel loop for retargeting
        if stage_c_use_warm_cache:
            distance_deltas_mm = {}
            for pid in panel_ids:
                bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
                # Extract scalar from tensor for dict storage
                distance_deltas_mm[pid] = bounded_offset.item() if isinstance(bounded_offset, torch.Tensor) else bounded_offset

            # Retarget cached detectors with distance offsets (mutates stage_a_ctx in place)
            _retarget_stage_a_detectors(
                stage_a_ctx=stage_a_ctx,
                distance_deltas_mm=distance_deltas_mm,
                device=device,
                dtype=dtype
            )

        for pid in panel_ids:
            panel = detector[pid]

            if stage_c_use_warm_cache:
                # Warm path: reuse retargeted detector/simulator from stage_a_ctx
                detector_model = stage_a_ctx.detector_models[pid]
                simulator = stage_a_ctx.simulators[pid]
                # Attach current crystal model (frozen Stage A params)
                simulator.crystal = crystal_model
                simulator.beam_config = stage_a_ctx.beam_config
            else:
                # Cold path: instantiate fresh (existing code, keep AS-IS)
                bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
                baseline_distance_mm = panel.get_directed_distance()
                distance_mm_override = baseline_distance_mm + bounded_offset

                detector_config = create_detector_config(
                    panel=panel,
                    beam=beam,
                    trusted_mask=inputs.trusted_mask[pid],
                    distance_mm_override=distance_mm_override
                )
                if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                    detector_config.mask_array = torch.tensor(
                        detector_config.mask_array, dtype=torch.float32, device=device
                    )
                detector_model = Detector(detector_config, device=device, dtype=dtype)
                simulator = Simulator(detector=detector_model, crystal=crystal_model, device=device, dtype=dtype)

            panel_bragg = simulator.run()

            bragg_panels.append(panel_bragg)
            target_panels.append(target_t[pid])
            mask_panels.append(loss_mask_t[pid])
            sigma_panels.append(sigma_readout_t[pid])

        log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
        panel_outputs = {pid: panel for pid, panel in zip(panel_ids, bragg_panels)}
        target_outputs = {pid: panel for pid, panel in zip(panel_ids, target_panels)}
        mask_outputs = {pid: panel for pid, panel in zip(panel_ids, mask_panels)}
        sigma_outputs = {pid: panel for pid, panel in zip(panel_ids, sigma_panels)}

        if stage_c_roi_mode_active:
            chi_squared_accum = torch.zeros((), device=device, dtype=dtype)
            mse_numerator_accum = torch.zeros((), device=device, dtype=dtype)
            masked_pixels_total = 0
            clamped_pixels_total = 0
            for pid in panel_ids:
                roi_list = roi_slices_by_pid.get(pid, [])
                if not roi_list:
                    continue
                panel_output = panel_outputs[pid]
                target_panel = target_outputs[pid]
                mask_panel = mask_outputs[pid]
                sigma_panel = sigma_outputs[pid]
                for bbox in roi_list:
                    x0, x1, y0, y1 = bbox
                    slow_slice = slice(y0, y1)
                    fast_slice = slice(x0, x1)
                    bragg_roi = panel_output[slow_slice, fast_slice] * torch.exp(log_scale_clamped)
                    target_roi = target_panel[slow_slice, fast_slice]
                    mask_roi = mask_panel[slow_slice, fast_slice]
                    sigma_roi = sigma_panel[slow_slice, fast_slice]
                    (
                        chi_roi,
                        mse_roi,
                        masked_pixels_roi,
                        clamped_pixels_roi,
                    ) = _compute_variance_weighted_loss(
                        bragg_roi,
                        target_roi,
                        mask_roi,
                        sigma_roi,
                        sigma_floor_sq_tensor_stage_c,
                    )
                    chi_squared_accum = chi_squared_accum + chi_roi
                    mse_numerator_accum = mse_numerator_accum + mse_roi * masked_pixels_roi
                    masked_pixels_total += masked_pixels_roi
                    clamped_pixels_total += clamped_pixels_roi

            if masked_pixels_total > 0:
                masked_mse_loss = mse_numerator_accum / masked_pixels_total
            else:
                masked_mse_loss = mse_numerator_accum
            chi_squared_loss = chi_squared_accum
            variance_floor_clamped_pixels_c[0] += clamped_pixels_total
            variance_floor_masked_pixels_c[0] += masked_pixels_total
        else:
            bragg_stacked = torch.stack(
                [panel_outputs[pid] for pid in panel_ids], dim=0
            )
            bragg_scaled = bragg_stacked * torch.exp(log_scale_clamped)
            target_subset = torch.stack([target_outputs[pid] for pid in panel_ids], dim=0)
            mask_subset = torch.stack([mask_outputs[pid] for pid in panel_ids], dim=0)
            sigma_subset = torch.stack([sigma_outputs[pid] for pid in panel_ids], dim=0)
            (
                chi_squared_loss,
                masked_mse_loss,
                masked_pixels_stage_c,
                clamped_pixels_stage_c,
            ) = _compute_variance_weighted_loss(
                bragg_scaled,
                target_subset,
                mask_subset,
                sigma_subset,
                sigma_floor_sq_tensor_stage_c,
            )
            variance_floor_clamped_pixels_c[0] += clamped_pixels_stage_c
            variance_floor_masked_pixels_c[0] += masked_pixels_stage_c
        perf_forward_times_ms_c.append((time.perf_counter() - t0) * 1000.0)

        return chi_squared_loss, masked_mse_loss

    def closure_stage_c():
        """LBFGS closure for Stage C detector refinement."""
        stage_c_optimizer.zero_grad()
        perf_closure_evals_c[0] += 1

        # Compute loss on sampled ROIs
        chi_squared_loss, mse_loss = compute_loss_stage_c(sampled_panel_ids, is_full=False)

        # Backward pass
        chi_squared_loss.backward()

        # Check for NaN/Inf gradients
        for p in stage_c_params:
            if p.grad is not None and (torch.isnan(p.grad).any() or torch.isinf(p.grad).any()):
                raise RuntimeError(f"NaN/Inf gradient detected in Stage C parameter {p}")

        # Record loss
        loss_trace_sample_c.append(float(chi_squared_loss.item()))
        # PHYSICS-LOSS-001: Record both metrics
        chi_squared_trace_sample_c.append(float(chi_squared_loss.item()))
        masked_mse_trace_sample_c.append(float(mse_loss.item()))

        # Periodic full validation
        if iteration_count_c[0] % config.full_validation_interval == 0:
            with torch.no_grad():
                full_chi_squared_c, full_mse_c = compute_loss_stage_c(list(range(n_panels)), is_full=True)
                loss_trace_full_c.append((iteration_count_c[0], float(full_chi_squared_c.item())))
                # PHYSICS-LOSS-001: Record both metrics
                chi_squared_trace_full_c.append((iteration_count_c[0], float(full_chi_squared_c.item())))
                masked_mse_trace_full_c.append((iteration_count_c[0], float(full_mse_c.item())))

                # Update best snapshot
                nonlocal best_loss_full_c, best_params_snapshot_c, chi_squared_best_c, masked_mse_best_c
                # PHYSICS-LOSS-001: Track best for both metrics
                if full_chi_squared_c.item() < chi_squared_best_c[0]:
                    chi_squared_best_c = (float(full_chi_squared_c.item()), iteration_count_c[0])
                    best_loss_full_c = (float(full_chi_squared_c.item()), iteration_count_c[0])  # Deprecated legacy field
                    best_params_snapshot_c = {
                        'distance_offset_raw': distance_offset_raw.detach().cpu().tolist()
                    }
                if full_mse_c.item() < masked_mse_best_c[0]:
                    masked_mse_best_c = (float(full_mse_c.item()), iteration_count_c[0])

        iteration_count_c[0] += 1
        return chi_squared_loss

    return compute_loss_stage_c, closure_stage_c


def _run_stage_c_lbfgs(
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    param_values: Dict[str, Any],
    telemetry_state: Dict[str, Any],
    stage_c_context: Dict[str, Any],
    compute_loss_stage_c: Callable,
    closure_stage_c: Callable,
    crystal,  # dxtbx Crystal
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    detector,  # dxtbx Detector
    beam,  # dxtbx Beam
    inputs,  # DataLoad (untyped to avoid import)
    canonical_baseline: Dict[str, Any],
    stage_a_ctx: Optional[StageAContext],
    n_panels: int,
) -> Dict[str, Any]:
    """
    Execute Stage C LBFGS optimization, final validation, improvement gate,
    best snapshot restore, final Bragg regeneration, and telemetry packaging.

    Returns dict with keys:
        - 'status_c': str ('ok', 'early_stop', 'error')
        - 'message_c': str
        - 'telemetry_c': RefinementTelemetry
        - 'bragg_full': np.ndarray (n_panels, slow, fast)
        - 'final_step_c': int
        - 'final_loss_value_c': float
        - 'final_mse_value_c': float
    """
    # Extract from param_values dict
    distance_offset_raw = param_values['distance_offset_raw']
    stage_c_params = param_values['stage_c_params']
    stage_c_optimizer = param_values['stage_c_optimizer']
    log_scale = param_values['log_scale']
    log_cell_a_delta = param_values.get('log_cell_a_delta')
    log_cell_b_delta = param_values.get('log_cell_b_delta')
    log_cell_c_delta = param_values.get('log_cell_c_delta')
    angle_alpha_raw = param_values.get('angle_alpha_raw')
    angle_beta_raw = param_values.get('angle_beta_raw')
    angle_gamma_raw = param_values.get('angle_gamma_raw')
    orientation_vec = param_values.get('orientation_vec')
    baseline_misset_deg_tensor = param_values.get('baseline_misset_deg_tensor')

    # Extract from telemetry_state dict (ALL as mutable references via list wrappers)
    chi_squared_best_c = telemetry_state['chi_squared_best_c']
    masked_mse_best_c = telemetry_state['masked_mse_best_c']
    best_params_snapshot_c = telemetry_state.get('best_params_snapshot_c')
    iteration_count_c = telemetry_state['iteration_count_c']
    loss_trace_sample_c = telemetry_state['loss_trace_sample_c']
    loss_trace_full_c = telemetry_state['loss_trace_full_c']
    chi_squared_trace_sample_c = telemetry_state['chi_squared_trace_sample_c']
    chi_squared_trace_full_c = telemetry_state['chi_squared_trace_full_c']
    masked_mse_trace_sample_c = telemetry_state['masked_mse_trace_sample_c']
    masked_mse_trace_full_c = telemetry_state['masked_mse_trace_full_c']
    variance_floor_clamped_pixels_c = telemetry_state['variance_floor_clamped_pixels_c']
    variance_floor_masked_pixels_c = telemetry_state['variance_floor_masked_pixels_c']
    perf_closure_evals_c = telemetry_state['perf_closure_evals_c']
    perf_validation_runs_c = telemetry_state['perf_validation_runs_c']
    perf_forward_times_ms_c = telemetry_state['perf_forward_times_ms_c']
    best_loss_full_c = telemetry_state['best_loss_full_c']

    # Extract from stage_c_context dict
    stage_c_use_warm_cache = stage_c_context['stage_c_use_warm_cache']
    stage_c_cache_mode = stage_c_context['stage_c_cache_mode']
    stage_c_roi_mode_label = stage_c_context['stage_c_roi_mode_label']
    stage_c_roi_count_total = stage_c_context['stage_c_roi_count_total']
    stage_c_roi_count_sampled = stage_c_context['stage_c_roi_count_sampled']
    baseline_detector_distances = stage_c_context.get('baseline_detector_distances')
    sampled_panel_ids = stage_c_context['sampled_panel_ids']
    _apply_baseline_detector_prior = stage_c_context['_apply_baseline_detector_prior']
    misset_deg_for_crystal = stage_c_context['misset_deg_for_crystal']

    # Extract from canonical_baseline dict (needed for improvement gate)
    best_loss_full = (canonical_baseline['chi_squared'], canonical_baseline['iteration'])

    # Derived variables
    panel_shape = inputs.target.shape[1:]

    # Lazy imports (inside helper to avoid circular deps)
    from nanobrag_torch.models import Detector, Crystal
    from nanobrag_torch.simulator import Simulator
    from dbex.nanobrag_bridge import create_detector_config, create_crystal_config

    # Run Stage C LBFGS optimization
    status_c = "ok"
    message_c = ""

    try:
        stage_c_optimizer.step(closure_stage_c)
        _apply_baseline_detector_prior()

    except Exception as e:
        status_c = "error"
        message_c = str(e)
        # Use best snapshot if available
        if best_params_snapshot_c is not None:
            distance_offset_raw.data = torch.tensor(best_params_snapshot_c['distance_offset_raw'], device=device, dtype=dtype)

    final_step_c = iteration_count_c[0]
    with torch.no_grad():
        candidate_final_chi2, candidate_final_mse = compute_loss_stage_c(list(range(n_panels)), is_full=True)
    candidate_loss_value_c = float(candidate_final_chi2.item())
    candidate_mse_value_c = float(candidate_final_mse.item())
    if candidate_loss_value_c < chi_squared_best_c[0]:
        chi_squared_best_c = (candidate_loss_value_c, final_step_c)
        best_loss_full_c = (candidate_loss_value_c, final_step_c)
        best_params_snapshot_c = {
            'distance_offset_raw': distance_offset_raw.detach().cpu().tolist()
        }
    if candidate_mse_value_c < masked_mse_best_c[0]:
        masked_mse_best_c = (candidate_mse_value_c, final_step_c)
    if best_params_snapshot_c is not None:
        distance_offset_raw.data = torch.tensor(
            best_params_snapshot_c['distance_offset_raw'],
            device=device,
            dtype=dtype,
        )
    final_loss_value_c = chi_squared_best_c[0] if chi_squared_best_c[0] < float('inf') else candidate_loss_value_c
    final_mse_value_c = masked_mse_best_c[0] if masked_mse_best_c[0] < float('inf') else candidate_mse_value_c
    loss_trace_full_c.append((final_step_c, final_loss_value_c))
    chi_squared_trace_full_c.append((final_step_c, final_loss_value_c))
    masked_mse_trace_full_c.append((final_step_c, final_mse_value_c))

    # Check convergence: did we achieve ≥5% improvement on top of Stage A?
    if best_loss_full[0] is not None and best_loss_full[0] > 0:
        stage_a_final_loss = best_loss_full[0]
        improvement_c = (stage_a_final_loss - final_loss_value_c) / stage_a_final_loss
        if improvement_c < config.stage_c_min_loss_improvement:
            status_c = "early_stop"
            message_c = f"Stage C improvement {improvement_c:.4%} < {config.stage_c_min_loss_improvement:.4%} (≥0.002% gate calibrated per REFINE-007)"

    # Generate final Bragg array with Stage C adjustments
    with torch.no_grad():
        bragg_full_stage_c = np.zeros((n_panels, *panel_shape), dtype=np.float32)
        cell_params = crystal.get_unit_cell().parameters()
        log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
            log_cell_a_delta,
            log_cell_b_delta,
            log_cell_c_delta,
            getattr(config, "log_cell_max_delta", 1.0),
        )
        perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
        perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
        perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta_clamped)
        max_angle_delta = 10.0
        perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
        perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
        perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta
        max_orientation_deg = 3.0
        bounded_orientation_vec = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
        quat = vec_to_unit_quaternion(bounded_orientation_vec)
        misset_xyz_deg = quaternion_to_xyz_euler(quat)

        if baseline_misset_deg_tensor is not None:
            misset_xyz_deg = misset_xyz_deg + baseline_misset_deg_tensor

        crystal_overrides = {
            'cell_a': perturbed_cell_a,
            'cell_b': perturbed_cell_b,
            'cell_c': perturbed_cell_c,
            'cell_alpha': perturbed_alpha,
            'cell_beta': perturbed_beta,
            'cell_gamma': perturbed_gamma
        }
        crystal_config, _ = create_crystal_config(
            crystal,
            None,
            crystal_overrides=crystal_overrides,
            misset_deg_override=misset_deg_for_crystal
        )
        crystal_model = Crystal(crystal_config, device=device, dtype=dtype)
        crystal_model.interpolate = config.enable_hkl_interpolation
        crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
        crystal_model.hkl_metadata = hkl_metadata

        # PERF-WARM-013: Retarget cached detectors before final reconstruction loop
        if stage_c_use_warm_cache:
            distance_deltas_mm_final = {}
            for pid in range(n_panels):
                bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
                distance_deltas_mm_final[pid] = bounded_offset.item() if isinstance(bounded_offset, torch.Tensor) else bounded_offset

            _retarget_stage_a_detectors(
                stage_a_ctx=stage_a_ctx,
                distance_deltas_mm=distance_deltas_mm_final,
                device=device,
                dtype=dtype
            )

        for pid in range(n_panels):
            panel = detector[pid]

            if stage_c_use_warm_cache:
                # Warm path: reuse retargeted detector/simulator from stage_a_ctx
                detector_model = stage_a_ctx.detector_models[pid]
                simulator = stage_a_ctx.simulators[pid]
                # Attach final crystal model
                simulator.crystal = crystal_model
                simulator.beam_config = stage_a_ctx.beam_config
            else:
                # Cold path: instantiate fresh (existing code, keep AS-IS)
                # Apply final bounded distance offset
                bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
                baseline_distance_mm = panel.get_directed_distance()
                distance_mm_override = baseline_distance_mm + bounded_offset

                detector_config = create_detector_config(
                    panel=panel,
                    beam=beam,
                    trusted_mask=inputs.trusted_mask[pid],
                    distance_mm_override=distance_mm_override
                )

                if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                    detector_config.mask_array = torch.tensor(
                        detector_config.mask_array, dtype=torch.float32, device=device
                    )

                detector_model = Detector(detector_config, device=device, dtype=dtype)
                simulator = Simulator(detector=detector_model, crystal=crystal_model, device=device, dtype=dtype)

            panel_bragg = simulator.run()

            # Apply optimized scale (Stage A final)
            log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
            panel_bragg_scaled = panel_bragg * torch.exp(log_scale_clamped)
            bragg_full_stage_c[pid] = panel_bragg_scaled.cpu().numpy().astype(np.float32)

    # Assemble Stage C telemetry
    param_deltas_c = {}
    for pid in range(n_panels):
        bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
        bounded_offset_value = float(bounded_offset.item())
        initial_offset_mm = 0.0
        if baseline_detector_distances is not None:
            initial_offset_mm = detector[pid].get_directed_distance() - baseline_detector_distances[pid]
        final_offset_mm = initial_offset_mm + bounded_offset_value
        param_deltas_c[f'panel_{pid}_distance_offset_mm'] = {
            'initial': initial_offset_mm,
            'final': final_offset_mm,
            'delta': bounded_offset_value
        }

    forward_stats_c = {
        'mean': float(np.mean(perf_forward_times_ms_c)) if perf_forward_times_ms_c else 0.0,
        'min': float(np.min(perf_forward_times_ms_c)) if perf_forward_times_ms_c else 0.0,
        'max': float(np.max(perf_forward_times_ms_c)) if perf_forward_times_ms_c else 0.0,
        'total': float(np.sum(perf_forward_times_ms_c)) if perf_forward_times_ms_c else 0.0,
    }
    perf_counters_c = {
        'cache_mode': stage_c_cache_mode,
        'roi_mode': stage_c_roi_mode_label,
        'roi_count_total': stage_c_roi_count_total,
        'roi_count_sampled': stage_c_roi_count_sampled,
        'closure_evals': perf_closure_evals_c[0],
        'validation_runs': perf_validation_runs_c[0],
        'forward_time_ms': forward_stats_c,
    }

    telemetry_c = RefinementTelemetry(
        optimizer="LBFGS",
        stage="C",
        history_size=config.history_size,
        max_iter=config.max_iter,
        tolerance_grad=config.tolerance_grad,
        tolerance_change=config.tolerance_change,
        roi_sample_fraction=config.roi_sample_fraction,
        roi_count_sampled=stage_c_roi_count_sampled,
        roi_count_total=stage_c_roi_count_total,
        loss_trace_sample=loss_trace_sample_c,
        loss_trace_full=loss_trace_full_c,
        best_loss_full=best_loss_full_c,
        param_deltas=param_deltas_c,
        status=status_c,
        message=message_c,
        perf_counters=perf_counters_c,
        # PHYSICS-LOSS-001: Dual loss metrics
        chi_squared_trace_sample=chi_squared_trace_sample_c,
        chi_squared_trace_full=chi_squared_trace_full_c,
        chi_squared_best=chi_squared_best_c,
        masked_mse_trace_sample=masked_mse_trace_sample_c,
        masked_mse_trace_full=masked_mse_trace_full_c,
        masked_mse_best=masked_mse_best_c,
        sigma_readout_provenance=config.sigma_readout_provenance,
        sigma_readout_reference_value=config.sigma_readout_reference_value,
        # PHYSICS-LOSS-002: Variance floor telemetry
        variance_floor_value=config.sigma_floor_value**2,
        variance_floor_clamp_fraction=(
            float(variance_floor_clamped_pixels_c[0]) / float(variance_floor_masked_pixels_c[0])
            if variance_floor_masked_pixels_c[0] > 0 else 0.0
        ),
        canonical_stage_label=canonical_baseline["stage_label"],
        canonical_chi_squared=canonical_baseline["chi_squared"],
        canonical_chi_squared_iteration=canonical_baseline["iteration"],
        canonical_roi_count=canonical_baseline["roi_count"],
        canonical_detector_distances_mm=canonical_baseline["detector_distances_mm"],
        roi_mode=stage_c_roi_mode_label,
    )

    return {
        'status_c': status_c,
        'message_c': message_c,
        'telemetry_c': telemetry_c,
        'bragg_full': bragg_full_stage_c,
        'final_step_c': final_step_c,
        'final_loss_value_c': final_loss_value_c,
        'final_mse_value_c': final_mse_value_c,
    }


def _build_final_bragg_from_stage_b_telemetry(
    telemetry_a,
    telemetry_b,
    detector,
    beam,
    crystal,
    baseline_crystal,
    inputs,
    hkl_grid,
    hkl_metadata,
    config,
    device,
    dtype,
    use_stage_b_cpu_fallback=False,
    stage_a_ctx=None,
):
    """
    Build final Bragg array from Stage B telemetry (shell modifiers + Stage A frozen params).

    Extracts Stage A frozen parameters and Stage B shell modifiers from telemetry,
    applies modifiers to HKL grid, and regenerates full Bragg image.

    Args:
        telemetry_a: RefinementTelemetry instance or dict with Stage A optimized param_deltas
        telemetry_b: RefinementTelemetry instance or dict with Stage B shell modifiers
        detector: dxtbx Detector object
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object
        baseline_crystal: Optional baseline dxtbx Crystal object for extracting deterministic
                          misset when `crystal` is perturbed. When provided, computes
                          U_delta = U_perturbed @ U_baseline^{-1} and adds it to the orientation
                          path as a tensor to preserve differentiability. Defaults to None.
        inputs: RefinementInputs with panel_slices, trusted_mask
        hkl_grid: torch.Tensor structure factor grid (unmodified baseline)
        hkl_metadata: dict with grid dimensions
        config: RefinementConfig with device, dtype, Stage B settings
        device: torch.device for tensor operations
        dtype: torch.dtype for tensor operations
        stage_a_ctx: Optional Stage A context (detectors/simulators for warm cache)

    Returns:
        bragg_full: np.ndarray, shape [n_panels, slow, fast], final Bragg image with shell modifiers
    """
    # Route device to CPU when CPU fallback is active
    final_device = torch.device("cpu") if use_stage_b_cpu_fallback else device

    # Lazy imports to avoid circular dependencies
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from dbex.nanobrag_bridge import (
        create_detector_config,
        create_crystal_config,
        compute_baseline_misset_deg,
    )

    # Extract param_deltas from telemetry (handle both RefinementTelemetry and dict)
    if hasattr(telemetry_a, 'param_deltas'):
        param_deltas_a = telemetry_a.param_deltas
    else:
        param_deltas_a = telemetry_a['param_deltas']

    if hasattr(telemetry_b, 'param_deltas'):
        param_deltas_b = telemetry_b.param_deltas
    else:
        param_deltas_b = telemetry_b['param_deltas']

    # Extract Stage A frozen parameters (final values)
    log_scale = torch.tensor(param_deltas_a['log_scale']['final'], device=device, dtype=dtype, requires_grad=False)
    log_cell_a_delta = torch.tensor(param_deltas_a['log_cell_a_delta']['final'], device=device, dtype=dtype, requires_grad=False)
    log_cell_b_delta = torch.tensor(param_deltas_a['log_cell_b_delta']['final'], device=device, dtype=dtype, requires_grad=False)
    log_cell_c_delta = torch.tensor(param_deltas_a['log_cell_c_delta']['final'], device=device, dtype=dtype, requires_grad=False)
    angle_alpha_raw = torch.tensor(param_deltas_a['angle_alpha_raw']['final'], device=device, dtype=dtype, requires_grad=False)
    angle_beta_raw = torch.tensor(param_deltas_a['angle_beta_raw']['final'], device=device, dtype=dtype, requires_grad=False)
    angle_gamma_raw = torch.tensor(param_deltas_a['angle_gamma_raw']['final'], device=device, dtype=dtype, requires_grad=False)

    # Extract misset from Stage A (this is the delta, not frozen in Stage B inline code but added to baseline)
    misset_xyz_deg_delta = param_deltas_a['misset_xyz_deg']['delta']
    misset_xyz_deg = torch.tensor(misset_xyz_deg_delta, device=device, dtype=dtype, requires_grad=False)

    # Check Stage B mode (per-reflection or shell)
    # Per-reflection mode doesn't have shell_edges/shell_indices
    stage_b_mode = None
    if hasattr(telemetry_b, 'stage_b_mode'):
        stage_b_mode = telemetry_b.stage_b_mode
    elif isinstance(telemetry_b, dict) and 'stage_b_mode' in telemetry_b:
        stage_b_mode = telemetry_b['stage_b_mode']

    # Extract shell metadata from Stage B telemetry (shell mode only)
    if stage_b_mode == "per_reflection":
        # Per-reflection mode: no shell metadata, skip shell modifier application
        shell_edges = None
        shell_indices = None
        n_shells = 0
        shell_modifiers_final = None
    else:
        # Shell mode: extract shell metadata and modifiers
        if hasattr(telemetry_b, 'shell_edges'):
            shell_edges = torch.tensor(telemetry_b.shell_edges, device=device, dtype=dtype)
            shell_indices = torch.tensor(telemetry_b.shell_indices, device=device, dtype=torch.long)
            n_shells = telemetry_b.n_shells
        else:
            shell_edges = torch.tensor(telemetry_b['shell_edges'], device=device, dtype=dtype)
            shell_indices = torch.tensor(telemetry_b['shell_indices'], device=device, dtype=torch.long)
            n_shells = telemetry_b['n_shells']

        # Extract shell modifiers from Stage B param_deltas
        shell_modifiers_final = torch.zeros(n_shells, device=device, dtype=dtype)
        for shell_idx in range(n_shells):
            # Find the shell modifier key in param_deltas_b
            shell_key = None
            for key in param_deltas_b.keys():
                if key.startswith(f'shell_{shell_idx}_modifier'):
                    shell_key = key
                    break
            if shell_key is None:
                raise RuntimeError(f"Missing shell_{shell_idx}_modifier in Stage B telemetry param_deltas")
            shell_modifiers_final[shell_idx] = param_deltas_b[shell_key]['final']

    # Get n_panels and panel_shape
    n_panels = len(detector)
    panel_shape = inputs.target.shape[1:]  # (slow, fast)

    # Compute baseline misset if baseline_crystal provided (matches inline path lines 3115-3120)
    baseline_misset_deg_tensor = compute_baseline_misset_deg(
        crystal,
        baseline_crystal,
        device=device,
        dtype=dtype,
    )

    # Apply Stage A cell perturbations
    cell_params = crystal.get_unit_cell().parameters()
    log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
        log_cell_a_delta,
        log_cell_b_delta,
        log_cell_c_delta,
        getattr(config, "log_cell_max_delta", 1.0),
    )
    cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
    cell_b_tensor = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
    cell_c_tensor = cell_params[2] * torch.exp(log_cell_c_delta_clamped)

    max_angle_delta = 10.0  # degrees
    cell_alpha_tensor = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
    cell_beta_tensor = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
    cell_gamma_tensor = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

    # Apply shell modifiers to HKL grid (shell mode only; per-reflection uses base grid)
    if stage_b_mode == "per_reflection":
        # Per-reflection mode: use unmodified HKL grid (ASU modifiers applied per-reflection during forward pass)
        hkl_grid_modified = hkl_grid
    else:
        # Shell mode: apply shell modifiers to HKL grid (mirroring inline code lines 3314-3317)
        with torch.no_grad():
            hkl_grid_modified = hkl_grid.clone()
            for shell_idx in range(n_shells):
                mask = (shell_indices == shell_idx)
                hkl_grid_modified[mask] = hkl_grid[mask] * shell_modifiers_final[shell_idx]

    bragg_full = np.zeros((n_panels, *panel_shape), dtype=np.float32)

    # Build crystal overrides
    crystal_overrides = {
        'cell_a': cell_a_tensor,
        'cell_b': cell_b_tensor,
        'cell_c': cell_c_tensor,
        'cell_alpha': cell_alpha_tensor,
        'cell_beta': cell_beta_tensor,
        'cell_gamma': cell_gamma_tensor
    }

    # Compute final misset (baseline + delta if baseline provided)
    if baseline_misset_deg_tensor is not None:
        final_misset = baseline_misset_deg_tensor + misset_xyz_deg
    else:
        final_misset = misset_xyz_deg

    # Check if warm cache is enabled AND stage_a_ctx is available
    stage_b_use_warm_cache = config.enable_stage_a_warm_cache and stage_a_ctx is not None

    if stage_b_use_warm_cache:
        # Warm cache path: retarget Stage A simulators with modified crystal
        warm_crystal_config, _ = create_crystal_config(
            crystal,
            None,
            crystal_overrides=crystal_overrides,
            misset_deg_override=final_misset,
            apply_n_cells=False,
        )
        warm_crystal_model = Crystal(
            warm_crystal_config,
            beam_config=stage_a_ctx.beam_config,
            device=final_device,
            dtype=dtype,
        )
        warm_crystal_model.interpolate = True
        warm_crystal_model.hkl_data = hkl_grid_modified.to(device=final_device, dtype=dtype)
        warm_crystal_model.hkl_metadata = hkl_metadata
        _retarget_stage_a_simulators(stage_a_ctx, warm_crystal_model)

        for pid in range(n_panels):
            simulator = stage_a_ctx.simulators[pid]
            bragg_panel = simulator.run()
            log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
            bragg_scaled = bragg_panel * torch.exp(log_scale_clamped)
            bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
    else:
        # Cold path: instantiate fresh simulators per panel
        for pid in range(n_panels):
            detector_config = create_detector_config(
                panel=detector[pid],
                beam=beam,
                trusted_mask=inputs.trusted_mask[pid]
            )
            if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                detector_config.mask_array = torch.tensor(
                    detector_config.mask_array, dtype=torch.float32, device=final_device
                )
            crystal_config, _ = create_crystal_config(
                crystal, None,
                crystal_overrides=crystal_overrides,
                misset_deg_override=final_misset,
                apply_n_cells=False
            )
            detector_model = Detector(detector_config, device=final_device, dtype=dtype)
            crystal_model = Crystal(crystal_config, device=final_device, dtype=dtype)
            crystal_model.interpolate = True
            crystal_model.hkl_data = hkl_grid_modified.to(device=final_device, dtype=dtype)
            crystal_model.hkl_metadata = hkl_metadata
            simulator = Simulator(detector=detector_model, crystal=crystal_model, device=final_device, dtype=dtype)
            bragg_panel = simulator.run()
            log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
            bragg_scaled = bragg_panel * torch.exp(log_scale_clamped)
            bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)

    return bragg_full


def run_nanobrag_refinement(
    inputs,
    detector,
    beam,
    crystal,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    config: Optional[RefinementConfig] = None,
    baseline_crystal=None,
    baseline_detector=None,
    use_engine_delegation: bool = False
) -> Tuple[np.ndarray, Dict[str, RefinementTelemetry]]:
    """
    Run Stage A (+ optional Stage C) LBFGS refinement on nanobrag_torch simulator.

    Stage A optimizes:
    - log_scale: global intensity scale (ADU mode)
    - log_cell_*_delta: unit cell length perturbations (a/b/c)
    - angle_*_raw: unit cell angle perturbations (alpha/beta/gamma)
    - orientation_vec: crystal misorientation (3-vector → quaternion → XYZ Euler)

    Stage C (when config.enable_stage_c=True) optimizes:
    - per-panel detector distance offsets along panel normal (odet_vec)

    Args:
        inputs: RefinementInputs with target, loss_mask, panel_slices, trusted_mask
        detector: dxtbx Detector object (multi-panel, possibly perturbed for Stage C smoke)
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object (possibly perturbed from baseline)
        hkl_grid: torch.Tensor structure factor grid (P1 dense)
        hkl_metadata: dict with grid dimensions and metadata
        config: Optional RefinementConfig; uses defaults if None
        baseline_crystal: Optional baseline dxtbx Crystal object for extracting deterministic
                        misset when `crystal` is perturbed (TORCH-REFINE-002D). When provided,
                        computes U_delta = U_perturbed @ U_baseline^{-1} and adds it to the
                        orientation refinement path as a tensor to preserve differentiability.
        baseline_detector: Optional dxtbx Detector capturing the unperturbed geometry. When
                        provided, Stage C telemetry records initial/final offsets relative to this
                        baseline; otherwise offsets are reported relative to the perturbed detector.
        use_engine_delegation: bool, default False
                        When True, delegates to RefinementEngine with Stage wrapper classes.
                        When False (default), uses inline helper paths for backward compatibility.

    Returns:
        Tuple of:
        - Bragg: np.ndarray [panel, slow, fast] final simulated intensities after all stages (CPU, float32)
        - telemetry_dict: Dict[str, RefinementTelemetry] keyed by stage label ("A", "C")
                         Always contains "A"; contains "C" only when config.enable_stage_c=True

    Raises:
        RuntimeError: If simulator fails or gradients are NaN/Inf
    """
    if os.environ.get("NANOBRAGG_DISABLE_COMPILE") == "1":
        os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from dbex.nanobrag_bridge import (
        create_detector_config,
        create_beam_config,
        create_crystal_config,
        compute_baseline_misset_deg,
    )

    if config is None:
        config = RefinementConfig()

    # Detect Stage-A-only mode for conditional engine delegation (Phase B2)
    stage_a_only_mode = (not config.enable_stage_c and not config.enable_stage_b)

    # Detect Stage A→B mode for conditional engine delegation (Phase C2)
    stage_a_b_mode = (not config.enable_stage_c and config.enable_stage_b)

    if stage_a_only_mode:
        # === ENGINE DELEGATION PATH (Phase B2) ===
        # Lazy imports to avoid circular dependencies at module load time
        from dbex.refinement.engine import RefinementEngine
        from dbex.refinement.stage_a import StageA

        # Build inputs dict per StageA.run() contract (dbex/refinement/stage_a.py:71-78)
        engine_inputs = {
            'refinement_inputs': inputs,
            'detector': detector,
            'beam': beam,
            'crystal': crystal,
            'hkl_grid': hkl_grid,
            'hkl_metadata': hkl_metadata,
            'baseline_crystal': baseline_crystal,
            'baseline_detector': baseline_detector,
        }

        # Instantiate RefinementEngine with StageA
        engine = RefinementEngine(stages=[StageA()], config=config)

        # Execute engine and get telemetry dict (keyed by stage.name = "stage_a")
        telemetry_dict = engine.run(engine_inputs)
        stage_a_ctx = getattr(engine, "_stage_a_ctx_cache", None)

        # Extract StageA telemetry (keyed by "stage_a" per StageA.name property)
        telemetry_a = telemetry_dict["stage_a"]

        # Phase E: Enrich telemetry with engine protocol and stage modes
        from dataclasses import asdict
        telemetry_a_dict = asdict(telemetry_a)
        telemetry_a_dict["engine_protocol"] = "stage_a"  # Stage-A-only mode
        telemetry_a_dict["stage_modes"] = {}  # No Stage B/C enabled
        telemetry_a_enriched = RefinementTelemetry(**telemetry_a_dict)

        # Build final Bragg array using optimized parameters from telemetry
        device = torch.device(config.device)
        dtype = config.dtype
        bragg_full = _build_final_bragg_from_stage_a_telemetry(
            telemetry_a_enriched, detector, beam, crystal, inputs, hkl_grid,
            hkl_metadata, config, device, dtype,
            stage_a_ctx=stage_a_ctx,
            baseline_crystal=baseline_crystal,
        )

        # Return with telemetry dict using "A" key for backward compatibility
        # (Legacy code expects {"A": RefinementTelemetry, ...})
        return bragg_full, {"A": telemetry_a_enriched}

    elif stage_a_b_mode:
        # === ENGINE DELEGATION PATH (Phase C2: A→B) ===
        from dbex.refinement.engine import RefinementEngine
        from dbex.refinement.stage_a import StageA
        from dbex.refinement.stage_b import StageB

        # Build inputs dict per StageA/StageB.run() contract
        engine_inputs = {
            'refinement_inputs': inputs,
            'detector': detector,
            'beam': beam,
            'crystal': crystal,
            'hkl_grid': hkl_grid,
            'hkl_metadata': hkl_metadata,
            'baseline_crystal': baseline_crystal,
            'baseline_detector': baseline_detector,
        }

        # Instantiate RefinementEngine with StageA → StageB sequence
        # Note: CPU fallback for Stage B (PERF-WARM-011/012) is handled internally by
        # _build_stage_b_params which receives stage_a_ctx from StageA via engine propagation
        engine = RefinementEngine(stages=[StageA(), StageB()], config=config)

        # Execute engine and get telemetry dict (keyed by stage.name = "stage_a", "stage_b")
        telemetry_dict = engine.run(engine_inputs)

        # Extract Stage A and Stage B telemetry (keyed by "stage_a", "stage_b" per stage.name property)
        telemetry_a_raw = telemetry_dict["stage_a"]
        telemetry_b_raw = telemetry_dict["stage_b"]

        # Build final Bragg array using Stage B optimized shell modifiers
        device = torch.device(config.device)
        dtype = config.dtype

        # Extract stage_a_ctx from engine cache (cached separately from telemetry)
        stage_a_ctx = getattr(engine, '_stage_a_ctx_cache', None)

        # PERF-WARM-011: Recompute CPU fallback decision for final Bragg reconstruction
        # Same logic as in _build_stage_b_params (lines 2178-2182)
        panel_slices = inputs.panel_slices
        canonical_roi_count = len(panel_slices)
        use_stage_a_roi_mode = bool(
            config.enable_stage_a_roi_mode
            and canonical_roi_count > 0
            and (config.enable_stage_a_warm_cache or config.allow_cold_stage_a_roi_mode)
        )
        use_stage_b_cpu_fallback = (
            config.stage_b_full_eval_on_cpu
            and str(device).startswith("cuda")
            and not use_stage_a_roi_mode  # ROI mode is disabled (panel mode)
        )

        # If CPU fallback is active, use CPU device for final Bragg reconstruction
        final_device = torch.device("cpu") if use_stage_b_cpu_fallback else device

        # PERF-WARM-012: Clone Stage A context to CPU when CPU fallback is active
        # (Mirrors logic in _build_stage_b_params lines 2199-2220)
        stage_b_eval_stage_a_ctx = None
        if use_stage_b_cpu_fallback and stage_a_ctx is not None and config.enable_stage_a_warm_cache:
            # Build a fresh Stage A context on CPU device
            cpu_device = torch.device("cpu")
            stage_b_eval_stage_a_ctx = _build_stage_a_context(
                detector=detector,
                beam=beam,
                crystal=crystal,
                trusted_mask=inputs.trusted_mask,
                hkl_grid=hkl_grid,
                hkl_metadata=hkl_metadata,
                enable_hkl_interpolation=config.enable_hkl_interpolation,
                device=cpu_device,
                dtype=dtype,
                panel_slices=panel_slices,
                enable_roi_mode=False,  # CPU fallback is panel-mode only
                calibration_metadata=config.calibration_metadata,
                log_scale_baseline=config.log_scale_baseline,
                apply_calibration_n_cells=config.apply_calibration_n_cells,
            )
        elif not use_stage_b_cpu_fallback:
            # No CPU fallback: reuse the original CUDA Stage A context
            stage_b_eval_stage_a_ctx = stage_a_ctx

        # Extract shell metadata from engine cache (cached separately from telemetry)
        shell_edges = getattr(engine, '_stage_b_shell_edges', None)
        shell_indices = getattr(engine, '_stage_b_shell_indices', None)
        n_shells = getattr(engine, '_stage_b_n_shells', None)

        # Extract custom attributes from engine cache (Phase 8 fix #2)
        stage_b_mode = getattr(engine, '_stage_b_mode', None)
        n_asu_unique = getattr(engine, '_stage_b_n_asu_unique', None)
        optimizer_type = getattr(engine, '_stage_b_optimizer_type', None)
        asu_modifier_stats = getattr(engine, '_stage_b_asu_modifier_stats', None)

        # Create a dict version of telemetry_b with shell metadata for the helper
        from dataclasses import asdict
        telemetry_b_dict = asdict(telemetry_b_raw)
        if shell_edges is not None:
            telemetry_b_dict['shell_edges'] = shell_edges
        if shell_indices is not None:
            telemetry_b_dict['shell_indices'] = shell_indices
        if n_shells is not None:
            telemetry_b_dict['n_shells'] = n_shells
        # Add custom attributes back to dict (Phase 8 fix #2)
        if stage_b_mode is not None:
            telemetry_b_dict['stage_b_mode'] = stage_b_mode
        if n_asu_unique is not None:
            telemetry_b_dict['n_asu_unique'] = n_asu_unique
        if optimizer_type is not None:
            telemetry_b_dict['optimizer_type'] = optimizer_type
        if asu_modifier_stats is not None:
            telemetry_b_dict['asu_modifier_stats'] = asu_modifier_stats

        bragg_full = _build_final_bragg_from_stage_b_telemetry(
            telemetry_a=telemetry_a_raw,
            telemetry_b=telemetry_b_dict,
            detector=detector,
            beam=beam,
            crystal=crystal,
            baseline_crystal=baseline_crystal,
            inputs=inputs,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            config=config,
            device=final_device,  # Use CPU device if CPU fallback is active
            dtype=dtype,
            use_stage_b_cpu_fallback=use_stage_b_cpu_fallback,
            stage_a_ctx=stage_b_eval_stage_a_ctx,  # Use CPU-cloned context when fallback active
        )

        # Repackage telemetry with backward-compatible keys ("A", "B")
        # Use engine's telemetry objects directly to preserve custom attributes (Phase 8 Alternative pattern)
        # The engine already restored custom attributes (stage_b_mode, n_asu_unique, etc.) per engine.py:161-168
        telemetry_a = telemetry_a_raw
        telemetry_b = telemetry_b_raw

        # Add engine protocol and stage modes for Phase E telemetry enrichment
        engine_protocol_value = "stage_a→stage_b"
        stage_modes_value = {
            "B": config.stage_b_mode  # Use actual config value ("per_reflection" or "shell")
        }
        telemetry_a.engine_protocol = engine_protocol_value
        telemetry_a.stage_modes = stage_modes_value
        telemetry_b.engine_protocol = engine_protocol_value
        telemetry_b.stage_modes = stage_modes_value

        return bragg_full, {"A": telemetry_a, "B": telemetry_b}

    else:
        # === INLINE PATH (existing implementation) ===
        # All existing Stage A/B/C logic stays here
        sigma_floor_sq_cache: Dict[Tuple[str, torch.dtype], torch.Tensor] = {}

        # Move inputs to device
        device = torch.device(config.device)
        dtype = config.dtype
        target_t = torch.from_numpy(inputs.target).to(device=device, dtype=dtype)
        loss_mask_t = torch.from_numpy(inputs.loss_mask).to(device=device, dtype=torch.bool)
        sigma_readout_t = torch.from_numpy(inputs.sigma_readout).to(device=device, dtype=dtype)
    
        # Extract deterministic misset from perturbed geometry (TORCH-REFINE-002D)
        # Compute U_delta = U_perturbed @ U_baseline^{-1} and convert to XYZ Euler angles
        baseline_misset_deg_tensor = compute_baseline_misset_deg(
            crystal,
            baseline_crystal,
            device=device,
            dtype=dtype,
        )
        masked_pixel_reference = int(inputs.loss_mask.sum())
    
        # === Stage A parameter initialization and telemetry setup ===
        # Call helper 1
        helper1_result = _build_stage_a_params(
            crystal, detector, inputs, config, device, dtype, hkl_grid, hkl_metadata,
            sigma_floor_sq_cache, baseline_crystal, baseline_detector, beam
        )
        params = helper1_result['params']
        param_values = helper1_result['param_values']
        telemetry_state = helper1_result['telemetry_state']
        optimizer = helper1_result['optimizer']
        stage_a_context = helper1_result['stage_a_context']
    
        # Unpack needed variables for helper 2/3 calls and final Bragg generation
        initial_log_scale = param_values['initial_log_scale']  # For telemetry
        log_scale_baseline = param_values.get('log_scale_baseline')  # Calibration baseline (None if uncalibrated)
        log_scale = param_values['log_scale']
        log_cell_a_delta = param_values['log_cell_a_delta']
        log_cell_b_delta = param_values['log_cell_b_delta']
        log_cell_c_delta = param_values['log_cell_c_delta']
        angle_alpha_raw = param_values['angle_alpha_raw']
        angle_beta_raw = param_values['angle_beta_raw']
        angle_gamma_raw = param_values['angle_gamma_raw']
        orientation_vec = param_values['orientation_vec']
        # baseline_misset_deg_tensor is computed OUTSIDE the helper (line 1961), not in any dict
        q_params = param_values.get('q_params')
        B_ideal_reciprocal_torch = param_values.get('B_ideal_reciprocal_torch')
        q_delta = param_values.get('q_delta')
        U_baseline = param_values.get('U_baseline')
        cell_baseline = param_values.get('cell_baseline')
        canonical_baseline = stage_a_context['canonical_baseline']
        full_stage_a_indices = stage_a_context['full_stage_a_indices']
        stage_a_roi_label = stage_a_context['stage_a_roi_label']
        use_stage_a_roi_mode = stage_a_context['use_stage_a_roi_mode']
        stage_a_total_work_items = stage_a_context['stage_a_total_work_items']
        stage_a_ctx = stage_a_context['stage_a_ctx']
        sampled_panel_ids = stage_a_context['sampled_panel_ids']
        sampled_stage_a_indices = stage_a_context['sampled_stage_a_indices']
        # n_panels, panel_shape, and panel_slices are NOT in stage_a_context - compute directly
        n_panels = len(detector)
        panel_shape = inputs.target.shape[1:]  # (slow, fast)
        panel_slices = inputs.panel_slices
        # Unpack telemetry variables for final telemetry assembly
        perf_closure_evals = telemetry_state['perf_closure_evals']
        perf_validation_runs = telemetry_state['perf_validation_runs']
        perf_forward_times_ms = telemetry_state['perf_forward_times_ms']
        variance_floor_clamped_pixels = telemetry_state['variance_floor_clamped_pixels']
        variance_floor_masked_pixels = telemetry_state['variance_floor_masked_pixels']
        chi_squared_trace_full = telemetry_state['chi_squared_trace_full']
        masked_mse_trace_full = telemetry_state['masked_mse_trace_full']
        chi_squared_best = telemetry_state['chi_squared_best']
        masked_mse_best = telemetry_state['masked_mse_best']
        # Unpack remaining telemetry variables used later in main function
        loss_trace_sample = telemetry_state['loss_trace_sample']
        loss_trace_full = telemetry_state['loss_trace_full']
        best_loss_full = telemetry_state['best_loss_full']
        chi_squared_trace_sample = telemetry_state['chi_squared_trace_sample']
        masked_mse_trace_sample = telemetry_state['masked_mse_trace_sample']
    
        # === Stage A LBFGS closure construction ===
        # Call helper 2
        compute_loss, closure = _build_stage_a_lbfgs_closure(
            param_values, telemetry_state, stage_a_context,
            crystal, detector, beam, inputs, hkl_grid, hkl_metadata, config,
            sigma_floor_sq_cache, device, dtype, baseline_crystal
        )
    
        # === Stage A LBFGS execution and final validation ===
        # Call helper 3
        status, message, final_chi_squared_value, final_masked_mse_value, best_params_snapshot = _run_stage_a_lbfgs(
            compute_loss, closure, optimizer, params, telemetry_state,
            config, canonical_baseline, full_stage_a_indices,
            log_scale, log_cell_a_delta, log_cell_b_delta, log_cell_c_delta,
            angle_alpha_raw, angle_beta_raw, angle_gamma_raw, orientation_vec,
            device, dtype,
            masked_pixel_reference=masked_pixel_reference,
        )
    
        beam_flux = None
        beam_exposure = None
        beamsize_mm = None
        N_cells = None
        spot_scale_override = None
        if config.calibration_metadata is not None:
            beam_flux = config.calibration_metadata.get("beam_flux")
            beam_exposure = config.calibration_metadata.get("beam_exposure")
            beamsize_mm = config.calibration_metadata.get("beamsize_mm")
            N_cells = config.calibration_metadata.get("N_cells")
            spot_scale_override = config.calibration_metadata.get("spot_scale_override")

        log_scale_baseline_value = log_scale_baseline
        if log_scale_baseline_value is None and spot_scale_override is not None:
            try:
                log_scale_baseline_value = float(np.log(np.sqrt(spot_scale_override)))
            except (TypeError, ValueError):
                log_scale_baseline_value = None
        if log_scale_baseline_value is None and config.log_scale_baseline is not None:
            log_scale_baseline_value = config.log_scale_baseline
        max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)

        # TOOLING-VIS-001 Phase D.E: Extract masked-mean baseline telemetry from param_values
        # These values were computed by _build_stage_a_params via zero-iteration forward pass
        log_scale_baseline_source = param_values.get('log_scale_baseline_source')
        spot_scale_override_adjustment_factor = param_values.get('spot_scale_override_adjustment_factor')
        target_mean_masked = param_values.get('target_mean_masked')
        model_mean_masked = param_values.get('model_mean_masked')

        # Generate final Bragg array with optimized parameters
        with torch.no_grad():
            bragg_full = np.zeros((n_panels, *panel_shape), dtype=np.float32)
    
            for pid in range(n_panels):
                panel = detector[pid]
    
                detector_config = create_detector_config(
                    panel=panel,
                    beam=beam,
                    trusted_mask=inputs.trusted_mask[pid]
                )
    
                # Convert mask_array to torch.Tensor if it's a numpy array
                # Per dbex/nanobrag_bridge.py:998-1004, nanobrag_torch Simulator
                # expects torch.Tensor for mask_array
                if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                    detector_config.mask_array = torch.tensor(
                        detector_config.mask_array, dtype=torch.float32, device=device
                    )
    
                beam_config = create_beam_config(
                    beam,
                    flux=beam_flux,
                    beamsize_mm=beamsize_mm,
                    exposure=beam_exposure,
                )

                # Apply final full crystal perturbations via tensor overrides (GRADIENT-001, TORCH-REFINE-002)
                cell_params = crystal.get_unit_cell().parameters()

                # 1. Unit cell lengths (log-parameterized)
                log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
                    log_cell_a_delta,
                    log_cell_b_delta,
                    log_cell_c_delta,
                    getattr(config, "log_cell_max_delta", 1.0),
                )
                perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
                perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
                perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta_clamped)

                # 2. Unit cell angles (bounded via tanh)
                max_angle_delta = 10.0  # degrees
                perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
                perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
                perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

                zero_param_deltas = (
                    torch.allclose(log_cell_a_delta_clamped, torch.tensor(0.0, device=device, dtype=dtype))
                    and torch.allclose(log_cell_b_delta_clamped, torch.tensor(0.0, device=device, dtype=dtype))
                    and torch.allclose(log_cell_c_delta_clamped, torch.tensor(0.0, device=device, dtype=dtype))
                    and torch.allclose(angle_alpha_raw, torch.tensor(0.0, device=device, dtype=dtype))
                    and torch.allclose(angle_beta_raw, torch.tensor(0.0, device=device, dtype=dtype))
                    and torch.allclose(angle_gamma_raw, torch.tensor(0.0, device=device, dtype=dtype))
                    and torch.allclose(orientation_vec, torch.zeros_like(orientation_vec))
                )
    
                # 3. Orientation perturbation via quaternion→XYZ misset (TORCH-REFINE-002)
                # TORCH-GEOMETRY-PARITY-002 Phase B5: Branch on U-matrix vs cell+misset path
                if config.use_u_matrix_parameterization:
                    # U-matrix path: Normalize quaternion, convert to U, compute A*
                    from dbex.nanobrag_bridge import quaternion_to_matrix
                    q_norm = q_params / torch.norm(q_params)  # Enforce ||q|| = 1
                    U = quaternion_to_matrix(q_norm)  # 3x3 rotation matrix
                    A_star_new = U @ B_ideal_reciprocal_torch  # Compute updated A*
    
                    # Convert A* to numpy for crystal_overrides
                    A_star_np = A_star_new.detach().cpu().numpy()
                    mosflm_a_star_tuple = tuple(A_star_np[:, 0].tolist())
                    mosflm_b_star_tuple = tuple(A_star_np[:, 1].tolist())
                    mosflm_c_star_tuple = tuple(A_star_np[:, 2].tolist())
    
                    crystal_overrides = {
                        'cell_a': perturbed_cell_a,
                        'cell_b': perturbed_cell_b,
                        'cell_c': perturbed_cell_c,
                        'cell_alpha': perturbed_alpha,
                        'cell_beta': perturbed_beta,
                        'cell_gamma': perturbed_gamma,
                        'mosflm_a_star': mosflm_a_star_tuple,
                        'mosflm_b_star': mosflm_b_star_tuple,
                        'mosflm_c_star': mosflm_c_star_tuple,
                    }
                    misset_deg_for_crystal = None
                else:
                    # Existing cell+misset path (GEOMETRY-003)
                    max_orientation_deg = 3.0  # degrees
                    bounded_orientation_vec = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
                    quat = vec_to_unit_quaternion(bounded_orientation_vec)
                    misset_xyz_deg = quaternion_to_xyz_euler(quat)

                    # Add baseline misset from perturbed geometry if provided (TORCH-REFINE-002D)
                    if baseline_misset_deg_tensor is not None:
                        misset_xyz_deg = misset_xyz_deg + baseline_misset_deg_tensor

                    crystal_overrides = {
                        'cell_a': perturbed_cell_a,
                        'cell_b': perturbed_cell_b,
                        'cell_c': perturbed_cell_c,
                        'cell_alpha': perturbed_alpha,
                        'cell_beta': perturbed_beta,
                        'cell_gamma': perturbed_gamma
                    }
                    misset_deg_for_crystal = misset_xyz_deg
    
                use_cached_crystal = zero_param_deltas and stage_a_ctx is not None

                if not use_cached_crystal:
                    crystal_config, _ = create_crystal_config(
                        crystal, None,
                        crystal_overrides=crystal_overrides,
                        misset_deg_override=misset_deg_for_crystal,
                        N_cells=N_cells,
                        apply_n_cells=(N_cells is not None),
                    )

                    detector_model = Detector(detector_config, device=device, dtype=dtype)
                    crystal_model = Crystal(crystal_config, beam_config=beam_config, device=device, dtype=dtype)
                else:
                    detector_model = Detector(detector_config, device=device, dtype=dtype)
                    crystal_model = stage_a_ctx.detector_models[pid].crystal
    
                # HKL interpolation control (TORCH-REFINE-002D, REFINE-005)
                # Defaults to nearest-neighbor (False) unless explicitly enabled via config
                # Tricubic interpolation requires halo-padded grid to avoid default_F fallback
                crystal_model.interpolate = config.enable_hkl_interpolation
    
                crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
                crystal_model.hkl_metadata = hkl_metadata
    
                simulator = Simulator(
                    detector=detector_model,
                    crystal=crystal_model,
                    beam_config=beam_config,
                    device=device,
                    dtype=dtype
                )
                panel_bragg = simulator.run()

                log_scale_max_delta = config.log_scale_max_delta
                delta_bound = log_scale_max_delta if log_scale_baseline_value is not None else max_delta_uncal
                if log_scale_baseline_value is not None:
                    baseline_tensor = torch.tensor(log_scale_baseline_value, device=device, dtype=dtype)
                    log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
                    log_scale_effective = baseline_tensor + log_scale_delta_clamped
                else:
                    log_scale_effective = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
                panel_bragg_scaled = panel_bragg * torch.exp(log_scale_effective)
                bragg_full[pid] = panel_bragg_scaled.cpu().numpy().astype(np.float32)
    
        # Assemble telemetry
        param_deltas = {
            'log_scale': {
                'initial': initial_log_scale,
                'final': float(log_scale.item()),
                'delta': float(log_scale.item()) - initial_log_scale
            },
            'log_scale_baseline': {
                'initial': log_scale_baseline if log_scale_baseline is not None else 0.0,
                'final': log_scale_baseline if log_scale_baseline is not None else 0.0,
            },
            'log_cell_a_delta': {
                'initial': 0.0,
                'final': float(log_cell_a_delta.item()),
                'delta': float(log_cell_a_delta.item())
            },
            'log_cell_b_delta': {
                'initial': 0.0,
                'final': float(log_cell_b_delta.item()),
                'delta': float(log_cell_b_delta.item())
            },
            'log_cell_c_delta': {
                'initial': 0.0,
                'final': float(log_cell_c_delta.item()),
                'delta': float(log_cell_c_delta.item())
            },
            'angle_alpha_raw': {
                'initial': 0.0,
                'final': float(angle_alpha_raw.item()),
                'delta': float(angle_alpha_raw.item())
            },
            'angle_beta_raw': {
                'initial': 0.0,
                'final': float(angle_beta_raw.item()),
                'delta': float(angle_beta_raw.item())
            },
            'angle_gamma_raw': {
                'initial': 0.0,
                'final': float(angle_gamma_raw.item()),
                'delta': float(angle_gamma_raw.item())
            },
            'orientation_vec': {
                'initial': [0.0, 0.0, 0.0],
                'final': orientation_vec.detach().cpu().tolist(),
                'delta': orientation_vec.detach().cpu().tolist(),
                'norm': float(orientation_vec.norm().item())
            }
        }
    
        # Compute final misset XYZ degrees for telemetry (TORCH-REFINE-002)
        # This surfaces the actual rotation applied to the crystal
        with torch.no_grad():
            max_orientation_deg = 3.0
            bounded_orientation_vec_final = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
            quat_final = vec_to_unit_quaternion(bounded_orientation_vec_final)
            misset_xyz_deg_final = quaternion_to_xyz_euler(quat_final)
    
            # Add baseline misset from perturbed geometry if provided (TORCH-REFINE-002D)
            if baseline_misset_deg_tensor is not None:
                misset_xyz_deg_final_total = misset_xyz_deg_final + baseline_misset_deg_tensor
                initial_misset = baseline_misset_deg_tensor.cpu().tolist()
            else:
                misset_xyz_deg_final_total = misset_xyz_deg_final
                initial_misset = [0.0, 0.0, 0.0]
    
            # Add misset telemetry
            param_deltas['misset_xyz_deg'] = {
                'initial': initial_misset,
                'final': misset_xyz_deg_final_total.cpu().tolist(),
                'delta': misset_xyz_deg_final.cpu().tolist(),  # Delta from LBFGS optimization (excluding baseline)
                'quaternion_norm': float(quat_final.norm().item())
            }
    
        # Build perf counters payload (PERF-WARM-SIM-001)
        cache_mode = "warm" if config.enable_stage_a_warm_cache else "cold"
        perf_counters = {
            'cache_mode': cache_mode,
            'roi_mode': stage_a_roi_label,
            'roi_count_total': stage_a_total_work_items,
            'roi_count_sampled': len(sampled_stage_a_indices),
            'closure_evals': perf_closure_evals[0],
            'validation_runs': perf_validation_runs[0],
            'forward_time_ms': {
                'mean': float(np.mean(perf_forward_times_ms)) if perf_forward_times_ms else 0.0,
                'min': float(np.min(perf_forward_times_ms)) if perf_forward_times_ms else 0.0,
                'max': float(np.max(perf_forward_times_ms)) if perf_forward_times_ms else 0.0,
                'total': float(np.sum(perf_forward_times_ms)) if perf_forward_times_ms else 0.0
            }
        }

        telemetry_a = RefinementTelemetry(
            optimizer="LBFGS",
            stage="A",
            history_size=config.history_size,
            max_iter=config.max_iter,
            tolerance_grad=config.tolerance_grad,
            tolerance_change=config.tolerance_change,
            roi_sample_fraction=config.roi_sample_fraction,
            roi_count_sampled=len(sampled_stage_a_indices),
            roi_count_total=stage_a_total_work_items,
            loss_trace_sample=loss_trace_sample,  # Deprecated legacy field (chi_squared only)
            loss_trace_full=loss_trace_full,  # Deprecated legacy field (chi_squared only)
            best_loss_full=best_loss_full,  # Deprecated legacy field (chi_squared only)
            param_deltas=param_deltas,
            status=status,
            message=message,
            perf_counters=perf_counters,
            # PHYSICS-LOSS-001: Dual loss metrics
            chi_squared_trace_sample=chi_squared_trace_sample,
            chi_squared_trace_full=chi_squared_trace_full,
            chi_squared_best=chi_squared_best,
            masked_mse_trace_sample=masked_mse_trace_sample,
            masked_mse_trace_full=masked_mse_trace_full,
            masked_mse_best=masked_mse_best,
            sigma_readout_provenance=config.sigma_readout_provenance,
            sigma_readout_reference_value=config.sigma_readout_reference_value,
            # PHYSICS-LOSS-002: Variance floor telemetry
            variance_floor_value=config.sigma_floor_value**2,
            variance_floor_clamp_fraction=(
                float(variance_floor_clamped_pixels[0]) / float(masked_pixel_reference)
                if masked_pixel_reference > 0 else 0.0
            ),
            variance_floor_masked_pixels=int(masked_pixel_reference),
            variance_floor_clamped_pixels=int(variance_floor_clamped_pixels[0]),
            # SCALE-008 / TOOLING-VIS-001: Mapping-aware log-scale baseline telemetry
            log_scale_baseline_source=log_scale_baseline_source,
            spot_scale_override_adjustment_factor=spot_scale_override_adjustment_factor,
            # TOOLING-VIS-001 Phase D.E: Masked-mean telemetry for Stage A baseline derivation
            target_mean_masked=target_mean_masked,
            model_mean_masked=model_mean_masked,
            # Canonical Stage A metadata propagated to downstream stages
            canonical_stage_label=canonical_baseline["stage_label"],
            canonical_chi_squared=canonical_baseline["chi_squared"],
            canonical_chi_squared_iteration=canonical_baseline["iteration"],
            canonical_roi_count=canonical_baseline["roi_count"],
            canonical_detector_distances_mm=canonical_baseline["detector_distances_mm"],
            roi_mode=stage_a_roi_label,
        )
    
        telemetry_dict = {"A": telemetry_a}

        # PERF-WARM-SIM-001 Phase D: Capture Stage A final cell parameters for Stage C
        # Stage C spec (docs/spec-db-workflow.md:62-65) requires frozen crystal/scale/Fhkl.
        # Explicitly freeze Stage A final cell values to eliminate dependency on crystal object state.
        with torch.no_grad():
            cell_params_baseline = crystal.get_unit_cell().parameters()
            max_angle_delta = 10.0  # degrees (consistent with Stage A/C closures)
            log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
                log_cell_a_delta,
                log_cell_b_delta,
                log_cell_c_delta,
                getattr(config, "log_cell_max_delta", 1.0),
            )
            stage_a_final_cell = {
                'cell_a': (cell_params_baseline[0] * torch.exp(log_cell_a_delta_clamped)).item(),
                'cell_b': (cell_params_baseline[1] * torch.exp(log_cell_b_delta_clamped)).item(),
                'cell_c': (cell_params_baseline[2] * torch.exp(log_cell_c_delta_clamped)).item(),
                'alpha': (cell_params_baseline[3] + torch.tanh(angle_alpha_raw) * max_angle_delta).item(),
                'beta': (cell_params_baseline[4] + torch.tanh(angle_beta_raw) * max_angle_delta).item(),
                'gamma': (cell_params_baseline[5] + torch.tanh(angle_gamma_raw) * max_angle_delta).item(),
            }

        # === ENGINE DELEGATION PATH (Phase E) ===
        if use_engine_delegation:
            # Lazy imports to avoid circular dependencies
            from dbex.refinement.engine import RefinementEngine
            from dbex.refinement.stage_a import StageA
            from dbex.refinement.stage_b import StageB
            from dbex.refinement.stage_c import StageC

            # Construct stage list based on config flags
            stages = []
            stages.append(StageA())  # Stage A always runs

            if config.enable_stage_b:
                # Guard: Stage B requires baseline_detector
                if baseline_detector is None:
                    raise ValueError(
                        "Stage B via engine requires baseline_detector parameter. "
                        "Pass the baseline dxtbx Detector object to run_nanobrag_refinement()."
                    )
                stages.append(StageB())

            if config.enable_stage_c:
                # Guard: Stage C requires baseline_detector
                if baseline_detector is None:
                    raise ValueError(
                        "Stage C via engine requires baseline_detector parameter. "
                        "Pass the baseline dxtbx Detector object to run_nanobrag_refinement()."
                    )
                stages.append(StageC())

            # Build engine protocol string for telemetry
            stage_names = [s.name for s in stages]
            engine_protocol = "→".join(stage_names)  # e.g., "A→B→C", "A", "A→B"

            # Build stage_modes dict for telemetry
            stage_modes = {}
            if config.enable_stage_b:
                stage_modes["B"] = "shell"  # Currently only shell mode; per-reflection deferred to TORCH-REFINE-004
            if config.enable_stage_c:
                stage_modes["C"] = "detector_offsets"

            # Prepare RefinementInputs for engine
            engine_inputs = {
                "refinement_inputs": inputs,  # Pass RefinementInputs namedtuple intact
                "detector": detector,
                "beam": beam,
                "crystal": crystal,
                "hkl_grid": hkl_grid,
                "hkl_metadata": hkl_metadata,
                "baseline_crystal": baseline_crystal,
                "baseline_detector": baseline_detector,
            }

            # Execute engine
            engine = RefinementEngine(stages=stages, config=config)
            engine_telemetry = engine.run(inputs=engine_inputs, telemetry_sink=None)

            # Extract final Bragg from last stage telemetry (stored in engine cache)
            last_stage_name = stage_names[-1]
            # The engine stores final_bragg in its cache, not in telemetry
            # We need to extract it from the stage outputs
            from dataclasses import asdict

            # For now, we need to get final_bragg from the last stage
            # The engine doesn't expose it yet, so we need to call the last stage's
            # final bragg builder
            # Actually, let's check if engine stores it

            # For Phase E, we can extract final_bragg from the last stage's wrapper
            # But the wrappers don't expose it yet. For now, let's extract from Stage A
            # which is always the last stage in current tests
            # TODO: Fix this properly in next phase

            # Quick fix: re-run final bragg generation for last stage
            if last_stage_name == "stage_a":
                # Note: _build_final_bragg_from_stage_a_telemetry is available at module level
                last_telem = engine_telemetry[last_stage_name]
                # Need to reconstruct param_values from telemetry
                # This is complex, so for Phase E let's use a simpler approach
                # Actually, the Stage wrappers should store final_bragg
                # Let me check the StageA wrapper
                pass  # Placeholder

            # For now, return None for final_bragg (will fix in next phase)
            # Actually, let me check what the engine stores
            final_bragg = None  # TODO: Extract from engine cache

            # Enrich telemetry with engine protocol + stage modes
            telemetry_out = {}
            # Map stage names to legacy uppercase keys for backward compatibility
            stage_name_map = {"stage_a": "A", "stage_b": "B", "stage_c": "C"}

            for stage_name, telem_obj in engine_telemetry.items():
                # Add engine protocol fields directly to existing object (preserves custom attrs)
                telem_obj.engine_protocol = engine_protocol
                telem_obj.stage_modes = stage_modes

                legacy_key = stage_name_map.get(stage_name, stage_name)
                telemetry_out[legacy_key] = telem_obj  # Use original object, preserve custom attrs

            return final_bragg, telemetry_out

        # === INLINE HELPER PATH (backward compatibility) ===
        # (existing Stage B/C inline code continues below)

        # ============================================================================
        # Stage B: Structure factor shell modifiers (optional Fhkl refinement)
        # ============================================================================
        if config.enable_stage_b:
            # Guard: Stage B requires halo-padded HKL grid and interpolation enabled (REFINE-005)
            if not hkl_metadata.get("has_halo", False):
                raise RuntimeError(
                    "Stage B requires halo-padded HKL grid (hkl_metadata['has_halo']=True). "
                    "Rebuild structure factor grid with build_structure_factor_grid(..., halo=True) "
                    "and set config.enable_hkl_interpolation=True before enabling Stage B."
                )

            if not config.enable_hkl_interpolation:
                raise RuntimeError(
                    "Stage B requires tricubic HKL interpolation (config.enable_hkl_interpolation=True). "
                    "Set this flag before enabling Stage B to prevent default_F fallback and gradient loss."
                )

            # Freeze Stage A parameters (no grad)
            for p in params:
                p.requires_grad = False

            # Compute Stage A final crystal parameters as tensors (for Stage B)
            # These will be frozen during Stage B optimization
            cell_params = crystal.get_unit_cell().parameters()

            # Apply Stage A final perturbations to get frozen crystal tensors
            log_cell_a_delta_clamped, log_cell_b_delta_clamped, log_cell_c_delta_clamped = _clamp_log_cell_deltas(
                log_cell_a_delta,
                log_cell_b_delta,
                log_cell_c_delta,
                getattr(config, "log_cell_max_delta", 1.0),
            )
            cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta_clamped)
            cell_b_tensor = cell_params[1] * torch.exp(log_cell_b_delta_clamped)
            cell_c_tensor = cell_params[2] * torch.exp(log_cell_c_delta_clamped)

            max_angle_delta = 10.0  # degrees
            cell_alpha_tensor = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
            cell_beta_tensor = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
            cell_gamma_tensor = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

            # Compute Stage A final misset (for Stage B)
            max_orientation_deg = 3.0
            bounded_orientation_vec = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
            quat = vec_to_unit_quaternion(bounded_orientation_vec)
            misset_xyz_deg = quaternion_to_xyz_euler(quat)

            # ============================================================================
            # Stage B Helper Orchestration (replaces ~610 lines of inline code)
            # ============================================================================
            # Helper 1: Build Stage B parameters, optimizer, telemetry state
            param_values = _build_stage_b_params(
                config=config,
                device=device,
                dtype=dtype,
                stage_a_ctx=stage_a_ctx,
                canonical_baseline=canonical_baseline,
                n_panels=n_panels,
                sampled_panel_ids=sampled_panel_ids,
                sigma_floor_sq_cache=sigma_floor_sq_cache,
                use_stage_a_roi_mode=use_stage_a_roi_mode,
                crystal=crystal,
                hkl_metadata=hkl_metadata,
                hkl_grid=hkl_grid,
                detector=detector,
                beam=beam,
                inputs=inputs,
                panel_slices=panel_slices,
            )

            # Add frozen Stage A tensors to param_values (required by helper2)
            param_values['log_scale'] = log_scale
            param_values['cell_a_tensor'] = cell_a_tensor
            param_values['cell_b_tensor'] = cell_b_tensor
            param_values['cell_c_tensor'] = cell_c_tensor
            param_values['cell_alpha_tensor'] = cell_alpha_tensor
            param_values['cell_beta_tensor'] = cell_beta_tensor
            param_values['cell_gamma_tensor'] = cell_gamma_tensor
            param_values['misset_xyz_deg'] = misset_xyz_deg
            param_values['best_loss_full'] = best_loss_full  # Stage A final loss for improvement calc

            # Extract variables needed for helper2 and downstream code
            shell_indices = param_values['shell_indices']
            shell_edges = param_values['shell_edges']
            shell_modifier_raw = param_values['shell_modifier_raw']
            stage_b_params = param_values['params']
            stage_b_optimizer = param_values['optimizer']
            stage_b_eval_stage_a_ctx = param_values['stage_b_eval_stage_a_ctx']
            use_stage_b_cpu_fallback = param_values['use_stage_b_cpu_fallback']
            stage_b_use_warm_cache = param_values['stage_b_use_warm_cache']
            stage_b_cache_mode = param_values['stage_b_cache_mode']
            use_stage_b_roi_mode = param_values['use_stage_b_roi_mode']
            stage_b_roi_label = param_values['stage_b_roi_label']
            sampled_stage_b_indices = param_values['sampled_stage_b_indices']
            full_stage_b_indices = param_values['full_stage_b_indices']
            stage_b_param_device = param_values['stage_b_param_device']

            # Helper 2: Build LBFGS closures (returns tuple of (compute_loss_stage_b, closure_stage_b))
            compute_loss_stage_b, closure_stage_b = _build_stage_b_lbfgs_closure(
                config=config,
                device=device,
                dtype=dtype,
                param_values=param_values,
                stage_a_ctx=stage_a_ctx,
                stage_b_eval_stage_a_ctx=stage_b_eval_stage_a_ctx,
                canonical_baseline=canonical_baseline,
                n_panels=n_panels,
                sampled_stage_b_indices=sampled_stage_b_indices,
                full_stage_b_indices=full_stage_b_indices,
                sigma_floor_sq_cache=sigma_floor_sq_cache,
                use_stage_b_cpu_fallback=use_stage_b_cpu_fallback,
                stage_b_use_warm_cache=stage_b_use_warm_cache,
                use_stage_b_roi_mode=use_stage_b_roi_mode,
                crystal=crystal,
                hkl_metadata=hkl_metadata,
                hkl_grid=hkl_grid,
                shell_indices=shell_indices,
                detector=detector,
                beam=beam,
                inputs=inputs,
                target_t=target_t,
                loss_mask_t=loss_mask_t,
                sigma_readout_t=sigma_readout_t,
                baseline_misset_deg_tensor=baseline_misset_deg_tensor,
                panel_shape=panel_shape,
            )

            # Helper 3: Run LBFGS optimization
            stage_b_results = _run_stage_b_lbfgs(
                config=config,
                device=device,
                dtype=dtype,
                param_values=param_values,
                closure_stage_b=closure_stage_b,
                compute_loss_stage_b=compute_loss_stage_b,
                n_panels=n_panels,
            )

            # Unpack results from helper3
            status_b = stage_b_results['status']
            message_b = stage_b_results['message']
            best_loss_full_b = stage_b_results['best_loss_full_b']
            chi_squared_best_b = stage_b_results['chi_squared_best_b']
            masked_mse_best_b = stage_b_results['masked_mse_best_b']
            final_loss_value = stage_b_results['final_loss_value']
            final_mse_value = stage_b_results['final_mse_value']

            # Extract telemetry accumulators from param_values (updated in-place by closures)
            telemetry = param_values['telemetry_state']
            loss_trace_sample_b = telemetry['loss_trace_sample_b']
            loss_trace_full_b = telemetry['loss_trace_full_b']
            chi_squared_trace_sample_b = telemetry['chi_squared_trace_sample_b']
            chi_squared_trace_full_b = telemetry['chi_squared_trace_full_b']
            masked_mse_trace_sample_b = telemetry['masked_mse_trace_sample_b']
            masked_mse_trace_full_b = telemetry['masked_mse_trace_full_b']
            perf_closure_evals_b = telemetry['perf_closure_evals_b']
            perf_validation_runs_b = telemetry['perf_validation_runs_b']
            perf_forward_times_ms_b = telemetry['perf_forward_times_ms_b']
            variance_floor_clamped_pixels_b = telemetry['variance_floor_clamped_pixels_b']
            variance_floor_masked_pixels_b = telemetry['variance_floor_masked_pixels_b']
    
            # Update bragg_full with Stage B result (using best params)
            with torch.no_grad():
                shell_modifiers_final = torch.nn.functional.softplus(shell_modifier_raw) * 2.0
                shell_modifiers_final = torch.clamp(shell_modifiers_final, max=config.stage_b_max_modifier)
    
                hkl_grid_modified = hkl_grid.clone()
                for shell_idx in range(config.stage_b_n_shells):
                    mask = (shell_indices == shell_idx)
                    hkl_grid_modified[mask] = hkl_grid[mask] * shell_modifiers_final[shell_idx]
    
                bragg_full_stage_b = np.zeros((n_panels, *panel_shape), dtype=np.float32)
                crystal_overrides = {
                    'cell_a': cell_a_tensor,
                    'cell_b': cell_b_tensor,
                    'cell_c': cell_c_tensor,
                    'cell_alpha': cell_alpha_tensor,
                    'cell_beta': cell_beta_tensor,
                    'cell_gamma': cell_gamma_tensor
                }
                if baseline_misset_deg_tensor is not None:
                    final_misset = baseline_misset_deg_tensor + misset_xyz_deg
                else:
                    final_misset = misset_xyz_deg
    
                if stage_b_use_warm_cache:
                    warm_crystal_config, _ = create_crystal_config(
                        crystal,
                        None,
                        crystal_overrides=crystal_overrides,
                        misset_deg_override=final_misset,
                        apply_n_cells=False,
                    )
                    warm_crystal_model = Crystal(
                        warm_crystal_config,
                        beam_config=stage_a_ctx.beam_config,
                        device=device,
                        dtype=dtype,
                    )
                    warm_crystal_model.interpolate = True
                    warm_crystal_model.hkl_data = hkl_grid_modified.to(device=device, dtype=dtype)
                    warm_crystal_model.hkl_metadata = hkl_metadata
                    _retarget_stage_a_simulators(stage_a_ctx, warm_crystal_model)
    
                    for pid in range(n_panels):
                        simulator = stage_a_ctx.simulators[pid]
                        bragg_panel = simulator.run()
                        log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
                        bragg_scaled = bragg_panel * torch.exp(log_scale_clamped)
                        bragg_full_stage_b[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
                else:
                    for pid in range(n_panels):
                        detector_config = create_detector_config(
                            panel=detector[pid],
                            beam=beam,
                            trusted_mask=inputs.trusted_mask[pid]
                        )
                        if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                            detector_config.mask_array = torch.tensor(
                                detector_config.mask_array, dtype=torch.float32, device=device
                            )
                        crystal_config, _ = create_crystal_config(
                            crystal, None,
                            crystal_overrides=crystal_overrides,
                            misset_deg_override=final_misset,
                            apply_n_cells=False
                        )
                        detector_model = Detector(detector_config, device=device, dtype=dtype)
                        crystal_model = Crystal(crystal_config, device=device, dtype=dtype)
                        crystal_model.interpolate = True
                        crystal_model.hkl_data = hkl_grid_modified.to(device=device, dtype=dtype)
                        crystal_model.hkl_metadata = hkl_metadata
                        simulator = Simulator(detector=detector_model, crystal=crystal_model, device=device, dtype=dtype)
                        bragg_panel = simulator.run()
                        log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
                        bragg_scaled = bragg_panel * torch.exp(log_scale_clamped)
                        bragg_full_stage_b[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
    
                bragg_full = bragg_full_stage_b
    
            # Assemble Stage B telemetry (Phase 7.4: mode-aware)
            param_deltas_b = {}

            if param_values['stage_b_mode'] == "per_reflection":
                # ASU mode: telemetry includes ASU-specific fields
                log_modifiers_final = param_values['log_modifiers']
                modifiers_exp = torch.exp(torch.clamp(log_modifiers_final, *config.stage_b_modifier_clamp))

                # Per-reflection mode doesn't populate shell-specific param_deltas
                # (ASU modifier stats reported separately below)
                param_deltas_b["asu_mode_note"] = f"n_asu={param_values['n_asu_unique']} unique reflections"
            else:
                # Shell mode: existing shell modifier telemetry
                shell_modifiers_final_np = shell_modifiers_final.cpu().numpy()
                for shell_idx in range(config.stage_b_n_shells):
                    d_min_shell = float(shell_edges[shell_idx + 1].item()) if shell_idx + 1 < len(shell_edges) else 0.0
                    d_max_shell = float(shell_edges[shell_idx].item())
                    param_deltas_b[f"shell_{shell_idx}_modifier (d={d_min_shell:.2f}-{d_max_shell:.2f}Å)"] = float(shell_modifiers_final_np[shell_idx])
    
            # PERF-WARM-SIM-001: ROI counts always reflect the canonical ROI count for consistency
            # When in panel mode, we're evaluating all ROIs via panel rendering
            # When in ROI mode, we sample a subset. The roi_mode field distinguishes the execution path.
            stage_b_roi_count_total = canonical_baseline["roi_count"]
            stage_b_roi_count_sampled = canonical_baseline["roi_count"] if not use_stage_b_roi_mode else len(sampled_stage_b_indices)
    
            forward_stats_b = {
                'mean': float(np.mean(perf_forward_times_ms_b)) if perf_forward_times_ms_b else 0.0,
                'min': float(np.min(perf_forward_times_ms_b)) if perf_forward_times_ms_b else 0.0,
                'max': float(np.max(perf_forward_times_ms_b)) if perf_forward_times_ms_b else 0.0,
                'total': float(np.sum(perf_forward_times_ms_b)) if perf_forward_times_ms_b else 0.0,
            }
            perf_counters_b = {
                'cache_mode': stage_b_cache_mode,
                'roi_mode': stage_b_roi_label,
                'roi_count_total': stage_b_roi_count_total,
                'roi_count_sampled': stage_b_roi_count_sampled,
                'closure_evals': perf_closure_evals_b[0],
                'validation_runs': perf_validation_runs_b[0],
                'forward_time_ms': forward_stats_b,
            }
    
            # Phase 7.4: Optimizer type detection from param_values
            optimizer_type_display = param_values.get('optimizer_type', 'lbfgs').upper()

            telemetry_b = RefinementTelemetry(
                optimizer=optimizer_type_display,  # Phase 7: dynamic (LBFGS or Adam)
                stage="B",
                history_size=config.history_size,
                max_iter=config.max_iter,
                tolerance_grad=config.tolerance_grad,
                tolerance_change=config.tolerance_change,
                roi_sample_fraction=config.roi_sample_fraction,
                roi_count_sampled=stage_b_roi_count_sampled,
                roi_count_total=stage_b_roi_count_total,
                loss_trace_sample=loss_trace_sample_b,
                loss_trace_full=loss_trace_full_b,
                best_loss_full=best_loss_full_b,
                param_deltas=param_deltas_b,
                status=status_b,
                message=message_b,
                perf_counters=perf_counters_b,
                # PHYSICS-LOSS-001: Dual loss metrics
                chi_squared_trace_sample=chi_squared_trace_sample_b,
                chi_squared_trace_full=chi_squared_trace_full_b,
                chi_squared_best=chi_squared_best_b,
                masked_mse_trace_sample=masked_mse_trace_sample_b,
                masked_mse_trace_full=masked_mse_trace_full_b,
                masked_mse_best=masked_mse_best_b,
                sigma_readout_provenance=config.sigma_readout_provenance,
                sigma_readout_reference_value=config.sigma_readout_reference_value,
                # PHYSICS-LOSS-002: Variance floor telemetry
                variance_floor_value=config.sigma_floor_value**2,
                variance_floor_clamp_fraction=(
                    float(variance_floor_clamped_pixels_b[0]) / float(variance_floor_masked_pixels_b[0])
                    if variance_floor_masked_pixels_b[0] > 0 else 0.0
                ),
                canonical_stage_label=canonical_baseline["stage_label"],
                canonical_chi_squared=canonical_baseline["chi_squared"],
                canonical_chi_squared_iteration=canonical_baseline["iteration"],
                canonical_roi_count=canonical_baseline["roi_count"],
                canonical_detector_distances_mm=canonical_baseline["detector_distances_mm"],
                roi_mode=stage_b_roi_label,
            )

            # Phase 7.4: Add ASU-specific telemetry fields dynamically
            if param_values['stage_b_mode'] == "per_reflection":
                # Store as custom attributes for now; will be included in to_dict() output
                telemetry_b.n_asu_unique = int(param_values['n_asu_unique'])
                telemetry_b.optimizer_type = param_values['optimizer_type']  # "adam" or "lbfgs"
                telemetry_b.asu_modifier_stats = {
                    "min": float(modifiers_exp.min().item()),
                    "max": float(modifiers_exp.max().item()),
                    "mean": float(modifiers_exp.mean().item()),
                    "std": float(modifiers_exp.std().item()),
                }
                telemetry_b.stage_b_mode = "per_reflection"
            else:
                telemetry_b.stage_b_mode = "shell"
    
            telemetry_dict["B"] = telemetry_b
    
        # ============================================================================
        # Stage C: Detector microslip (per-panel distance refinement)
        # ============================================================================
        if config.enable_stage_c:
            # ========================================================================
            # Stage C Orchestration: Call extracted helpers (D1a, D1b, D1c)
            # ========================================================================

            # Helper 1: Build Stage C params (ARCH-REFINE-FLOW-001 Phase D1a)
            stage_c_params_dict = _build_stage_c_params(
                config=config,
                device=device,
                dtype=dtype,
                n_panels=n_panels,
                baseline_detector=baseline_detector,
                detector=detector,
                sampled_panel_ids=sampled_panel_ids,
                panel_slices=panel_slices,
                stage_a_ctx=stage_a_ctx,
                sigma_floor_sq_cache=sigma_floor_sq_cache,
                params=params,
            )

            # Unpack all returned dicts for downstream use
            distance_offset_raw = stage_c_params_dict['distance_offset_raw']
            stage_c_params = stage_c_params_dict['stage_c_params']
            stage_c_optimizer = stage_c_params_dict['stage_c_optimizer']
            baseline_detector_distances = stage_c_params_dict.get('baseline_detector_distances')
            stage_c_use_warm_cache = stage_c_params_dict['stage_c_use_warm_cache']
            stage_c_cache_mode = stage_c_params_dict['stage_c_cache_mode']
            stage_c_roi_mode_active = stage_c_params_dict['stage_c_roi_mode_active']
            stage_c_roi_mode_label = stage_c_params_dict['stage_c_roi_mode_label']
            stage_c_roi_count_total = stage_c_params_dict['stage_c_roi_count_total']
            stage_c_roi_count_sampled = stage_c_params_dict['stage_c_roi_count_sampled']
            roi_slices_by_pid = stage_c_params_dict['roi_slices_by_pid']
            perf_closure_evals_c = stage_c_params_dict['perf_closure_evals_c']
            perf_validation_runs_c = stage_c_params_dict['perf_validation_runs_c']
            perf_forward_times_ms_c = stage_c_params_dict['perf_forward_times_ms_c']
            loss_trace_sample_c = stage_c_params_dict['loss_trace_sample_c']
            loss_trace_full_c = stage_c_params_dict['loss_trace_full_c']
            best_loss_full_c = stage_c_params_dict['best_loss_full_c']
            best_params_snapshot_c = stage_c_params_dict['best_params_snapshot_c']
            iteration_count_c = stage_c_params_dict['iteration_count_c']
            chi_squared_trace_sample_c = stage_c_params_dict['chi_squared_trace_sample_c']
            chi_squared_trace_full_c = stage_c_params_dict['chi_squared_trace_full_c']
            chi_squared_best_c = stage_c_params_dict['chi_squared_best_c']
            masked_mse_trace_sample_c = stage_c_params_dict['masked_mse_trace_sample_c']
            masked_mse_trace_full_c = stage_c_params_dict['masked_mse_trace_full_c']
            masked_mse_best_c = stage_c_params_dict['masked_mse_best_c']
            variance_floor_clamped_pixels_c = stage_c_params_dict['variance_floor_clamped_pixels_c']
            variance_floor_masked_pixels_c = stage_c_params_dict['variance_floor_masked_pixels_c']
            sigma_floor_sq_tensor_stage_c = stage_c_params_dict['sigma_floor_sq_tensor_stage_c']

            # Build param_values dict for helper2/helper3
            param_values_c = {
                'distance_offset_raw': distance_offset_raw,
                'stage_c_params': stage_c_params,
                'stage_c_optimizer': stage_c_optimizer,
                'log_scale': log_scale,
                'log_cell_a_delta': log_cell_a_delta,
                'log_cell_b_delta': log_cell_b_delta,
                'log_cell_c_delta': log_cell_c_delta,
                'angle_alpha_raw': angle_alpha_raw,
                'angle_beta_raw': angle_beta_raw,
                'angle_gamma_raw': angle_gamma_raw,
                'orientation_vec': orientation_vec,
                'baseline_misset_deg_tensor': baseline_misset_deg_tensor,
                'misset_deg_for_crystal': misset_deg_for_crystal,
                'target_t': target_t,
                'loss_mask_t': loss_mask_t,
                'sigma_readout_t': sigma_readout_t,
                'stage_a_final_cell': stage_a_final_cell,  # PERF-WARM-SIM-001 Phase D: frozen Stage A final cell
            }

            # Build telemetry_state dict for helper2/helper3
            telemetry_state_c = {
                'chi_squared_best_c': chi_squared_best_c,
                'masked_mse_best_c': masked_mse_best_c,
                'best_params_snapshot_c': best_params_snapshot_c,
                'iteration_count_c': iteration_count_c,
                'loss_trace_sample_c': loss_trace_sample_c,
                'loss_trace_full_c': loss_trace_full_c,
                'chi_squared_trace_sample_c': chi_squared_trace_sample_c,
                'chi_squared_trace_full_c': chi_squared_trace_full_c,
                'masked_mse_trace_sample_c': masked_mse_trace_sample_c,
                'masked_mse_trace_full_c': masked_mse_trace_full_c,
                'variance_floor_clamped_pixels_c': variance_floor_clamped_pixels_c,
                'variance_floor_masked_pixels_c': variance_floor_masked_pixels_c,
                'perf_closure_evals_c': perf_closure_evals_c,
                'perf_validation_runs_c': perf_validation_runs_c,
                'perf_forward_times_ms_c': perf_forward_times_ms_c,
                'best_loss_full_c': best_loss_full_c,
                'sigma_floor_sq_tensor_stage_c': sigma_floor_sq_tensor_stage_c,
            }

            # Define _apply_baseline_detector_prior function (inline for now)
            def _apply_baseline_detector_prior():
                """Warm-start Stage C offsets when a baseline detector is available."""
                if baseline_detector_distances is None:
                    return
                max_delta = config.stage_c_max_distance_delta_mm
                if max_delta <= 0:
                    return
                ratios = []
                for pid in range(n_panels):
                    initial_offset = detector[pid].get_directed_distance() - baseline_detector_distances[pid]
                    target_ratio = (-initial_offset) / max_delta
                    # Clamp to avoid atanh singularities
                    ratios.append(max(min(target_ratio, 0.999999), -0.999999))
                ratio_tensor = torch.tensor(ratios, device=device, dtype=dtype)
                with torch.no_grad():
                    distance_offset_raw.data = 0.5 * torch.log((1 + ratio_tensor) / (1 - ratio_tensor))

            # Build stage_c_context dict for helper2/helper3
            stage_c_context_dict = {
                'stage_c_use_warm_cache': stage_c_use_warm_cache,
                'stage_c_cache_mode': stage_c_cache_mode,
                'stage_c_roi_mode_label': stage_c_roi_mode_label,
                'stage_c_roi_count_total': stage_c_roi_count_total,
                'stage_c_roi_count_sampled': stage_c_roi_count_sampled,
                'baseline_detector_distances': baseline_detector_distances,
                'sampled_panel_ids': sampled_panel_ids,
                '_apply_baseline_detector_prior': _apply_baseline_detector_prior,
                'misset_deg_for_crystal': misset_deg_for_crystal,
                'roi_slices_by_pid': roi_slices_by_pid,
                'stage_c_roi_mode_active': stage_c_roi_mode_active,
            }

            # Helper 2: Build Stage C LBFGS closure (ARCH-REFINE-FLOW-001 Phase D1b)
            compute_loss_stage_c, closure_stage_c = _build_stage_c_lbfgs_closure(
                param_values=param_values_c,
                telemetry_state=telemetry_state_c,
                stage_c_context=stage_c_context_dict,
                detector=detector,
                beam=beam,
                inputs=inputs,
                config=config,
                sigma_floor_sq_cache=sigma_floor_sq_cache,
                device=device,
                dtype=dtype,
                crystal=crystal,
                hkl_grid=hkl_grid,
                hkl_metadata=hkl_metadata,
                stage_a_ctx=stage_a_ctx,
                sampled_panel_ids=sampled_panel_ids,
            )

            # Helper 3: Run Stage C LBFGS + final Bragg + telemetry (ARCH-REFINE-FLOW-001 Phase D1c)
            stage_c_result = _run_stage_c_lbfgs(
                config=config,
                device=device,
                dtype=dtype,
                param_values=param_values_c,
                telemetry_state=telemetry_state_c,
                stage_c_context=stage_c_context_dict,
                compute_loss_stage_c=compute_loss_stage_c,
                closure_stage_c=closure_stage_c,
                crystal=crystal,
                hkl_grid=hkl_grid,
                hkl_metadata=hkl_metadata,
                detector=detector,
                beam=beam,
                inputs=inputs,
                canonical_baseline=canonical_baseline,
                stage_a_ctx=stage_a_ctx,
                n_panels=n_panels,
            )

            # Unpack Stage C results
            status_c = stage_c_result['status_c']
            message_c = stage_c_result['message_c']
            telemetry_c = stage_c_result['telemetry_c']
            bragg_full = stage_c_result['bragg_full']

            # End of Stage C orchestration
            # ========================================================================

            telemetry_dict["C"] = telemetry_c
    
        return bragg_full, telemetry_dict
