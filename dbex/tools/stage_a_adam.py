"""
Stage A Debug Tooling — Reusable Utilities

Extracted from plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py
Initiative: ARCH-REFACTOR-001 Phase D D2.1
Owner: galph

Core utilities for Stage A mapping/orientation debug instrumentation.
See `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T092000Z/phase_d_d2_planning_analysis.md` for extraction strategy.

Applied Findings:
- POLICY-001 (Environment Freeze): Uses existing dependencies only
- ARCH-ENGINE-002 (Lazy Imports): Preserves torch lazy import pattern
"""

from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Dict, List, Tuple

import numpy as np

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    build_structure_factor_grid,
    create_beam_config,
    create_crystal_config,
    create_detector_config,
    compute_baseline_misset_deg,
)
from dbex.refinement.stage_a_impl import (
    quaternion_to_xyz_euler,
    vec_to_unit_quaternion,
)
from dbex.physics.loss import _compute_variance_weighted_loss
# ParityMetrics and compute_parity_metrics imported lazily within functions
# that use them to avoid breaking CLI scripts (ARCH-ENGINE-002)


@dataclass
class StageADebugConfig:
    """Configuration for Stage A debug tooling runs.

    Attributes:
        repo_root: Path to repository root
        device: Torch device string (e.g., "cpu", "cuda:0")
        seed: Random seed for reproducibility
        mode: Execution mode ("phases" or "gradient_probe")
        phases: List of phase numbers to run
        adam_steps: Number of Adam optimizer steps for Phase 5
        adam_lr: Learning rate for Adam optimizer (cell+misset path)
        u_matrix_lr: Learning rate for Adam optimizer (U-matrix path)
        out_dir: Output directory override (None for auto-generated)
        dof_variants: List of DoF variant names to run (None for all)
        use_u_matrix: Enable U-matrix parameterization for orientation
        use_lbfgs: Use LBFGS optimizer instead of Adam (U-matrix path only)
        optimizer_steps: Number of optimizer steps (Adam or LBFGS)
        telemetry_dir: Directory for per-step telemetry JSON files
        base_output_dir: Base directory for auto-generated output paths
    """
    repo_root: Path
    device: str
    seed: int
    mode: str
    phases: List[int]
    adam_steps: int
    adam_lr: float
    u_matrix_lr: float
    out_dir: Path | None
    dof_variants: List[str] | None
    use_u_matrix: bool
    use_lbfgs: bool
    optimizer_steps: int
    telemetry_dir: Path | None
    base_output_dir: Path


def build_dataload(repo_root: Path) -> DataLoad:
    """Construct a DataLoad instance for canonical assets (prefer refined geometry).

    Parameters:
        repo_root: Path to repository root containing test fixtures and assets

    Returns:
        DataLoad: Configured DataLoad instance with experiment and reflection data

    Notes:
        Prefers refined geometry files (refined.expt/refl) over legacy (refGeom.expt/refl).
        Uses standard assets: scaled.mtz for structure factors, 747_mask.pkl for mask.
    """
    fixtures_root = repo_root / "tests" / "fixtures" / "golden_data" / "simple_cubic"
    refined_expt = fixtures_root / "refined.expt"
    refined_refl = fixtures_root / "refined.refl"
    legacy_expt = repo_root / "refGeom.expt"
    legacy_refl = repo_root / "refGeom.refl"

    if refined_expt.exists() and refined_refl.exists():
        expt = refined_expt
        refl = refined_refl
    else:
        expt = legacy_expt
        refl = legacy_refl

    mtz = repo_root / "scaled.mtz"
    mask = repo_root / "747_mask.pkl"

    args = argparse.Namespace(
        exptName=str(expt),
        reflName=str(refl),
        exptIdx=0,
        mtzFile=str(mtz),
        mtzCol="F,SIGF",
        maskFile=str(mask),
    )
    return DataLoad(args)


def setup_environment(seed: int, device_str: str) -> int:
    """Phase 0 — Environment lockdown and seeding.

    Parameters:
        seed: Random seed for numpy, random, and torch
        device_str: Device string (e.g., "cpu", "cuda:0")

    Returns:
        int: The seed value used (same as input)

    Notes:
        - Sets CUDA_VISIBLE_DEVICES="" for CPU mode (unless explicitly set)
        - Sets NANOBRAG_DISABLE_COMPILE=1 and KMP_DUPLICATE_LIB_OK=TRUE
        - Seeds random, numpy, and torch (if available)
        - Respects explicit CUDA device requests in device_str
        - Environment freeze policy: no package installation
    """
    if "CUDA_VISIBLE_DEVICES" not in os.environ:
        if device_str.lower().startswith("cuda"):
            # Respect explicit CUDA device requests; do not mask GPUs here.
            pass
        else:
            os.environ["CUDA_VISIBLE_DEVICES"] = ""

    os.environ.setdefault("NANOBRAG_DISABLE_COMPILE", "1")
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

    random.seed(seed)
    np.random.seed(seed)

    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        # Torch or CUDA may be unavailable in some environments; environment
        # freeze policy forbids installing additional packages here.
        pass

    return seed


def create_debug_run_dir(base_dir: Path) -> Tuple[str, Path]:
    """Create a timestamped debug run directory for this invocation.

    Parameters:
        base_dir: Base directory under which to create timestamped subdirectory

    Returns:
        Tuple[str, Path]: (timestamp string, output directory path)

    Notes:
        Timestamp format: %Y%m%dT%H%M%SZ (UTC)
        Creates directory structure: base_dir/<timestamp>/
        Directory is created with parents=True, exist_ok=True
    """
    from datetime import datetime

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_root = base_dir / timestamp
    out_root.mkdir(parents=True, exist_ok=True)
    return timestamp, out_root


def write_commands_txt(out_dir: Path, seed: int, argv: List[str]) -> None:
    """Record exact command line, seed, and key env vars for reproducibility.

    Parameters:
        out_dir: Output directory where commands.txt will be written
        seed: Random seed used for this run
        argv: Command-line arguments (typically sys.argv)

    Notes:
        Creates commands.txt with:
        - Command-line invocation
        - Seed value
        - Snapshot of key environment variables:
          - CUDA_VISIBLE_DEVICES
          - NANOBRAG_DISABLE_COMPILE
          - KMP_DUPLICATE_LIB_OK
    """
    env_snapshot = {
        "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
        "NANOBRAG_DISABLE_COMPILE": os.environ.get("NANOBRAG_DISABLE_COMPILE", ""),
        "KMP_DUPLICATE_LIB_OK": os.environ.get("KMP_DUPLICATE_LIB_OK", ""),
    }
    lines = [
        "# Stage A mapping Adam debug run",
        "",
        f"command: {' '.join(argv)}",
        f"seed: {seed}",
        "",
        "env:",
    ]
    for key, value in env_snapshot.items():
        lines.append(f"  {key}={value}")

    (out_dir / "commands.txt").write_text("\n".join(lines))


def import_stage_a_dependencies():
    """Import torch and nanobrag_torch components used for Stage A debugging.

    Returns:
        Tuple: (torch, TorchCrystal, TorchDetector, Simulator)

    Raises:
        ImportError: If torch or nanobrag_torch are unavailable

    Notes:
        Lazy import pattern to defer torch loading until actually needed.
        Environment freeze policy: does not install missing packages.
        Caller must handle ImportError and document torch requirement.
    """
    try:
        import torch
        from nanobrag_torch.models.crystal import Crystal as TorchCrystal  # type: ignore
        from nanobrag_torch.models.detector import Detector as TorchDetector  # type: ignore
        from nanobrag_torch.simulator import Simulator  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "Stage A mapping Adam debug tooling requires nanobrag_torch and torch. "
            f"Import failed: {exc}"
        ) from exc

    return torch, TorchCrystal, TorchDetector, Simulator


@dataclass
class StageAComponents:
    """Shared Stage A simulator components for mapping-aligned helpers.

    Attributes:
        torch: torch module reference
        device: torch.device instance
        dtype: torch dtype (typically torch.float32)
        target_t: Target intensity tensor
        sigma_t: Readout noise sigma tensor
        mask_t: Loss mask tensor (bool)
        hkl_grid: Structure factor grid tensor
        hkl_metadata: HKL metadata dictionary
        beam_config: Beam configuration object
        detector_models: List of TorchDetector instances (one per panel)
        sqrt_spot_scale: Square root of spot scale calibration factor
        N_cells: Number of unit cells (from calibration)
        apply_n_cells: Whether to apply N_cells scaling
        baseline_misset_deg_tensor: Baseline misset angles (degrees) as tensor
        use_u_matrix: Enable U-matrix parameterization (TORCH-GEOMETRY-PARITY-002)
        q_initial: Initial quaternion from MOSFLM A* (U-matrix mode only)
        B_ideal_reciprocal: Reciprocal B_ideal for U @ B conversion (U-matrix mode only)
    """

    torch: object
    device: object
    dtype: object
    target_t: object
    sigma_t: object
    mask_t: object
    hkl_grid: object
    hkl_metadata: Dict[str, object]
    beam_config: object
    detector_models: List[object]
    sqrt_spot_scale: float
    N_cells: object
    apply_n_cells: bool
    baseline_misset_deg_tensor: object
    # TORCH-GEOMETRY-PARITY-002 Phase C2: U-matrix parameterization support
    use_u_matrix: bool = False
    q_initial: object = None  # Initial quaternion from MOSFLM A*
    B_ideal_reciprocal: object = None  # Reciprocal B_ideal for U @ B conversion


