# SPEC-SQUARE-PARTIALITY-001 Phase B Planning Notes

**Loop:** i=159 (Galph)
**Date:** 2025-12-08T080000Z
**Action:** Planning / Delegation

## Focus Selection Rationale

1. **Phase A completed (i=158)**: Ralph completed Phase A (docs-only) — created physics_summary.md, updated SIM-CONSTR-PARTIALITY-001 finding with Resolution section, verified spec-db-core.md needs no changes.

2. **Implementation floor applied**: Phase A was docs-only, so Phase B (test updates) must follow per Galph non-negotiables.

3. **Physics is clarified**: Maintainer response (`inbox/nanobrag_torch_response_2025_12_08.md`) provides definitive physics:
   - Peak intensity at exact Bragg: ∝ `(Na×Nb×Nc)²`
   - Integrated/summed intensity: ∝ `Na×Nb×Nc` (linear)

4. **Test fix is mechanical**: Line 45 of test file needs `(Na * Nb * Nc) ** 2` → `Na * Nb * Nc`

## Problems.md Review

- Unchecked entry: **DB-AT-028/029 scale mismatch (SCALE-009, ARCH-SIM-CONSTRUCTION-001)**
- This initiative addresses part of that issue by correcting the SQUARE lattice expectation mismatch
- ARCH-SIM-CONSTRUCTION-001 is blocked_pending_environment, and this initiative resolves the spec/test side

## Phase B Tasks Delegated

1. **B1**: Update test expectation from `(Na*Nb*Nc)**2` to `Na*Nb*Nc`
2. **B2**: Update probe script comments (no logic changes per PROBE-FREEZE-001)
3. **B3**: Run partiality test and capture logs
4. **B4**: Verify no other tests enforce old scaling
5. **B5**: Update implementation.md and create summary.md

## Expected Outcome

Test should PASS after fix — actual simulator behavior was always correct; only test expectation was wrong.

## References

- Maintainer response: `inbox/nanobrag_torch_response_2025_12_08.md`
- Phase A summary: `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T070000Z/summary.md`
- Physics summary: `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T070000Z/physics_summary.md`
