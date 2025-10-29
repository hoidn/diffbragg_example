# NANOBRAG-GOLDEN-001 Loop Planning Notes (2025-10-29T091339Z)

## Status
**BLOCKED** - torch zero-output persists despite scaling fix

## Objective
Execute input.md Do Now: inject DiffBragg global scale into structure factor grid, log raw torch intensities, verify non-zero panels, and prepare parity validation.

## Implementation Summary

### Code Changes
Modified `scripts/generate_simple_cubic_golden.py`:
1. Added detailed amplitude logging before/after scaling (lines 114-120)
2. Added structure factor grid statistics logging (lines 142-147)
3. Added raw simulator output logging immediately after `simulator.run()` (lines 495-500)

### Canonical Capture Results

#### DiffBragg Baseline (SUCCESS)
- Refinement converged: 5 macro cycles, Resid=192876.84, sigZ=6.28
- Baseline tensor: `bragg_diffbragg.npy` (24M)
- Max intensity: 36,169.54
- Nonzero pixels: 97,131
- Spot scale: 3.186e+17

#### Structure Factor Grid (SUCCESS)
- BEFORE scaling: amps min=1.546, max=518.3, mean=47.41
- Scale factor applied: sqrt(3.186e+17) = 5.645e+08
- AFTER scaling: amps min=8.728e+08, max=2.926e+11, mean=2.676e+10
- HKL grid: 69,614 reflections, 100% in-range
- Grid stats: min=0, max=2.926e+11, mean=1.059e+10, nonzero=69,614

#### nanobrag_torch Simulator (BLOCKED)
- Raw output: device=cuda:0, dtype=torch.float32, shape=[2527, 2463]
- **min=0.0, max=0.0, mean=0.0, nonzero=0**
- nanoBragg banner shows: "incident fluence: 1e+18 photons/m^2"
- BeamConfig: flux=1e12, beamsize_mm=1.0, exposure=1.0, wavelength_A=0.9768
- CrystalConfig: N_cells=(36, 28, 26), mosflm_a_star/b_star/c_star set
- DetectorConfig: oversample=1, distance_mm=231.3, pixel_size_mm=0.172
- HKL data assigned to `crystal_model.hkl_data` (grid on cuda:0)

## Root Cause Analysis

### Known Facts
1. Structure factors are being scaled correctly - we see them go from ~500 max to 2.9e+11 max
2. HKL grid is populated correctly - 69,614 nonzero elements, 100% in-range
3. Beam parameters are set - flux, beamsize, exposure all present
4. nanoBragg C++ code is running - we see the banner printout
5. Output tensor is correctly allocated - shape [2527, 2463] on cuda:0
6. **Output is exactly zero** - no nonzero pixels at all

### Hypotheses

#### H1: Scale Magnitude Overflow
- Structure factor amplitudes are 2.9e+11, which might overflow in nanoBragg's internal calculations
- nanoBragg expects structure factors in electron units, not arbitrary scaled values
- Multiplying by sqrt(3.186e+17) = 5.645e+08 might be too aggressive
- **Test**: Try using the DiffBragg scale parameter differently, or scaling output intensities instead of input structure factors

#### H2: nanobrag_torch API Mismatch
- The way we're assigning `crystal_model.hkl_data = torch_grid` might not be the correct API
- There may be additional initialization or configuration needed after setting hkl_data
- The hkl_metadata might need to be passed differently
- **Test**: Inspect nanobrag_torch source code for proper HKL data assignment pattern

#### H3: Missing Parameter
- Some critical parameter is missing that causes nanoBragg to skip all calculations
- Could be related to mosaic domains, phi steps, or other crystal parameters
- The nanoBragg banner shows "1 mosaic domains over mosaic spread of 0 degrees" which might be problematic
- **Test**: Check nanobrag_torch examples for required parameters we might be missing

#### H4: Device/Memory Issue
- The grid is on cuda:0 but something in the simulator chain expects CPU
- Or there's a CUDA memory issue that causes silent failure
- **Test**: Try moving grid to CPU, or inspecting CUDA error state after simulator.run()

## Diagnostic Evidence

### From canonical_capture.log (tail -100)
```
INFO: BEFORE scaling: amps min=1.546e+00, max=5.183e+02, mean=4.741e+01
INFO: Scaling structure factors by sqrt(scale_override)=5.645e+08
INFO: AFTER scaling: amps min=8.728e+08, max=2.926e+11, mean=2.676e+10
INFO: Structure factor grid stats: min=0.000e+00, max=2.926e+11, mean=1.059e+10, nonzero=69614
INFO: HKL grid: 69614/69614 reflections in range (100.0%)
INFO: Panel 0 RAW torch output: device=cuda:0, dtype=torch.float32, shape=torch.Size([2527, 2463]), min=0.000000e+00, max=0.000000e+00, mean=0.000000e+00, nonzero=0
```

### From torch/panel_metrics.json
```json
{
  "panel_id": 0,
  "torch_max": 0.0,
  "torch_sum": 0.0,
  "loss_mask_coverage": 0.002102506
}
```

### From torch_hkl_debug.json
```json
{
  "n_reflections": 69614,
  "n_in_range": 69614,
  "in_range_fraction": 1.0,
  "grid_nonzero": 69614,
  "grid_min": 0.0,
  "grid_max": 292557619968.0,
  "grid_mean": 10589476096.0
}
```

## Next Actions

### Per Environment Freeze Policy
Cannot install/upgrade packages or modify toolchain. Must work with existing nanobrag_torch 0.1.0.

### Options
1. **Escalate to supervisor** - This requires nanobrag_torch maintainer expertise or source inspection
2. **Test alternative scaling approach** - Instead of scaling structure factors by sqrt(scale), try:
   - Scaling output intensities by the full scale factor
   - Using log-scale structure factors
   - Normalizing structure factors to reasonable electron units first
3. **Inspect nanobrag_torch source** - Look for:
   - Proper HKL data assignment API
   - Examples of structure factor grid setup
   - Any validation or sanitization that might zero out large values
4. **DiffBragg-only golden dataset** - Downgrade scope to use only DiffBragg baseline for parity tests

## Artifacts
- `planning_notes.md` (this file)
- `canonical_capture.log` (897 KB, full capture trace)
- `golden_dataset/legacy/bragg_diffbragg.npy` (24M, max=36,169.54)
- `golden_dataset/torch/bragg_torch.npy` (24M, all zeros)
- `torch_hkl_debug.json` (HKL statistics)
- `golden_dataset/torch/panel_metrics.json` (per-panel stats)
- `golden_dataset/metrics.json` (parity summary, NaN correlations)

## Blockers
1. nanobrag_torch Simulator produces all-zero output despite:
   - Correct structure factor grid (69,614 nonzero, properly scaled)
   - Correct beam parameters (flux, beamsize, exposure)
   - Correct crystal parameters (N_cells, orientation)
   - Correct detector parameters (distance, pixel size, oversample)
2. No error messages or warnings from nanobrag_torch
3. nanoBragg C++ banner prints correctly, suggesting initialization succeeded
4. Root cause unclear - could be scale overflow, API mismatch, missing parameter, or device issue

## Findings to Document
- **TORCH-SCALE-001**: Scaling structure factors by sqrt(DiffBragg scale_override) produces values up to 2.9e+11, which may overflow nanobrag_torch internal calculations
- **TORCH-SILENT-ZERO-001**: nanobrag_torch Simulator can produce all-zero output without raising exceptions or logging warnings, making debugging difficult
