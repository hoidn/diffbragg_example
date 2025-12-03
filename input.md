# Input for Ralph (Loop 2025-12-02T224500Z)

## Summary
Investigate why simulator produces all-zero Bragg output despite correct scale factors and oversample parameters.

## Mode
none (evidence collection: zero-output root cause investigation)

## InitiativeType
architecture

## Focus
ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment (Phase D: Zero-Output Investigation)

## Branch
integration

## Mapped tests
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity` (validates non-zero simulator output)
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity` (validates ROI correlation)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (validates LBFGS parameter movement)

## Artifacts
`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T224500Z/`
- `zero_output_diagnostics.json` (HKL/crystal/beam/detector diagnostics)
- `probe_run.log` (probe execution log)
- `zero_output_analysis.md` (root cause analysis)
- `summary.md` (loop summary)

## Do Now

**Context**: DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C successfully threaded oversample=3 to all 292 DetectorConfig instances, but DB-AT-028 reveals simulator producing all-zero Bragg output. Debug evidence shows:
```
log_scale_baseline_value: 20.138489594990745
scale_factor (after exp): 557230080.0          ← CORRECT
bragg_panel[0] mean (raw sim output): 0.000000e+00  ← PROBLEM
bragg_panel[0] max: 0.000000e+00                    ← PROBLEM
```

Scale factors are correct, oversample is correct (3, not -1), but simulator produces no diffraction signal. This is a **NEW BLOCKER** distinct from the oversample issue.

**Investigation Strategy**: Create minimal standalone diagnostic probe to identify which component (HKL grid / crystal / beam / detector) is zero or invalid.

### Task D.1: Create diagnostic probe script

**File**: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/diagnose_zero_output.py`

**Content**: Copy the complete Python script from the How-To Map section below (labeled "COMPLETE PROBE SCRIPT TEMPLATE")

### Task D.2: Run diagnostic probe

**Command**:
```bash
cd /home/ollie/Documents/diffbragg_example
mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/bin
mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T224500Z

# Copy script from template below
# Then run:
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/diagnose_zero_output.py \
    --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T224500Z/ \
    > plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T224500Z/probe_run.log 2>&1
```

**Expected**: JSON file with diagnostics showing which component is zero

### Task D.3: Analyze results

Create `zero_output_analysis.md` identifying root cause:
- Which component is broken (HKL grid / crystal / beam / detector)?
- Evidence from diagnostics JSON
- Hypothesis for why it's broken
- Recommended fix

**Template**:
```markdown
# Zero-Output Root Cause Analysis

## Probe Results

[Paste key statistics from zero_output_diagnostics.json]

**HKL Grid**:
- Nonzero count: X / Y elements
- Sum: Z
- Max: W

**Crystal**: a=X Å, n_cells=Y
**Beam**: λ=X Å, flux=Y
**Detector**: distance=X mm, oversample=Y

**Simulator Output**:
- Mean: X
- Max: Y
- Nonzero pixels: Z / W

## Root Cause

**Broken Component**: [name]
**Evidence**: [specific diagnostic value]
**Hypothesis**: [why this is zero]

## Recommended Fix

[Specific changes needed]

## Next Steps

[Implementation plan or escalation path]
```

### Task D.4: Write summary

Create `summary.md` documenting findings and next steps

## How-To Map

### COMPLETE PROBE SCRIPT TEMPLATE

Save this to `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/diagnose_zero_output.py`:

```python
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
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    build_structure_factor_grid,
    create_beam_config,
    create_crystal_config,
    create_detector_config,
)
from nanobrag_torch import Simulator


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
        "cell_a": float(crystal_config.a),
        "cell_b": float(crystal_config.b),
        "cell_c": float(crystal_config.c),
        "n_cells": int(crystal_config.n_cells),
        "has_missets": crystal_config.misset_deg is not None,
        "original_unit_cell": [float(x) for x in crystal_model.get_unit_cell().parameters()],
    }


def diagnose_beam(beam_config, beam_model):
    return {
        "wavelength_angstrom": float(beam_config.wavelength),
        "flux_photons": float(beam_config.flux) if beam_config.flux is not None else None,
        "exposure_sec": float(beam_config.exposure) if beam_config.exposure is not None else None,
        "polarization_fraction": float(beam_model.get_polarization_fraction()),
    }


def diagnose_detector(detector_config, panel):
    return {
        "pixel_size_mm": [float(x) for x in detector_config.pixel_size],
        "distance_mm": float(detector_config.distance),
        "oversample": int(detector_config.oversample),
        "panel_size_pixels": [int(x) for x in panel.get_image_size()],
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
    hkl_grid, hkl_metadata = build_structure_factor_grid(
        crystal=crystal,
        mtz_column_label="F,SIGF",
        mtz_file_path=data_args.mtzFile,
        enable_hkl_interpolation=False,
        device="cpu",
    )

    hkl_diag = diagnose_hkl_grid(hkl_grid, hkl_metadata)
    print(f"HKL: {hkl_diag['nonzero_count']}/{hkl_diag['total_elements']} nonzero, sum={hkl_diag['sum']:.3e}, max={hkl_diag['max']:.3e}")

    # Crystal
    crystal_config = create_crystal_config(
        crystal=crystal,
        misset_deg_override=None,
        crystal_overrides={},
    )
    crystal_diag = diagnose_crystal(crystal_config, crystal)
    print(f"Crystal: a={crystal_diag['cell_a']:.3f}Å, n_cells={crystal_diag['n_cells']}")

    # Beam
    beam_config = create_beam_config(beam=beam, beam_flux=None, beam_exposure=None, beamsize_mm=None)
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
```

### Execution Steps

1. Save script to `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/diagnose_zero_output.py`
2. Run: `python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/diagnose_zero_output.py --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T224500Z/ > plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T224500Z/probe_run.log 2>&1`
3. Read `zero_output_diagnostics.json`
4. Write `zero_output_analysis.md` with root cause
5. Write `summary.md`

## Pitfalls To Avoid

1. **Do NOT skip HKL grid check** - most likely culprit for zero output
2. **Do NOT assume oversample is still the issue** - we already fixed that (292/292 configs have oversample=3)
3. **Do NOT try to fix in this loop** - evidence collection only
4. **Do NOT modify test fixtures** - use existing refGeom.expt/refl/mtz

## If Blocked

**If script errors on imports**:
- Check nanobrag_torch installed
- Check paths to refGeom.expt exist

**If output is non-zero**:
- Document difference between probe and test
- Check if test uses different fixture

**If all configs look valid but output still zero**:
- Document in analysis.md
- Recommend nanobrag_torch version check or maintainer escalation

## Findings Applied

- **DIAG-OVERSAMPLE-001**: Resolved (292/292 oversample=3)
- **DIAG-OVERSAMPLE-002**: Anticipated (simulator zero-output post-oversample fix)

## Pointers

- `dbex/nanobrag_bridge.py::build_structure_factor_grid`
- `nanobrag_torch.Simulator.run()`
- `tests/dbex/test_torch_refine_smoke.py::refgeom_dataload`

## Next Up

**If HKL grid zero**: Fix MTZ loading
**If crystal invalid**: Fix crystal config
**If cause unclear**: Escalate to Galph for deeper investigation
