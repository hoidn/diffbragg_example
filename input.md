# Loop i=108 — ARCH-IMPL-CONFORMANCE-001 Phase A.1 Planning

## Summary
Plan Phase A.1 (nucleus architecture test) for ARCH-IMPL-CONFORMANCE-001 after ARCH-SIM-CONSTRUCTION-001 blocked pending environment investigation.

## Mode
Docs

## ActionType
planning

## DecisionStatus
exploring

## InitiativeType
architecture

## Focus
[ARCH-IMPL-CONFORMANCE-001] — Architecture / Implementation Contract Alignment

## Branch
integration

## Mapped Tests
none — planning-only (architecture test nucleus will be defined this loop)

## Artifacts
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/`

## Findings Applied (Mandatory)
- **SCALE-008** (docs/findings.md:322-339): Stage A warm-cache baseline authority — relevant for defining the Stage A ↔ reconstruction scaling contract.
- **SCALE-009** (docs/findings.md:341-358): Reconstruction scaling provenance (to be corrected/clarified under this initiative).
- **ARCH-FACTORY-001** (docs/findings.md:360-377): Unified simulator factory responsibilities — provides boundaries for the proposed owner API.
- **PROBE-FREEZE-001** (docs/findings.md:379-396): Probe freeze policy — enforcement tests must be under `tests/architecture/`, not plan-local.
- **No other findings directly applicable** to Phase A.1 planning scope.

## Pointers
- **Spec:** docs/spec-db-core.md:20-140 (simulator construction, calibration threading)
- **Architecture:** docs/architecture/calibration_scaling.md:80-145 (spot_scale/sigma threading), docs/architecture/module_map.md (owner modules)
- **Testing Guide:** docs/TESTING_GUIDE.md:255-320 (architecture test execution workflow)
- **Implementation Plan:** plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md:1-100
- **Kickoff Report:** plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/summary.md (findings inventory, module inventory)

## ARCH Contracts (mandatory)
### Relevant ARCH-CONTRACTs for this initiative:
1. **ARCH-SCALE-PARITY-001** (to be defined this initiative):
   - **Owner Module/API:** `dbex.refinement.helpers.simulate_forward_once` (canonical mapping forward path)
   - **Forbidden Duplicates:** Any Stage A or reconstruction helper that re-implements spot_scale threading or sqrt multiplication outside the owner API
   - **Failure Classification:** Implementation bug (Stage A vs reconstruction currently duplicate spot_scale logic; must centralize)

2. **ARCH-BASELINE-OVERRIDE-001** (to be defined this initiative):
   - **Owner Module/API:** `dbex.refinement.stage_a_utils.build_mapping_stage_a_context` (warm-cache authority for masked-intensity baseline)
   - **Forbidden Duplicates:** Reconstruction helpers must not re-derive masked baselines independently; must consume telemetry baseline
   - **Failure Classification:** Architecture conformance failure (reconstruction helper currently ignores telemetry baseline in some paths)

## Do Now (hard validity contract)

### Focus
[ARCH-IMPL-CONFORMANCE-001] Phase A.1 — Nucleus Architecture Test Planning

### Implement
Not applicable (Mode: Docs) — **Planning loop only**. Next loop will implement the nucleus test defined here.

### Validating pytest selector(s)
None this loop (nucleus test does not exist yet; will be created next loop per plan output).

### Artifacts path
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/`

### Initiative type constraint check
✅ Initiative type=architecture; requested work=planning ARCH-CONTRACTs, defining nucleus test scope — **VALID**

### Concrete deliverables for this loop:
1. **Read kickoff report** (plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/summary.md, findings_inventory.md, module_inventory.md) to understand duplicated scaling patterns already identified.

2. **Design nucleus architecture test** (Phase A.0 checklist item):
   - Test file: `tests/architecture/test_scale_contracts.py` (new file)
   - Test function: `test_stage_a_vs_reconstruction_scale` (minimal reproducer)
   - Scope: Compare masked mean outputs from Stage A warm-cache vs reconstruction helper using refGeom_small fixture (same geometry, same calibration metadata, param_state="initial")
   - Expected behavior: Masked means must match within ≤1e-6 relative error (docs/spec-db-core.md:60-140 tolerance)
   - Current expected outcome: **FAIL** (exposes current mismatch from ARCH-SIM-CONSTRUCTION-001 C.1-C.39 evidence)

3. **Document test design** in new planning note:
   - File: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/nucleus_test_design.md`
   - Contents:
     - Test rationale (expose Stage A vs reconstruction scaling drift)
     - Fixture selection (refGeom_small, same as DB-AT-027/028/029)
     - Assertion logic (masked mean comparison)
     - Success criteria (FAIL initially, PASS after Phase B owner API implemented)
     - Cross-refs to SCALE-008/009, ARCH-FACTORY-001

4. **Draft Phase A.1 implementation plan** for next loop:
   - File: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/phase_a1_implementation_plan.md`
   - Contents:
     - Step-by-step guide for implementing `test_stage_a_vs_reconstruction_scale`
     - Required imports (`DataLoad`, `build_mapping_stage_a_context`, `build_final_bragg_from_stage_a_telemetry`)
     - Fixture setup (load refGeom_small, run Stage A to get telemetry)
     - Reconstruction invocation (call helper with telemetry, param_state="initial")
     - Comparison logic (compute masked means, assert within tolerance)
     - Validation commands (pytest selector, expected FAIL outcome with metrics capture)

