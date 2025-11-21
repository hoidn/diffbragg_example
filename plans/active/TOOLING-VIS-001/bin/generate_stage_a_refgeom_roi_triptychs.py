#!/usr/bin/env python3
"""
Generate mapping-aligned Stage A ROI triptych PNGs for the canonical refGeom dataset.

This TOOLING-VIS-001 driver builds a mapping-based Stage A context and runs a
vis-only, scale-only refinement layer on top of the DB-AT-024 forward model:

- Loads refGeom assets via :class:`dbex.data_load.DataLoad`.
- Uses ``build_mapping_stage_a_context`` to prepare ``RefinementInputs``,
  run ``simulate_forward_once``, and capture the zero-iteration Bragg stack
  plus ``sigma_floor_value`` diagnostics.
- Uses ``refine_on_mapping_model`` to optimize a single global scale
  parameter against the variance-weighted chi-squared loss.
- Emits per-ROI triptychs (Data | Model_before/after | Residual Z) via
  :func:`dbex.vis.stage_a.emit_stage_a_roi_triptychs`.

Artifacts are written under:

    plans/active/TOOLING-VIS-001/reports/stage_a_refgeom/<timestamp>/

This script is visualization-only and does not modify the canonical
``run_nanobrag_refinement`` Stage A engine.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace


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


def main() -> None:
    # Keep nanobrag_torch in eager mode to match smoke-test environment.
    os.environ.setdefault("NANOBRAGG_DISABLE_COMPILE", "1")

    repo_root = Path(__file__).resolve().parents[4]
    if str(repo_root) not in os.sys.path:
        os.sys.path.insert(0, str(repo_root))

    from dbex.vis import (
        MappingRefinementConfig,
        build_mapping_stage_a_context,
        emit_stage_a_roi_triptychs,
        refine_on_mapping_model,
    )

    refgeom_dataload = _build_refgeom_dataload(repo_root)
    context = build_mapping_stage_a_context(refgeom_dataload, device="cpu")

    refine_config = MappingRefinementConfig(
        n_steps=100,
        learning_rate=1e-3,
        device="cpu",
    )
    refine_result = refine_on_mapping_model(
        context.inputs,
        context.bragg_zero_iter,
        context.sigma_floor_value,
        config=refine_config,
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
        context.inputs,
        context.bragg_zero_iter,
        refine_result.bragg_after,
        out_dir=out_root / "roi_triptychs",
        max_rois=16,
        sigma_floor_value=context.sigma_floor_value,
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