def build_stage_a_components(
    dataload: DataLoad,
    context,
    *,
    device_str: str,
    use_u_matrix: bool = False,
) -> StageAComponents:
    """Construct shared Stage A tensors/config used by mapping helpers.

    Parameters:
        dataload: DataLoad instance with experiment/reflection data
        context: Mapping stage A context from build_mapping_stage_a_context()
        device_str: Device string (e.g., "cpu", "cuda:0")
        use_u_matrix: If True, initialize quaternion U-matrix params for orientation
            instead of cell+misset (TORCH-GEOMETRY-PARITY-002)

    Returns:
        StageAComponents: Container with all initialized Stage A components

    Raises:
        ImportError: If torch or nanobrag_torch are unavailable

    Notes:
        - Converts numpy arrays to torch tensors on specified device
        - Builds HKL structure factor grid (no halo)
        - Creates beam and detector configuration objects
        - Computes baseline misset relative to B_ideal frame
        - In U-matrix mode: derives U and B_ideal from MOSFLM A*, converts U to quaternion
        - CONVERGENCE-001 Phase C4: Validates A* reconstruction accuracy (float64 and float32)
        - CONVERGENCE-001 bugfix: U and B_ideal derived from same TorchCrystal computation
    """
    torch, TorchCrystal, TorchDetector, Simulator = import_stage_a_dependencies()

    device = torch.device(device_str)
    dtype = torch.float32

    inputs = context.inputs

    target_t = torch.tensor(inputs.target, device=device, dtype=dtype)
    sigma_t = torch.tensor(inputs.sigma_readout, device=device, dtype=dtype)
    mask_t = torch.tensor(inputs.loss_mask, device=device, dtype=torch.bool)

    if context.hkl_indices is not None and context.hkl_amplitudes is not None:
        hkl_indices = context.hkl_indices
        hkl_amplitudes = context.hkl_amplitudes
    else:
        hkl_indices = dataload.F.indices()
        hkl_amplitudes = dataload.F.data()

    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device,
        halo=False,
    )

    calibration = context.calibration
    if calibration is not None:
        spot_scale_override = calibration.get("spot_scale_override", 1.0)
        beam_flux = calibration.get("beam_flux")
        beam_exposure = calibration.get("beam_exposure")
        beamsize_mm = calibration.get("beamsize_mm")
        N_cells = calibration.get("N_cells")
    else:
        spot_scale_override = 1.0
        beam_flux = None
        beam_exposure = None
        beamsize_mm = None
        N_cells = None

    sqrt_spot_scale = float(np.sqrt(spot_scale_override))

    beam_config = create_beam_config(
        dataload.beam,
        flux=beam_flux,
        beamsize_mm=beamsize_mm,
        exposure=beam_exposure,
    )

    apply_n_cells = N_cells is not None

    n_panels = len(dataload.detector)
    detector_models: List[object] = []
    for pid in range(n_panels):
        det_cfg = create_detector_config(
            panel=dataload.detector[pid],
            beam=dataload.beam,
            trusted_mask=inputs.trusted_mask[pid],
        )
        mask_array = det_cfg.mask_array
        if mask_array is not None and not isinstance(mask_array, torch.Tensor):
            det_cfg.mask_array = torch.tensor(
                mask_array, dtype=torch.float32, device=device
            )
        elif mask_array is not None and (
            mask_array.device != device or mask_array.dtype != torch.float32
        ):
            det_cfg.mask_array = mask_array.to(device=device, dtype=torch.float32)

        detector_models.append(TorchDetector(det_cfg, device=device, dtype=dtype))

    # GEOMETRY-003 / TORCH-REFINE-002E:
    # Use robust misset derivation aligned to nanobrag's B_ideal frame by
    # requesting absolute misset relative to B_ideal (baseline_crystal=None).
    baseline_misset_deg_tensor = compute_baseline_misset_deg(
        dataload.crystal,
        None,
        device=device,
        dtype=dtype,
    )

    # TORCH-GEOMETRY-PARITY-002 Phase C2: U-matrix initialization
    q_initial = None
    B_ideal_reciprocal = None
    if use_u_matrix:
        from dbex.nanobrag_bridge import (
            derive_u_matrix_from_mosflm_a_star,
            matrix_to_quaternion,
        )
        # Extract MOSFLM A* from crystal
        A_star_mosflm = np.array(dataload.crystal.get_A(), dtype=np.float64).reshape(3, 3)
        cell = dataload.crystal.get_unit_cell()
        cell_params = cell.parameters()  # Convert to tuple (a, b, c, alpha, beta, gamma)
        # Derive U-matrix (no SO(3) projection - preserve mapping geometry exactly)
        # Get BOTH U and B_ideal from same TorchCrystal computation (CONVERGENCE-001 bugfix)
        # Ensures U @ B_ideal == A_star_mosflm numerically at initialization
        U_matrix, B_ideal_reciprocal_np = derive_u_matrix_from_mosflm_a_star(A_star_mosflm, cell_params)

        # Convert U to quaternion
        q_initial_np = matrix_to_quaternion(torch.tensor(U_matrix, dtype=torch.float64))
        q_initial = torch.tensor(q_initial_np, device=device, dtype=dtype)

        # Convert B_ideal to torch tensor
        B_ideal_reciprocal = torch.tensor(B_ideal_reciprocal_np, device=device, dtype=dtype)

        # CONVERGENCE-001 Phase C4: Verify A* reconstruction accuracy
        # Test if quaternion round-trip preserves A* to sufficient precision
        U_matrix_torch = torch.tensor(U_matrix, dtype=torch.float64, device=device)
        B_ideal_torch_f64 = torch.tensor(B_ideal_reciprocal_np, dtype=torch.float64, device=device)
        A_star_reconstructed_f64 = U_matrix_torch @ B_ideal_torch_f64
        A_star_original_f64 = torch.tensor(A_star_mosflm, dtype=torch.float64, device=device)

        reconstruction_error = torch.norm(A_star_reconstructed_f64 - A_star_original_f64).item()
        print(f"[C4 DIAGNOSTIC] A* reconstruction error (float64): {reconstruction_error:.15e}")

        # Test quaternion round-trip precision
        q_test = matrix_to_quaternion(U_matrix_torch)
        from dbex.nanobrag_bridge import quaternion_to_matrix
        U_roundtrip = quaternion_to_matrix(q_test / torch.norm(q_test))
        U_error = torch.norm(U_roundtrip - U_matrix_torch).item()
        print(f"[C4 DIAGNOSTIC] U matrix round-trip error (quat→matrix→quat→matrix): {U_error:.15e}")

        # Test float32 precision loss
        B_ideal_f32 = B_ideal_reciprocal  # Already converted to dtype (float32)
        U_f32 = U_matrix_torch.to(dtype=dtype)
        A_star_reconstructed_f32 = U_f32 @ B_ideal_f32
        A_star_original_f32 = A_star_original_f64.to(dtype=dtype)
        f32_error = torch.norm(A_star_reconstructed_f32 - A_star_original_f32).item()
        print(f"[C4 DIAGNOSTIC] A* reconstruction error (float32): {f32_error:.15e}")

        # DELETE the cctbx_cell() code below - no longer needed (CONVERGENCE-001 bugfix)
        # Prior bug: cctbx fractionalization_matrix() produced different B_ideal than TorchCrystal,
        # causing U @ B_ideal reconstruction to fail (chi²=1.425B vs expected ~990k)

    return StageAComponents(
        torch=torch,
        device=device,
        dtype=dtype,
        target_t=target_t,
        sigma_t=sigma_t,
        mask_t=mask_t,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        beam_config=beam_config,
        detector_models=detector_models,
        sqrt_spot_scale=sqrt_spot_scale,
        N_cells=N_cells,
        apply_n_cells=apply_n_cells,
        baseline_misset_deg_tensor=baseline_misset_deg_tensor,
        use_u_matrix=use_u_matrix,
        q_initial=q_initial,
        B_ideal_reciprocal=B_ideal_reciprocal,
    )


