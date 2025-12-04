#!/usr/bin/env python
"""
Stage A baseline telemetry thin wrapper (ARCH-PROBE-FREEZE-001 Phase B).

Minimal wrapper over RefinementEngine that enables Stage A baseline metrics collection
via config.enable_stage_a_baseline_metrics=True and dumps the resulting artifact bundle.

This script replaces the 2865-line shadow pipeline with a thin wrapper that:
(1) Loads canonical refGeom dataset via DataLoad/prepare_refinement_inputs,
(2) Configures Stage A with the new baseline metrics flag + output path,
(3) Runs RefinementEngine with Stage A only (no B/C),
(4) Writes out StageAArtifacts.baseline_metrics (masked/unmasked means, chi²/px, ROI Pearson).

No simulator/ROI/mapping math duplication — all semantics live in production code.

Usage:
    AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \\
    DBEX_SMOKE_SIGMA_SOURCE=cli_override \\
    DBEX_SMOKE_DETECTOR_SIZE=small \\
    KMP_DUPLICATE_LIB_OK=TRUE \\
    NANOBRAGG_DISABLE_COMPILE=1 \\
    python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py \\
        --output plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-28T010000Z/stage_a_baseline.json

References:
    - input.md Do Now (2025-12-28T010000Z)
    - plans/active/ARCH-PROBE-FREEZE-001/implementation.md Phase B
    - docs/architecture/data_telemetry_flow.md:40-120 (Stage A telemetry ownership)
    - prompts/supervisor.md:272-287 (thin-wrapper policy)
"""

import argparse
import json
import os
import sys
from pathlib import Path

import torch

from dbex.data_load import DataLoad
from dbex.refinement.config import RefinementConfig
from dbex.refinement.context import build_refinement_context
from dbex.refinement.engine import RefinementEngine
from dbex.refinement.inputs import prepare_refinement_inputs
from dbex.refinement.stage_a import StageA


def get_refgeom_dataload():
    """
    Load refGeom dataset for refinement tests.

    Honors environment variables:
    - DBEX_SMOKE_DETECTOR_SIZE: "small" or "full" (default: "small")
    - DBEX_SMOKE_CALIB_PATH: Override calibration config path
    - DBEX_SMOKE_HKL_PATH: Override HKL MTZ path
    - DBEX_SMOKE_SIGMA_SOURCE: "cli_override" or "metadata" (default: "cli_override")

    Returns:
        DataLoad instance with refGeom experiment/reflections/MTZ/mask loaded.
    """
    repo_root = Path(__file__).parent.parent.parent.parent.parent

    # Determine detector size from environment variable
    detector_size = os.environ.get("DBEX_SMOKE_DETECTOR_SIZE", "small")

    if detector_size == "small":
        smoke_dir = repo_root / "sp.proc" / "refGeom_small"
    elif detector_size == "full":
        smoke_dir = repo_root / "sp.proc" / "refGeom"
    else:
        raise ValueError(f"Invalid DBEX_SMOKE_DETECTOR_SIZE: {detector_size}. Must be 'small' or 'full'.")

    # Resolve calibration config path
    calib_env = os.environ.get("DBEX_SMOKE_CALIB_PATH")
    if calib_env:
        calib_config = Path(calib_env)
    else:
        # Default: detector-size-specific calibration in .proc_assets
        calib_config = smoke_dir / ".proc_assets" / f"calibration_refGeom_{detector_size}.json"

    # Resolve HKL MTZ path (prefer refined when calibration exists)
    hkl_env = os.environ.get("DBEX_SMOKE_HKL_PATH")
    if hkl_env:
        mtz_file = Path(hkl_env)
        mtz_col = "I(+),SIGI(+),I(-),SIGI(-)"  # Assume raw columns when overridden
    else:
        if calib_config.exists():
            # Prefer refined MTZ when calibration metadata exists
            mtz_file = smoke_dir / "refined.mtz"
            mtz_col = "Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)"
        else:
            # Fallback: scaled MTZ with raw Bijvoet columns
            mtz_file = smoke_dir / "scaled.mtz"
            mtz_col = "I(+),SIGI(+),I(-),SIGI(-)"

    # Load via DataLoad
    expt_file = smoke_dir / "indexed.expt"
    refl_file = smoke_dir / "indexed.refl"
    mask_file = smoke_dir / "mask.pickle"

    dataload = DataLoad(
        expt_file=str(expt_file),
        refl_file=str(refl_file),
        mask_file=str(mask_file),
        mtz_file=str(mtz_file),
        mtz_col=mtz_col,
        calib_file=str(calib_config) if calib_config.exists() else None,
    )

    # Tag with detector size for downstream use
    dataload.detector_size = detector_size

    return dataload


def create_perturbed_geometry(crystal, detector, beam):
    """
    Create deterministically perturbed copies of crystal/detector/beam for Stage A smoke testing.

    Simplified version from test_torch_refine_smoke.py.
    """
    import copy
    from math import cos, radians, sin

    from cctbx.uctbx import unit_cell
    from scitbx import matrix

    # Deep copy to avoid mutating baseline
    crystal_perturbed = copy.deepcopy(crystal)
    detector_perturbed = copy.deepcopy(detector)
    beam_perturbed = copy.deepcopy(beam)

    # Perturb unit cell (+2% a-axis, +1% b/c-axes)
    a, b, c, alpha, beta, gamma = crystal_perturbed.get_unit_cell().parameters()
    perturbed_cell = unit_cell((a * 1.02, b * 1.01, c * 1.01, alpha, beta, gamma))
    crystal_perturbed.set_unit_cell(perturbed_cell)

    # Perturb orientation (+1.5° misset along Z-axis)
    U_matrix = matrix.sqr(crystal_perturbed.get_U())
    angle_rad = radians(1.5)
    Rz = matrix.sqr((cos(angle_rad), -sin(angle_rad), 0,
                     sin(angle_rad),  cos(angle_rad), 0,
                     0, 0, 1))
    U_perturbed = Rz * U_matrix
    crystal_perturbed.set_U(U_perturbed)

    return crystal_perturbed, detector_perturbed, beam_perturbed


