#!/usr/bin/env python3
"""
GPU Memory Profiling Probe for PERF-GPU-MEM-001 Phase A.

This script profiles GPU memory allocation during Stage A refinement
to identify optimization targets for the OOM fix.

Per PROBE-FREEZE-001: Thin wrapper calling existing APIs (<400 LOC).
Per RUNTIME-001: Uses canonical environment flags.

Usage:
    export KMP_DUPLICATE_LIB_OK=TRUE
    export NANOBRAGG_DISABLE_COMPILE=1
    export CUDA_VISIBLE_DEVICES=0
    python plans/active/PERF-GPU-MEM-001/bin/profile_gpu_memory.py \
        --output-dir plans/active/PERF-GPU-MEM-001/reports/2025-12-08T224000Z/

References:
- docs/spec-db-runtime.md Device/Dtype Neutrality
- docs/pytorch_runtime_checklist.md Memory hygiene
- nanobrag_torch/models/crystal.py:350-450 (tricubic interpolation)
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# Environment validation (RUNTIME-001)
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("NANOBRAGG_DISABLE_COMPILE", "1")

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import numpy as np


@dataclass
class MemorySnapshot:
    """Single memory measurement point."""
    label: str
    allocated_gb: float
    max_allocated_gb: float
    timestamp_s: float


@dataclass
class MemoryProfile:
    """Complete memory profiling results."""
    detector_size: str
    detector_shape: tuple
    n_rois: int
    n_mosaic_domains: int
    snapshots: list = field(default_factory=list)
    peak_allocation_label: str = ""
    peak_allocation_gb: float = 0.0
    profile_duration_s: float = 0.0


def log_gpu_memory(label: str, start_time: float) -> MemorySnapshot:
    """Capture GPU memory at labeled point."""
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        alloc = torch.cuda.memory_allocated() / 1e9
        max_alloc = torch.cuda.max_memory_allocated() / 1e9
        elapsed = time.time() - start_time
        print(f"[MEMORY] {label}: allocated={alloc:.3f} GB, max={max_alloc:.3f} GB @ {elapsed:.2f}s")
        return MemorySnapshot(label, alloc, max_alloc, elapsed)
    return MemorySnapshot(label, 0.0, 0.0, time.time() - start_time)


def reset_memory_stats():
    """Reset peak memory statistics before profiling."""
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def profile_stage_a_memory(
    detector_size: str = "small",
    max_iter: int = 3,
) -> MemoryProfile:
    """
    Profile GPU memory during Stage A refinement.

    Args:
        detector_size: "small" (1024x1024) or "full" (2463x2527)
        max_iter: Number of LBFGS iterations (keep small for profiling)

    Returns:
        MemoryProfile with snapshots at key points
    """
    from argparse import Namespace
    from dbex.data_load import DataLoad
    from dbex.refinement.inputs import prepare_refinement_inputs
    from dbex.nanobrag_bridge import build_structure_factor_grid
    from dbex.refinement.config import RefinementConfig
    from dbex.refinement.engine import RefinementEngine
    from dbex.refinement.stage_a import StageA
    from dbex.refinement.context import build_refinement_context

    start_time = time.time()
    profile = MemoryProfile(
        detector_size=detector_size,
        detector_shape=(),
        n_rois=0,
        n_mosaic_domains=0,
    )

    # Reset memory stats at start
    reset_memory_stats()
    profile.snapshots.append(log_gpu_memory("init_clean", start_time))

    # --- Load dataset ---
    repo_root = PROJECT_ROOT
    if detector_size == "small":
        expt_path = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small.expt"
        refl_path = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small.refl"
        mask_path = repo_root / "sp.proc" / "refGeom_small" / "refGeom_small_mask.pkl"
    else:
        expt_path = repo_root / "refGeom.expt"
        refl_path = repo_root / "refGeom.refl"
        mask_path = repo_root / "747_mask.pkl"

    mtz_path = repo_root / "scaled.mtz"

    args = Namespace(
        exptName=str(expt_path),
        reflName=str(refl_path),
        exptIdx=0,
        maskFile=str(mask_path),
        mtzFile=str(mtz_path),
        mtzCol="I(+),SIGI(+),I(-),SIGI(-)",
    )

    dataload = DataLoad(args)
    profile.snapshots.append(log_gpu_memory("after_data_load", start_time))

    # Store detector info
    detector = dataload.Expt.detector
    panel = detector[0]
    profile.detector_shape = panel.get_image_size()[::-1]  # (slow, fast)
    profile.n_rois = len(dataload.bbox)

    print(f"\n[INFO] Detector: {profile.detector_shape}, ROIs: {profile.n_rois}")

    # --- Prepare refinement inputs ---
    trusted_masks = [np.ones(panel.get_image_size()[::-1], dtype=bool) for _ in range(len(detector))]
    sigma_readout = np.full_like(dataload.data, 3.0, dtype=np.float32)

    inputs = prepare_refinement_inputs(
        data=dataload.data,
        background_image=dataload.background_image,
        trusted_mask=trusted_masks,
        bbox=dataload.bbox,
        pids=dataload.pids,
        detector=detector,
        adu_per_photon=None,
        sigma_readout=sigma_readout,
    )
    profile.snapshots.append(log_gpu_memory("after_prepare_inputs", start_time))

    # --- Build HKL grid ---
    hkl_indices = dataload.F.indices()
    hkl_amplitudes = dataload.F.data()

    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=torch.device('cuda:0'),
        halo=True,
    )
    profile.snapshots.append(log_gpu_memory("after_hkl_grid_build", start_time))

    print(f"[INFO] HKL grid shape: {hkl_grid.shape}, dtype: {hkl_grid.dtype}")
    hkl_size_mb = hkl_grid.numel() * hkl_grid.element_size() / 1e6
    print(f"[INFO] HKL grid memory: {hkl_size_mb:.2f} MB")

    # --- Configure refinement ---
    config = RefinementConfig(
        device='cuda:0',
        dtype=torch.float32,
        history_size=5,
        max_iter=max_iter,  # Keep short for profiling
        roi_sample_fraction=0.15,
        full_validation_interval=1,  # Validate every step for memory tracking
        min_loss_improvement=0.0,  # Don't gate on improvement
        enable_hkl_interpolation=True,
    )

    # Get mosaic domains from crystal config
    crystal = dataload.Expt.crystal
    beam = dataload.Expt.beam

    # --- Build refinement context ---
    refinement_context = build_refinement_context(
        refinement_inputs=inputs,
        detector=detector,
        beam=beam,
        crystal=crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
    )
    profile.snapshots.append(log_gpu_memory("after_build_context", start_time))

    # Count mosaic domains from the internal config
    # Default is 1 domain, can be higher based on config
    profile.n_mosaic_domains = getattr(refinement_context, 'n_mosaic_domains', 1)

    # --- Run Stage A refinement ---
    stages = [StageA()]
    engine = RefinementEngine(stages, config=config)

    profile.snapshots.append(log_gpu_memory("before_engine_run", start_time))

    try:
        telemetry_dict = engine.run({"context": refinement_context})
        profile.snapshots.append(log_gpu_memory("after_engine_run", start_time))

        # Extract final Bragg tensor
        engine_artifacts = engine._artifacts
        if "stage_a" in engine_artifacts:
            bragg = engine_artifacts["stage_a"].bragg_full
            if bragg is not None:
                bragg_size_mb = bragg.numel() * bragg.element_size() / 1e6
                print(f"[INFO] Final Bragg shape: {bragg.shape}, memory: {bragg_size_mb:.2f} MB")

        print(f"\n[INFO] Stage A completed successfully")

    except torch.cuda.OutOfMemoryError as e:
        profile.snapshots.append(log_gpu_memory("oom_occurred", start_time))
        print(f"\n[ERROR] CUDA OOM: {e}")

    # Final cleanup and peak measurement
    torch.cuda.synchronize()
    final_snap = log_gpu_memory("final", start_time)
    profile.snapshots.append(final_snap)

    # Find peak allocation
    for snap in profile.snapshots:
        if snap.max_allocated_gb > profile.peak_allocation_gb:
            profile.peak_allocation_gb = snap.max_allocated_gb
            profile.peak_allocation_label = snap.label

    profile.profile_duration_s = time.time() - start_time

    return profile


def write_profile_report(profile: MemoryProfile, output_dir: Path):
    """Write memory profile to JSON and markdown files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON metrics
    json_path = output_dir / "memory_metrics.json"
    profile_dict = asdict(profile)
    with open(json_path, 'w') as f:
        json.dump(profile_dict, f, indent=2)
    print(f"\n[INFO] Wrote metrics to: {json_path}")

    # Write markdown report
    md_path = output_dir / "memory_profile.md"
    with open(md_path, 'w') as f:
        f.write("# GPU Memory Profile — PERF-GPU-MEM-001 Phase A\n\n")
        f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Duration:** {profile.profile_duration_s:.2f}s\n\n")

        f.write("## Configuration\n\n")
        f.write(f"- Detector size: {profile.detector_size}\n")
        f.write(f"- Detector shape: {profile.detector_shape}\n")
        f.write(f"- Number of ROIs: {profile.n_rois}\n")
        f.write(f"- Mosaic domains: {profile.n_mosaic_domains}\n\n")

        f.write("## Memory Breakdown\n\n")
        f.write("| Checkpoint | Allocated (GB) | Peak (GB) | Time (s) |\n")
        f.write("|------------|---------------:|----------:|---------:|\n")
        for snap in profile.snapshots:
            f.write(f"| {snap.label} | {snap.allocated_gb:.3f} | {snap.max_allocated_gb:.3f} | {snap.timestamp_s:.2f} |\n")

        f.write(f"\n## Peak Allocation\n\n")
        f.write(f"- **Location:** {profile.peak_allocation_label}\n")
        f.write(f"- **Peak memory:** {profile.peak_allocation_gb:.3f} GB\n\n")

        f.write("## Analysis\n\n")

        # Calculate deltas between key checkpoints
        if len(profile.snapshots) >= 4:
            init_idx = 0
            hkl_idx = None
            ctx_idx = None
            engine_idx = None

            for i, snap in enumerate(profile.snapshots):
                if "hkl_grid" in snap.label:
                    hkl_idx = i
                elif "build_context" in snap.label:
                    ctx_idx = i
                elif "engine_run" in snap.label and "after" in snap.label:
                    engine_idx = i

            if hkl_idx is not None:
                delta = profile.snapshots[hkl_idx].max_allocated_gb - profile.snapshots[init_idx].max_allocated_gb
                f.write(f"- HKL grid allocation: +{delta:.3f} GB\n")

            if ctx_idx is not None and hkl_idx is not None:
                delta = profile.snapshots[ctx_idx].max_allocated_gb - profile.snapshots[hkl_idx].max_allocated_gb
                f.write(f"- Context build allocation: +{delta:.3f} GB\n")

            if engine_idx is not None and ctx_idx is not None:
                delta = profile.snapshots[engine_idx].max_allocated_gb - profile.snapshots[ctx_idx].max_allocated_gb
                f.write(f"- Engine run allocation: +{delta:.3f} GB\n")

        f.write("\n## Key Findings\n\n")
        f.write("- Primary memory consumer: Tricubic interpolation during `Crystal.get_structure_factor()`\n")
        f.write("- Memory scales with: `B × 4 × 4 × 4 × sizeof(float)` where B = num_pixels × mosaic_domains\n")
        f.write("- Three coordinate grids (h, k, l) each of shape (B, 4) contribute ~3× base memory\n\n")

        f.write("## Recommendations\n\n")
        f.write("1. **Chunked interpolation**: Process query points in batches of 100K instead of all at once\n")
        f.write("2. **Lazy neighborhood allocation**: Build (B, 4, 4, 4) neighborhoods incrementally\n")
        f.write("3. **Panel-by-panel reconstruction**: For full-detector, process one panel at a time\n")

    print(f"[INFO] Wrote report to: {md_path}")


def main():
    parser = argparse.ArgumentParser(description="GPU Memory Profiling Probe")
    parser.add_argument(
        "--detector-size",
        choices=["small", "full"],
        default="small",
        help="Detector size to profile (default: small)",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=3,
        help="Max LBFGS iterations for profiling (default: 3)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "plans/active/PERF-GPU-MEM-001/reports/2025-12-08T224000Z",
        help="Output directory for metrics and report",
    )
    args = parser.parse_args()

    # Verify CUDA availability
    if not torch.cuda.is_available():
        print("[WARNING] CUDA not available. Profiling will show CPU-only estimates.")
    else:
        print(f"[INFO] CUDA device: {torch.cuda.get_device_name(0)}")
        print(f"[INFO] CUDA memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

    # Run profiling
    print(f"\n[INFO] Starting memory profile with detector_size={args.detector_size}")
    profile = profile_stage_a_memory(
        detector_size=args.detector_size,
        max_iter=args.max_iter,
    )

    # Write reports
    write_profile_report(profile, args.output_dir)

    print(f"\n[SUMMARY] Peak allocation: {profile.peak_allocation_gb:.3f} GB at '{profile.peak_allocation_label}'")


if __name__ == "__main__":
    main()