def stage_a_forward(
    dataload: DataLoad,
    context,
    components: StageAComponents,
    *,
    log_scale,
    log_cell_a_delta,
    log_cell_b_delta,
    log_cell_c_delta,
    angle_alpha_raw,
    angle_beta_raw,
    angle_gamma_raw,
    orientation_vec,
    q_params,  # TORCH-GEOMETRY-PARITY-002: quaternion for U-matrix mode (None if cell+misset)
    sigma_floor_sq_tensor,
    use_mapping_zero_geometry: bool,
):
    """Shared Stage A forward model used by no-op and Adam helpers.

    Parameters:
        dataload: DataLoad instance with experiment data
        context: Mapping stage A context
        components: StageAComponents container with initialized Stage A objects
        log_scale: Log-scale parameter (scalar tensor)
        log_cell_a_delta: Log-space delta for cell parameter a
        log_cell_b_delta: Log-space delta for cell parameter b
        log_cell_c_delta: Log-space delta for cell parameter c
        angle_alpha_raw: Raw (unbounded) alpha angle parameter
        angle_beta_raw: Raw (unbounded) beta angle parameter
        angle_gamma_raw: Raw (unbounded) gamma angle parameter
        orientation_vec: 3-element orientation vector (cell+misset path)
        q_params: Quaternion parameters for U-matrix mode (4-DOF). If None, uses
            cell+misset path with orientation_vec.
        sigma_floor_sq_tensor: Variance floor squared (scalar tensor)
        use_mapping_zero_geometry: If True, bypass parameterization and inject MOSFLM A* directly

    Returns:
        Tuple[Tensor, Tensor, dict]: (bragg_t, chi_sq_t, diagnostic_data)
            - bragg_t: Simulated Bragg intensities (shape matches target_t)
            - chi_sq_t: Chi-squared loss (scalar tensor)
            - diagnostic_data: Dict with A* checksum, max element, code path label

    Notes:
        - Zero-geometry path uses create_crystal_config with no overrides (MOSFLM A* injection)
        - Non-zero parameters use baseline misset + deltas with explicit crystal_overrides
        - TORCH-GEOMETRY-PARITY-002: U-matrix path uses quaternion → U → A* instead of cell+misset
        - CONVERGENCE-001 Phase C5: A* checksum tracking for code path equivalence diagnostic
        - CONVERGENCE-001 Phase C6: Closure bypass at zero to avoid U/B_ideal precision divergence
        - Cell parameter deltas: log-space (perturbed = nominal * exp(delta))
        - Angle deltas: tanh-bounded (perturbed = nominal + tanh(raw) * max_angle_delta)
        - Orientation: tanh-bounded to ±10° in cell+misset path
        - Scale: clamped to [-10, 10] log-space
    """
    import numpy as np  # CONVERGENCE-001 Phase C5: needed for A* checksum extraction
    torch = components.torch
    device = components.device
    dtype = components.dtype

    target_t = components.target_t
    sigma_t = components.sigma_t
    mask_t = components.mask_t
    hkl_grid = components.hkl_grid
    hkl_metadata = components.hkl_metadata
    beam_config = components.beam_config
    detector_models = components.detector_models
    sqrt_spot_scale = components.sqrt_spot_scale
    N_cells = components.N_cells
    apply_n_cells = components.apply_n_cells
    baseline_misset_deg_tensor = components.baseline_misset_deg_tensor

    # Geometry path:
    # - Zero-geometry path uses create_crystal_config with no overrides so
    #   MOSFLM A* injection and mapping geometry are preserved.
    # - Non-zero parameters use baseline misset + deltas and explicit
    #   crystal_overrides, matching Stage A refinement conventions.
    # TORCH-GEOMETRY-PARITY-002: When use_u_matrix=True, orientation is via
    # quaternion → U → A* instead of cell+misset decomposition.

    # CONVERGENCE-001 Phase C5: A* checksum tracking for code path equivalence diagnostic
    a_star_checksum = None
    a_star_max_element = None
    code_path = None

    # CONVERGENCE-001 Phase C6: Check if ALL parameter deltas are zero (at mapping zero point)
    # If true, bypass U/B_ideal round-trip and use direct MOSFLM A* injection
    # to avoid numerical precision divergence confirmed by Phase C5 diagnostic.
    all_params_at_zero = True  # Assume true, falsify below

    # Check cell parameter deltas (6 DOF)
    if not torch.allclose(log_cell_a_delta, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9):
        all_params_at_zero = False
    if not torch.allclose(log_cell_b_delta, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9):
        all_params_at_zero = False
    if not torch.allclose(log_cell_c_delta, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9):
        all_params_at_zero = False
    if not torch.allclose(angle_alpha_raw, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9):
        all_params_at_zero = False
    if not torch.allclose(angle_beta_raw, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9):
        all_params_at_zero = False
    if not torch.allclose(angle_gamma_raw, torch.tensor(0.0, device=device, dtype=dtype), atol=1e-9):
        all_params_at_zero = False

    # Check orientation parameter delta (4 DOF quaternion for U-matrix, or 3 DOF orientation_vec for cell+misset)
    if components.use_u_matrix:
        # U-matrix path: compare q_params to q_initial
        if q_params is not None and not torch.allclose(q_params, components.q_initial, atol=1e-9):
            all_params_at_zero = False
    else:
        # Cell+misset path: check orientation_vec
        if not torch.allclose(orientation_vec, torch.tensor([0.0, 0.0, 0.0], device=device, dtype=dtype), atol=1e-9):
            all_params_at_zero = False

    # If all deltas are zero AND we're in closure mode, force direct MOSFLM injection
    use_direct_mosflm_injection = use_mapping_zero_geometry or all_params_at_zero

    if use_direct_mosflm_injection:
        crystal_config, _ = create_crystal_config(
            dataload.crystal,
            dataload.Expt,
            N_cells=N_cells,
            apply_n_cells=apply_n_cells,
            crystal_overrides=None,
            misset_deg_override=None,
        )
        # CONVERGENCE-001 Phase C5: Extract A* from crystal_config for zero-point path
        A_star_direct = np.array([
            crystal_config.mosflm_a_star,
            crystal_config.mosflm_b_star,
            crystal_config.mosflm_c_star
        ], dtype=np.float64).reshape(3, 3)
        a_star_checksum = float(A_star_direct.sum())
        a_star_max_element = float(np.abs(A_star_direct).max())
        # CONVERGENCE-001 Phase C6: Distinguish explicit zero-point check from closure bypass at zero
        code_path = "zero_point" if use_mapping_zero_geometry else "closure_bypass_at_zero"
    else:
        cell_params = dataload.crystal.get_unit_cell().parameters()

        perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
        perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
        perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)

        max_angle_delta = 10.0
        perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
        perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
        perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

        crystal_overrides = {
            "cell_a": perturbed_cell_a,
            "cell_b": perturbed_cell_b,
            "cell_c": perturbed_cell_c,
            "cell_alpha": perturbed_alpha,
            "cell_beta": perturbed_beta,
            "cell_gamma": perturbed_gamma,
        }

        # TORCH-GEOMETRY-PARITY-002: Branch on U-matrix vs cell+misset orientation
        if components.use_u_matrix:
            # U-matrix path: quaternion → rotation matrix → A*
            from dbex.nanobrag_bridge import quaternion_to_matrix
            # Normalize quaternion to unit sphere
            q_norm = q_params / torch.norm(q_params)
            # Convert to rotation matrix U ∈ SO(3)
            U_matrix = quaternion_to_matrix(q_norm)
            # Reconstruct A* = U @ B_ideal_reciprocal
            A_star_new = U_matrix @ components.B_ideal_reciprocal
            # CONVERGENCE-001 Phase B5 fix: Use mosflm_a_star/b_star/c_star keys
            # (create_crystal_config does NOT support "A_star" key)
            A_star_np = A_star_new.detach().cpu().numpy()
            crystal_overrides["mosflm_a_star"] = tuple(A_star_np[:, 0].tolist())
            crystal_overrides["mosflm_b_star"] = tuple(A_star_np[:, 1].tolist())
            crystal_overrides["mosflm_c_star"] = tuple(A_star_np[:, 2].tolist())
            misset_xyz_deg = None  # No misset override in U-matrix mode
            # CONVERGENCE-001 Phase C5: Extract A* checksums for closure path
            A_star_roundtrip = A_star_np  # Already numpy from above
            a_star_checksum = float(A_star_roundtrip.sum())
            a_star_max_element = float(np.abs(A_star_roundtrip).max())
            code_path = "closure"
        else:
            # Cell+misset path: orientation_vec → Euler angles
            max_orientation_deg = 10.0
            bounded_orientation_vec = (
                torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
            )
            quat = vec_to_unit_quaternion(bounded_orientation_vec)
            delta_misset_deg = quaternion_to_xyz_euler(quat)
            if baseline_misset_deg_tensor is not None:
                misset_xyz_deg = baseline_misset_deg_tensor + delta_misset_deg
            else:
                misset_xyz_deg = delta_misset_deg

        crystal_config, _ = create_crystal_config(
            dataload.crystal,
            dataload.Expt,
            N_cells=N_cells,
            apply_n_cells=apply_n_cells,
            crystal_overrides=crystal_overrides,
            misset_deg_override=misset_xyz_deg,
        )

    from nanobrag_torch.models.experiment import (  # type: ignore  # noqa: E402
        ExperimentModel,
    )

    log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)

    bragg_t = torch.zeros_like(target_t, device=device, dtype=dtype)
    for pid, det_model in enumerate(detector_models):
        exp_model = ExperimentModel(
            crystal_config=crystal_config,
            detector_config=det_model.config,  # type: ignore[attr-defined]
            beam_config=beam_config,
            device=device,
            dtype=dtype,
            param_init="frozen",
            hkl_data=hkl_grid,
            hkl_metadata=hkl_metadata,
        )
        panel_output = exp_model()
        panel_scaled = panel_output * sqrt_spot_scale * torch.exp(log_scale_clamped)
        bragg_t[pid] = panel_scaled

    chi_sq_t, _, _, _ = _compute_variance_weighted_loss(
        bragg_t,
        target_t,
        mask_t,
        sigma_t,
        sigma_floor_sq_tensor,
    )

    # CONVERGENCE-001 Phase C5: Return diagnostic data for telemetry
    diagnostic_data = {
        "a_star_checksum": a_star_checksum,
        "a_star_max_element": a_star_max_element,
        "code_path": code_path,
    }

    return bragg_t, chi_sq_t, diagnostic_data


def build_stage_a_bragg_noop(
    dataload: DataLoad,
    context,
    *,
    device_str: str = "cpu",
) -> np.ndarray:
    """Phase 1 helper — run Stage A simulator with zero deltas and log_scale=0.

    Parameters:
        dataload: DataLoad instance with experiment data
        context: Mapping stage A context
        device_str: Device string (default: "cpu")

    Returns:
        np.ndarray: Simulated Bragg intensities at mapping zero point (float32)

    Notes:
        - Runs Stage A forward model with all parameter deltas = 0
        - Uses use_mapping_zero_geometry=True to inject MOSFLM A* directly
        - Returns numpy array (CPU) for comparison with mapping Bragg
        - No gradients computed (torch.no_grad context)
    """
    components = build_stage_a_components(
        dataload,
        context,
        device_str=device_str,
    )

    torch = components.torch
    device = components.device
    dtype = components.dtype

    sigma_floor_sq_tensor = torch.tensor(
        float(context.sigma_floor_value ** 2),
        device=device,
        dtype=dtype,
    )

    with torch.no_grad():
        bragg_t, _, _ = stage_a_forward(
            dataload,
            context,
            components,
            log_scale=torch.tensor(0.0, device=device, dtype=dtype),
            log_cell_a_delta=torch.tensor(0.0, device=device, dtype=dtype),
            log_cell_b_delta=torch.tensor(0.0, device=device, dtype=dtype),
            log_cell_c_delta=torch.tensor(0.0, device=device, dtype=dtype),
            angle_alpha_raw=torch.tensor(0.0, device=device, dtype=dtype),
            angle_beta_raw=torch.tensor(0.0, device=device, dtype=dtype),
            angle_gamma_raw=torch.tensor(0.0, device=device, dtype=dtype),
            orientation_vec=torch.zeros(3, device=device, dtype=dtype),
            q_params=None,
            sigma_floor_sq_tensor=sigma_floor_sq_tensor,
            use_mapping_zero_geometry=True,
        )

    return bragg_t.cpu().numpy().astype(np.float32)


@dataclass
class ForwardModelProbeSummary:
    """Summary statistics for forward model probe (Phase 1).

    Attributes:
        max_abs_diff: Maximum absolute difference between Stage A and mapping Bragg
        mean_abs_diff: Mean absolute difference
        n_roi: Number of ROIs analyzed
        corr_median_mapping: Median correlation coefficient (mapping Bragg vs data)
        corr_median_stage_a_noop: Median correlation coefficient (Stage A no-op vs data)
    """
    max_abs_diff: float
    mean_abs_diff: float
    n_roi: int
    corr_median_mapping: float
    corr_median_stage_a_noop: float


