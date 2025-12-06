# ARCH-IMPL-CONFORMANCE-001 Loop i=108 — Phase A.0 Nucleus Test Design

---

### Turn Summary (Ralph, 2026-01-13T200000Z)

Completed docs-only planning loop (i=108, Mode: Docs) for ARCH-IMPL-CONFORMANCE-001 Phase A.0 nucleus test design. Designed `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale` to enforce Stage A vs reconstruction masked_mean parity (ARCH-CONTRACT-002, ≤1e-6 rel tolerance, expected baseline FAIL). Drafted detailed Phase A.1 implementation plan with step-by-step guide for next loop (API search, test implementation, baseline FAIL capture, ledgers update, commit). Updated implementation.md: marked A0 complete, added status note. Next: Implement nucleus test per phase_a1_implementation_plan.md (loop i=109).

Artifacts: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/nucleus_test_design.md, phase_a1_implementation_plan.md

---

# ARCH-IMPL-CONFORMANCE-001 Loop i=108 — Portfolio Switch After ARCH-SIM-CONSTRUCTION-001 Blocked

## Status: Planning (Focus Switch from Blocked Initiative)

## Loop Context

### Previous Focus (ARCH-SIM-CONSTRUCTION-001)
- **Outcome**: Marked `blocked_pending_environment` after 39 loops (C.1-C.39)
- **Root Cause**: sincg lattice factor bug in nanobrag_torch SQUARE branch
  - F_latt at 11% of expected amplitude (4206.5 vs 38,048)
  - Observed intensity at 9.4% of expected ((Na·Nb·Nc)²)
  - Deficit exists in raw subpixel sum BEFORE omega application
- **Blocking Factors**:
  - PROBE-FREEZE-001 forbids further plan-local instrumentation
  - Lifecycle budget exceeded: 39 loops vs 6-loop hard limit
  - Ralph's C.39 omega blocking was correct (omega hypothesis rejected by evidence)
- **Unblock Options**:
  - (A) Maintainer investigation [RECOMMENDED] — engage nanobrag_torch maintainer
  - (B) spec_change — relax DB-AT-028/029 acceptance criteria (risky)
  - (C) Harness-grade diagnostic initiative — new architecture/harness initiative with first-class tooling

### Portfolio Steering Decision
- **Switched focus to**: ARCH-IMPL-CONFORMANCE-001 (Tier 0, pending, architecture type, unblocked)
- **Rationale**: Define ARCH-CONTRACTs + enforcement tests to prevent future Stage A/reconstruction drift
- **Dependencies**: No blockers; kickoff planning complete (2026-01-13T150000Z)

## This Loop Actions (Planning)

### Deliverables Delegated to Ralph (input.md)

**Mode**: Docs (planning-only loop)

**ActionType**: planning

**Artifacts Path**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/`

**Concrete Deliverables**:
1. Read kickoff report (2026-01-13T150000Z: summary.md, findings_inventory.md, module_inventory.md)
2. Design nucleus architecture test:
   - Test file: `tests/architecture/test_scale_contracts.py` (new)
   - Test function: `test_stage_a_vs_reconstruction_scale`
   - Scope: Compare masked mean outputs (Stage A warm-cache vs reconstruction helper, refGeom_small fixture)
   - Expected: **FAIL** initially (exposes current mismatch from ARCH-SIM-CONSTRUCTION-001 C.1-C.39 evidence)
3. Document test design in `nucleus_test_design.md`
4. Draft Phase A.1 implementation plan for next loop (`phase_a1_implementation_plan.md`)
5. Update implementation.md Phase A checklist (mark A0 complete)
6. Write summary.md for this planning loop

**Mapped Tests**: None (planning-only; nucleus test does not exist yet)

## ARCH-CONTRACTs Identified

### 1. ARCH-SCALE-PARITY-001 (to be formally defined)
- **Owner Module/API**: `dbex.refinement.helpers.simulate_forward_once` (canonical mapping forward path)
- **Forbidden Duplicates**: Stage A/reconstruction helpers that re-implement spot_scale threading or sqrt multiplication
- **Current Status**: Implementation bug (duplicated spot_scale logic; must centralize)

### 2. ARCH-BASELINE-OVERRIDE-001 (to be formally defined)
- **Owner Module/API**: `dbex.refinement.stage_a_utils.build_mapping_stage_a_context` (warm-cache authority)
- **Forbidden Duplicates**: Reconstruction helpers must consume telemetry baseline, not re-derive independently
- **Current Status**: Architecture conformance failure (reconstruction ignores telemetry baseline in some paths)

## Key Findings Referenced
- **SCALE-008** (docs/findings.md:322-339): Stage A warm-cache baseline authority
- **SCALE-009** (docs/findings.md:341-358): Reconstruction scaling provenance (to be corrected)
- **ARCH-FACTORY-001** (docs/findings.md:360-377): Unified simulator factory responsibilities
- **PROBE-FREEZE-001** (docs/findings.md:379-396): Enforcement tests under `tests/architecture/` only

## Next Loop Expectations

**Phase A.1 Implementation** (next loop):
- Ralph will implement the nucleus test per the design from this loop
- Expected outcome: Test **FAILS** initially, exposing Stage A vs reconstruction mismatch
- Validation: Capture pytest log + metrics showing failure signature
- No production fixes yet (Phase B will implement owner API to make test pass)

## Lifecycle Tracking

**ARCH-SIM-CONSTRUCTION-001 Final State**:
- Status: blocked_pending_environment
- Blocks: ARCH-REFACTOR-001 Phase D.3
- Lifecycle decision: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T200000Z/lifecycle_decision.md

**ARCH-IMPL-CONFORMANCE-001 State**:
- Status: pending → will become in_progress after A.1 implementation
- Priority: High (Tier 0)
- Initiative type: architecture
- Current phase: A.0 (nucleus test planning) → A.1 (implementation next loop)

## Turn Summary

Lifecycle decision for ARCH-SIM-CONSTRUCTION-001: Marked blocked_pending_environment after 39 loops exceeding 6-loop budget. Ralph's C.39 omega blocking was correct—omega hypothesis rejected by evidence. F_latt at 11% of expected amplitude indicates sincg lattice factor bug in nanobrag_torch. Three unblock options identified (maintainer investigation recommended). Switched focus to ARCH-IMPL-CONFORMANCE-001 (Tier 0, unblocked). Issued planning Do Now for Phase A.0: design nucleus architecture test to expose Stage A vs reconstruction scaling drift. Next loop: implement nucleus test (expected FAIL initially).

Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T200000Z/lifecycle_decision.md, plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/summary.md (this file), input.md (planning delegation to Ralph)
