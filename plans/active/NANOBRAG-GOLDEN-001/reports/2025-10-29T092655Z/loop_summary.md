# NANOBRAG-GOLDEN-001 Loop Summary (2025-10-29T092655Z)

## Objective
Fix nanobrag_torch Miller index calculation to use reciprocal vectors and emit non-zero intensities for DB_AT_001 dataset.

## Changes Made

### 1. Miller Index Calculation Fix (simulator.py:196-222)
**Problem**: Code was projecting scattering vector onto real-space vectors (rot_a, rot_b, rot_c) instead of reciprocal vectors (rot_a_star, rot_b_star, rot_c_star) to compute Miller indices.

**Fix Applied**:
- Changed from real-space to reciprocal vectors for h,k,l calculation
- Added unit conversion: scattering vector from m^-1 to Å^-1 (divide by 1e10)
- Applied proper broadcasting for multi-source and single-source cases

**Code Location**: `/home/ollie/Documents/nanoBragg/src/nanobrag_torch/simulator.py` lines 196-222

### 2. Bounded Logging Addition (simulator.py:234-243)
**Feature**: Added bounded logging to track in-range structure factor hit rates

**Implementation**:
- Logs once per panel execution (<100 lines total)
- Reports: nonzero_F_cells / total_pixels with percentage
- Helps diagnose zero-output issues

## Test Results

### Test: DB_AT_001 Forward Equivalence
**Command**: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001`
**Result**: XFAIL (expected - test uses stub simulators, not real nanobrag_torch)
**Note**: This test doesn't exercise the actual simulator, so it couldn't validate the fix.

### Test: Golden Dataset Generation
**Command**: `python scripts/generate_simple_cubic_golden.py --canonical-out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T092655Z/golden_dataset`
**Result**: **STILL ZERO OUTPUT**
- DiffBragg baseline: max=36182.91 (non-zero ✓)
- Torch baseline: max=0.0 (all zeros ✗)
- HKL hit rate: 0/6,224,001 pixels (0.00%)

## Root Cause Analysis

The fix addressed two issues:
1. ✓ Using reciprocal instead of real-space vectors
2. ✓ Converting scattering vector units (m^-1 → Å^-1)

However, the **0% hit rate** persists, indicating that even after these fixes, the computed h,k,l values are NOT landing within the structure factor grid bounds [h_min, h_max], [k_min, k_max], [l_min, l_max].

### Possible Remaining Issues:
1. **Sign convention mismatch**: The scattering vector definition or reciprocal vector orientation may differ from what crystal.get_structure_factor() expects
2. **Missing scale factor**: There may be an additional multiplicative factor needed in the Miller index calculation
3. **Grid alignment**: The structure factor grid indexing might use a different convention than the physics calculation
4. **Rotation bug**: The reciprocal vectors might not be properly rotated or might be rotated in the wrong direction

### Evidence:
- Structure factor grid confirmed populated: 69,614 nonzero entries (100% in-range according to generator)
- Grid stats: min=0, max=2.926e+11, mean=1.059e+10
- All structure factor lookups return 0, meaning computed h0,k0,l0 are out of bounds

## Artifacts Generated
- `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T092655Z/simulator_reciprocal_fix.patch` - Patch file documenting changes
- `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T092655Z/canonical_capture.log` - Full generator output (897 KB)
- `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T092655Z/pytest.log` - Test output

## Next Actions
1. **Debug h,k,l values**: Add instrumentation to log actual h,k,l values being computed and compare to grid bounds
2. **Verify scattering vector**: Check if scattering vector calculation matches crystallographic convention
3. **Check sign conventions**: Verify incident vs diffracted beam direction signs
4. **Review C-code**: Compare with nanoBragg.c implementation of Miller index calculation (lines ~3050-3100)
5. **Consider alternative approach**: May need guidance from nanobrag_torch maintainer on correct Miller index calculation

## Status
**BLOCKED**: Torch output remains all-zero despite fixing reciprocal vector usage and unit conversion. The 0% HKL hit rate indicates a deeper issue with how Miller indices are being calculated or how the structure factor grid is indexed.
