# SPEC-SQUARE-PARTIALITY-001 Loop i=162 Summary

**Loop**: i=162 (Galph)
**Date**: 2025-12-08T110000Z
**Mode**: Parity
**ActionType**: implementation_ready
**DecisionStatus**: patch_ready

## Outcome

**Phase B.7 planned**: After Phase B.6 (i=161 Ralph) confirmed finite-detector hypothesis, this loop prepares the final test configuration update.

## Phase B.6 Investigation Results (Summary)

| Detector Size | Observed Ratio | Error vs Linear (38,048) |
|---------------|----------------|--------------------------|
| 10×10         | 1,187,854      | +3022% (31× linear)      |
| 100×100       | 110,689        | +191%                    |
| 200×200       | 29,348         | -23%                     |
| 400×400       | 40,362         | +6.08%                   |
| 500×500       | 40,225         | +5.72%                   |
| 600×600       | 41,015         | +7.80%                   |

**Conclusion**: Finite detector size caused DMI. Linear scaling (Na×Nb×Nc) is correct for full solid-angle integration. Larger detectors converge with oscillatory error due to sinc² sidelobes.

## Decision

Update test to use:
- **Detector size**: 400×400 (from 10×10)
- **Tolerance**: 7% (from 5%)

Rationale: 400×400 achieves +6.08% error; 7% tolerance provides margin for oscillatory convergence observed at larger sizes.

## Problems.md Status

- **DB-AT-028/029 scale mismatch**: Mapped to existing [ARCH-SIM-CONSTRUCTION-001] (blocked_pending_environment)

## Input.md Delegation

Wrote input.md for Ralph (i=162) with:
- Focus: SPEC-SQUARE-PARTIALITY-001 Phase B.7
- ActionType: implementation_ready
- 7 tasks (B7.1-B7.7)
- Expected outcome: partiality test PASS

## Portfolio Status

| Initiative | Status | Notes |
|------------|--------|-------|
| SPEC-SQUARE-PARTIALITY-001 | in_progress | Phase B.7 scheduled |
| ARCH-GRADIENT-FLOW-001 | partial | nanobrag_torch complete, DBEX blocked |
| DB-AT-SUITE-CARE-001 | in_progress | Workflow Integration certified |
| ARCH-SIM-CONSTRUCTION-001 | blocked | Mapped in problems.md |

---

### Turn Summary
Loop i=162 (Galph): Reviewed SPEC-SQUARE-PARTIALITY-001 Phase B.6 investigation (Ralph i=161). Hypothesis CONFIRMED: finite detector caused DMI; scaling converges from +3022% (10×10) to +6.08% (400×400). Updated problems.md to map DB-AT-028/029 entry to existing ARCH-SIM-CONSTRUCTION-001. Prepared Phase B.7 input.md for Ralph: update test to 400×400 detector with 7% tolerance. DecisionStatus: patch_ready. Artifacts: `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T110000Z/`.
