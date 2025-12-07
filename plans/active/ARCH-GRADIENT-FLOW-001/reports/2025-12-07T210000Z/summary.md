# ARCH-GRADIENT-FLOW-001 — Planning Summary (Loop i=137, Galph)

**Date**: 2025-12-07T210000Z
**Initiative**: ARCH-GRADIENT-FLOW-001 — Gradient Flow Restoration (DB-AT-010 Unblock)
**Action Type**: planning
**Decision Status**: exploring
**Branch**: integration

---

## Executive Summary

Created new **Tier-0 architecture initiative** ARCH-GRADIENT-FLOW-001 in response to DB-AT-SUITE-CARE-001 Phase B.1 verification (Ralph i=136) confirming DB-AT-010 gradcheck regression persists: **5/5 tests FAILING** with identical signature (`GradcheckError: disconnected autograd graph`). Escalated per DB-AT-SUITE-CARE-001 implementation.md Phase B.1 directive. Authored full initiative plan (Phases A/B/C), updated fix_plan.md Tier 0, created cross-references, and prepared input.md for Ralph i=138 (Phase A.1-A.2: call graph trace + suspect module audit).

**Key Decision**: Tier-0 blocker requires immediate focus; DB-AT-SUITE-CARE-001 portfolio advancement now blocked pending gradient flow fix.

---

## Context

### Trigger Event (Ralph i=136)
- **DB-AT-010 verification**: 5/5 gradcheck tests executed with canonical flags (`KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 --smoke-detector-size=full`)
- **Exit code**: 1 (test failures, not collection errors)
- **Pass rate**: 0/5 (0%)
- **Failure signature**: `torch.autograd.gradcheck.GradcheckError: Numerical gradient for function expected to be zero` (torch/autograd/gradcheck.py:981)
- **Root cause pattern**: Disconnected autograd graph — forward simulation executes (loss ~3.66e+09), but `torch.autograd.backward()` cannot propagate gradients
- **Harness status**: Stable (Phase B.3/B.4 fixes successful, no collection errors)

### Escalation Directive
DB-AT-SUITE-CARE-001 Phase B.1 task definition (implementation.md lines 36-37):
> **B1 — Tier-0 escalation**: Coordinate DB-AT-010 Phase D unblocking (gradcheck regression fix). Ensure TorchCrystal bridge audit and `.item()` coercion patch land before advancing other plans.

This loop executes that directive by creating dedicated Tier-0 initiative.

---

## Deliverables (This Loop)

### 1. Initiative Implementation Plan
**File**: `plans/active/ARCH-GRADIENT-FLOW-001/implementation.md`

**Contents**: Full Phases A/B/C structure (16 tasks, 5 exit criteria, estimated 5-7 loops)

**Phase A — Gradient Flow Audit & Root Cause Localization** (3-4 loops):
- A1: Call graph trace (test → forward → loss → backward path mapping)
- A2: Suspect module audit (grep `.item()`, `.detach()`, `.numpy()`, in-place ops, `.cpu()` in 4 modules)
- A3: Minimal gradient probe (thin wrapper <400 LOC, isolate break point empirically)
- A4: Hypothesis ranking (top 3 root causes, confidence scores)

**Phase B — Root Cause Fix & Enforcement Test** (2-3 loops):
- B1: Implement fix (patch identified gradient break, preserve production logic)
- B2: Gradcheck verification (re-run DB-AT-010 suite, expect 5/5 PASS)
- B3: Enforcement test authoring (`tests/architecture/test_gradient_contracts.py::test_simulate_forward_torch_preserves_gradients`)
- B4: Documentation updates (findings.md::GRADIENT-002, architecture.md §13 Pitfalls, TEST_SUITE_INDEX.md)

**Phase C — Closure & Lessons Learned** (1 loop):
- C1: fix_plan.md update (add Tier 0 entry, cross-ref DB-AT-SUITE-CARE-001)
- C2: Closure summary (problem, root cause, fix, validation, lessons)
- C3: Archive artifacts (move to archive/plans/ after closure)
- C4: Propagate lessons (search other modules for similar patterns)

