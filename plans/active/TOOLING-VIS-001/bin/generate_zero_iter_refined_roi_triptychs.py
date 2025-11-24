#!/usr/bin/env python3
"""
Generate zero-iteration ROI triptych PNGs using DIALS-refined geometry.

This script is a minimal, reproducible driver for inspecting whether the
nanobrag_torch forward model starts in the right ballpark when seeded with
the refined experiment geometry and calibration metadata used by DB-AT-024.

Artifacts are written under:

    plans/active/TOOLING-VIS-001/reports/stage_a_zero_iter_refined/<timestamp>/

Each ROI PNG is a spec-db-vis triptych:

    Data | Model (zero-iteration) | Residual Z-Score
"""

from __future__ import annotations

import os
from argparse import Namespace
from datetime import datetime
from pathlib import Path

import numpy as np
import torch


def main() -> None:
    # Keep nanobrag_torch in eager mode (no compile) for determinism.
    os.environ.setdefault("NANOBRAGG_DISABLE_COMPILE", "1")

    repo_root = Path(__file__).resolve().parents[4]
    # Ensure repo root is importable when the script is invoked directly.
    import sys as _sys
    if str(repo_root) not in _sys.path:
        _sys.path.insert(0, str(repo_root))
    from dbex.data_load import DataLoad
    from dbex.nanobrag_bridge import (
        prepare_refinement_inputs,
        simulate_forward_once,
        load_calibration_metadata,
        load_refined_mtz,
    )
    from dbex.vis.triptych import plot_triptych
    from dbex.vis.residuals import compute_z_scores

    fixtures_root = repo_root / "tests" / "fixtures" / "golden_data" / "simple_cubic"
    refined_expt = fixtures_root / "refined.expt"
    refined_refl = fixtures_root / "refined.refl"
    mtz = repo_root / "scaled.mtz"
    mask = repo_root / "747_mask.pkl"

    args = Namespace(
        exptName=str(refined_expt),
        reflName=str(refined_refl),
        exptIdx=0,
        mtzFile=str(mtz),
        mtzCol="F,SIGF",
        maskFile=str(mask),
    )

    dl = DataLoad(args)

    # Sigma_readout: prefer external_lookup map when available, else 3.0 ADU.
    sigma_map = getattr(dl, "sigma_readout_map", None)
    sigma_source = getattr(dl, "sigma_readout_map_source", None)
    if sigma_map is not None and sigma_source == "external_lookup":
        sigma_readout_array = np.asarray(sigma_map, dtype=np.float32)
    else:
        sigma_readout_array = np.full_like(dl.data, 3.0, dtype=np.float32)

    inputs = prepare_refinement_inputs(
        data=dl.data,
        background_image=dl.background_image,
        trusted_mask=dl.trusted_mask,
        bbox=dl.bbox,
        pids=dl.pids,
        detector=dl.detector,
        adu_per_photon=None,
        sigma_readout=sigma_readout_array,
    )

    # Calibration + refined structure factors as in DB-AT-024.
    config_json = fixtures_root / "config_torch.json"
    refined_mtz = fixtures_root / "refined_structure_factors.mtz"
    calibration = load_calibration_metadata(config_json)
    hkl_indices, hkl_amplitudes = load_refined_mtz(refined_mtz, column="F")

    bragg, diagnostics = simulate_forward_once(
        inputs=inputs,
        detector=dl.detector,
        beam=dl.beam,
        crystal=dl.crystal,
        experiment=dl.Expt,
        hkl_indices=hkl_indices,
        hkl_amplitudes=hkl_amplitudes,
        calibration=calibration,
        hkl_source="refined",
        hkl_path=str(refined_mtz),
        device="cpu",
    )

    # Prepare output directory.
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_root = (
        repo_root
        / "plans"
        / "active"
        / "TOOLING-VIS-001"
        / "reports"
        / "stage_a_zero_iter_refined"
        / timestamp
    )
    out_root.mkdir(parents=True, exist_ok=True)

    sigma_floor_value = float(diagnostics.get("sigma_floor_value", 1.0))
    var_floor_sq = sigma_floor_value ** 2

    n_rois = len(inputs.panel_slices)
    max_rois = min(16, n_rois)

    lines = [
        "# Zero-Iteration ROI Triptychs (Refined Geometry)",
        "",
        f"- Timestamp: {timestamp}",
        f"- Output directory: {out_root}",
        f"- Number of ROIs rendered: {max_rois}",
        "",
        "## ROI Table",
        "",
        "| ROI | Panel | BBox (x0,x1,y0,y1) | PNG |",
        "| --- | ----- | ------------------ | --- |",
    ]

    for idx in range(max_rois):
        panel_id, bbox = inputs.panel_slices[idx]
        x0, x1, y0, y1 = map(int, bbox)

        data_roi = inputs.target[panel_id, y0:y1, x0:x1]
        model_roi = bragg[panel_id, y0:y1, x0:x1]
        sigma_roi = inputs.sigma_readout[panel_id, y0:y1, x0:x1]

        variance = np.maximum(
            model_roi.astype(np.float64) + sigma_roi.astype(np.float64) ** 2,
            var_floor_sq,
        )

        out_path = out_root / f"roi_{idx:04d}_zero_iter.png"
        plot_triptych(data_roi, model_roi, variance, filename=str(out_path))

        lines.append(
            f"| {idx} | {panel_id} | "
            f"({x0},{x1},{y0},{y1}) | {out_path.name} |"
        )

    (out_root / "summary.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
