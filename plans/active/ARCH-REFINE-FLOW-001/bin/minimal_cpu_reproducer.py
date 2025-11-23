#!/usr/bin/env python3
"""
Minimal reproducer for CPU simulator zero-Bragg bug (initiative: ARCH-REFINE-FLOW-001, owner: galph)

Inputs: refGeom data paths
Data deps: tests/dbex/fixtures/refGeom/{refine_experimental_image_0_indexed.json,
                                       refine_experimental_image_0_indexed.refl,
                                       shoebox_mask_0.pickle,
                                       4bs7.mtz,
                                       hkl_grid_halo.pt,
                                       hkl_metadata.pt}
Outputs: reproducer_result.json
Repro: python plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_reproducer.py
"""
import argparse
import json
import sys
from pathlib import Path

import torch
import numpy as np


def main():
    ap = argparse.ArgumentParser(description="CPU simulator minimal reproducer")
    ap.add_argument(
        "--output-dir",
        type=str,
        default="plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T120500Z",
        help="Output directory for result JSON",
    )
    args = ap.parse_args()

    # 1. Load refGeom fixtures
    from dbex.data_load import DataLoad
    from types import SimpleNamespace

    try:
        dataload_args = SimpleNamespace(
            mtzFile="scaled.mtz",
            mtzCol="F,SIGF",
            exptName="sp.proc/refGeom_small/refGeom_small.expt",
            exptIdx=0,
            reflName="sp.proc/refGeom_small/refGeom_small.refl",
            maskFile="sp.proc/refGeom_small/refGeom_small_mask.pkl",
        )
        DL = DataLoad(dataload_args)
    except Exception as e:
        error_msg = f"DataLoad failed: {e}"
        print(f"[REPRODUCER_ERROR] {error_msg}")
        result = {
            "reproducer_passed": False,
            "bragg_stats": None,
            "device": "cpu",
            "panel_id": None,
            "error": error_msg,
        }
        output_path = Path(args.output_dir) / "reproducer_result.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        return 1

    # 2. Build HKL grid from MTZ
    try:
        from dbex.nanobrag_bridge import build_structure_factor_grid

        # Build haloed grid for tricubic interpolation support
        hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
            indices=DL.F.indices(),
            amplitudes=DL.F.data(),
            device=torch.device("cpu"),
            halo=True
        )
    except Exception as e:
        error_msg = f"HKL grid load failed: {e}"
        print(f"[REPRODUCER_ERROR] {error_msg}")
        result = {
            "reproducer_passed": False,
            "bragg_stats": None,
            "device": "cpu",
            "panel_id": None,
            "error": error_msg,
        }
        output_path = Path(args.output_dir) / "reproducer_result.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        return 1

    # 3. Build CPU StageAContext (minimal setup)
    device = torch.device("cpu")
    dtype = torch.float32

    crystal = DL.crystal
    detector = DL.detector
    beam = DL.beam
    trusted_mask = DL.trusted_mask

    # Import nanobrag_torch components
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.models.crystal import Crystal
    from nanobrag_torch.simulator import Simulator
    from dbex.nanobrag_bridge import (
        create_detector_config,
        create_beam_config,
        create_crystal_config,
    )

    try:
        # Build crystal config
        crystal_config, _ = create_crystal_config(crystal, None)
        beam_config = create_beam_config(beam)

        # Transfer HKL grid to device
        hkl_grid_device = hkl_grid.to(device=device, dtype=dtype)

        # Build crystal model
        crystal_model = Crystal(
            crystal_config, beam_config=beam_config, device=device, dtype=dtype
        )
        crystal_model.interpolate = True  # Enable tricubic interpolation
        crystal_model.hkl_data = hkl_grid_device
        crystal_model.hkl_metadata = hkl_metadata

        # Build detector config for panel 0
        panel_id = 0
        panel = detector[panel_id]
        detector_config = create_detector_config(
            panel=panel, beam=beam, trusted_mask=trusted_mask[panel_id]
        )

        # Convert mask_array to torch.Tensor if needed
        mask_array = detector_config.mask_array
        if mask_array is not None and not isinstance(mask_array, torch.Tensor):
            mask_array = torch.tensor(mask_array, dtype=torch.float32, device=device)
            detector_config.mask_array = mask_array
        elif mask_array is not None and (
            mask_array.device != device or mask_array.dtype != torch.float32
        ):
            mask_array = mask_array.to(device=device, dtype=torch.float32)
            detector_config.mask_array = mask_array

        # Instantiate detector model
        detector_model = Detector(detector_config, device=device, dtype=dtype)

        # Build simulator
        simulator = Simulator(
            detector=detector_model,
            crystal=crystal_model,
            beam_config=beam_config,
            device=device,
            dtype=dtype,
        )

    except Exception as e:
        error_msg = f"Context setup failed: {e}"
        print(f"[REPRODUCER_ERROR] {error_msg}")
        result = {
            "reproducer_passed": False,
            "bragg_stats": None,
            "device": str(device),
            "panel_id": panel_id,
            "error": error_msg,
        }
        output_path = Path(args.output_dir) / "reproducer_result.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        return 1

    # 4. Run simulation
    try:
        bragg_panel = simulator.run()
    except Exception as e:
        error_msg = f"Simulation failed: {e}"
        print(f"[REPRODUCER_ERROR] {error_msg}")
        result = {
            "reproducer_passed": False,
            "bragg_stats": None,
            "device": str(device),
            "panel_id": panel_id,
            "error": error_msg,
        }
        output_path = Path(args.output_dir) / "reproducer_result.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        return 1

    # 5. Check Bragg tensor stats
    bragg_min = bragg_panel.min().item()
    bragg_max = bragg_panel.max().item()
    bragg_mean = bragg_panel.mean().item()
    bragg_nonzero_frac = (bragg_panel > 0).float().mean().item()

    # 6. Verdict
    reproducer_passed = bragg_nonzero_frac > 0.0  # Any nonzero pixels → simulator works

    # 7. Write result JSON
    result = {
        "reproducer_passed": reproducer_passed,
        "bragg_stats": {
            "min": bragg_min,
            "max": bragg_max,
            "mean": bragg_mean,
            "nonzero_fraction": bragg_nonzero_frac,
            "shape": list(bragg_panel.shape),
        },
        "device": str(device),
        "panel_id": panel_id,
        "error": None
        if reproducer_passed
        else "Zero Bragg output on CPU — nanobrag_torch simulator bug confirmed",
    }

    output_path = Path(args.output_dir) / "reproducer_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[REPRODUCER] Verdict: {'PASS' if reproducer_passed else 'FAIL'}")
    print(
        f"[REPRODUCER] Bragg stats: min={bragg_min}, max={bragg_max}, mean={bragg_mean}, nonzero_frac={bragg_nonzero_frac}"
    )
    print(f"[REPRODUCER] Result written to {output_path}")

    return 0 if reproducer_passed else 1


if __name__ == "__main__":
    sys.exit(main())
