# Input for Loop i=113 — ARCH-IMPL-CONFORMANCE-001 Phase B.5: Debug Cold-Path Test Hang

## Summary
Diagnose and resolve Phase A.2 cold-path test hang from loop i=112. Implementation complete but validation blocked.

## Mode
none

## ActionType
debug

## DecisionStatus
patch_ready

## InitiativeType
architecture

## Focus
ARCH-IMPL-CONFORMANCE-001 — Architecture / Implementation Contract Alignment

## Branch
integration

## Mapped tests
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path` (Phase A.2, expect PASS after timeout fix)
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale` (Phase A.1, regression check, expect PASS)

## Artifacts
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T060000Z/`

## Findings Applied (Mandatory)
- **SCALE-002**: Global scaling factor application (spot_scale_override sqrt) — canonical API now enforces
- **SCALE-008**: Stage A warm-cache authority — Phase A.1 validated
- **SCALE-009**: Reconstruction scaling provenance — corrected via canonical API (Phase B.3-B.4)
- **ARCH-CONTRACT-002**: Canonical scaling owner API (apply_sqrt_spot_scale) — now enforced
- **POLICY-001**: Environment Freeze — adhered to (no upstream changes)

## ARCH Contracts (mandatory)
**ARCH-CONTRACT-002**: Stage A vs Reconstruction Scaling Contract
- **Owner module/API**: `dbex.refinement.scaling_utils.apply_sqrt_spot_scale`
- **Duplicates removed**: Stage A (stage_a.py:438-450), Reconstruction (reconstruction.py:213-221)
- **Failure classification**: Implementation conformance (duplicated logic eliminated Phase B.3-B.4)

## Do Now (hard validity contract)

**Focus**: ARCH-IMPL-CONFORMANCE-001 Phase B.5

**Context**:
Loop i=112 completed Phase B.3-B.4 refactor (canonical API integration). Phase A.1 warm-cache test PASSED (9.57s). Phase A.2 cold-path test HUNG after ~2.5min. Code review shows implementation is correct (canonical API properly applied at reconstruction.py:501-509). Need to diagnose hang source.

**Implement**:
1. **Primary diagnostic**: Run Phase A.2 with 10min pytest timeout to rule out slow-but-working execution
2. **If still hangs**: Add minimal print instrumentation to identify where execution stalls
3. **If passes with extended timeout**: Update Phase A.2 test with timeout decorator and document expected runtime
4. **If fails with error**: Capture full stack trace, analyze root cause, fix if simple config issue

**Validating pytest**:
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path` (diagnostic run, expect PASS or actionable error)
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale` (regression, expect PASS)

**Artifacts path**:
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T060000Z/`

**Initiative type consistency**:
`architecture` (ARCH-IMPL-CONFORMANCE-001 enforcing ARCH-CONTRACT-002)

## Forbidden This Loop
- **No new probes**: Use pytest timeout + minimal print instrumentation only
- **No plan-local diagnostic scripts**: All instrumentation inline
- **No architecture changes**: This is debug-only to unblock validation

## Pointers
- **Implementation plan**: `plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md`
- **Phase B.3-B.4 planning**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/phase_b3_b4_planning.md`
- **Canonical API**: `dbex/refinement/scaling_utils.py:35-111`
- **Stage A scaling**: `dbex/refinement/stage_a.py:438-450`
- **Reconstruction scaling**: `dbex/refinement/reconstruction.py:501-509`
- **Phase A.2 test**: `tests/architecture/test_scale_contracts.py:232-305`
- **TESTING_GUIDE**: `docs/TESTING_GUIDE.md:56-68` (test execution workflow)
- **Findings**: `docs/findings.md` (SCALE-002, SCALE-008, SCALE-009, ARCH-CONTRACT-002)
