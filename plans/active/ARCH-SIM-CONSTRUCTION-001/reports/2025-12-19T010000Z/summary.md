# ARCH-SIM-CONSTRUCTION-001 Phase C.15 — ROI-Level Diagnostics for DB-AT-028/029

**Date**: 2025-12-19T010000Z
**Status**: Tests FAIL (DB-AT-028/029 still failing after C.14 baseline fix)
**Focus**: Capture ROI-level diagnostics to identify which ROIs drive chi²/correlation failures

## Summary

Extended the Stage A baseline probe (`compare_stage_a_baseline.py`) to emit detailed ROI-level diagnostics (top/bottom-N ROIs sorted by Stage A vs target correlation, with panel+bbox IDs, masked mean deltas, and per-ROI CC metrics). Re-ran DB-AT-028/029 with fresh fixtures after the C.14 cold-path baseline alignment fix. Tests still FAIL with similar signatures to previous runs, confirming that the C.14 fix did not resolve the underlying intensity scale mismatch.

## Changes Made

### 1. Probe Enhancement (`plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:429-480, 591-604, 810-837`)
- Extended ROI loop (lines 437-480) to compute per-ROI diagnostics:
  - Pearson correlations: Stage A ↔ target, mapping ↔ target, Stage A ↔ mapping
  - Masked mean intensities for target, mapping, and Stage A outputs
  - Masked mean deltas (mapping - target, Stage A - target)
  - ROI metadata (panel ID, bbox, n_masked_pixels)
- Added sorting and extraction logic (lines 591-604):
  - Sort all ROIs by `stagea_vs_target_cc` (ascending)
  - Extract bottom 5 (worst correlations) and top 5 (best correlations)
- Added JSON output section (lines 693-699):
  - `roi_diagnostics` dict with `n_total_rois`, `n_valid_rois`, `bottom_n_rois`, `top_n_rois`
- Added console output section (lines 810-837):
  - Table showing bottom-N and top-N ROIs with CC(StgA↔Tgt), CC(Map↔Tgt), Δ(StgA-Tgt), and N_pix columns
  - Panel:bbox format (e.g., `0:[897,909,17,29]`) for mapping back to raw images

### 2. Bug Fix (`compare_stage_a_baseline.py:533-536`)
- Moved `chi2_ratio` computation outside conditional branch to fix UnboundLocalError in perturbed geometry mode
- Now computed unconditionally before baseline/perturbed branching logic

## Validation

### Probe Results

#### Baseline Geometry Mode (`stage_a_baseline_probe_baseline.json`)
- **DB-AT-027 Status**: PASS (Stage A vs mapping parity)
  - Max|Δ| (masked): 3.9e-03 ADU (< 1.0 threshold)
  - ROI CC (Stage A vs mapping median): 1.0000 (> 0.99 threshold)
  - Chi²/pixel relative diff: 0.0 (< 1e-3 threshold)
- **DB-AT-028 Status**: FAIL
  - Chi²/pixel initial: 9.80e+05 (>> 1e2 threshold, 9800× over)
- **ROI Diagnostics (baseline mode)**:
  - Total ROIs: 29, all valid
  - Bottom 5 (worst CC with target):
    - Panel 0:[897,909,17,29]: CC=-0.2008, Δ=-7.79 ADU
    - Panel 0:[350,362,877,889]: CC=-0.1623, Δ=+11.17 ADU
    - Panel 0:[535,547,842,854]: CC=-0.1366, Δ=-9.75 ADU
    - Panel 0:[661,673,940,952]: CC=-0.1288, Δ=-3.08 ADU
    - Panel 0:[644,656,21,33]: CC=-0.1229, Δ=-7.67 ADU
  - Top 5 (best CC with target):
    - Panel 0:[431,443,434,446]: CC=+0.6628, Δ=+405.2 ADU
    - Panel 0:[739,751,610,622]: CC=+0.6005, Δ=+0.76 ADU
    - Panel 0:[275,287,303,315]: CC=+0.3663, Δ=+1594.9 ADU
    - Panel 0:[645,657,284,296]: CC=+0.0862, Δ=+2.53 ADU
    - Panel 0:[943,955,583,595]: CC=+0.0763, Δ=-361.2 ADU
