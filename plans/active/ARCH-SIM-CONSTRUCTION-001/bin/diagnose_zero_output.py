#!/usr/bin/env python3
"""
Zero-output diagnostic probe for ARCH-SIM-CONSTRUCTION-001 Phase D.

Identifies which component (HKL/crystal/beam/detector) causes zero simulator output.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

# Add repo root
# This script is at plans/active/ARCH-SIM-CONSTRUCTION-001/bin/diagnose_zero_output.py
# Repo root: bin -> ARCH-SIM-CONSTRUCTION-001 -> active -> plans -> repo_root (5 parents)
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import build_structure_factor_grid
from dbex.refinement.config_factories import (
    create_beam_config,
    create_crystal_config,
    create_detector_config,
)
from nanobrag_torch.simulator import Simulator


def diagnose_hkl_grid(hkl_grid, hkl_metadata):
    grid_np = hkl_grid.detach().cpu().numpy()
    return {
        "shape": list(hkl_grid.shape),
        "sum": float(grid_np.sum()),
        "max": float(grid_np.max()),
        "min": float(grid_np.min()),
        "mean": float(grid_np.mean()),
        "nonzero_count": int(np.count_nonzero(grid_np)),
        "total_elements": int(grid_np.size),
        "nonzero_fraction": float(np.count_nonzero(grid_np) / grid_np.size),
        "metadata": hkl_metadata,
    }


def diagnose_crystal(crystal_config, crystal_model):
    return {
        "cell_a": float(crystal_config.cell_a),
        "cell_b": float(crystal_config.cell_b),
        "cell_c": float(crystal_config.cell_c),
        "n_cells": int(crystal_config.n_cells) if hasattr(crystal_config, 'n_cells') else None,
        "has_missets": crystal_config.misset_deg != (0.0, 0.0, 0.0),
        "original_unit_cell": [float(x) for x in crystal_model.get_unit_cell().parameters()],
    }


def diagnose_beam(beam_config, beam_model):
    return {
        "wavelength_angstrom": float(beam_config.wavelength_A),
        "flux_photons": float(beam_config.flux) if hasattr(beam_config, 'flux') and beam_config.flux is not None else None,
        "exposure_sec": float(beam_config.exposure) if hasattr(beam_config, 'exposure') and beam_config.exposure is not None else None,
        "polarization_fraction": float(beam_model.get_polarization_fraction()),
    }


def diagnose_detector(detector_config, panel):
    return {
        "pixel_size_mm": float(detector_config.pixel_size_mm),
        "distance_mm": float(detector_config.distance_mm),
        "oversample": int(detector_config.oversample),
        "panel_size_pixels": [int(x) for x in panel.get_image_size()],
        "spixels": int(detector_config.spixels),
        "fpixels": int(detector_config.fpixels),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load fixture
    from argparse import Namespace
    data_args = Namespace(
        exptName=str(repo_root / "refGeom.expt"),
        reflName=str(repo_root / "refGeom.refl"),
        exptIdx=0,
        maskFile=str(repo_root / "747_mask.pkl"),
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
    )

    dataload = DataLoad(data_args)
    detector = dataload.detector
    beam = dataload.beam
    crystal = dataload.crystal

    # HKL grid
    hkl_indices = dataload.F.indices()
    hkl_amplitudes = dataload.F.data()
    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device="cpu",
        halo=False,
    )

    hkl_diag = diagnose_hkl_grid(hkl_grid, hkl_metadata)
    print(f"HKL: {hkl_diag['nonzero_count']}/{hkl_diag['total_elements']} nonzero, sum={hkl_diag['sum']:.3e}, max={hkl_diag['max']:.3e}")

    # Crystal
    # DataLoad has a single experiment in Expt attribute
    experiment = dataload.Expt
    crystal_config, n_cells_applied = create_crystal_config(
        crystal=crystal,
        experiment=experiment,
        misset_deg_override=None,
        crystal_overrides={},
    )
    crystal_diag = diagnose_crystal(crystal_config, crystal)
    print(f"Crystal: a={crystal_diag['cell_a']:.3f}Å, n_cells={crystal_diag['n_cells']}")

    # Beam
    beam_config = create_beam_config(beam=beam, flux=None, exposure=None, beamsize_mm=None)
    beam_diag = diagnose_beam(beam_config, beam)
    print(f"Beam: λ={beam_diag['wavelength_angstrom']:.6f}Å, flux={beam_diag['flux_photons']}")

    # Detector
    panel = detector[0]
    detector_config = create_detector_config(
        panel=panel,
        beam=beam,
        trusted_mask=np.ones(panel.get_image_size()[::-1], dtype=bool),
        oversample=3,
    )
    detector_diag = diagnose_detector(detector_config, panel)
    print(f"Detector: dist={detector_diag['distance_mm']:.1f}mm, oversample={detector_diag['oversample']}")

    # Simulator
    simulator = Simulator(
        detector=detector_config,
        beam=beam_config,
        crystal=crystal_config,
        hkl_grid=hkl_grid,
        device="cpu",
    )

    bragg = simulator.run(oversample=None)
    bragg_np = bragg.detach().cpu().numpy()

    sim_diag = {
        "mean": float(bragg_np.mean()),
        "max": float(bragg_np.max()),
        "min": float(bragg_np.min()),
        "sum": float(bragg_np.sum()),
        "nonzero_count": int(np.count_nonzero(bragg_np)),
        "total_pixels": int(bragg_np.size),
    }

    print(f"Simulator: mean={sim_diag['mean']:.3e}, max={sim_diag['max']:.3e}, nonzero={sim_diag['nonzero_count']}/{sim_diag['total_pixels']}")

    # Save
    diagnostics = {
        "hkl_grid": hkl_diag,
        "crystal": crystal_diag,
        "beam": beam_diag,
        "detector": detector_diag,
        "simulator_output": sim_diag,
    }

    output_path = output_dir / "zero_output_diagnostics.json"
    output_path.write_text(json.dumps(diagnostics, indent=2))
    print(f"\nDiagnostics → {output_path}")

    # Verdict
    if sim_diag["max"] == 0.0:
        print("\n❌ ZERO OUTPUT CONFIRMED")
        if hkl_diag["nonzero_count"] == 0:
            print("  → HKL grid is all zeros")
        elif crystal_diag["n_cells"] == 0:
            print("  → Crystal has zero cells")
        elif beam_diag["flux_photons"] is None or beam_diag["flux_photons"] == 0:
            print("  → Beam flux is zero/None")
        else:
            print("  → Unknown cause (all configs look valid)")
    else:
        print(f"\n✓ Simulator OK: max={sim_diag['max']:.3e}")


if __name__ == "__main__":
    main()
