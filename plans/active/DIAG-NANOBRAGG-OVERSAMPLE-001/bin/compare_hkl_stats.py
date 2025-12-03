#!/usr/bin/env python
"""
Compare HKL coverage statistics from simulate_forward_once.

DIAG-NANOBRAGG-OVERSAMPLE-001 Phase F (2025-12-09)

Purpose:
    Collect HKL coverage statistics from simulate_forward_once to determine
    whether queries fall within the structure-factor grid bounds.

Strategy:
    - Load smoke fixtures via DataLoad
    - Run simulate_forward_once(debug_config={'collect_hkl_stats': True})
    - Emit hkl_stats_comparison.json summarizing grid metadata vs. observed HKL ranges
      plus a prose summary.md

Findings Applied:
    - DIAG-OVERSAMPLE-001: Keeping detector/beam configs consistent
    - DIAG-UNIT-001: Retracted; focus on HKL coverage deltas instead
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

# Add repo root to path for dbex imports
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from dbex.data_load import DataLoad
from dbex.vis.mapping import build_mapping_stage_a_context
from dbex.nanobrag_bridge import simulate_forward_once, build_structure_factor_grid
from dbex.refinement.stage_a_utils import _build_stage_a_context
from dbex.refinement.config import RefinementConfig


def load_smoke_fixture(detector_size="small"):
    """
    Load smoke fixture data following canonical paths from data_dependency_manifest.md.

    Args:
        detector_size: "small" or "full"

    Returns:
        DataLoad object with Expt, bbox, trusted_mask, calibration_path
    """
    repo_root_path = Path(__file__).parent.parent.parent.parent.parent

    if detector_size == "small":
        smoke_data_dir = repo_root_path / "sp.proc" / "refGeom_small"
        expt_name = "refGeom_small.expt"
        refl_name = "refGeom_small.refl"
        mask_name = "refGeom_small_mask.pkl"
        calib_path = repo_root_path / "sp.proc" / "calibration" / "config_torch_smoke_small.json"
        refined_mtz = repo_root_path / "sp.proc" / "calibration" / "smoke_refined_structure_factors_small.mtz"
    else:
        smoke_data_dir = repo_root_path / "sp.proc"
        expt_name = "idx-0000_imported.expt"
        refl_name = "idx-0000_indexed.refl"
        mask_name = "idx-0000_mask.pkl"
        calib_path = repo_root_path / "sp.proc" / "calibration" / "config_torch_smoke.json"
        refined_mtz = repo_root_path / "sp.proc" / "calibration" / "smoke_refined_structure_factors.mtz"

    calibration_config_path = str(calib_path) if calib_path.exists() else None

    # Resolve HKL path (refined MTZ when calibration exists, else scaled.mtz)
    scaled_mtz = repo_root_path / "scaled.mtz"
    if refined_mtz.exists():
        hkl_source_path = refined_mtz
    else:
        hkl_source_path = scaled_mtz

    # Build args namespace following refgeom_dataload fixture pattern
    from argparse import Namespace
    args = Namespace(
        exptName=(smoke_data_dir / expt_name).as_posix(),
        reflName=(smoke_data_dir / refl_name).as_posix(),
        exptIdx=0,
        maskFile=(smoke_data_dir / mask_name).as_posix(),
        mtzFile=str(scaled_mtz),
        mtzCol="F,SIGF",
        hkl_source_path=str(hkl_source_path),
        calibration_config_path=calibration_config_path,
    )

    # Load via DataLoad
    loader = DataLoad(args)
    return loader


def aggregate_panel_stats(per_panel_stats):
    """
    Aggregate per-panel HKL stats into a single summary dict.

    Args:
        per_panel_stats: List of dicts with 'panel_id' and 'hkl_stats' keys

    Returns:
        dict with aggregated min/max h,k,l and summed counts
    """
    if not per_panel_stats:
        return None

    h_min = min(s['hkl_stats']['h_min'] for s in per_panel_stats)
    h_max = max(s['hkl_stats']['h_max'] for s in per_panel_stats)
    k_min = min(s['hkl_stats']['k_min'] for s in per_panel_stats)
    k_max = max(s['hkl_stats']['k_max'] for s in per_panel_stats)
    l_min = min(s['hkl_stats']['l_min'] for s in per_panel_stats)
    l_max = max(s['hkl_stats']['l_max'] for s in per_panel_stats)
    total_queries = sum(s['hkl_stats']['total_queries'] for s in per_panel_stats)
    in_bounds_count = sum(s['hkl_stats']['in_bounds_count'] for s in per_panel_stats)
    out_of_bounds_count = sum(s['hkl_stats']['out_of_bounds_count'] for s in per_panel_stats)

    return {
        'h_min': h_min,
        'h_max': h_max,
        'k_min': k_min,
        'k_max': k_max,
        'l_min': l_min,
        'l_max': l_max,
        'total_queries': total_queries,
        'in_bounds_count': in_bounds_count,
        'out_of_bounds_count': out_of_bounds_count,
        'in_bounds_fraction': in_bounds_count / total_queries if total_queries > 0 else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Collect HKL coverage stats from simulate_forward_once"
    )
    parser.add_argument(
        "--detector-size",
        choices=["small", "full"],
        default="small",
        help="Smoke fixture detector size (default: small)"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for artifacts (e.g., plans/active/.../reports/<timestamp>/)"
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="PyTorch device (default: cpu)"
    )
    args = parser.parse_args()

    # Create output directory
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("HKL Coverage Collection: simulate_forward_once")
    print("=" * 80)
    print()

    # ============================================================
    # 1. Load smoke fixture and build mapping context for HKL data
    # ============================================================
    print("[1/2] Loading smoke fixture...")
    loader = load_smoke_fixture(args.detector_size)
    print(f"  Detector size: {args.detector_size}")
    print(f"  N panels: {len(loader.Expt.detector)}")

    # Build mapping context to extract HKL indices/amplitudes
    mapping_ctx = build_mapping_stage_a_context(
        loader,
        default_sigma_readout=3.0,
        device=args.device,
        apply_calibration_n_cells=True,
    )
    print(f"  HKL indices shape: {mapping_ctx.hkl_indices.shape}")
    print(f"  HKL amplitudes shape: {mapping_ctx.hkl_amplitudes.shape}")
    print()

    # ============================================================
    # 2. Build Stage A warm-cache context with HKL stats enabled
    # ============================================================
    print("[2/4] Building Stage A warm-cache context with HKL stats enabled...")

    device = torch.device(args.device)
    dtype = torch.float32

    # Build RefinementConfig with default oversample=3
    config = RefinementConfig(oversample=3)

    # Build HKL grid from mapping context indices/amplitudes
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=mapping_ctx.hkl_indices,
        amplitudes=mapping_ctx.hkl_amplitudes,
        device=device,
        halo=False,
    )

    print(f"  HKL grid shape: {hkl_grid.shape}")
    print(f"  HKL metadata: {hkl_metadata}")

    # Build Stage A context using mapping inputs
    stage_a_ctx = _build_stage_a_context(
        detector=loader.Expt.detector,
        beam=loader.Expt.beam,
        crystal=loader.Expt.crystal,
        trusted_mask=loader.trusted_mask,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        enable_hkl_interpolation=False,
        device=device,
        dtype=dtype,
        panel_slices=None,
        enable_roi_mode=False,
        calibration_metadata=mapping_ctx.calibration,
        config=config,
        debug_config={'collect_hkl_stats': True},  # Enable HKL stats collection
    )

    print(f"  Stage A simulators: {len(stage_a_ctx.simulators)}")
    print()

    # ============================================================
    # 3. Harvest HKL stats from Stage A simulators
    # ============================================================
    print("[3/4] Running Stage A simulators to harvest HKL stats...")

    stage_a_per_panel_stats = []
    for panel_id, simulator in enumerate(stage_a_ctx.simulators):
        # Run the simulator once to trigger HKL collection
        # Using the same crystal as in mapping_ctx to ensure consistency
        _ = simulator.run()

        # Extract HKL stats from simulator
        if hasattr(simulator, 'hkl_stats') and simulator.hkl_stats is not None:
            stage_a_per_panel_stats.append({
                'panel_id': panel_id,
                'hkl_stats': simulator.hkl_stats,
            })

    stage_a_aggregated = aggregate_panel_stats(stage_a_per_panel_stats)

    if stage_a_aggregated:
        print(f"  Total queries: {stage_a_aggregated['total_queries']:,}")
        print(f"  In-bounds: {stage_a_aggregated['in_bounds_count']:,} ({stage_a_aggregated['in_bounds_fraction']:.2%})")
        print(f"  Out-of-bounds: {stage_a_aggregated['out_of_bounds_count']:,}")
        print(f"  h range: [{stage_a_aggregated['h_min']}, {stage_a_aggregated['h_max']}]")
        print(f"  k range: [{stage_a_aggregated['k_min']}, {stage_a_aggregated['k_max']}]")
        print(f"  l range: [{stage_a_aggregated['l_min']}, {stage_a_aggregated['l_max']}]")
    else:
        print("  No HKL stats collected from Stage A simulators")
    print()

    # ============================================================
    # 4. Run simulate_forward_once with HKL stats enabled
    # ============================================================
    print("[4/4] Running simulate_forward_once with HKL stats enabled...")

    device = torch.device(args.device)

    # Reuse inputs from mapping_ctx to ensure consistency
    inputs = mapping_ctx.inputs

    # Run simulate_forward_once with HKL stats collection
    bragg, diagnostics = simulate_forward_once(
        inputs=inputs,
        detector=loader.Expt.detector,
        beam=loader.Expt.beam,
        crystal=loader.Expt.crystal,
        experiment=loader.Expt,
        hkl_indices=mapping_ctx.hkl_indices,
        hkl_amplitudes=mapping_ctx.hkl_amplitudes,
        calibration=mapping_ctx.calibration,
        device=device,
        debug_config={'collect_hkl_stats': True}
    )

    # Extract per-panel HKL stats from diagnostics
    mapping_per_panel_stats = diagnostics.get('per_panel_hkl_stats', [])
    mapping_aggregated = aggregate_panel_stats(mapping_per_panel_stats)

    if mapping_aggregated:
        print(f"  Total queries: {mapping_aggregated['total_queries']:,}")
        print(f"  In-bounds: {mapping_aggregated['in_bounds_count']:,} ({mapping_aggregated['in_bounds_fraction']:.2%})")
        print(f"  Out-of-bounds: {mapping_aggregated['out_of_bounds_count']:,}")
        print(f"  h range: [{mapping_aggregated['h_min']}, {mapping_aggregated['h_max']}]")
        print(f"  k range: [{mapping_aggregated['k_min']}, {mapping_aggregated['k_max']}]")
        print(f"  l range: [{mapping_aggregated['l_min']}, {mapping_aggregated['l_max']}]")
    else:
        print("  No HKL stats collected from simulate_forward_once")
    print()

    # ============================================================
    # 5. Emit comparison artifacts
    # ============================================================
    print("[5/5] Writing artifacts...")

    # Build comparison JSON
    comparison = {
        'detector_size': args.detector_size,
        'device': str(device),
        'hkl_grid_metadata': diagnostics['hkl_stats'],
        'stage_a_warm_cache': {
            'n_panels': len(stage_a_ctx.simulators),
            'per_panel_stats': stage_a_per_panel_stats,
            'aggregated': stage_a_aggregated,
        },
        'simulate_forward_once': {
            'n_panels': len(loader.Expt.detector),
            'per_panel_stats': mapping_per_panel_stats,
            'aggregated': mapping_aggregated,
        },
    }

    # Write JSON
    json_path = args.out_dir / "hkl_stats_comparison.json"
    with open(json_path, 'w') as f:
        json.dump(comparison, f, indent=2)
    print(f"  JSON written to: {json_path}")

    # Write prose summary
    summary_path = args.out_dir / "summary.md"
    with open(summary_path, 'w') as f:
        f.write("# HKL Coverage Analysis — DIAG-NANOBRAGG-OVERSAMPLE-001 Phase F\n\n")
        f.write("## Overview\n\n")
        f.write(f"Detector size: {args.detector_size}\n\n")
        f.write(f"Device: {args.device}\n\n")

        f.write("## HKL Grid Metadata\n\n")
        grid_meta = diagnostics['hkl_stats']
        f.write(f"- h_range: {grid_meta.get('h_range', 'N/A')}\n")
        f.write(f"- k_range: {grid_meta.get('k_range', 'N/A')}\n")
        f.write(f"- l_range: {grid_meta.get('l_range', 'N/A')}\n")
        f.write(f"- has_halo: {grid_meta.get('has_halo', False)}\n\n")

        f.write("## Stage A Warm-Cache Results\n\n")
        if stage_a_aggregated:
            f.write(f"- Total queries: {stage_a_aggregated['total_queries']:,}\n")
            f.write(f"- In-bounds: {stage_a_aggregated['in_bounds_count']:,} ({stage_a_aggregated['in_bounds_fraction']:.2%})\n")
            f.write(f"- Out-of-bounds: {stage_a_aggregated['out_of_bounds_count']:,}\n")
            f.write(f"- Observed h range: [{stage_a_aggregated['h_min']}, {stage_a_aggregated['h_max']}]\n")
            f.write(f"- Observed k range: [{stage_a_aggregated['k_min']}, {stage_a_aggregated['k_max']}]\n")
            f.write(f"- Observed l range: [{stage_a_aggregated['l_min']}, {stage_a_aggregated['l_max']}]\n\n")
        else:
            f.write("No HKL stats collected from Stage A.\n\n")

        f.write("## simulate_forward_once Results\n\n")
        if mapping_aggregated:
            f.write(f"- Total queries: {mapping_aggregated['total_queries']:,}\n")
            f.write(f"- In-bounds: {mapping_aggregated['in_bounds_count']:,} ({mapping_aggregated['in_bounds_fraction']:.2%})\n")
            f.write(f"- Out-of-bounds: {mapping_aggregated['out_of_bounds_count']:,}\n")
            f.write(f"- Observed h range: [{mapping_aggregated['h_min']}, {mapping_aggregated['h_max']}]\n")
            f.write(f"- Observed k range: [{mapping_aggregated['k_min']}, {mapping_aggregated['k_max']}]\n")
            f.write(f"- Observed l range: [{mapping_aggregated['l_min']}, {mapping_aggregated['l_max']}]\n\n")
        else:
            f.write("No HKL stats collected.\n\n")

        f.write("## Interpretation\n\n")

        # Compare Stage A vs mapping coverage
        if stage_a_aggregated and mapping_aggregated:
            stage_a_frac = stage_a_aggregated['in_bounds_fraction']
            mapping_frac = mapping_aggregated['in_bounds_fraction']

            if stage_a_frac < 0.01 and mapping_frac < 0.01:
                f.write("**Both paths miss the HKL grid** — suggests upstream structure-factor grid issue.\n")
                f.write("Recommend opening ARCH-SIM-HKL-BOUNDS-001 to realign HKL sources.\n\n")
            elif stage_a_frac < 0.01 and mapping_frac >= 0.01:
                f.write("**Stage A misses the HKL grid while mapping succeeds** — Stage A construction issue.\n")
                f.write("Investigate Stage A simulator setup in stage_a_utils.py.\n\n")
            elif stage_a_frac >= 0.01 and mapping_frac < 0.01:
                f.write("**Mapping misses the HKL grid while Stage A succeeds** — simulate_forward_once issue.\n")
                f.write("Investigate simulate_forward_once configuration.\n\n")
            else:
                f.write("**Both paths have sufficient in-bounds coverage** — HKL stats appear normal.\n\n")
        elif stage_a_aggregated:
            if stage_a_aggregated['in_bounds_fraction'] < 0.01:
                f.write("**Stage A misses the HKL grid** (mapping data unavailable).\n\n")
            else:
                f.write("**Stage A has sufficient coverage** (mapping data unavailable).\n\n")
        elif mapping_aggregated:
            if mapping_aggregated['in_bounds_fraction'] < 0.01:
                f.write("**Mapping misses the HKL grid** (Stage A data unavailable).\n\n")
            else:
                f.write("**Mapping has sufficient coverage** (Stage A data unavailable).\n\n")
        else:
            f.write("**Insufficient data** — HKL stats collection did not work for either path.\n\n")

    print(f"  Summary written to: {summary_path}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
