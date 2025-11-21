#!/usr/bin/env python3
"""
Experimental mapping-based Stage A ROI triptychs using Adam (full Stage A).

This helper is **visualization-only** and does NOT modify the canonical
``run_nanobrag_refinement`` path, which remains LBFGS per spec-db-workflow.

Pipeline (current implementation):
- Load refined geometry + canonical mask/sigma via DataLoad.
- Build a mapping-based Stage A context using ``build_mapping_stage_a_context``
  (zero-iteration Bragg stack from ``simulate_forward_once`` + sigma_floor).
- Run an experimental full Stage A Adam refinement helper on top of the
  mapping context (scale + cell + orientation) using its own forward path.
- Emit ROI triptychs comparing:
    Data | Model_before | Z-before
    Data | Model_after  | Z-after (Adam full Stage A, experimental)

Important:
- The full Stage A branch here is **not** required to satisfy the
  Mapping-Aligned Stage‑A Initialization zero-point invariant used by the
  `stage_a_mapping_adam_debug.py` driver, and it is explicitly treated as
  non-mapping-aligned tooling.
- It MUST NOT be used as the canonical "before" reference for TOOLING-VIS-001
  visuals or as a DB-AT selector. Use the mapping-only context and
  scale-only refinement (`refine_on_mapping_model`) for spec-aligned paths.

Artifacts are written under:

    plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam/<timestamp>/
"""

from __future__ import annotations

import os
from argparse import Namespace
import argparse
from datetime import datetime
from pathlib import Path
from pathlib import Path as _Path
import sys as _sys

import numpy as np
from matplotlib import pyplot as plt

_REPO_ROOT = _Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))

from dbex.data_load import DataLoad  # type: ignore  # noqa: E402
from dbex.nanobrag_bridge import (  # type: ignore  # noqa: E402
    build_structure_factor_grid,
    create_beam_config,
    create_crystal_config,
    create_detector_config,
)
from dbex.nanobrag_refinement import (  # type: ignore  # noqa: E402
    _compute_variance_weighted_loss,
    quaternion_to_xyz_euler,
    vec_to_unit_quaternion,
)
from dbex.vis import (  # type: ignore  # noqa: E402
    build_mapping_stage_a_context,
    emit_stage_a_roi_triptychs,
)
from dbex.vis.residuals import compute_z_scores  # type: ignore  # noqa: E402


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

    args = Namespace(
        exptName=str(expt),
        reflName=str(refl),
        exptIdx=0,
        mtzFile=str(mtz),
        mtzCol="F,SIGF",
        maskFile=str(mask),
    )

    return DataLoad(args)