def run_forward_model_probe(
    dataload: DataLoad,
    context,
    *,
    device_str: str,
    out_dir: Path,
) -> Dict[str, object]:
    """Phase 1 — Forward-model equality probe.

    Parameters:
        dataload: DataLoad instance
        context: Mapping stage A context (must have bragg_zero_iter)
        device_str: Device string
        out_dir: Output directory for forward_model_probe.json

    Returns:
        Dict: Payload with summary statistics and per-ROI metrics

    Notes:
        - Compares mapping Bragg (context.bragg_zero_iter) vs Stage A no-op
        - Computes max/mean absolute difference
        - Computes per-ROI correlation coefficients vs data
        - Writes forward_model_probe.json to out_dir
    """
    # Lazy import (ARCH-ENGINE-002)
    from tests.fixtures.parity_loader import ParityMetrics, compute_parity_metrics

    bragg_mapping = np.asarray(context.bragg_zero_iter, dtype=np.float32)
    bragg_stage_a_noop = build_stage_a_bragg_noop(
        dataload,
        context,
        device_str=device_str,
    )

    diff = bragg_stage_a_noop.astype(np.float64) - bragg_mapping.astype(np.float64)
    max_abs_diff = float(np.max(np.abs(diff)))
    mean_abs_diff = float(np.mean(np.abs(diff)))

    inputs = context.inputs
    roi_rows: List[Dict[str, object]] = []
    corr_mapping: List[float] = []
    corr_stage: List[float] = []

    for roi_index, (pid, bbox) in enumerate(inputs.panel_slices):
        x0, x1, y0, y1 = map(int, bbox)

        data_roi = inputs.target[pid, y0:y1, x0:x1]
        mask_roi = inputs.loss_mask[pid, y0:y1, x0:x1]
        mapping_roi = bragg_mapping[pid, y0:y1, x0:x1]
        stage_roi = bragg_stage_a_noop[pid, y0:y1, x0:x1]

        metrics_mapping: ParityMetrics = compute_parity_metrics(
            mapping_roi, data_roi, loss_mask=mask_roi
        )
        metrics_stage: ParityMetrics = compute_parity_metrics(
            stage_roi, data_roi, loss_mask=mask_roi
        )

        cm = float(metrics_mapping.correlation)
        cs = float(metrics_stage.correlation)
        lm = float(metrics_mapping.localization)
        ls = float(metrics_stage.localization)

        if not np.isnan(cm):
            corr_mapping.append(cm)
        if not np.isnan(cs):
            corr_stage.append(cs)

        roi_rows.append(
            {
                "roi_index": int(roi_index),
                "panel_id": int(pid),
                "bbox": [int(x0), int(x1), int(y0), int(y1)],
                "corr_mapping": cm,
                "corr_stage_a_noop": cs,
                "corr_delta": cs - cm if not np.isnan(cs) and not np.isnan(cm) else float("nan"),
                "localization_mapping": lm,
                "localization_stage_a_noop": ls,
            }
        )

    summary = ForwardModelProbeSummary(
        max_abs_diff=max_abs_diff,
        mean_abs_diff=mean_abs_diff,
        n_roi=len(roi_rows),
        corr_median_mapping=median(corr_mapping) if corr_mapping else float("nan"),
        corr_median_stage_a_noop=median(corr_stage) if corr_stage else float("nan"),
    )

    payload: Dict[str, object] = {
        "summary": asdict(summary),
        "per_roi": roi_rows,
    }

    (out_dir / "forward_model_probe.json").write_text(json.dumps(payload, indent=2))
    return payload


def run_loss_alignment_probe(
    context,
    *,
    device_str: str,
    out_dir: Path,
) -> Dict[str, object]:
    """Phase 2 — Loss-definition alignment at mapping point.

    Parameters:
        context: Mapping stage A context (must have bragg_zero_iter, diagnostics)
        device_str: Device string
        out_dir: Output directory for loss_alignment.json

    Returns:
        Dict: Payload with chi-squared comparison (mapping vs Stage A)

    Notes:
        - Evaluates Stage A variance-weighted chi-squared loss at mapping Bragg
        - Compares with context.diagnostics["chi_squared"] from mapping code
        - Reports absolute and relative differences
        - Writes loss_alignment.json to out_dir
    """
    import torch

    device = torch.device(device_str)
    dtype = torch.float32

    inputs = context.inputs

    target_t = torch.tensor(inputs.target, device=device, dtype=dtype)
    sigma_t = torch.tensor(inputs.sigma_readout, device=device, dtype=dtype)
    mask_t = torch.tensor(inputs.loss_mask, device=device, dtype=torch.bool)
    bragg_t = torch.tensor(context.bragg_zero_iter, device=device, dtype=dtype)
    sigma_floor_sq_tensor = torch.tensor(
        float(context.sigma_floor_value ** 2),
        device=device,
        dtype=dtype,
    )

    chi_sq_t, masked_mse_t, masked_pixels, clamped_pixels = _compute_variance_weighted_loss(
        bragg_t,
        target_t,
        mask_t,
        sigma_t,
        sigma_floor_sq_tensor,
    )

    chi2_stage_a = float(chi_sq_t.item())
    mse_stage_a = float(masked_mse_t.item())

    chi2_mapping = float(context.diagnostics.get("chi_squared", float("nan")))
    chi2_abs_diff = (
        chi2_stage_a - chi2_mapping if not np.isnan(chi2_mapping) else float("nan")
    )
    chi2_rel_diff = (
        chi2_abs_diff / chi2_mapping if not np.isnan(chi2_mapping) and chi2_mapping != 0 else float("nan")
    )

    payload: Dict[str, object] = {
        "chi2_mapping": chi2_mapping,
        "chi2_stage_a": chi2_stage_a,
        "chi2_abs_diff": chi2_abs_diff,
        "chi2_rel_diff": chi2_rel_diff,
        "masked_pixels": int(masked_pixels),
        "clamped_pixels": int(clamped_pixels),
        "sigma_floor_value": float(context.sigma_floor_value),
    }

    (out_dir / "loss_alignment.json").write_text(json.dumps(payload, indent=2))
    return payload


