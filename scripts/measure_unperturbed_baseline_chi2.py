#!/usr/bin/env python3
"""
Measure unperturbed baseline chi² for Stage A perturbation analysis.

Computes chi² at unperturbed baseline geometry (no refinement) to quantify
perturbation penalty and refinement recovery performance.

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
    python scripts/measure_unperturbed_baseline_chi2.py
"""

import sys
import json
import numpy as np
import torch
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    create_detector_config,
    create_beam_config,
    create_crystal_config,
)
from nanobrag_torch.simulator import Simulator
from nanobrag_torch.models.detector import Detector
from nanobrag_torch.models.crystal import Crystal

def compute_chi_squared(bragg_model, target, loss_mask, sigma_readout, sigma_floor_sq):
    """
    Compute variance-weighted chi² loss.
    
    Implements spec-db-core.md:57-68 variance model:
    V = I_model + sigma_readout^2, clamped to sigma_floor^2
    chi² = Sum((I_model - I_obs)^2 / V) over trusted pixels
    """
    # Variance denominator (detached to prevent attraction to zero)
    variance_raw = bragg_model.detach() + sigma_readout ** 2
    variance_denom = torch.maximum(variance_raw, sigma_floor_sq)
    
    # Chi-squared loss
    diff = bragg_model - target
    chi_squared = torch.sum((diff ** 2 / variance_denom) * loss_mask)
    
    return chi_squared.item()