### 2. Planning Notes
**File**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T210000Z/planning_notes.md`

**Contents**:
- Context (trigger event, symptoms, escalation directive)
- Objectives (initiative creation, Phase A task design, exit criteria, enforcement test pattern)
- Phase A task design (A1-A4 detailed approach: call graph tracing, grep patterns, probe structure, hypothesis ranking)
- Exit criteria mapping (how Phase A outputs enable Phase B fix)
- Spec/Arch alignment (GRADIENT-001, RUNTIME-001, TESTING-003, architecture.md §13)
- Risks & mitigations (PROBE-FREEZE-001 compliance, multiple gradient breaks, upstream nanobrag_torch issues, behavior preservation)
- Pointers (evidence artifacts from i=136, SPEC/ARCH/Testing docs)
- Expected flow (Ralph i=138 execution steps, Galph i=139 review criteria)

### 3. fix_plan.md Updates
**Tier 0 Addition**:
- Inserted [ARCH-GRADIENT-FLOW-001] as first Tier 0 item (above ARCH-IMPL-CONFORMANCE-001)
- Status: **in_progress** (Phase A planning complete, Phase A.1-A.2 execution next)
- Cross-refs: Blocks DB-AT-SUITE-CARE-001, Gradient-Safe Profile conformance
- Governed by: GRADIENT-001, RUNTIME-001, TESTING-003

**DB-AT-SUITE-CARE-001 Updates**:
- Updated Dependencies: Now depends on ARCH-GRADIENT-FLOW-001 (DB-AT-010 unblock)
- Updated Status: Phase B.1 complete — escalated to Tier-0; Phase B.2-B.7 pending
- Attempts History: Added i=136 (verification result), i=137 (escalation to ARCH-GRADIENT-FLOW-001)

**Detailed Entry**:
- Lines 228-244: Full ARCH-GRADIENT-FLOW-001 initiative with exit criteria, working plan pointer, Attempts History

### 4. input.md for Ralph i=138
**File**: `/home/ollie/Documents/diffbragg_example/input.md`

**Contents**:
- Summary: Phase A.1-A.2 call graph trace + suspect module audit
- Focus: ARCH-GRADIENT-FLOW-001
- ActionType: planning (evidence collection, not implementation)
- DecisionStatus: exploring
- Findings Applied: GRADIENT-001, RUNTIME-001, TESTING-003
- ARCH Contracts: ARCH-CONTRACT-GRADIENT-FLOW (implicit), ARCH-CONTRACT-TESTING-001, ARCH-CONTRACT-FORWARD-SIMULATION
- Do Now:
  - A.1: Trace test → forward → loss → backward path, create call graph diagram (≥5 call stack levels)
  - A.2: Grep 4 modules for 6 gradient-break patterns (.item(), .detach(), .numpy(), *=, +=, .cpu()), classify SAFE/UNSAFE, identify top candidate
- Deliverables: call_graph_trace.md, grep_*.txt (6 files), suspect_audit.md, summary.md
- Pitfalls: No test execution, no fixes, environment freeze, type discipline, thin wrapper guardrail
- Expected runtime: 2-2.5 hours

### 5. galph_memory.md Update
Prepended i=137 entry:
- Focus: ARCH-GRADIENT-FLOW-001
- State: planning
- Action: planning
- Artifacts: plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T210000Z/
- Next action: phase_a1_a2_call_graph_and_suspect_audit
- Summary: Created Tier-0 initiative, escalated from DB-AT-SUITE-CARE-001, scoped 4 suspect modules, authored plans

---

## Key Decisions

### 1. Initiative Type: Architecture (Not Bugfix)
**Rationale**:
- Requires enforcement test (Phase B.3: `tests/architecture/test_gradient_contracts.py`)
- Gradient flow preservation is architectural contract for differentiable forward simulation
- Fix scope includes contract formalization + enforcement mechanism (not just code patch)

**Type Discipline Adherence**: Architecture initiatives require enforcement tests to prevent regression (per ARCH-IMPL-CONFORMANCE-001 precedent).

### 2. Tier-0 Priority (Highest)
**Rationale**:
- **Blocks Gradient-Safe Profile conformance**: DB-AT-010 is acceptance gate per `docs/spec-db-conformance.md`
- **Blocks DB-AT-SUITE-CARE-001 portfolio advancement**: Phase B.2-B.7 cannot proceed until Tier-0 resolved
- **Affects 7 member plans**: DB-AT-002/010/020/021/022/023/024 depend on gradient correctness

**Portfolio Steering**: All Tier 0 items except ARCH-GRADIENT-FLOW-001 are blocked or done; this is sole unblocked Tier-0 focus.

### 3. Phase A Approach: Evidence-First (Not Immediate Fix)
**Rationale**:
- **Non-negotiables Evidence→Action contract**: Must identify exact root cause before implementing fix
- **Ralph's i=136 evidence insufficient**: Failure signature identifies symptom (disconnected graph), not location (which module/line breaks gradient)
- **Avoid stacking fixes**: If fix attempt fails without localization, creates cliff (multiple hypotheses, no triage)

**Expected Value**: Phase A.1-A.2 (call graph + grep) should identify top candidate with ≥0.5 confidence; Phase B.1 fix attempt follows.

### 4. Suspect Module Scope: 4 Modules (Not Full Codebase)
**Modules**: `dbex/physics/forward.py`, `dbex/geometry/crystallography.py`, `dbex/physics/loss.py`, `dbex/refinement/inputs.py`

**Rationale**:
- **Call path relevance**: These 4 modules lie on test → forward → loss execution path (per Ralph's i=136 test structure analysis)
- **Gradient flow criticality**: Entry points (forward.py), parameter hydration (crystallography.py), loss computation (loss.py), config assembly (inputs.py)
- **Grep efficiency**: 4 modules = ~2000 LOC audit scope; 6 patterns × 4 modules = 24 grep commands (manageable in 1 loop)

**Alternative Rejected**: Full `dbex/` codebase grep would produce noise (e.g., `.item()` in writer/telemetry safe to ignore).

### 5. Enforcement Test Location: `tests/architecture/` (Not `tests/dbex/`)
**Rationale**:
- **ARCH-IMPL-CONFORMANCE-001 precedent**: Architecture contract enforcement tests live under `tests/architecture/test_*_contracts.py`
- **Separation of concerns**: Acceptance tests (DB-AT-010) validate end-to-end behavior; enforcement tests validate architectural invariants
- **Regression prevention**: Architecture tests run in CI; detect contract violations early

**File**: `tests/architecture/test_gradient_contracts.py::test_simulate_forward_torch_preserves_gradients` (Phase B.3)

---

## Spec/Arch Alignment

### SPEC: docs/spec-db-conformance.md §Gradient-Safe Profile
- **Requirement**: DB-AT-010 gradcheck must pass with `eps=1e-6, atol=1e-5, rtol≈0.05`
- **Current Status**: NON-CONFORMING (0/5 tests PASS)
- **ARCH-GRADIENT-FLOW-001 Contribution**: Restores conformance by fixing gradient flow break

### ARCH: docs/architecture.md §13 Common Pitfalls
- **Current Coverage**: Device/dtype neutrality, square-pixel enforcement, ADU↔photon policy
- **Phase B.4 Addition**: "Gradient Flow Preservation" subsection documenting `.item()` / `.detach()` / in-place op risks
- **Purpose**: Prevent future gradient breaks via developer awareness

### FINDINGS: GRADIENT-001 (Gradient test patterns)
- **Contract**: Tests inject differentiable parameters via `crystal_overrides` dict (correct pattern verified)
- **Current Status**: Test harness uses correct pattern (Ralph's i=136 verification confirms)
- **Implication**: Problem is NOT in test harness (production code issue)

### FINDINGS: RUNTIME-001 (Runtime execution guardrails)
- **Contract**: DB-AT-010 requires `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference
- **Current Status**: Ralph's i=136 verification used canonical flags (correct)
- **Implication**: Runtime environment correct; gradient break is code issue, not config issue

