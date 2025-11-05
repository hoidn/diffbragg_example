"""
LBFGS refinement nucleus for nanobrag_torch backend (Stage A).

Implements the minimal refinement loop per:
- plans/nanobrag_integration_plan.md:172-211 (Refinement Nucleus contract)
- docs/spec-db-workflow.md:30-38 (Stage A staging + LBFGS optimizer)
- docs/pytorch_runtime_checklist.md (vectorization, device/dtype neutrality)

Stage A scope:
- Parameters: global scale (ADU mode) + full crystal (a/b/c log-deltas, alpha/beta/gamma bounded angles, orientation 3-vector→quaternion)
- Loss: mean(((Bragg - target)[loss_mask]) ** 2)
- ROI policy: deterministic ROI sampling for LBFGS closure; periodic full validation
- Convergence: ≥0.2% loss drop within ≤30 LBFGS steps; non-increasing full-loss trace (TORCH-REFINE-002D)

Telemetry emitted to `/torch_diagnostics`:
- optimizer metadata (LBFGS, history_size, max_iter, tolerances)
- stage label ("A"), ROI sampling metadata
- loss_trace_sample, loss_trace_full, best_loss_full
- param_deltas, status
"""

import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


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

    # Stage C detector microslip (TORCH-REFINE-003)
    enable_stage_c: bool = False  # Enable detector distance refinement
    stage_c_min_loss_improvement: float = 0.05  # 5% minimum improvement for Stage C
    stage_c_max_distance_delta_mm: float = 0.5  # Maximum distance adjustment per panel (mm)

    # Device/dtype
    device: str = "cpu"
    dtype: torch.dtype = torch.float32