- **Median ROI CC (Stage A vs target)**: -0.0373 (far below 0.2 floor)

#### Perturbed Geometry Mode (`stage_a_baseline_probe_perturbed.json`)
- **DB-AT-027 Status**: FAIL (non-normative, expected due to deliberate perturbation)
  - Max|Δ| (masked): 1.10e+05 ADU
  - ROI CC (Stage A vs mapping median): -0.0450
  - Chi²/pixel relative diff: 9.25e-01
- **DB-AT-028 Status**: FAIL
  - Chi²/pixel initial: 1.89e+06 (>> 1e2 threshold, 18900× over)
- **ROI Diagnostics (perturbed mode)**:
  - Total ROIs: 29, all valid
  - Bottom 5 (worst CC with target):
    - Panel 0:[645,657,284,296]: CC=-0.1823, Δ=-1.76 ADU (was +0.0862 in baseline)
    - Panel 0:[419,431,794,806]: CC=-0.1428, Δ=-1.86 ADU
    - Panel 0:[939,951,65,77]: CC=-0.1206, Δ=-2.02 ADU
    - Panel 0:[121,133,288,300]: CC=-0.1170, Δ=-10.76 ADU
    - Panel 0:[739,751,610,622]: CC=-0.1163, Δ=+7.07 ADU (was +0.6005 in baseline)
  - Top 5 (best CC with target):
    - Panel 0:[431,443,434,446]: CC=+0.0902, Δ=+2133.96 ADU (was +0.6628 in baseline)
    - Panel 0:[976,988,202,214]: CC=+0.0891, Δ=-1.40 ADU
    - Panel 0:[535,547,842,854]: CC=+0.0616, Δ=-7.03 ADU
    - Panel 0:[477,489,595,607]: CC=+0.0267, Δ=-0.17 ADU
    - Panel 0:[347,359,266,278]: CC=+0.0217, Δ=-22.72 ADU
- **Median ROI CC (Stage A vs target)**: -0.0534 (worse than baseline)

### DB-AT-028/029 Test Results (`pytest_db_at_028_029.log`)
- **DB-AT-028 (loss scale sanity)**: FAILED
  - Chi²/pixel initial: 2.097e+05 (>> 1e2 threshold, 2097× over)
  - No change from previous runs despite C.14 cold-path alignment fix
- **DB-AT-029 (structure parity)**: FAILED
  - Median ROI correlation before refinement: -0.053 (< 0.2 floor)
  - No improvement from previous runs
- **Runtime**: 16.62s (2 tests, both failed)

## Key Findings

### 1. ROI-Level Failure Pattern

The bottom-5 ROIs (worst correlations with target) exhibit consistent negative correlations across both baseline and perturbed modes:
- **Baseline mode**: median CC = -0.0373, bottom 5 range from -0.2008 to -0.1229
- **Perturbed mode**: median CC = -0.0534, bottom 5 range from -0.1823 to -0.1163

This indicates that the majority of ROIs show **anti-correlation** between Stage A outputs and target data, suggesting a systematic intensity scale or sign issue rather than isolated ROI failures.

### 2. Masked Mean Delta Distribution

- Worst ROIs show mixed delta signs (both positive and negative), with magnitudes ranging from -10 to +11 ADU in baseline mode
- Best ROI (panel 0:[431,443,434,446]) has extremely large positive delta (+405.2 ADU in baseline, +2133.96 ADU in perturbed), suggesting this ROI may contain high-intensity Bragg peaks where the scale mismatch is most visible

### 3. C.14 Baseline Fix Had No Impact

