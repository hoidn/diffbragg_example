# SPEC-SQUARE-PARTIALITY-001 Loop i=160 Summary

**Loop**: i=160 (Galph)
**Date**: 2025-12-08T090000Z
**Mode**: Parity
**ActionType**: review_or_housekeeping
**DecisionStatus**: blocked (DMI requires investigation)

## Outcome

**Phase B DMI Review**: Analyzed Phase B evidence (i=159 Ralph) and identified a strong hypothesis for the scaling discrepancy.

## DMI Analysis

| Metric | Value |
|--------|-------|
| Expected linear (Na×Nb×Nc) | 38,048 |
| Expected quadratic ((Na×Nb×Nc)²) | 1,447,650,304 |
| **Observed ratio** | **1,187,854** |
| `Na×Nb×Nc×Nc` = 38,048 × 32 | **1,217,536** |
| Match to `Na×Nb×Nc×Nc` | **97.5%** (2.5% error) |

## Hypothesis (Confidence: 0.85)

The observed scaling closely matches `Na × Nb × Nc × Nc` (within 2.5%), suggesting **one axis (Nc) contributes squared scaling while Na and Nb contribute linear scaling**.

**Root Cause**: The test uses a 10×10 pixel detector, which doesn't integrate over the full reciprocal space solid angle. The sincg function produces peaks of width ~1/N in each axis. For different N_cells values:
- a-axis: peak width ∝ 1/Na
- b-axis: peak width ∝ 1/Nb
- c-axis: peak width ∝ 1/Nc

If the detector is large enough to capture the full peak in the a* and b* directions but NOT in the c* direction, then:
- a-axis and b-axis integrate fully → linear contribution (Na × Nb)
- c-axis partially samples the peak → captures peak height ∝ Nc² instead of integral ∝ Nc

The maintainer's linear scaling claim assumes infinite-area integration (all axes integrated). The test's finite 10×10 detector violates this assumption.

## Verification Path

**Option A (Recommended)**: Modify test to use larger detector (100×100 pixels) and verify:
- If scaling becomes linear → finite-detector hypothesis confirmed
- If scaling still shows partial squaring → deeper physics issue

**Option B**: Escalate to maintainers with specific evidence:
- Observed: `Na × Nb × Nc × Nc` scaling (31× linear)
- Test config: 10×10 px detector, oversample=13, N_cells=(41,29,32)
- Request clarification on finite-detector integration expectations

## Decision

Per dwell limits, this is the first evidence loop after DMI (dwell=1). Next loop should execute Option A (larger detector test) to verify hypothesis before escalating. If Option A doesn't resolve, retype to spec_change or escalate to maintainers.

## Portfolio Status

- **SPEC-SQUARE-PARTIALITY-001**: blocked (Phase B DMI, dwell=1)
- **ARCH-GRADIENT-FLOW-001**: partial (nanobrag_torch layer complete, DBEX layer deferred)
- **DB-AT-SUITE-CARE-001**: in_progress (Workflow Integration CERTIFIED)

## Artifacts

- `summary.md`: This file

---

### Turn Summary
Loop i=160 (Galph): Reviewed SPEC-SQUARE-PARTIALITY-001 Phase B DMI. Key finding: observed scaling 1,187,854 matches `Na×Nb×Nc×Nc` = 1,217,536 within 2.5%. Hypothesis (confidence 0.85): 10×10 pixel detector doesn't integrate c* axis fully, causing Nc² contribution instead of linear Nc. Verification path: run test with larger detector (100×100 px) to confirm finite-detector hypothesis. Initiative remains blocked; next loop should attempt verification or escalate with specific evidence.
