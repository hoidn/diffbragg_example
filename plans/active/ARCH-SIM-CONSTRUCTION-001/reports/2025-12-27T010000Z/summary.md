# Turn Summary - ARCH-SIM-CONSTRUCTION-001 (2025-12-27T010000Z)

## Changes Shipped
Implemented fractional-delta float64 upcast in simulator.py SQUARE lattice branch (lines 299-315) to fix sincg underflow near integer HKLs, added enforcement test infrastructure under tests/architecture/, captured environment rebuild state and patch file.

## Problem Handling
Fixed SIM-CONSTR-PARTIALITY-001 (lattice weight collapse): sincg() evaluated on float32 deltas near zero returned incorrect values; upcasting to float64 preserves (Na·Nb·Nc)² scaling.

## Next Step
Run Stage A baseline probe + DB-AT-028/029 acceptance tests to validate fix resolves median StageA/(|F|²·F_latt²·LP) → 1 and chi²/pixel normalization.

## Artifacts
- plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T010000Z/
- Key files: pytest_arch_partiality.log, partiality_fix.patch, environment.md, rebuild.log
