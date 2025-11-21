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


def _build_stage_a_components(
    dataload: DataLoad,
    context,
    *,
    device_str: str,
) -> _StageAComponents:
    """Construct shared Stage A tensors/config used by mapping helpers."""
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

    baseline_misset_deg_tensor = compute_baseline_misset_deg(
        dataload.crystal,
        dataload.Expt.crystal,
        device=device,
        dtype=dtype,
    )

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
    sigma_floor_sq_tensor,
    use_mapping_zero_geometry: bool,
):
    """Shared Stage A forward model used by no-op and Adam helpers."""
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

        crystal_overrides = {
            "cell_a": perturbed_cell_a,
            "cell_b": perturbed_cell_b,
            "cell_c": perturbed_cell_c,
            "cell_alpha": perturbed_alpha,
            "cell_beta": perturbed_beta,
            "cell_gamma": perturbed_gamma,
        }

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
) -> Dict[str, object]:
    """Core helper for Stage A Adam experiments (Phase 4 / Phase 5)."""
    components = _build_stage_a_components(
        dataload,
        context,
        device_str=device_str,
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

    params = [
        log_scale,
        log_cell_a_delta,
        log_cell_b_delta,
        log_cell_c_delta,
        angle_alpha_raw,
        angle_beta_raw,
        angle_gamma_raw,
        orientation_vec,
    ]
    trainable_params = [p for p in params if p.requires_grad]
    optimizer = torch.optim.Adam(trainable_params, lr=lr) if trainable_params else None

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
            sigma_floor_sq_tensor=sigma_floor_sq_tensor,
            use_mapping_zero_geometry=use_mapping_zero_geometry,
        )

    with torch.no_grad():
        # Always treat the initial parameters as the mapping-aligned zero point.
        bragg_before_t, chi_sq_before_t = _forward_once(use_mapping_zero_geometry=True)

    loss_trace: List[float] = [float(chi_sq_before_t.item())]

    if optimizer is not None and n_steps > 0:
        for _ in range(n_steps):
            optimizer.zero_grad()
            bragg_t, chi_sq_t = _forward_once(use_mapping_zero_geometry=False)
            chi_sq_t.backward()
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
) -> Dict[str, object]:
    """Phase 5 — Block-wise DoF isolation experiments."""
    variants = {
        "A_scale_only": dict(train_scale=True, train_cell=False, train_orientation=False),
        "B_scale_plus_cell": dict(train_scale=True, train_cell=True, train_orientation=False),
        "C_scale_plus_orientation": dict(train_scale=True, train_cell=False, train_orientation=True),
        "D_full": dict(train_scale=True, train_cell=True, train_orientation=True),
    }

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
        )
        chi = payload.get("chi_squared", {})
        cc = payload.get("cc_summary", {})
        results[name] = {
            "optimizer": payload.get("optimizer", {}),
            "chi_squared": chi,
            "cc_summary": cc,
        }

    block_payload: Dict[str, object] = {"variants": results}
    (out_dir / "block_dof_results.json").write_text(json.dumps(block_payload, indent=2))
    return block_payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage A mapping Adam debug driver (TOOLING-VIS-001)."
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
    return parser.parse_args()


def main(argv: List[str] | None = None) -> None:
    args = _parse_args()
    phases = {p.strip() for p in args.phases.split(",") if p.strip()}

    seed = _setup_environment(args.seed, args.device)
    timestamp, out_root = _create_debug_run_dir()
    _write_commands_txt(out_root, seed, sys.argv if argv is None else argv)

    dataload = _build_dataload(REPO_ROOT)
    context = build_mapping_stage_a_context(dataload, device="cpu")

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
        _run_blockwise_dof_experiments(
            dataload,
            context,
            device_str=args.device,
            n_steps=max(args.adam_steps, 0),
            lr=args.adam_lr,
            out_dir=out_root,
        )

    # This script is debug-only; no exceptions here are converted to non-zero
    # exit codes beyond Python's defaults.
    print(
        f"[stage_a_mapping_adam_debug] Completed phases {sorted(phases)} "
        f"→ artifacts under {out_root} (timestamp={timestamp})"
    )


if __name__ == "__main__":
    main()
