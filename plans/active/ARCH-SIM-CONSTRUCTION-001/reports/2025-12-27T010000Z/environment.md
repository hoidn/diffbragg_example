# Environment State for ARCH-SIM-CONSTRUCTION-001 Partiality Fix

**Tag:** nanobrag-partiality-2025-12-26

**Timestamp:** 2025-12-04T01:27:01-08:00

## Changes Applied

Modified `src/nanobrag-torch/src/nanobrag_torch/simulator.py` to upcast fractional HKL deltas to float64 before sincg evaluation in the SQUARE lattice branch.

### Key Changes:
- Lines 295-315: Compute `delta_h`, `delta_k`, `delta_l` as `(h - h0).to(torch.float64)` etc.
- Convert `Na`, `Nb`, `Nc` to float64 tensors on correct device
- Evaluate `sincg()` in float64 precision
- Downcast final `F_latt` product back to simulator dtype (h.dtype) before combining with F_cell

### Rationale:
When HKL values are near integers and computed in float32, the fractional deltas `(h - h0)` collapse to zero or lose precision, causing `sincg(π·delta, N)` to return incorrect values. The sincg function should return ±N for small deltas, but float32 underflows prevent this. By computing deltas in float64, we preserve the (Na·Nb·Nc)² lattice weight scaling.

## Rebuild Command
```bash
cd src/nanobrag-torch && python -m pip install -e .
```

## Patch Location
`plans/active/ARCH-SIM-CONSTRUCTION-001/patches/partiality_fix.patch`

## Git Status
See `git_status.txt` in same directory.

## Related Artifacts
- ARCH-CONTRACT: docs/spec-db-core.md:60-140 (lattice weights ∝ (Na·Nb·Nc)²)
- FINDING: SIM-CONSTR-PARTIALITY-001 (to be added to docs/findings.md)
- TEST: tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells (to be created)
