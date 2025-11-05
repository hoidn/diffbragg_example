"""Quick probe to inspect LBFGS telemetry from Stage A expansion."""

import sys
sys.path.insert(0, '/home/ollie/Documents/diffbragg_example_2/diffbragg_example')

from pathlib import Path
import torch
import numpy as np

# Setup fixtures
from argparse import Namespace
from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import prepare_refinement_inputs, build_structure_factor_grid
from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig

repo_root = Path('/home/ollie/Documents/diffbragg_example_2/diffbragg_example')

# Load data
args = Namespace(
    exptName=str(repo_root / "refGeom.expt"),
    reflName=str(repo_root / "refGeom.refl"),
    exptIdx=0,
    maskFile=str(repo_root / "747_mask.pkl"),
    mtzFile=str(repo_root / "scaled.mtz"),
    mtzCol="F,SIGF"
)

data_load = DataLoad(args)

# Build trusted mask
detector = data_load.Expt.detector
n_panels = len(detector)
trusted_masks = []
for pid in range(n_panels):
    panel = detector[pid]
    image_size = panel.get_image_size()
    mask = np.ones(image_size[::-1], dtype=bool)
    trusted_masks.append(mask)

# Prepare inputs
inputs = prepare_refinement_inputs(
    data=data_load.data,
    background_image=data_load.background_image,
    trusted_mask=trusted_masks,
    bbox=data_load.bbox,
    pids=data_load.pids,
    detector=data_load.Expt.detector,
    adu_per_photon=None
)

# Build HKL
hkl_indices = data_load.F.indices()
hkl_amplitudes = data_load.F.data()
hkl_grid, hkl_metadata = build_structure_factor_grid(
    indices=hkl_indices,
    amplitudes=hkl_amplitudes,
    device=torch.device('cpu')
)

# Configure
config = RefinementConfig(
    device='cpu',
    dtype=torch.float32,
    history_size=10,
    max_iter=30,
    roi_sample_fraction=0.15,
    full_validation_interval=5,
    min_loss_improvement=0.05
)

# Run
bragg_refined, telemetry = run_nanobrag_refinement(
    inputs=inputs,
    detector=data_load.detector,
    beam=data_load.beam,
    crystal=data_load.crystal,
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    config=config
)

# Print telemetry
print("=== LBFGS Telemetry ===")
print(f"Status: {telemetry.status}")
print(f"Message: {telemetry.message}")
print(f"Iterations: {len(telemetry.loss_trace_sample)}")
print(f"Sample loss trace (first 5): {telemetry.loss_trace_sample[:5]}")
print(f"Sample loss trace (last 5): {telemetry.loss_trace_sample[-5:]}")
print(f"Full loss trace: {telemetry.loss_trace_full}")
print(f"Best loss (full): {telemetry.best_loss_full}")

print("\n=== Parameter Deltas ===")
for param_name, delta_info in telemetry.param_deltas.items():
    print(f"{param_name}:")
    if isinstance(delta_info.get('delta'), list):
        print(f"  initial: {delta_info['initial']}")
        print(f"  final: {delta_info['final']}")
        print(f"  norm: {delta_info.get('norm', 'N/A')}")
    else:
        print(f"  initial: {delta_info['initial']:.6f}")
        print(f"  final: {delta_info['final']:.6f}")
        print(f"  delta: {delta_info['delta']:.6f}")

# Calculate improvement
if len(telemetry.loss_trace_full) >= 2:
    initial_loss = telemetry.loss_trace_full[0][1]
    final_loss = telemetry.loss_trace_full[-1][1]
    improvement = (initial_loss - final_loss) / initial_loss
    print(f"\n=== Improvement Analysis ===")
    print(f"Initial loss: {initial_loss:.6e}")
    print(f"Final loss: {final_loss:.6e}")
    print(f"Improvement: {improvement:.2%}")
    print(f"Target: 5.00%")
    print(f"Gap: {(0.05 - improvement) * 100:.2f}%")
