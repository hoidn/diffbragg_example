# ARCH-GRADIENT-FLOW-001 Phase A Planning Notes

**Loop**: i=137 (Galph)
**Date**: 2025-12-07T210000Z
**Initiative**: ARCH-GRADIENT-FLOW-001 — Gradient Flow Restoration (DB-AT-010 Unblock)
**Action Type**: planning
**Decision Status**: exploring

---

## Context

### Trigger Event
DB-AT-SUITE-CARE-001 Phase B.1 verification (Loop i=136, Ralph) confirmed **Tier-0 blocker**:
- **Test Status**: DB-AT-010 gradcheck suite FAILING (5/5 tests, 0% pass rate)
- **Failure Signature**: `torch.autograd.gradcheck.GradcheckError: Numerical gradient for function expected to be zero`
- **Root Cause Pattern**: Disconnected autograd graph prevents analytical gradient computation
- **Evidence**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/db_at_010_status_verification.md`

### Gradient Flow Break Symptoms
1. **Loss computes successfully**: All tests produce similar loss values (~3.66e+09), proving forward simulation executes
2. **Numerical gradients exist**: PyTorch's finite-difference method detects non-zero sensitivity
3. **Analytical gradients missing**: `torch.autograd.backward()` cannot propagate gradients from loss to refined parameters
4. **Consistent across parameters**: All 5 tests fail identically (crystal cell_a/gamma, detector distance, beam wavelength, wrapper test)

### Per Implementation.md Phase B.1 Directive
DB-AT-SUITE-CARE-001 Phase B.1 task definition (lines 36-37):
> **B1 — Tier-0 escalation**: Coordinate DB-AT-010 Phase D unblocking (gradcheck regression fix). Ensure TorchCrystal bridge audit and `.item()` coercion patch land before advancing other plans.

This planning loop creates the Tier-0 architecture initiative to execute that directive.

---

## Objectives (This Loop)

1. **Create ARCH-GRADIENT-FLOW-001 initiative** under `plans/active/` with full implementation.md (Phases A/B/C)
2. **Seed Phase A tasks** from Ralph's i=136 evidence (call graph, suspect modules, gradient probe, hypothesis ranking)
3. **Define exit criteria** aligned with Gradient-Safe Profile conformance requirements
4. **Establish enforcement test pattern** following ARCH-IMPL-CONFORMANCE-001 precedent
5. **Update fix_plan.md Tier 0** with new initiative and cross-refs to DB-AT-SUITE-CARE-001
6. **Prepare input.md for Ralph** with Phase A.1-A.2 Do Now (call graph trace + suspect audit)

---

## Phase A Task Design

### A1 — Call Graph Trace
**Objective**: Map full execution path from test → forward → loss → backward to identify module boundaries.

**Approach**:
1. Start from `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_crystal_cell_a` (line ~230 per verification report)
2. Trace through:
   - Test fixture setup (refGeom load, config assembly)
   - `simulate_forward_torch` call (entry point)
   - Internal forwarding (TorchCrystal, Simulator, loss computation)
   - Backward pass (gradcheck invocation)
3. Document each module crossing with file:line references
4. Identify tensor flow points (where `requires_grad=True` tensors pass between functions)

**Output**: `call_graph_trace.md` with ≥5 call stack levels documented

**Validation**: Trace covers test → dbex/physics/forward.py → dbex/geometry/crystallography.py → loss → backward

---

### A2 — Suspect Module Audit
**Objective**: Search high-risk gradient break patterns in 4 key modules.

**High-Risk Patterns** (from Ralph's i=136 hypothesis + GRADIENT-001):
1. **`.item()` coercion**: Converts tensor to Python scalar, breaks autograd graph
2. **`.detach()` or `.data` access**: Explicitly removes gradient tracking
3. **`.numpy()` conversion**: Moves to NumPy (non-differentiable)
4. **In-place ops on leaf tensors**: `*=`, `+=`, `.copy_()` when `requires_grad=True`
5. **`.cpu()` without grad retention**: Device move that loses gradient

**Modules to Audit**:
1. `dbex/physics/forward.py::simulate_forward_torch` (primary entry point)
2. `dbex/geometry/crystallography.py::TorchCrystal` (cell parameter hydration)
3. `dbex/physics/loss.py::_compute_variance_weighted_loss` (denominator computation)
4. `dbex/refinement/inputs.py::prepare_refinement_inputs` (config assembly from dxtbx metadata)

**Grep Commands**:
```bash
grep -n '\.item()' dbex/physics/forward.py dbex/geometry/crystallography.py dbex/physics/loss.py dbex/refinement/inputs.py
grep -n '\.detach()' dbex/physics/forward.py dbex/geometry/crystallography.py dbex/physics/loss.py dbex/refinement/inputs.py
grep -n '\.numpy()' dbex/physics/forward.py dbex/geometry/crystallography.py dbex/physics/loss.py dbex/refinement/inputs.py
grep -n '\.\*=' dbex/physics/forward.py dbex/geometry/crystallography.py dbex/physics/loss.py dbex/refinement/inputs.py
grep -n '\.cpu()' dbex/physics/forward.py dbex/geometry/crystallography.py dbex/physics/loss.py dbex/refinement/inputs.py
```

**Output**: `suspect_audit.md` with file:line citations for each pattern match + context analysis

**Validation**: ≥4 modules audited, grep results documented with assessment (safe/unsafe for gradient flow)

---

### A3 — Minimal Gradient Probe
**Objective**: Isolate which module breaks gradient via minimal reproduction.

**Probe Design** (thin wrapper, <400 LOC per PROBE-FREEZE-001):
1. **Fixture loading**: Use canonical refGeom assets (validated per DB-AT-SUITE-CARE-001 Phase B.2)
2. **Parameter injection**: Create `crystal_overrides = {'cell_a': torch.tensor(27.3758, dtype=torch.float64, requires_grad=True)}`
3. **Forward call**: Invoke `simulate_forward_torch(...)` with overrides
4. **Loss computation**: Compute masked MSE per SCALE-001/002 contract
5. **Backward pass**: Call `loss.backward()`
6. **Gradient check**: Assert `crystal_overrides['cell_a'].grad is not None`

**Expected Outcomes**:
- **If grad is None**: Gradient flow breaks inside `simulate_forward_torch` or earlier (TorchCrystal bridge)
- **If grad is tensor (non-zero)**: Gradient flow intact; problem may be in test harness or gradcheck config
- **If backward() errors**: Explicit detachment or in-place op detected

**Guardrails**:
- Script must stay <400 LOC (thin wrapper rule)
- Must call production `simulate_forward_torch` (no re-implementation)
- Artifacts under `plans/active/ARCH-GRADIENT-FLOW-001/reports/<ts>/gradient_probe_results.md`

**Output**: `gradient_probe_results.md` with:
- Execution status (success/error)
- `crystal_overrides['cell_a'].grad` value (None vs tensor)
- Traceback (if backward() errors)
- Conclusion (which module breaks gradient)

**Validation**: Probe executes, grad status determined, conclusion documented

---

### A4 — Hypothesis Ranking
**Objective**: Synthesize A1-A3 evidence into ranked root cause hypotheses.

**Ranking Criteria**:
1. **Confidence**: Strength of evidence from grep matches + gradient probe
2. **Specificity**: Exact file:line location identified
3. **Impact**: Likelihood this fix resolves all 5 gradcheck failures

**Expected Hypotheses** (examples):
1. **Hypothesis H1** (confidence 0.8): `dbex/geometry/crystallography.py:LINE` — TorchCrystal.cell_a property getter calls `.item()` during parameter hydration
2. **Hypothesis H2** (confidence 0.6): `dbex/physics/loss.py:LINE` — Variance denominator uses `.item()` to convert mask sum to scalar
3. **Hypothesis H3** (confidence 0.4): `dbex/physics/forward.py:LINE` — Simulator config assembly detaches tensors

**Output**: `hypothesis_ranking.md` with ≥3 hypotheses, confidence scores, file:line citations

**Validation**: Top hypothesis has confidence ≥0.5, ≥3 hypotheses documented

---

## Exit Criteria Mapping

### Initiative Exit Criteria (from implementation.md)
1. **Gradient flow restored**: DB-AT-010 gradcheck tests pass (5/5)
2. **Root cause fixed**: Code patch preserves gradient graph
3. **Enforcement test added**: `tests/architecture/test_gradient_contracts.py`
4. **Documentation updated**: findings.md (GRADIENT-002), architecture.md (§13 Pitfalls), TEST_SUITE_INDEX.md
5. **Regression validation**: Full DB-AT-010 suite PASSES

### Phase A Deliverables Required for Phase B
- **A1 output** enables B1 fix location identification
- **A2 output** guides B1 patch strategy (which pattern to remove)
- **A3 output** validates B2 gradcheck verification scope
- **A4 output** prioritizes B1 implementation attempts (start with top hypothesis)

---

## Spec/Arch Alignment

### SPEC: docs/spec-db-conformance.md §Gradient-Safe Profile
- **Requirement**: DB-AT-010 gradcheck must pass with `eps=1e-6, atol=1e-5, rtol≈0.05`
- **Current Status**: NON-CONFORMING (0/5 tests PASS)
- **Phase A Contribution**: Identifies fix to restore conformance

### ARCH: docs/architecture.md §13 Common Pitfalls
- **Current State**: Lists device/dtype neutrality, square-pixel enforcement, ADU↔photon policy
- **Phase B.4 Addition**: "Gradient Flow Preservation" subsection documenting `.item()` / `.detach()` risks
- **Phase A Contribution**: Seeds content for new pitfall subsection

### FINDINGS: GRADIENT-001 (Gradient test patterns)
- **Contract**: Tests must inject differentiable parameters via `crystal_overrides` dict
- **Current Status**: Test harness uses correct pattern (verified per i=136 pytest log)
- **Phase A Contribution**: Confirms problem is NOT in test harness (production code issue)

### FINDINGS: RUNTIME-001 (Runtime execution guardrails)
- **Contract**: DB-AT-010 requires `NANOBRAGG_DISABLE_COMPILE=1`
- **Current Status**: Phase B.1 verification used canonical flags (confirmed)
- **Phase A Contribution**: No impact (runtime flags correct)

---

## Risks & Mitigations

### Risk 1: Probe Violates PROBE-FREEZE-001
**Symptom**: A3 gradient probe exceeds 400 LOC or re-implements production semantics
**Mitigation**: Strict thin wrapper enforcement (import production `simulate_forward_torch`, measure only)
**Contingency**: If probe grows large, skip A3 and rely on A1+A2 grep evidence for hypothesis ranking

### Risk 2: Multiple Gradient Breaks
**Symptom**: A3 probe finds grad=None, but A2 audit shows >5 suspect `.item()` calls across modules
**Mitigation**: Fix top-ranked hypothesis (H1) first, re-run gradcheck, iterate if needed
**Contingency**: Phase B.1 may require 2-3 loops if multiple fixes needed

### Risk 3: Root Cause in nanobrag_torch Upstream
**Symptom**: A1-A3 evidence points to `nanobrag_torch.Simulator` internals (outside dbex/)
**Mitigation**: Document as blocked_pending_environment, escalate to maintainer per problems.md pattern
**Contingency**: Alternative: spec_change to relax gradcheck tolerances or mark DB-AT-010 xfail

### Risk 4: Fix Breaks Production Logic
**Symptom**: B1 patch changes numerical output (e.g., replacing `.item()` changes loss computation)
**Mitigation**: B2 gradcheck verification + Stage A/B/C smoke regression tests must PASS
**Contingency**: If behavior changes, reclassify as bugfix (not architecture) and update exit criteria

---

## Pointers to Key Documents

### Evidence Base (DB-AT-SUITE-CARE-001 Phase B.1, i=136)
- **Verification report**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/db_at_010_status_verification.md`
- **Pytest log**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/pytest_db_at_010_verification.log`
- **Exit code**: 1 (test failures, not collection errors)
- **Runtime**: 130.69s (full-detector size, 5 tests)

### SPEC References
- **docs/spec-db-conformance.md** §Gradient-Safe Profile (DB-AT-010 acceptance criteria)
- **docs/spec-db-core.md** §Objective Function (variance-weighted loss definition)
- **docs/spec-db-runtime.md** §Gradient Hygiene (differentiability requirements)

### ARCH References
- **docs/architecture.md** §13 Common Pitfalls (to be extended Phase B.4)
- **docs/architecture/module_map.md** (physics/geometry module ownership)
- **docs/architecture/data_telemetry_flow.md** (forward → loss path)

### Testing Docs
- **docs/TESTING_GUIDE.md** §1.4 (DB-AT-010 selector, canonical flags)
- **docs/development/TEST_SUITE_INDEX.md** (DB-AT-010 status row, currently FAILING)
- **docs/development/testing_strategy.md** §4.1 (gradcheck tolerances)

### Findings
- **docs/findings.md::GRADIENT-001** (test patterns for crystal_overrides)
- **docs/findings.md::RUNTIME-001** (NANOBRAGG_DISABLE_COMPILE=1 requirement)
- **docs/findings.md::TESTING-003** (registry maintenance triggers)

---

## Expected Flow (Next Loop i=138)

### Ralph's Phase A.1-A.2 Execution
1. **Call graph trace** (A1):
   - Start from `tests/dbex/test_gradients.py:230` (gradcheck call site)
   - Trace import chain: test → forward.py → crystallography.py → loss.py
   - Document 5-10 function calls with file:line references
   - Output: `call_graph_trace.md`

2. **Suspect module audit** (A2):
   - Run 5 grep commands (`.item()`, `.detach()`, `.numpy()`, `*=`, `.cpu()`)
   - Review each match for gradient safety (context analysis)
   - Classify as safe (e.g., `.item()` on non-grad tensor) or unsafe (on requires_grad=True)
   - Output: `suspect_audit.md` with ≥10 grep matches analyzed

3. **Planning for A3** (gradient probe):
   - Draft probe script skeleton (fixture load, override injection, forward call, backward, grad check)
   - Estimate LOC (<200 expected, well under 400 cap)
   - Schedule A3 for loop i=139 (separate implementation loop)

4. **Summary**:
   - `summary.md` with A1-A2 completion status
   - Preliminary hypothesis (if A2 grep finds obvious `.item()` in TorchCrystal)
   - Next action: A3 gradient probe implementation (i=139)

### Galph's Review Criteria (i=139)
- ✅ **A1 complete**: call_graph_trace.md exists with ≥5 call stack levels
- ✅ **A2 complete**: suspect_audit.md covers 4 modules, ≥10 grep matches analyzed
- ✅ **Hypothesis seeded**: Top candidate identified (even if confidence < 0.5 yet)
- ➡️ **Next**: Approve A3 gradient probe Do Now (i=139) or skip to Phase B.1 if A2 evidence strong

---

## Success Criteria (This Loop)

- [x] **Implementation.md authored**: Full Phases A/B/C structure with exit criteria, tasks, validation rules
- [x] **Planning notes complete**: This document (context, objectives, Phase A design, risks, pointers)
- [ ] **fix_plan.md updated**: Add ARCH-GRADIENT-FLOW-001 to Tier 0 (deferred to end-of-loop hygiene)
- [ ] **galph_memory.md updated**: Prepend i=137 entry (deferred to end-of-loop hygiene)
- [ ] **input.md overwritten**: Phase A.1-A.2 Do Now for Ralph i=138 (deferred to end-of-loop hygiene)

---

**Planning complete**: 2025-12-07T210000Z
**Next loop (i=138)**: Ralph executes Phase A.1-A.2 (call graph trace + suspect audit)
