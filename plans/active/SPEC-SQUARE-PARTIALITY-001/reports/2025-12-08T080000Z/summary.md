# SPEC-SQUARE-PARTIALITY-001 Phase B Summary

**Loop**: i=159 (Ralph)
**Date**: 2025-12-08T080000Z
**Mode**: Parity
**ActionType**: implementation_ready
**DecisionStatus**: patch_ready (now blocked)

## Outcome

**Phase B: BLOCKED** — Test changes applied but test fails with unexpected scaling behavior.

## What Was Shipped

1. **B1 — Test expectation updated** (`tests/architecture/test_nanobrag_partiality.py`):
   - Line 50: Changed `expected_ratio = (Na * Nb * Nc) ** 2` to `expected_ratio = Na * Nb * Nc`
   - Updated header comment (lines 1-13) to reference linear scaling per maintainer response
   - Updated docstring (lines 31-47) with corrected physics explanation
   - Made auxiliary telemetry checks conditional (partiality_stats API may be unavailable)
   - Updated assertion message to say "Integrated intensity scaling violation" instead of "Lattice weight scaling violation"

2. **B2 — Probe script comments updated** (`plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py`):
   - Updated module docstring (lines 1-22) to clarify peak vs integrated scaling physics
   - Added commentary about linear scaling evaluation in markdown output generation
   - No logic changes per PROBE-FREEZE-001

3. **B4 — No other tests found** enforcing old `(Na×Nb×Nc)²` scaling pattern

## Main Problem

**DMI Detected**: Observed nanobrag_torch behavior matches NEITHER the old expectation (`(Na×Nb×Nc)²`) NOR the maintainer's claimed linear (`Na×Nb×Nc`) scaling:

| Metric | Value |
|--------|-------|
| Expected linear (Na×Nb×Nc) | 38,048 |
| Expected quadratic ((Na×Nb×Nc)²) | 1,447,650,304 |
| **Observed ratio** | **1,187,854** |
| Observed / Linear | 31.2× |
| Observed / Quadratic | 0.00082× |

The observed ratio (1,187,854) is approximately `Na × Nb × Nc × Nc` = 38,048 × 32 = 1,217,536 (within 2.5%).

**Hypothesis**: The simulator may be applying partial quadratic scaling (e.g., only one axis). This requires investigation at the nanobrag_torch level.

## Test Results

```
FAILED tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells[cpu]
AssertionError: Integrated intensity scaling violation:
  expected ratio=38048.0 (linear Na×Nb×Nc),
  observed=1187854.4,
  relative_error=3021.99% (tolerance=5%)
```

## Next Step

**Escalate to Galph**: The maintainer response (`inbox/nanobrag_torch_response_2025_12_08.md`) claimed linear integrated intensity scaling, but observed behavior is ~31× the linear expectation. Options:
1. Request physics clarification from nanobrag_torch maintainer
2. Investigate if test configuration (oversample, detector size) affects the scaling
3. Treat as suspected spec/physics issue; defer Phase B completion until resolved

## Artifacts

- `pytest_partiality.log`: Test failure log with observed values
- `collect_partiality.log`: pytest collect-only verification (2 tests collected)
- `summary.md`: This file

---

### Turn Summary
Shipped Phase B test expectation changes (linear Na×Nb×Nc instead of (Na×Nb×Nc)²) and probe comment updates. Test execution revealed DMI: observed ratio 1,187,854 is ~31× linear expectation (neither linear nor quadratic). Phase B blocked pending physics clarification from nanobrag_torch maintainer. No other tests enforce old squared scaling.

Artifacts: `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T080000Z/` (pytest_partiality.log, collect_partiality.log, summary.md)
