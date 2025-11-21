#!/usr/bin/env python3
"""
Generate Stage A before/after ROI triptych PNGs for the canonical refGeom dataset.

This script is scoped to TOOLING-VIS-001 and is intended as a reproducible driver
for the Stage A visualization helpers under :mod:`dbex.vis`. It:

- Loads refGeom assets via :class:`dbex.data_load.DataLoad`.
- Prepares ``RefinementInputs`` using the same conventions as the Stage A smoke tests.
- Runs a zero-iteration forward simulation (`simulate_forward_once`) to obtain the
  "before" Bragg stack.
- Runs Stage A refinement on CPU with a tricubic, haloed HKL grid to obtain the
  "after" Bragg stack.
- Emits per-ROI triptychs (Data | Model_before/after | Residual Z) via
  :func:`dbex.vis.stage_a.emit_stage_a_roi_triptychs`.

Artifacts are written under:

    plans/active/TOOLING-VIS-001/reports/stage_a_refgeom/<timestamp>/
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch


def _build_refgeom_dataload(repo_root: Path):
    """Construct a DataLoad instance for canonical assets (prefer refined geometry).

    Mirrors the DB-AT-024 geometry preference:
    - Prefer refined.expt/refined.refl under tests/fixtures/golden_data/simple_cubic
    - Fall back to legacy refGeom.expt/refGeom.refl when refined assets are missing.
    """
    from dbex.data_load import DataLoad

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

    args = SimpleNamespace(
        exptName=str(expt),
        reflName=str(refl),
        exptIdx=0,
        mtzFile=str(mtz),
        mtzCol="F,SIGF",
        maskFile=str(mask),
    )

    return DataLoad(args)


def _prepare_refinement_inputs_for_stage_a(refgeom_dataload):
    """Mirror the Stage A smoke/DB-AT-024 pipeline to build RefinementInputs."""
    from dbex.nanobrag_bridge import prepare_refinement_inputs

    # Use canonical trusted mask from 747_mask.pkl (or all-True when maskFile missing),
    # matching DB-AT-024 and tmp/visual_demo behavior.
    trusted_masks = refgeom_dataload.trusted_mask

    # Sigma_readout: prefer external_lookup map when available, otherwise 3.0 ADU,
    # identical to DB-AT-024's refinement_inputs fixture.
    sigma_map = getattr(refgeom_dataload, "sigma_readout_map", None)
    sigma_map_source = getattr(refgeom_dataload, "sigma_readout_map_source", None)
    if sigma_map is not None and sigma_map_source == "external_lookup":
        sigma_readout_array = np.asarray(sigma_map, dtype=np.float32)
    else:
        sigma_readout_array = np.full_like(refgeom_dataload.data, 3.0, dtype=np.float32)

    inputs = prepare_refinement_inputs(
        data=refgeom_dataload.data,
        background_image=refgeom_dataload.background_image,
        trusted_mask=trusted_masks,
        bbox=refgeom_dataload.bbox,
        pids=refgeom_dataload.pids,
        detector=refgeom_dataload.detector,
        adu_per_photon=None,
        sigma_readout=sigma_readout_array,
    )

    return inputs


def _build_hkl_grid(refgeom_dataload):
    """Build a haloed HKL grid for tricubic interpolation on CPU."""
    from dbex.nanobrag_bridge import build_structure_factor_grid

    hkl_indices = refgeom_dataload.F.indices()
    hkl_amplitudes = refgeom_dataload.F.data()

    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=torch.device("cpu"),
        halo=True,
    )
    return hkl_grid, hkl_metadata


def _simulate_zero_iteration(refgeom_dataload, inputs, repo_root: Path):
    """Run zero-iteration forward simulation to obtain the 'before' model."""
    from dbex.nanobrag_bridge import (
        load_calibration_metadata,
        load_refined_mtz,
        simulate_forward_once,
    )
    fixtures_root = (
        repo_root / "tests" / "fixtures" / "golden_data" / "simple_cubic"
    )
    config_json = fixtures_root / "config_torch.json"
    refined_mtz = fixtures_root / "refined_structure_factors.mtz"

    # Default HKL source from DataLoad.F (raw scaled.mtz).
    hkl_indices = refgeom_dataload.F.indices()
    hkl_amplitudes = refgeom_dataload.F.data()
    hkl_source = "raw"
    hkl_path = str((repo_root / "scaled.mtz").resolve())

    calibration = None
    if config_json.exists():
        try:
            calibration = load_calibration_metadata(config_json)
        except Exception:
            calibration = None

    if refined_mtz.exists():
        try:
            hkl_indices, hkl_amplitudes = load_refined_mtz(refined_mtz, column="F")
            hkl_source = "refined"
            hkl_path = str(refined_mtz.resolve())
        except Exception:
            # Fall back to raw MTZ if refined MTZ cannot be used.
            pass

    bragg_before, _ = simulate_forward_once(
        inputs=inputs,
        detector=refgeom_dataload.detector,
        beam=refgeom_dataload.beam,
        crystal=refgeom_dataload.crystal,
        experiment=refgeom_dataload.Expt,
        hkl_indices=hkl_indices,
        hkl_amplitudes=hkl_amplitudes,
        calibration=calibration,
        hkl_source=hkl_source,
        hkl_path=hkl_path,
    )

    # Warm-start global_scale_hint from masked means in ADU mode.
    num = float(inputs.target[inputs.loss_mask].mean())
    den = float(bragg_before[inputs.loss_mask].mean())
    if den > 1e-12:
        inputs.global_scale_hint = num / den

    return bragg_before


def _run_stage_a_refinement(refgeom_dataload, inputs, hkl_grid, hkl_metadata):
    """Run Stage A refinement on CPU to obtain the 'after' model."""
    from dbex.nanobrag_refinement import RefinementConfig, run_nanobrag_refinement
    from tests.dbex.test_torch_refine_smoke import create_perturbed_geometry  # type: ignore

    baseline_crystal = refgeom_dataload.Expt.crystal
    baseline_detector = refgeom_dataload.Expt.detector
    baseline_beam = refgeom_dataload.Expt.beam

    # Apply deterministic geometry perturbation to make Stage A improvement visible.
    perturbed_crystal, perturbed_detector, perturbed_beam = create_perturbed_geometry(
        baseline_crystal,
        baseline_detector,
        baseline_beam,
        enable_detector_perturbation=False,
    )

    config = RefinementConfig(
        device="cpu",
        dtype=torch.float32,
        history_size=10,
        max_iter=30,
        roi_sample_fraction=0.15,
        full_validation_interval=5,
        min_loss_improvement=0.0,
        enable_hkl_interpolation=True,
        sigma_readout_provenance=getattr(
            refgeom_dataload, "sigma_readout_map_source", None
        ),
    )

    bragg_after, _ = run_nanobrag_refinement(
        inputs=inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        baseline_crystal=baseline_crystal,
    )

    return bragg_after, config


def main() -> None:
    # Keep nanobrag_torch in eager mode to match smoke-test environment.
    os.environ.setdefault("NANOBRAGG_DISABLE_COMPILE", "1")

    repo_root = Path(__file__).resolve().parents[4]
    if str(repo_root) not in os.sys.path:
        os.sys.path.insert(0, str(repo_root))

    from dbex.vis.stage_a import emit_stage_a_roi_triptychs

    refgeom_dataload = _build_refgeom_dataload(repo_root)
    inputs = _prepare_refinement_inputs_for_stage_a(refgeom_dataload)
    hkl_grid, hkl_metadata = _build_hkl_grid(refgeom_dataload)

    bragg_before = _simulate_zero_iteration(refgeom_dataload, inputs, repo_root)
    bragg_after, config = _run_stage_a_refinement(
        refgeom_dataload, inputs, hkl_grid, hkl_metadata
    )

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_root = (
        repo_root
        / "plans"
        / "active"
        / "TOOLING-VIS-001"
        / "reports"
        / "stage_a_refgeom"
        / timestamp
    )
    out_root.mkdir(parents=True, exist_ok=True)

    triptychs = emit_stage_a_roi_triptychs(
        inputs,
        bragg_before,
        bragg_after,
        out_dir=out_root / "roi_triptychs",
        max_rois=16,
        sigma_floor_value=config.sigma_floor_value,
    )

    # Write a lightweight summary alongside the PNGs.
    summary_lines = [
        "# Stage A ROI Before/After Triptychs",
        "",
        f"- Timestamp: {timestamp}",
        f"- Output directory: {out_root}",
        f"- Number of ROIs rendered: {len(triptychs)}",
        "",
        "## ROI Table",
        "",
        "| ROI | Panel | BBox (x0,x1,y0,y1) | CC_before | CC_after | PNG_before | PNG_after |",
        "| --- | ----- | ------------------ | --------- | -------- | ---------- | --------- |",
    ]
    for record in triptychs:
        summary_lines.append(
            f"| {record.roi_index} | {record.panel_id} | "
            f"({record.bbox[0]},{record.bbox[1]},{record.bbox[2]},{record.bbox[3]}) | "
            f"{record.cc_before:.3f} | {record.cc_after:.3f} | "
            f"{record.path_before.name} | {record.path_after.name} |"
        )

    (out_root / "summary.md").write_text("\n".join(summary_lines))


if __name__ == "__main__":
    main()