---

## Risks & Mitigations

### Risk 1: Gradient Break in nanobrag_torch Upstream
**Symptom**: Phase A.1-A.3 evidence points to `nanobrag_torch.Simulator` internals (outside dbex/)
**Mitigation**: Mark ARCH-GRADIENT-FLOW-001 as blocked_pending_environment; escalate to maintainer
**Contingency**: Spec_change to relax gradcheck tolerances OR xfail DB-AT-010 with documented hypothesis

### Risk 2: Multiple Gradient Breaks Across Modules
**Symptom**: Phase A.2 grep finds >10 unsafe `.item()` calls in 4 modules
**Mitigation**: Phase A.4 hypothesis ranking prioritizes by call graph order; fix top candidate first (Phase B.1), re-run gradcheck, iterate
**Contingency**: Phase B budget may expand from 2-3 loops to 4-5 loops (still under 6-loop total budget)

### Risk 3: Fix Changes Production Behavior
**Symptom**: Phase B.1 patch (e.g., removing `.item()`) alters numerical output (loss value changes)
**Mitigation**: Phase B.2 gradcheck verification PLUS Stage A/B/C smoke regression tests must PASS
**Contingency**: If behavior changes, reclassify as bugfix (not architecture) and update exit criteria with numerical parity requirements

### Risk 4: Probe Violates PROBE-FREEZE-001
**Symptom**: Phase A.3 gradient probe (next loop) exceeds 400 LOC or re-implements production semantics
**Mitigation**: Strict thin wrapper enforcement (import production `simulate_forward_torch`, measure only, no physics re-derivation)
**Contingency**: If probe grows large, skip A.3 and rely on A.1+A.2 grep evidence for hypothesis ranking

