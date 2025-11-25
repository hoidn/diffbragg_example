### Turn Summary
Extended mapping probe and test fixtures with sigma/HKL provenance (sigma_source, HKL path/count, spot_scale_override, masked/unmasked scale ratios) and ran diagnostics for both metadata and cli_override sigma sources.
Both sigma sources produce **identical negative ROI CC** (≈-0.04), confirming the -0.04 baseline is **not** explained by sigma source differences but by fundamental mapping forward model misconfiguration.
Next: isolate HKL grid selection or geometry/scale alignment as the root cause before re-running DB-AT-028/029 gates.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T060403Z/ (mapping_variants/{metadata,cli_override}/, db_at_028/, db_at_029/, pytest logs, mapping_forward_cpu_gpu.json in both variants)

## Detailed Analysis

### Probe Results

**Metadata Sigma Source:**
- CPU ROI CC median: -0.039912
- GPU ROI CC median: -0.039915
- CPU scale ratio (masked): 2.5872e-01
- GPU scale ratio (unmasked): 1.8052e+00
- HKL count: 69614
- spot_scale_override: 3.1847e+17
- CPU/GPU parity: Excellent (mean_abs_diff=4.5e-05, max_abs_diff=74.4 ADU)

**CLI Override Sigma Source:**
- CPU ROI CC median: -0.043557
- GPU ROI CC median: -0.043560
- CPU scale ratio (masked): 5.7404e-01
- GPU scale ratio (unmasked): 2.9263e+00
- HKL count: 69614
- spot_scale_override: 3.1847e+17
- CPU/GPU parity: Excellent (mean_abs_diff=1.5e-04, max_abs_diff=52.0 ADU)

### Key Findings

1. **Sigma source does NOT explain the -0.04 ROI CC baseline**: Both metadata and cli_override produce nearly identical negative correlations (within 0.004).

2. **CPU/GPU mapping forward parity is excellent**: Both devices produce nearly identical forward passes, so device selection is not the issue.

3. **The mapping forward model is fundamentally misconfigured**: Negative ROI CC indicates the model is producing the wrong structure/intensity pattern relative to experimental data.

4. **Scale ratios vary more between sigma sources** (0.26 vs 0.57 for masked), but both are within reasonable bounds and don't explain the anti-correlation.

5. **DB-AT-028/029 failures persist** with metadata sigma:
   - chi²/pixel_initial = 1.084e+05 (spec requires ≤1e2)
   - roi_cc_median_before = -0.050 (spec requires ≥0.2)
   - roi_cc_median_mapping = -0.040 (Stage A inherits this pathological baseline)

### Root Cause Hypothesis

The mapping forward (`build_mapping_stage_a_context` → `simulate_forward_once`) is using incorrect HKL grid selection, geometry baseline, or calibration payload, causing the simulated Bragg pattern to be systematically anti-correlated with the experimental data. Sigma source does not affect this; the problem is upstream in:
- HKL grid provenance (refined vs raw MTZ, halo policy)
- Geometry baseline (U-matrix, cell parameters)
- Calibration payload threading (spot_scale, flux, N_cells)

### Next Actions

1. Investigate HKL grid selection: check if `scaled.mtz` vs `refined_structure_factors.mtz` affects ROI CC.
2. Audit geometry baseline: verify MOSFLM A* injection and U-matrix parameterization align with mapping.
3. Consider falling back to a known-good HKL/geometry configuration that previously showed positive ROI CC.
4. Document blocked status in fix_plan.md if sigma/HKL differences cannot isolate the root cause.
