#!/usr/bin/env python3
"""
Canonical Stage A ROI triptychs using the tested LBFGS refinement path.

This TOOLING-VIS-001 helper now drives the same Stage A refinement engine
used by the `test_stage_a_expansion` smoke test:

- Loads refGeom assets via :class:`dbex.data_load.DataLoad`.
- Builds a mapping-based zero-iteration context via
  :func:`dbex.vis.mapping.build_mapping_stage_a_context` to obtain
  ``RefinementInputs`` and the pre-refinement Bragg stack
  (``bragg_zero_iter``).
- Runs :func:`dbex.nanobrag_refinement.run_nanobrag_refinement` with a
  Stage-A-only LBFGS configuration (no Stage B/C) on top of the same HKL
  grid and inputs.
- Emits ROI triptychs comparing:

    Data | Model_before | Z-before
    Data | Model_after  | Z-after  (canonical Stage A LBFGS)

Artifacts are written under:

    plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam/<timestamp>/

The older experimental Adam-based full-Stage-A mapping helper has been
retired in favor of this canonical, test-backed refinement path.
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
    RefinementConfig,
    _build_final_bragg_from_stage_a_telemetry,
    run_nanobrag_refinement,
)
from dbex.vis.mapping import (  # type: ignore  # noqa: E402
    build_mapping_stage_a_context,
)
from dbex.vis.stage_a import (  # type: ignore  # noqa: E402
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


def _run_canonical_stage_a(
    dataload: DataLoad,
    *,
    n_steps: int = 30,
    device_str: str = "cpu",
):
    """Run canonical Stage A LBFGS refinement and build before/after Bragg stacks.

    Uses the same Stage A engine as ``test_stage_a_expansion`` and returns:
    - inputs: RefinementInputs used by Stage A
    - sigma_floor_value: variance floor from mapping diagnostics
    - bragg_before: Stage-A zero-iteration Bragg stack (initial params)
    - bragg_after: Stage-A refined Bragg stack
    - chi2_trace: full chi-squared trace from telemetry
    """
    import copy
    import torch

    # Build mapping context once (only to obtain RefinementInputs and sigma_floor).
    context = build_mapping_stage_a_context(dataload, device=device_str)
    inputs = context.inputs
    sigma_floor_value = context.sigma_floor_value

    device = torch.device(device_str)

    # HKL grid: reuse mapping indices/amplitudes, add halo for Stage A interpolation.
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
        halo=True,
    )

    # Stage A-only LBFGS config; mirror test_stage_a_expansion where possible.
    config = RefinementConfig(
        device=device_str,
        dtype=torch.float32,
        history_size=10,
        max_iter=int(n_steps),
        roi_sample_fraction=0.15,
        full_validation_interval=5,
        enable_hkl_interpolation=True,
        enable_stage_b=False,
        enable_stage_c=False,
        sigma_readout_provenance=getattr(
            inputs, "sigma_readout_provenance", "cli_override"
        ),
    )

    # Use the unperturbed geometry as both current and baseline.
    baseline_crystal = dataload.crystal
    baseline_detector = dataload.detector

    bragg_after, telemetry_dict = run_nanobrag_refinement(
        inputs=inputs,
        detector=dataload.detector,
        beam=dataload.beam,
        crystal=dataload.crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,
        use_engine_delegation=True,
    )

    telemetry_a = telemetry_dict["A"]
    chi2_trace = [float(loss) for _, loss in telemetry_a.chi_squared_trace_full]

    # Build Stage-A zero-iteration Bragg by replaying initial parameters.
    telemetry_initial = copy.deepcopy(telemetry_a)
    param_keys = [
        "log_scale",
        "log_cell_a_delta",
        "log_cell_b_delta",
        "log_cell_c_delta",
        "angle_alpha_raw",
        "angle_beta_raw",
        "angle_gamma_raw",
        "orientation_vec",
    ]
    for key in param_keys:
        if key in telemetry_initial.param_deltas:
            entry = telemetry_initial.param_deltas[key]
            if isinstance(entry, dict) and "initial" in entry and "final" in entry:
                entry["final"] = entry["initial"]

    bragg_before = _build_final_bragg_from_stage_a_telemetry(
        telemetry_initial,
        dataload.detector,
        dataload.beam,
        dataload.crystal,
        inputs,
        hkl_grid,
        hkl_metadata,
        config,
        device,
        torch.float32,
    )

    return inputs, sigma_floor_value, bragg_before, bragg_after, chi2_trace


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


def _render_full_frame(
    data_stack: np.ndarray,
    title: str,
    out_path: Path,
) -> None:
    """Render a single full-frame image by tiling panels vertically.

    For multi-panel detectors, panels are concatenated along the slow axis so
    that the output remains a single 2D image.
    """
    arr = np.asarray(data_stack, dtype=float)
    if arr.ndim != 3:
        raise ValueError(f"Expected [panel, slow, fast] stack, got shape {arr.shape}")

    n_panels, slow, fast = arr.shape
    tiled = arr.reshape(n_panels * slow, fast)

    finite = tiled[np.isfinite(tiled)]
    if finite.size == 0:
        vmax = 1.0
    else:
        vmax = np.percentile(finite, 99.0)
        if vmax <= 0.0 or not np.isfinite(vmax):
            vmax = 1.0

    vmin = 0.0

    fig, ax = plt.subplots(figsize=(6, 6), constrained_layout=True)
    im = ax.imshow(
        tiled,
        origin="upper",
        cmap="cividis",
        vmin=vmin,
        vmax=vmax,
    )
    ax.set_title(title)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    os.environ.setdefault("NANOBRAGG_DISABLE_COMPILE", "1")

    parser = argparse.ArgumentParser(
        description=(
            "Generate Stage A ROI triptychs using the canonical LBFGS "
            "Stage-A refinement engine (before/after from the same model)."
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
    (
        inputs,
        sigma_floor_value,
        bragg_before,
        bragg_after,
        loss_trace,
    ) = _run_canonical_stage_a(
        dataload,
        n_steps=args.steps,
        device_str=args.device,
    )

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

    # Full-frame diagnostics: experimental data, Stage-A before, Stage-A after.
    _render_full_frame(
        inputs.target,
        "Experimental data (full frame)",
        out_root / "fullframe_experiment.png",
    )
    _render_full_frame(
        bragg_before,
        "Stage A before refinement (full frame)",
        out_root / "fullframe_stage_a_before.png",
    )
    _render_full_frame(
        bragg_after,
        "Stage A after refinement (full frame)",
        out_root / "fullframe_stage_a_after.png",
    )

    if loss_trace:
        fig, ax = plt.subplots(figsize=(6, 4))
        steps = range(len(loss_trace))
        ax.plot(steps, loss_trace, marker="o", linewidth=1)
        ax.set_xlabel("LBFGS validation index")
        ax.set_ylabel("Chi-squared loss")
        ax.set_title("Canonical Stage A LBFGS chi-squared trace")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        # Legacy name plus the explicit *_curve variant requested.
        curve_path = out_root / "stage_a_loss_curve.png"
        trace_path = out_root / "stage_a_loss_trace.png"
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
        "# Stage A ROI Before/After Triptychs (Canonical LBFGS)",
        "",
        f"- Timestamp: {timestamp}",
        f"- Output directory: {out_root}",
        f"- Number of ROIs rendered: {len(triptychs)}",
        "",
        "## Optimizer",
        "",
        f"- Optimizer: LBFGS (canonical Stage A)",
        f"- Steps (max_iter): {len(loss_trace)}",
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
