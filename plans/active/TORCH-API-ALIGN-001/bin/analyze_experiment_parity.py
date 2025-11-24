#!/usr/bin/env python3
"""
Analyze ExperimentModel vs Factory parity blocker (initiative: TORCH-API-ALIGN-001, owner: galph)

Inputs: refGeom.expt + refGeom_gen.mtz fixtures, panel_id (default 0)
Data deps: dbex_files/refGeom/{refGeom.expt,refGeom_gen.mtz}
Outputs: Diff heatmap PNG, outlier pixel analysis JSON, comparison metrics
         under plans/active/TORCH-API-ALIGN-001/reports/<timestamp>/
Repro: python plans/active/TORCH-API-ALIGN-001/bin/analyze_experiment_parity.py --panel-id 0 --output-dir plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T215000Z
"""

import argparse
import json
import sys
import torch
import numpy as np
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Analyze ExperimentModel parity blocker")
    ap.add_argument("--panel-id", type=int, default=0, help="Panel ID to analyze")
    ap.add_argument("--output-dir", type=str, required=True, help="Output directory for artifacts")
    ap.add_argument("--tolerance", type=float, default=1e-6, help="Target parity tolerance")
    args = ap.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Import dbex modules
    from dbex.data_load import DataLoad
    from dbex.nanobrag_bridge import (
        create_detector_config,
        create_beam_config,
        create_crystal_config,
        build_structure_factor_grid
    )
    from dbex.refinement.helpers import create_unified_simulator, simulate_via_experiment_model

    # Load fixtures (match test_experiment_parity.py pattern exactly)
    from argparse import Namespace
    base_path = Path(__file__).parent.parent.parent.parent
    expt_path = base_path / "sp.proc" / "refGeom_small" / "refGeom_small.expt"
    refl_path = base_path / "sp.proc" / "refGeom_small" / "refGeom_small.refl"
    mtz_path = base_path / "scaled.mtz"

    DL_args = Namespace(
        exptName=str(expt_path),
        reflName=str(refl_path),
        exptIdx=0,
        maskFile=None,
        mtzFile=str(mtz_path),
        mtzCol="F,SIGF"
    )

    DL = DataLoad(DL_args)
    panel = DL.detector[args.panel_id]

    # Build HKL grid from experiment (no MTZ)
    hkl_indices = DL.indices.as_vec3_double()
    hkl_amplitudes = DL.F.data()

    device = torch.device("cpu")
    dtype = torch.float32

    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device,
        halo=False
    )

    # Create configs
    detector_config = create_detector_config(panel=panel, beam=DL.beam, trusted_mask=None)
    beam_config = create_beam_config(DL.beam)
    crystal_config, _ = create_crystal_config(DL.crystal, DL.Expt)

    device = torch.device("cpu")
    dtype = torch.float32

    print(f"[INFO] Running factory path...")
    simulator_factory, _, sqrt_scale_factory, metadata_factory = create_unified_simulator(
        detector_config=detector_config,
        crystal_config=crystal_config,
        beam_config=beam_config,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        mask_array=None,
        spot_scale_override=1.0,
        device=device,
        dtype=dtype,
        calibration_metadata=None
    )
    image_factory = simulator_factory.run()

    print(f"[INFO] Running adapter path...")
    image_adapter, sqrt_scale_adapter, metadata_adapter = simulate_via_experiment_model(
        detector_config=detector_config,
        crystal_config=crystal_config,
        beam_config=beam_config,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        mask_array=None,
        spot_scale_override=1.0,
        device=device,
        dtype=dtype,
        calibration_metadata=None
    )

    # Compute diff
    diff = torch.abs(image_factory - image_adapter)
    max_abs_diff = torch.max(diff).item()
    mse = torch.mean((image_factory - image_adapter) ** 2).item()

    # Identify outlier pixels (> tolerance)
    outlier_mask = diff > args.tolerance
    outlier_count = torch.sum(outlier_mask).item()
    outlier_fraction = outlier_count / diff.numel()

    # Get outlier pixel locations and values
    outlier_indices = torch.nonzero(outlier_mask, as_tuple=False).cpu().numpy()
    outlier_diffs = diff[outlier_mask].cpu().numpy()
    outlier_factory_vals = image_factory[outlier_mask].cpu().numpy()
    outlier_adapter_vals = image_adapter[outlier_mask].cpu().numpy()

    # Spatial analysis
    if outlier_count > 0:
        outlier_slow = outlier_indices[:, 0]
        outlier_fast = outlier_indices[:, 1]
        spatial_stats = {
            "slow_min": int(outlier_slow.min()),
            "slow_max": int(outlier_slow.max()),
            "slow_mean": float(outlier_slow.mean()),
            "fast_min": int(outlier_fast.min()),
            "fast_max": int(outlier_fast.max()),
            "fast_mean": float(outlier_fast.mean()),
        }
    else:
        spatial_stats = {}

    # Summary metrics
    metrics = {
        "panel_id": args.panel_id,
        "image_shape": list(image_factory.shape),
        "total_pixels": diff.numel(),
        "max_abs_diff": float(max_abs_diff),
        "mse": float(mse),
        "tolerance": args.tolerance,
        "outlier_count": int(outlier_count),
        "outlier_fraction": float(outlier_fraction),
        "sqrt_scale_factory": float(sqrt_scale_factory),
        "sqrt_scale_adapter": float(sqrt_scale_adapter),
        "factory_stats": {
            "min": float(image_factory.min().item()),
            "max": float(image_factory.max().item()),
            "mean": float(image_factory.mean().item()),
        },
        "adapter_stats": {
            "min": float(image_adapter.min().item()),
            "max": float(image_adapter.max().item()),
            "mean": float(image_adapter.mean().item()),
        },
        "spatial_stats": spatial_stats,
    }

    # Top-N outliers
    if outlier_count > 0:
        top_n = min(20, outlier_count)
        sorted_indices = np.argsort(outlier_diffs)[::-1][:top_n]
        top_outliers = [
            {
                "rank": int(i + 1),
                "slow": int(outlier_indices[sorted_indices[i], 0]),
                "fast": int(outlier_indices[sorted_indices[i], 1]),
                "diff": float(outlier_diffs[sorted_indices[i]]),
                "factory_val": float(outlier_factory_vals[sorted_indices[i]]),
                "adapter_val": float(outlier_adapter_vals[sorted_indices[i]]),
            }
            for i in range(top_n)
        ]
        metrics["top_outliers"] = top_outliers

    # Write metrics JSON
    metrics_path = output_dir / "parity_analysis.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"[INFO] Metrics written to {metrics_path}")

    # Create diff heatmap
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        # Factory image
        im0 = axes[0].imshow(image_factory.cpu().numpy(), cmap='viridis', aspect='auto')
        axes[0].set_title(f'Factory (max={image_factory.max().item():.2e})')
        axes[0].set_xlabel('Fast pixel')
        axes[0].set_ylabel('Slow pixel')
        plt.colorbar(im0, ax=axes[0])

        # Adapter image
        im1 = axes[1].imshow(image_adapter.cpu().numpy(), cmap='viridis', aspect='auto')
        axes[1].set_title(f'Adapter (max={image_adapter.max().item():.2e})')
        axes[1].set_xlabel('Fast pixel')
        axes[1].set_ylabel('Slow pixel')
        plt.colorbar(im1, ax=axes[1])

        # Diff heatmap (log scale for visibility)
        diff_np = diff.cpu().numpy()
        diff_np_nonzero = np.where(diff_np > 0, diff_np, 1e-12)  # Avoid log(0)
        im2 = axes[2].imshow(np.log10(diff_np_nonzero), cmap='hot', aspect='auto')
        axes[2].set_title(f'|Diff| (log10, max={max_abs_diff:.2e})')
        axes[2].set_xlabel('Fast pixel')
        axes[2].set_ylabel('Slow pixel')
        plt.colorbar(im2, ax=axes[2], label='log10(|diff|)')

        # Mark outliers on diff plot
        if outlier_count > 0 and outlier_count < 1000:
            axes[2].scatter(outlier_fast, outlier_slow, c='cyan', s=10, alpha=0.6, label=f'{outlier_count} outliers')
            axes[2].legend()

        plt.tight_layout()
        heatmap_path = output_dir / "parity_diff_heatmap.png"
        plt.savefig(heatmap_path, dpi=150)
        print(f"[INFO] Heatmap written to {heatmap_path}")
        plt.close()
    except ImportError:
        print("[WARN] matplotlib not available, skipping heatmap generation")

    # Print summary
    print(f"\n[SUMMARY]")
    print(f"  Max abs diff: {max_abs_diff:.2e} (tolerance {args.tolerance:.1e})")
    print(f"  MSE: {mse:.2e}")
    print(f"  Outliers: {outlier_count}/{diff.numel()} ({outlier_fraction * 100:.2f}%)")
    if outlier_count > 0:
        print(f"  Outlier spatial range: slow=[{spatial_stats['slow_min']},{spatial_stats['slow_max']}], fast=[{spatial_stats['fast_min']},{spatial_stats['fast_max']}]")
        print(f"  Top outlier: slow={top_outliers[0]['slow']}, fast={top_outliers[0]['fast']}, diff={top_outliers[0]['diff']:.2e}")

    # Exit code
    if max_abs_diff <= args.tolerance:
        print(f"\n[PASS] Parity within tolerance")
        sys.exit(0)
    else:
        print(f"\n[FAIL] Parity exceeds tolerance by {max_abs_diff / args.tolerance:.1f}x")
        sys.exit(1)


if __name__ == "__main__":
    main()