def stage_a_adam_core(
    dataload: DataLoad,
    context,
    *,
    device_str: str,
    n_steps: int,
    lr: float,
    train_scale: bool,
    train_cell: bool,
    train_orientation: bool,
    use_u_matrix: bool = False,
    use_lbfgs: bool = False,
    telemetry_output_dir: str | None = None,
) -> Dict[str, object]:
    """Core helper for Stage A Adam experiments (Phase 4 / Phase 5).

    Parameters:
        dataload: DataLoad instance
        context: Mapping stage A context
        device_str: Device string
        n_steps: Number of optimizer steps
        lr: Learning rate (Adam or LBFGS lr parameter)
        train_scale: Enable scale parameter training
        train_cell: Enable cell parameter training
        train_orientation: Enable orientation parameter training
        use_u_matrix: If True, use quaternion U-matrix parameterization for
            orientation (TORCH-GEOMETRY-PARITY-002)
        use_lbfgs: If True, use LBFGS optimizer instead of Adam for U-matrix path
            (TORCH-GEOMETRY-CONVERGENCE-001 Test B1)
        telemetry_output_dir: Directory for per-step telemetry JSON files (optional)

    Returns:
        Dict: Payload with optimizer config, parameters (initial/final), chi-squared,
              loss trace, zero-point summary, CC summary, per-ROI metrics

    Notes:
        - Initializes all parameters at zero (mapping zero point)
        - For zero-point probes (n_steps=0, train_scale=False), forces log_scale=0
        - Uses global_scale_hint from context if available (for non-zero-point runs)
        - Optimizer selection: LBFGS (use_lbfgs=True, use_u_matrix=True) or Adam (default)
        - LBFGS: lr=1.0, max_iter=20, strong_wolfe line search
        - Adam: lr from caller, trainable params only
        - Telemetry: Emits per-step JSON files if telemetry_output_dir is set
        - Zero-point alignment metrics: max/mean abs diff vs mapping Bragg
        - Per-ROI CC metrics: before/after optimization, vs mapping Bragg reference
    """
    # Lazy import (ARCH-ENGINE-002)
    from tests.fixtures.parity_loader import ParityMetrics, compute_parity_metrics

    components = build_stage_a_components(
        dataload,
        context,
        device_str=device_str,
        use_u_matrix=use_u_matrix,
    )

    torch = components.torch
    device = components.device
    dtype = components.dtype

    inputs = context.inputs

    if inputs.global_scale_hint is not None and inputs.global_scale_hint > 0:
        initial_log_scale = float(np.log(inputs.global_scale_hint))
    else:
        initial_log_scale = 0.0
    # For zero-point probes (no trainable scale, no steps), force log_scale=0
    # so the Stage A zero point matches the mapping Bragg scale.
    if not train_scale and n_steps <= 0:
        initial_log_scale = 0.0
    # Plan-local global scale parameter used as a proxy for the
    # beam δ_log_fluence Stage-A DOF described in docs/nanobrag_api.md.

    log_scale = torch.tensor(
        initial_log_scale,
        device=device,
        dtype=dtype,
        requires_grad=train_scale,
    )

    log_cell_a_delta = torch.tensor(
        0.0, device=device, dtype=dtype, requires_grad=train_cell
    )
    log_cell_b_delta = torch.tensor(
        0.0, device=device, dtype=dtype, requires_grad=train_cell
    )
    log_cell_c_delta = torch.tensor(
        0.0, device=device, dtype=dtype, requires_grad=train_cell
    )

    angle_alpha_raw = torch.tensor(
        0.0, device=device, dtype=dtype, requires_grad=train_orientation
    )
    angle_beta_raw = torch.tensor(
        0.0, device=device, dtype=dtype, requires_grad=train_orientation
    )
    angle_gamma_raw = torch.tensor(
        0.0, device=device, dtype=dtype, requires_grad=train_orientation
    )

    orientation_vec = torch.zeros(
        3, device=device, dtype=dtype, requires_grad=train_orientation
    )

    # TORCH-GEOMETRY-PARITY-002: U-matrix initialization
    q_params = None
    if use_u_matrix:
        # Initialize quaternion from q_initial (already computed in components)
        q_params = components.q_initial.clone().requires_grad_(train_orientation)

    params = [
        log_scale,
        log_cell_a_delta,
        log_cell_b_delta,
        log_cell_c_delta,
        angle_alpha_raw,
        angle_beta_raw,
        angle_gamma_raw,
    ]
    # Add orientation params based on mode
    if use_u_matrix and q_params is not None:
        params.append(q_params)
    else:
        params.append(orientation_vec)

    trainable_params = [p for p in params if p.requires_grad]

    # TORCH-GEOMETRY-CONVERGENCE-001 Test B1: Support LBFGS optimizer for U-matrix path
    if trainable_params:
        if use_lbfgs and use_u_matrix:
            # LBFGS for quaternion U-matrix refinement
            optimizer = torch.optim.LBFGS(
                trainable_params,
                lr=1.0,  # LBFGS uses line search; LR=1.0 is standard
                max_iter=20,  # Per-step line search iterations
                tolerance_grad=1e-7,
                tolerance_change=1e-9,
                history_size=10,
                line_search_fn='strong_wolfe'
            )
            print("Stage A: Using LBFGS optimizer for U-matrix path (CONVERGENCE-001 Test B1)")
        else:
            # Default Adam optimizer
            optimizer = torch.optim.Adam(trainable_params, lr=lr)
            if use_u_matrix:
                print("Stage A: Using Adam optimizer for U-matrix path (default)")
            else:
                print("Stage A: Using Adam optimizer for cell+misset path (default)")
    else:
        optimizer = None

    sigma_floor_sq_tensor = torch.tensor(
        float(context.sigma_floor_value ** 2),
        device=device,
        dtype=dtype,
    )

    def _forward_once(use_mapping_zero_geometry: bool) -> Tuple[torch.Tensor, torch.Tensor, dict]:
        """Forward model wrapper that returns (bragg, chi_sq, diagnostic_data).

        diagnostic_data contains Phase C5 A* checksum tracking for code path equivalence.
        """
        return stage_a_forward(
            dataload,
            context,
            components,
            log_scale=log_scale,
            log_cell_a_delta=log_cell_a_delta,
            log_cell_b_delta=log_cell_b_delta,
            log_cell_c_delta=log_cell_c_delta,
            angle_alpha_raw=angle_alpha_raw,
            angle_beta_raw=angle_beta_raw,
            angle_gamma_raw=angle_gamma_raw,
            orientation_vec=orientation_vec,
            q_params=q_params,
            sigma_floor_sq_tensor=sigma_floor_sq_tensor,
            use_mapping_zero_geometry=use_mapping_zero_geometry,
        )

    with torch.no_grad():
        # Always treat the initial parameters as the mapping-aligned zero point.
        bragg_before_t, chi_sq_before_t, _ = _forward_once(use_mapping_zero_geometry=True)

    loss_trace: List[float] = [float(chi_sq_before_t.item())]

    if optimizer is not None and n_steps > 0:
        if use_lbfgs and use_u_matrix:
            # LBFGS requires closure pattern
            for step_idx in range(n_steps):
                def closure():
                    optimizer.zero_grad()
                    bragg_t, chi_sq_t, _ = _forward_once(use_mapping_zero_geometry=False)
                    chi_sq_t.backward()
                    return chi_sq_t

                # Get loss value before optimizer step for telemetry
                with torch.no_grad():
                    _, chi_sq_before_step, diag_before_step = _forward_once(use_mapping_zero_geometry=False)

                # Telemetry: Emit per-step metrics (TORCH-GEOMETRY-CONVERGENCE-001 Phase A1)
                if telemetry_output_dir and q_params is not None:
                    from pathlib import Path

                    # Capture parameters (before optimizer step)
                    q_norm_value = torch.norm(q_params).item()
                    telemetry_params = {
                        'step_index': step_idx,
                        'q_params': q_params.detach().cpu().tolist(),
                        'q_norm_value': q_norm_value,
                        'log_scale': log_scale.item(),
                    }

                    # For LBFGS, gradients are computed inside closure
                    # We capture them after a forward/backward pass before step()
                    optimizer.zero_grad()
                    _, chi_sq_temp, diag_temp = _forward_once(use_mapping_zero_geometry=False)
                    chi_sq_temp.backward()

                    telemetry_gradients = {
                        'grad_q_norm': torch.norm(q_params.grad).item() if q_params.grad is not None else None,
                        'grad_q_max': torch.max(torch.abs(q_params.grad)).item() if q_params.grad is not None else None,
                        'grad_q_min': torch.min(torch.abs(q_params.grad)).item() if q_params.grad is not None else None,
                        'grad_log_scale': torch.abs(log_scale.grad).item() if log_scale.grad is not None else None,
                        'grad_has_nan': torch.isnan(q_params.grad).any().item() if q_params.grad is not None else False,
                        'grad_has_inf': torch.isinf(q_params.grad).any().item() if q_params.grad is not None else False,
                    }

                    telemetry_loss = {
                        'chi_squared': chi_sq_before_step.item(),
                        'masked_mse': None,
                        'masked_pixels': None,
                        'clamped_pixels': None,
                        'clamp_fraction': None,
                    }

                    telemetry_variance = {
                        'i_model_min': None,
                        'i_model_median': None,
                        'i_model_max': None,
                        'i_model_std': None,
                    }

                    # CONVERGENCE-001 Phase C5: Add A* checksum diagnostic data
                    telemetry_diagnostics = {
                        'a_star_checksum': diag_temp.get('a_star_checksum'),
                        'a_star_max_element': diag_temp.get('a_star_max_element'),
                        'code_path': diag_temp.get('code_path'),
                    }

                    telemetry_step = {
                        **telemetry_params,
                        **telemetry_gradients,
                        **telemetry_loss,
                        **telemetry_variance,
                        **telemetry_diagnostics,
                    }

                    try:
                        telemetry_path = Path(telemetry_output_dir) / f"telemetry_step_{step_idx:03d}.json"
                        telemetry_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(telemetry_path, 'w') as f:
                            json.dump(telemetry_step, f, indent=2)
                    except Exception as e:
                        import sys
                        print(f"Warning: Failed to write telemetry JSON at step {step_idx}: {e}", file=sys.stderr)

                # LBFGS step with closure
                optimizer.step(closure)

                # Record loss after step
                with torch.no_grad():
                    _, chi_sq_after_step, _ = _forward_once(use_mapping_zero_geometry=False)
                    loss_trace.append(float(chi_sq_after_step.item()))
        else:
            # Adam pattern (no closure)
            for step_idx in range(n_steps):
                optimizer.zero_grad()
                bragg_t, chi_sq_t, diag_data = _forward_once(use_mapping_zero_geometry=False)
                chi_sq_t.backward()

                # Telemetry: Emit per-step metrics (TORCH-GEOMETRY-CONVERGENCE-001 Phase A1)
                if telemetry_output_dir and use_u_matrix and q_params is not None:
                    from pathlib import Path

                    # Capture parameters (before optimizer step)
                    q_norm_value = torch.norm(q_params).item()
                    telemetry_params = {
                        'step_index': step_idx,
                        'q_params': q_params.detach().cpu().tolist(),
                        'q_norm_value': q_norm_value,
                        'log_scale': log_scale.item(),
                    }

                    # Capture gradients (after backward, before step)
                    telemetry_gradients = {
                        'grad_q_norm': torch.norm(q_params.grad).item() if q_params.grad is not None else None,
                        'grad_q_max': torch.max(torch.abs(q_params.grad)).item() if q_params.grad is not None else None,
                        'grad_q_min': torch.min(torch.abs(q_params.grad)).item() if q_params.grad is not None else None,
                        'grad_log_scale': torch.abs(log_scale.grad).item() if log_scale.grad is not None else None,
                        'grad_has_nan': torch.isnan(q_params.grad).any().item() if q_params.grad is not None else False,
                        'grad_has_inf': torch.isinf(q_params.grad).any().item() if q_params.grad is not None else False,
                    }

                    # Capture loss (chi_squared from forward pass)
                    # Note: This script doesn't have per-pixel variance stats available inline
                    # so we emit simplified telemetry with chi_squared only
                    telemetry_loss = {
                        'chi_squared': chi_sq_t.item(),
                        'masked_mse': None,  # Not available in this simplified loop
                        'masked_pixels': None,
                        'clamped_pixels': None,
                        'clamp_fraction': None,
                    }

                    # Variance components: Not available in this simplified forward loop
                    telemetry_variance = {
                        'i_model_min': None,
                        'i_model_median': None,
                        'i_model_max': None,
                        'i_model_std': None,
                    }

                    # CONVERGENCE-001 Phase C5: Add A* checksum diagnostic data
                    telemetry_diagnostics = {
                        'a_star_checksum': diag_data.get('a_star_checksum'),
                        'a_star_max_element': diag_data.get('a_star_max_element'),
                        'code_path': diag_data.get('code_path'),
                    }

                    # Combine and emit INIT telemetry (TORCH-GEOMETRY-CONVERGENCE-001 Phase B4)
                    telemetry_step_init = {
                        **telemetry_params,
                        **telemetry_gradients,
                        **telemetry_loss,
                        **telemetry_variance,
                        **telemetry_diagnostics,
                        'closure_state': 'before_optimizer_step',
                    }

                    try:
                        telemetry_path = Path(telemetry_output_dir) / f"telemetry_step_{step_idx:03d}_init.json"
                        telemetry_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(telemetry_path, 'w') as f:
                            json.dump(telemetry_step_init, f, indent=2)
                    except Exception as e:
                        import sys
                        print(f"Warning: Failed to write telemetry JSON at step {step_idx}: {e}", file=sys.stderr)

                optimizer.step()
                loss_trace.append(float(chi_sq_t.item()))

                # Emit POST telemetry after optimizer step (TORCH-GEOMETRY-CONVERGENCE-001 Phase B4)
                if telemetry_output_dir and use_u_matrix and q_params is not None:
                    # Recompute forward pass to get post-step chi²
                    with torch.no_grad():
                        _, chi_sq_post, _ = _forward_once(use_mapping_zero_geometry=False)

                    telemetry_step_post = {
                        'step_index': step_idx,
                        'closure_state': 'after_optimizer_step',
                        'q_params': q_params.detach().cpu().tolist(),
                        'q_norm_value': torch.norm(q_params).item(),
                        'log_scale': log_scale.item(),
                        'chi_squared': chi_sq_post.item(),
                        # Gradients are not available after step (would need another backward pass)
                        'grad_q_norm': None,
                        'grad_log_scale': None,
                        'grad_has_nan': None,
                        'grad_has_inf': None,
                    }

                    try:
                        telemetry_path_post = Path(telemetry_output_dir) / f"telemetry_step_{step_idx:03d}_post.json"
                        with open(telemetry_path_post, 'w') as f:
                            json.dump(telemetry_step_post, f, indent=2)
                    except Exception as e:
                        import sys
                        print(f"Warning: Failed to write post-step telemetry JSON at step {step_idx}: {e}", file=sys.stderr)

    with torch.no_grad():
        bragg_after_t, chi_sq_after_t, _ = _forward_once(use_mapping_zero_geometry=False)

    # Per-ROI CC vs mapping bragg_zero_iter.
    bragg_before = bragg_before_t.cpu().numpy().astype(np.float32)
    bragg_after = bragg_after_t.cpu().numpy().astype(np.float32)
    bragg_mapping = np.asarray(context.bragg_zero_iter, dtype=np.float32)

    inputs_np = context.inputs
    roi_rows: List[Dict[str, object]] = []
    corr_before: List[float] = []
    corr_after: List[float] = []

    for roi_index, (pid, bbox) in enumerate(inputs_np.panel_slices):
        x0, x1, y0, y1 = map(int, bbox)

        mapping_roi = bragg_mapping[pid, y0:y1, x0:x1]
        before_roi = bragg_before[pid, y0:y1, x0:x1]
        after_roi = bragg_after[pid, y0:y1, x0:x1]
        mask_roi = inputs_np.loss_mask[pid, y0:y1, x0:x1]

        metrics_before: ParityMetrics = compute_parity_metrics(
            before_roi, mapping_roi, loss_mask=mask_roi
        )
        metrics_after: ParityMetrics = compute_parity_metrics(
            after_roi, mapping_roi, loss_mask=mask_roi
        )

        cb = float(metrics_before.correlation)
        ca = float(metrics_after.correlation)

        if not np.isnan(cb):
            corr_before.append(cb)
        if not np.isnan(ca):
            corr_after.append(ca)

        roi_rows.append(
            {
                "roi_index": int(roi_index),
                "panel_id": int(pid),
                "bbox": [int(x0), int(x1), int(y0), int(y1)],
                "corr_before": cb,
                "corr_after": ca,
                "corr_delta": ca - cb if not np.isnan(cb) and not np.isnan(ca) else float("nan"),
            }
        )

    # Zero-point alignment metrics vs mapping Bragg at initial parameters.
    diff0 = bragg_before.astype(np.float64) - bragg_mapping.astype(np.float64)
    max_abs_diff0 = float(np.max(np.abs(diff0)))
    mean_abs_diff0 = float(np.mean(np.abs(diff0)))

    zero_point_summary: Dict[str, object] = {
        "max_abs_diff": max_abs_diff0,
        "mean_abs_diff": mean_abs_diff0,
        "n_roi": len(roi_rows),
        "corr_median_vs_mapping": median(corr_before) if corr_before else float("nan"),
    }

    payload: Dict[str, object] = {
        "optimizer": {
            "type": "Adam",
            "learning_rate": float(lr),
            "steps": int(max(n_steps, 0)),
            "train_scale": bool(train_scale),
            "train_cell": bool(train_cell),
            "train_orientation": bool(train_orientation),
        },
        "parameters": {
            "initial": {
                "log_scale": float(initial_log_scale),
                "log_cell_a_delta": 0.0,
                "log_cell_b_delta": 0.0,
                "log_cell_c_delta": 0.0,
                "angle_alpha_raw": 0.0,
                "angle_beta_raw": 0.0,
                "angle_gamma_raw": 0.0,
                "orientation_vec": [0.0, 0.0, 0.0],
            },
            "final": {
                "log_scale": float(log_scale.detach().cpu().item()),
                "log_cell_a_delta": float(log_cell_a_delta.detach().cpu().item()),
                "log_cell_b_delta": float(log_cell_b_delta.detach().cpu().item()),
                "log_cell_c_delta": float(log_cell_c_delta.detach().cpu().item()),
                "angle_alpha_raw": float(angle_alpha_raw.detach().cpu().item()),
                "angle_beta_raw": float(angle_beta_raw.detach().cpu().item()),
                "angle_gamma_raw": float(angle_gamma_raw.detach().cpu().item()),
                "orientation_vec": [
                    float(v) for v in orientation_vec.detach().cpu().tolist()
                ],
            },
        },
        "chi_squared": {
            "before": float(chi_sq_before_t.item()),
            "after": float(chi_sq_after_t.item()),
        },
        "loss_trace": loss_trace,
        "zero_point": zero_point_summary,
        "cc_summary": {
            "median_before": median(corr_before) if corr_before else float("nan"),
            "median_after": median(corr_after) if corr_after else float("nan"),
        },
        "per_roi": roi_rows,
    }

    return payload


