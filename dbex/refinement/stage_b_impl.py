"""
Stage B implementation helpers for nanobrag_torch backend.

Contains the Stage B LBFGS refinement helpers extracted from the monolithic
nanobrag_refinement.py to support both the inline refinement path and the
Protocol Engine StageB wrapper.

Provides:
- ASU/shell utility functions for per-reflection and shell modes
- Stage B parameter building and LBFGS execution
- ARCH-STAGE-CONTEXT-001 Phase B.2: Closure construction moved to StageB._build_lbfgs_closure

References:
- docs/spec-db-workflow.md:76-79 (Stage B structure factor modifiers)
- plans/active/ARCH-REFINE-001/implementation.md (Phase A.2 helper extraction)
- plans/active/TORCH-REFINE-004/implementation.md (per-reflection mode)
"""

import math
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch

# Import Stage A helpers for dependencies
from dbex.refinement.stage_a_impl import (
    _build_stage_a_context,
    _retarget_stage_a_simulators,
    _get_sigma_floor_sq_tensor,
)
from dbex.refinement.context import RefinementSharedContext, StageBTelemetryState
from dbex.physics.loss import _compute_variance_weighted_loss


def _check_stage_b_baseline_parity(
    canonical_baseline: Dict[str, Any],
    initial_chi_squared_b: torch.Tensor,
    telemetry: Any,  # Dict[str, Any] | StageBTelemetryState | StageBTelemetryCollector
    param_values: Dict[str, Any],
    compute_loss_stage_b: Callable[[List[int], bool, bool], Tuple[torch.Tensor, torch.Tensor]],
    n_panels: int,
) -> None:
    """
    Stage B baseline parity guard (REFINE-FLOW-001).

    Compares Stage B initial chi² against Stage A canonical chi² to detect
    parameter reconstruction drift. Emits actionable JSON diff when parity fails.

    Args:
        canonical_baseline: Stage A final state dict with 'chi_squared', 'log_scale',
                            cell params, misset, roi_count, iteration
        initial_chi_squared_b: Stage B initial chi² tensor (before optimization)
        telemetry: Telemetry dict, StageBTelemetryState, or StageBTelemetryCollector
                   to record parity diagnostics (stage_b_baseline_rel_diff, etc)
        param_values: Stage B param dict with cell/misset tensors, cache_mode, etc
        compute_loss_stage_b: Loss computation callable for per-panel breakdown
        n_panels: Number of detector panels for per-panel chi² queries

    Raises:
        RuntimeError: If |rel_diff| > 1e-3 (0.1% tolerance per REFINE-FLOW-001)

    Mutates:
        telemetry fields via dict assignment, dataclass setattr, or collector helper

    References:
        - docs/findings.md:71 (REFINE-FLOW-001 tolerance and actionable diffs)
        - docs/spec-db-workflow.md:76-79 (Stage B baseline parity requirement)
        - ARCH-TELEMETRY-001 Phase C.1 (collector support)
    """
    import json
    import os
    from pathlib import Path
    import logging

    canonical_chi_squared = canonical_baseline.get('chi_squared')

    if canonical_chi_squared is None:
        # No baseline to compare against; skip guard
        return

    stage_b_initial_chi2 = float(initial_chi_squared_b.item())
    canonical_chi2 = float(canonical_chi_squared)
    abs_diff = stage_b_initial_chi2 - canonical_chi2
    rel_diff = abs_diff / canonical_chi2 if canonical_chi2 != 0 else float('inf')

    # Record parity diagnostics in telemetry (always, for observability)
    # ARCH-TELEMETRY-001 Phase C.1: Support collector, dataclass, or dict telemetry
    from dbex.refinement.telemetry_collectors import StageBTelemetryCollector

    if isinstance(telemetry, StageBTelemetryCollector):
        # Collector path: use helper method (ARCH-TELEMETRY-001)
        telemetry.set_baseline_parity_metrics(rel_diff, abs_diff)
    elif isinstance(telemetry, StageBTelemetryState):
        # Dataclass path: use setattr for type-safe attribute assignment
        telemetry.stage_b_baseline_rel_diff = rel_diff
        telemetry.stage_b_baseline_abs_diff = abs_diff
    else:
        # Legacy dict path (for test_stage_b_cpu_fallback backward compat)
        telemetry['stage_b_baseline_rel_diff'] = rel_diff
        telemetry['stage_b_baseline_abs_diff'] = abs_diff

    # Guard: raise if parity exceeds 0.1% tolerance (1e-3 relative difference)
    tolerance = 1e-3
    if abs(rel_diff) > tolerance:
        # Emit JSON diff file for debugging with per-panel chi² breakdown

        # Determine artifacts directory from environment or default to cwd
        telemetry_path_env = os.environ.get("DBEX_SMOKE_TELEMETRY_PATH")
        if telemetry_path_env:
            artifacts_dir = Path(telemetry_path_env).parent
        else:
            # Fallback to current working directory
            artifacts_dir = Path.cwd()
            logging.warning(
                "DBEX_SMOKE_TELEMETRY_PATH not set, writing stage_b_baseline_diff.json to cwd: %s",
                artifacts_dir
            )

        artifacts_dir.mkdir(parents=True, exist_ok=True)
        diff_path = artifacts_dir / "stage_b_baseline_diff.json"

        # Compute per-panel chi² breakdown
        per_panel_breakdown = []
        with torch.no_grad():
            for pid in range(n_panels):
                panel_chi2, panel_mse = compute_loss_stage_b([pid], is_full=True, force_panel_eval=True)
                per_panel_breakdown.append({
                    "panel_id": pid,
                    "chi_squared": float(panel_chi2.item()),
                    "masked_mse": float(panel_mse.item()),
                })

        # Extract Stage A canonical snapshot
        canonical_snapshot = {
            "stage_label": canonical_baseline.get('stage_label', 'A'),
            "chi_squared": canonical_chi2,
            "iteration": canonical_baseline.get('iteration', 0),
            "roi_count": canonical_baseline.get('roi_count', 0),
            "log_scale": canonical_baseline.get('log_scale', 0.0),
            "cell_a": canonical_baseline.get('cell_a', 0.0),
            "cell_b": canonical_baseline.get('cell_b', 0.0),
            "cell_c": canonical_baseline.get('cell_c', 0.0),
            "cell_alpha": canonical_baseline.get('cell_alpha', 90.0),
            "cell_beta": canonical_baseline.get('cell_beta', 90.0),
            "cell_gamma": canonical_baseline.get('cell_gamma', 90.0),
            "misset_deg": canonical_baseline.get('misset_deg', (0.0, 0.0, 0.0)),
        }

        # Extract Stage B reconstructed parameters (what Stage B actually used)
        stage_b_mode = param_values.get('stage_b_mode', 'shell')
        stage_b_reconstructed = {
            "log_scale": float(param_values['log_scale'].item()) if 'log_scale' in param_values else 0.0,
            "cell_a": float(param_values['cell_a_tensor'].item()) if 'cell_a_tensor' in param_values else 0.0,
            "cell_b": float(param_values['cell_b_tensor'].item()) if 'cell_b_tensor' in param_values else 0.0,
            "cell_c": float(param_values['cell_c_tensor'].item()) if 'cell_c_tensor' in param_values else 0.0,
            "cell_alpha": float(param_values['cell_alpha_tensor'].item()) if 'cell_alpha_tensor' in param_values else 90.0,
            "cell_beta": float(param_values['cell_beta_tensor'].item()) if 'cell_beta_tensor' in param_values else 90.0,
            "cell_gamma": float(param_values['cell_gamma_tensor'].item()) if 'cell_gamma_tensor' in param_values else 90.0,
            "misset_deg": tuple(float(x) for x in param_values['misset_xyz_deg'].tolist()) if 'misset_xyz_deg' in param_values else (0.0, 0.0, 0.0),
            "cache_mode": param_values.get('stage_b_cache_mode', 'cold'),
            "cpu_fallback": param_values.get('use_stage_b_cpu_fallback', False),
            "stage_b_mode": stage_b_mode,
        }

        diff_data = {
            "canonical_snapshot": canonical_snapshot,
            "stage_b_reconstructed": stage_b_reconstructed,
            "stage_b_initial_chi_squared": stage_b_initial_chi2,
            "absolute_difference": abs_diff,
            "relative_difference": rel_diff,
            "tolerance": tolerance,
            "per_panel_breakdown": per_panel_breakdown,
        }

        with open(diff_path, 'w') as f:
            json.dump(diff_data, f, indent=2)

        # Store diff path in telemetry for test assertions
        # ARCH-TELEMETRY-001 Phase C.1: Support collector, dataclass, or dict telemetry
        if isinstance(telemetry, StageBTelemetryCollector):
            # Collector path: use helper method to set diff_path
            telemetry.set_baseline_parity_metrics(rel_diff, abs_diff, str(diff_path))
        elif isinstance(telemetry, StageBTelemetryState):
            # Dataclass path: use setattr
            telemetry.stage_b_baseline_diff_path = str(diff_path)
        else:
            # Legacy dict path
            telemetry['stage_b_baseline_diff_path'] = str(diff_path)

        raise RuntimeError(
            f"REFINE-FLOW-001 baseline drift: Stage B initial chi² ({stage_b_initial_chi2:.3e}) "
            f"differs from Stage A final ({canonical_chi2:.3e}) by {rel_diff:.4%} "
            f"(tolerance={tolerance:.1%}). See {diff_path} for details."
        )
    else:
        # Parity passed, record diff path as None
        # ARCH-STAGE-CONTEXT-001 Phase B.4: Dataclass vs dict branching
        if isinstance(telemetry, StageBTelemetryState):
            telemetry.stage_b_baseline_diff_path = None
        else:
            telemetry['stage_b_baseline_diff_path'] = None


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


