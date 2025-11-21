#!/usr/bin/env python3
"""
Experimental mapping-based Stage A ROI triptychs using Adam (scale-only).

This helper is **visualization-only** and does NOT modify the canonical
``run_nanobrag_refinement`` path, which remains LBFGS per spec-db-workflow.

Pipeline:
- Load refined geometry + canonical mask/sigma via DataLoad.
- Build a mapping-based Stage A context using ``build_mapping_stage_a_context``
  (zero-iteration Bragg stack from ``simulate_forward_once`` + sigma_floor).
- Optimize a single global log_scale parameter with ``refine_on_mapping_model``
  against the variance-weighted chi-squared loss (geometry fixed).
- Emit ROI triptychs comparing:
    Data | Model_before | Z-before
    Data | Model_after  | Z-after (Adam scale-only)

Artifacts are written under:

    plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam/<timestamp>/
"""

from __future__ import annotations

import os
from argparse import Namespace
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
from dbex.vis import (  # type: ignore  # noqa: E402
    MappingRefinementConfig,
    build_mapping_stage_a_context,
    emit_stage_a_roi_triptychs,
    refine_on_mapping_model,
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


def _run_mapping_adam_scale_only(
    dataload: DataLoad,
    *,
    n_steps: int = 100,
    lr: float = 1e-3,
):
    """Run mapping-based scale-only refinement using the mapping helpers."""
    context = build_mapping_stage_a_context(dataload, device="cpu")
    cfg = MappingRefinementConfig(
        n_steps=n_steps,
        learning_rate=lr,
        device="cpu",
    )
    result = refine_on_mapping_model(
        context.inputs,
        context.bragg_zero_iter,
        context.sigma_floor_value,
        config=cfg,
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
    """Render aggregate before/after ROI triptych grids for quick scanning."""
    n = len(triptychs)
    if n == 0:
        return

    sigma = inputs.sigma_readout
    loss_mask = inputs.loss_mask
    panel_slices = inputs.panel_slices

    ncols = 3
    fig_b, axes_b = plt.subplots(
        n, ncols, figsize=(4 * ncols, 2 * n), constrained_layout=True
    )
    fig_a, axes_a = plt.subplots(
        n, ncols, figsize=(4 * ncols, 2 * n), constrained_layout=True
    )

    if n == 1:
        axes_b = np.array([axes_b])
        axes_a = np.array([axes_a])

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

        ax = axes_b[row]
        ax[0].imshow(
            data_roi,
            origin="upper",
            cmap="cividis",
            vmin=vmin_int,
            vmax=vmax_data,
        )
        ax[0].set_title(f"ROI {roi_idx} Data")
        ax[1].imshow(
            mb_roi,
            origin="upper",
            cmap="cividis",
            vmin=vmin_int,
            vmax=vmax_before,
        )
        ax[1].set_title("Model (before)")
        zb_abs = np.nanmax(np.abs(z_before))
        zb_extent = zb_abs if zb_abs > 0 else 1.0
        ax[2].imshow(
            z_before,
            origin="upper",
            cmap="coolwarm",
            vmin=-zb_extent,
            vmax=zb_extent,
        )
        ax[2].set_title("Z (before)")
        for c in range(ncols):
            ax[c].set_xticks([])
            ax[c].set_yticks([])

        ax = axes_a[row]
        ax[0].imshow(
            data_roi,
            origin="upper",
            cmap="cividis",
            vmin=vmin_int,
            vmax=vmax_data,
        )
        ax[0].set_title(f"ROI {roi_idx} Data")
        ax[1].imshow(
            ma_roi,
            origin="upper",
            cmap="cividis",
            vmin=vmin_int,
            vmax=vmax_after,
        )
        ax[1].set_title("Model (after, Adam)")
        za_abs = np.nanmax(np.abs(z_after))
        za_extent = za_abs if za_abs > 0 else 1.0
        ax[2].imshow(
            z_after,
            origin="upper",
            cmap="coolwarm",
            vmin=-za_extent,
            vmax=za_extent,
        )
        ax[2].set_title("Z (after, Adam)")
        for c in range(ncols):
            ax[c].set_xticks([])
            ax[c].set_yticks([])

    fig_b.suptitle("All ROIs — Data | Model (before) | Z (before)", fontsize=12)
    fig_a.suptitle("All ROIs — Data | Model (after, Adam) | Z (after)", fontsize=12)
    fig_b.savefig(out_root / "all_rois_before.png", dpi=150, bbox_inches="tight")
    fig_a.savefig(out_root / "all_rois_after.png", dpi=150, bbox_inches="tight")
    plt.close(fig_b)
    plt.close(fig_a)


def main() -> None:
    os.environ.setdefault("NANOBRAGG_DISABLE_COMPILE", "1")

    repo_root = Path(__file__).resolve().parents[4]

    dataload = _build_dataload(repo_root)
    context, refine_result = _run_mapping_adam_scale_only(
        dataload,
        n_steps=100,
        lr=1e-3,
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
        ax.plot(range(len(loss_trace)), loss_trace, marker="o", linewidth=1)
        ax.set_xlabel("Adam step")
        ax.set_ylabel("Chi-squared loss")
        ax.set_title("Mapping-based Stage A (Adam scale-only) loss trace")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_root / "adam_loss_trace.png", dpi=150, bbox_inches="tight")
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

