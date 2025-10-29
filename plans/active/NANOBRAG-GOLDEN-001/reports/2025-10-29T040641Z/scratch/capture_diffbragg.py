#!/usr/bin/env python
"""
Capture DiffBragg forward-only Bragg tensor without refinement.
Used for NANOBRAG-GOLDEN-001 Phase A2: DiffBragg baseline export.
"""
import sys
import numpy as np
from dbex.data_load import DataLoad
from dbex.run_diffbragg import run_diffbragg

def main():
    expt_path = "refGeom.expt"
    refl_path = "refGeom.refl"
    mtz_path = "scaled.mtz"
    mask_path = "747_mask.pkl"
    expt_idx = 0
    mtz_col = "F,SIGF"

    # Create args object matching DataLoad expectations
    class Args:
        def __init__(self):
            self.exptName = expt_path
            self.reflName = refl_path
            self.mtzFile = mtz_path
            self.maskFile = mask_path
            self.exptIdx = expt_idx
            self.mtzCol = mtz_col

    args = Args()

    print(f"Loading data from {expt_path}, {refl_path}, {mtz_path}")
    DL = DataLoad(args)

    print(f"Running DiffBragg forward model (devId=0)...")
    Bragg = run_diffbragg(DL, devId=0)

    print(f"Bragg tensor shape: {Bragg.shape}, dtype: {Bragg.dtype}")
    print(f"Bragg tensor stats: min={Bragg.min():.2f}, max={Bragg.max():.2f}, mean={Bragg.mean():.2f}")

    # Save the Bragg tensor
    out_path = "plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/golden_dataset/legacy/bragg_diffbragg.npy"
    np.save(out_path, Bragg)
    print(f"Saved DiffBragg Bragg tensor to {out_path}")

    # Save metadata
    meta_path = "plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/golden_dataset/legacy/metadata.txt"
    with open(meta_path, 'w') as f:
        f.write(f"DiffBragg Forward Baseline\n")
        f.write(f"=========================\n\n")
        f.write(f"Input files:\n")
        f.write(f"  Experiment: {expt_path}\n")
        f.write(f"  Reflections: {refl_path}\n")
        f.write(f"  MTZ: {mtz_path}\n")
        f.write(f"  Mask: {mask_path}\n")
        f.write(f"  Experiment index: {expt_idx}\n")
        f.write(f"  MTZ columns: {mtz_col}\n\n")
        f.write(f"Output:\n")
        f.write(f"  Shape: {Bragg.shape}\n")
        f.write(f"  Dtype: {Bragg.dtype}\n")
        f.write(f"  Min: {Bragg.min():.6f}\n")
        f.write(f"  Max: {Bragg.max():.6f}\n")
        f.write(f"  Mean: {Bragg.mean():.6f}\n")
        f.write(f"  Std: {Bragg.std():.6f}\n")
        f.write(f"  n_rois: {len(DL.bbox)}\n")
    print(f"Saved metadata to {meta_path}")

if __name__ == '__main__':
    main()