def _run_mapping_full_stage_a(
    dataload: DataLoad,
    *,
    n_steps: int = 100,
    lr: float = 1e-3,
    device_str: str = "cpu",
):
    """Optimize full Stage A parameters (scale + geometry) on the mapping model.

    This helper reuses the same HKL grid, calibration path, and sqrt(spot_scale)
    scaling as :func:`simulate_forward_once` so the mapping \"before\" and
    Stage-A-refined \"after\" truly share a forward model.

    Internally it now uses :class:`nanobrag_torch.models.experiment.ExperimentModel`
    with the external HKL-grid hook (``hkl_data``/``hkl_metadata``) instead of
    reaching into ``Crystal.hkl_data`` directly. Stage-A degrees of freedom for
    cell/angles/orientation remain plan-local and are injected via
    :func:`create_crystal_config`; ``ExperimentModel`` is used as the canonical
    way to wire configs + HKL grid into the Simulator.
    """
    import torch
    from nanobrag_torch.models.experiment import (  # type: ignore  # noqa: E402
        ExperimentModel,
    )
    from dbex.vis.mapping import MappingRefinementResult  # type: ignore  # noqa: E402

    # Build mapping context once (zero-iteration mapping + diagnostics).
    context = build_mapping_stage_a_context(dataload, device=device_str)
    inputs = context.inputs

    device = torch.device(device_str)
    dtype = torch.float32

    # HKL grid: mirror simulate_forward_once (no halo).
    if context.hkl_indices is None or context.hkl_amplitudes is None:
        hkl_indices = dataload.F.indices()
        hkl_amplitudes = dataload.F.data()
    else:
        hkl_indices = context.hkl_indices
        hkl_amplitudes = context.hkl_amplitudes

    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device,
        halo=False,
    )

    # Calibration path: same fields as simulate_forward_once.
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

    # Pre-build Detector configs once (geometry-only, no Stage-A params).
    n_panels = len(dataload.detector)
    detector_configs: list[object] = []
    for pid in range(n_panels):
        det_cfg = create_detector_config(
            panel=dataload.detector[pid],
            beam=dataload.beam,
            trusted_mask=inputs.trusted_mask[pid],
        )
        detector_configs.append(det_cfg)

    target_t = torch.tensor(inputs.target, device=device, dtype=dtype)
    sigma_t = torch.tensor(inputs.sigma_readout, device=device, dtype=dtype)
    mask_t = torch.tensor(inputs.loss_mask, device=device, dtype=torch.bool)

    # Initialize Stage A parameters.
    if inputs.global_scale_hint is not None and inputs.global_scale_hint > 0:
        initial_log_scale = float(np.log(inputs.global_scale_hint))
    else:
        initial_log_scale = 0.0
    log_scale = torch.tensor(
        initial_log_scale,
        device=device,
        dtype=dtype,
        requires_grad=True,
    )

    log_cell_a_delta = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    log_cell_b_delta = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    log_cell_c_delta = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)

    angle_alpha_raw = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    angle_beta_raw = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)
    angle_gamma_raw = torch.tensor(0.0, device=device, dtype=dtype, requires_grad=True)

    orientation_vec = torch.zeros(3, device=device, dtype=dtype, requires_grad=True)

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
    optimizer = torch.optim.Adam(params, lr=lr)

    sigma_floor_sq_tensor = torch.tensor(
        context.sigma_floor_value ** 2, device=device, dtype=dtype
    )

    trace: list[float] = []

    for _ in range(n_steps):
        optimizer.zero_grad()

        # Crystal perturbations (cell lengths, angles, orientation).
        cell_params = dataload.crystal.get_unit_cell().parameters()

        perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
        perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
        perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)

        max_angle_delta = 10.0
        perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
        perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
        perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta

        # Per docs/nanobrag_api.md Stage-A summary, orientation
        # deltas are bounded to ±10° via tanh; keep this helper
        # aligned with that convention.
        max_orientation_deg = 10.0
        bounded_orientation_vec = (
            torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
        )
        quat = vec_to_unit_quaternion(bounded_orientation_vec)
        misset_xyz_deg = quaternion_to_xyz_euler(quat)

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

        log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)

        # Build per-panel ExperimentModels with the external HKL grid hook.
        bragg_t = torch.zeros_like(target_t, device=device, dtype=dtype)
        for pid in range(n_panels):
            exp_model = ExperimentModel(
                crystal_config=crystal_config,
                detector_config=detector_configs[pid],
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

        chi_squared, _, _, _ = _compute_variance_weighted_loss(
            bragg_t,
            target_t,
            mask_t,
            sigma_t,
            sigma_floor_sq_tensor,
        )

        loss = chi_squared
        loss.backward()
        optimizer.step()

        trace.append(float(loss.item()))

    # Rebuild full Bragg array at final parameters.
    with torch.no_grad():
        log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
        bragg_after_t = torch.zeros_like(target_t, device=device, dtype=dtype)

        # Rebuild final crystal config with last parameters.
        cell_params = dataload.crystal.get_unit_cell().parameters()
        perturbed_cell_a = cell_params[0] * torch.exp(log_cell_a_delta)
        perturbed_cell_b = cell_params[1] * torch.exp(log_cell_b_delta)
        perturbed_cell_c = cell_params[2] * torch.exp(log_cell_c_delta)
        max_angle_delta = 10.0
        perturbed_alpha = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta
        perturbed_beta = cell_params[4] + torch.tanh(angle_beta_raw) * max_angle_delta
        perturbed_gamma = cell_params[5] + torch.tanh(angle_gamma_raw) * max_angle_delta
        # Match the ±10° Stage-A orientation bounds from
        # docs/nanobrag_api.md when rebuilding the final model.
        max_orientation_deg = 10.0
        bounded_orientation_vec = (
            torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
        )
        quat = vec_to_unit_quaternion(bounded_orientation_vec)
        misset_xyz_deg = quaternion_to_xyz_euler(quat)

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

        for pid in range(n_panels):
            exp_model = ExperimentModel(
                crystal_config=crystal_config,
                detector_config=detector_configs[pid],
                beam_config=beam_config,
                device=device,
                dtype=dtype,
                param_init="frozen",
                hkl_data=hkl_grid,
                hkl_metadata=hkl_metadata,
            )
            panel_output = exp_model()
            panel_scaled = panel_output * sqrt_spot_scale * torch.exp(log_scale_clamped)
            bragg_after_t[pid] = panel_scaled

        bragg_after = bragg_after_t.cpu().numpy().astype(np.float32)

    final_scale = float(torch.exp(log_scale_clamped).cpu().item())

    result = MappingRefinementResult(
        bragg_after=bragg_after,
        loss_trace=trace,
        final_scale=final_scale,
    )
    return context, result


def _plot_all_roi_triptychs(
    inputs,
    bragg_before: np.ndarray,
    bragg_after: np.ndarray,
    sigma_floor_value: float,
    triptychs,
    out_root: Path,
) -> None:
    """Render a single all-ROI side-by-side comparison PNG.

    Layout per ROI (row):
        Data | Model_before | Z_before | Model_after | Z_after
    """
    n = len(triptychs)
    if n == 0:
        return

    sigma = inputs.sigma_readout
    loss_mask = inputs.loss_mask
    panel_slices = inputs.panel_slices

    ncols = 5
    fig, axes = plt.subplots(
        n, ncols, figsize=(4 * ncols, 2 * n), constrained_layout=True
    )

    if n == 1:
        axes = np.array([axes])

    var_floor_sq = sigma_floor_value ** 2

    def _robust_vmax(arr: np.ndarray) -> float:
        flat = np.asarray(arr, dtype=float).ravel()
        flat = flat[np.isfinite(flat)]
        if flat.size == 0:
            return 1.0
        vmax = np.percentile(flat, 99.0)
        return float(vmax) if vmax > 0 else 1.0

    for row, rec in enumerate(triptychs):
        roi_idx = rec.roi_index
        pid, bbox = panel_slices[roi_idx]
        x0, x1, y0, y1 = map(int, bbox)

        data_roi = inputs.target[pid, y0:y1, x0:x1]
        mb_roi = bragg_before[pid, y0:y1, x0:x1]
        ma_roi = bragg_after[pid, y0:y1, x0:x1]
        sigma_roi = sigma[pid, y0:y1, x0:x1]
        mask_roi = loss_mask[pid, y0:y1, x0:x1]

        vmax_data = _robust_vmax(data_roi)
        vmax_before = _robust_vmax(mb_roi)
        vmax_after = _robust_vmax(ma_roi)
        vmin_int = 0.0

        var_before = np.maximum(
            mb_roi.astype(np.float64) + sigma_roi.astype(np.float64) ** 2,
            var_floor_sq,
        )
        z_before = compute_z_scores(
            data_roi,
            mb_roi,
            variance=var_before,
            sigma_floor=sigma_floor_value,
        )

        var_after = np.maximum(
            ma_roi.astype(np.float64) + sigma_roi.astype(np.float64) ** 2,
            var_floor_sq,
        )
        z_after = compute_z_scores(
            data_roi,
            ma_roi,
            variance=var_after,
            sigma_floor=sigma_floor_value,
        )

        row_axes = axes[row]

        # Data
        row_axes[0].imshow(
            data_roi,
            origin="upper",
            cmap="cividis",
            vmin=vmin_int,
            vmax=vmax_data,
        )
        row_axes[0].set_title(f"ROI {roi_idx} Data")

        # Model_before
        row_axes[1].imshow(
            mb_roi,
            origin="upper",
            cmap="cividis",
            vmin=vmin_int,
            vmax=vmax_before,
        )
        row_axes[1].set_title(f"Model_before (CC={rec.cc_before:.3f})")

        # Z_before
        zb_abs = np.nanmax(np.abs(z_before))
        zb_extent = zb_abs if zb_abs > 0 else 1.0
        row_axes[2].imshow(
            z_before,
            origin="upper",
            cmap="coolwarm",
            vmin=-zb_extent,
            vmax=zb_extent,
        )
        row_axes[2].set_title("Z_before")

        # Model_after
        row_axes[3].imshow(
            ma_roi,
            origin="upper",
            cmap="cividis",
            vmin=vmin_int,
            vmax=vmax_after,
        )
        row_axes[3].set_title(f"Model_after (CC={rec.cc_after:.3f})")

        # Z_after
        za_abs = np.nanmax(np.abs(z_after))
        za_extent = za_abs if za_abs > 0 else 1.0
        row_axes[4].imshow(
            z_after,
            origin="upper",
            cmap="coolwarm",
            vmin=-za_extent,
            vmax=za_extent,
        )
        row_axes[4].set_title("Z_after")

        for c in range(ncols):
            row_axes[c].set_xticks([])
            row_axes[c].set_yticks([])

    fig.suptitle(
        "All ROIs — Data | Model_before | Z_before | Model_after | Z_after",
        fontsize=12,
    )
    fig.savefig(
        out_root / "all_rois_side_by_side.png",
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(fig)


def main() -> None:
    os.environ.setdefault("NANOBRAGG_DISABLE_COMPILE", "1")

    parser = argparse.ArgumentParser(
        description=(
            "Generate mapping-based Stage A ROI triptychs with experimental "
            "full-DoF Adam refinement on top of the mapping context."
        )
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Torch device for simulation (e.g. 'cpu', 'cuda:0'; default: cpu).",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=20,
        help="Number of Adam steps for full Stage A refinement (default: 20).",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=1e-3,
        help="Learning rate for full Stage A Adam refinement (default: 1e-3).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[4]

    dataload = _build_dataload(repo_root)
    context, refine_result = _run_mapping_full_stage_a(
        dataload,
        n_steps=args.steps,
        lr=args.lr,
        device_str=args.device,
    )

    inputs = context.inputs
    bragg_before = context.bragg_zero_iter
    bragg_after = refine_result.bragg_after
    sigma_floor_value = context.sigma_floor_value
    loss_trace = refine_result.loss_trace

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_root = (
        repo_root
        / "plans"
        / "active"
        / "TOOLING-VIS-001"
        / "reports"
        / "stage_a_refgeom_adam"
        / timestamp
    )
    out_root.mkdir(parents=True, exist_ok=True)

    triptychs = emit_stage_a_roi_triptychs(
        inputs,
        bragg_before,
        bragg_after,
        out_dir=out_root / "roi_triptychs",
        max_rois=16,
        sigma_floor_value=sigma_floor_value,
    )

    if loss_trace:
        fig, ax = plt.subplots(figsize=(6, 4))
        steps = range(len(loss_trace))
        ax.plot(steps, loss_trace, marker="o", linewidth=1)
        ax.set_xlabel("Adam step")
        ax.set_ylabel("Chi-squared loss")
        ax.set_title("Mapping-based Stage A (Adam full-DoF, experimental) loss curve")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        # Legacy name plus the explicit *_curve variant requested.
        curve_path = out_root / "adam_loss_curve.png"
        trace_path = out_root / "adam_loss_trace.png"
        fig.savefig(curve_path, dpi=150, bbox_inches="tight")
        fig.savefig(trace_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

    _plot_all_roi_triptychs(
        inputs,
        bragg_before,
        bragg_after,
        sigma_floor_value,
        triptychs,
        out_root,
    )

    lines = [
        "# Stage A ROI Before/After Triptychs (Mapping + Adam Scale-Only)",
        "",
        f"- Timestamp: {timestamp}",
        f"- Output directory: {out_root}",
        f"- Number of ROIs rendered: {len(triptychs)}",
        "",
        "## Optimizer",
        "",
        f"- Optimizer: Adam (global log_scale only)",
        f"- Steps: {len(loss_trace)}",
        f"- Initial loss: {loss_trace[0]:.6e}" if loss_trace else "- Initial loss: n/a",
        f"- Final loss: {loss_trace[-1]:.6e}" if loss_trace else "- Final loss: n/a",
        "",
        "## ROI Table",
        "",
        "| ROI | Panel | BBox (x0,x1,y0,y1) | CC_before | CC_after | PNG_before | PNG_after |",
        "| --- | ----- | ------------------ | --------- | -------- | ---------- | --------- |",
    ]
    for rec in triptychs:
        lines.append(
            f"| {rec.roi_index} | {rec.panel_id} | "
            f"({rec.bbox[0]},{rec.bbox[1]},{rec.bbox[2]},{rec.bbox[3]}) | "
            f"{rec.cc_before:.3f} | {rec.cc_after:.3f} | "
            f"{rec.path_before.name} | {rec.path_after.name} |"
        )

    (out_root / "summary.md").write_text("\n".join(lines))

    if loss_trace:
        initial_loss = loss_trace[0]
        final_loss = loss_trace[-1]
        if final_loss > initial_loss * 1.05:
            raise RuntimeError(
                f"Mapping-based scale refinement increased loss by more than 5% "
                f"(initial={initial_loss:.6e}, final={final_loss:.6e})"
            )

    if triptychs:
        cc_before = np.array([rec.cc_before for rec in triptychs], dtype=float)
        cc_after = np.array([rec.cc_after for rec in triptychs], dtype=float)
        median_before = float(np.median(cc_before))
        median_after = float(np.median(cc_after))
        if median_after < median_before - 0.05:
            raise RuntimeError(
                f"Mapping-based refinement degraded median CC by more than 0.05 "
                f"(before={median_before:.3f}, after={median_after:.3f})"
            )


if __name__ == "__main__":
    main()
