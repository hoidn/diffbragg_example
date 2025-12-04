# BLOCKED: SQUARE Lattice Parity Failure After Normalization Fix

**Loop**: 2026-01-06T200000Z
**Initiative**: ARCH-SIM-CONSTRUCTION-001
**DecisionStatus**: localized (normalization fix applied, but parity not restored)
**Blocker Type**: physics/sampling issue (not implementation bug)

## Summary

The requested normalization fix was implemented correctly per Do Now specification (simulator.py:1086-1099):
- SQUARE lattices now use `oversample_norm = 1` (integral semantics)
- Other shapes retain `oversample_norm = oversample²` (mean semantics)
- `steps_scalar` is correctly emitted via `_partiality_stats`

Test assertions for `steps_scalar==1` **PASS** for both cpu and cuda paths.

However, **parity validation FAILS**:
- Expected ratio: (41×29×32)² = 1,447,650,304
- Observed ratio: ~601,000,000 (41% of expected)
- Relative error: **58%** (tolerance: 1%)

## Evidence

### Test Results (test_nanobrag_partiality.py)
```
FAILED: Lattice weight scaling violation:
  expected ratio=1447650304.0,
  observed=601278195.4 (cpu) / 600785136.0 (cuda),
  relative_error=58.47% / 58.50% (tolerance=1%)
```

### Probe Results (single-pixel, oversample=13)
- Observed ratio: 84,612.7 (0.0058% of expected)
- Subpixels in central sincg lobe: **0/169** (0.00%)
- This proves the normalization fix improves multi-pixel scenarios but doesn't solve the sampling density issue

### Root Cause Analysis

SQUARE lattice sincg peaks have width ~1/N_cells. For N_cells=(41,29,32):
- Peak width: ~1/41 ≈ 0.024 (h-axis), ~1/29 ≈ 0.034 (k-axis), ~1/32 ≈ 0.031 (l-axis)
- With oversample=13, subpixel grid spacing: 1/13 ≈ 0.077
- **Consequence**: Most pixels don't have a subpixel that lands in all three narrow peaks simultaneously

The 10×10 detector achieves 41% of expected because ~41% of pixels are well-aligned. The single-pixel probe gets 0.0058% because its alignment is poor.

## Boundary Bisection Outcome

Per input.md line 40-41:
> "Boundary Bisection Step: Apply the normalization fix; if `(Na·Nb·Nc)²` parity still fails, escalate to spec_change or revisit the sincg accumulation math."

**Status**: Normalization fix applied ✓, parity still fails ✗

## Recommended Next Steps

1. **Escalate to spec_change**: Re-evaluate whether SQUARE lattice shape is appropriate for Stage-A smoke tests with sparse sampling (oversample=13 may be insufficient for N_cells=(41,29,32))

2. **OR increase oversample**: Test with oversample=41 (worst-case N_cells) to ensure at least one subpixel per axis lands in the sincg peak

3. **OR adaptive sampling**: Implement peak-aware subpixel placement for SQUARE shape (would be an architecture change, not a bugfix)

4. **OR change test expectations**: If 41% parity is acceptable for SQUARE with realistic oversample values, update tolerance in test and spec

## Files

- Test log: `pytest_partiality.log`
- Probe log: `square_lattice_probe.log`
- Probe metrics: `square_lattice_scaling.{json,md}`

## Blocker ID

**ARCH-SIM-CONSTRUCTION-001-PARITY-SAMPLING-001**: SQUARE lattice parity requires either (a) much higher oversample, (b) adaptive sampling, or (c) relaxed tolerance