def _build_stage_b_params(
    config: 'RefinementConfig',
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
    context: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Build Stage B shell modifier parameters, optimizer, and telemetry state.

    Args:
        context: Optional RefinementContext with pre-computed asu_map, hkl_indices_grid, halo_mask
                (ARCH-REFINE-001 Phase B.3). If provided and asu_map is available, Stage B reuses
                it instead of calling compute_hkl_asu_map to avoid cctbx dependency and duplicating work.

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
        # ARCH-REFINE-001 Phase B.3: Check for pre-computed ASU map in context
        # If CLI already built asu_map via build_structure_factor_grid, reuse it
        # to avoid calling cctbx compute_hkl_asu_map again (REFINE-005)
        asu_indices = None
        n_asu_unique = 0
        if context is not None and hasattr(context, 'asu_map') and context.asu_map is not None:
            # Context provides pre-computed ASU map; use it directly
            import logging
            logger = logging.getLogger(__name__)
            logger.info("[Stage B] Reusing pre-computed asu_map from context (ARCH-REFINE-001 Phase B.3)")
            asu_indices = context.asu_map  # torch.Tensor from build_structure_factor_grid
            # Extract n_asu_unique from hkl_metadata if available (CLI stores it there)
            n_asu_unique = hkl_metadata.get("n_unique_asu", 0)
            if n_asu_unique == 0:
                # Fall back to computing max ASU index + 1 from asu_map tensor
                n_asu_unique = int(asu_indices.max().item()) + 1
            config_stage_b_mode_override = "per_reflection"
        else:
            # No pre-computed ASU map; compute it via cctbx fallback
            halo_mask = hkl_metadata.get("halo_mask")  # 3D boolean array
            if context is not None and hasattr(context, 'halo_mask') and context.halo_mask is not None:
                halo_mask = context.halo_mask  # Prefer context-provided halo_mask
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

                # Get HKL indices grid from metadata or context (ARCH-REFINE-001 Phase B.3)
                hkl_indices_grid = None
                if context is not None and hasattr(context, 'hkl_indices_grid') and context.hkl_indices_grid is not None:
                    hkl_indices_grid = context.hkl_indices_grid  # Prefer context-provided grid
                if hkl_indices_grid is None:
                    hkl_indices_grid = hkl_metadata.get("hkl_indices_grid")
                if hkl_indices_grid is None:
                    # HKL indices grid not in metadata/context, build it from grid bounds
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

    # ARCH-STAGE-CONTEXT-001 Phase B.3.2: Build telemetry state dataclass
    # Instantiate StageBTelemetryState with explicit field values to match existing dict behavior
    telemetry_state = StageBTelemetryState(
        iteration_count=[0],
        loss_trace_sample=loss_trace_sample_b,
        loss_trace_full=loss_trace_full_b,
        best_loss_full=best_loss_full_b,
        best_params_snapshot=best_params_snapshot_b,
        chi_squared_trace_sample=chi_squared_trace_sample_b,
        chi_squared_trace_full=chi_squared_trace_full_b,
        chi_squared_best=chi_squared_best_b,
        masked_mse_trace_sample=masked_mse_trace_sample_b,
        masked_mse_trace_full=masked_mse_trace_full_b,
        masked_mse_best=masked_mse_best_b,
        perf_closure_evals=[0],
        perf_validation_runs=[0],
        perf_forward_times_ms=[],
        variance_floor_clamped_pixels=variance_floor_clamped_pixels_b,
        variance_floor_masked_pixels=variance_floor_masked_pixels_b,
        sigma_floor_sq_tensor=None,  # Will be set during closure execution
    )

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
        'canonical_baseline': canonical_baseline,  # REFINE-FLOW-001: Thread baseline for parity guard
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



# ARCH-STAGE-CONTEXT-001 Phase B.2: _build_stage_b_lbfgs_closure moved to StageB._build_lbfgs_closure
# This helper export is now retired. StageB.run owns the closure construction directly,
# keeping the nested compute_loss_stage_b / closure_stage_b functions, the RefinementSharedContext
# typed path, CPU fallback routing, and env-gated panel diagnostics hook intact.
# See dbex/refinement/stage_b.py::StageB._build_lbfgs_closure for the current implementation.


def _run_stage_b_lbfgs(
    config: 'RefinementConfig',
    device: torch.device,
    dtype: torch.dtype,
    param_values: Dict[str, Any],
    closure_stage_b: Callable[[], torch.Tensor],
    compute_loss_stage_b: Callable[[List[int], bool, bool], Tuple[torch.Tensor, torch.Tensor]],
    n_panels: int,
    collector: Any,
) -> Dict[str, Any]:
    """
    Run LBFGS optimization for Stage B shell modifier refinement.

    Args:
        collector: StageBTelemetryCollector for observer-based telemetry
                   (ARCH-TELEMETRY-001 Phase C.1). Required parameter.

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
    # ARCH-STAGE-CONTEXT-001 Phase B.3.2: Extract telemetry from dataclass (with dict compat)
    telemetry = param_values['telemetry_state']
    if isinstance(telemetry, dict):
        loss_trace_full_b = telemetry['loss_trace_full_b']
        chi_squared_trace_full_b = telemetry['chi_squared_trace_full_b']
        masked_mse_trace_full_b = telemetry['masked_mse_trace_full_b']
        loss_trace_sample_b = telemetry['loss_trace_sample_b']
        best_params_snapshot_b = telemetry['best_params_snapshot_b']
    else:
        loss_trace_full_b = telemetry.loss_trace_full
        chi_squared_trace_full_b = telemetry.chi_squared_trace_full
        masked_mse_trace_full_b = telemetry.masked_mse_trace_full
        loss_trace_sample_b = telemetry.loss_trace_sample
        best_params_snapshot_b = telemetry.best_params_snapshot
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

            # Phase 7: Mode-aware best params snapshot
            # ARCH-STAGE-CONTEXT-001 Phase B.3.2: Handle both list and dict snapshot types
            snapshot_data = {}
            if param_values['stage_b_mode'] == "per_reflection":
                snapshot_data['log_modifiers'] = param_values['log_modifiers'].data.clone()
            else:
                snapshot_data['shell_modifier_raw'] = param_values['shell_modifier_raw'].data.clone()

            # ARCH-TELEMETRY-001 Phase C.1: Route baseline validation through collector (observer pattern)
            # Observer path: emit baseline validation via collector
            payload = {
                'loss': float(initial_chi_squared_b.item()),
                'masked_mse': float(initial_mse_b.item()),
                'best_snapshot': snapshot_data,
            }
            collector.on_validation(
                scope='baseline',
                chi2=float(initial_chi_squared_b.item()),
                payload=payload,
            )

        # REFINE-FLOW-001: Stage B baseline parity guard
        # Compare Stage B initial chi² against Stage A canonical chi² to detect parameter reconstruction drift
        # ARCH-TELEMETRY-001 Phase C.1: Pass collector instead of telemetry_state for observer pattern
        canonical_baseline = param_values.get('canonical_baseline', {})
        _check_stage_b_baseline_parity(
            canonical_baseline=canonical_baseline,
            initial_chi_squared_b=initial_chi_squared_b,
            telemetry=collector,
            param_values=param_values,
            compute_loss_stage_b=compute_loss_stage_b,
            n_panels=n_panels,
        )

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
        # ARCH-STAGE-CONTEXT-001 Phase B.3.2: Handle both list and dict snapshot types
        snapshot_data = {}
        if param_values['stage_b_mode'] == "per_reflection":
            snapshot_data['log_modifiers'] = param_values['log_modifiers'].data.clone()
        else:
            snapshot_data['shell_modifier_raw'] = param_values['shell_modifier_raw'].data.clone()
        if isinstance(best_params_snapshot_b, list):
            best_params_snapshot_b.clear()
            best_params_snapshot_b.append(snapshot_data)
        else:
            best_params_snapshot_b.update(snapshot_data)
    if candidate_mse_value < masked_mse_best_b[0]:
        masked_mse_best_b[0] = candidate_mse_value
        masked_mse_best_b[1] = final_step

    # Phase 7: Restore best params (mode-aware)
    # ARCH-STAGE-CONTEXT-001 Phase B.3.2: Extract snapshot from list or dict
    if best_loss_full_b[0] < float('inf'):
        # Get snapshot dict: from list[0] if list-type, directly if dict-type
        snapshot_dict = best_params_snapshot_b[0] if isinstance(best_params_snapshot_b, list) else best_params_snapshot_b
        if param_values['stage_b_mode'] == "per_reflection":
            param_values['log_modifiers'].data = snapshot_dict['log_modifiers'].to(
                device=stage_b_param_device,
                dtype=dtype
            )
        else:
            param_values['shell_modifier_raw'].data = snapshot_dict['shell_modifier_raw'].to(
                device=stage_b_param_device,
                dtype=dtype
            )

    final_loss_value = chi_squared_best_b[0] if chi_squared_best_b[0] < float('inf') else candidate_loss_value
    final_mse_value = masked_mse_best_b[0] if masked_mse_best_b[0] < float('inf') else candidate_mse_value

    # ARCH-TELEMETRY-001 Phase C.1: Route final validation through collector (observer pattern)
    # Emit final validation to capture end-of-optimization metrics
    final_snapshot_data = {}
    if param_values['stage_b_mode'] == "per_reflection":
        final_snapshot_data['log_modifiers'] = param_values['log_modifiers'].data.clone()
    else:
        final_snapshot_data['shell_modifier_raw'] = param_values['shell_modifier_raw'].data.clone()
    final_payload = {
        'loss': final_loss_value,
        'masked_mse': final_mse_value,
        'best_snapshot': final_snapshot_data,
    }
    collector.on_validation(
        scope='final',
        chi2=final_loss_value,
        payload=final_payload,
    )

    # Improvement gate check (REFINE-008)
    if status_b != "error" and best_loss_full[0] is not None and best_loss_full[0] > 0:
        stage_a_final_loss = best_loss_full[0]
        improvement_b = (stage_a_final_loss - final_loss_value) / stage_a_final_loss
        if improvement_b < config.stage_b_min_loss_improvement:
            status_b = "early_stop"
            message_b = (
                f"Stage B improvement {improvement_b:.4%} < "
                f"{config.stage_b_min_loss_improvement:.4%} (calibrated gate per TORCH-REFINE-004, "
                "artifact: plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z/)"
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
