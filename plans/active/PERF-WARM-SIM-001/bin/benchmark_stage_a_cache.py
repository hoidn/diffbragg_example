#!/usr/bin/env python
"""
Stage A warm cache benchmark script (PERF-WARM-SIM-001).

Compares Stage A refinement performance with warm cache (default) vs cold baseline
(per-iteration reconstruction) using identical inputs and deterministic execution.

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \\
    python plans/active/PERF-WARM-SIM-001/bin/benchmark_stage_a_cache.py \\
        --modes warm cold \\
        --artifacts plans/active/PERF-WARM-SIM-001/reports/2025-11-06T090721Z/
        [--allow-cold-roi]  # Opt-in ROI sampling for cold mode (defaults to panel rendering)

Outputs:
    - JSON summary: <artifacts>/benchmark_summary.json
    - Human-readable report: <artifacts>/benchmark_report.txt
    - Per-mode perf counters: <artifacts>/{warm,cold}_perf_counters.json

Requirements:
    - refGeom.refl (generated via dials.stills_process)
    - CPU-only determinism via NANOBRAGG_DISABLE_COMPILE=1
    - KMP_DUPLICATE_LIB_OK=TRUE for OpenMP compatibility

Exit codes:
    0: Success
    1: Benchmark failure (exception or inconsistent results)
    2: Missing required inputs
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Prepend repo root to sys.path to ensure we import workspace dbex, not installed wheel
_repo_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(_repo_root))

import torch
import numpy as np


def load_refgeom_dataset():
    """
    Load canonical refGeom dataset for benchmarking.

    Returns:
        DataLoad object with refGeom assets

    Raises:
        FileNotFoundError: If refGeom.refl is missing
    """
    from argparse import Namespace
    from dbex.data_load import DataLoad

    repo_root = Path(__file__).parent.parent.parent.parent.parent
    refl_path = repo_root / "refGeom.refl"

    if not refl_path.exists():
        raise FileNotFoundError(
            f"refGeom.refl not found at {refl_path}; "
            "see README.md Step 5 for generation"
        )

    args = Namespace(
        exptName=str(repo_root / "refGeom.expt"),
        reflName=str(refl_path),
        exptIdx=0,
        maskFile=str(repo_root / "747_mask.pkl"),
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF"
    )

    return DataLoad(args)


def create_perturbed_crystal(crystal):
    """
    Create deterministically perturbed crystal for reproducible refinement test.

    Applies +2/+1/+1% cell stretch and +1.5° Z-axis misset to provide headroom
    for Stage A to demonstrate refinement capability with identical inputs across
    warm/cold runs.

    Args:
        crystal: dxtbx Crystal object

    Returns:
        Perturbed dxtbx Crystal object
    """
    from dxtbx.model import Crystal
    from cctbx import uctbx
    from scitbx.matrix import sqr
    import math

    # Extract baseline cell parameters
    base_cell = crystal.get_unit_cell().parameters()

    # Apply deterministic cell stretch
    perturbed_a = base_cell[0] * 1.02  # +2% on a-axis
    perturbed_b = base_cell[1] * 1.01  # +1% on b-axis
    perturbed_c = base_cell[2] * 1.01  # +1% on c-axis
    perturbed_alpha = base_cell[3]  # unchanged
    perturbed_beta = base_cell[4]   # unchanged
    perturbed_gamma = base_cell[5]  # unchanged

    # Create new crystal with original real space vectors
    perturbed_crystal = Crystal(
        real_space_a=crystal.get_real_space_vectors()[0],
        real_space_b=crystal.get_real_space_vectors()[1],
        real_space_c=crystal.get_real_space_vectors()[2],
        space_group=crystal.get_space_group()
    )

    # Set perturbed unit cell
    perturbed_uc = uctbx.unit_cell((perturbed_a, perturbed_b, perturbed_c,
                                     perturbed_alpha, perturbed_beta, perturbed_gamma))
    perturbed_crystal.set_unit_cell(perturbed_uc)

    # Apply small Z-axis rotation (+1.5° misorientation)
    misset_z_deg = 1.5
    misset_z_rad = misset_z_deg * (math.pi / 180.0)

    # Rotation matrix around Z-axis
    cos_z = math.cos(misset_z_rad)
    sin_z = math.sin(misset_z_rad)
    rotation_z = sqr([
        cos_z, -sin_z, 0.0,
        sin_z,  cos_z, 0.0,
        0.0,    0.0,   1.0
    ])

    # Apply rotation to U matrix
    U_tuple = perturbed_crystal.get_U()
    U = sqr(U_tuple)
    U_perturbed = rotation_z * U
    perturbed_crystal.set_U(U_perturbed)

    return perturbed_crystal


def run_stage_a_benchmark(mode: str, DL, perturbed_crystal, artifacts_dir: Path, allow_cold_roi: bool = False):
    """
    Run Stage A refinement with specified cache mode.

    Args:
        mode: "warm" or "cold"
        DL: DataLoad object with refGeom dataset
        perturbed_crystal: Perturbed crystal for refinement
        artifacts_dir: Directory for output artifacts

    Returns:
        dict: Benchmark results with timings and telemetry
    """
    from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig
    from dbex.nanobrag_bridge import build_structure_factor_grid
    from dbex.refinement.inputs import prepare_refinement_inputs

    # Build HKL grid (shared across modes)
    hkl_indices = DL.F.indices()
    hkl_amplitudes = DL.F.data()
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=torch.device('cpu'),
        halo=True  # Per REFINE-005, Stage A uses haloed grid
    )

    # Build trusted masks
    detector = DL.Expt.detector
    n_panels = len(detector)
    trusted_masks = []
    for pid in range(n_panels):
        panel = detector[pid]
        image_size = panel.get_image_size()
        mask = np.ones(image_size[::-1], dtype=bool)  # (slow, fast)
        trusted_masks.append(mask)

    # Prepare refinement inputs
    inputs = prepare_refinement_inputs(
        data=DL.data,
        background_image=DL.background_image,
        trusted_mask=trusted_masks,
        bbox=DL.bbox,
        pids=DL.pids,
        detector=DL.Expt.detector,
        adu_per_photon=None  # ADU mode with learnable scale
    )

    # Configure refinement
    is_warm_mode = (mode == "warm")
    config = RefinementConfig(
        enable_stage_a_warm_cache=is_warm_mode,
        enable_hkl_interpolation=True,  # Per REFINE-005
        max_iter=30,
        history_size=10,
        min_loss_improvement=0.002,  # 0.2% gate per REFINE-004
        device="cpu",
        dtype=torch.float32
    )
    if not is_warm_mode:
        if allow_cold_roi:
            config.allow_cold_stage_a_roi_mode = True
        else:
            config.enable_stage_a_roi_mode = False

    # Time Stage A execution
    t0 = time.perf_counter()
    bragg_refined, telemetry_dict = run_nanobrag_refinement(
        inputs=inputs,
        detector=DL.detector,
        beam=DL.beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config
    )
    elapsed_sec = time.perf_counter() - t0

    # Extract telemetry
    stage_a_telem = telemetry_dict["A"]
    perf_counters = stage_a_telem.perf_counters or {}

    # Extract forward timing from nested dict structure
    forward_time_ms = perf_counters.get("forward_time_ms", {})

    results = {
        "mode": mode,
        "cache_mode": perf_counters.get("cache_mode", "unknown"),
        "wall_clock_sec": elapsed_sec,
        "closure_evals": perf_counters.get("closure_evals", 0),
        "validation_runs": perf_counters.get("validation_runs", 0),
        "forward_time_ms_mean": forward_time_ms.get("mean", 0.0),
        "forward_time_ms_total": forward_time_ms.get("total", 0.0),
        "lbfgs_iterations": len(stage_a_telem.loss_trace_sample),
        "final_loss": stage_a_telem.best_loss_full[0],
        "status": stage_a_telem.status,
        "param_deltas": stage_a_telem.param_deltas
    }

    # Write per-mode perf counters
    perf_path = artifacts_dir / f"{mode}_perf_counters.json"
    with open(perf_path, 'w') as f:
        json.dump(perf_counters, f, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Stage A warm cache vs cold baseline"
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["warm", "cold"],
        default=["warm", "cold"],
        help="Cache modes to benchmark"
    )
    parser.add_argument(
        "--artifacts",
        type=Path,
        required=True,
        help="Artifacts directory for outputs"
    )
    parser.add_argument(
        "--allow-cold-roi",
        action="store_true",
        help="Allow ROI sampling in cold mode (defaults to panel rendering for control runs)"
    )
    args = parser.parse_args()

    artifacts_dir = args.artifacts
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Load dataset
        print("Loading refGeom dataset...")
        DL = load_refgeom_dataset()

        # Create perturbed crystal (shared across modes for parity)
        perturbed_crystal = create_perturbed_crystal(DL.crystal)

        # Run benchmarks
        results = {}
        for mode in args.modes:
            print(f"\n{'='*60}")
            print(f"Running {mode.upper()} mode benchmark...")
            print(f"{'='*60}\n")

            results[mode] = run_stage_a_benchmark(
                mode,
                DL,
                perturbed_crystal,
                artifacts_dir,
                allow_cold_roi=args.allow_cold_roi,
            )

            print(f"\n{mode.upper()} results:")
            print(f"  Wall clock: {results[mode]['wall_clock_sec']:.2f}s")
            print(f"  Closure evals: {results[mode]['closure_evals']}")
            print(f"  Final loss: {results[mode]['final_loss']:.6f}")
            print(f"  Status: {results[mode]['status']}")

        # Compute speedup if both modes ran
        if "warm" in results and "cold" in results:
            speedup = results["cold"]["wall_clock_sec"] / results["warm"]["wall_clock_sec"]
            print(f"\n{'='*60}")
            print(f"SPEEDUP: {speedup:.2f}× (cold={results['cold']['wall_clock_sec']:.2f}s / warm={results['warm']['wall_clock_sec']:.2f}s)")
            print(f"{'='*60}\n")

            results["speedup"] = speedup

        # Write summary JSON
        summary_path = artifacts_dir / "benchmark_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(results, f, indent=2)

        # Write human-readable report
        report_path = artifacts_dir / "benchmark_report.txt"
        with open(report_path, 'w') as f:
            f.write("Stage A Warm Cache Benchmark Results\n")
            f.write("=" * 60 + "\n\n")

            for mode in args.modes:
                r = results[mode]
                f.write(f"{mode.upper()} MODE:\n")
                f.write(f"  Wall clock: {r['wall_clock_sec']:.2f}s\n")
                f.write(f"  Closure evaluations: {r['closure_evals']}\n")
                f.write(f"  Validation runs: {r['validation_runs']}\n")
                f.write(f"  Forward time (mean): {r['forward_time_ms_mean']:.2f}ms\n")
                f.write(f"  Forward time (total): {r['forward_time_ms_total']:.2f}ms\n")
                f.write(f"  LBFGS iterations: {r['lbfgs_iterations']}\n")
                f.write(f"  Final loss: {r['final_loss']:.6f}\n")
                f.write(f"  Status: {r['status']}\n")
                f.write(f"  Param deltas: {r['param_deltas']}\n")
                f.write("\n")

            if "speedup" in results:
                f.write(f"SPEEDUP: {results['speedup']:.2f}×\n")
                f.write(f"  (cold={results['cold']['wall_clock_sec']:.2f}s / warm={results['warm']['wall_clock_sec']:.2f}s)\n")

        print(f"\nArtifacts written to {artifacts_dir}/")
        print(f"  - benchmark_summary.json")
        print(f"  - benchmark_report.txt")
        for mode in args.modes:
            print(f"  - {mode}_perf_counters.json")

        return 0

    except Exception as e:
        print(f"\nERROR: Benchmark failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
