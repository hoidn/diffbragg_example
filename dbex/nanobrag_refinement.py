"""
LBFGS refinement nucleus for nanobrag_torch backend (Stage A/B/C).

Implements the staged refinement loop per:
- plans/nanobrag_integration_plan.md:172-244 (Refinement + Stage B contract)
- docs/spec-db-workflow.md:30-41 (Staging policy + LBFGS optimizer)
- docs/pytorch_runtime_checklist.md (vectorization, device/dtype neutrality)

Stage A scope:
- Parameters: global scale (ADU mode) + full crystal (a/b/c log-deltas, alpha/beta/gamma bounded angles, orientation 3-vector→quaternion)
- Loss: mean(((Bragg - target)[loss_mask]) ** 2)
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
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch


def vec_to_unit_quaternion(vec: torch.Tensor) -> torch.Tensor:
    """
    Convert 3-vector to unit quaternion for orientation perturbation.

    Maps R^3 → S^3 (unit quaternion) by treating vec as the imaginary part
    and normalizing: q = [sqrt(1 - ||v||^2), v] when ||v|| < 1, else normalize full [0, v].

    Args:
        vec: torch.Tensor shape (3,) representing orientation perturbation

    Returns:
        q: torch.Tensor shape (4,) with q[0]=w (real), q[1:4]=x,y,z (imaginary), ||q||=1
    """
    # Clamp norm to prevent gradient issues at ||v|| = 1
    norm_sq = (vec ** 2).sum()
    norm_sq_clamped = torch.clamp(norm_sq, max=0.99)

    # Real part: w = sqrt(1 - ||v||^2)
    w = torch.sqrt(1.0 - norm_sq_clamped)

    # Quaternion [w, x, y, z]
    q = torch.cat([w.unsqueeze(0), vec])

    # Normalize to ensure unit quaternion (handles edge cases)
    q = q / (q.norm() + 1e-8)

    return q


def quaternion_to_rotation_matrix(q: torch.Tensor) -> torch.Tensor:
    """
    Convert unit quaternion to 3×3 rotation matrix.

    Args:
        q: torch.Tensor shape (4,) with q[0]=w, q[1:4]=x,y,z, ||q||=1

    Returns:
        R: torch.Tensor shape (3, 3) rotation matrix
    """
    w, x, y, z = q[0], q[1], q[2], q[3]

    # Build rotation matrix per standard quaternion→matrix formula
    R = torch.stack([
        torch.stack([1 - 2*(y**2 + z**2), 2*(x*y - w*z), 2*(x*z + w*y)]),
        torch.stack([2*(x*y + w*z), 1 - 2*(x**2 + z**2), 2*(y*z - w*x)]),
        torch.stack([2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x**2 + y**2)])
    ])

    return R


def quaternion_to_xyz_euler(q: torch.Tensor) -> torch.Tensor:
    """
    Convert unit quaternion to XYZ extrinsic Euler angles (degrees).

    Per docs/spec-db-workflow.md:30 and docs/nanobrag_api.md:55-56, orientation
    is controlled via misset_deg XYZ extrinsic rotations applied after MOSFLM A*.

    Args:
        q: torch.Tensor of shape (4,) representing unit quaternion [w, x, y, z]
           where w is the scalar part

    Returns:
        xyz_deg: torch.Tensor of shape (3,) with XYZ extrinsic Euler angles in degrees
                 Convention: R = R_z(gamma) @ R_y(beta) @ R_x(alpha) (extrinsic XYZ)

    References:
        - reports/maintainer_responses.md:685 — misset_deg applied as XYZ extrinsic rotations
        - plans/nanobrag_integration_plan.md:114 — quaternion→XYZ conversion pattern
    """
    # Normalize quaternion to ensure unit length (differentiable)
    q = q / torch.sqrt(torch.sum(q**2) + 1e-8)

    w, x, y, z = q[0], q[1], q[2], q[3]

    # XYZ extrinsic Euler angles from quaternion
    # R = R_z(gamma) @ R_y(beta) @ R_x(alpha)
    # See: https://en.wikipedia.org/wiki/Conversion_between_quaternions_and_Euler_angles

    # Roll (alpha, rotation about X-axis)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x**2 + y**2)
    alpha_rad = torch.atan2(sinr_cosp, cosr_cosp)

    # Pitch (beta, rotation about Y-axis)
    sinp = 2 * (w * y - z * x)
    # Clamp to avoid NaN from asin at ±1
    sinp = torch.clamp(sinp, -1.0, 1.0)
    beta_rad = torch.asin(sinp)

    # Yaw (gamma, rotation about Z-axis)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y**2 + z**2)
    gamma_rad = torch.atan2(siny_cosp, cosy_cosp)

    # Convert to degrees
    xyz_deg = torch.stack([alpha_rad, beta_rad, gamma_rad]) * (180.0 / np.pi)

    return xyz_deg


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
    stage_b_mode: str = "shell"  # "shell" (production) or "per_reflection" (parity, deferred)
    stage_b_n_shells: int = 5  # Number of resolution shells for shell mode
    stage_b_min_loss_improvement: float = 1e-8  # 0.000001% minimum improvement for Stage B (calibrated per TORCH-REFINE-004 refGeom probe: measured ceiling ~6.4e-8%, essentially zero)
    stage_b_max_modifier: float = 2.0  # Maximum shell modifier (softplus clamp)
    stage_b_regularization: float = 0.0  # L2 regularization strength (reserved for future)
    stage_b_full_eval_on_cpu: bool = True  # Run Stage B evaluations on CPU to avoid GPU OOM when gradients require large buffers

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

    # Telemetry output directory (TORCH-GEOMETRY-CONVERGENCE-001 Phase A1)
    # When set, enables per-step telemetry emission for convergence diagnosis
    telemetry_output_dir: Optional[str] = None

    # Device/dtype
    device: str = "cpu"
    dtype: torch.dtype = torch.float32


@dataclass
class StageAROIEntry:
    """Cached ROI detector + simulator pair for Stage A warm cache."""
    roi_index: int
    panel_id: int
    bbox: Tuple[int, int, int, int]
    slow_slice: slice
    fast_slice: slice
    detector_model: Any
    simulator: Any


@dataclass
class StageAContext:
    """
    Cached detector models and tensors for Stage A refinement (PERF-WARM-SIM-001).

    Hoists per-panel Detector model instantiation, mask tensorization, and HKL grid
    transfers out of the LBFGS closure. The closure then only updates parameter tensors
    and runs forward passes through cached models, eliminating repeated construction overhead.
    When ROI sampling is enabled, this context additionally stores cropped Detector/Simulator
    pairs per ROI so closures can simulate only the requested bounding boxes.

    Fields:
        detector_configs: List of DetectorConfig objects per panel (length n_panels)
        detector_models: List of Detector model instances per panel (length n_panels)
        simulators: List of Simulator instances per panel cached with detector/beam state
        roi_entries: Optional list of StageAROIEntry objects (length roi_count when ROI cache enabled)
        beam_config: Single BeamConfig shared across all panels/ROIs
        trusted_masks_t: torch.Tensor stacked trusted masks [panel, slow, fast] (dtype=bool)
        baseline_distance_mm: List of baseline detector distances per panel (length n_panels)
        hkl_grid: torch.Tensor structure factor grid on target device
        hkl_metadata: dict with grid dimensions and halo status
        device: torch device for all tensors
        dtype: torch dtype for all tensors
        n_panels: int, number of panels
        roi_count: int, number of cached ROI entries
        enable_hkl_interpolation: bool, tricubic interpolation flag
        q_params: Optional quaternion parameters for U-matrix path (TORCH-GEOMETRY-PARITY-002 Phase B4)
        B_ideal_reciprocal: Optional B_ideal matrix for U-matrix path (TORCH-GEOMETRY-PARITY-002 Phase B4)
    """
    detector_configs: List
    detector_models: List
    simulators: List
    roi_entries: Optional[List[StageAROIEntry]]
    beam_config: object
    trusted_masks_t: Optional[torch.Tensor]
    baseline_distance_mm: List[float]
    hkl_grid: torch.Tensor
    hkl_metadata: Dict
    device: torch.device
    dtype: torch.dtype
    n_panels: int
    roi_count: int
    enable_hkl_interpolation: bool
    q_params: Optional[torch.Tensor] = None
    B_ideal_reciprocal: Optional[torch.Tensor] = None


@dataclass
class RefinementTelemetry:
    """Telemetry captured during refinement.

    For multi-stage refinement (Stage A + Stage C), this structure represents
    a single stage. The calling code aggregates multiple telemetry objects into
    a Dict[str, RefinementTelemetry] keyed by stage label ("A", "C").

    PHYSICS-LOSS-001: Tracks both chi_squared (variance-weighted loss, the optimization objective)
    and masked_mse (legacy metric for comparison). All stages minimize chi_squared per spec-db-core.md:57-68.
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
    loss_trace_sample: List[float]  # Deprecated: will be chi_squared_trace_sample after PHYSICS-LOSS-001
    loss_trace_full: List[Tuple[int, float]]  # Deprecated: will be chi_squared_trace_full after PHYSICS-LOSS-001
    best_loss_full: Tuple[float, int]  # Deprecated: will be chi_squared_best after PHYSICS-LOSS-001
    param_deltas: Dict[str, float]
    status: str  # "ok" | "early_stop" | "rollback" | "error"
    message: str
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
    # PHYSICS-LOSS-003: Canonical Stage A snapshot propagated to downstream stages
    canonical_stage_label: Optional[str] = None
    canonical_chi_squared: Optional[float] = None
    canonical_chi_squared_iteration: Optional[int] = None
    canonical_roi_count: Optional[int] = None
    canonical_detector_distances_mm: Optional[List[float]] = None
    roi_mode: Optional[str] = None


def _compute_variance_weighted_loss(
    bragg_tensor: torch.Tensor,
    target_tensor: torch.Tensor,
    loss_mask: torch.Tensor,
    sigma_tensor: torch.Tensor,
    sigma_floor_sq_tensor: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor, int, int]:
    """
    Sum variance-weighted chi-squared + masked-MSE per spec-db-core.md:57-80.

    Returns:
        chi-squared sum, masked-MSE value, masked pixel count, clamp pixel count.
    """
    variance_raw = bragg_tensor.detach() + sigma_tensor ** 2
    variance = torch.maximum(variance_raw, sigma_floor_sq_tensor)

    mask_bool = loss_mask
    masked_pixels = int(mask_bool.sum().item())
    clamped_pixels = int(((variance_raw < sigma_floor_sq_tensor) & mask_bool).sum().item())

    diff = bragg_tensor - target_tensor
    squared_error = diff ** 2
    masked_squared_error = torch.where(mask_bool, squared_error, torch.zeros_like(squared_error))

    weighted_error = squared_error / variance
    masked_weighted_error = torch.where(mask_bool, weighted_error, torch.zeros_like(weighted_error))
    chi_squared_sum = masked_weighted_error.sum()

    if masked_pixels > 0:
        masked_mse_value = masked_squared_error.sum() / masked_pixels
    else:
        masked_mse_value = masked_squared_error.sum()

    return chi_squared_sum, masked_mse_value, masked_pixels, clamped_pixels


def _get_sigma_floor_sq_tensor(
    cache: Dict[Tuple[str, torch.dtype], torch.Tensor],
    device: torch.device,
    dtype: torch.dtype,
    sigma_floor_value: float,
) -> torch.Tensor:
    """Cache sigma_floor^2 scalars per (device, dtype) to avoid re-allocation."""
    key = (str(device), dtype)
    tensor = cache.get(key)
    if tensor is None:
        tensor = torch.tensor(sigma_floor_value ** 2, device=device, dtype=dtype)
        cache[key] = tensor
    return tensor


