#!/usr/bin/env python3
"""
TORCH-REFINE-002E Phase A3 — Mapping Forward Model vs Stage-A Explicit Comparison.

Compare forward-model outputs between the mapping MOSFLM A* injection path
and the Stage-A explicit cell+misset parameterization (at zero deltas) on a
single panel to isolate whether the 2.6× chi-squared discrepancy originates
from encoding conventions or simulator numerical differences.

Artifacts:
    plans/active/TORCH-REFINE-002E/reports/<timestamp>/
    ├── forward_model_comparison.json
    ├── forward_model_comparison.log
    └── commands.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional

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
    derive_robust_misset,
)
from dbex.vis import build_mapping_stage_a_context  # type: ignore  # noqa: E402
from dbex.nanobrag_refinement import (  # type: ignore  # noqa: E402
    _compute_variance_weighted_loss,
)


@dataclass
class PathMetrics:
    """Metrics for a single forward model path."""

    chi_squared: float
    bragg_stack_shape: tuple
    bragg_stack_sum: float
    hkl_hits: int
    hkl_out_of_bounds: int


@dataclass
class ComparisonMetrics:
    """Per-pixel comparison metrics between two forward model paths."""

    bragg_diff_max: float
    bragg_diff_mean: float
    bragg_diff_median: float
    bragg_rel_diff_max: float
    bragg_rel_diff_mean: float
    chi_squared_diff_abs: float
    chi_squared_diff_rel: float


@dataclass
class ForwardModelComparisonSummary:
    """Complete Phase A3 comparison summary."""

    mode: str
    panel_id: int
    device: str
    mapping_path: PathMetrics
    stage_a_zero_path: PathMetrics
    comparison: ComparisonMetrics
    conclusion: str


def _build_dataload(repo_root: Path) -> DataLoad:
    """Construct a DataLoad instance for canonical refGeom assets."""
    sp_proc = repo_root / "sp.proc"

    # Use idx-0000_refined.expt (has refined geometry from mapping)
    expt = sp_proc / "idx-0000_refined.expt"
    refl = sp_proc / "idx-0000_indexed.refl"

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


def _simulate_mapping_path(
    dataload: DataLoad,
    panel_id: int,
    *,
    device_str: str = "cpu",
) -> tuple[np.ndarray, PathMetrics]:
    """
    Run the mapping MOSFLM A* path through nanobrag_torch simulator.

    Returns:
        (bragg_stack, metrics) where bragg_stack is [panel, slow, fast] numpy array.
    """
    # Build mapping context (reuses DB-AT-024 machinery)
    context = build_mapping_stage_a_context(
        dataload,
        default_sigma_readout=3.0,
        device=device_str,
    )

    # Extract the mapping Bragg stack (from simulate_forward_once)
    bragg_mapping = np.asarray(context.bragg_zero_iter, dtype=np.float32)

    # Compute chi-squared using variance-weighted loss
    import torch

    device = torch.device(device_str)
    dtype = torch.float32

    target_t = torch.tensor(context.inputs.target, device=device, dtype=dtype)
    sigma_t = torch.tensor(context.inputs.sigma_readout, device=device, dtype=dtype)
    mask_t = torch.tensor(context.inputs.loss_mask, device=device, dtype=torch.bool)
    bragg_t = torch.tensor(bragg_mapping, device=device, dtype=dtype)
    sigma_floor_sq_tensor = torch.tensor(
        float(context.sigma_floor_value**2),
        device=device,
        dtype=dtype,
    )

    chi_sq_t, _, _, _ = _compute_variance_weighted_loss(
        bragg_t,
        target_t,
        mask_t,
        sigma_t,
        sigma_floor_sq_tensor,
    )

    chi_squared = float(chi_sq_t.item())

    # HKL grid stats (placeholder for now; actual HKL tracking requires simulator instrumentation)
    # For Phase A3, we focus on pixel-level comparisons
    hkl_hits = len(context.hkl_indices) if context.hkl_indices is not None else 0
    hkl_out_of_bounds = 0  # Not tracked in current mapping path

    metrics = PathMetrics(
        chi_squared=chi_squared,
        bragg_stack_shape=tuple(bragg_mapping.shape),
        bragg_stack_sum=float(np.sum(bragg_mapping)),
        hkl_hits=hkl_hits,
        hkl_out_of_bounds=hkl_out_of_bounds,
    )

    return bragg_mapping, metrics


def _simulate_stage_a_zero_path(
    dataload: DataLoad,
    panel_id: int,
    *,
    device_str: str = "cpu",
) -> tuple[np.ndarray, PathMetrics]:
    """
    Run the Stage-A explicit cell+misset path (at zero deltas) through nanobrag_torch.

    Uses GEOMETRY-003 baseline misset derived from dxtbx A* matrix.

    Returns:
        (bragg_stack, metrics) where bragg_stack is [panel, slow, fast] numpy array.
    """
    import torch
    from nanobrag_torch.config import BeamConfig, CrystalConfig, DetectorConfig
    from nanobrag_torch.models.experiment import ExperimentModel

    device = torch.device(device_str)
    dtype = torch.float32

    # Build HKL grid (same as mapping path)
    hkl_grid, hkl_metadata, _asu_map = build_structure_factor_grid(
        dataload.F.indices(),
        dataload.F.data(),
        device=device,
        halo=False,
    )

    # Get crystal, detector, beam from dxtbx
    crystal_dxtbx = dataload.Expt.crystal
    detector = dataload.Expt.detector
    beam = dataload.Expt.beam

    # Derive baseline misset using GEOMETRY-003 (B_ideal-based alignment)
    misset_deg = derive_robust_misset(
        crystal_dxtbx,
        crystal_nanobrag_default=None,
        device=device,
        dtype=dtype,
        b_ideal_override=None,
    )

    # Build Stage-A crystal config with explicit cell+misset (zero deltas)
    # Use dxtbx unit cell parameters as the baseline
    a, b, c, alpha, beta, gamma = crystal_dxtbx.get_unit_cell().parameters()

    crystal_config, _ = create_crystal_config(
        crystal_dxtbx,
        device=device,
        dtype=dtype,
        use_mosflm_a_star=False,  # Explicit cell+misset path
        misset_deg=misset_deg.cpu().numpy() if isinstance(misset_deg, torch.Tensor) else misset_deg,
        apply_n_cells=False,  # SCALE-005 guard
    )

    # Build detector and beam configs for the specified panel
    beam_config = create_beam_config(beam, device=device, dtype=dtype)

    # For Phase A3, we run on a single panel to isolate differences
    # Build detector config for the target panel only
    panel_detector = detector[panel_id : panel_id + 1]
    detector_config = create_detector_config(
        panel_detector,
        dataload.trusted_mask[panel_id : panel_id + 1],
        device=device,
        dtype=dtype,
    )

    # Instantiate ExperimentModel and run forward pass
    exp_model = ExperimentModel(
        crystal_config=crystal_config,
        detector_config=detector_config,
        beam_config=beam_config,
        device=device,
        dtype=dtype,
        param_init="frozen",
        hkl_data=hkl_grid,
        hkl_metadata=hkl_metadata,
    )

    with torch.no_grad():
        panel_output = exp_model()  # [slow, fast] tensor for the single panel
        # Scale by sqrt(spot_scale) if needed (following Stage A closure convention)
        # For Phase A3, we use the default spot_scale from the crystal config
        # and apply zero log_scale (exp(0) = 1.0)
        bragg_single_panel = panel_output.cpu().numpy().astype(np.float32)

    # Expand to [panel, slow, fast] shape for consistency
    bragg_stack = np.expand_dims(bragg_single_panel, axis=0)

    # Compute chi-squared using variance-weighted loss
    # Need target/sigma for the specified panel
    target_panel = dataload.data[panel_id : panel_id + 1]
    sigma_panel = np.full_like(target_panel, 3.0, dtype=np.float32)  # Default sigma
    mask_panel = dataload.trusted_mask[panel_id : panel_id + 1]

    target_t = torch.tensor(target_panel, device=device, dtype=dtype)
    sigma_t = torch.tensor(sigma_panel, device=device, dtype=dtype)
    mask_t = torch.tensor(mask_panel, device=device, dtype=torch.bool)
    bragg_t = torch.tensor(bragg_stack, device=device, dtype=dtype)
    sigma_floor_sq_tensor = torch.tensor(1.0, device=device, dtype=dtype)  # sigma_floor = 1.0

    chi_sq_t, _, _, _ = _compute_variance_weighted_loss(
        bragg_t,
        target_t,
        mask_t,
        sigma_t,
        sigma_floor_sq_tensor,
    )

    chi_squared = float(chi_sq_t.item())

    # HKL grid stats (placeholder)
    hkl_hits = hkl_grid.shape[0] if hkl_grid is not None else 0
    hkl_out_of_bounds = 0  # Not tracked in current implementation

    metrics = PathMetrics(
        chi_squared=chi_squared,
        bragg_stack_shape=tuple(bragg_stack.shape),
        bragg_stack_sum=float(np.sum(bragg_stack)),
        hkl_hits=hkl_hits,
        hkl_out_of_bounds=hkl_out_of_bounds,
    )

    return bragg_stack, metrics


def _compute_comparison(
    bragg_mapping: np.ndarray,
    bragg_stage_a: np.ndarray,
    chi_mapping: float,
    chi_stage_a: float,
) -> ComparisonMetrics:
    """Compute pixel-level and chi-squared comparison metrics."""
    bragg_diff = np.abs(bragg_mapping.astype(np.float64) - bragg_stage_a.astype(np.float64))
    bragg_rel_diff = bragg_diff / (bragg_mapping.astype(np.float64) + 1.0)  # Avoid divide-by-zero

    bragg_diff_max = float(np.max(bragg_diff))
    bragg_diff_mean = float(np.mean(bragg_diff))
    bragg_diff_median = float(np.median(bragg_diff))

    bragg_rel_diff_max = float(np.max(bragg_rel_diff))
    bragg_rel_diff_mean = float(np.mean(bragg_rel_diff))

    chi_squared_diff_abs = float(chi_stage_a - chi_mapping)
    chi_squared_diff_rel = (
        chi_squared_diff_abs / chi_mapping if chi_mapping != 0.0 else float("nan")
    )

    return ComparisonMetrics(
        bragg_diff_max=bragg_diff_max,
        bragg_diff_mean=bragg_diff_mean,
        bragg_diff_median=bragg_diff_median,
        bragg_rel_diff_max=bragg_rel_diff_max,
        bragg_rel_diff_mean=bragg_rel_diff_mean,
        chi_squared_diff_abs=chi_squared_diff_abs,
        chi_squared_diff_rel=chi_squared_diff_rel,
    )


def main():
    parser = argparse.ArgumentParser(
        description="TORCH-REFINE-002E Phase A3 — Mapping vs Stage-A forward model comparison"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="Torch device (default: cpu)",
    )
    parser.add_argument(
        "--panel-id",
        type=int,
        default=0,
        help="Panel ID to simulate (default: 0)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for artifacts",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build DataLoad
    dataload = _build_dataload(REPO_ROOT)

    print(f"Running Phase A3 forward model comparison:")
    print(f"  Device: {args.device}")
    print(f"  Panel ID: {args.panel_id}")
    print(f"  Output directory: {out_dir}")

    # Run mapping path
    print("\n[1/2] Simulating mapping MOSFLM A* path...")
    bragg_mapping, metrics_mapping = _simulate_mapping_path(
        dataload,
        args.panel_id,
        device_str=args.device,
    )
    print(f"  χ² (mapping): {metrics_mapping.chi_squared:.4e}")
    print(f"  Bragg sum (mapping): {metrics_mapping.bragg_stack_sum:.4e}")

    # Run Stage-A zero path
    print("\n[2/2] Simulating Stage-A explicit cell+misset path (zero deltas)...")
    bragg_stage_a, metrics_stage_a = _simulate_stage_a_zero_path(
        dataload,
        args.panel_id,
        device_str=args.device,
    )
    print(f"  χ² (Stage-A zero): {metrics_stage_a.chi_squared:.4e}")
    print(f"  Bragg sum (Stage-A zero): {metrics_stage_a.bragg_stack_sum:.4e}")

    # Compute comparisons
    print("\n[3/3] Computing pixel-level comparisons...")
    comparison = _compute_comparison(
        bragg_mapping,
        bragg_stage_a,
        metrics_mapping.chi_squared,
        metrics_stage_a.chi_squared,
    )
    print(f"  |Δ Bragg| max: {comparison.bragg_diff_max:.4e} photons")
    print(f"  |Δ Bragg| mean: {comparison.bragg_diff_mean:.4e} photons")
    print(f"  |Δ χ²|: {comparison.chi_squared_diff_abs:.4e}")
    print(f"  Δ χ² (relative): {comparison.chi_squared_diff_rel:.4e}")

    # Determine conclusion
    if (
        comparison.bragg_diff_max < 1e-6
        and abs(comparison.chi_squared_diff_abs) < 1e-6
    ):
        conclusion = "identical"
    else:
        conclusion = "differs_numerically"

    print(f"\n[CONCLUSION] Forward models: {conclusion}")

    # Build summary
    summary = ForwardModelComparisonSummary(
        mode="forward_model_comparison",
        panel_id=args.panel_id,
        device=args.device,
        mapping_path=metrics_mapping,
        stage_a_zero_path=metrics_stage_a,
        comparison=comparison,
        conclusion=conclusion,
    )

    # Write JSON
    json_path = out_dir / "forward_model_comparison.json"
    with open(json_path, "w") as f:
        json.dump(asdict(summary), f, indent=2)

    print(f"\n[ARTIFACTS]")
    print(f"  JSON summary: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
