# Phase C.39 Omega Diagnosis Correction (2026-01-13T150000Z)

## Status: Planning (Omega hypothesis rejected; reverting to C.38 evidence)

## Ralph's Block Was Correct

Ralph correctly identified a specification contradiction in the C.39 Do Now and blocked implementation. The block summary (reports/2026-01-13T010000Z/summary.md:71-79) exposed a critical flaw in the supervisor's omega compensation hypothesis.

## Evidence Re-Analysis

Re-reading the Phase C.38 instrumentation results (reports/2026-01-11T010000Z/) and the latest probe run (reports/2026-01-13T010000Z/square_lattice_scaling.md):

### Key Metrics
- **Base case (N_cells=1,1,1):**
  - trace_subpixel_F_total_sq_sum: 1.187207e+09
  - trace_normalized_intensity: 1.187207e+03
  - Omega: 9.999999e-07

- **Scaled case (N_cells=41,29,32):**
  - trace_subpixel_F_total_sq_sum: 1.614788e+17
  - trace_normalized_intensity: 1.614788e+11
  - Omega: 9.999999e-07

### Critical Observation
**Ratio of RAW sums (before omega):**
```
1.614788e+17 / 1.187207e+09 = 1.360158e+08
```

**Observed intensity ratio (after omega):**
```
1.614788e+11 / 1.187207e+03 = 1.360158e+08
```

**Expected ratio:**
```
(41×29×32)² = 1.447650e+09
```

**Relative error in RAW sum ratio:** 90.60%

## Root Cause Correction

The deficit of 0.094x appears in `trace_subpixel_F_total_sq_sum` **BEFORE omega is applied**. This proves:

1. **Omega is a red herring** — Both base and scaled cases have omega≈1e-6 applied, so it cancels in the ratio
2. **The bug is in the per-subpixel accumulation** — The raw Riemann sum is already missing the `(Na·Nb·Nc)²` boost
3. **C.39 omega compensation was based on a misdiagnosis** — Moving omega outside the loop doesn't fix a problem that exists before omega is applied

## Hypothesis: Steps Scalar Bug

Looking at the telemetry:
- `steps_scalar`: 1.0 (both base and scaled)
- `square_used_riemann_sum`: 1.0 (confirmed SQUARE path active)
- `omega_applied_post_sum`: 1.0 (confirmed post-sum application)

The Phase C.35 fix (removing `oversample²` from steps scalar for SQUARE lattices) correctly set `steps_scalar=1.0`. However, the deficit persists.

## Re-Reading Phase C.34-C.38 Evidence

Phase C.34 coverage analysis (square_lattice_scaling.md:120-137):
- 81/169 subpixels (47.93%) hit the central sincg lobe
- Central lobe contributes 93.53% of total intensity
- **Implied (Na·Nb·Nc)² from coverage: 1.354007e+09**
- **This matches the observed deficit!**

The coverage-implied ratio (1.354007e+09) is very close to our observed raw ratio (1.360158e+08) when we account for the order of magnitude.

Wait - let me recalculate:
- Coverage-implied: 1.354007e+09
- Observed: 1.360158e+08
- These differ by 10x!

Let me check the F_latt values:
- Base F_latt: 1.0
- Scaled F_latt: 4206.5
- F_latt ratio: 4206.5
- **Expected F_latt ratio:** (Na·Nb·Nc) = 41×29×32 = 38,048
- **F_latt deficit:** 4206.5 / 38,048 = 0.1106 (11% of expected)

So F_latt (the lattice amplitude) is at 11% of expected, which when squared gives (0.1106)² ≈ 0.0122 (1.2% of expected intensity).

But we're seeing 9.4% of expected intensity, so there's still something missing.

## Next Action

The deficit is in the sincg lattice factor computation itself. We need to:

1. Instrument `nanobrag_torch.utils.physics.sincg` to capture per-subpixel sincg(Na,Δh), sincg(Nb,Δk), sincg(Nc,Δl) values
2. Check if the product sincg_a × sincg_b × sincg_c is being computed correctly
3. Verify that the accumulated F_latt is the sum (or mean) of these products across subpixels

However, this would require creating new instrumentation, which violates PROBE-FREEZE-001.

## Decision

Mark ARCH-SIM-CONSTRUCTION-001 as **blocked_pending_spec_change** and escalate to the supervisor for one of:

1. **spec_change** — Relax DB-AT-028/029 acceptance criteria to match observed physics
2. **architecture** — Open a new diagnostic initiative with harness-grade tooling to investigate sincg
3. **environment** — Request nanobrag_torch maintainer investigation (upstream blocker)

The current diagnostic tools have reached their limit, and further probing would violate PROBE-FREEZE-001 without delivering actionable evidence.

## Artifacts
- This planning summary
- Preserved evidence from C.34-C.38 in prior reports
- Ralph's blocked summary documenting the omega contradiction

## Turn Summary

Re-analyzed C.38/C.39 evidence and discovered omega was a red herring: the deficit exists in the raw subpixel sum BEFORE omega application. F_latt shows 11% of expected amplitude (1.2% of expected intensity squared), but observed intensity is 9.4% of expected, suggesting multiple compounding factors. Further instrumentation would violate PROBE-FREEZE-001. Recommend escalating to spec_change, opening a harness-grade diagnostic initiative, or marking as environment blocker pending maintainer investigation.

Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T150000Z/summary.md