---

## Portfolio Implications

### Tier 0 Status
- **Before this loop**: ARCH-IMPL-CONFORMANCE-001 (done), ARCH-SIM-CONSTRUCTION-001 (blocked_pending_environment), ARCH-REFACTOR-001 (blocked_pending_architecture), others (done/archived)
- **After this loop**: ARCH-GRADIENT-FLOW-001 added (in_progress, sole unblocked Tier-0 focus)
- **Impact**: Tier 0 now has exactly 1 unblocked active initiative (ARCH-GRADIENT-FLOW-001); portfolio must resolve this before Tier 1 work

### Tier 1 DB-AT-SUITE-CARE-001 Status
- **Before this loop**: Phase B.1 complete (verification determined DB-AT-010 FAILING), ready for Phase B.2-B.7
- **After this loop**: Blocked pending ARCH-GRADIENT-FLOW-001 Phase B completion (gradcheck 5/5 PASS required)
- **Impact**: DB-AT-SUITE-CARE-001 portfolio advancement paused; 7 member plans await Tier-0 resolution

### Gradient-Safe Profile Conformance
- **Before this loop**: NON-CONFORMING (DB-AT-010 FAILING)
- **After this loop**: Still NON-CONFORMING (work in progress)
- **Expected Resolution**: ARCH-GRADIENT-FLOW-001 Phase B.2 (5-7 loops estimated)

---

## Next Steps

### Ralph Loop i=138 (Phase A.1-A.2 Execution)
**Deliverables**:
1. `call_graph_trace.md` — Execution path diagram (≥5 call stack levels, tensor flow points)
2. `grep_*.txt` — 6 grep output files (item, detach, numpy, inplace_mul, inplace_add, cpu)
3. `suspect_audit.md` — Analysis of grep results (SAFE/UNSAFE classification, top candidate hypothesis)
4. `summary.md` — Phase A.1-A.2 completion status, preliminary hypothesis, next action recommendation

