#!/usr/bin/env python3
"""
Diagnose why simulator produces zero output despite non-zero fluence default.
(initiative: DIAG-NANOBRAGG-OVERSAMPLE-001, owner: galph)

Inputs: DB-AT-028 test fixtures (data/golden/sp.proc/idx-0000_sigma_metadata.{expt,refl,mtz,mask.pkl})
Data deps: Uses test harness fixtures, no external override
Outputs: diagnostic JSON under plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/<timestamp>/
Repro: python plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/diagnose_zero_output.py

Strategy:
1. Load test fixtures matching DB-AT-028 test
2. Create beam_config via create_beam_config(beam) with no calibration args (same as reconstruction.py:488)
3. Print beam_config fields: flux, exposure, beamsize_mm, fluence
4. Create a minimal simulator and run it
5. Instrument simulator to capture: normalized_intensity, steps, r_e_sqr, fluence, physical_intensity
6. Identify which factor causes zero output
"""

import sys
import json
from pathlib import Path

def main():
    # Add repo root to path
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root))

    import torch
    import numpy as np
    from dxtbx.model import ExperimentList
    from dials.array_family import flex

    # Load test fixtures (DB-AT-028 uses full-size sigma_metadata fixture)
    # Fixtures are at repo root under sp.proc
    data_root = Path.cwd() / "sp.proc"
    expt_path = data_root / "idx-0000_sigma_metadata.expt"
    refl_path = data_root / "idx-0000_sigma_metadata.refl"
    mtz_path = data_root / "refGeom.mtz"
    mask_path = data_root / "idx-0000_mask.pkl"

    print(f"Loading fixtures from {data_root}")
    print(f"  expt: {expt_path.exists()}")
    print(f"  refl: {refl_path.exists()}")
    print(f"  mtz: {mtz_path.exists()}")
    print(f"  mask: {mask_path.exists()}")

    if not all([expt_path.exists(), refl_path.exists(), mtz_path.exists(), mask_path.exists()]):
        print("ERROR: Missing test fixtures")
        return 1

    expt_list = ExperimentList.from_file(str(expt_path))
    experiment = expt_list[0]
    beam = experiment.beam
    detector = experiment.detector
    crystal = experiment.crystal

    # Create beam_config with NO calibration args (matches reconstruction.py:488)
    from dbex.refinement.config_factories import create_beam_config

    print("\n=== BeamConfig Creation ===")
    print(f"Calling: create_beam_config(beam)  # No flux/exposure/beamsize args")
    beam_config = create_beam_config(beam)

    print("\n=== BeamConfig Fields ===")
    print(f"  flux: {beam_config.flux}")
    print(f"  exposure: {beam_config.exposure}")
    print(f"  beamsize_mm: {beam_config.beamsize_mm}")
    print(f"  fluence: {beam_config.fluence}")
    print(f"  wavelength_A: {beam_config.wavelength_A}")

    # Create minimal detector/crystal configs for one panel
    from dbex.refinement.config_factories import create_detector_config, create_crystal_config

    panel = detector[0]
    detector_config = create_detector_config(panel, beam, trusted_mask=None)
    crystal_config, _ = create_crystal_config(crystal, experiment, apply_n_cells=False)

    # Build minimal HKL grid (just a few reflections for testing)
    from dbex.nanobrag_bridge import build_structure_factor_grid

    print("\n=== Building HKL Grid ===")
    hkl_grid, hkl_metadata = build_structure_factor_grid(
        crystal=crystal,
        experiment=experiment,
        mtz_path=str(mtz_path),
        dmin=1.5,  # Coarse resolution for speed
        device='cpu',
        dtype=torch.float32
    )
    print(f"  HKL grid shape: {hkl_grid.shape}")
    print(f"  has_halo: {hkl_metadata['has_halo']}")

    # Create simulator
    from nanobrag_torch.simulator import Simulator
    from nanobrag_torch.models import Detector, Crystal

    print("\n=== Creating Simulator ===")

    # Prepare detector model
    detector_model = Detector(detector_config)
    detector_model.hkl_grid = hkl_grid
    detector_model.hkl_metadata = hkl_metadata

    # Prepare crystal model
    crystal_model = Crystal(crystal_config)
    crystal_model.hkl_grid = hkl_grid
    crystal_model.hkl_metadata = hkl_metadata

    simulator = Simulator(
        detector=detector_model,
        crystal=crystal_model,
        beam_config=beam_config,
        device='cpu',
        dtype=torch.float32
    )

    print(f"  simulator.fluence (from beam_config): {simulator.fluence}")
    print(f"  simulator.r_e_sqr: {simulator.r_e_sqr}")

    # Run simulator
    print("\n=== Running Simulator ===")
    bragg_panel = simulator.run()

    print(f"  Output shape: {bragg_panel.shape}")
    print(f"  Output mean: {bragg_panel.mean().item()}")
    print(f"  Output max: {bragg_panel.max().item()}")
    print(f"  Output min: {bragg_panel.min().item()}")
    print(f"  Non-zero pixels: {(bragg_panel > 0).sum().item()}")

    # Save diagnostic
    diagnostic = {
        "beam_config": {
            "flux": float(beam_config.flux),
            "exposure": float(beam_config.exposure),
            "beamsize_mm": float(beam_config.beamsize_mm),
            "fluence": float(beam_config.fluence),
            "wavelength_A": float(beam_config.wavelength_A),
        },
        "simulator": {
            "fluence": float(simulator.fluence),
            "r_e_sqr": float(simulator.r_e_sqr),
        },
        "output": {
            "shape": list(bragg_panel.shape),
            "mean": float(bragg_panel.mean().item()),
            "max": float(bragg_panel.max().item()),
            "min": float(bragg_panel.min().item()),
            "non_zero_pixels": int((bragg_panel > 0).sum().item()),
        }
    }

    # Write to artifacts
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    output_dir = repo_root / "plans" / "active" / "DIAG-NANOBRAGG-OVERSAMPLE-001" / "reports" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "diagnose_zero_output.json"
    with open(output_path, 'w') as f:
        json.dump(diagnostic, f, indent=2)

    print(f"\n=== Diagnostic Written ===")
    print(f"  {output_path}")

    # Verdict
    print("\n=== Analysis ===")
    if beam_config.fluence == 0:
        print("ROOT CAUSE: beam_config.fluence is ZERO")
        print("  -> BeamConfig __post_init__ must be zeroing it somehow")
    elif float(simulator.fluence) == 0:
        print("ROOT CAUSE: simulator.fluence is ZERO despite beam_config.fluence being non-zero")
        print("  -> Simulator.__init__ is zeroing it")
    elif bragg_panel.max().item() == 0:
        print("MYSTERY: fluence is non-zero but output is still zero")
        print("  -> Problem is in normalized_intensity, steps, or lattice/structure factors")
        print("  -> Requires deeper instrumentation of simulator.run() internals")
    else:
        print("SUCCESS: Simulator produced non-zero output!")
        print(f"  Output mean: {bragg_panel.mean().item():.6e}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