5. **Update implementation.md Phase A checklist**:
   - Mark A0 as [x] complete (nucleus test designed)
   - Update status to reflect planning complete, ready for A.1 implementation next loop

6. **Write summary.md** for this planning loop documenting:
   - Lifecycle decision from ARCH-SIM-CONSTRUCTION-001 (marked blocked_pending_environment)
   - Portfolio switch rationale (Tier 0 unblocked item)
   - Nucleus test design summary
   - Next action (delegate test implementation to Ralph)

## Forbidden This Loop
- **No production code changes** (planning only)
- **No new probes** (enforcement tests are the mechanism, not plan-local probes)
- **Do not implement the nucleus test yet** (design it, defer implementation to next loop)

## How-To Map

### Commands for this loop
No pytest/probe runs this loop. Planning only.

### Artifact destinations
All deliverables go to: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/`
- `nucleus_test_design.md`
- `phase_a1_implementation_plan.md`
- `summary.md`
- Updated `../implementation.md` (mark A0 complete)

## Pitfalls To Avoid
1. **Type discipline:** This is an `architecture` initiative. Do not attempt `spec_change` work (relaxing acceptance criteria). Only align implementation to existing spec.
2. **No stacking on cliff:** ARCH-SIM-CONSTRUCTION-001 is blocked on environment dependency; do not try to fix it here. Focus on ARCH-IMPL-CONFORMANCE-001 scope only.
3. **Parity-first:** Nucleus test should expose the Stage A vs reconstruction mismatch that blocked ARCH-SIM-CONSTRUCTION-001. Design it carefully so it's a stable baseline.
4. **Shadow-pipeline guard:** Enforcement tests go under `tests/architecture/`, NOT `plans/active/.../bin/`. Follow PROBE-FREEZE-001 policy.
5. **Implementation floor:** This is the first planning loop for this initiative. Next loop MUST implement the nucleus test (not another planning loop).
6. **ARCH/Impl consistency gate:** You have classified this as an implementation bug (Stage A vs reconstruction duplicate spot_scale logic). Do not retype unless evidence shows otherwise.

## If Blocked
If you discover that the nucleus test cannot be designed without additional evidence (e.g., missing telemetry fields, unclear reconstruction helper API):
- Document the blocking condition in `nucleus_test_design.md`
- Mark initiative as `blocked_pending_<reason>` in implementation.md
- Switch focus back to Tier 1 or propose a diagnostic initiative to gather missing evidence
- Do NOT proceed with Phase A.1 implementation if design is incomplete

## Doc Sync Plan
Not applicable this loop (no new tests yet; nucleus test will be added next loop and collection log will be captured then).

---

## Background Context

### ARCH-SIM-CONSTRUCTION-001 Blocking Summary
- After 39 loops (C.1-C.39), ARCH-SIM-CONSTRUCTION-001 marked **blocked_pending_environment** (2026-01-13T200000Z).
- Root cause: sincg lattice factor bug in nanobrag_torch SQUARE branch (F_latt at 11% of expected amplitude).
- PROBE-FREEZE-001 forbids further plan-local instrumentation.
- Three unblock options: (A) maintainer investigation [RECOMMENDED], (B) spec_change, (C) harness-grade diagnostic initiative.
- Lifecycle budget exceeded: 39 loops vs 6-loop hard limit without validated first-divergence or monotonic improvement.
- Cross-refs: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T200000Z/lifecycle_decision.md, reports/2026-01-13T150000Z/BLOCKED.md

### Portfolio Steering Decision
- Switched focus to ARCH-IMPL-CONFORMANCE-001 (Tier 0, pending, architecture type, unblocked).
- Rationale: Define ARCH-CONTRACTs + enforcement tests to prevent future Stage A/reconstruction drift.
- Kickoff planning already complete (2026-01-13T150000Z): findings inventory, module inventory.
- Next step: Design nucleus test (Phase A.0), then implement it (Phase A.1 next loop).

### Key Findings Context
- **SCALE-008:** Stage A warm-cache masked-intensity baseline is authoritative (docs/findings.md:322-339).
- **SCALE-009:** Reconstruction scaling provenance (to be corrected under this initiative; docs/findings.md:341-358).
- **ARCH-FACTORY-001:** Unified simulator factory responsibilities (docs/findings.md:360-377).
- **PROBE-FREEZE-001:** Enforcement tests must be under `tests/architecture/`, not plan-local (docs/findings.md:379-396).

---

**End of input.md**