**Expected Runtime**: 2-2.5 hours

**Validation Criteria**:
- ≥5 module/function boundaries documented in call graph
- ≥10 grep matches analyzed (SAFE vs UNSAFE classification)
- Top candidate hypothesis identified (confidence score, file:line location)
- Next action clear (Phase A.3 gradient probe OR Phase B.1 fix if evidence conclusive)

### Galph Loop i=139 (Phase A.3 Planning OR Phase B.1 Planning)
**Decision Point**: If Ralph's i=138 grep audit identifies high-confidence root cause (≥0.7), proceed to Phase B.1 (fix implementation). Otherwise, proceed to Phase A.3 (gradient probe).

**Phase B.1 Trigger**: Top candidate hypothesis with:
- Exact file:line location (e.g., `loss.py:145`)
- Explicit code pattern (e.g., `.item()` on variance denominator)
- Confidence ≥0.7
- Single fix location (not multiple hypotheses)

**Phase A.3 Trigger**: If:
- Grep finds zero unsafe patterns (gradient break hidden in property getter/external module)
- Multiple candidates with similar confidence (<0.5 each)
- Call graph trace reveals gradient break may be in nanobrag_torch upstream

---

## Artifacts

**Location**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T210000Z/`

**Files Created (This Loop)**:
1. `implementation.md` — Full Phases A/B/C plan (16 tasks, 5 exit criteria, estimated 5-7 loops)
2. `planning_notes.md` — Context, objectives, Phase A design, risks, expected flow (comprehensive planning document)
3. `summary.md` — This file (loop summary)

**Files Updated (This Loop)**:
1. `/home/ollie/Documents/diffbragg_example/docs/fix_plan.md` — Tier 0 addition (ARCH-GRADIENT-FLOW-001), DB-AT-SUITE-CARE-001 updates (dependency, status, Attempts History)
2. `/home/ollie/Documents/diffbragg_example/galph_memory.md` — Prepended i=137 entry
3. `/home/ollie/Documents/diffbragg_example/input.md` — Overwritten with Phase A.1-A.2 Do Now for Ralph i=138

---

## Turn Summary

**Loop i=137 (Galph)**: Created Tier-0 architecture initiative ARCH-GRADIENT-FLOW-001 in response to DB-AT-010 gradcheck regression (5/5 tests FAILING with disconnected autograd graph, confirmed Ralph i=136 verification). Escalated per DB-AT-SUITE-CARE-001 Phase B.1 directive. Authored full initiative plan with Phases A/B/C (call graph trace, suspect audit, gradient probe, fix, enforcement test, closure). Updated fix_plan.md Tier 0, created cross-refs to DB-AT-SUITE-CARE-001, prepared input.md for Ralph i=138 (Phase A.1-A.2: call graph trace + suspect module grep audit). Scoped 4 suspect modules (forward.py, crystallography.py, loss.py, inputs.py). Estimated effort: 5-7 loops. Next: Ralph executes Phase A.1-A.2, produces call graph diagram + grep audit with SAFE/UNSAFE classification + top candidate hypothesis.

**Artifacts**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T210000Z/` — `implementation.md`, `planning_notes.md`, `summary.md`

**fix_plan.md**: Tier 0 updated with ARCH-GRADIENT-FLOW-001 (in_progress), DB-AT-SUITE-CARE-001 dependency added

**galph_memory.md**: Updated with i=137 focus (ARCH-GRADIENT-FLOW-001, planning, exploring)

**Portfolio Status**: Tier 0 has 1 unblocked initiative (ARCH-GRADIENT-FLOW-001); DB-AT-SUITE-CARE-001 (Tier 1) blocked pending gradient flow fix

---

**Completed by**: Galph (Loop i=137)
**Branch**: integration
**Commit**: Deferred (no code changes, planning only)
