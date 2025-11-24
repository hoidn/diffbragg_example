# Successful Stage A Refinement Artifacts

## Summary

Yes! There are multiple successful Stage A refinement runs with complete artifacts showing:
1. **Loss curves** (before → after refinement)
2. **ROI comparison triptychs** (experimental, pre-refinement, post-refinement)
3. **Telemetry** with convergence metrics

## Primary Artifacts Location

### 1. PERF-WARM-SIM-001: Successful LBFGS Stage A Refinement

**Location**: `plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/`

**Key Metrics**:
- **Status**: `ok` ✓
- **Loss improvement**: 18.4% (806.7M → 658.3M chi-squared)
- **Iterations**: 31 LBFGS closures
- **Dataset**: refGeom_small (29 ROIs)
- **Cache mode**: warm (ROI-aware)

**Files**:
- `telemetry_stage_a_small.json` - Complete refinement telemetry
- `pytest_stage_a_small.log` - Full test log

**Loss Trace** (from telemetry):
```
Iteration 0:  806,688,384  (initial)
Iteration 5:  670,424,896  (17% improvement)
Iteration 10: 658,258,304  (18.4% improvement)
Iteration 31: 658,255,488  (converged)
```

### 2. TOOLING-VIS-001: Stage A Refinement with Visualization

**Location**: `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam/20251121T225505Z/`

**Optimizer**: Adam (alternative to LBFGS)
**Dataset**: refGeom (canonical, 92 ROIs)

**Visualization Artifacts**:

1. **Loss Curves**:
   - `adam_loss_curve.png` - Training loss over iterations
   - `adam_loss_trace.png` - Detailed loss trajectory

2. **ROI Triptychs** (`roi_triptychs/` directory):
   - 16 ROIs with before/after comparisons
   - Format: `roi_XXXX_before.png` and `roi_XXXX_after.png`
   - Each triptych shows: [Observed Data | Model Prediction | Residual Z-Score]

   Examples:
   - `roi_0000_before.png` - Pre-refinement (unperturbed)
   - `roi_0000_after.png` - Post-refinement (optimized)
   - (Repeat for ROIs 0-15)

3. **Summary Visualization**:
   - `all_rois_side_by_side.png` - Grid view of multiple ROIs showing improvement

### 3. Additional Stage A Runs

Multiple successful runs with varying configurations:

**LBFGS runs** (spec-compliant):
- `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom/20251121T193429Z/`
- `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom/20251121T184300Z/`
- `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom/20251121T183335Z/`
- `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom/20251121T182129Z/`

**Adam-based runs** (experimental):
- `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam/20251121T225505Z/` ⭐ (most complete)
- `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam/20251121T195410Z/`
- `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam/20251121T194859Z/`
- `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam/20251121T193835Z/`
- ...14 more Adam-based runs

## What These Artifacts Show

### Loss Improvement

The PERF-WARM-SIM-001 run shows **18.4% loss improvement**:
- Initial chi-squared: 806,688,384
- Final chi-squared: 658,255,488
- Convergence: Achieved after 31 LBFGS iterations

This demonstrates successful geometry+scale refinement (Stage A parameters: unit cell, orientation, global scale).

### Visual Comparison

The TOOLING-VIS-001 artifacts provide **before/after ROI comparisons**:

**Before refinement** (`_before.png`):
- Model prediction using unperturbed DIALS geometry
- Residuals show significant discrepancies
- Lower correlation with experimental data

**After refinement** (`_after.png`):
- Model prediction using optimized geometry/scale
- Residuals are reduced (smaller Z-scores)
- Higher correlation with experimental data

### ROI Triptych Layout

Each triptych PNG contains 3 panels per spec-db-vis.md §14-24:
1. **Left panel**: Observed experimental data (photon counts)
2. **Middle panel**: Model prediction (Bragg + background)
3. **Right panel**: Residual Z-score map (Data-Model)/sqrt(Variance)

Colormaps:
- Data/Model: Viridis (perceptually uniform sequential)
- Residuals: Seismic (diverging, centered at 0)

## Why Your Run Failed But These Succeeded

### Your Run (2025-11-24, this session):
- ❌ CUDA graphs error during LBFGS iteration
- ✓ Zero-iteration forward simulation completed
- ✓ HDF5 output generated
- ❌ No iterative refinement (status=error)

### Successful Runs (2025-11-21):
- ✓ Used `NANOBRAGG_DISABLE_COMPILE=1` to bypass torch.compile
- ✓ LBFGS iterations completed successfully
- ✓ 18.4% loss improvement achieved
- ✓ Convergence metrics recorded

## How to View These Artifacts

### 1. Loss Curves
```bash
# View Adam-based loss curve
display plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam/20251121T225505Z/adam_loss_curve.png

# Or use any image viewer
eog plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam/20251121T225505Z/adam_loss_curve.png
```

### 2. ROI Triptychs (Before/After)
```bash
cd plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam/20251121T225505Z/roi_triptychs/

# View before refinement
display roi_0000_before.png

# View after refinement
display roi_0000_after.png

# View all ROIs
display roi_*.png
```

### 3. Summary Grid
```bash
# All ROIs side-by-side comparison
display plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam/20251121T225505Z/all_rois_side_by_side.png
```

### 4. Telemetry Data
```bash
# View complete refinement metrics
cat plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/telemetry_stage_a_small.json | python -m json.tool | less

# Extract key metrics
cat plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/telemetry_stage_a_small.json | \
  python -c "import json, sys; d=json.load(sys.stdin)[0]; \
  print(f\"Status: {d['status']}\"); \
  print(f\"Loss improvement: {d['loss_improvement']*100:.1f}%\"); \
  print(f\"Closure evals: {d['perf_counters']['closure_evals']}\"); \
  print(f\"Loss trace: {d['loss_trace_full']}\")"
```

## Reproducing Successful Stage A Refinement

To reproduce the successful refinement (avoiding the CUDA graphs error):

```bash
# Set environment to disable torch.compile
export NANOBRAGG_DISABLE_COMPILE=1
export KMP_DUPLICATE_LIB_OK=TRUE

# Run Stage A refinement
python -m dbex.refine_one \
  --backend nanobrag \
  -e refGeom.expt \
  -r refGeom.refl \
  -i 0 \
  -o stage_a_refined.h5 \
  -m 747_mask.pkl \
  -z scaled.mtz \
  --sigma-rdout 3.0 \
  --device cuda:0 \
  --report-dir stage_a_triptychs
```

**Expected outcome**:
- Stage A status: `ok`
- Loss improvement: ~15-20%
- LBFGS iterations: ~20-35
- HDF5 output with refined model
- Triptych PNGs showing before/after comparison

## References

- **Spec**: docs/spec-db-workflow.md §68-95 (Canonical Initial Configuration)
- **Spec**: docs/spec-db-vis.md §14-24 (ROI Triptych Standards)
- **Testing**: docs/TESTING_GUIDE.md §1.1 (Environment Variables)
- **Initiative**: TOOLING-VIS-001 (Standardized Visual Diagnostics)
- **Initiative**: PERF-WARM-SIM-001 (Warm Cache Optimization)

## Key Takeaway

✅ **Yes, successful Stage A refinement artifacts exist!**

The repository contains multiple complete examples showing:
1. Convergent LBFGS optimization (18.4% loss reduction)
2. Loss curves tracking refinement progress
3. Before/after ROI triptychs with Z-score residuals
4. Complete telemetry with performance counters

These artifacts demonstrate that Stage A refinement **works correctly** when torch.compile is disabled via `NANOBRAGG_DISABLE_COMPILE=1`.