def main():
    parser = argparse.ArgumentParser(
        description="Stage A baseline telemetry thin wrapper (ARCH-PROBE-FREEZE-001 Phase B)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output JSON path for baseline metrics",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0" if torch.cuda.is_available() else "cpu",
        help="Device for computation (default: cuda:0 if available, else cpu)",
    )
    parser.add_argument(
        "--geometry-mode",
        type=str,
        choices=["perturbed", "baseline"],
        default="perturbed",
        help="Geometry mode: 'perturbed' applies smoke perturbations (default), 'baseline' uses mapping geometry",
    )
    args = parser.parse_args()

    # Resolve device
    device_obj = torch.device(args.device)
    device = str(device_obj)

    print(f"[Stage A Baseline Wrapper] Loading refGeom dataset...")
    dataload = get_refgeom_dataload()

    # Extract geometry
    detector = dataload.get_detector()
    beam = dataload.get_beam()
    crystal = dataload.get_crystal()

    # Apply geometry perturbation if requested
    if args.geometry_mode == "perturbed":
        print(f"[Stage A Baseline Wrapper] Applying perturbed geometry...")
        crystal, detector, beam = create_perturbed_geometry(crystal, detector, beam)
        baseline_crystal = dataload.get_crystal()
        baseline_detector = dataload.get_detector()
    else:
        print(f"[Stage A Baseline Wrapper] Using baseline (mapping) geometry...")
        baseline_crystal = None
        baseline_detector = None

    # Prepare refinement inputs
    print(f"[Stage A Baseline Wrapper] Preparing refinement inputs...")
    sigma_source = os.environ.get("DBEX_SMOKE_SIGMA_SOURCE", "cli_override")
    default_sigma_readout = 3.0 if sigma_source == "cli_override" else None

    refinement_inputs = prepare_refinement_inputs(
        dataload,
        detector=detector,
        beam=beam,
        crystal=crystal,
        device=device,
        default_sigma_readout=default_sigma_readout,
    )

    # Build HKL grid
    print(f"[Stage A Baseline Wrapper] Building HKL grid...")
    from dbex.nanobrag_bridge import build_structure_factor_grid
    hkl_grid, hkl_metadata = build_structure_factor_grid(
        crystal=crystal,
        mtz_file=dataload.mtz_file,
        mtz_col=dataload.mtz_col,
        device=device,
    )

    # Configure RefinementEngine with Stage A baseline metrics enabled
    print(f"[Stage A Baseline Wrapper] Configuring RefinementEngine with baseline metrics enabled...")
    config = RefinementConfig(
        device=device,
        dtype=torch.float32,
        enable_hkl_interpolation=False,  # Nearest-neighbor for DB-AT-028/029
        enable_stage_a_warm_cache=True,
        enable_stage_a_baseline_metrics=True,  # Enable baseline metrics collection
        stage_a_baseline_metrics_path=str(args.output),  # Write JSON to output path
        enable_stage_b=False,  # Stage A only
        enable_stage_c=False,
        calibration_metadata=dataload.calibration_metadata if hasattr(dataload, 'calibration_metadata') else None,
        sigma_readout_reference_value=default_sigma_readout,
    )

    # Build refinement context
    print(f"[Stage A Baseline Wrapper] Building refinement context...")
    context = build_refinement_context(
        refinement_inputs=refinement_inputs,
        detector=detector,
        beam=beam,
        crystal=crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,
    )

    # Initialize RefinementEngine with Stage A only
    stage_a = StageA()
    engine = RefinementEngine(stages=[stage_a], config=config)

    # Run refinement (Stage A only)
    print(f"[Stage A Baseline Wrapper] Running Stage A refinement...")
    result = engine.run(context)

    # Extract Stage A artifacts with baseline metrics
    stage_a_artifacts = result.artifacts.get("stage_a")
    if stage_a_artifacts is None or stage_a_artifacts.baseline_metrics is None:
        print(f"[Stage A Baseline Wrapper] ERROR: Stage A artifacts or baseline_metrics missing!")
        return 1

    print(f"[Stage A Baseline Wrapper] Stage A baseline metrics collected successfully.")
    print(f"  Masked chi²/px: {stage_a_artifacts.baseline_metrics['chi_squared']['chi_squared_per_pixel_initial']:.2e}")
    print(f"  Masked pixels: {stage_a_artifacts.baseline_metrics['chi_squared']['n_masked_pixels']}")
    print(f"  Median ROI Pearson: {stage_a_artifacts.baseline_metrics['roi_correlations']['median_roi_pearson']:.4f}")
    print(f"  N ROIs with correlations: {stage_a_artifacts.baseline_metrics['roi_correlations']['n_rois_with_correlations']}")

    # Baseline metrics JSON already written by StageA.run
    print(f"[Stage A Baseline Wrapper] Baseline metrics written to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
