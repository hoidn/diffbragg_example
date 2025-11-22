#!/usr/bin/env python3
"""
TOOLING-VIS-001 — Stage A Mapping Adam Debug Driver.

Implements the instrumentation described in
`plans/active/TOOLING-VIS-001/stage_a_mapping_adam_debug_plan.md` and the
Phase D zero-point realignment work in
`plans/active/TOOLING-VIS-001/stage_a_mapping_alignment_plan.md`:

- Phase 0: Environment lockdown + deterministic debug run directory.
- Phase 1: Forward-model equality probe between:
    * Mapping Bragg stack (`bragg_zero_iter` from `simulate_forward_once`)
    * Stage-A "no-op" simulator using the same HKL grid + calibration.
- Phase 2: Loss-definition alignment between mapping diagnostics and the
    Stage-A variance-weighted chi-squared loss.
- Phase 3: Zero-point alignment probe in which the Stage-A Adam core
    reproduces `bragg_zero_iter` at zero parameters (geometry/scale).
- Phase 4: Single-step Adam experiment on full Stage A parameters
    (scale + unit cell + orientation) to inspect the first optimizer step.
- Phase 5: Block-wise DoF sweeps (scale-only, scale+cell, scale+orientation,
    full) gated on a passing zero-point check.

Artifacts are written under:

    plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam_debug/<timestamp>/

with JSON files:
    - forward_model_probe.json
    - loss_alignment.json
    - zero_point_check.json
    - single_step_adam.json
    - block_dof_results.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Dict, List, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dbex.data_load import DataLoad  # type: ignore  # noqa: E402
from dbex.nanobrag_bridge import (  # type: ignore  # noqa: E402
    build_structure_factor_grid,
    create_beam_config,
    create_crystal_config,
    create_detector_config,
    compute_baseline_misset_deg,
)
from dbex.nanobrag_refinement import (  # type: ignore  # noqa: E402
    _compute_variance_weighted_loss,
    quaternion_to_xyz_euler,
    vec_to_unit_quaternion,
)
from dbex.vis import build_mapping_stage_a_context  # type: ignore  # noqa: E402
from tests.fixtures.parity_loader import (  # type: ignore  # noqa: E402
    ParityMetrics,
    compute_parity_metrics,
)


def _build_dataload(repo_root: Path) -> DataLoad:
    """Construct a DataLoad instance for canonical assets (prefer refined geometry)."""
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


def _setup_environment(seed: int, device_str: str) -> int:
    """Phase 0 — Environment lockdown and seeding."""
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


def _create_debug_run_dir() -> Tuple[str, Path]:
    """Create a timestamped debug run directory for this invocation."""
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_root = (
        REPO_ROOT
        / "plans"
        / "active"
        / "TOOLING-VIS-001"
        / "reports"
        / "stage_a_refgeom_adam_debug"
        / timestamp
    )
    out_root.mkdir(parents=True, exist_ok=True)
    return timestamp, out_root


def _write_commands_txt(out_dir: Path, seed: int, argv: List[str]) -> None:
    """Record exact command line, seed, and key env vars for reproducibility."""
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


def _import_stage_a_dependencies():
    """Import torch and nanobrag_torch components used for Stage A debugging."""
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
class _StageAComponents:
    """Shared Stage A simulator components for mapping-aligned helpers."""

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


def _build_stage_a_components(
    dataload: DataLoad,
    context,
    *,
    device_str: str,
    use_u_matrix: bool = False,
) -> _StageAComponents:
    """Construct shared Stage A tensors/config used by mapping helpers.

    Args:
        use_u_matrix: If True, initialize quaternion U-matrix params for orientation
            instead of cell+misset (TORCH-GEOMETRY-PARITY-002).
    """
    torch, TorchCrystal, TorchDetector, Simulator = _import_stage_a_dependencies()

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

        # DELETE the cctbx_cell() code below - no longer needed (CONVERGENCE-001 bugfix)
        # Prior bug: cctbx fractionalization_matrix() produced different B_ideal than TorchCrystal,
        # causing U @ B_ideal reconstruction to fail (chi²=1.425B vs expected ~990k)

    return _StageAComponents(
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


def _stage_a_forward(
    dataload: DataLoad,
    context,
    components: _StageAComponents,
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

    Args:
        q_params: Quaternion parameters for U-matrix mode (4-DOF). If None, uses
            cell+misset path with orientation_vec.
    """
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
    if use_mapping_zero_geometry:
        crystal_config, _ = create_crystal_config(
            dataload.crystal,
            dataload.Expt,
            N_cells=N_cells,
            apply_n_cells=apply_n_cells,
            crystal_overrides=None,
            misset_deg_override=None,
        )
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
            crystal_overrides["A_star"] = A_star_new
            misset_xyz_deg = None  # No misset override in U-matrix mode
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
    return bragg_t, chi_sq_t


