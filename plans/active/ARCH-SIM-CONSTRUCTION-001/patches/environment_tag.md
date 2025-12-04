# Environment Tag: nanobrag-partiality-2025-12-26

## Summary
Fixed SQUARE lattice factor sincg evaluation to use fractional Miller index offsets (h-h0, k-k0, l-l0) in float64 precision.

## Patch Applied
- File: `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/partiality_fix.patch`
- Target: `src/nanobrag-torch/src/nanobrag_torch/simulator.py`
- Lines modified: 283-304 (SQUARE branch in compute_physics_for_position)

## Changes Made
1. **SQUARE lattice factor fix** (simulator.py:294-304):
   - Changed from using integer Miller indices `h, k, l` directly
   - Now computes fractional offsets `delta_h = (h - h0)`, etc.
   - Promotes deltas to `torch.float64` before calling `sincg`
   - Casts result back to simulator dtype to preserve precision
   - Prevents sincg collapse at integer Miller indices

2. **Enforcement test** (tests/architecture/test_nanobrag_partiality.py):
   - Created `test_square_lattice_applies_ncells`
   - Verifies intensity scales by (Na·Nb·Nc)^2 for N_cells=(Na,Nb,Nc)
   - Compares baseline (1,1,1) vs (5,7,11) with 10% tolerance
   - ARCH-CONTRACT enforcement per docs/spec-db-core.md:70-110

## Rebuild Command
```bash
cd src/nanobrag-torch
python -m pip install -e .
```

## Git Status at Patch Time
```
# nanobrag-torch submodule
Modified: src/nanobrag_torch/simulator.py (lines 283-304)

# Main repository
Added: tests/architecture/test_nanobrag_partiality.py
```

## Validation
- Mapped test: Stage A baseline probe should show median f_latt ≈ Na·Nb·Nc (not ≈1e-4)
- Architecture test: pytest tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells
- Acceptance gates: DB-AT-028, DB-AT-029 should pass with partiality-corrected intensities

## Contract References
- ARCH-SIM-CONSTRUCTION-001: docs/spec-db-core.md:70-110
- Config preservation: docs/config_crosswalk.md:61-85
- Acceptance gates: docs/spec-db-conformance.md:139-172
