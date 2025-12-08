# Phase B.8 Magnitude Audit Report

**Date:** 2025-12-08T232143Z
**Loop:** i=218
**Focus:** Cell parameter gradient magnitude investigation

## Executive Summary

All synthetic tests PASS with 1.00× gradient ratio; only real refGeom data test FAILS.
This isolates the magnitude issue to **data-specific factors** in the real experiment metadata.

## Test Results

| Test | Status | Notes |
|------|--------|-------|
| `test_minimal_nanobrag_gradcheck` | ✓ PASS | Direct nanobrag_torch, bypasses DBEX |
| `test_gradient_magnitude_diagnostic` | ✓ PASS | Ratio 1.00× for all 3 variants |
| `test_dbex_hkl_grid_gradient` | ✓ PASS | DBEX HKL grid builder |
| `test_dbex_full_factory_gradient` | ✓ PASS | DBEX create_crystal_config with crystal_overrides |
| `test_simulate_forward_torch_gradient` | ✓ PASS | Full simulate_forward_torch with synthetic dxtbx |
| `test_db_at_010_gradcheck_crystal_cell_a` | ✗ FAIL | Real refGeom data |

## Findings

### Confirmed Working

1. **nanobrag_torch gradients**: Cell parameter gradcheck passes (upstream confirmed 6/6)
2. **DBEX config_factories.py**: `create_crystal_config()` with `crystal_overrides` preserves gradients
3. **DBEX HKL grid**: `build_structure_factor_grid()` doesn't break gradient flow
4. **DBEX forward path**: `simulate_forward_torch()` works with synthetic data

### Suspected Root Cause

The real refGeom experiment contains metadata that triggers additional code paths:

1. **ML_half_mosaicity_deg**: Extracted at `config_factories.py:382-383`, sets `mosaic_spread_deg > 0`
2. **ML_domain_size_ang**: Extracted at `config_factories.py:383`, may trigger N_cells fallback
3. **Mosaic domain sampling**: When `mosaic_spread_deg > 0`, different simulation path is taken

Per fix_plan.md, there are **TWO separate blockers**:
- (1) Cell magnitude → This investigation (possibly mosaic-related)
- (2) Mosaic gradient bug → Upstream fix pending (`mosaic_gradient_bug_2025_12_08.md`)

### Recommended Next Steps

1. **Verify mosaic hypothesis**: Add diagnostic to print `mosaic_spread_deg` and `mosaic_domains` values used in real test
2. **Try workaround**: Force `mosaic_spread_deg=0.0` in test to see if it passes
3. **If workaround passes**: Cell magnitude issue is coupled to mosaic code path, may be resolved by upstream mosaic fix
4. **If workaround fails**: Deeper investigation into non-cubic crystal geometry effects needed

## Code Pointers

- `config_factories.py:382-383` - ML_half_mosaicity_deg extraction
- `config_factories.py:388-396` - mosaic_spread_deg application
- `config_factories.py:402-420` - N_cells fallback from ML_domain_size_ang
- `helpers.py:198` - Crystal construction with beam_config

## Artifacts

- `minimal_gradcheck.log` - Minimal test (PASS)
- `dbex_gradcheck_cell_a.log` - Real data test (FAIL)
- `gradient_diagnostic.log` - All diagnostic tests

## Conclusion

The DBEX integration layer does NOT break cell parameter gradients when using synthetic cubic crystals.
The magnitude mismatch only occurs with real refGeom data, suggesting the issue is in mosaic/mosaicity
handling or non-cubic crystal geometry effects. Recommend trying `mosaic_spread_deg=0.0` workaround
before further investigation.