def main():
    from argparse import Namespace

    print("\n=== Measuring Unperturbed Baseline Chi² ===\n")

    # Load data (same as test_stage_a_expansion fixture)
    print("Loading data from tests/fixtures/golden_data/refGeom.expt...")
    repo_root = Path(__file__).parent.parent

    args = Namespace(
        exptName=str(repo_root / "tests/fixtures/golden_data/refGeom.expt"),
        reflName=str(repo_root / "tests/fixtures/golden_data/refGeom.refl"),
        exptIdx=0,
        maskFile=str(repo_root / "tests/fixtures/golden_data/masked.pickle"),
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
    )

    dataload = DataLoad(args)
    
    # Get unperturbed geometry
    detector = dataload.Expt.detector
    beam = dataload.Expt.beam
    crystal = dataload.Expt.crystal
    
    print(f"  Detector: {len(detector)} panels")
    print(f"  Crystal: {crystal.get_unit_cell()}")
    
    # Load HKL grid
    print("\nLoading HKL grid...")
    hkl_path = Path("tests/fixtures/golden_data/hkl_grids/thermolysin_grid_halo1.pt")
    if not hkl_path.exists():
        print(f"ERROR: HKL grid not found at {hkl_path}")
        return 1
    
    hkl_data = torch.load(hkl_path)
    hkl_grid = hkl_data['grid']
    hkl_metadata = hkl_data['metadata']
    
    print(f"  Grid shape: {hkl_grid.shape}")
    print(f"  Grid device: {hkl_grid.device}")
    
    # Setup device/dtype
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    dtype = torch.float32
    
    print(f"\nUsing device: {device}, dtype: {dtype}")
    
    # Move data to device
    target = torch.from_numpy(dataload.roi_target_adu).to(device=device, dtype=dtype)
    loss_mask = torch.from_numpy(dataload.roi_loss_mask).to(device=device, dtype=torch.bool)
    sigma_readout = torch.from_numpy(dataload.roi_sigma_readout).to(device=device, dtype=dtype)
    hkl_grid_device = hkl_grid.to(device=device, dtype=dtype)
    
    # Sigma floor
    sigma_floor_value = 1.0  # Default from RefinementConfig
    sigma_floor_sq = torch.tensor(sigma_floor_value ** 2, device=device, dtype=dtype)
    
    print(f"\nTarget shape: {target.shape}")
    print(f"Loss mask coverage: {loss_mask.float().mean().item():.1%}")
    
    # Create detector/beam/crystal configs (unperturbed)
    print("\nCreating simulator with unperturbed geometry...")
    beam_config = create_beam_config(beam)
    
    # Simulate all panels
    n_panels = len(detector)
    bragg_panels = []
    
    for panel_id in range(n_panels):
        panel = detector[panel_id]
        
        # Create detector config
        detector_config = create_detector_config(
            panel=panel,
            beam=beam,
            trusted_mask=dataload.trusted_mask[panel_id],
        )
        
        # Tensorize mask if needed
        mask_array = detector_config.mask_array
        if mask_array is not None and not isinstance(mask_array, torch.Tensor):
            mask_array = torch.tensor(mask_array, dtype=torch.float32, device=device)
            detector_config.mask_array = mask_array
        elif mask_array is not None and (mask_array.device != device or mask_array.dtype != torch.float32):
            mask_array = mask_array.to(device=device, dtype=torch.float32)
            detector_config.mask_array = mask_array
        
        detector_model = Detector(detector_config, device=device, dtype=dtype)
        
        # Create crystal config (unperturbed, no overrides)
        crystal_config, _ = create_crystal_config(
            crystal,
            None,  # No structure factors override
            crystal_overrides={},  # No perturbations
            misset_deg_override=None
        )
        
        crystal_model = Crystal(
            crystal_config,
            beam_config=beam_config,
            device=device,
            dtype=dtype
        )
        
        # Set HKL grid
        crystal_model.interpolate = True  # Enable tricubic interpolation
        crystal_model.hkl_data = hkl_grid_device
        crystal_model.hkl_metadata = hkl_metadata
        
        # Create simulator
        simulator = Simulator(
            detector=detector_model,
            crystal=crystal_model,
            beam_config=beam_config,
            device=device,
            dtype=dtype
        )
        
        # Run forward simulation
        bragg_panel = simulator.run()
        bragg_panels.append(bragg_panel)
        
        if (panel_id + 1) % 10 == 0 or panel_id == n_panels - 1:
            print(f"  Simulated {panel_id + 1}/{n_panels} panels...")
    
    # Stack panels
    bragg_stacked = torch.stack(bragg_panels, dim=0)
    
    print(f"\nBragg shape: {bragg_stacked.shape}")
    print(f"Bragg range: [{bragg_stacked.min().item():.2e}, {bragg_stacked.max().item():.2e}]")
    
    # Compute chi² at unperturbed baseline (scale=1.0, no refinement)
    chi_squared_unperturbed = compute_chi_squared(
        bragg_stacked,
        target,
        loss_mask,
        sigma_readout,
        sigma_floor_sq
    )
    
    print(f"\n=== Results ===")
    print(f"Unperturbed baseline chi²: {chi_squared_unperturbed:.2e}")
    
    # Load baseline test results for comparison
    baseline_telemetry_path = Path("plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/telemetry_small.json")
    
    if baseline_telemetry_path.exists():
        with open(baseline_telemetry_path) as f:
            baseline_data = json.load(f)
        
        # Extract chi² values from baseline test
        chi2_trace = baseline_data.get('chi_squared_trace_full', [])
        if chi2_trace:
            perturbed_initial_chi2 = chi2_trace[0][1]
            refined_final_chi2 = chi2_trace[-1][1]
            
            print(f"\nComparison with baseline test:")
            print(f"  Unperturbed baseline: {chi_squared_unperturbed:.2e}")
            print(f"  Perturbed initial:    {perturbed_initial_chi2:.2e}")
            print(f"  Refined final:        {refined_final_chi2:.2e}")
            
            # Compute perturbation penalty and recovery
            perturbation_penalty = perturbed_initial_chi2 - chi_squared_unperturbed
            perturbation_penalty_pct = (perturbed_initial_chi2 / chi_squared_unperturbed - 1) * 100
            
            recovery = perturbed_initial_chi2 - refined_final_chi2
            recovery_pct = (recovery / perturbation_penalty) * 100 if perturbation_penalty > 0 else 0
            
            residual_error = refined_final_chi2 - chi_squared_unperturbed
            residual_error_pct = (refined_final_chi2 / chi_squared_unperturbed - 1) * 100
            
            print(f"\nPerturbation Analysis:")
            print(f"  Penalty (unperturbed → perturbed): {perturbation_penalty:+.2e} ({perturbation_penalty_pct:+.1f}%)")
            print(f"  Recovery (perturbed → refined):    {recovery:+.2e} ({recovery_pct:.1f}% of penalty)")
            print(f"  Residual error (refined vs unperturbed): {residual_error:+.2e} ({residual_error_pct:+.1f}%)")
            
            # Save results
            output_path = Path("plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/unperturbed_chi2_analysis.json")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            results = {
                "chi2_unperturbed": chi_squared_unperturbed,
                "chi2_perturbed_initial": perturbed_initial_chi2,
                "chi2_refined_final": refined_final_chi2,
                "perturbation_penalty": perturbation_penalty,
                "perturbation_penalty_pct": perturbation_penalty_pct,
                "recovery_chi2": recovery,
                "recovery_pct": recovery_pct,
                "residual_error": residual_error,
                "residual_error_pct": residual_error_pct,
                "device": str(device),
                "dtype": str(dtype),
            }
            
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\nResults saved to: {output_path}")
    else:
        print(f"\nWARNING: Baseline telemetry not found at {baseline_telemetry_path}")
        print("Cannot compute perturbation/recovery analysis")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
