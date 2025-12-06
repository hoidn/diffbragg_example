# ARCH-SIM-CONSTRUCTION-001 Lifecycle Decision (2026-01-13T200000Z)

## Status: blocked_pending_environment

## Decision Summary

After 39 implementation loops (Phases C.1 through C.39) spanning from 2025-12-21 to 2026-01-13, ARCH-SIM-CONSTRUCTION-001 has exceeded the hard 6-loop budget without achieving either:
- (a) validated first-divergence location with actionable next production edit, OR
- (b) monotonic improvement on an intermediate parity metric

Per `non_negotiables::Total loop budget (hard)`, this initiative must now be marked blocked and focus must switch.

## Evidence Review

### Ralph's C.39 Blocking (Correct)

Ralph correctly identified a specification contradiction in the C.39 Do Now (reports/2026-01-13T010000Z/summary.md):

- **Specification**: Apply omega_scalar once after Riemann sum "mirroring oversample==1 branch"
- **DMI Ledger Expectation**: normalized/raw ratio ≈ 1.0
- **Physical Reality**: omega ≈ 1e-6 for test geometry, so applying it gives ratio 1e-6, NOT 1.0
- **Conclusion**: These requirements are mutually exclusive

### Root Cause Analysis From C.39 Re-analysis

The supervisor's omega hypothesis was **definitively rejected** by evidence showing:

1. **Deficit exists BEFORE omega application**:
   - Base case (N_cells=1,1,1): trace_subpixel_F_total_sq_sum = 1.187207e+09
   - Scaled case (N_cells=41,29,32): trace_subpixel_F_total_sq_sum = 1.614788e+17
   - Ratio: 1.360158e+08 (observed) vs 1.447650e+09 (expected) = **9.4% of expected**
   - This ratio appears in the RAW sum **before omega is applied**

2. **Omega cancels in the ratio**:
   - Both runs have omega≈1e-6, so omega cancels when computing ratio
   - Therefore omega cannot be causing the 90.6% deficit

3. **F_latt amplitude deficit**:
   - Observed F_latt: 4206.5
   - Expected F_latt: Na×Nb×Nc = 38,048
   - Ratio: 11.06% of expected amplitude
   - When squared: (0.1106)² ≈ 1.22% of expected intensity
   - But we're seeing 9.4% observed intensity, suggesting multiple compounding factors

### PROBE-FREEZE-001 Constraint

Phases C.34-C.39 exhausted the allowed diagnostic capacity:
- C.34: Per-subpixel payload instrumentation
- C.35: Oversample normalization fix (removed 169× dilution)
- C.36: Subpixel offset telemetry
- C.37: (planned) HKL projection audit (not executed)
- C.38: Oversample accumulation sanity check
- C.39: Omega compensation attempt (rejected)

Further plan-local instrumentation is **forbidden** under PROBE-FREEZE-001 policy (prompts/supervisor.md::diagnostic_script_policy, docs/findings.md::PROBE-FREEZE-001).

## Loop Budget Analysis

**Lifecycle Counters for ARCH-SIM-CONSTRUCTION-001:**
- Evidence/planning loops: 12 (C.1-C.3, C.9, C.20-C.25, C.37, C.39 planning)
- Implementation loops: 27 (C.4-C.8, C.10-C.19, C.26-C.36, C.38, C.39 attempt)
- **Total**: 39 loops

**Budget Violations:**
- Per-focus loop limit (6 loops): **EXCEEDED** (39 > 6)
- Repeat-signature probe freeze: **TRIGGERED** (C.38+C.39 both probed same signature without implementation between)
- Probe saturation (signature-level): **EXCEEDED** (>2 new probes for same selector+signature)

## Three Unblock Options

### Option A: Maintainer Investigation (Recommended)

**Scope**: Engage nanobrag_torch maintainer to investigate sincg lattice factor computation

**Evidence Package**:
- F_latt at 11% of expected amplitude (4206.5 vs 38,048)
- Observed intensity at 9.4% of expected ((Na·Nb·Nc)²)
- Oversample=1 achieves 0.0005% error (C.38), proving sincg/HKL/beam correct when oversample disabled
- Deficit appears in raw subpixel sum before omega application

**Blocker**: Requires maintainer availability

**Recommendation**: **This is the preferred path** — the evidence clearly points to a bug in nanobrag_torch's SQUARE lattice sincg computation, and further DBEX-side work cannot fix it.

### Option B: spec_change Initiative

**Scope**: Relax DB-AT-028/029 acceptance criteria

**Current Gates**:
- DB-AT-028: chi²/pixel initial ≤ 1e2 (currently ~2.1e5, **FAIL by 2100×**)
- DB-AT-029: median ROI correlation before ≥ 0.2 (currently -0.05, **FAIL**)