def _build_stage_a_context(
    detector,
    beam,
    crystal,
    trusted_mask,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    enable_hkl_interpolation: bool,
    device: torch.device,
    dtype: torch.dtype,
    panel_slices,
    enable_roi_mode: bool,
) -> StageAContext:
    """
    Prebuild Stage A detector models and tensorize masks/HKL once (PERF-WARM-SIM-001).

    This helper constructs all per-panel Detector models, tensorizes trusted masks,
    and transfers the HKL grid to the target device. The LBFGS closure then reuses
    these cached models and only updates Crystal parameter tensors per iteration,
    eliminating repeated construction overhead.

    Args:
        detector: dxtbx Detector object (multi-panel)
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object providing baseline configuration
        trusted_mask: numpy array or tuple of masks [panel, slow, fast]
        hkl_grid: torch.Tensor structure factor grid (P1 dense)
        hkl_metadata: dict with grid dimensions and halo status
        enable_hkl_interpolation: bool, tricubic interpolation flag
        device: torch device
        dtype: torch dtype
        panel_slices: List of (panel_id, bbox) tuples describing ROI bounds
        enable_roi_mode: bool flag for ROI cache construction

    Returns:
        StageAContext with prebuilt models and tensorized data
    """
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from nanobrag_torch.simulator import Simulator
    from dbex.nanobrag_bridge import (
        create_detector_config,
        create_beam_config,
        create_crystal_config,
    )

    n_panels = len(detector)

    # Build detector configs and models per panel
    detector_configs = []
    detector_models = []
    simulators = []
    trusted_masks_t_list: List[torch.Tensor] = []
    roi_entries: List[StageAROIEntry] = []
    baseline_distance_mm: List[float] = []

    beam_config = create_beam_config(beam)
    hkl_grid_device = hkl_grid.to(device=device, dtype=dtype)
    crystal_config, _ = create_crystal_config(crystal, None)

    # DIAGNOSTIC: Crystal config post-bridge (temp)
    device_str = str(device)
    device_label = "CUDA" if "cuda" in device_str else "CPU"
    print(f"[CRYSTAL_{device_label}_POST] cell_a={crystal_config.cell_a}, cell_b={crystal_config.cell_b}, cell_c={crystal_config.cell_c}")
    print(f"[CRYSTAL_{device_label}_POST] cell_alpha={crystal_config.cell_alpha}, cell_beta={crystal_config.cell_beta}, cell_gamma={crystal_config.cell_gamma}")
    print(f"[CRYSTAL_{device_label}_POST] mosflm_a_star={getattr(crystal_config, 'mosflm_a_star', None)}")
    print(f"[CRYSTAL_{device_label}_POST] mosflm_b_star={getattr(crystal_config, 'mosflm_b_star', None)}")
    print(f"[CRYSTAL_{device_label}_POST] mosflm_c_star={getattr(crystal_config, 'mosflm_c_star', None)}")
    print(f"[CRYSTAL_{device_label}_POST] misset_deg={getattr(crystal_config, 'misset_deg', None)}")
    print(f"[CRYSTAL_{device_label}_POST] device={device}")

    base_crystal_model = Crystal(crystal_config, beam_config=beam_config, device=device, dtype=dtype)
    base_crystal_model.interpolate = enable_hkl_interpolation
    base_crystal_model.hkl_data = hkl_grid_device
    base_crystal_model.hkl_metadata = hkl_metadata

    for pid in range(n_panels):
        panel = detector[pid]

        # Capture baseline distance for Stage C retargeting (PERF-WARM-SIM-001)
        baseline_distance_mm.append(panel.get_directed_distance())

        # Create detector config
        detector_config = create_detector_config(
            panel=panel,
            beam=beam,
            trusted_mask=trusted_mask[pid]
        )

        # Convert mask_array to torch.Tensor if it's a numpy array
        # Per dbex/nanobrag_bridge.py:998-1004, nanobrag_torch Simulator
        # expects torch.Tensor for mask_array
        mask_array = detector_config.mask_array
        if mask_array is not None and not isinstance(mask_array, torch.Tensor):
            mask_array = torch.tensor(mask_array, dtype=torch.float32, device=device)
            detector_config.mask_array = mask_array
        elif mask_array is not None and (mask_array.device != device or mask_array.dtype != torch.float32):
            mask_array = mask_array.to(device=device, dtype=torch.float32)
            detector_config.mask_array = mask_array

        # Instantiate Detector model
        detector_model = Detector(detector_config, device=device, dtype=dtype)

        detector_configs.append(detector_config)
        detector_models.append(detector_model)

        simulator = Simulator(
            detector=detector_model,
            crystal=base_crystal_model,
            beam_config=beam_config,
            device=device,
            dtype=dtype,
        )
        simulators.append(simulator)

        # Tensorize trusted mask (bool) for reuse in loss masks
        mask_bool = torch.as_tensor(trusted_mask[pid], dtype=torch.bool, device=device)
        trusted_masks_t_list.append(mask_bool)

    if enable_roi_mode and panel_slices:
        for roi_index, (pid, bbox) in enumerate(panel_slices):
            x0, x1, y0, y1 = bbox
            panel = detector[int(pid)]
            detector_config = create_detector_config(
                panel=panel,
                beam=beam,
                trusted_mask=trusted_mask[int(pid)],
                roi_bbox=bbox,
            )
            mask_array = detector_config.mask_array
            if mask_array is not None and not isinstance(mask_array, torch.Tensor):
                mask_array = torch.tensor(mask_array, dtype=torch.float32, device=device)
                detector_config.mask_array = mask_array
            elif mask_array is not None and (mask_array.device != device or mask_array.dtype != torch.float32):
                mask_array = mask_array.to(device=device, dtype=torch.float32)
                detector_config.mask_array = mask_array

            detector_model = Detector(detector_config, device=device, dtype=dtype)
            simulator = Simulator(
                detector=detector_model,
                crystal=base_crystal_model,
                beam_config=beam_config,
                device=device,
                dtype=dtype,
            )
            roi_entries.append(
                StageAROIEntry(
                    roi_index=roi_index,
                    panel_id=int(pid),
                    bbox=tuple(int(v) for v in bbox),
                    slow_slice=slice(int(y0), int(y1)),
                    fast_slice=slice(int(x0), int(x1)),
                    detector_model=detector_model,
                    simulator=simulator,
                )
            )

    trusted_masks_t = torch.stack(trusted_masks_t_list, dim=0) if trusted_masks_t_list else None

    return StageAContext(
        detector_configs=detector_configs,
        detector_models=detector_models,
        simulators=simulators,
        roi_entries=roi_entries if roi_entries else None,
        beam_config=beam_config,
        trusted_masks_t=trusted_masks_t,
        baseline_distance_mm=baseline_distance_mm,
        hkl_grid=hkl_grid_device,
        hkl_metadata=hkl_metadata,
        device=device,
        dtype=dtype,
        n_panels=n_panels,
        roi_count=len(roi_entries),
        enable_hkl_interpolation=enable_hkl_interpolation
    )


def _sync_stage_a_crystal(stage_a_ctx: StageAContext, crystal_model):
    """
    Ensure the warmed Crystal carries the cached HKL grid + interpolation flag.
    """
    crystal_model.interpolate = stage_a_ctx.enable_hkl_interpolation
    crystal_model.hkl_data = stage_a_ctx.hkl_grid
    crystal_model.hkl_metadata = stage_a_ctx.hkl_metadata
    # Allow Simulator fallback (when beam_config argument omitted) to pick up cached beam config
    crystal_model.beam_config = stage_a_ctx.beam_config  # type: ignore[attr-defined]
    return crystal_model


def _retarget_stage_a_simulators(stage_a_ctx: StageAContext, crystal_model) -> None:
    """
    Attach the warmed Crystal to every cached Simulator so ROI/pixel caches stay hot.
    """
    for simulator in stage_a_ctx.simulators:
        simulator.crystal = crystal_model
        simulator.beam_config = stage_a_ctx.beam_config
    if stage_a_ctx.roi_entries:
        for entry in stage_a_ctx.roi_entries:
            entry.simulator.crystal = crystal_model
            entry.simulator.beam_config = stage_a_ctx.beam_config