def run_single_step_adam(
    dataload: DataLoad,
    context,
    *,
    device_str: str,
    lr: float,
    out_dir: Path,
) -> Dict[str, object]:
    """Phase 4 — Single-step Adam experiment on full Stage A.

    Parameters:
        dataload: DataLoad instance
        context: Mapping stage A context
        device_str: Device string
        lr: Learning rate for Adam
        out_dir: Output directory for single_step_adam.json

    Returns:
        Dict: Payload from stage_a_adam_core

    Notes:
        - Runs 1 step of Adam optimizer
        - Trains all parameters: scale, cell, orientation
        - Writes single_step_adam.json to out_dir
    """
    payload = stage_a_adam_core(
        dataload,
        context,
        device_str=device_str,
        n_steps=1,
        lr=lr,
        train_scale=True,
        train_cell=True,
        train_orientation=True,
    )

    (out_dir / "single_step_adam.json").write_text(json.dumps(payload, indent=2))
    return payload


def run_zero_point_check(
    dataload: DataLoad,
    context,
    *,
    device_str: str,
    out_dir: Path,
) -> Dict[str, object]:
    """Phase D — Zero-point alignment probe (no-op Stage A).

    Runs `stage_a_adam_core` with `n_steps=0` and all geometry deltas frozen,
    then compares the initial Stage-A forward model against `bragg_zero_iter`.
    Emits `zero_point_check.json` with max/mean |Δ| and per-ROI CC vs mapping,
    plus a `zero_point_ok` flag used to gate geometry experiments.

    Parameters:
        dataload: DataLoad instance
        context: Mapping stage A context
        device_str: Device string
        out_dir: Output directory for zero_point_check.json

    Returns:
        Dict: Payload with zero_point_ok flag, tolerances, chi-squared comparison

    Notes:
        - Runs stage_a_adam_core with n_steps=0, no training
        - Compares Stage A zero-point vs mapping Bragg
        - Tolerances: max_abs < 200, mean_abs < 1e-3, chi2_rel < 1e-3
        - zero_point_ok=True if all tolerances pass
        - Writes zero_point_check.json to out_dir
    """
    payload = stage_a_adam_core(
        dataload,
        context,
        device_str=device_str,
        n_steps=0,
        lr=0.0,
        train_scale=False,
        train_cell=False,
        train_orientation=False,
    )

    zero_point = payload.get("zero_point", {}) or {}
    per_roi = payload.get("per_roi", []) or []

    max_abs = float(zero_point.get("max_abs_diff", float("inf")))
    mean_abs = float(zero_point.get("mean_abs_diff", float("inf")))
    # Tolerances on per-pixel Bragg differences. These are calibrated to the
    # observed DB-AT-024 mapping vs Stage-A no-op deltas (order 1e-5 mean and
    # O(1e2) max for canonical assets).
    max_abs_tol = 200.0
    mean_abs_tol = 1e-3

    # Chi-squared equality gate at zero parameters.
    chi_block = payload.get("chi_squared", {}) or {}
    chi2_stage_a = float(chi_block.get("before", float("nan")))
    chi2_mapping = float(context.diagnostics.get("chi_squared", float("nan")))
    if np.isfinite(chi2_mapping) and chi2_mapping != 0.0 and np.isfinite(chi2_stage_a):
        chi2_abs_diff = chi2_stage_a - chi2_mapping
        chi2_rel_diff = chi2_abs_diff / chi2_mapping
    else:
        chi2_abs_diff = float("nan")
        chi2_rel_diff = float("nan")

    # Chi-squared relative tolerance at zero parameters.
    chi2_rel_tol = 1e-3

    zero_point_ok = bool(
        np.isfinite(max_abs)
        and max_abs <= max_abs_tol
        and np.isfinite(mean_abs)
        and mean_abs <= mean_abs_tol
        and np.isfinite(chi2_rel_diff)
        and abs(chi2_rel_diff) <= chi2_rel_tol
    )

    result: Dict[str, object] = {
        "summary": zero_point,
        "per_roi": per_roi,
        "zero_point_ok": zero_point_ok,
        "max_abs_diff_tolerance": max_abs_tol,
        "chi2": {
            "mapping": chi2_mapping,
            "stage_a": chi2_stage_a,
            "abs_diff": chi2_abs_diff,
            "rel_diff": chi2_rel_diff,
        },
        "chi2_rel_diff_tolerance": chi2_rel_tol,
        "mean_abs_diff_tolerance": mean_abs_tol,
    }

    (out_dir / "zero_point_check.json").write_text(json.dumps(result, indent=2))
    return result


