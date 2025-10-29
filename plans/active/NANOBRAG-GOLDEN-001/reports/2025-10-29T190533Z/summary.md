# NANOBRAG-GOLDEN-001 Loop 2025-10-29T190533Z Summary

## Objective
Reapply canonical torch scale (SCALE-002), regenerate golden tensors, and repoint DB_AT_001 parity artifacts to new loop timestamp.

## Actions Taken

### 1. Parity Harness Update
- Updated `tests/dbex/test_db_at_001_parity.py:760` to redirect artifact output to `2025-10-29T190533Z/parity_harness`

### 2. Canonical Dataset Regeneration
- Ran `scripts/generate_simple_cubic_golden.py` with SCALE-002 fix already in place
- Structure factors used as-is (no pre-scaling per SCALE-001)
- Applied √(spot_scale_override) = 5.643325e+08 post-simulation to torch output (SCALE-002)

### 3. DiffBragg Refinement
- Converged in 5 macro cycles
- Final sigZ: 6.282190
- Final forward pass: max=36170.30

### 4. nanobrag_torch Simulation
- HKL hit rate: 98.73% (6144872/6224001 reflections)
- Raw torch output: max=6.894e-05
- Scaled torch output: max=38905.06 (after applying √scale)

### 5. Parity Test Execution
- Ran `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke`
- Test collected and executed successfully
- Result: XFAIL (as expected per CONFORMANCE-001 due to poor correlation)

## Key Metrics

### Canonical Dataset (from golden_dataset/metrics.json)
- DiffBragg max: 36170.30
- Torch max: 38905.06
- Median correlation: -0.0358
- Median RMSE: 4.600
- Localization success rate: 5.6%
- Loss mask coverage: 0.21%

### Parity Test (from parity_harness/metrics.json)
- Correlation: -0.0041
- RMSE: 888.62
- Max |Δ|: 36169.60
- Sum ratio: 0.0880
- Localization: 1.00
- n_pixels (in loss mask): 13086

### First Divergence
- Pixel: (0, 582)
- Predicted: 1.014e-04
- Target: 5.218e-12
- Abs diff: 1.014e-04
- Rel diff: 1.943e+07
- Scanned: 1 pixel

## Artifacts Generated

### Golden Dataset
- `golden_dataset/legacy/bragg_diffbragg.npy` (DiffBragg baseline)
- `golden_dataset/torch/bragg_torch.npy` (nanobrag_torch baseline)
- `golden_dataset/torch/loss_mask_panel_0.npy` (bool mask)
- `golden_dataset/torch/target_panel_0.npy` (observed data)
- `golden_dataset/manifest.json` (with SHA256 checksums)
- `golden_dataset/metrics.json` (parity metrics)

### Parity Harness
- `parity_harness/parity_harness/predicted.npy`
- `parity_harness/parity_harness/target.npy`
- `parity_harness/parity_harness/metrics.json`
- `parity_harness/parity_harness/first_divergence.json`

### Logs
- `canonical_capture.log` (full DiffBragg + torch simulation log)
- `pytest_db_at_001.log` (pytest output)
- `torch_hkl_debug.json` (HKL statistics)
- `fixture_files.txt` (list of fixture .npy files)

## Fixtures Refreshed
All canonical tensors copied to `tests/fixtures/golden_data/simple_cubic/`:
- bragg_diffbragg.npy (SHA256: 6e0c76a0a6476d64...)
- bragg_torch.npy (SHA256: 6b23e2724a081bd7...)
- target_panel_0.npy (SHA256: 3ae4d01ef0a57dd8...)
- loss_mask_panel_0.npy (SHA256: 9301d36f09eb6a15...)
- manifest.json (SHA256: 356143cd9b34baa9...)

## Status
✅ All Do Now tasks completed (A3/B1/B3/C1 per implementation.md)
- Canonical tensors regenerated with correct scale
- Manifest emitted with provenance
- Parity harness repointed to new timestamp
- DB_AT_001 selector remains Active (1 xfailed as expected)

## Next Actions
Per input.md priorities and docs/forward_equivalence.md:46-52:
1. Parity discrepancy (correlation=-0.004, localization=5.6%) remains below target thresholds (corr≥0.2, loc≥0.9)
2. Known issue: intensity scale mismatch requires investigation (torch=38905 vs diffbragg=36170, ~8% ratio)
3. Consider follow-up parity-debug loop per docs/spec-db-tracing.md first-divergence workflow