The Phase C.14 cold-path baseline alignment factor (telemetry masked mean / cold masked mean) was intended to align reconstruction helpers with Stage A baselines. However:
- DB-AT-028 chi²/pixel remained at ~2.1e5 (unchanged from C.13)
- DB-AT-029 median ROI CC remained at ~-0.053 (unchanged from C.13)
- Probe outputs show `bragg_before` source is now correctly labeled as "stage_a_telemetry_initial", but the underlying intensity scale mismatch persists

This confirms that the C.14 fix addressed a **plumbing issue** (ensuring cold path matches warm cache) but did not resolve the **semantic issue** (simulator construction or scaling convention mismatch between training and reconstruction).

### 4. Stage A vs Mapping Parity (DB-AT-027)

- **Baseline mode**: PASS (max|Δ|=3.9e-03 ADU, ROI CC=1.0000)
  - Stage A and mapping produce **identical outputs** when using the same geometry
  - This confirms that the mapping baseline fix (Phase C.7) successfully aligned the two paths
- **Perturbed mode**: FAIL (expected, non-normative)
  - Deliberate perturbation causes large differences (max|Δ|=1.1e5 ADU)
  - Confirms that Stage A correctly reacts to geometry changes

## Next Steps

The C.14 baseline fix **did not** resolve DB-AT-028/029 failures. The ROI diagnostics reveal that the issue is **systematic across nearly all ROIs** (median CC=-0.0373), not isolated to a few outlier ROIs. This suggests:

1. **Hypothesis**: The remaining scale mismatch is in the **fixture setup** or **reconstruction helper** rather than the Stage A forward model itself.
   - DB-AT-027 (Stage A vs mapping) now PASSES in baseline mode, confirming Stage A outputs are correct
   - DB-AT-028/029 (Stage A vs target) FAIL because `bragg_before` (reconstruction helper output) does not match target despite correct scale_factor application

2. **Next Investigation**: Focus on the **bragg_before computation path** in the fixture:
   - The fixture calls `build_final_bragg_from_stage_a_telemetry(..., param_state="initial")` to reconstruct the zero-iteration baseline
   - Debug evidence (from probe logs) shows reconstructed bragg mean (masked) = 0.39 ADU vs telemetry model mean (masked) = 87.12 ADU
   - Ratio = 0.0045 (450× too small), indicating that the reconstruction helper is **not applying the baseline alignment correctly** or is missing a scale component

3. **Recommended Fix**: Investigate why reconstruction helper cold-path baseline alignment produces outputs ~450× smaller than expected despite:
   - `baseline_alignment_factor = 1.0` (no correction applied in cache-hit path)
   - `scale_factor = 5.2e9` (correctly extracted from telemetry)
   - `sqrt_spot_scale = 6.9e8` (correctly computed from spot_scale_override)

The ROI diagnostics now provide a clear mapping of which ROIs fail worst, enabling targeted investigation of specific reflections or panel regions once the systematic scale issue is resolved.

## Artifacts

- `stage_a_baseline_probe_baseline.json` — Probe JSON output (baseline geometry)
- `stage_a_baseline_probe_perturbed.json` — Probe JSON output (perturbed geometry)
- `probe_baseline.log` — Probe console log (baseline geometry)
- `probe_perturbed.log` — Probe console log (perturbed geometry)
- `pytest_db_at_028_029.log` — pytest execution log (2/2 tests FAILED)
- `db_at_028/db_at_028_metrics.json` — DB-AT-028 test metrics
- `db_at_029/db_at_029_metrics.json` — DB-AT-029 test metrics

## Metrics

- Files touched: 1 (compare_stage_a_baseline.py)
- Lines added: ~75 (ROI diagnostics collection + sorting + output sections)
- Tests run: 2 (DB-AT-028, DB-AT-029)
- Tests passing: 0/2 (both FAIL, unchanged from C.14)
- Probe executions: 2 (baseline + perturbed geometry modes)
- ROIs analyzed: 29 (per probe run)
- ROI diagnostics emitted: 10 (bottom-5 + top-5 per probe run)