def _build_stage_a_params(
    crystal,
    detector,
    inputs,
    config: RefinementConfig,
    device,
    dtype,
    hkl_grid,
    hkl_metadata,
    sigma_floor_sq_cache,
    baseline_crystal,
    baseline_detector,
    beam
):
    """
    Build trainable parameters for Stage A LBFGS refinement.

    Supports 3 parameterization modes:
    - cell + misset (default)
    - U-matrix (config.use_u_matrix_parameterization=True)
    - incremental UB (config.use_incremental_ub=True)

    Returns:
        Dict with keys: params, param_values, telemetry_state, stage_a_context, optimizer
    """
    # Initialize refinement parameters
    # Stage A expansion: global scale + full crystal (a/b/c logs, alpha/beta/gamma bounded, orientation)

    # 1. log_scale: global intensity scale
    # Warm-start from global_scale_hint when available (per spec-db-workflow.md:20-40, REFINE-001)
    if inputs.global_scale_hint is not None and inputs.global_scale_hint > 0:
        initial_log_scale = float(torch.log(torch.tensor(inputs.global_scale_hint, dtype=dtype)))
    else:
        initial_log_scale = 0.0  # fallback: scale=1.0
    log_scale = torch.tensor(initial_log_scale, device=device, dtype=dtype, requires_grad=True)

    # 2. Unit cell length deltas (log parameterization for positivity)
    log_cell_a_delta = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    log_cell_b_delta = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    log_cell_c_delta = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)

    # 3. Unit cell angle deltas (unbounded, will be mapped via tanh to bounded range)
    # angles in degrees: alpha, beta, gamma typically near 90° for orthorhombic/cubic
    # Use tanh(x) * max_delta to bound perturbations (e.g., ±10°)
    angle_alpha_raw = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    angle_beta_raw = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    angle_gamma_raw = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)

    # 4. Orientation perturbation (3-vector that will be converted to unit quaternion)
    # Initialize to small values near identity rotation
    orientation_vec = torch.zeros(3, device=device, dtype=dtype, requires_grad=True)

    # TORCH-GEOMETRY-PARITY-002 Phase B4: U-matrix quaternion parameterization (opt-in)
    q_params = None
    B_ideal_reciprocal_torch = None
    if config.use_u_matrix_parameterization:
        from dbex.nanobrag_bridge import (
            derive_u_matrix_from_mosflm_a_star,
            matrix_to_quaternion,
        )
        # Extract MOSFLM A* from the crystal (mapping zero point)
        A_star_np = np.array(crystal.get_A()).reshape(3, 3)
        cell_params = crystal.get_unit_cell().parameters()

        # Derive U-matrix from mapping MOSFLM A* (no SO(3) projection)
        # Get BOTH U and B_ideal from same TorchCrystal computation (CONVERGENCE-001 bugfix)
        # CRITICAL FIX (Phase B Deep Diagnostic): Use the MOSFLM-derived B_ideal, do NOT recompute from cctbx
        U_0, B_ideal_reciprocal_np = derive_u_matrix_from_mosflm_a_star(A_star_np, cell_params)

        # Convert to quaternion
        q_0 = matrix_to_quaternion(torch.tensor(U_0, dtype=torch.float64))

        # Initialize trainable quaternion params (float64 for precision)
        q_params = q_0.clone().to(device=device, dtype=dtype).requires_grad_(True)

        # Use the MOSFLM-derived B_ideal (ensures U @ B_ideal == A*_MOSFLM at initialization)
        # Prior bug: recomputed B_ideal from cctbx cell, causing catastrophic chi²=1.425B divergence
        # Root cause: cctbx cell.parameters() → TorchCrystal → compute_cell_tensors() produces
        # DIFFERENT B_ideal than MOSFLM A* decomposition, breaking U @ B_ideal = A*_MOSFLM invariant
        B_ideal_reciprocal_torch = torch.tensor(B_ideal_reciprocal_np, device=device, dtype=dtype)

    # TORCH-GEOMETRY-UB-REALIGN-001 Phase B3: Incremental UB parameterization (opt-in)
    # Trainable parameters for incremental UB path:
    #   - q_delta: quaternion delta [w,x,y,z] (4 params), identity = [1,0,0,0]
    #   - delta_log_a/b/c: log-perturbations for cell lengths (3 params), zero = no change
    #   - delta_alpha/beta/gamma: angle deltas in degrees (3 params), zero = no change
    #   - log_scale: global intensity scale (1 param, shared with default path)
    # Total: 10 DOF (4 orientation + 3 lengths + 3 angles)
    q_delta = None
    delta_log_a = None
    delta_log_b = None
    delta_log_c = None
    delta_alpha = None
    delta_beta = None
    delta_gamma = None
    U_baseline = None
    cell_baseline = None
    if config.use_incremental_ub:
        # Extract baseline crystal state from dxtbx
        U_baseline = torch.tensor(
            np.array(crystal.get_U()).reshape(3, 3),
            dtype=dtype,
            device=device
        )
        unit_cell = crystal.get_unit_cell()
        cell_baseline = torch.tensor(
            [unit_cell.parameters()[i] for i in range(6)],  # [a, b, c, α, β, γ]
            dtype=dtype,
            device=device
        )

        # Initialize quaternion delta to identity [w=1, x=0, y=0, z=0]
        q_delta = torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=dtype, device=device, requires_grad=True)

        # Initialize cell perturbations to zero (no change at params=0)
        delta_log_a = torch.tensor(0.0, dtype=dtype, device=device, requires_grad=True)
        delta_log_b = torch.tensor(0.0, dtype=dtype, device=device, requires_grad=True)
        delta_log_c = torch.tensor(0.0, dtype=dtype, device=device, requires_grad=True)
        delta_alpha = torch.tensor(0.0, dtype=dtype, device=device, requires_grad=True)
        delta_beta = torch.tensor(0.0, dtype=dtype, device=device, requires_grad=True)
        delta_gamma = torch.tensor(0.0, dtype=dtype, device=device, requires_grad=True)

    params = [
        log_scale,
        log_cell_a_delta, log_cell_b_delta, log_cell_c_delta,
        angle_alpha_raw, angle_beta_raw, angle_gamma_raw,
        orientation_vec
    ]

    # Add q_params to optimizer if U-matrix mode is enabled
    if config.use_u_matrix_parameterization:
        params.append(q_params)

    # Add incremental UB params to optimizer if incremental UB mode is enabled
    if config.use_incremental_ub:
        params = [
            log_scale,
            q_delta,
            delta_log_a, delta_log_b, delta_log_c,
            delta_alpha, delta_beta, delta_gamma
        ]

    # Setup LBFGS optimizer
    optimizer = torch.optim.LBFGS(
        params,
        history_size=config.history_size,
        max_iter=config.max_iter,
        tolerance_grad=config.tolerance_grad,
        tolerance_change=config.tolerance_change,
        line_search_fn="strong_wolfe"  # Enable strong Wolfe line search for stability
    )

    # Telemetry accumulators
    loss_trace_sample = []  # Deprecated: chi_squared only (PHYSICS-LOSS-001)
    loss_trace_full = []  # Deprecated: chi_squared only (PHYSICS-LOSS-001)
    best_loss_full = (float('inf'), -1)  # Deprecated: chi_squared only (PHYSICS-LOSS-001)
    best_params_snapshot = None
    iteration_count = [0]  # Mutable counter for closure

    # PHYSICS-LOSS-001: Dual metric tracking (chi_squared + masked_mse)
    chi_squared_trace_sample = []
    chi_squared_trace_full = []
    chi_squared_best = (float('inf'), -1)
    masked_mse_trace_sample = []
    masked_mse_trace_full = []
    masked_mse_best = (float('inf'), -1)

    # Perf counters (PERF-WARM-SIM-001)
    perf_closure_evals = [0]  # Total closure calls
    perf_validation_runs = [0]  # Full validation runs
    perf_forward_times_ms = []  # Per-closure forward pass timings

    # PHYSICS-LOSS-002: Variance floor clamp statistics
    variance_floor_clamped_pixels = [0]  # Total pixels where floor engaged
    variance_floor_masked_pixels = [0]  # Total masked pixels evaluated
    sigma_floor_sq_tensor = _get_sigma_floor_sq_tensor(
        sigma_floor_sq_cache, device, dtype, config.sigma_floor_value
    )

    # Deterministic ROI/Panel sampling seeds
    np.random.seed(42)  # Fixed seed for deterministic behavior
    n_panels = len(detector)
    baseline_detector_distances = None
    if baseline_detector is not None:
        if len(baseline_detector) != n_panels:
            raise ValueError(
                "baseline_detector must have the same number of panels as detector"
            )
        baseline_detector_distances = [
            baseline_detector[pid].get_directed_distance() for pid in range(n_panels)
        ]
    panel_shape = inputs.target.shape[1:]  # (slow, fast)
    panel_slices = inputs.panel_slices
    canonical_roi_count = len(panel_slices)
    if baseline_detector_distances is not None:
        canonical_detector_distances = list(baseline_detector_distances)
    else:
        canonical_detector_distances = [
            detector[pid].get_directed_distance() for pid in range(n_panels)
        ]
    canonical_baseline = {
        "stage_label": "A",
        "chi_squared": None,
        "iteration": None,
        "roi_count": canonical_roi_count,
        "detector_distances_mm": canonical_detector_distances,
    }

    # Sample panels (~15%) for Stage B reuse + fallback
    sampled_panel_ids = sorted(
        np.random.choice(
            n_panels,
            size=max(1, int(n_panels * config.roi_sample_fraction)),
            replace=False,
        ).tolist()
    )

    # Stage A ROI sampling (panel_slices-defined) with fallback to panel sampling
    use_stage_a_roi_mode = bool(
        config.enable_stage_a_roi_mode
        and canonical_roi_count > 0
        and (config.enable_stage_a_warm_cache or config.allow_cold_stage_a_roi_mode)
    )
    stage_a_roi_label = "roi" if use_stage_a_roi_mode else "panel"
    stage_a_total_work_items = canonical_roi_count if use_stage_a_roi_mode else n_panels
    if use_stage_a_roi_mode:
        roi_sample_size = max(1, int(stage_a_total_work_items * config.roi_sample_fraction))
        roi_sample_size = min(stage_a_total_work_items, roi_sample_size)
        sampled_stage_a_indices = sorted(
            np.random.choice(stage_a_total_work_items, size=roi_sample_size, replace=False).tolist()
        )
    else:
        sampled_stage_a_indices = list(sampled_panel_ids)
    full_stage_a_indices = list(range(stage_a_total_work_items))

    # Build Stage A context conditionally (PERF-WARM-SIM-001)
    # When warm cache is enabled (default), prebuild detector models and tensorize masks once
    # for 2-5× speedup. When disabled (benchmarking), rebuild inside compute_loss for cold baseline.
    stage_a_ctx = None
    if config.enable_stage_a_warm_cache:
        # DIAGNOSTIC: CUDA crystal config comparison (temp)
        print(f"[CRYSTAL_CUDA_PRE] cell={crystal.get_unit_cell().parameters()}")
        print(f"[CRYSTAL_CUDA_PRE] A_matrix={np.array(crystal.get_A()).reshape(3,3).tolist()}")
        print(f"[CRYSTAL_CUDA_PRE] U_matrix={np.array(crystal.get_U()).reshape(3,3).tolist()}")
        print(f"[CRYSTAL_CUDA_PRE] B_matrix={np.array(crystal.get_B()).reshape(3,3).tolist()}")

        stage_a_ctx = _build_stage_a_context(
            detector=detector,
            beam=beam,
            crystal=crystal,
            trusted_mask=inputs.trusted_mask,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            enable_hkl_interpolation=config.enable_hkl_interpolation,
            device=device,
            dtype=dtype,
            panel_slices=panel_slices,
            enable_roi_mode=use_stage_a_roi_mode,
        )

    # Telemetry step counter (TORCH-GEOMETRY-CONVERGENCE-001 Phase A1)
    # Mutable list for closure capture; increments after each closure call
    telemetry_step_counter = [0]

    # Lifecycle tracking for U-matrix and A* reconstruction (TORCH-GEOMETRY-CONVERGENCE-001 Phase B4)
    u_matrix_lifecycle_log = []  # Track U checksum per closure call
    a_star_lifecycle_log = []    # Track A* reconstruction per closure call

    # Build param_values dict for return
    param_values = {
        'initial_log_scale': initial_log_scale,  # Store initial value for telemetry
        'log_scale': log_scale,
        'log_cell_a_delta': log_cell_a_delta,
        'log_cell_b_delta': log_cell_b_delta,
        'log_cell_c_delta': log_cell_c_delta,
        'angle_alpha_raw': angle_alpha_raw,
        'angle_beta_raw': angle_beta_raw,
        'angle_gamma_raw': angle_gamma_raw,
        'orientation_vec': orientation_vec,
        'params': params,  # List of Parameter objects for optimizer
        'optimizer': optimizer,  # LBFGS optimizer for closure
        'q_params': q_params,
        'B_ideal_reciprocal_torch': B_ideal_reciprocal_torch,
        'q_delta': q_delta,
        'delta_log_a': delta_log_a,
        'delta_log_b': delta_log_b,
        'delta_log_c': delta_log_c,
        'delta_alpha': delta_alpha,
        'delta_beta': delta_beta,
        'delta_gamma': delta_gamma,
        'U_baseline': U_baseline,
        'cell_baseline': cell_baseline,
    }

    # Build telemetry_state dict
    telemetry_state = {
        'loss_trace_sample': loss_trace_sample,
        'loss_trace_full': loss_trace_full,
        'best_loss_full': best_loss_full,
        'best_params_snapshot': best_params_snapshot,
        'iteration_count': iteration_count,
        'chi_squared_trace_sample': chi_squared_trace_sample,
        'chi_squared_trace_full': chi_squared_trace_full,
        'chi_squared_best': chi_squared_best,
        'masked_mse_trace_sample': masked_mse_trace_sample,
        'masked_mse_trace_full': masked_mse_trace_full,
        'masked_mse_best': masked_mse_best,
        'perf_closure_evals': perf_closure_evals,
        'perf_validation_runs': perf_validation_runs,
        'perf_forward_times_ms': perf_forward_times_ms,
        'variance_floor_clamped_pixels': variance_floor_clamped_pixels,
        'variance_floor_masked_pixels': variance_floor_masked_pixels,
        'sigma_floor_sq_tensor': sigma_floor_sq_tensor,
        'telemetry_step_counter': telemetry_step_counter,
        'u_matrix_lifecycle_log': u_matrix_lifecycle_log,
        'a_star_lifecycle_log': a_star_lifecycle_log,
    }

    # Build stage_a_context dict
    stage_a_context = {
        'stage_a_ctx': stage_a_ctx,
        'sampled_panel_ids': sampled_panel_ids,
        'canonical_baseline': canonical_baseline,
        'use_stage_a_roi_mode': use_stage_a_roi_mode,
        'stage_a_roi_label': stage_a_roi_label,
        'stage_a_total_work_items': stage_a_total_work_items,
        'sampled_stage_a_indices': sampled_stage_a_indices,
        'full_stage_a_indices': full_stage_a_indices,
    }

    return {
        'params': params,
        'param_values': param_values,
        'telemetry_state': telemetry_state,
        'stage_a_context': stage_a_context,
        'optimizer': optimizer
    }