def run_engine_zero_point_probe(
    dataload: DataLoad,
    *,
    device_str: str = "cpu",
    sigma_source: str = "metadata",
) -> Dict[str, object]:
    """Engine-delegation zero-point probe (DB-AT-027).

    Reuses `build_mapping_stage_a_context` to construct mapping baseline,
    then runs `run_nanobrag_refinement` with Stage A only, `max_iter=0`,
    `use_engine_delegation=True`, and reconstructs `bragg_stagea_zero` via
    `_build_final_bragg_from_stage_a_telemetry` with initial params copied
    to final slots. Computes mean/max |Δ| + chi² stats, and returns them
    for comparison against DB-AT-027 tolerances.

    Parameters:
        dataload: DataLoad instance (canonical refGeom assets)
        device_str: Device string ("cpu" recommended for determinism)
        sigma_source: Sigma readout provenance ("metadata" or other)

    Returns:
        Dict with:
            - mean_abs_diff: Mean |bragg_stagea_zero - bragg_mapping|
            - max_abs_diff: Max |bragg_stagea_zero - bragg_mapping|
            - chi2_stagea: Stage A chi² on mapping stack
            - chi2_mapping: Mapping chi² from context
            - chi2_rel_diff: Relative chi² difference
            - variance_floor_masked_pixels: Pixel count used in chi² normalization
            - roi_cc_samples: List of per-ROI correlation coefficients vs data
            - db_at_027_pass: Boolean flag (True if all tolerances met)

    Notes:
        - Tolerances (from docs/spec-db-conformance.md:201-239):
          - mean_abs_diff <= 1e-3
          - max_abs_diff <= 2.0e2
          - |chi2_rel_diff| <= 1e-3
        - Uses canonical variance-weighted loss from PHYSICS-LOSS-001
        - Preserves mapping calibration payload entirely (spot_scale_override,
          flux, exposure, N_cells, sigma_floor)
        - Engine delegation ensures consistency with production refinement path
    """
    # Lazy import torch (ARCH-ENGINE-002)
    import torch
    from dbex.nanobrag_bridge import build_structure_factor_grid
    from dbex.nanobrag_refinement import (
        RefinementConfig,
        _build_final_bragg_from_stage_a_telemetry,
        run_nanobrag_refinement,
    )
    from dbex.vis.mapping import build_mapping_stage_a_context

    # Build mapping context (DB-AT-024 baseline)
    context = build_mapping_stage_a_context(
        dataload,
        default_sigma_readout=3.0,
        device=device_str,
    )

    # Extract HKL indices/amplitudes from context
    hkl_indices = context.hkl_indices
    hkl_amplitudes = context.hkl_amplitudes
    calibration = context.calibration or {}
    spot_scale_override = context.spot_scale_override
    if spot_scale_override is None and calibration is not None:
        spot_scale_override = calibration.get("spot_scale_override")
    log_scale_baseline = None
    if spot_scale_override is not None:
        try:
            log_scale_baseline = float(np.log(np.sqrt(spot_scale_override)))
        except (TypeError, ValueError):
            log_scale_baseline = None

    # Build dense HKL grid with same halo as mapping
    hkl_has_halo = bool(context.diagnostics.get("hkl_stats", {}).get("has_halo", False))
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device_str,
        halo=hkl_has_halo,  # Match mapping behavior
    )

    # Build RefinementConfig for zero-iteration engine run with calibration payload
    # (TOOLING-VIS-001 Phase D.C, DB-AT-027)
    config = RefinementConfig(
        device=device_str,
        max_iter=0,  # Zero iterations (no LBFGS updates)
        enable_stage_b=False,
        enable_stage_c=False,
        sigma_readout_provenance=sigma_source,
        calibration_metadata=context.calibration,  # Forward mapping calibration into engine
    )
    config.log_scale_baseline = log_scale_baseline

    # Run engine with delegation to capture telemetry
    _, telemetry = run_nanobrag_refinement(
        inputs=context.inputs,
        detector=dataload.detector,
        beam=dataload.beam,
        crystal=dataload.crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        use_engine_delegation=True,
    )

    # Extract Stage A telemetry (keyed as "A" for backward compatibility)
    telemetry_a = telemetry.get("A")
    if telemetry_a is None:
        raise RuntimeError(f"Engine delegation failed to produce Stage A telemetry. Keys: {list(telemetry.keys())}")

    # Deep-copy telemetry and force initial → final to ensure zero-point reconstruction
    import copy
    telemetry_a_zero = copy.deepcopy(telemetry_a)
    param_deltas = telemetry_a_zero.param_deltas
    for key in param_deltas:
        if "initial" in param_deltas[key] and "final" in param_deltas[key]:
            param_deltas[key]["final"] = param_deltas[key]["initial"]

    # Reconstruct bragg_stagea_zero via canonical helper
    device = torch.device(device_str)
    dtype = torch.float32
    bragg_stagea_zero = _build_final_bragg_from_stage_a_telemetry(
        telemetry_a=telemetry_a_zero,
        detector=dataload.detector,
        beam=dataload.beam,
        crystal=dataload.crystal,
        inputs=context.inputs,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        device=device,
        dtype=dtype,
    )

    # Compute forward-model differences
    bragg_mapping = context.bragg_zero_iter
    diff = bragg_stagea_zero - bragg_mapping
    max_abs_diff = float(np.abs(diff).max())
    mean_abs_diff = float(np.abs(diff).mean())

    # Compute Stage A chi² on mapping stack using canonical variance-weighted loss
    from dbex.physics.loss import _compute_variance_weighted_loss

    sigma_floor_sq = float(context.sigma_floor_value ** 2)
    # Convert numpy arrays to torch tensors for variance-weighted loss
    bragg_mapping_t = torch.from_numpy(bragg_mapping).to(device=device, dtype=dtype)
    target_t = torch.from_numpy(context.inputs.target).to(device=device, dtype=dtype)
    loss_mask_t = torch.from_numpy(context.inputs.loss_mask).to(device=device)
    sigma_readout_t = torch.from_numpy(context.inputs.sigma_readout).to(device=device, dtype=dtype)
    sigma_floor_sq_t = torch.tensor(sigma_floor_sq, device=device, dtype=dtype)

    chi2_stagea_at_mapping, _, _, _ = _compute_variance_weighted_loss(
        bragg_mapping_t,  # Use mapping stack for Stage A chi² (DB-AT-027 contract)
        target_t,
        loss_mask_t,
        sigma_readout_t,
        sigma_floor_sq_t,
    )
    chi2_stagea_at_mapping = chi2_stagea_at_mapping.item()  # Convert to scalar

    chi2_mapping = float(context.diagnostics.get("chi_squared", float("nan")))
    if np.isfinite(chi2_mapping) and chi2_mapping != 0.0 and np.isfinite(chi2_stagea_at_mapping):
        chi2_rel_diff = (chi2_stagea_at_mapping - chi2_mapping) / chi2_mapping
    else:
        chi2_rel_diff = float("nan")

    # Extract variance floor masked pixels
    variance_floor_masked_pixels = int(context.diagnostics.get("variance_floor_masked_pixels", 0))

    # Compute per-ROI correlation coefficients vs data
    roi_cc_samples = []
    for pid, (x0, x1, y0, y1) in context.inputs.panel_slices:
        data_roi = context.inputs.target[pid, y0:y1, x0:x1]
        model_roi = bragg_stagea_zero[pid, y0:y1, x0:x1]
        mask_roi = context.inputs.loss_mask[pid, y0:y1, x0:x1]
        if mask_roi.sum() > 10:
            data_masked = data_roi[mask_roi]
            model_masked = model_roi[mask_roi]
            cc = float(np.corrcoef(data_masked.ravel(), model_masked.ravel())[0, 1])
            if np.isfinite(cc):
                roi_cc_samples.append(cc)

    # DB-AT-027 tolerances (docs/spec-db-conformance.md:201-239)
    mean_abs_tol = 1e-3
    max_abs_tol = 2.0e2
    chi2_rel_tol = 1e-3

    db_at_027_pass = bool(
        mean_abs_diff <= mean_abs_tol
        and max_abs_diff <= max_abs_tol
        and np.isfinite(chi2_rel_diff)
        and abs(chi2_rel_diff) <= chi2_rel_tol
    )

    return {
        "mean_abs_diff": mean_abs_diff,
        "max_abs_diff": max_abs_diff,
        "chi2_stagea": float(chi2_stagea_at_mapping),
        "chi2_mapping": chi2_mapping,
        "chi2_rel_diff": float(chi2_rel_diff),
        "variance_floor_masked_pixels": variance_floor_masked_pixels,
        "roi_cc_samples": roi_cc_samples,
        "db_at_027_pass": db_at_027_pass,
        "calibration": {
            "spot_scale_override": spot_scale_override,
            "log_scale_baseline": log_scale_baseline,
            "beam_flux": calibration.get("beam_flux") if calibration else None,
            "beam_exposure": calibration.get("beam_exposure") if calibration else None,
            "beamsize_mm": calibration.get("beamsize_mm") if calibration else None,
            "N_cells": calibration.get("N_cells") if calibration else None,
        },
        "tolerances": {
            "mean_abs_diff": mean_abs_tol,
            "max_abs_diff": max_abs_tol,
            "chi2_rel_diff": chi2_rel_tol,
        },
    }


def run_blockwise_dof_experiments(
    dataload: DataLoad,
    context,
    *,
    device_str: str,
    n_steps: int,
    lr: float,
    out_dir: Path,
    dof_variants: list[str] | None = None,
    use_u_matrix: bool = False,
    use_lbfgs: bool = False,
    telemetry_output_dir: str | None = None,
) -> Dict[str, object]:
    """Phase 5 — Block-wise DoF isolation experiments.

    Parameters:
        dataload: DataLoad instance
        context: Mapping stage A context
        device_str: Device string
        n_steps: Number of optimizer steps per variant
        lr: Learning rate
        out_dir: Output directory for block_dof_results.json
        dof_variants: List of variant names to run (None = all)
        use_u_matrix: If True, use quaternion U-matrix parameterization for
            orientation instead of cell+misset (TORCH-GEOMETRY-PARITY-002)
        use_lbfgs: If True, use LBFGS optimizer instead of Adam
        telemetry_output_dir: If provided, emit per-step telemetry JSON files
            for convergence diagnosis (TORCH-GEOMETRY-CONVERGENCE-001 Phase A1)

    Returns:
        Dict: Payload with variants (keys: A_scale_only, B_scale_plus_cell,
              C_scale_plus_orientation, D_full), each with optimizer config,
              chi_squared, cc_summary

    Notes:
        - Variant A: scale only
        - Variant B: scale + cell
        - Variant C: scale + orientation
        - Variant D: full (scale + cell + orientation)
        - Writes block_dof_results.json (or block_dof_results_u_matrix.json for U-matrix mode)
    """
    all_variants = {
        "A_scale_only": dict(train_scale=True, train_cell=False, train_orientation=False),
        "B_scale_plus_cell": dict(train_scale=True, train_cell=True, train_orientation=False),
        "C_scale_plus_orientation": dict(train_scale=True, train_cell=False, train_orientation=True),
        "D_full": dict(train_scale=True, train_cell=True, train_orientation=True),
    }

    # Filter variants if requested
    if dof_variants is not None:
        variants = {k: v for k, v in all_variants.items() if k in dof_variants}
    else:
        variants = all_variants

    results: Dict[str, object] = {}
    for name, cfg in variants.items():
        payload = stage_a_adam_core(
            dataload,
            context,
            device_str=device_str,
            n_steps=max(n_steps, 0),
            lr=lr,
            train_scale=cfg["train_scale"],
            train_cell=cfg["train_cell"],
            train_orientation=cfg["train_orientation"],
            use_u_matrix=use_u_matrix,
            use_lbfgs=use_lbfgs,
            telemetry_output_dir=telemetry_output_dir,
        )
        chi = payload.get("chi_squared", {})
        cc = payload.get("cc_summary", {})
        results[name] = {
            "optimizer": payload.get("optimizer", {}),
            "chi_squared": chi,
            "cc_summary": cc,
        }

    block_payload: Dict[str, object] = {"variants": results}
    # TORCH-GEOMETRY-PARITY-002: Use different filename for U-matrix mode
    output_filename = "block_dof_results_u_matrix.json" if use_u_matrix else "block_dof_results.json"
    (out_dir / output_filename).write_text(json.dumps(block_payload, indent=2))
    return block_payload


