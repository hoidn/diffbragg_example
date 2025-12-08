# SQUARE Lattice Scaling Physics Summary

## Key Result (from nanobrag_torch maintainer response)

Per `inbox/nanobrag_torch_response_2025_12_08.md`, the correct SQUARE lattice scaling behavior is:

1. **Peak intensity at exact Bragg condition**: proportional to `(Na * Nb * Nc)^2`
   - The lattice factor F_latt peaks at integer HKL with amplitude proportional to Na*Nb*Nc
   - Peak height = |F_latt|^2 is proportional to (Na*Nb*Nc)^2

2. **Integrated/summed intensity over a reflection**: proportional to `Na * Nb * Nc` (linear)
   - When integrating over the full reflection profile (all subpixels, all angles)
   - The sinc^2 envelope integrates to a constant per unit cell
   - Total integrated intensity scales linearly with number of unit cells

## Mathematical Basis

For the SQUARE lattice sincg function:
- Peak height scales as N^2
- Peak width scales as 1/N
- Integral = height x width is proportional to N^2 x 1/N = N

For 3D:
- Peak intensity (at exact Bragg): proportional to (Na * Nb * Nc)^2
- Integrated intensity (sum over detector): proportional to Na * Nb * Nc

This is fundamental crystallographic physics: integrated intensity of a Bragg reflection is independent of crystal size (kinematic theory). Larger crystals produce sharper but not more intense integrated reflections.

## DBEX Expectation Mismatch (Historical)

Previous DBEX probes (ARCH-SIM-CONSTRUCTION-001 C.34-C.39) expected `(Na*Nb*Nc)^2` for integrated intensity sums. This was physically incorrect. The observed ratios from probes were consistent with linear scaling, not a sincg bug in nanobrag_torch.

## Enforcement Implications

- Architecture test `tests/architecture/test_nanobrag_partiality.py` currently asserts `(Na*Nb*Nc)^2` for `image.sum()` (integrated intensity) - MUST be changed to linear in Phase B
- If peak-height testing is desired, it must use exact Bragg condition sampling, not integration over the full image

## References

- `inbox/nanobrag_torch_response_2025_12_08.md` (maintainer response, 2025-12-08)
- `docs/findings.md::SIM-CONSTR-PARTIALITY-001` (updated finding)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/` (historical probe evidence)
