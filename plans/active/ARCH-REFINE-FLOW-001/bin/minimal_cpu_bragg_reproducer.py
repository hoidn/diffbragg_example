#!/usr/bin/env python3
"""
Minimal CPU Bragg Reproducer — Isolate dbex vs nanobrag_torch bug
Initiative: ARCH-REFINE-FLOW-001, Owner: galph, Loop: i=220

Purpose:
  Build CPU StageAContext with canonical refGeom.expt parameters,
  run single-panel simulation, check if Bragg output is non-zero.

Inputs:
  --expt-path (optional): Path to refGeom.expt (default: refGeom.expt)
  --out-dir (optional): Output directory for JSON decision (default: current dir)

Outputs:
  reproducer_result.json: {"result": "PASS"|"FAIL", "bragg_stats": {...}, "next_path": "A"|"B"|"C"|"D"}

Repro:
  python plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py \
    --expt-path refGeom.expt \
    --out-dir plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T130000Z/

Decision Criteria:
  - IF bragg.max() > 0 → PASS (dbex bug, Path A: investigate cache/context)
  - ELSE → FAIL (nanobrag_torch bug, Path B: source inspection + patch OR defer)
"""
import argparse
import json
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Minimal CPU Bragg reproducer")
    ap.add_argument("--expt-path", type=str, default="refGeom.expt",
                    help="Path to refGeom.expt")
    ap.add_argument("--out-dir", type=str, default=".",
                    help="Output directory for JSON decision")
    args = ap.parse_args()

    # Lazy imports to avoid circular dependencies
    import torch
    from dxtbx.model.experiment_list import ExperimentListFactory
    from simtbx.diffBragg import utils

    # Load refGeom.expt
    expt_path = Path(args.expt_path)
    if not expt_path.exists():
        print(f"ERROR: {expt_path} not found", file=sys.stderr)
        sys.exit(1)

    expt_list = ExperimentListFactory.from_json_file(str(expt_path), check_format=False)
    expt = expt_list[0]
    detector = expt.detector
    beam = expt.beam
    crystal = expt.crystal

    print(f"[LOAD] Loaded {expt_path}")
    print(f"[CRYSTAL] cell={crystal.get_unit_cell().parameters()}")
    print(f"[DETECTOR] {len(detector)} panels")
    print(f"[BEAM] wavelength={beam.get_wavelength()}")

    # Load MTZ (use canonical path from project root)
    mtz_path = Path("scaled.mtz")
    if not mtz_path.exists():
        print(f"ERROR: {mtz_path} not found", file=sys.stderr)
        sys.exit(1)

    # Load structure factors from MTZ using simtbx utils
    mtz_data = utils.open_mtz(str(mtz_path), "F,SIGF")
    mtz_data = mtz_data.generate_bijvoet_mates()  # Generate Friedel mates
    indices = mtz_data.indices()
    amplitudes = mtz_data.data()
    print(f"[MTZ] Loaded {mtz_path}, {len(indices)} structure factors")

    # Device and dtype
    device = torch.device("cpu")
    dtype = torch.float32

    # Import dbex helper (lazy to avoid circular deps)
    from dbex.nanobrag_bridge import build_structure_factor_grid

    # Build HKL grid with halo for interpolation (per REFINE-005)
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=indices,
        amplitudes=amplitudes,
        device=device,
        halo=True
    )

    print(f"[HKL] Built HKL grid with halo, shape={hkl_grid.shape}")
    print(f"[HKL] Metadata: {hkl_metadata}")

    # Create trusted mask (all True for simplicity)
    import numpy as np
    # Get detector panel dimensions
    panel = detector[0]
    slow_size, fast_size = panel.get_image_size()
    trusted_mask = np.ones((1, fast_size, slow_size), dtype=bool)  # (n_panels, slow, fast)

    # Create panel_slices for single panel
    panel_slices = [slice(0, slow_size * fast_size)]

    # Build CPU StageAContext helper
    from dbex.nanobrag_refinement import _build_stage_a_context

    # Build CPU context (same parameters as CUDA path)
    # Reference: dbex/nanobrag_refinement.py:2234-2246 (CPU context builder in inline path)
    stage_a_ctx = _build_stage_a_context(
        detector=detector,
        beam=beam,
        crystal=crystal,
        trusted_mask=trusted_mask,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        enable_hkl_interpolation=True,  # tricubic per REFINE-005
        device=device,
        dtype=dtype,
        panel_slices=panel_slices,
        enable_roi_mode=False,          # panel mode for reproducer
    )

    print(f"[CONTEXT] Built CPU StageAContext")
    print(f"[CONTEXT] Detectors cached: {len(stage_a_ctx.detector_configs)}")

    # Extract panel 0 (first panel)
    panel_id = 0
    detector_config = stage_a_ctx.detector_configs[panel_id]
    hkl_grid_ctx = stage_a_ctx.hkl_grid

    print(f"[PANEL] Extracted panel {panel_id}")

    # Use the pre-built simulator from context (it's already cached with correct crystal/beam)
    simulator = stage_a_ctx.simulators[panel_id]

    print(f"[SIMULATOR] Created on device={device}, dtype={dtype}")

    # Run simulator.run() with HKL grid
    print(f"[SIMULATION] Running single panel on CPU...")

    with torch.no_grad():  # No gradients needed for reproducer
        bragg_panel = simulator.run(hkl_grid_ctx)

    print(f"[SIMULATION] Complete")

    # Compute Bragg stats
    bragg_min = float(bragg_panel.min().item())
    bragg_max = float(bragg_panel.max().item())
    bragg_mean = float(bragg_panel.mean().item())
    nonzero_count = int((bragg_panel > 0).sum().item())
    total_pixels = bragg_panel.numel()

    print(f"[BRAGG] shape={bragg_panel.shape}")
    print(f"[BRAGG] min={bragg_min}, max={bragg_max}, mean={bragg_mean}")
    print(f"[BRAGG] nonzero_count={nonzero_count}/{total_pixels} ({100*nonzero_count/total_pixels:.2f}%)")

    bragg_stats = {
        "shape": list(bragg_panel.shape),
        "min": bragg_min,
        "max": bragg_max,
        "mean": bragg_mean,
        "nonzero_count": nonzero_count,
        "total_pixels": total_pixels,
        "nonzero_fraction": nonzero_count / total_pixels,
    }

    # Decision criteria: bragg_max > 0 → PASS, else FAIL
    if bragg_max > 0:
        result = "PASS"
        next_path = "A"  # dbex bug (cache/context issue)
        message = "Bragg output is non-zero on CPU reproducer. Bug is in dbex warm cache or context cloning."
    else:
        result = "FAIL"
        next_path = "B"  # nanobrag_torch bug (simulator issue)
        message = "Bragg output is zero on CPU reproducer. Bug is in nanobrag_torch Simulator.run() CPU path."

    decision = {
        "result": result,
        "next_path": next_path,
        "message": message,
        "bragg_stats": bragg_stats,
        "crystal_params": {
            "cell_a": float(crystal.get_unit_cell().parameters()[0]),
            "cell_b": float(crystal.get_unit_cell().parameters()[1]),
            "cell_c": float(crystal.get_unit_cell().parameters()[2]),
            "cell_alpha": float(crystal.get_unit_cell().parameters()[3]),
            "cell_beta": float(crystal.get_unit_cell().parameters()[4]),
            "cell_gamma": float(crystal.get_unit_cell().parameters()[5]),
        },
        "device": str(device),
        "dtype": str(dtype),
    }

    # Write JSON
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "reproducer_result.json"
    with open(json_path, "w") as f:
        json.dump(decision, f, indent=2)

    print(f"[RESULT] {result} ({next_path})")
    print(f"[OUTPUT] {json_path}")

    # Exit code: 0 if PASS, 1 if FAIL
    sys.exit(0 if result == "PASS" else 1)


if __name__ == "__main__":
    main()