def run_gradient_probe(
    dataload: DataLoad,
    context,
    *,
    device_str: str,
    out_dir: Path,
) -> Dict[str, object]:
    """
    Phase B1 (TORCH-REFINE-002E): Gradient probe at mapping zero point.

    Evaluates chi-squared and per-DoF gradients for:
    - log_scale
    - cell_logs (a, b, c)
    - angle_raws (alpha, beta, gamma)
    - orientation_vec (3-element tangent space)

    at the mapping zero point (all delta parameters = 0).

    Also computes gradients using a trusted ROI subset (mapping CC >= 0.95)
    to isolate potential outlier effects.

    Artifacts:
    - gradient_probe.json: JSON with global and trusted-ROI gradient evaluations

    Parameters:
        dataload: DataLoad instance
        context: Mapping stage A context
        device_str: Device string
        out_dir: Output directory for gradient_probe.json

    Returns:
        Dict: Payload with mode, zero_point (chi-squared, gradients), trusted_roi_subset

    Notes:
        - Initializes all DoF parameters at zero (mapping zero point)
        - Computes chi-squared via stage_a_forward
        - Computes gradients via backward() on chi_squared
        - Gradient magnitudes: L2 norm for vector parameters, abs for scalars
        - Trusted ROI subset: Not implemented (warning emitted)
        - Writes gradient_probe.json to out_dir
    """
    print("[gradient_probe] Initializing Stage-A components at mapping zero point...")
    components = build_stage_a_components(dataload, context, device_str=device_str)
    torch = components.torch
    device = components.device
    dtype = components.dtype

    # PHYSICS-LOSS-002: sigma_floor_value from calibration or default 1.0 photon
    calibration = context.calibration if context.calibration else {}
    sigma_floor_value = calibration.get("sigma_floor_value", 1.0)
    sigma_floor_sq_tensor = torch.tensor(
        sigma_floor_value ** 2, device=device, dtype=dtype
    )

    # Initialize DoF parameters at zero (mapping zero point)
    log_scale = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    log_cell_a_delta = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    log_cell_b_delta = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    log_cell_c_delta = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    angle_alpha_raw = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    angle_beta_raw = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    angle_gamma_raw = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    orientation_vec = torch.zeros(3, device=device, dtype=dtype, requires_grad=True)

    # Global gradient evaluation
    print("[gradient_probe] Computing global gradients...")
    bragg_tensor, chi_squared_global_from_forward, _ = stage_a_forward(
        dataload,
        context,
        components,
        log_scale=log_scale,
        log_cell_a_delta=log_cell_a_delta,
        log_cell_b_delta=log_cell_b_delta,
        log_cell_c_delta=log_cell_c_delta,
        angle_alpha_raw=angle_alpha_raw,
        angle_beta_raw=angle_beta_raw,
        angle_gamma_raw=angle_gamma_raw,
        orientation_vec=orientation_vec,
        q_params=None,
        sigma_floor_sq_tensor=sigma_floor_sq_tensor,
        use_mapping_zero_geometry=False,  # Use explicit parameterization even at zero
    )

    # Use the chi_squared from forward (already computed), but also compute MSE for telemetry
    chi_squared_global = chi_squared_global_from_forward
    diff = bragg_tensor - components.target_t
    squared_error = diff ** 2
    mask_bool = components.mask_t
    masked_squared_error = torch.where(mask_bool, squared_error, torch.zeros_like(squared_error))
    masked_pixels_global = int(mask_bool.sum().item())
    if masked_pixels_global > 0:
        masked_mse_global = masked_squared_error.sum() / masked_pixels_global
    else:
        masked_mse_global = masked_squared_error.sum()

    # Compute clamped pixels count
    variance_raw = bragg_tensor.detach() + components.sigma_t ** 2
    variance = torch.maximum(variance_raw, sigma_floor_sq_tensor)
    clamped_pixels_global = int(((variance_raw < sigma_floor_sq_tensor) & mask_bool).sum().item())

    chi_squared_global.backward()

    global_gradients = {
        "log_scale": {
            "value": float(log_scale.grad.item()) if log_scale.grad is not None else 0.0,
            "magnitude": float(torch.abs(log_scale.grad).item()) if log_scale.grad is not None else 0.0,
        },
        "cell_logs": {
            "value": [
                float(log_cell_a_delta.grad.item()) if log_cell_a_delta.grad is not None else 0.0,
                float(log_cell_b_delta.grad.item()) if log_cell_b_delta.grad is not None else 0.0,
                float(log_cell_c_delta.grad.item()) if log_cell_c_delta.grad is not None else 0.0,
            ],
            "magnitude": float(
                torch.sqrt(
                    (log_cell_a_delta.grad ** 2 if log_cell_a_delta.grad is not None else 0.0)
                    + (log_cell_b_delta.grad ** 2 if log_cell_b_delta.grad is not None else 0.0)
                    + (log_cell_c_delta.grad ** 2 if log_cell_c_delta.grad is not None else 0.0)
                ).item()
            ),
            "element_wise_max_abs": float(
                max(
                    abs(log_cell_a_delta.grad.item()) if log_cell_a_delta.grad is not None else 0.0,
                    abs(log_cell_b_delta.grad.item()) if log_cell_b_delta.grad is not None else 0.0,
                    abs(log_cell_c_delta.grad.item()) if log_cell_c_delta.grad is not None else 0.0,
                )
            ),
        },
        "angle_raws": {
            "value": [
                float(angle_alpha_raw.grad.item()) if angle_alpha_raw.grad is not None else 0.0,
                float(angle_beta_raw.grad.item()) if angle_beta_raw.grad is not None else 0.0,
                float(angle_gamma_raw.grad.item()) if angle_gamma_raw.grad is not None else 0.0,
            ],
            "magnitude": float(
                torch.sqrt(
                    (angle_alpha_raw.grad ** 2 if angle_alpha_raw.grad is not None else 0.0)
                    + (angle_beta_raw.grad ** 2 if angle_beta_raw.grad is not None else 0.0)
                    + (angle_gamma_raw.grad ** 2 if angle_gamma_raw.grad is not None else 0.0)
                ).item()
            ),
            "element_wise_max_abs": float(
                max(
                    abs(angle_alpha_raw.grad.item()) if angle_alpha_raw.grad is not None else 0.0,
                    abs(angle_beta_raw.grad.item()) if angle_beta_raw.grad is not None else 0.0,
                    abs(angle_gamma_raw.grad.item()) if angle_gamma_raw.grad is not None else 0.0,
                )
            ),
        },
        "orientation_vec": {
            "value": [
                float(orientation_vec.grad[i].item()) if orientation_vec.grad is not None else 0.0
                for i in range(3)
            ],
            "magnitude": float(
                torch.norm(orientation_vec.grad).item() if orientation_vec.grad is not None else 0.0
            ),
            "element_wise_max_abs": float(
                torch.max(torch.abs(orientation_vec.grad)).item()
                if orientation_vec.grad is not None
                else 0.0
            ),
        },
    }

    zero_point_global = {
        "chi_squared": float(chi_squared_global.item()),
        "masked_mse": float(masked_mse_global.item()),
        "masked_pixels": masked_pixels_global,
        "clamped_pixels": clamped_pixels_global,
        "dof_gradients": global_gradients,
    }

    # Trusted ROI subset gradient evaluation
    # Use mapping CC from context if available
    trusted_roi_result = None
    if hasattr(context, "roi_cc_mapping") and context.roi_cc_mapping is not None:
        roi_cc_mapping = context.roi_cc_mapping
        trusted_threshold = 0.95
        trusted_indices = [i for i, cc in enumerate(roi_cc_mapping) if cc >= trusted_threshold]

        if len(trusted_indices) > 0:
            print(f"[gradient_probe] Computing trusted ROI subset gradients (N={len(trusted_indices)}, CC>={trusted_threshold})...")

            # Zero out previous gradients
            if log_scale.grad is not None:
                log_scale.grad.zero_()
            if log_cell_a_delta.grad is not None:
                log_cell_a_delta.grad.zero_()
            if log_cell_b_delta.grad is not None:
                log_cell_b_delta.grad.zero_()
            if log_cell_c_delta.grad is not None:
                log_cell_c_delta.grad.zero_()
            if angle_alpha_raw.grad is not None:
                angle_alpha_raw.grad.zero_()
            if angle_beta_raw.grad is not None:
                angle_beta_raw.grad.zero_()
            if angle_gamma_raw.grad is not None:
                angle_gamma_raw.grad.zero_()
            if orientation_vec.grad is not None:
                orientation_vec.grad.zero_()

            # Build a trusted ROI mask
            # For simplicity, assume we can identify which pixels belong to trusted ROIs
            # via the context's ROI metadata. If not available, skip this section.
            # Since we don't have per-pixel ROI ID readily available, we'll skip the
            # trusted ROI computation and log a warning.
            print("[gradient_probe] Warning: Per-pixel ROI ID mapping not available; skipping trusted ROI subset.")
        else:
            print(f"[gradient_probe] Warning: No ROIs with mapping CC >= {trusted_threshold}; skipping trusted subset.")
    else:
        print("[gradient_probe] Warning: roi_cc_mapping not available in context; skipping trusted ROI subset.")

    payload = {
        "mode": "gradient_probe",
        "zero_point": zero_point_global,
        "trusted_roi_subset": trusted_roi_result,
    }

    (out_dir / "gradient_probe.json").write_text(json.dumps(payload, indent=2))
    print(f"[gradient_probe] Wrote gradient_probe.json to {out_dir}/")
    print(f"[gradient_probe] Chi-squared at zero point: {zero_point_global['chi_squared']:.6e}")
    print(f"[gradient_probe] Gradient magnitudes:")
    print(f"  log_scale:       {global_gradients['log_scale']['magnitude']:.6e}")
    print(f"  cell_logs:       {global_gradients['cell_logs']['magnitude']:.6e}")
    print(f"  angle_raws:      {global_gradients['angle_raws']['magnitude']:.6e}")
    print(f"  orientation_vec: {global_gradients['orientation_vec']['magnitude']:.6e}")

    return payload