def _build_stage_a_lbfgs_closure(
    # Parameters from helper 1 return dict
    param_values: Dict[str, Any],
    telemetry_state: Dict[str, Any],
    stage_a_context: Dict[str, Any],
    # Additional closure context (11 params)
    crystal,
    detector,
    beam,
    inputs,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    config: 'RefinementConfig',
    sigma_floor_sq_cache: Optional[Dict],
    device,
    dtype,
    baseline_crystal
) -> Tuple['Callable', 'Callable']:
    """
    Build LBFGS closure for Stage A refinement with nested compute_loss and closure functions.

    Captures lexical scope for ~30 nonlocal variables from param_values, telemetry_state, stage_a_context.
    Supports 3 parameterization modes: cell+misset, U-matrix, incremental UB.

    Args:
        param_values: Dict with trainable tensors (log_scale, log_cell_*_delta, angle_*_raw,
                     orientation_vec, q_params, delta_log_*, delta_alpha/beta/gamma, q_delta)
        telemetry_state: Dict with mutable telemetry accumulators (loss traces, perf counters,
                        variance floor stats, lifecycle logs)
        stage_a_context: Dict with ROI/panel sampling state, warm cache context
        crystal: dxtbx Crystal object
        detector: dxtbx Detector object
        beam: dxtbx Beam object
        inputs: RefinementInputs (target, loss_mask, panel_slices, trusted_mask)
        hkl_grid: Structure factor grid tensor
        hkl_metadata: HKL metadata dict
        config: RefinementConfig (use_u_matrix_parameterization, use_incremental_ub, telemetry_output_dir)
        sigma_floor_sq_cache: Optional precomputed variance floor tensor
        device: torch device
        dtype: torch dtype
        baseline_crystal: Optional baseline dxtbx Crystal for incremental UB mode

    Returns:
        Tuple of (compute_loss, closure) callables with captured lexical scope
    """
    # Unpack param_values
    log_scale = param_values['log_scale']
    log_cell_a_delta = param_values.get('log_cell_a_delta')
    log_cell_b_delta = param_values.get('log_cell_b_delta')
    log_cell_c_delta = param_values.get('log_cell_c_delta')
    angle_alpha_raw = param_values.get('angle_alpha_raw')
    angle_beta_raw = param_values.get('angle_beta_raw')
    angle_gamma_raw = param_values.get('angle_gamma_raw')
    orientation_vec = param_values.get('orientation_vec')
    q_params = param_values.get('q_params')
    delta_log_a = param_values.get('delta_log_a')
    delta_log_b = param_values.get('delta_log_b')
    delta_log_c = param_values.get('delta_log_c')
    delta_alpha = param_values.get('delta_alpha')
    delta_beta = param_values.get('delta_beta')
    delta_gamma = param_values.get('delta_gamma')
    q_delta = param_values.get('q_delta')
    params = param_values.get('params', [])  # List of Parameter objects
    B_ideal_reciprocal_torch = param_values.get('B_ideal_reciprocal_torch')

    # Unpack telemetry_state (mutable lists/dicts for closure capture)
    iteration_count = telemetry_state['iteration_count']
    loss_trace_sample = telemetry_state['loss_trace_sample']
    loss_trace_full = telemetry_state['loss_trace_full']
    best_loss_full = telemetry_state['best_loss_full']
    best_params_snapshot = telemetry_state['best_params_snapshot']
    chi_squared_trace_sample = telemetry_state['chi_squared_trace_sample']
    chi_squared_trace_full = telemetry_state['chi_squared_trace_full']
    chi_squared_best = telemetry_state['chi_squared_best']
    masked_mse_trace_sample = telemetry_state['masked_mse_trace_sample']
    masked_mse_trace_full = telemetry_state['masked_mse_trace_full']
    masked_mse_best = telemetry_state['masked_mse_best']
    perf_closure_evals = telemetry_state['perf_closure_evals']
    perf_validation_runs = telemetry_state['perf_validation_runs']
    perf_forward_times_ms = telemetry_state['perf_forward_times_ms']
    variance_floor_clamped_pixels = telemetry_state['variance_floor_clamped_pixels']
    variance_floor_masked_pixels = telemetry_state['variance_floor_masked_pixels']
    sigma_floor_sq_tensor = telemetry_state['sigma_floor_sq_tensor']
    telemetry_step_counter = telemetry_state['telemetry_step_counter']
    u_matrix_lifecycle_log = telemetry_state.get('u_matrix_lifecycle_log', [])
    a_star_lifecycle_log = telemetry_state.get('a_star_lifecycle_log', [])

    # Unpack stage_a_context
    stage_a_ctx = stage_a_context.get('stage_a_ctx')
    sampled_panel_ids = stage_a_context.get('sampled_panel_ids')
    use_stage_a_roi_mode = stage_a_context['use_stage_a_roi_mode']
    sampled_stage_a_indices = stage_a_context['sampled_stage_a_indices']
    full_stage_a_indices = stage_a_context['full_stage_a_indices']

    # Additional context for incremental UB mode
    U_baseline = param_values.get('U_baseline')
    cell_baseline = param_values.get('cell_baseline')

    # Extract additional context needed for compute_loss
    from dbex.nanobrag_bridge import (
        create_detector_config,
        create_beam_config,
        create_crystal_config,
        compute_baseline_misset_deg,
    )

    target_t = torch.from_numpy(inputs.target).to(device=device, dtype=dtype)
    loss_mask_t = torch.from_numpy(inputs.loss_mask).to(device=device, dtype=torch.bool)
    sigma_readout_t = torch.from_numpy(inputs.sigma_readout).to(device=device, dtype=dtype)

    baseline_misset_deg_tensor = compute_baseline_misset_deg(
        crystal,
        baseline_crystal,
        device=device,
        dtype=dtype,
    )

    n_panels = len(detector)
    panel_slices = inputs.panel_slices

    # Telemetry step counter (TORCH-GEOMETRY-CONVERGENCE-001 Phase A1)
    # Mutable list for closure capture; increments after each closure call
    # NOTE: Already unpacked from telemetry_state above, but keeping these lines
    # for compatibility with original source lines 1320-1326
    # telemetry_step_counter = [0]

    # Lifecycle tracking for U-matrix and A* reconstruction (TORCH-GEOMETRY-CONVERGENCE-001 Phase B4)
    # NOTE: Already unpacked from telemetry_state above
    # u_matrix_lifecycle_log = []  # Track U checksum per closure call
    # a_star_lifecycle_log = []    # Track A* reconstruction per closure call

    def compute_loss(work_item_ids: List[int], is_full: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute variance-weighted chi-squared loss over specified work items.

        Implements spec-db-core.md:57-68 variance model:
        - Variance: V = I_model.detach() + sigma_readout^2
        - Loss: Sum((I_model - I_obs)^2 / V) over trusted pixels
        - Detached denominator implements IRLS (prevents "attraction to zero")

        Warm mode (default): Reuses cached detector models and masks (PERF-WARM-SIM-001).
        Cold mode (benchmarking): Rebuilds detector models/masks inside closure.

        Args:
            work_item_ids: List of ROI indices (when ROI sampling enabled) or panel indices
            is_full: If True, this is a full validation run

        Returns:
            Tuple of (chi_squared_loss, masked_mse_loss): Both scalar tensors for telemetry
        """
        # Time forward pass (CPU-only, PERF-WARM-SIM-001)
        t0 = time.perf_counter()

        # Compute cell/orientation parameters once per loss evaluation (shared across panels/ROIs)
        cell_params = crystal.get_unit_cell().parameters()  # (a, b, c, alpha, beta, gamma)

        # 1. Unit cell lengths (log-parameterized)
        perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
        perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
        perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)

        # 2. Unit cell angles (bounded via tanh, max perturbation ±10°)
        max_angle_delta = 10.0  # degrees
        perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
        perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
        perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

        # 3. Orientation perturbation via quaternion→XYZ misset (TORCH-REFINE-002)
        # TORCH-GEOMETRY-UB-REALIGN-001 Phase B3: Branch on incremental UB vs U-matrix vs cell+misset path
        if config.use_incremental_ub:
            # Incremental UB path: Derive A* = U(q_delta) @ B(cell_deltas)
            from dbex.nanobrag_bridge import (
                derive_orientation_from_quaternion_delta,
                derive_B_from_cell_deltas,
            )

            # Derive U(params) = ΔR(q_delta) @ U_baseline
            U_current = derive_orientation_from_quaternion_delta(
                q_delta, U_baseline, dtype=dtype, device=device
            )

            # Derive B(params) from cell perturbations
            B_current = derive_B_from_cell_deltas(
                delta_log_a, delta_log_b, delta_log_c,
                delta_alpha, delta_beta, delta_gamma,
                cell_baseline=tuple(cell_baseline.detach().cpu().numpy().tolist()),
                dtype=dtype,
                device=device
            )

            # Construct A* = U @ B (one-way construction per spec-db-core.md:64-67)
            A_star_new = U_current @ B_current  # Shape: [3, 3]

            # Extract MOSFLM a/b/c_star for crystal_config injection
            # A* columns are reciprocal lattice vectors a*, b*, c*
            a_star = A_star_new[:, 0].detach().cpu().numpy()  # Shape: [3]
            b_star = A_star_new[:, 1].detach().cpu().numpy()
            c_star = A_star_new[:, 2].detach().cpu().numpy()

            # Inject via MOSFLM a/b/c_star (per GRADIENT-001: no cell overrides with MOSFLM injection)
            crystal_overrides = {
                'mosflm_a_star': tuple(a_star.tolist()),
                'mosflm_b_star': tuple(b_star.tolist()),
                'mosflm_c_star': tuple(c_star.tolist()),
            }
            # CRITICAL: Do NOT inject cell parameters when using MOSFLM a/b/c_star (GRADIENT-001)
            misset_deg_for_crystal = None  # MOSFLM A* is provided directly

        elif config.use_u_matrix_parameterization:
            # U-matrix path: Normalize quaternion, convert to U, compute A*
            from dbex.nanobrag_bridge import quaternion_to_matrix
            q_norm = q_params / torch.norm(q_params)  # Enforce ||q|| = 1

            U = quaternion_to_matrix(q_norm)  # 3x3 rotation matrix
            A_star_new = U @ B_ideal_reciprocal_torch  # Compute updated A*

            # Lifecycle logging: U-matrix and A* reconstruction (TORCH-GEOMETRY-CONVERGENCE-001 Phase B4)
            if not is_full:
                U_checksum = U.sum().item()
                A_star_checksum = A_star_new.sum().item()
                B_ideal_checksum = B_ideal_reciprocal_torch.sum().item()

                u_matrix_lifecycle_log.append({
                    "closure_call_index": len(u_matrix_lifecycle_log),
                    "U_checksum": U_checksum,
                    "q_params_norm": torch.norm(q_params).item(),
                    "log_scale_value": log_scale.item()
                })

                a_star_lifecycle_log.append({
                    "closure_call_index": len(a_star_lifecycle_log),
                    "A_star_checksum": A_star_checksum,
                    "U_checksum": U_checksum,
                    "B_ideal_checksum": B_ideal_checksum
                })

            # Telemetry: Capture parameters (TORCH-GEOMETRY-CONVERGENCE-001 Phase B2)
            if not is_full and config.telemetry_output_dir:
                q_norm_value = torch.norm(q_params).item()
                telemetry_params = {
                    'step_index': telemetry_step_counter[0],
                    'q_params': q_params.detach().cpu().tolist(),
                    'q_norm_value': q_norm_value,
                    'log_scale': log_scale.item(),
                    'u_matrix_checksum': U.sum().item(),  # Phase B2: U-matrix checksum
                }

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
            # FIX: Define misset_deg_for_crystal here in U-matrix branch
            misset_deg_for_crystal = None  # MOSFLM A* is provided directly
        else:
            # Existing cell+misset path (GEOMETRY-003)
            max_orientation_deg = 3.0  # degrees (per input.md pitfalls)
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
            # FIX: Define misset_deg_for_crystal here in cell+misset branch
            misset_deg_for_crystal = misset_xyz_deg

        log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
        beam_config_for_run = stage_a_ctx.beam_config if stage_a_ctx is not None else create_beam_config(beam)

        warm_crystal_model: Optional['Crystal'] = None
        if stage_a_ctx is not None:
            warm_crystal_config, _ = create_crystal_config(
                crystal,
                None,
                crystal_overrides=crystal_overrides,
                misset_deg_override=misset_deg_for_crystal
            )
            from nanobrag_torch.models.crystal import Crystal
            warm_crystal_model = Crystal(
                warm_crystal_config,
                beam_config=beam_config_for_run,
                device=device,
                dtype=dtype
            )
            warm_crystal_model = _sync_stage_a_crystal(stage_a_ctx, warm_crystal_model)
            _retarget_stage_a_simulators(stage_a_ctx, warm_crystal_model)

        if use_stage_a_roi_mode:
            indices = work_item_ids if work_item_ids else full_stage_a_indices
            chi_squared_accum = torch.zeros((), device=device, dtype=dtype)
            mse_numerator_accum = torch.zeros((), device=device, dtype=dtype)
            masked_pixels_total = 0
            clamped_pixels_total = 0

            # Telemetry: Initialize variance component accumulators (TORCH-GEOMETRY-CONVERGENCE-001 Phase B2)
            if not is_full and config.telemetry_output_dir and config.use_u_matrix_parameterization:
                i_model_min_global = float('inf')
                i_model_max_global = float('-inf')
                i_model_values_list = []
                v_denom_values_list = []
                weighted_residuals_list = []

            for roi_index in indices:
                pid, bbox = panel_slices[roi_index]
                x0, x1, y0, y1 = map(int, bbox)
                slow_slice = slice(y0, y1)
                fast_slice = slice(x0, x1)

                target_subset = target_t[pid, slow_slice, fast_slice]
                mask_subset = loss_mask_t[pid, slow_slice, fast_slice]
                if stage_a_ctx is not None and stage_a_ctx.trusted_masks_t is not None:
                    trusted_slice = stage_a_ctx.trusted_masks_t[pid, slow_slice, fast_slice]
                    mask_subset = torch.logical_and(mask_subset, trusted_slice)
                sigma_subset = sigma_readout_t[pid, slow_slice, fast_slice]

                if stage_a_ctx is not None and stage_a_ctx.roi_entries:
                    simulator = stage_a_ctx.roi_entries[roi_index].simulator
                else:
                    detector_config = create_detector_config(
                        panel=detector[pid],
                        beam=beam,
                        trusted_mask=inputs.trusted_mask[pid],
                        roi_bbox=(x0, x1, y0, y1),
                    )
                    mask_array = detector_config.mask_array
                    if mask_array is not None and not isinstance(mask_array, torch.Tensor):
                        detector_config.mask_array = torch.tensor(mask_array, dtype=torch.float32, device=device)
                    elif mask_array is not None and (mask_array.device != device or mask_array.dtype != torch.float32):
                        detector_config.mask_array = mask_array.to(device=device, dtype=torch.float32)
                    from nanobrag_torch.models.detector import Detector
                    detector_model = Detector(detector_config, device=device, dtype=dtype)

                    crystal_config, _ = create_crystal_config(
                        crystal,
                        None,
                        crystal_overrides=crystal_overrides,
                        misset_deg_override=misset_deg_for_crystal
                    )
                    from nanobrag_torch.models.crystal import Crystal
                    crystal_model = Crystal(
                        crystal_config,
                        beam_config=beam_config_for_run,
                        device=device,
                        dtype=dtype
                    )
                    crystal_model.interpolate = config.enable_hkl_interpolation
                    crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
                    crystal_model.hkl_metadata = hkl_metadata

                    from nanobrag_torch.simulator import Simulator
                    simulator = Simulator(
                        detector=detector_model,
                        crystal=crystal_model,
                        beam_config=beam_config_for_run,
                        device=device,
                        dtype=dtype
                    )

                bragg_patch = simulator.run()
                bragg_scaled = bragg_patch * torch.exp(log_scale_clamped)

                chi_sq_roi, mse_roi, masked_pixels, clamped_pixels = _compute_variance_weighted_loss(
                    bragg_scaled,
                    target_subset,
                    mask_subset,
                    sigma_subset,
                    sigma_floor_sq_tensor,
                )

                # Telemetry: Capture I_model, V_denom, and weighted residuals (TORCH-GEOMETRY-CONVERGENCE-001 Phase B2)
                if not is_full and config.telemetry_output_dir and config.use_u_matrix_parameterization:
                    # I_model stats
                    i_model_values = bragg_scaled[mask_subset]
                    i_model_min_global = min(i_model_min_global, torch.min(bragg_scaled).item())
                    i_model_max_global = max(i_model_max_global, torch.max(bragg_scaled).item())
                    i_model_values_list.append(i_model_values.detach().cpu())

                    # V_denom (variance denominator) stats
                    variance_raw = bragg_scaled.detach() + sigma_subset ** 2
                    v_denom = torch.maximum(variance_raw, sigma_floor_sq_tensor)
                    v_denom_values_list.append(v_denom[mask_subset].detach().cpu())

                    # Weighted residuals stats
                    diff = bragg_scaled - target_subset
                    squared_error = diff ** 2
                    weighted_error = squared_error / v_denom
                    weighted_residuals_list.append(weighted_error[mask_subset].detach().cpu())
                chi_squared_accum = chi_squared_accum + chi_sq_roi
                mse_numerator_accum = mse_numerator_accum + (mse_roi * masked_pixels)
                masked_pixels_total += masked_pixels
                clamped_pixels_total += clamped_pixels

            if masked_pixels_total > 0:
                masked_mse_loss = mse_numerator_accum / masked_pixels_total
            else:
                masked_mse_loss = mse_numerator_accum
            chi_squared_loss = chi_squared_accum

            # Telemetry: Capture loss components and variance stats (TORCH-GEOMETRY-CONVERGENCE-001 Phase B2)
            if not is_full and config.telemetry_output_dir and config.use_u_matrix_parameterization:
                clamp_fraction = clamped_pixels_total / max(masked_pixels_total, 1)
                mean_per_pixel_chi_squared = chi_squared_loss.item() / max(masked_pixels_total, 1)

                telemetry_loss = {
                    'chi_squared': chi_squared_loss.item(),
                    'mean_per_pixel_chi_squared': mean_per_pixel_chi_squared,
                    'masked_mse': masked_mse_loss.item() if masked_pixels_total > 0 else 0.0,
                    'masked_pixels': masked_pixels_total,
                    'clamped_pixels': clamped_pixels_total,
                    'clamp_fraction': clamp_fraction,
                }

                # Compute variance component statistics
                if i_model_values_list:
                    i_model_all = torch.cat(i_model_values_list)
                    v_denom_all = torch.cat(v_denom_values_list)
                    weighted_residuals_all = torch.cat(weighted_residuals_list)

                    telemetry_variance = {
                        'i_model_min': i_model_min_global,
                        'i_model_median': torch.median(i_model_all).item(),
                        'i_model_max': i_model_max_global,
                        'i_model_mean': torch.mean(i_model_all).item(),
                        'i_model_std': torch.std(i_model_all).item() if i_model_all.numel() > 1 else 0.0,
                        'v_denom_min': torch.min(v_denom_all).item(),
                        'v_denom_median': torch.median(v_denom_all).item(),
                        'v_denom_max': torch.max(v_denom_all).item(),
                        'weighted_residuals_min': torch.min(weighted_residuals_all).item(),
                        'weighted_residuals_median': torch.median(weighted_residuals_all).item(),
                        'weighted_residuals_max': torch.max(weighted_residuals_all).item(),
                        'weighted_residuals_mean': torch.mean(weighted_residuals_all).item(),
                    }
                else:
                    telemetry_variance = {
                        'i_model_min': None,
                        'i_model_median': None,
                        'i_model_max': None,
                        'i_model_mean': None,
                        'i_model_std': None,
                        'v_denom_min': None,
                        'v_denom_median': None,
                        'v_denom_max': None,
                        'weighted_residuals_min': None,
                        'weighted_residuals_median': None,
                        'weighted_residuals_max': None,
                        'weighted_residuals_mean': None,
                    }

            variance_floor_clamped_pixels[0] += clamped_pixels_total
            variance_floor_masked_pixels[0] += masked_pixels_total
        else:
            panel_ids = work_item_ids if work_item_ids else list(range(n_panels))
            bragg_panels = []
            for pid in panel_ids:
                if stage_a_ctx is not None:
                    simulator = stage_a_ctx.simulators[pid]
                else:
                    detector_config = create_detector_config(
                        panel=detector[pid],
                        beam=beam,
                        trusted_mask=inputs.trusted_mask[pid]
                    )
                    if detector_config.mask_array is not None and not isinstance(detector_config.mask_array, torch.Tensor):
                        detector_config.mask_array = torch.tensor(
                            detector_config.mask_array, dtype=torch.float32, device=device
                        )
                    from nanobrag_torch.models.detector import Detector
                    detector_model = Detector(detector_config, device=device, dtype=dtype)

                    crystal_config, _ = create_crystal_config(
                        crystal,
                        None,
                        crystal_overrides=crystal_overrides,
                        misset_deg_override=misset_deg_for_crystal
                    )
                    from nanobrag_torch.models.crystal import Crystal
                    crystal_model = Crystal(
                        crystal_config,
                        beam_config=beam_config_for_run,
                        device=device,
                        dtype=dtype
                    )
                    crystal_model.interpolate = config.enable_hkl_interpolation
                    crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
                    crystal_model.hkl_metadata = hkl_metadata

                    from nanobrag_torch.simulator import Simulator
                    simulator = Simulator(
                        detector=detector_model,
                        crystal=crystal_model,
                        beam_config=beam_config_for_run,
                        device=device,
                        dtype=dtype
                    )
                bragg_panels.append(simulator.run())

            bragg_stacked = torch.stack(bragg_panels, dim=0)
            bragg_scaled = bragg_stacked * torch.exp(log_scale_clamped)

            target_subset = target_t[panel_ids]
            mask_subset = loss_mask_t[panel_ids]
            if stage_a_ctx is not None and stage_a_ctx.trusted_masks_t is not None:
                trusted_subset = stage_a_ctx.trusted_masks_t[panel_ids]
                mask_subset = torch.logical_and(mask_subset, trusted_subset)
            sigma_subset = sigma_readout_t[panel_ids]

            (
                chi_squared_loss,
                masked_mse_loss,
                masked_pixels,
                clamped_pixels,
            ) = _compute_variance_weighted_loss(
                bragg_scaled,
                target_subset,
                mask_subset,
                sigma_subset,
                sigma_floor_sq_tensor,
            )
            variance_floor_clamped_pixels[0] += clamped_pixels
            variance_floor_masked_pixels[0] += masked_pixels

        if not is_full:  # Only track closure forward times, not validation
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            perf_forward_times_ms.append(elapsed_ms)

        return chi_squared_loss, masked_mse_loss

    def closure():
        """LBFGS closure: recompute loss and gradients."""
        optimizer = param_values.get('optimizer')
        optimizer.zero_grad()

        # Increment closure evaluation counter (PERF-WARM-SIM-001)
        perf_closure_evals[0] += 1

        # Compute loss on sampled ROIs or panels depending on mode
        chi_squared_loss, masked_mse_loss = compute_loss(sampled_stage_a_indices, is_full=False)

        # Backward pass (optimize chi_squared, not MSE)
        chi_squared_loss.backward()

        # Check for NaN/Inf gradients
        for p in params:
            if p.grad is not None and (torch.isnan(p.grad).any() or torch.isinf(p.grad).any()):
                raise RuntimeError(f"NaN/Inf gradient detected in {p}")

        # Telemetry: Capture gradients and emit JSON (TORCH-GEOMETRY-CONVERGENCE-001 Phase B2)
        if config.telemetry_output_dir and config.use_u_matrix_parameterization:
            # Capture detailed gradient statistics
            if q_params.grad is not None:
                q_grad_has_nan = bool(torch.isnan(q_params.grad).any().item())
                q_grad_has_inf = bool(torch.isinf(q_params.grad).any().item())
                q_grad_norm = torch.norm(q_params.grad).item()
                q_grad_min = torch.min(q_params.grad).item()
                q_grad_max = torch.max(q_params.grad).item()
                q_grad_mean = torch.mean(q_params.grad).item()
                q_grad_std = torch.std(q_params.grad).item() if q_params.grad.numel() > 1 else 0.0
                # Sign consistency: count positive vs negative elements
                q_grad_positive_count = int((q_params.grad > 0).sum().item())
                q_grad_negative_count = int((q_params.grad < 0).sum().item())
            else:
                q_grad_has_nan = None
                q_grad_has_inf = None
                q_grad_norm = None
                q_grad_min = None
                q_grad_max = None
                q_grad_mean = None
                q_grad_std = None
                q_grad_positive_count = None
                q_grad_negative_count = None

            if log_scale.grad is not None:
                log_scale_grad_has_nan = bool(torch.isnan(log_scale.grad).any().item())
                log_scale_grad_has_inf = bool(torch.isinf(log_scale.grad).any().item())
                log_scale_grad_norm = torch.norm(log_scale.grad).item()
                log_scale_grad_value = log_scale.grad.item()
            else:
                log_scale_grad_has_nan = None
                log_scale_grad_has_inf = None
                log_scale_grad_norm = None
                log_scale_grad_value = None

            telemetry_gradients = {
                'log_scale': {
                    'norm': log_scale_grad_norm,
                    'value': log_scale_grad_value,
                    'has_nan': log_scale_grad_has_nan,
                    'has_inf': log_scale_grad_has_inf,
                },
                'q_params': {
                    'norm': q_grad_norm,
                    'min': q_grad_min,
                    'max': q_grad_max,
                    'mean': q_grad_mean,
                    'std': q_grad_std,
                    'positive_count': q_grad_positive_count,
                    'negative_count': q_grad_negative_count,
                    'has_nan': q_grad_has_nan,
                    'has_inf': q_grad_has_inf,
                },
            }

            # Combine all telemetry with structured format per input.md Phase B2
            # Note: telemetry_params, telemetry_loss, telemetry_variance are nonlocal from compute_loss
            telemetry_step = {
                'step': telemetry_params['step_index'],
                'parameters': {
                    'log_scale': telemetry_params['log_scale'],
                    'q_params': telemetry_params['q_params'],
                    'q_norm': telemetry_params['q_norm_value'],
                    'u_matrix_checksum': telemetry_params['u_matrix_checksum'],
                },
                'gradients': telemetry_gradients,
                'variance': telemetry_variance,
                'loss': telemetry_loss,
            }

            # Emit telemetry JSON
            import json
            from pathlib import Path
            try:
                telemetry_path = Path(config.telemetry_output_dir) / f"telemetry_step_{telemetry_step_counter[0]:03d}.json"
                telemetry_path.parent.mkdir(parents=True, exist_ok=True)
                with open(telemetry_path, 'w') as f:
                    json.dump(telemetry_step, f, indent=2)
            except Exception as e:
                import sys
                print(f"Warning: Failed to write telemetry JSON: {e}", file=sys.stderr)

            # Increment step counter
            telemetry_step_counter[0] += 1

        # Record loss (use chi_squared for optimizer feedback)
        loss_trace_sample.append(float(chi_squared_loss.item()))  # Deprecated legacy field
        # PHYSICS-LOSS-001: Record both metrics
        chi_squared_trace_sample.append(float(chi_squared_loss.item()))
        masked_mse_trace_sample.append(float(masked_mse_loss.item()))

        # Periodic full validation
        if iteration_count[0] % config.full_validation_interval == 0:
            perf_validation_runs[0] += 1  # PERF-WARM-SIM-001
            with torch.no_grad():
                full_chi_squared, full_mse = compute_loss(full_stage_a_indices, is_full=True)
                loss_trace_full.append((iteration_count[0], float(full_chi_squared.item())))  # Deprecated legacy field
                # PHYSICS-LOSS-001: Record both metrics
                chi_squared_trace_full.append((iteration_count[0], float(full_chi_squared.item())))
                masked_mse_trace_full.append((iteration_count[0], float(full_mse.item())))

                # Update best snapshot
                nonlocal best_loss_full, best_params_snapshot, chi_squared_best, masked_mse_best
                # PHYSICS-LOSS-001: Track best for both metrics
                if full_chi_squared.item() < chi_squared_best[0]:
                    chi_squared_best = (float(full_chi_squared.item()), iteration_count[0])
                    best_loss_full = (float(full_chi_squared.item()), iteration_count[0])  # Deprecated legacy field
                    # Compute misset XYZ for snapshot (TORCH-REFINE-002)
                    max_orientation_deg = 3.0
                    bounded_orientation_vec_snap = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
                    quat_snap = vec_to_unit_quaternion(bounded_orientation_vec_snap)
                    misset_xyz_deg_snap = quaternion_to_xyz_euler(quat_snap)

                    best_params_snapshot = {
                        'log_scale': float(log_scale.item()),
                        'log_cell_a_delta': float(log_cell_a_delta.item()),
                        'log_cell_b_delta': float(log_cell_b_delta.item()),
                        'log_cell_c_delta': float(log_cell_c_delta.item()),
                        'angle_alpha_raw': float(angle_alpha_raw.item()),
                        'angle_beta_raw': float(angle_beta_raw.item()),
                        'angle_gamma_raw': float(angle_gamma_raw.item()),
                        'orientation_vec': orientation_vec.detach().cpu().tolist(),
                        'misset_xyz_deg': misset_xyz_deg_snap.detach().cpu().tolist()
                    }
                # PHYSICS-LOSS-001: Track masked_mse best separately (informational only, not for rollback)
                if full_mse.item() < masked_mse_best[0]:
                    masked_mse_best = (float(full_mse.item()), iteration_count[0])

        iteration_count[0] += 1

        # Emit lifecycle JSON (TORCH-GEOMETRY-CONVERGENCE-001 Phase B4)
        if config.telemetry_output_dir and config.use_u_matrix_parameterization:
            import json
            from pathlib import Path
            try:
                lifecycle_path = Path(config.telemetry_output_dir) / f"u_matrix_lifecycle_step_{telemetry_step_counter[0]-1:03d}.json"
                lifecycle_path.parent.mkdir(parents=True, exist_ok=True)
                with open(lifecycle_path, 'w') as f:
                    json.dump({
                        "u_matrix_lifecycle": u_matrix_lifecycle_log,
                        "a_star_lifecycle": a_star_lifecycle_log
                    }, f, indent=2)
            except Exception as e:
                import sys
                print(f"Warning: Failed to write lifecycle JSON: {e}", file=sys.stderr)

        return chi_squared_loss

    return compute_loss, closure


def _run_stage_a_lbfgs(
    compute_loss,  # Callable from helper 2
    closure,  # Callable from helper 2
    optimizer,  # torch.optim.LBFGS from helper 1
    params,  # List[Parameter] from helper 1
    telemetry_state: Dict[str, Any],  # From helper 1
    config: RefinementConfig,
    canonical_baseline: Dict[str, Any],  # From run_nanobrag_refinement
    full_stage_a_indices: List[int],  # From run_nanobrag_refinement
    log_scale,  # Parameter from helper 1
    log_cell_a_delta, log_cell_b_delta, log_cell_c_delta,  # Parameters from helper 1
    angle_alpha_raw, angle_beta_raw, angle_gamma_raw,  # Parameters from helper 1
    orientation_vec,  # Parameter from helper 1
    device,
    dtype,
) -> Tuple[str, str, Optional[float], Optional[float], Optional[Dict[str, Any]]]:
    """
    Execute Stage A LBFGS optimization and final validation.

    Returns:
        Tuple of (status, message, final_chi_squared_value, final_masked_mse_value, best_params_snapshot)
    """
    # Unpack telemetry_state variables
    iteration_count = telemetry_state['iteration_count']
    loss_trace_full = telemetry_state['loss_trace_full']
    chi_squared_trace_full = telemetry_state['chi_squared_trace_full']
    chi_squared_best = telemetry_state['chi_squared_best']
    masked_mse_trace_full = telemetry_state['masked_mse_trace_full']
    masked_mse_best = telemetry_state['masked_mse_best']
    best_loss_full = telemetry_state['best_loss_full']
    perf_validation_runs = telemetry_state['perf_validation_runs']
    best_params_snapshot = telemetry_state.get('best_params_snapshot')

    # Run LBFGS optimization
    status = "ok"
    message = ""

    final_chi_squared_value: Optional[float] = None
    final_masked_mse_value: Optional[float] = None

    try:
        optimizer.step(closure)

        # Final full validation
        perf_validation_runs[0] += 1  # PERF-WARM-SIM-001
        with torch.no_grad():
            final_chi_squared, final_mse = compute_loss(full_stage_a_indices, is_full=True)
            final_chi_squared_value = float(final_chi_squared.item())
            final_masked_mse_value = float(final_mse.item())
            loss_trace_full.append((iteration_count[0], final_chi_squared_value))  # Deprecated legacy field
            # PHYSICS-LOSS-001: Record both metrics
            chi_squared_trace_full.append((iteration_count[0], final_chi_squared_value))
            masked_mse_trace_full.append((iteration_count[0], final_masked_mse_value))

            if final_chi_squared_value < best_loss_full[0]:
                best_loss_full = (final_chi_squared_value, iteration_count[0])  # Deprecated legacy field
            # PHYSICS-LOSS-001: Track best for both metrics
            if final_chi_squared_value < chi_squared_best[0]:
                chi_squared_best = (final_chi_squared_value, iteration_count[0])
            if final_masked_mse_value < masked_mse_best[0]:
                masked_mse_best = (final_masked_mse_value, iteration_count[0])

            if final_chi_squared_value < best_loss_full[0]:
                # Compute misset XYZ for final snapshot (TORCH-REFINE-002)
                max_orientation_deg = 3.0
                bounded_orientation_vec_final = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
                quat_final = vec_to_unit_quaternion(bounded_orientation_vec_final)
                misset_xyz_deg_final = quaternion_to_xyz_euler(quat_final)

                best_params_snapshot = {
                    'log_scale': float(log_scale.item()),
                    'log_cell_a_delta': float(log_cell_a_delta.item()),
                    'log_cell_b_delta': float(log_cell_b_delta.item()),
                    'log_cell_c_delta': float(log_cell_c_delta.item()),
                    'angle_alpha_raw': float(angle_alpha_raw.item()),
                    'angle_beta_raw': float(angle_beta_raw.item()),
                    'angle_gamma_raw': float(angle_gamma_raw.item()),
                    'orientation_vec': orientation_vec.detach().cpu().tolist(),
                    'misset_xyz_deg': misset_xyz_deg_final.detach().cpu().tolist()
                }
            if final_chi_squared_value is not None:
                canonical_baseline["chi_squared"] = final_chi_squared_value
                canonical_baseline["iteration"] = iteration_count[0]

        # Check convergence: did we achieve ≥0.2% improvement?
        if len(loss_trace_full) > 0:
            initial_loss = loss_trace_full[0][1]
            final_loss_val = loss_trace_full[-1][1]
            improvement = (initial_loss - final_loss_val) / initial_loss

            if improvement < config.min_loss_improvement:
                status = "early_stop"
                message = f"Improvement {improvement:.2%} < {config.min_loss_improvement:.2%} (Stage A gate calibrated per TORCH-REFINE-002D)"

    except Exception as e:
        status = "error"
        message = str(e)
        # Use best snapshot if available
        if best_params_snapshot is not None:
            log_scale.data = torch.tensor(best_params_snapshot['log_scale'], device=device, dtype=dtype)
            log_cell_a_delta.data = torch.tensor(best_params_snapshot['log_cell_a_delta'], device=device, dtype=dtype)
            log_cell_b_delta.data = torch.tensor(best_params_snapshot['log_cell_b_delta'], device=device, dtype=dtype)
            log_cell_c_delta.data = torch.tensor(best_params_snapshot['log_cell_c_delta'], device=device, dtype=dtype)
            angle_alpha_raw.data = torch.tensor(best_params_snapshot['angle_alpha_raw'], device=device, dtype=dtype)
            angle_beta_raw.data = torch.tensor(best_params_snapshot['angle_beta_raw'], device=device, dtype=dtype)
            angle_gamma_raw.data = torch.tensor(best_params_snapshot['angle_gamma_raw'], device=device, dtype=dtype)
            orientation_vec.data = torch.tensor(best_params_snapshot['orientation_vec'], device=device, dtype=dtype)

    if not chi_squared_trace_full:
        fallback_chi2 = final_chi_squared_value
        fallback_iter = iteration_count[0]
        if fallback_chi2 is None and chi_squared_best[0] < float('inf'):
            fallback_chi2 = chi_squared_best[0]
            fallback_iter = chi_squared_best[1]
        if fallback_chi2 is None and best_loss_full[0] < float('inf'):
            fallback_chi2 = best_loss_full[0]
            fallback_iter = best_loss_full[1]
        if fallback_chi2 is not None:
            chi_squared_trace_full.append((fallback_iter, fallback_chi2))
            if not loss_trace_full:
                loss_trace_full.append((fallback_iter, fallback_chi2))
            if fallback_chi2 < chi_squared_best[0]:
                chi_squared_best = (fallback_chi2, fallback_iter)

    if not masked_mse_trace_full:
        fallback_mse = final_masked_mse_value
        fallback_iter = iteration_count[0]
        if fallback_mse is None and masked_mse_best[0] < float('inf'):
            fallback_mse = masked_mse_best[0]
            fallback_iter = masked_mse_best[1]
        if fallback_mse is not None:
            masked_mse_trace_full.append((fallback_iter, fallback_mse))
            if fallback_mse < masked_mse_best[0]:
                masked_mse_best = (fallback_mse, fallback_iter)

    if canonical_baseline["chi_squared"] is None:
        if chi_squared_trace_full:
            last_iter, last_val = chi_squared_trace_full[-1]
            canonical_baseline["chi_squared"] = last_val
            canonical_baseline["iteration"] = last_iter
        elif chi_squared_best[0] < float('inf'):
            canonical_baseline["chi_squared"] = chi_squared_best[0]
            canonical_baseline["iteration"] = chi_squared_best[1]

    # Update telemetry_state (mutations visible to caller via dict reference)
    telemetry_state['loss_trace_full'] = loss_trace_full
    telemetry_state['chi_squared_trace_full'] = chi_squared_trace_full
    telemetry_state['chi_squared_best'] = chi_squared_best
    telemetry_state['masked_mse_trace_full'] = masked_mse_trace_full
    telemetry_state['masked_mse_best'] = masked_mse_best
    telemetry_state['best_loss_full'] = best_loss_full
    telemetry_state['best_params_snapshot'] = best_params_snapshot

    # Canonical_baseline mutations are visible via dict reference (no need to return)

    return (status, message, final_chi_squared_value, final_masked_mse_value, best_params_snapshot)


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
):
    """
    Build final Bragg array from Stage A telemetry (optimized parameters).

    Extracts optimized parameters from telemetry.param_deltas and regenerates
    full Bragg image by looping over panels with final crystal geometry.

    Args:
        telemetry_a: RefinementTelemetry instance or dict with optimized param_deltas
        detector: dxtbx Detector object
        beam: dxtbx Beam object
        crystal: dxtbx Crystal object
        inputs: RefinementInputs with panel_slices, trusted_mask
        hkl_grid: torch.Tensor structure factor grid
        hkl_metadata: dict with grid dimensions
        config: RefinementConfig with device, dtype, parameterization mode
        device: torch.device for tensor operations
        dtype: torch.dtype for tensor operations

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
    if hasattr(telemetry_a, 'param_deltas'):
        param_deltas = telemetry_a.param_deltas
    else:
        param_deltas = telemetry_a['param_deltas']

    # Convert param deltas to torch tensors (no requires_grad, final forward pass)
    log_scale = torch.tensor(param_deltas['log_scale']['final'], device=device, dtype=dtype, requires_grad=False)
    log_cell_a_delta = torch.tensor(param_deltas['log_cell_a_delta']['final'], device=device, dtype=dtype, requires_grad=False)
    log_cell_b_delta = torch.tensor(param_deltas['log_cell_b_delta']['final'], device=device, dtype=dtype, requires_grad=False)
    log_cell_c_delta = torch.tensor(param_deltas['log_cell_c_delta']['final'], device=device, dtype=dtype, requires_grad=False)
    angle_alpha_raw = torch.tensor(param_deltas['angle_alpha_raw']['final'], device=device, dtype=dtype, requires_grad=False)
    angle_beta_raw = torch.tensor(param_deltas['angle_beta_raw']['final'], device=device, dtype=dtype, requires_grad=False)
    angle_gamma_raw = torch.tensor(param_deltas['angle_gamma_raw']['final'], device=device, dtype=dtype, requires_grad=False)
    orientation_vec = torch.tensor(param_deltas['orientation_vec']['final'], device=device, dtype=dtype, requires_grad=False)

    # Extract optional params for U-matrix/incremental UB modes
    # (Not currently populated by StageA, but handle gracefully for future support)
    q_params = param_deltas.get('q_params')
    if q_params is not None:
        q_params = torch.tensor(q_params, device=device, dtype=dtype, requires_grad=False)

    q_delta = param_deltas.get('q_delta')
    if q_delta is not None:
        q_delta = torch.tensor(q_delta, device=device, dtype=dtype, requires_grad=False)

    B_ideal_reciprocal_torch = param_deltas.get('B_ideal_reciprocal_torch')
    if B_ideal_reciprocal_torch is not None:
        B_ideal_reciprocal_torch = torch.tensor(B_ideal_reciprocal_torch, device=device, dtype=dtype, requires_grad=False)

    # Get n_panels and panel_shape
    n_panels = len(detector)
    panel_shape = inputs.target.shape[1:]  # (slow, fast)

    # Compute baseline misset if needed (required for TORCH-REFINE-002D compatibility)
    # This is None when no baseline_crystal provided
    baseline_misset_deg_tensor = None
    # Note: baseline_crystal is not passed to this helper, so baseline misset is not supported
    # in engine delegation path yet. This is OK for Phase B2 (Stage-A-only validation).

    # Generate final Bragg array with optimized parameters (lines 2046-2153 from inline code)
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

            beam_config = create_beam_config(beam)

            # Apply final full crystal perturbations via tensor overrides (GRADIENT-001, TORCH-REFINE-002)
            cell_params = crystal.get_unit_cell().parameters()

            # 1. Unit cell lengths (log-parameterized)
            perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
            perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
            perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)

            # 2. Unit cell angles (bounded via tanh)
            max_angle_delta = 10.0  # degrees
            perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
            perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
            perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

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

            crystal_config, _ = create_crystal_config(
                crystal, None,
                crystal_overrides=crystal_overrides,
                misset_deg_override=misset_deg_for_crystal
            )

            detector_model = Detector(detector_config, device=device, dtype=dtype)
            crystal_model = Crystal(crystal_config, device=device, dtype=dtype)

            # HKL interpolation control (TORCH-REFINE-002D, REFINE-005)
            # Defaults to nearest-neighbor (False) unless explicitly enabled via config
            # Tricubic interpolation requires halo-padded grid to avoid default_F fallback
            crystal_model.interpolate = config.enable_hkl_interpolation

            crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
            crystal_model.hkl_metadata = hkl_metadata

            simulator = Simulator(detector=detector_model, crystal=crystal_model, device=device, dtype=dtype)
            panel_bragg = simulator.run()

            # Apply optimized scale (with same clamping as in compute_loss)
            log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
            panel_bragg_scaled = panel_bragg * torch.exp(log_scale_clamped)
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

    # Compute shell lookup for per-shell modifiers
    shell_indices, shell_edges = compute_hkl_shell_lookup(
        crystal, hkl_metadata, n_shells=config.stage_b_n_shells, device=device, dtype=dtype
    )

    # Initialize shell modifiers (softplus parameterization to keep multipliers positive)
    # Start near identity: softplus(0) ≈ 0.69, so initialize slightly negative to get ~1.0
    # GRADIENT-001: Create parameters on CPU when CPU fallback active to prevent gradient chain break
    stage_b_param_device = torch.device("cpu") if use_stage_b_cpu_fallback else torch.device(config.device)
    shell_modifier_raw = torch.zeros(config.stage_b_n_shells, device=stage_b_param_device, dtype=dtype, requires_grad=True)
    identity_raw = math.log(math.expm1(0.5))  # softplus(identity_raw)*2 == 1.0
    shell_modifier_raw.data.fill_(identity_raw)

    stage_b_params = [shell_modifier_raw]

    # Setup LBFGS optimizer for Stage B
    stage_b_optimizer = torch.optim.LBFGS(
        stage_b_params,
        history_size=config.history_size,
        max_iter=config.max_iter,
        tolerance_grad=config.tolerance_grad,
        tolerance_change=config.tolerance_change,
        line_search_fn='strong_wolfe'
    )

    # Telemetry accumulators for Stage B
    loss_trace_sample_b = []
    loss_trace_full_b = []
    best_loss_full_b = (float('inf'), 0)
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

    # PERF-WARM-012: CPU fallback already computed above for device-aware parameter init
    # DIAGNOSTIC INSTRUMENTATION (TEMPORARY — remove after CPU fallback bug fixed)
    import json
    fallback_diagnostics = {
        "location": "_build_stage_b_params",
        "config_stage_b_full_eval_on_cpu": config.stage_b_full_eval_on_cpu,
        "device_global": str(device),
        "device_type": type(device).__name__,
        "device_is_cuda": str(device).startswith("cuda"),
        "use_stage_a_roi_mode": use_stage_a_roi_mode,
        "use_stage_a_roi_mode_type": type(use_stage_a_roi_mode).__name__,
        "stage_a_ctx_is_not_none": stage_a_ctx is not None,
        "use_stage_b_cpu_fallback": use_stage_b_cpu_fallback,
        "stage_b_param_device": str(stage_b_param_device),
        "shell_modifier_raw_device": str(shell_modifier_raw.device),
        "shell_modifier_raw_requires_grad": shell_modifier_raw.requires_grad,
    }
    print(f"CPU_FALLBACK_DIAGNOSTICS_PARAMS: {json.dumps(fallback_diagnostics)}", flush=True)

    # PERF-WARM-012: Clone StageAContext to CPU when fallback is active so Stage B can reuse
    # cached detectors/HKL/masks even on CPU, maintaining cache_mode="warm"
    stage_b_eval_stage_a_ctx = None
    if use_stage_b_cpu_fallback and stage_a_ctx is not None and config.enable_stage_a_warm_cache:
        # Build a fresh Stage A context on CPU device
        cpu_device = torch.device("cpu")

        # DIAGNOSTIC: CPU crystal config comparison (temp)
        print(f"[CRYSTAL_CPU_PRE] cell={crystal.get_unit_cell().parameters()}")
        print(f"[CRYSTAL_CPU_PRE] A_matrix={np.array(crystal.get_A()).reshape(3,3).tolist()}")
        print(f"[CRYSTAL_CPU_PRE] U_matrix={np.array(crystal.get_U()).reshape(3,3).tolist()}")
        print(f"[CRYSTAL_CPU_PRE] B_matrix={np.array(crystal.get_B()).reshape(3,3).tolist()}")

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

    return {
        'shell_indices': shell_indices,
        'shell_edges': shell_edges,
        'shell_modifier_raw': shell_modifier_raw,
        'params': stage_b_params,
        'optimizer': stage_b_optimizer,
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
    shell_modifier_raw = param_values['shell_modifier_raw']
    stage_b_optimizer = param_values['optimizer']
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

        shell_modifiers = torch.nn.functional.softplus(shell_modifier_raw) * 2.0
        shell_modifiers = torch.clamp(shell_modifiers, max=config.stage_b_max_modifier)

        # PERF-WARM-011: Route to CPU when fallback is active (panel mode + CUDA + config flag)
        eval_device = torch.device("cpu") if use_stage_b_cpu_fallback else device

        # DIAGNOSTIC INSTRUMENTATION (TEMPORARY — remove after CPU fallback bug fixed)
        import json
        eval_device_diagnostics = {
            "location": "_build_stage_b_lbfgs_closure",
            "use_stage_b_cpu_fallback": use_stage_b_cpu_fallback,
            "is_full": is_full,
            "grad_enabled": torch.is_grad_enabled(),
            "device_global": str(device),
            "shell_modifier_raw_device": str(shell_modifier_raw.device),
            "shell_modifiers_device": str(shell_modifiers.device),
            "eval_device": str(eval_device),
            "eval_device_type": eval_device.type,
            "shell_modifier_raw_requires_grad": shell_modifier_raw.requires_grad,
            "shell_modifiers_requires_grad": shell_modifiers.requires_grad,
            "shell_modifiers_grad_fn": str(shell_modifiers.grad_fn) if shell_modifiers.grad_fn else "None",
        }
        print(f"CPU_FALLBACK_DIAGNOSTICS_CLOSURE: {json.dumps(eval_device_diagnostics)}", flush=True)

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

        hkl_grid_local = hkl_grid if eval_device == device else hkl_grid.to(device=eval_device, dtype=dtype)
        shell_indices_local = shell_indices if eval_device == device else shell_indices.to(device=eval_device)
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

        # DIAGNOSTIC: Verify HKL grid has gradients after out-of-place construction
        print(f"[HKL_GRAD_CHECK] hkl_grid_modified.requires_grad={hkl_grid_modified.requires_grad}, "
              f"grad_fn={hkl_grid_modified.grad_fn}, device={hkl_grid_modified.device}")

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

                    # DIAGNOSTIC: Extract Bragg tensor stats after run (temp)
                    if eval_device.type == "cpu":
                        print(f"[BRAGG_CPU_WARM] bragg_panel.shape={bragg_panel.shape}, bragg_panel.min={bragg_panel.min().item()}, bragg_panel.max={bragg_panel.max().item()}, bragg_panel.mean={bragg_panel.mean().item()}")
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

                    # DIAGNOSTIC: Extract Bragg tensor stats after run (temp)
                    if eval_device.type == "cpu":
                        print(f"[BRAGG_CPU_COLD] bragg_panel.shape={bragg_panel.shape}, bragg_panel.min={bragg_panel.min().item()}, bragg_panel.max={bragg_panel.max().item()}, bragg_panel.mean={bragg_panel.mean().item()}")

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
    # Extract param_values dict entries
    stage_b_optimizer = param_values['optimizer']
    shell_modifier_raw = param_values['shell_modifier_raw']
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
            best_params_snapshot_b['shell_modifier_raw'] = shell_modifier_raw.data.clone()

        # Run LBFGS optimization
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
        best_params_snapshot_b['shell_modifier_raw'] = shell_modifier_raw.data.clone()
    if candidate_mse_value < masked_mse_best_b[0]:
        masked_mse_best_b[0] = candidate_mse_value
        masked_mse_best_b[1] = final_step

    if best_loss_full_b[0] < float('inf'):
        shell_modifier_raw.data = best_params_snapshot_b['shell_modifier_raw'].to(
            device=stage_b_param_device,
            dtype=dtype
        )

    final_loss_value = chi_squared_best_b[0] if chi_squared_best_b[0] < float('inf') else candidate_loss_value
    final_mse_value = masked_mse_best_b[0] if masked_mse_best_b[0] < float('inf') else candidate_mse_value
    loss_trace_full_b.append((final_step, final_loss_value))
    chi_squared_trace_full_b.append((final_step, final_loss_value))
    masked_mse_trace_full_b.append((final_step, final_mse_value))

    # Improvement gate check (REFINE-008)
    if status_b != "error" and best_loss_full[0] > 0:
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

    # Extract shell metadata from Stage B telemetry
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
    cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta)
    cell_b_tensor = cell_params[1] * torch.exp(log_cell_b_delta)
    cell_c_tensor = cell_params[2] * torch.exp(log_cell_c_delta)

    max_angle_delta = 10.0  # degrees
    cell_alpha_tensor = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
    cell_beta_tensor = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
    cell_gamma_tensor = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

    # Apply shell modifiers to HKL grid (mirroring inline code lines 3314-3317)
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
    baseline_detector=None
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

        # Extract StageA telemetry (keyed by "stage_a" per StageA.name property)
        telemetry_a = telemetry_dict["stage_a"]

        # Build final Bragg array using optimized parameters from telemetry
        device = torch.device(config.device)
        dtype = config.dtype
        bragg_full = _build_final_bragg_from_stage_a_telemetry(
            telemetry_a, detector, beam, crystal, inputs, hkl_grid,
            hkl_metadata, config, device, dtype
        )

        # Return with telemetry dict using "A" key for backward compatibility
        # (Legacy code expects {"A": RefinementTelemetry, ...})
        return bragg_full, {"A": telemetry_a}

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
            )
        elif not use_stage_b_cpu_fallback:
            # No CPU fallback: reuse the original CUDA Stage A context
            stage_b_eval_stage_a_ctx = stage_a_ctx

        # Extract shell metadata from engine cache (cached separately from telemetry)
        shell_edges = getattr(engine, '_stage_b_shell_edges', None)
        shell_indices = getattr(engine, '_stage_b_shell_indices', None)
        n_shells = getattr(engine, '_stage_b_n_shells', None)

        # Create a dict version of telemetry_b with shell metadata for the helper
        from dataclasses import asdict
        telemetry_b_dict = asdict(telemetry_b_raw)
        if shell_edges is not None:
            telemetry_b_dict['shell_edges'] = shell_edges
        if shell_indices is not None:
            telemetry_b_dict['shell_indices'] = shell_indices
        if n_shells is not None:
            telemetry_b_dict['n_shells'] = n_shells

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
        # Filter out stage_type/mode fields to maintain RefinementTelemetry structure
        from dataclasses import asdict
        from dbex.nanobrag_refinement import RefinementTelemetry

        # Convert RefinementTelemetry dataclass instances to dicts before filtering
        telemetry_a_dict = asdict(telemetry_a_raw)
        telemetry_b_dict = asdict(telemetry_b_raw)

        # Filter out extra fields not in RefinementTelemetry schema
        telemetry_b = RefinementTelemetry(**{k: v for k, v in telemetry_b_dict.items() if k not in ['stage_type', 'mode', 'shell_edges', 'shell_indices', 'n_shells']})
        telemetry_a = RefinementTelemetry(**{k: v for k, v in telemetry_a_dict.items() if k not in ['stage_type', 'mode', 'stage_a_ctx']})

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
            device, dtype
        )
    
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
    
                beam_config = create_beam_config(beam)
    
                # Apply final full crystal perturbations via tensor overrides (GRADIENT-001, TORCH-REFINE-002)
                cell_params = crystal.get_unit_cell().parameters()
    
                # 1. Unit cell lengths (log-parameterized)
                perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
                perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
                perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)
    
                # 2. Unit cell angles (bounded via tanh)
                max_angle_delta = 10.0  # degrees
                perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
                perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
                perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta
    
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
    
                crystal_config, _ = create_crystal_config(
                    crystal, None,
                    crystal_overrides=crystal_overrides,
                    misset_deg_override=misset_deg_for_crystal
                )
    
                detector_model = Detector(detector_config, device=device, dtype=dtype)
                crystal_model = Crystal(crystal_config, device=device, dtype=dtype)
    
                # HKL interpolation control (TORCH-REFINE-002D, REFINE-005)
                # Defaults to nearest-neighbor (False) unless explicitly enabled via config
                # Tricubic interpolation requires halo-padded grid to avoid default_F fallback
                crystal_model.interpolate = config.enable_hkl_interpolation
    
                crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
                crystal_model.hkl_metadata = hkl_metadata
    
                simulator = Simulator(detector=detector_model, crystal=crystal_model, device=device, dtype=dtype)
                panel_bragg = simulator.run()
    
                # Apply optimized scale (with same clamping as in compute_loss)
                log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
                panel_bragg_scaled = panel_bragg * torch.exp(log_scale_clamped)
                bragg_full[pid] = panel_bragg_scaled.cpu().numpy().astype(np.float32)
    
        # Assemble telemetry
        param_deltas = {
            'log_scale': {
                'initial': initial_log_scale,
                'final': float(log_scale.item()),
                'delta': float(log_scale.item()) - initial_log_scale
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
                float(variance_floor_clamped_pixels[0]) / float(variance_floor_masked_pixels[0])
                if variance_floor_masked_pixels[0] > 0 else 0.0
            ),
            # Canonical Stage A metadata propagated to downstream stages
            canonical_stage_label=canonical_baseline["stage_label"],
            canonical_chi_squared=canonical_baseline["chi_squared"],
            canonical_chi_squared_iteration=canonical_baseline["iteration"],
            canonical_roi_count=canonical_baseline["roi_count"],
            canonical_detector_distances_mm=canonical_baseline["detector_distances_mm"],
            roi_mode=stage_a_roi_label,
        )
    
        telemetry_dict = {"A": telemetry_a}
    
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
            cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta)
            cell_b_tensor = cell_params[1] * torch.exp(log_cell_b_delta)
            cell_c_tensor = cell_params[2] * torch.exp(log_cell_c_delta)

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
    
            # Assemble Stage B telemetry
            param_deltas_b = {}
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
    
            telemetry_b = RefinementTelemetry(
                optimizer="LBFGS",
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
    
            telemetry_dict["B"] = telemetry_b
    
        # ============================================================================
        # Stage C: Detector microslip (per-panel distance refinement)
        # ============================================================================
        if config.enable_stage_c:
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
    
            def compute_loss_stage_c(panel_ids: List[int], is_full: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
                """
                Compute variance-weighted chi-squared loss with Stage C detector distance adjustments.
    
                Uses Stage A's final crystal parameters (frozen) and varies per-panel distances.
    
                Returns:
                    Tuple of (chi_squared_loss, masked_mse_loss): Both scalar tensors for telemetry
                """
                t0 = time.perf_counter()
                if is_full:
                    perf_validation_runs_c[0] += 1
                bragg_panels = []
                target_panels = []
                mask_panels = []
                sigma_panels = []
    
                cell_params = crystal.get_unit_cell().parameters()
                perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
                perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
                perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)
    
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
    
                for pid in panel_ids:
                    panel = detector[pid]
    
                    bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
                    baseline_distance_mm = panel.get_directed_distance()
                    distance_mm_override = baseline_distance_mm + bounded_offset
    
                    if stage_c_use_warm_cache:
                        detector_config = copy.copy(stage_a_ctx.detector_configs[pid])
                        detector_config.distance_mm = distance_mm_override
                        detector_model = Detector(detector_config, device=device, dtype=dtype)
                        simulator = Simulator(
                            detector=detector_model,
                            crystal=crystal_model,
                            beam_config=stage_a_ctx.beam_config,
                            device=device,
                            dtype=dtype,
                        )
                    else:
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
            if best_loss_full[0] > 0:
                stage_a_final_loss = best_loss_full[0]
                improvement_c = (stage_a_final_loss - final_loss_value_c) / stage_a_final_loss
                if improvement_c < config.stage_c_min_loss_improvement:
                    status_c = "early_stop"
                    message_c = f"Stage C improvement {improvement_c:.4%} < {config.stage_c_min_loss_improvement:.4%} (≥0.002% gate calibrated per REFINE-007)"
    
            # Generate final Bragg array with Stage C adjustments
            with torch.no_grad():
                bragg_full_stage_c = np.zeros((n_panels, *panel_shape), dtype=np.float32)
                cell_params = crystal.get_unit_cell().parameters()
                perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
                perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
                perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)
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
    
                for pid in range(n_panels):
                    panel = detector[pid]
    
                    # Apply final bounded distance offset
                    bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm
                    baseline_distance_mm = panel.get_directed_distance()
                    distance_mm_override = baseline_distance_mm + bounded_offset
    
                    if stage_c_use_warm_cache:
                        detector_config = copy.copy(stage_a_ctx.detector_configs[pid])
                        detector_config.distance_mm = distance_mm_override
                        detector_model = Detector(detector_config, device=device, dtype=dtype)
                        simulator = Simulator(
                            detector=detector_model,
                            crystal=crystal_model,
                            beam_config=stage_a_ctx.beam_config,
                            device=device,
                            dtype=dtype,
                        )
                    else:
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
    
                # Update bragg_full with Stage C result
                bragg_full = bragg_full_stage_c
    
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
    
            telemetry_dict["C"] = telemetry_c
    
        return bragg_full, telemetry_dict
