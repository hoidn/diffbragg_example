#!/usr/bin/env python
"""Probe reciprocal lattice alignment between dxtbx and nanobrag_torch (ARCH-SIM-HKL-BOUNDS-001 Phase A.1).

This diagnostic tool quantifies the HKL offset observed during DIAG-NANOBRAGG-OVERSAMPLE-001
by comparing the dxtbx-derived reciprocal lattice matrix (A*) against the nanobrag_torch
Crystal model's computed reciprocal lattice at the Stage-A zero point.

Per docs/spec-db-core.md:64-80, the zero-parameter Stage-A forward must satisfy:
  A*(0) = A*_mapping = crystal.get_A()
where crystal.get_A() is the authoritative dxtbx reciprocal lattice matrix.

Usage:
    NANOBRAGG_DISABLE_COMPILE=1 python probe_crystal_hkl_alignment.py \\
        --detector-size small \\
        --out-dir plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T161200Z/ \\
        --device cpu

Outputs:
    - <out-dir>/hkl_alignment_metrics.json: Quantitative comparison (max/mean |ΔA*|, per-axis deltas)
    - <out-dir>/hkl_alignment_summary.txt: Human-readable prose summary
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

# Push repo root onto sys.path for editable install access
_repo_root = Path(__file__).resolve().parents[4]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from dbex.data_load import DataLoad
from dbex.refinement.config_factories import create_crystal_config
from dbex.vis.mapping import build_mapping_stage_a_context

# Import nanobrag_torch after sys.path adjustment
try:
    from nanobrag_torch.models.crystal import Crystal
except ImportError as e:
    print(f"ERROR: nanobrag_torch.models.crystal import failed: {e}", file=sys.stderr)
    print("Ensure nanobrag_torch is installed (editable or via environment).", file=sys.stderr)
    sys.exit(1)


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Probe reciprocal lattice alignment (ARCH-SIM-HKL-BOUNDS-001 Phase A.1)"
    )
    parser.add_argument(
        "--detector-size",
        choices=["small", "full"],
        default="small",
        help="Detector size variant (default: small)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for metrics JSON and summary",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Torch device (default: cpu for deterministic debugging)",
    )
    return parser.parse_args()


def build_dataload_args(detector_size: str) -> SimpleNamespace:
    """Build DataLoad args for canonical refGeom smoke dataset.

    Mirrors the fixture setup from docs/data_dependency_manifest.md:34-54.
    """
    repo_root = Path(__file__).resolve().parents[4]

    if detector_size == "small":
        expt_name = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small.expt"
        refl_name = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small.refl"
        mask_path = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small_mask.pkl"
    else:
        expt_name = repo_root / "sp.proc" / "refGeom.expt"
        refl_name = repo_root / "sp.proc" / "refGeom.refl"
        mask_path = repo_root / "747_mask.pkl"

    mtz_file = repo_root / "scaled.mtz"

    # Validate paths
    for p, label in [
        (expt_name, "experiment"),
        (refl_name, "reflections"),
        (mask_path, "mask"),
        (mtz_file, "MTZ"),
    ]:
        if not p.exists():
            raise FileNotFoundError(f"{label} asset not found: {p}")

    return SimpleNamespace(
        exptName=str(expt_name),
        reflName=str(refl_name),
        maskFile=str(mask_path),
        mtzFile=str(mtz_file),
        mtzCol="I(+),SIGI(+),I(-),SIGI(-)",  # Use intensity columns from scaled.mtz
        exptIdx=0,  # Load first experiment
        adu_per_photon=None,
        sigma_map=None,
        config_path=None,
        hkl_source_path=None,  # Let mapping context pick refined or raw
        calibration_config_path=None,  # No calibration override for baseline probe
    )


def compare_reciprocal_lattices(
    dxtbx_crystal,
    dxtbx_experiment,
    calibration: dict | None,
    device: str,
) -> dict:
    """Compare dxtbx A* against nanobrag_torch Crystal reciprocal lattice at zero point.

    Args:
        dxtbx_crystal: dxtbx Crystal object from DataLoad
        dxtbx_experiment: dxtbx Experiment object from DataLoad
        calibration: Optional calibration dict (for N_cells if present)
        device: Torch device string

    Returns:
        Dictionary with comparison metrics:
            - dxtbx_A_star: 3x3 array (columns = a*, b*, c* from dxtbx)
            - nanobrag_A_star: 3x3 array (computed by nanobrag_torch Crystal)
            - max_abs_diff: scalar max|ΔA*|
            - mean_abs_diff: scalar mean|ΔA*|
            - per_column_max: (3,) array of max|Δ| per reciprocal column
            - per_column_mean: (3,) array of mean|Δ| per reciprocal column
    """
    # Extract dxtbx A* (authoritative per spec-db-core.md:66)
    A_dxtbx_flat = dxtbx_crystal.get_A()
    A_dxtbx = np.array(A_dxtbx_flat).reshape(3, 3)  # columns = (a*, b*, c*)

    # Build CrystalConfig respecting calibration metadata
    N_cells = None
    apply_n_cells = True
    if calibration is not None and "N_cells" in calibration:
        N_cells = calibration["N_cells"]

    crystal_config, n_cells_applied = create_crystal_config(
        crystal=dxtbx_crystal,
        experiment=dxtbx_experiment,
        N_cells=N_cells,
        apply_n_cells=apply_n_cells,
        crystal_overrides=None,  # Zero-point: no refinement deltas
        misset_deg_override=None,  # Zero-point: no misset
    )

    # Instantiate nanobrag_torch Crystal
    crystal_torch = Crystal(crystal_config, device=device)

    # Compute reciprocal lattice at zero point
    # Crystal exposes a_star, b_star, c_star properties; build A* as columns
    a_star = crystal_torch.a_star.detach().cpu().numpy()  # (3,)
    b_star = crystal_torch.b_star.detach().cpu().numpy()  # (3,)
    c_star = crystal_torch.c_star.detach().cpu().numpy()  # (3,)
    A_torch = np.column_stack([a_star, b_star, c_star])  # (3, 3)

    # Compute deltas
    delta_A = A_torch - A_dxtbx
    max_abs_diff = float(np.max(np.abs(delta_A)))
    mean_abs_diff = float(np.mean(np.abs(delta_A)))

    # Per-column statistics (a*, b*, c*)
    per_column_max = np.max(np.abs(delta_A), axis=0)  # (3,)
    per_column_mean = np.mean(np.abs(delta_A), axis=0)  # (3,)

    return {
        "dxtbx_A_star": A_dxtbx.tolist(),
        "nanobrag_A_star": A_torch.tolist(),
        "delta_A_star": delta_A.tolist(),
        "max_abs_diff": max_abs_diff,
        "mean_abs_diff": mean_abs_diff,
        "per_column_max": per_column_max.tolist(),
        "per_column_mean": per_column_mean.tolist(),
        "n_cells_applied": n_cells_applied,
    }


def format_summary(metrics: dict, detector_size: str) -> str:
    """Format human-readable summary of A* comparison."""
    lines = [
        "# HKL Reciprocal Lattice Alignment Probe (ARCH-SIM-HKL-BOUNDS-001 Phase A.1)",
        "",
        f"Dataset: refGeom {detector_size}-detector smoke fixture",
        f"N_cells applied: {metrics['n_cells_applied']}",
        "",
        "## Reciprocal Lattice Matrix Comparison (A* columns = a*, b*, c*)",
        "",
        "dxtbx A* (authoritative):",
    ]
    A_dxtbx = np.array(metrics["dxtbx_A_star"])
    for i in range(3):
        lines.append(f"  [{A_dxtbx[i, 0]:12.8f}, {A_dxtbx[i, 1]:12.8f}, {A_dxtbx[i, 2]:12.8f}]")

    lines.append("")
    lines.append("nanobrag_torch A* (zero-point):")
    A_torch = np.array(metrics["nanobrag_A_star"])
    for i in range(3):
        lines.append(f"  [{A_torch[i, 0]:12.8f}, {A_torch[i, 1]:12.8f}, {A_torch[i, 2]:12.8f}]")

    lines.append("")
    lines.append("ΔA* = A*_torch - A*_dxtbx:")
    delta_A = np.array(metrics["delta_A_star"])
    for i in range(3):
        lines.append(f"  [{delta_A[i, 0]:12.8e}, {delta_A[i, 1]:12.8e}, {delta_A[i, 2]:12.8e}]")

    lines.extend([
        "",
        "## Summary Statistics (Å⁻¹)",
        f"max|ΔA*|:  {metrics['max_abs_diff']:.6e}",
        f"mean|ΔA*|: {metrics['mean_abs_diff']:.6e}",
        "",
        "Per-column max|Δ| (a*, b*, c*):",
        f"  a*: {metrics['per_column_max'][0]:.6e}",
        f"  b*: {metrics['per_column_max'][1]:.6e}",
        f"  c*: {metrics['per_column_max'][2]:.6e}",
        "",
        "Per-column mean|Δ| (a*, b*, c*):",
        f"  a*: {metrics['per_column_mean'][0]:.6e}",
        f"  b*: {metrics['per_column_mean'][1]:.6e}",
        f"  c*: {metrics['per_column_mean'][2]:.6e}",
        "",
        "## Acceptance Criterion (docs/spec-db-core.md:72)",
        f"Zero-point tolerance: max|ΔA*| ≤ 1e-6 Å⁻¹",
        f"Status: {'PASS' if metrics['max_abs_diff'] <= 1e-6 else 'FAIL'}",
        "",
    ])

    if metrics['max_abs_diff'] > 1e-6:
        lines.extend([
            "## Interpretation",
            f"The observed max|ΔA*| = {metrics['max_abs_diff']:.6e} exceeds the spec tolerance,",
            "indicating a reciprocal-space misalignment between dxtbx and nanobrag_torch at the",
            "Stage-A zero point. This explains the 0% HKL in-bounds coverage observed in",
            "DIAG-NANOBRAGG-OVERSAMPLE-001 Phase F.",
            "",
            "Next action: Phase B — isolate the transformation bug (MOSFLM injection, basis order,",
            "2π factor, or reciprocal tensor recomputation) inside create_crystal_config or",
            "nanobrag_torch.models.Crystal.",
        ])
    else:
        lines.extend([
            "## Interpretation",
            "Reciprocal lattice alignment is within spec tolerance. If HKL coverage issues persist,",
            "the root cause lies downstream (HKL grid indexing, structure-factor grid bounds, or",
            "mapping coordinate transforms).",
        ])

    return "\n".join(lines)


def main():
    """Main probe execution."""
    args = parse_args()

    # Create output directory
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[PROBE] ARCH-SIM-HKL-BOUNDS-001 Phase A.1 — Reciprocal Lattice Alignment")
    print(f"[PROBE] Detector size: {args.detector_size}")
    print(f"[PROBE] Device: {args.device}")
    print(f"[PROBE] Output directory: {args.out_dir}")
    print()

    # Build DataLoad for canonical refGeom smoke dataset
    try:
        dataload_args = build_dataload_args(args.detector_size)
        print(f"[PROBE] Loading DataLoad from {dataload_args.exptName}")
        dataload = DataLoad(dataload_args)
    except Exception as e:
        print(f"ERROR: DataLoad initialization failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Build mapping context to get calibration metadata
    print("[PROBE] Building mapping context...")
    try:
        context = build_mapping_stage_a_context(
            dataload,
            default_sigma_readout=3.0,
            device=args.device,
            apply_calibration_n_cells=True,
        )
        calibration = context.calibration
    except Exception as e:
        print(f"ERROR: Mapping context build failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Compare reciprocal lattices
    print("[PROBE] Comparing dxtbx A* vs nanobrag_torch reciprocal lattice...")
    try:
        metrics = compare_reciprocal_lattices(
            dxtbx_crystal=dataload.crystal,
            dxtbx_experiment=dataload.Expt,
            calibration=calibration,
            device=args.device,
        )
    except Exception as e:
        print(f"ERROR: Reciprocal lattice comparison failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Write JSON metrics
    metrics_path = args.out_dir / "hkl_alignment_metrics.json"
    print(f"[PROBE] Writing metrics to {metrics_path}")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    # Write human-readable summary
    summary_path = args.out_dir / "hkl_alignment_summary.txt"
    summary = format_summary(metrics, args.detector_size)
    print(f"[PROBE] Writing summary to {summary_path}")
    with open(summary_path, "w") as f:
        f.write(summary)

    # Print summary to stdout
    print()
    print(summary)

    # Exit with appropriate status
    if metrics["max_abs_diff"] > 1e-6:
        print(f"\n[PROBE] FAIL: max|ΔA*| = {metrics['max_abs_diff']:.6e} > 1e-6 Å⁻¹")
        sys.exit(1)
    else:
        print(f"\n[PROBE] PASS: max|ΔA*| = {metrics['max_abs_diff']:.6e} ≤ 1e-6 Å⁻¹")
        sys.exit(0)


if __name__ == "__main__":
    main()