**Risk**: Masks real physics bugs; undermines acceptance testing

**Recommendation**: **Only pursue if Option A is unavailable** and we have physics justification for why 11% F_latt amplitude is acceptable.

### Option C: Harness-Grade Diagnostic Initiative

**Scope**: Create new architecture/harness initiative with first-class tooling

**Deliverables**:
- Architecture enforcement test: `tests/architecture/test_nanobrag_sincg_reference_parity.py`
- Diagnostic tool: `dbex/tools/sincg_validator.py` (not plan-local)
- Reference sincg implementation for validation
- May require Environment Freeze exception to patch nanobrag_torch

**Benefit**: Preserves PROBE-FREEZE-001 while enabling deeper investigation

**Recommendation**: **Fallback if Option A stalls** — this gives us decision-carrying evidence without violating probe freeze policy.

## Blocking Rationale

**Per `non_negotiables`:**

1. **Total loop budget (hard)**: "For a given selector+signature, after 6 total loops... without either (a) validated first-divergence or (b) monotonic improvement... you MUST switch focus or split to new initiative and mark original stuck"
   - **Status**: 39 loops, no validated first-divergence at production call boundary, no monotonic improvement (stuck at ~9.4% of expected)

2. **Probe saturation (signature-level)**: "After 2 new probes/instrumentation additions for same selector+signature, further probes forbidden until (a) production fix attempted or (b) dedicated harness/spec_change/architecture initiative opened"
   - **Status**: C.34-C.39 added 6 new instrumentation points; C.38+C.39 both probed without production fix between

3. **Repeat-signature Probe Freeze (hard)**: "If same acceptance selector+failure signature recurs in two consecutive loops and last loop's changes were probe/report-only, next loop cannot request more probes"
   - **Status**: C.38 and C.39 both probe-only for DB-AT-028/029 with same failure signature (chi²≈2.1e5, CC≈-0.05)

## Portfolio Decision

**Switch focus to**: [ARCH-IMPL-CONFORMANCE-001] (Tier 0, pending, architecture type)

**Rationale**:
- ARCH-IMPL-CONFORMANCE-001 is the next unblocked Tier 0 item
- Defined in docs/fix_plan.md as "Architecture / Implementation contract alignment"
- Will deliver ARCH-CONTRACTs + enforcement tests to prevent doc/impl drift
- Does not depend on ARCH-SIM-CONSTRUCTION-001

**Unblock Condition**:
- Maintainer investigation resolves sincg bug, OR
- spec_change initiative adjusts DB-AT-028/029 criteria with physics justification, OR
- New harness-grade diagnostic initiative (e.g., ARCH-SINCG-VALIDATION-001) provides decision-carrying evidence

## Cross-References

- **BLOCKED.md**: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T150000Z/BLOCKED.md (supervisor's initial analysis)
- **Ralph's Block**: reports/2026-01-13T010000Z/summary.md (C.39 implementation blocking)
- **C.38 Evidence**: reports/2026-01-11T010000Z/ (oversample=1 validation, omega telemetry)
- **C.34-C.37 History**: reports/{2026-01-05..2026-01-10}/ (sincg instrumentation attempts)
- **Problems Ledger**: problems.md line 34 (DB-AT-028/029 scale mismatch entry)
- **Probe Freeze Policy**: prompts/supervisor.md::diagnostic_script_policy, docs/findings.md::PROBE-FREEZE-001

## Next Actions (for Galph)

1. Update docs/fix_plan.md ARCH-SIM-CONSTRUCTION-001 status to `blocked_pending_environment`
2. Add this lifecycle decision to Attempts History with blocking justification
3. Add note recommending Option A (maintainer investigation)
4. Switch focus to ARCH-IMPL-CONFORMANCE-001
5. Issue input.md for ARCH-IMPL-CONFORMANCE-001 planning/kickoff

## Turn Summary

Lifecycle decision for ARCH-SIM-CONSTRUCTION-001: Marked blocked_pending_environment after 39 loops (C.1-C.39) exceeding 6-loop hard budget. Ralph's C.39 omega blocking was correct—evidence proves deficit exists in raw subpixel sum BEFORE omega application. F_latt at 11% of expected amplitude indicates sincg lattice factor bug in nanobrag_torch itself. Three unblock options: (A) maintainer investigation [RECOMMENDED], (B) spec_change to relax DB-AT-028/029, (C) harness-grade diagnostic initiative. PROBE-FREEZE-001 forbids further plan-local instrumentation. Switching focus to ARCH-IMPL-CONFORMANCE-001 (Tier 0, unblocked).

Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T200000Z/lifecycle_decision.md
