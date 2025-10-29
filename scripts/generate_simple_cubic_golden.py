#!/usr/bin/env python
"""
Generate simple cubic golden data for DB-AT-001 parity harness.

Per docs/parity_harness_spec.md:28-41 and input.md:21-22:
- Creates minimal representative golden dataset for parity testing
- Uses refGeom experiment as geometry basis
- Generates synthetic Bragg prediction for simple cubic lattice
- Stores tensors as .npy files with manifest.json + SHA256 checksums

Output structure:
    tests/fixtures/golden_data/simple_cubic/
    ├── manifest.json           # Dataset metadata + checksums
    ├── bragg_panel_0.npy      # Predicted Bragg intensities [slow, fast]
    ├── target_panel_0.npy     # Background-subtracted targets [slow, fast]
    ├── loss_mask_panel_0.npy  # Loss mask [slow, fast] bool
    └── metadata.json          # Detector/beam/crystal config snapshot

This is a FALLBACK implementation pending availability of canonical nanoBragg2 golden data.
"""

import sys
import json
import hashlib
import numpy as np
from pathlib import Path
from argparse import Namespace

# Add repo root to path for imports
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    prepare_refinement_inputs,
    create_detector_config,
    create_beam_config,
    create_crystal_config,
)


def compute_sha256(file_path):
    """Compute SHA256 checksum for a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def generate_simple_cubic_golden(output_dir: Path):
    """
    Generate simple cubic golden dataset using refGeom experiment.

    Args:
        output_dir: Path to tests/fixtures/golden_data/simple_cubic/
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load refGeom experiment
    print("Loading refGeom experiment...")
    args = Namespace(
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
        exptName=str(repo_root / "refGeom.expt"),
        exptIdx=0,
        reflName=str(repo_root / "refGeom.refl")
    )

    try:
        dl = DataLoad(args)
    except Exception as e:
        print(f"ERROR: Failed to load DataLoad: {e}")
        print("Ensure refGeom.refl exists (see test_nanobrag_smoke.py docstring)")
        sys.exit(1)

    # Build trusted masks
    detector = dl.Expt.detector
    trusted_masks = []
    for panel in detector:
        fast_px, slow_px = panel.get_image_size()
        panel_mask = np.ones((slow_px, fast_px), dtype=bool)
        if hasattr(panel, 'get_mask') and panel.get_mask():
            for rect in panel.get_mask():
                x0, y0, x1, y1 = rect
                panel_mask[y0:y1, x0:x1] = False
        trusted_masks.append(panel_mask)
    trusted_masks = np.array(trusted_masks, dtype=bool)

    # Prepare refinement inputs
    print("Preparing refinement inputs...")
    inputs = prepare_refinement_inputs(
        data=dl.data,
        background_image=dl.background_image,
        trusted_mask=trusted_masks,
        bbox=dl.bbox,
        pids=dl.pids,
        detector=detector
    )

    # Create detector/beam/crystal configs for metadata
    print("Hydrating detector/beam/crystal configs...")
    beam_config = create_beam_config(dl.Expt.beam)
    crystal_config = create_crystal_config(dl.Expt.crystal, dl.Expt)

    detector_configs = []
    for panel_id, panel in enumerate(detector):
        config = create_detector_config(
            panel=panel,
            beam=dl.Expt.beam,
            trusted_mask=trusted_masks[panel_id]
        )
        detector_configs.append(config)

    # Generate synthetic Bragg prediction (simple Gaussian pattern on ROI support)
    # This is a STUB; replace with real nanobrag_torch simulator when available
    print("Generating synthetic Bragg prediction (stub)...")
    bragg = np.zeros_like(inputs.target)
    for panel_id, (pid, bbox) in enumerate(inputs.panel_slices):
        x0, x1, y0, y1 = bbox
        slow_size = y1 - y0
        fast_size = x1 - x0

        # Generate 2D Gaussian centered in the ROI
        slow_grid, fast_grid = np.meshgrid(
            np.linspace(-1, 1, slow_size),
            np.linspace(-1, 1, fast_size),
            indexing='ij'
        )
        gaussian = np.exp(-(slow_grid**2 + fast_grid**2) / 0.3)
        gaussian *= 500  # Scale to reasonable intensity

        bragg[pid, y0:y1, x0:x1] = gaussian

    bragg = bragg.astype(np.float32)

    # Save per-panel tensors (for simplicity, save only panel 0)
    # Full implementation would save all panels
    panel_id = 0

    print(f"Saving golden data for panel {panel_id}...")

    files_written = {}

    # Save Bragg tensor
    bragg_path = output_dir / f"bragg_panel_{panel_id}.npy"
    np.save(bragg_path, bragg[panel_id])
    files_written["bragg"] = str(bragg_path.name)

    # Save target tensor
    target_path = output_dir / f"target_panel_{panel_id}.npy"
    np.save(target_path, inputs.target[panel_id])
    files_written["target"] = str(target_path.name)

    # Save loss mask
    loss_mask_path = output_dir / f"loss_mask_panel_{panel_id}.npy"
    np.save(loss_mask_path, inputs.loss_mask[panel_id])
    files_written["loss_mask"] = str(loss_mask_path.name)

    # Save metadata
    metadata = {
        "provenance": "DBEX fallback golden data generator (simple cubic stub)",
        "source_experiment": str(args.exptName),
        "source_reflections": str(args.reflName),
        "source_mtz": str(args.mtzFile),
        "generation_date": "2025-10-29T010131Z",
        "panel_id": panel_id,
        "shape": {
            "bragg": list(bragg[panel_id].shape),
            "target": list(inputs.target[panel_id].shape),
            "loss_mask": list(inputs.loss_mask[panel_id].shape)
        },
        "beam_config": {
            "wavelength_A": beam_config.wavelength_A,
            "polarization_factor": beam_config.polarization_factor,
            "nopolar": beam_config.nopolar
        },
        "crystal_config": {
            "cell_a": crystal_config.cell_a,
            "cell_b": crystal_config.cell_b,
            "cell_c": crystal_config.cell_c,
            "cell_alpha": crystal_config.cell_alpha,
            "cell_beta": crystal_config.cell_beta,
            "cell_gamma": crystal_config.cell_gamma
        },
        "detector_config": {
            "distance_mm": detector_configs[panel_id].distance_mm,
            "beam_center_s": detector_configs[panel_id].beam_center_s,
            "beam_center_f": detector_configs[panel_id].beam_center_f,
            "beam_center_source": detector_configs[panel_id].beam_center_source,
            "spixels": detector_configs[panel_id].spixels,
            "fpixels": detector_configs[panel_id].fpixels,
            "pixel_size_mm": detector_configs[panel_id].pixel_size_mm
        },
        "notes": [
            "This is a FALLBACK dataset pending canonical nanoBragg2 golden data.",
            "Bragg tensor is synthetic (Gaussian pattern on ROI support).",
            "Target tensor is background-subtracted refGeom data.",
            "Replace with real parity baseline when available."
        ]
    }

    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    files_written["metadata"] = str(metadata_path.name)

    # Generate manifest with SHA256 checksums
    print("Computing SHA256 checksums...")
    manifest = {
        "dataset_name": "simple_cubic_fallback",
        "version": "1.0.0",
        "provenance": "DBEX fallback generator (pending canonical nanoBragg2 data)",
        "generation_date": "2025-10-29T010131Z",
        "spec_reference": "docs/parity_harness_spec.md:28-41",
        "files": {}
    }

    for key, filename in files_written.items():
        file_path = output_dir / filename
        sha256 = compute_sha256(file_path)
        manifest["files"][key] = {
            "filename": filename,
            "sha256": sha256,
            "dtype": str(np.load(file_path).dtype) if filename.endswith('.npy') else "json",
            "shape": list(np.load(file_path).shape) if filename.endswith('.npy') else None
        }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    # Compute manifest checksum
    manifest_sha256 = compute_sha256(manifest_path)

    print("\n" + "="*60)
    print("Golden data generation complete!")
    print("="*60)
    print(f"Output directory: {output_dir}")
    print(f"Files written: {len(files_written) + 1}")
    print(f"Manifest SHA256: {manifest_sha256}")
    print("\nFiles:")
    for key, info in manifest["files"].items():
        print(f"  {key:12} {info['filename']:30} {info['sha256'][:16]}...")
    print(f"  manifest     manifest.json                  {manifest_sha256[:16]}...")
    print("\nNOTE: This is a FALLBACK dataset. Replace with canonical nanoBragg2")
    print("      golden data when available per docs/parity_harness_spec.md:28-41")

    return manifest_path


if __name__ == "__main__":
    output_dir = repo_root / "tests/fixtures/golden_data/simple_cubic"
    manifest_path = generate_simple_cubic_golden(output_dir)

    print(f"\nManifest written to: {manifest_path}")
    print("Use this data for DB-AT-001 parity harness testing.")