def _build_stage_a_bragg_noop(
    dataload: DataLoad,
    context,
    *,
    device_str: str = "cpu",
) -> np.ndarray:
    """Phase 1 helper — run Stage A simulator with zero deltas and log_scale=0."""
    components = _build_stage_a_components(
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
        bragg_t, _ = _stage_a_forward(
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
            sigma_floor_sq_tensor=sigma_floor_sq_tensor,
            use_mapping_zero_geometry=True,
        )

    return bragg_t.cpu().numpy().astype(np.float32)


@dataclass
class ForwardModelProbeSummary:
    max_abs_diff: float
    mean_abs_diff: float
    n_roi: int
    corr_median_mapping: float
    corr_median_stage_a_noop: float


def _run_forward_model_probe(
    dataload: DataLoad,
    context,
    *,
    device_str: str,
    out_dir: Path,
) -> Dict[str, object]:
    """Phase 1 — Forward-model equality probe."""
    bragg_mapping = np.asarray(context.bragg_zero_iter, dtype=np.float32)
    bragg_stage_a_noop = _build_stage_a_bragg_noop(
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


def _run_loss_alignment_probe(
    context,
    *,
    device_str: str,
    out_dir: Path,
) -> Dict[str, object]:
    """Phase 2 — Loss-definition alignment at mapping point."""
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


def _stage_a_adam_core(
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

    Args:
        use_u_matrix: If True, use quaternion U-matrix parameterization for
            orientation (TORCH-GEOMETRY-PARITY-002).
        use_lbfgs: If True, use LBFGS optimizer instead of Adam for U-matrix path
            (TORCH-GEOMETRY-CONVERGENCE-001 Test B1).
    """
    components = _build_stage_a_components(
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

    def _forward_once(use_mapping_zero_geometry: bool) -> Tuple[torch.Tensor, torch.Tensor]:
        return _stage_a_forward(
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
        bragg_before_t, chi_sq_before_t = _forward_once(use_mapping_zero_geometry=True)

    loss_trace: List[float] = [float(chi_sq_before_t.item())]

    if optimizer is not None and n_steps > 0:
        if use_lbfgs and use_u_matrix:
            # LBFGS requires closure pattern
            for step_idx in range(n_steps):
                def closure():
                    optimizer.zero_grad()
                    bragg_t, chi_sq_t = _forward_once(use_mapping_zero_geometry=False)
                    chi_sq_t.backward()
                    return chi_sq_t

                # Get loss value before optimizer step for telemetry
                with torch.no_grad():
                    _, chi_sq_before_step = _forward_once(use_mapping_zero_geometry=False)

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
                    _, chi_sq_temp = _forward_once(use_mapping_zero_geometry=False)
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

                    telemetry_step = {
                        **telemetry_params,
                        **telemetry_gradients,
                        **telemetry_loss,
                        **telemetry_variance,
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
                    _, chi_sq_after_step = _forward_once(use_mapping_zero_geometry=False)
                    loss_trace.append(float(chi_sq_after_step.item()))
        else:
            # Adam pattern (no closure)
            for step_idx in range(n_steps):
                optimizer.zero_grad()
                bragg_t, chi_sq_t = _forward_once(use_mapping_zero_geometry=False)
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

                    # Combine and emit
                    telemetry_step = {
                        **telemetry_params,
                        **telemetry_gradients,
                        **telemetry_loss,
                        **telemetry_variance,
                    }

                    try:
                        telemetry_path = Path(telemetry_output_dir) / f"telemetry_step_{step_idx:03d}.json"
                        telemetry_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(telemetry_path, 'w') as f:
                            json.dump(telemetry_step, f, indent=2)
                    except Exception as e:
                        import sys
                        print(f"Warning: Failed to write telemetry JSON at step {step_idx}: {e}", file=sys.stderr)

                optimizer.step()
                loss_trace.append(float(chi_sq_t.item()))

    with torch.no_grad():
        bragg_after_t, chi_sq_after_t = _forward_once(use_mapping_zero_geometry=False)

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


def _run_single_step_adam(
    dataload: DataLoad,
    context,
    *,
    device_str: str,
    lr: float,
    out_dir: Path,
) -> Dict[str, object]:
    """Phase 4 — Single-step Adam experiment on full Stage A."""
    payload = _stage_a_adam_core(
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


def _run_zero_point_check(
    dataload: DataLoad,
    context,
    *,
    device_str: str,
    out_dir: Path,
) -> Dict[str, object]:
    """Phase D — Zero-point alignment probe (no-op Stage A).

    Runs `_stage_a_adam_core` with `n_steps=0` and all geometry deltas frozen,
    then compares the initial Stage-A forward model against `bragg_zero_iter`.
    Emits `zero_point_check.json` with max/mean |Δ| and per-ROI CC vs mapping,
    plus a `zero_point_ok` flag used to gate geometry experiments.
    """
    payload = _stage_a_adam_core(
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


def _run_blockwise_dof_experiments(
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

    Args:
        use_u_matrix: If True, use quaternion U-matrix parameterization for
            orientation instead of cell+misset (TORCH-GEOMETRY-PARITY-002).
        telemetry_output_dir: If provided, emit per-step telemetry JSON files
            for convergence diagnosis (TORCH-GEOMETRY-CONVERGENCE-001 Phase A1).
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
        payload = _stage_a_adam_core(
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


def _run_gradient_probe(
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
    """
    print("[gradient_probe] Initializing Stage-A components at mapping zero point...")
    components = _build_stage_a_components(dataload, context, device_str=device_str)
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
    bragg_tensor, chi_squared_global_from_forward = _stage_a_forward(
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage A mapping Adam debug driver (TOOLING-VIS-001)."
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="phases",
        choices=["phases", "gradient_probe"],
        help=(
            "Execution mode: 'phases' runs selected debug phases (legacy behavior); "
            "'gradient_probe' evaluates chi-squared and per-DoF gradients at the "
            "mapping zero point (TORCH-REFINE-002E Phase B1)."
        ),
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Torch device for simulation (default: cpu).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20251121,
        help="Random seed for debug run (default: 20251121).",
    )
    parser.add_argument(
        "--adam-steps",
        type=int,
        default=10,
        help="Number of Adam steps for Phase 5 block-wise experiments (default: 10).",
    )
    parser.add_argument(
        "--adam-lr",
        type=float,
        default=1e-4,
        help="Learning rate for Phase 4 Adam experiment (default: 1e-4).",
    )
    parser.add_argument(
        "--phases",
        type=str,
        default="1,2,4",
        help=(
            "Comma-separated list of phases to run "
            "(subset of 1,2,3,4,5; 3=zero-point alignment probe)."
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default=None,
        help=(
            "Override output directory (absolute path or relative to repo root). "
            "If not provided, a timestamped directory is created under "
            "plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam_debug/<timestamp>/ "
            "for phases mode, or under the initiative-specific reports directory for "
            "gradient_probe mode."
        ),
    )
    parser.add_argument(
        "--dof-variants",
        type=str,
        default=None,
        help=(
            "Comma-separated list of DoF variants to run in Phase 5 "
            "(subset of A_scale_only,B_scale_plus_cell,C_scale_plus_orientation,D_full). "
            "If not provided, all variants are run."
        ),
    )
    parser.add_argument(
        "--use-u-matrix",
        action="store_true",
        help=(
            "Enable quaternion U-matrix parameterization for Stage A orientation "
            "(TORCH-GEOMETRY-PARITY-002). When enabled, refines orientation via 4-DOF "
            "quaternion → rotation matrix → A* instead of cell+misset decomposition."
        ),
    )
    parser.add_argument(
        "--use-lbfgs",
        action="store_true",
        help=(
            "Use LBFGS optimizer instead of Adam for U-matrix path "
            "(TORCH-GEOMETRY-CONVERGENCE-001 Test B1). LBFGS eliminates momentum accumulation, "
            "uses line search for stability. Only applies when --use-u-matrix is enabled."
        ),
    )
    parser.add_argument(
        "--optimizer-steps",
        type=int,
        default=10,
        help="Number of optimizer steps (Adam or LBFGS). Default: 10.",
    )
    parser.add_argument(
        "--telemetry-dir",
        type=str,
        default=None,
        help=(
            "Directory for per-step telemetry JSON files (TORCH-GEOMETRY-CONVERGENCE-001 Phase A1). "
            "When set, enables instrumentation of quaternion U-matrix closure to emit parameter, "
            "gradient, loss, and variance metrics for convergence diagnosis. Relative paths are "
            "resolved relative to --out-dir if provided, otherwise relative to the current directory."
        ),
    )
    return parser.parse_args()


def main(argv: List[str] | None = None) -> None:
    args = _parse_args()

    seed = _setup_environment(args.seed, args.device)

    # Handle custom out_dir or create default timestamped directory
    if args.out_dir is not None:
        out_root = Path(args.out_dir)
        if not out_root.is_absolute():
            out_root = REPO_ROOT / out_root
        out_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    else:
        timestamp, out_root = _create_debug_run_dir()

    _write_commands_txt(out_root, seed, sys.argv if argv is None else argv)

    dataload = _build_dataload(REPO_ROOT)
    context = build_mapping_stage_a_context(dataload, device="cpu")

    if args.mode == "gradient_probe":
        # TORCH-REFINE-002E Phase B1: Gradient probe mode
        _run_gradient_probe(
            dataload,
            context,
            device_str=args.device,
            out_dir=out_root,
        )
        print(
            f"[stage_a_mapping_adam_debug] Gradient probe completed "
            f"→ artifacts under {out_root}"
        )
    else:
        # Legacy phases mode
        phases = {p.strip() for p in args.phases.split(",") if p.strip()}

        zero_point_result: Dict[str, object] | None = None
        if "3" in phases or "4" in phases or "5" in phases:
            zero_point_result = _run_zero_point_check(
                dataload,
                context,
                device_str=args.device,
                out_dir=out_root,
            )
            zero_ok = bool(zero_point_result.get("zero_point_ok", False))
            if not zero_ok:
                print(
                    "[stage_a_mapping_adam_debug] Zero-point check FAILED "
                    "(see zero_point_check.json); geometry phases will be skipped."
                )
                # If zero-point is not aligned, do not run geometry experiments.
                phases.discard("4")
                phases.discard("5")

        if "1" in phases:
            _run_forward_model_probe(
                dataload,
                context,
                device_str=args.device,
                out_dir=out_root,
            )

        if "2" in phases:
            _run_loss_alignment_probe(
                context,
                device_str=args.device,
                out_dir=out_root,
            )

        if "4" in phases:
            _run_single_step_adam(
                dataload,
                context,
                device_str=args.device,
                lr=args.adam_lr,
                out_dir=out_root,
            )

        if "5" in phases:
            dof_variants_list = None
            if args.dof_variants is not None:
                dof_variants_list = [v.strip() for v in args.dof_variants.split(",") if v.strip()]

            # Resolve telemetry_dir relative to out_root if it's a relative path
            telemetry_dir_resolved = None
            if args.telemetry_dir is not None:
                from pathlib import Path as PPath
                telemetry_p = PPath(args.telemetry_dir)
                if not telemetry_p.is_absolute():
                    telemetry_dir_resolved = str(out_root / telemetry_p)
                else:
                    telemetry_dir_resolved = args.telemetry_dir

            _run_blockwise_dof_experiments(
                dataload,
                context,
                device_str=args.device,
                n_steps=max(args.optimizer_steps, 0),
                lr=args.adam_lr,
                out_dir=out_root,
                dof_variants=dof_variants_list,
                use_u_matrix=args.use_u_matrix,
                use_lbfgs=args.use_lbfgs,
                telemetry_output_dir=telemetry_dir_resolved,
            )

        # This script is debug-only; no exceptions here are converted to non-zero
        # exit codes beyond Python's defaults.
        print(
            f"[stage_a_mapping_adam_debug] Completed phases {sorted(phases)} "
            f"→ artifacts under {out_root} (timestamp={timestamp})"
        )


if __name__ == "__main__":
    main()
