# TOOLING-VIS-001 Loop Summary — 2025-11-25T055039Z

## Implementation Nucleus

Extended masked diagnostics per `input.md` Do Now:

1. **Test fixture** (`tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result`):
   - Compute mapping scale_ratio using loss_mask for both Bragg and target (masked mean)
   - Add `scale_ratio_mapping_unmasked` for diagnostic comparison
   - Persist both masked and unmasked scale ratios in DB-AT-028/029 metrics JSONs

2. **Probe script** (`plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py::compute_cpu_gpu_mapping_metrics`):
   - Emit masked vs unmasked scale ratios for CPU and GPU contexts
   - Add spot_scale_override, HKL source/path to metrics output
   - Updated parity metrics to include both masked and unmasked relative differences

## Validation Results

### Probe Execution
- Command: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T055039Z/mapping_cpu_gpu`
- **CPU metrics**: ROI CC median=-0.0399, scale_ratio_masked=0.2587, scale_ratio_unmasked=1.805, spot_scale_override=3.18e+17
- **GPU metrics**: ROI CC median=-0.0400, scale_ratio_masked=0.2587, scale_ratio_unmasked=1.805, spot_scale_override=3.18e+17
- **Parity**: mean_abs_diff=4.54e-05 ADU, max_abs_diff=74.4 ADU, scale_ratio_masked_rel_diff=7.07e-05
- **Conclusion**: Excellent CPU/GPU parity; both devices show pathological ROI CC ≈ -0.04, confirming mapping baseline uncorrelated with data

## Code Changes

### tests/dbex/test_stage_a_smoke_parity.py (+40 lines)
- Lines 206-237: Compute masked/unmasked mapping scale ratios using loss_mask
- Lines 262-263: Add scale_ratio_mapping_masked/unmasked to return dict
- Lines 325-327: Persist masked/unmasked metrics in DB-AT-028 JSON
- Lines 398-400: Persist masked/unmasked metrics in DB-AT-029 JSON

### plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py (+64 lines)
- Lines 110-134: CPU masked/unmasked scale ratios + spot_scale_override/HKL metadata
- Lines 171-195: GPU masked/unmasked scale ratios + spot_scale_override/HKL metadata
- Lines 216-243: Parity metrics with masked/unmasked relative differences
- Lines 356-375: Summary print statements with calibration/HKL diagnostics

## Observed Metrics (metadata-sigma dataset, small detector)

Mapping ROI CC median: **-0.04** (negatively correlated), scale_ratio_masked: **0.259**, scale_ratio_unmasked: **1.805**, spot_scale_override: **3.18e+17**

Stage A: chi²/pixel_initial=**1.084e+05** (spec ≤1e2), median_corr_before=**-0.050** (spec ≥0.2)

Root cause: Mapping forward stack produces uncorrelated predictions; Stage A inherits the pathological baseline.

## Artifacts
- mapping_cpu_gpu/{mapping_forward_cpu_gpu.json, probe.log}
- db_at_028/db_at_028_metrics.json, db_at_029/db_at_029_metrics.json
- pytest_db_at_028_029.log (2 FAILED), pytest_db_at_028_029_collect.log (2 collected)
