# Stage A Refinement Output — Unperturbed Configuration

Generated: 2025-11-24
Configuration: Per spec-db-workflow.md §68-95 (Canonical Initial Configuration)

## Summary

This directory contains outputs from a Stage A refinement run starting from an **unperturbed (zero-iteration) configuration**, which provides the canonical mapping-aligned forward simulation per spec-db-conformance.md §63-100 (DB-AT-024).

### Configuration Used

- **Geometry**: `refGeom.expt` / `refGeom.refl` (canonical)
- **Structure Factors**: `scaled.mtz` (raw, not refined)
- **Trusted Mask**: `747_mask.pkl`
- **Sigma Readout**: 3.0 ADU (CLI override via `--sigma-rdout`)
- **Sigma Floor**: 1.0 (default per spec-db-core.md §86-90)
- **Backend**: nanobrag (PyTorch-based)
- **Device**: CUDA (cuda:0)

### Refinement Status

**Stage A optimization encountered a CUDA/torch.compile error** and did not complete iterative refinement:
```
Error: accessing tensor output of CUDAGraphs that has been overwritten by a subsequent run
```

However, the **zero-iteration forward simulation completed successfully**, which provides:
- Experimental data (observed)
- Model prediction from unperturbed geometry (pre-refinement baseline)
- Residual analysis (Z-scores)

This zero-iteration output represents the **mapping-aligned Stage-A no-op** configuration per spec-db-vis.md §40-44, which is the correct baseline for "before refinement" visualizations.

## Output Files

### 1. HDF5 Data (`stage_a_refinement.h5`)

Per spec-db-interfaces.md, contains:
- `data/roi%d`: Experimental observed intensities (92 ROIs)
- `model/roi%d`: Model predictions from zero-iteration forward simulation
- `bragg/roi%d`: Bragg component only (no background)
- `bg/roi%d`: Background component
- `variance/roi%d`: Variance per pixel (V = max(I_model + σ_rdout², σ_floor²))
- `score`: Correlation coefficient per ROI (0-1 scale)
- `bragg_scale`: Optimized Bragg scaling factors per ROI

**Metadata** (per spec-db-core.md §86-90):
- `sigma_readout`: 3.0 (ADU)
- `sigma_floor`: 1.0 (ADU)

**Torch Diagnostics** (`/torch_diagnostics` group):
- `masked_mse`: 981,637.6 (zero-iteration chi-squared)
- `loss_mask_coverage`: 0.21% (fraction of pixels in loss mask)
- `n_rois`: 92
- `hkl_n_reflections`: 69,614 (structure factors)
- `sigma_readout_provenance`: "cli_override"
- Full refinement telemetry (status=error due to CUDA issue)

### 2. ROI Comparison Triptychs

**Individual Triptychs** (`triptychs_auto/roi_XXXX_triptych.png`):
- 92 PNG files, one per ROI
- Layout per spec-db-vis.md §14-24: `[Observed Data | Model Prediction | Residual Z-Score]`
- Colormaps: Viridis (intensity), Seismic (residuals)
- Origin: upper (slow axis = vertical top→bottom)

**Summary Visualization** (`roi_comparison_summary.png`):
- First 3 ROIs displayed in grid layout
- Shows observed data, model (post-zero-iter), and Z-score residuals

### 3. Loss Curve

**Not generated** - The refinement did not complete iterative optimization due to the CUDA error, so there is no loss trace. The only loss value recorded is the zero-iteration masked MSE: **981,637.6**.

## ROI Scoring Results

- **Total ROIs**: 92
- **Average Correlation**: 21.8% ± 25.0%
- **Well-modeled spots**: 21.7%

Many ROIs have CC=0 because the zero-iteration model (unperturbed geometry with raw MTZ) produces poor matches. This is expected for the baseline configuration.

**Top-scoring ROIs** (CC > 60%):
- ROI 0: 61.4%
- ROI 26: 65.0%
- ROI 30: 66.2%
- ROI 46: 66.6%
- ROI 48: 66.9%
- ROI 56: 67.4%
- ROI 83: 67.3%

## Interpretation

This output represents the **"before refinement"** baseline:
1. **Experimental data**: Observed diffraction pattern from experiment
2. **Model (pre-refinement)**: Forward simulation using unperturbed DIALS geometry and raw structure factors
3. **Residuals**: Z-scores showing discrepancies between data and model

The moderate correlation scores (21.8% average) and significant residuals indicate that refinement would improve the model fit. However, the iterative refinement step failed due to the CUDA environment issue.

## Next Steps

To obtain a **post-refinement** comparison:
1. Resolve the CUDA/torch.compile error (likely requires environment fix or disabling compile)
2. Re-run with `NANOBRAGG_DISABLE_COMPILE=1` environment variable to bypass torch.compile
3. Or use the diffbragg backend instead of nanobrag for a working refinement

## Viewing Outputs

Interactive HDF5 viewer:
```bash
python -m dbex.look stage_a_refinement.h5
```

View individual triptychs:
```bash
ls triptychs_auto/
```

## References

- spec-db-workflow.md §68-95: Canonical Initial Configuration
- spec-db-core.md §86-90: Variance Model
- spec-db-vis.md §14-24: ROI Triptych Layout
- spec-db-conformance.md §63-100: DB-AT-024 Mapping Consistency
- docs/TESTING_GUIDE.md §1.1: Required Environment Variables