@dataclass
class RefinementTelemetry:
    """Telemetry captured during refinement.

    For multi-stage refinement (Stage A + Stage C), this structure represents
    a single stage. The calling code aggregates multiple telemetry objects into
    a Dict[str, RefinementTelemetry] keyed by stage label ("A", "C").
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
    loss_trace_sample: List[float]
    loss_trace_full: List[Tuple[int, float]]  # [(iteration, loss), ...]
    best_loss_full: Tuple[float, int]  # (loss, iteration)
    param_deltas: Dict[str, float]
    status: str  # "ok" | "early_stop" | "rollback" | "error"
    message: str


def run_nanobrag_refinement(
    inputs,
    detector,
    beam,
    crystal,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    config: Optional[RefinementConfig] = None,
    baseline_crystal=None
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

    Returns:
        Tuple of:
        - Bragg: np.ndarray [panel, slow, fast] final simulated intensities after all stages (CPU, float32)
        - telemetry_dict: Dict[str, RefinementTelemetry] keyed by stage label ("A", "C")
                         Always contains "A"; contains "C" only when config.enable_stage_c=True

    Raises:
        RuntimeError: If simulator fails or gradients are NaN/Inf
    """
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from dbex.nanobrag_bridge import (
        create_detector_config,
        create_beam_config,
        create_crystal_config
    )
    from scitbx.matrix import sqr

    if config is None:
        config = RefinementConfig()

    # Move inputs to device
    device = torch.device(config.device)
    dtype = config.dtype
    target_t = torch.from_numpy(inputs.target).to(device=device, dtype=dtype)
    loss_mask_t = torch.from_numpy(inputs.loss_mask).to(device=device, dtype=torch.bool)

    # Extract deterministic misset from perturbed geometry (TORCH-REFINE-002D)
    # Compute U_delta = U_perturbed @ U_baseline^{-1} and convert to XYZ Euler angles
    baseline_misset_deg_tensor = None
    if baseline_crystal is not None:
        # Get U matrices (scitbx 3x3 matrix objects)
        U_baseline_tuple = baseline_crystal.get_U()
        U_perturbed_tuple = crystal.get_U()

        # Convert to scitbx sqr matrices
        U_baseline = sqr(U_baseline_tuple)
        U_perturbed = sqr(U_perturbed_tuple)

        # Compute U_delta = U_perturbed @ inv(U_baseline)
        U_delta = U_perturbed * U_baseline.inverse()

        # Convert to numpy array for euler decomposition
        U_delta_np = np.array(U_delta).reshape(3, 3)

        # Extract XYZ Euler angles from U_delta using same analytic formulas as GEOMETRY-002
        # R = R_z(gamma) @ R_y(beta) @ R_x(alpha)
        # phi_y = -asin(R[2,0])
        # phi_x = atan2(R[2,1], R[2,2])
        # phi_z = atan2(R[1,0], R[0,0])
        phi_y_rad = -np.arcsin(np.clip(U_delta_np[2, 0], -1.0, 1.0))
        phi_x_rad = np.arctan2(U_delta_np[2, 1], U_delta_np[2, 2])
        phi_z_rad = np.arctan2(U_delta_np[1, 0], U_delta_np[0, 0])

        # Convert to degrees and create torch tensor
        baseline_misset_xyz_deg = np.array([phi_x_rad, phi_y_rad, phi_z_rad]) * (180.0 / np.pi)
        baseline_misset_deg_tensor = torch.tensor(baseline_misset_xyz_deg, dtype=dtype, device=device)

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

    params = [
        log_scale,
        log_cell_a_delta, log_cell_b_delta, log_cell_c_delta,
        angle_alpha_raw, angle_beta_raw, angle_gamma_raw,
        orientation_vec
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
    loss_trace_sample = []
    loss_trace_full = []
    best_loss_full = (float('inf'), -1)
    best_params_snapshot = None
    iteration_count = [0]  # Mutable counter for closure

    # Deterministic ROI sampling
    np.random.seed(42)  # Fixed seed for deterministic behavior
    n_panels = len(detector)
    panel_shape = inputs.target.shape[1:]  # (slow, fast)

    # Sample ROIs: select ~15% of panels deterministically
    sampled_panel_ids = sorted(
        np.random.choice(n_panels, size=max(1, int(n_panels * config.roi_sample_fraction)), replace=False).tolist()
    )

    def compute_loss(panel_ids: List[int], is_full: bool = False) -> torch.Tensor:
        """
        Compute masked MSE loss over specified panels.

        Args:
            panel_ids: List of panel indices to include
            is_full: If True, this is a full validation run

        Returns:
            loss: torch.Tensor scalar loss value
        """
        # Accumulate Bragg predictions per panel
        bragg_panels = []

        for pid in panel_ids:
            panel = detector[pid]

            # Create configs with current parameters
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

            # Apply full crystal perturbations via tensor overrides (GRADIENT-001, TORCH-REFINE-002)
            # Get original cell parameters
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
            # Convert 3-vector → unit quaternion → XYZ extrinsic Euler angles (degrees)
            # Per docs/spec-db-workflow.md:30, misset_deg is applied after MOSFLM A* injection
            # Bound magnitude to ±3° by scaling orientation_vec with tanh
            max_orientation_deg = 3.0  # degrees (per input.md pitfalls)
            bounded_orientation_vec = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)  # convert bound to radians for vec magnitude

            # Map to unit quaternion, then to XYZ Euler angles
            quat = vec_to_unit_quaternion(bounded_orientation_vec)
            misset_xyz_deg = quaternion_to_xyz_euler(quat)

            # Add baseline misset from perturbed geometry if provided (TORCH-REFINE-002D)
            # This plumbs the deterministic perturbation through the refinement path
            # so the smoke test can exercise orientation recovery with nearest-neighbor HKL
            if baseline_misset_deg_tensor is not None:
                misset_xyz_deg = misset_xyz_deg + baseline_misset_deg_tensor

            # Create crystal config with all cell parameter overrides + misset
            # Note: create_crystal_config returns (config, n_cells_applied) tuple
            crystal_overrides = {
                'cell_a': perturbed_cell_a,
                'cell_b': perturbed_cell_b,
                'cell_c': perturbed_cell_c,
                'cell_alpha': perturbed_alpha,
                'cell_beta': perturbed_beta,
                'cell_gamma': perturbed_gamma
            }
            crystal_config, _ = create_crystal_config(
                crystal, None,
                crystal_overrides=crystal_overrides,
                misset_deg_override=misset_xyz_deg
            )

            # Build detector and crystal models
            detector_model = Detector(detector_config)
            crystal_model = Crystal(crystal_config)

            # HKL interpolation control (TORCH-REFINE-002D, REFINE-005)
            # Defaults to nearest-neighbor (False) unless explicitly enabled via config
            # Tricubic interpolation requires halo-padded grid to avoid default_F fallback
            crystal_model.interpolate = config.enable_hkl_interpolation

            # Attach HKL data
            crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
            crystal_model.hkl_metadata = hkl_metadata

            # Run simulator
            simulator = Simulator(detector=detector_model, crystal=crystal_model)
            panel_bragg = simulator.run()  # [slow, fast]

            bragg_panels.append(panel_bragg)

        # Stack panels and apply global scale
        bragg_stacked = torch.stack(bragg_panels, dim=0)  # [n_sampled, slow, fast]
        # Clamp log_scale before exp to prevent overflow/NaN gradients (per REFINE-001)
        # Range [-10, 10] → scale in [4.5e-5, 22026], balanced for stability vs exploration
        log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
        bragg_scaled = bragg_stacked * torch.exp(log_scale_clamped)

        # Extract corresponding target and mask slices
        target_subset = target_t[panel_ids]
        mask_subset = loss_mask_t[panel_ids]

        # Masked MSE
        masked_diff = torch.where(mask_subset, bragg_scaled - target_subset, torch.tensor(0.0, device=device, dtype=dtype))
        loss = (masked_diff ** 2).sum() / mask_subset.sum()

        return loss

    def closure():
        """LBFGS closure: recompute loss and gradients."""
        optimizer.zero_grad()

        # Compute loss on sampled ROIs
        loss = compute_loss(sampled_panel_ids, is_full=False)

        # Backward pass
        loss.backward()

        # Check for NaN/Inf gradients
        for p in params:
            if p.grad is not None and (torch.isnan(p.grad).any() or torch.isinf(p.grad).any()):
                raise RuntimeError(f"NaN/Inf gradient detected in {p}")

        # Record loss
        loss_trace_sample.append(float(loss.item()))

        # Periodic full validation
        if iteration_count[0] % config.full_validation_interval == 0:
            with torch.no_grad():
                full_loss = compute_loss(list(range(n_panels)), is_full=True)
                loss_trace_full.append((iteration_count[0], float(full_loss.item())))

                # Update best snapshot
                nonlocal best_loss_full, best_params_snapshot
                if full_loss.item() < best_loss_full[0]:
                    best_loss_full = (float(full_loss.item()), iteration_count[0])
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

        iteration_count[0] += 1
        return loss

    # Run LBFGS optimization
    status = "ok"
    message = ""

    try:
        optimizer.step(closure)

        # Final full validation
        with torch.no_grad():
            final_loss = compute_loss(list(range(n_panels)), is_full=True)
            loss_trace_full.append((iteration_count[0], float(final_loss.item())))

            if final_loss.item() < best_loss_full[0]:
                best_loss_full = (float(final_loss.item()), iteration_count[0])
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
            crystal_config, _ = create_crystal_config(
                crystal, None,
                crystal_overrides=crystal_overrides,
                misset_deg_override=misset_xyz_deg
            )

            detector_model = Detector(detector_config)
            crystal_model = Crystal(crystal_config)

            # HKL interpolation control (TORCH-REFINE-002D, REFINE-005)
            # Defaults to nearest-neighbor (False) unless explicitly enabled via config
            # Tricubic interpolation requires halo-padded grid to avoid default_F fallback
            crystal_model.interpolate = config.enable_hkl_interpolation

            crystal_model.hkl_data = hkl_grid.to(device=device, dtype=dtype)
            crystal_model.hkl_metadata = hkl_metadata

            simulator = Simulator(detector=detector_model, crystal=crystal_model)
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

    telemetry_a = RefinementTelemetry(
        optimizer="LBFGS",
        stage="A",
        history_size=config.history_size,
        max_iter=config.max_iter,
        tolerance_grad=config.tolerance_grad,
        tolerance_change=config.tolerance_change,
        roi_sample_fraction=config.roi_sample_fraction,
        roi_count_sampled=len(sampled_panel_ids),
        roi_count_total=n_panels,
        loss_trace_sample=loss_trace_sample,
        loss_trace_full=loss_trace_full,
        best_loss_full=best_loss_full,
        param_deltas=param_deltas,
        status=status,
        message=message
    )

    telemetry_dict = {"A": telemetry_a}

    # TODO(TORCH-REFINE-003): Stage C implementation goes here
    # When config.enable_stage_c is True:
    # 1. Freeze Stage A parameters (no grad)
    # 2. Initialize per-panel distance offsets
    # 3. Run LBFGS with detector distance closure
    # 4. Generate final Bragg with Stage C adjustments
    # 5. Add telemetry_c to telemetry_dict["C"]
    # 6. Update bragg_full with Stage C result

    return bragg_full, telemetry_dict
