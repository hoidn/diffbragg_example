# NANOBRAG-GOLDEN-001 Loop Summary (2025-10-29T084244Z)

## Status
**PARTIAL COMPLETION - BLOCKED** by nanobrag_torch zero-output issue

## Completed Tasks

### A3: Canonical Capture Implementation
- ✓ Completely rewrote `scripts/generate_simple_cubic_golden.py` to implement canonical DiffBragg + nanobrag_torch capture pipeline
- ✓ Added HKL sanity instrumentation (`build_structure_factor_grid` with in-range tracking)
- ✓ Integrated DiffBragg 5-macro-cycle refinement with structure factor optimization
- ✓ Captured DiffBragg baseline: `bragg_diffbragg.npy` (24M, max=36165.40)
- ✓ Configured BeamConfig with **FIX**: `flux=1e12`, `beamsize_mm=1.0`, `exposure=1.0` (previously missing)
- ✓ Built HKL structure factor grid: 69,614 reflections, 100% in-range
- ✓ Emitted provenance metadata, config JSONs, and HKL debug artifacts

### B1/B2: Artifact Emission
- ✓ Saved to `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T084244Z/golden_dataset/`
  - `legacy/bragg_diffbragg.npy` + `config_diffbragg.json`
  - `torch/bragg_torch.npy` + `config_torch.json` + `panel_metrics.json` + target/loss_mask
  - `logs/canonical_capture.log` (897 KB, full refinement trace)
  - `torch_hkl_debug.json` (HKL stats: 100% in-range)
  - `metrics.json` + `roi_metrics.csv`

## Blocker Details

### Torch Zero-Output Issue
**Problem**: nanobrag_torch Simulator produces all-zero intensity despite correct configuration

**Evidence**:
- DiffBragg baseline: max=36165.40, 97,131 nonzero pixels
- Torch baseline: max=0.00, **0 nonzero pixels**
- Panel metrics: `torch_max=0.0`, `torch_sum=0.0`
- Parity metrics: `median_correlation=NaN`, `localization_success_rate=0.0`

**Configuration Verified**:
1. ✓ BeamConfig: flux=1e12, beamsize_mm=1.0, exposure=1.0, wavelength_A=0.9768
2. ✓ CrystalConfig: N_cells=(36, 28, 26), mosflm_a_star/b_star/c_star set
3. ✓ DetectorConfig: oversample=1, distance_mm=231.3, pixel_size_mm=0.172
4. ✓ HKL grid: 69,614 structure factors, 100% in-range, grid_nonzero=69,614
5. ✓ Device: cuda:0 (GeForce RTX 3090)

**Prior Hypothesis (WRONG)**: Missing flux/beamsize/exposure in BeamConfig
- **Fix Applied**: Added `flux=float(SIM_fhkl.D.flux)`, `beamsize_mm=float(SIM_fhkl.D.beamsize_mm)`, `exposure=1.0` to BeamConfig (lines 393-395 of generate_simple_cubic_golden.py)
- **Outcome**: Flux/beamsize now present in config_torch.json, but torch output still zero

**New Hypothesis**: Missing scale application to structure factors OR nanobrag_torch API issue
- DiffBragg uses `spot_scale_override=3.19e17` which multiplies output
- nanobrag_torch CrystalConfig has no `scale` parameter
- Per docs/config_crosswalk.md:71: "No `no_Nabc_scale` in torch; use global scale to absorb lattice magnitude differences"
- **Unclear**: Should structure factor *amplitudes* be multiplied by sqrt(scale) before grid assignment?
- **Unclear**: Is there a separate fluence/scale factor that needs to be applied?

### Next Debugging Steps (Proposed)
1. Inspect nanobrag_torch source to understand scaling/fluence application
2. Test minimal reproducer: simple cubic lattice, single HKL, confirm nonzero output
3. Compare nanobrag_torch BeamConfig fluence calculation with DiffBragg flux*exposure*beamsize²
4. Check if CrystalConfig.fudge parameter affects intensity (currently using default)
5. Verify DetectorConfig mask_array isn't zero-masking all pixels (currently using trusted_mask)

## Artifacts

### Captured Tensors
- `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T084244Z/golden_dataset/legacy/bragg_diffbragg.npy`: 24M (SHA256 pending)
- `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T084244Z/golden_dataset/torch/bragg_torch.npy`: 24M (all zeros)
- `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T084244Z/golden_dataset/torch/target_panel_0.npy`: 24M
- `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T084244Z/golden_dataset/torch/loss_mask_panel_0.npy`: 6M

### Metadata & Logs
- `canonical_capture.log`: 897 KB (DiffBragg refinement trace, 5 macro cycles)
- `config_diffbragg.json`: DiffBragg parameters (flux=1e12, beamsize_mm=1.0, oversample=1)
- `config_torch.json`: Torch parameters (flux=1e12, beamsize_mm=1.0, exposure=1.0)
- `torch_hkl_debug.json`: HKL statistics (100% in-range, 69,614 nonzero)
- `panel_metrics.json`: Per-panel stats (torch_max=0.0 BLOCKER)
- `metrics.json`: Parity summary (correlation=NaN, localization=0.0%)
- `roi_metrics.csv`: Per-ROI correlations (all NaN due to torch zeros)

## Code Changes
- **scripts/generate_simple_cubic_golden.py**: Completely rewritten (611 lines)
  - Replaced synthetic Gaussian stub with canonical DiffBragg refinement pipeline
  - Added `to_native()`, `build_structure_factor_grid()`, `compute_roi_metrics()` helpers
  - Integrated 5-macro-cycle refinement with structure factor optimization
  - Added flux/beamsize/exposure to TorchBeamConfig (CRITICAL FIX, but insufficient)
  - Added HKL in-range instrumentation and debug JSON emission
  - Added logging, provenance metadata, and artifact organization per spec

## Metrics
- DiffBragg refinement: 5 macro cycles, converged (F=678151, sigZ=12.27)
- DiffBragg baseline: max=36165.40, mean(nonzero)=12.1, 97,131 nonzero pixels
- Torch baseline: **max=0.00**, **0 nonzero pixels** ❌
- HKL grid: 69,614 reflections, 100% in-range, grid_nonzero=69,614 ✓
- Execution time: ~180s (DiffBragg refinement), ~15s (torch capture)

## Next Actions
1. **Escalate to supervisor**: Torch zero-output blocker requires nanobrag_torch expertise or source inspection
2. **Alternative paths**:
   - Defer torch baseline; use DiffBragg-only golden dataset for parity harness (downgrade scope)
   - Request nanobrag_torch maintainer guidance on scale/fluence application
   - Instrument nanobrag_torch Simulator.run() with debug_config to trace zero-output cause
3. **If unblocked**: Copy tensors to `tests/fixtures/golden_data/simple_cubic/`, update manifest.json, run parity tests

## Findings to Document
- **TORCH-FLUX-001**: nanobrag_torch TorchBeamConfig requires explicit `flux`, `beamsize_mm`, `exposure` parameters; omitting them silently produces zero output (though this fix alone was insufficient)
- **TORCH-HKL-001**: HKL grid 100% in-range is necessary but not sufficient for nonzero output; scale/fluence application mechanism unclear
