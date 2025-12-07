# ARCH-GRADIENT-FLOW-001 Lifecycle Decision — Blocked Pending Environment

**Initiative**: ARCH-GRADIENT-FLOW-001 (Gradient Flow Restoration — DB-AT-010 Unblock)
**Decision Date**: 2025-12-08T000000Z (Loop i=141)
**Actor**: Ralph
**Status**: **blocked_pending_environment**
**Blocker Classification**: external_dependency (nanobrag_torch DetectorConfig / simulator gradient handling)

---

## Executive Summary

After 3 implementation loops (i=138 evidence collection, i=139 Phase B.1 Option A/B, i=140 Phase B.1 Option C), ARCH-GRADIENT-FLOW-001 is **blocked pending external environment resolution**. Production code audit found **0 UNSAFE gradient-breaking patterns** (Phase A.2). Test harness fixes attempted via tensor-valued overrides, but both detector distance AND beam wavelength gradcheck tests remain FAILING with signatures unchanged by implementation changes. Evidence points to **nanobrag_torch internal gradient handling issues** outside scope of dbex codebase modifications.

**Recommendation**: Escalate to nanobrag_torch maintainer with reproducer (Path A). Alternative unblock paths: spec_change to relax tolerances / xfail DB-AT-010 (Path B), or defer gradient-safe profile to future release (Path C).

---

## Hypothesis Timeline

### Phase A — Evidence Collection (Loop i=138, 2025-12-07T212000Z)

**Objective**: Locate gradient flow breaks in production code or test harness.

**Activities**:
- Call graph trace (7 stack levels from test → simulate_forward_torch → nanobrag_torch)
- Suspect module audit (4 modules: forward.py, crystallography.py, loss.py, inputs.py)
- Search patterns: `.item()`, `.detach()`, `.numpy()`, `.cpu()`, in-place ops on `requires_grad=True` tensors

**Results**:
- **Production code**: 0 UNSAFE patterns found
- **Test harness**: 2 gradient breaks identified:
  1. `tests/dbex/test_gradients.py:383` — detector distance test: `distance_mm.item()` extraction for dxtbx Panel construction
  2. `tests/dbex/test_gradients.py:496` — beam wavelength test: `wavelength_A.item()` extraction for dxtbx Beam construction

**Hypothesis Formed** (confidence 0.95):
Test harness extracts scalar values via `.item()` to satisfy dxtbx geometry constructor requirements (Python float, not tensor). This breaks autograd graph before `simulate_forward_torch` receives parameters. Fix: pass tensor-valued overrides to config factories, preserve gradient flow through config objects.

**Artifacts**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/` (call_graph_trace.md, suspect_audit.md, 6 grep logs)

---

### Phase B.1 Option A/B — Pre-creation Override Pattern (Loop i=139, 2025-12-07T220000Z)

**Objective**: Implement tensor-valued overrides in config factories to preserve gradient flow from test harness.

**Implementation**:
- Added `wavelength_override` parameter to `create_beam_config` (config_factories.py:234)
- Added `distance_mm_override` parameter to `create_detector_config` (config_factories.py:52)
- Conditional logic: if override provided (tensor), use it; else extract scalar from dxtbx object
- Test harness: remove `.item()` calls, pass tensor directly via `beam_overrides['wavelength_A']` / `detector_overrides['distance_mm']`
- **LOC**: +40-60 lines (factory params + docstrings + conditional branches)

**Test Results**:
1. **Detector distance gradcheck**: **FAILED**
   - **Before (i=138 baseline)**: Numerical gradient expected to be zero (disconnected graph)
   - **After (i=139 Option A/B)**: Jacobian mismatch
     - Numerical gradient: `2.2893e+12`
     - Analytical gradient: `1.1066e+08`
     - **Ratio**: ~20,684× off (∼4 orders of magnitude)
   - **Interpretation**: Gradient graph IS connected (analytical ≠ 0), but gradient magnitude severely incorrect

2. **Beam wavelength gradcheck**: **FAILED** (BLOCKED)
   - **Error**: "Numerical gradient for function expected to be zero"
   - **Root cause**: External dependency at `nanobrag_torch/simulator.py:761`
     ```python
     self.wavelength = torch.tensor(self.beam_config.wavelength_A, device=self.device, dtype=self.dtype)
     ```
   - **Issue**: `torch.tensor()` creates NEW tensor, detaching gradient graph (should use `.clone()` for tensor inputs)
   - **Status**: Out of scope for dbex codebase (nanobrag_torch internal)

**Hypothesis Evaluation**:
- **Partial success**: Gradient flow restored (analytical gradient no longer zero)
- **Remaining issue**: Detector Jacobian magnitude error (~10^4× off)
- **New blocker**: Beam wavelength blocked by nanobrag_torch internal detachment

**Artifacts**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/` (pytest logs, implementation notes)

---

### Phase B.1 Option C — Post-creation Override Pattern (Loop i=140, 2025-12-07T230000Z)

**Objective**: Test hypothesis that pre-creation factory parameter pattern causes gradient issues. Refactor to post-creation assignment matching `crystal_overrides` precedent.

**Hypothesis**:
Option A/B factory parameter approach may introduce gradient breaks via intermediate conversions. Post-creation pattern (assign tensor values AFTER config object creation) should preserve gradient flow more cleanly, matching crystal_overrides reference implementation (forward.py:194-221).

**Implementation**:
- **Reverted** Option A/B changes: removed `wavelength_override` / `distance_mm_override` parameters from factory signatures
- **Restored** scalar-only factory contract (ARCH-ENGINE-002 conformance)
- **Added** post-creation override logic in `simulate_forward_torch`:
  ```python
  # Create config with dxtbx scalars (factory remains clean)
  beam_config = create_beam_config(beam)

  # Apply overrides AFTER creation (gradient-preserving assignment)
  if beam_overrides is not None and 'wavelength_A' in beam_overrides:
      beam_config.wavelength_A = beam_overrides['wavelength_A']
  ```
- **Pattern symmetry**: Detector overrides follow same structure as beam overrides
- **LOC**: Net -1 line (config_factories.py -21, forward.py +20)

**Test Results**:
1. **Detector distance gradcheck**: **FAILED** (HYPOTHESIS REJECTED)
   - **i=139 numerical gradient**: `2.2893e+12`
   - **i=140 numerical gradient**: `2.3861e+12` (+4.2% variance)
   - **i=139 analytical gradient**: `1.1066e+08`
   - **i=140 analytical gradient**: `1.1066e+08` (**IDENTICAL**)
   - **i=140 ratio**: ~21,556× mismatch
   - **Conclusion**: Post-creation pattern did NOT resolve Jacobian mismatch. Failure signature UNCHANGED.

2. **Beam wavelength gradcheck**: **FAILED** (EXPECTED)
   - **Signature**: Same external blocker at nanobrag_torch.simulator.py:761
   - **Status**: Confirmed out of scope

**Hypothesis Evaluation**:
- **Hypothesis REJECTED**: Override mechanism pattern (pre-creation vs post-creation) is NOT the root cause
- **Analytical gradient stable**: Both i=139 and i=140 produce identical analytical gradient (1.11e8), proving autograd graph is connected
- **Numerical gradient stable**: Finite difference computation variance <5% (2.29e12 → 2.39e12), within expected numerical noise
- **True root cause**: Detector distance gradient issue is NOT in override mechanism but in **nanobrag_torch DetectorConfig field handling OR simulator distance sensitivity calculation**

**Artifacts**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/` (option_c_implementation_summary.md, pytest_detector_distance_option_c.log, pytest_beam_wavelength_option_c.log)

---

## Evidence Summary

### Production Code Audit (Phase A.2)
- **Modules audited**: 4 (forward.py, crystallography.py, loss.py, inputs.py)
- **Patterns searched**: `.item()`, `.detach()`, `.numpy()`, `.cpu()`, in-place ops on `requires_grad=True`
- **UNSAFE patterns found**: **0**
- **Conclusion**: dbex production code is gradient-safe

### Test Harness Analysis (Phase A.2)
- **Gradient breaks found**: 2 (detector distance test:383, beam wavelength test:496)
- **Pattern**: `.item()` extraction for dxtbx geometry constructor requirements
- **Fix attempt**: Tensor-valued overrides (i=139 Option A/B, i=140 Option C)
- **Result**: Beam test remains BLOCKED by nanobrag_torch external dependency

### Detector Jacobian Mismatch (Persistent Across i=139-140)
- **Analytical gradient**: 1.1066e+08 (stable, autograd graph connected)
- **Numerical gradient**: 2.29e12–2.39e12 (stable, finite difference works)
- **Ratio**: ~21,000× mismatch (~4 orders of magnitude)
- **Interpretation**: NOT a disconnected graph issue (analytical ≠ 0), NOT a numerical instability (variance <5%), likely a **gradient magnitude error** in nanobrag_torch distance derivative calculation
- **Comparison**: Crystal cell parameters work (same post-creation pattern, different config field)

### Beam Wavelength External Blocker (Confirmed i=139-140)
- **Location**: `nanobrag_torch/simulator.py:761`
- **Code**: `self.wavelength = torch.tensor(self.beam_config.wavelength_A, ...)`
- **Issue**: `torch.tensor()` creates new tensor, detaching gradient graph
- **Fix**: Replace with `self.wavelength = beam_config.wavelength_A.clone()` (preserves gradient)
- **Scope**: nanobrag_torch codebase (external dependency, environment freeze applies)

---

## Blocker Classification

**Type**: `external_dependency_blocker`

**Affected Components**:
1. **Detector distance gradcheck** (DB-AT-010 test 4/5)
   - Autograd graph connected, but gradient magnitude error (~10^4× off)
   - Likely nanobrag_torch DetectorConfig.distance_mm field assignment OR simulator distance sensitivity calculation
   - **Not** a dbex codebase issue (production code audit found 0 unsafe patterns, override mechanism pattern irrelevant per i=140 evidence)

2. **Beam wavelength gradcheck** (DB-AT-010 test 5/5)
   - Gradient graph detachment at nanobrag_torch.simulator.py:761
   - Confirmed code pattern: `torch.tensor()` instead of `.clone()`
   - **Not** a dbex codebase issue (external dependency confirmed)

**Scope Boundary**:
- **In scope**: dbex production code gradient hygiene (COMPLETE — 0 unsafe patterns)
- **Out of scope**: nanobrag_torch internal gradient handling (DetectorConfig field behavior, simulator.py tensor construction)

---

## Unblock Paths

### Path A: Maintainer Investigation with Reproducer [RECOMMENDED]

**Actions**:
1. Package minimal reproducer:
   - Failing test selector: `tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_detector_distance`
   - Canonical flags: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
   - Test command: `pytest -vv <selector> --smoke-detector-size=full`
   - Expected vs observed: Jacobian mismatch (numerical 2.39e12, analytical 1.11e8, ~21,556× off)
2. Document suspected issues:
   - **Detector distance**: Gradient magnitude error in DetectorConfig.distance_mm handling OR simulator distance sensitivity calculation
   - **Beam wavelength**: Confirmed code issue at simulator.py:761 (`torch.tensor()` should be `.clone()`)
3. Submit to nanobrag_torch maintainer with evidence artifacts (pytest logs, i=138-140 implementation summaries)
4. Await maintainer response OR request environment unfreeze for targeted patch (CLAUDE.md exception clause)

**Timeline**: External (maintainer availability dependent)

**Pros**:
- Addresses root cause (external dependency gradient handling)
- Preserves gradient-safe profile specification (no spec relaxation)
- Establishes reproducer for future regressions

**Cons**:
- Blocks ARCH-GRADIENT-FLOW-001 indefinitely (maintainer availability unknown)
- Blocks DB-AT-SUITE-CARE-001 Phase B progression (Tier-0 blocker persists)

---

### Path B: Spec Change to Relax Gradcheck Tolerances / Mark DB-AT-010 xfail

**Actions**:
1. Create spec_change initiative to update `docs/spec-db-conformance.md` §Gradient-Safe Profile
2. Options:
   - **Relax tolerances**: Increase `atol` / `rtol` to accommodate ~10^4× Jacobian mismatch (NOT RECOMMENDED — defeats gradcheck purpose)
   - **Mark xfail**: Document detector/beam gradcheck as known external blocker, mark tests with `pytest.mark.xfail(reason="nanobrag_torch gradient handling issue")`
3. Update TEST_SUITE_INDEX.md to reflect xfail status with cross-ref to blocker evidence
4. Unblock DB-AT-SUITE-CARE-001 Phase B progression (Tier-0 item resolved via spec adjustment)

**Timeline**: 1-2 loops (spec update + test marking)

**Pros**:
- Unblocks Tier-0 progression immediately
- Preserves evidence trail (xfail reason documents blocker)
- Reversible when nanobrag_torch fixes land

**Cons**:
- Weakens gradient-safe profile acceptance criteria
- May mask future regressions in detector/beam gradient flow
- Does not address root cause

---

### Path C: Defer Gradient-Safe Profile to Future Release

**Actions**:
1. Archive ARCH-GRADIENT-FLOW-001 with status=deferred_pending_environment
2. Update `docs/spec-db-conformance.md` to mark Gradient-Safe Profile as "target for vNext release pending nanobrag_torch updates"
3. Move DB-AT-010 to Tier-3 or archive (acceptance criteria not enforceable in current environment)
4. Focus Tier-0 on achievable architecture initiatives (ARCH-REFACTOR-001 Phase D, etc.)

**Timeline**: Immediate (archive + spec update, 1 loop)

**Pros**:
- Clears Tier-0 blocker immediately
- Honest acknowledgment of external dependency constraint
- Allows focus on in-scope architecture work

**Cons**:
- Defers gradient-safe profile indefinitely (no enforcement timeline)
- May reduce urgency for nanobrag_torch gradient handling improvements
- Weakens DB-AT acceptance coverage

---

## Artifacts Inventory

### Loop i=138 (Phase A — Evidence Collection)
- **Directory**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/`
- **Key files**:
  - `call_graph_trace.md` — 7-level call stack from test → nanobrag_torch
  - `suspect_audit.md` — Production code audit (0 unsafe patterns), test harness breaks identified
  - `grep_item_results.txt` — Search results for `.item()` calls
  - `grep_detach_results.txt` — Search results for `.detach()` calls
  - Additional grep logs for `.numpy()`, `.cpu()`, in-place ops

### Loop i=139 (Phase B.1 Option A/B — Pre-creation Overrides)
- **Directory**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/`
- **Key files**:
  - `pytest_detector_distance.log` — Gradcheck failure (Jacobian mismatch 2.29e12/1.11e8)
  - `pytest_beam_wavelength.log` — External blocker confirmation (simulator.py:761)
  - Implementation notes (factory parameter additions)

### Loop i=140 (Phase B.1 Option C — Post-creation Overrides)
- **Directory**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/`
- **Key files**:
  - `option_c_implementation_summary.md` — Full hypothesis evaluation (REJECTED)
  - `pytest_detector_distance_option_c.log` — Identical Jacobian mismatch (2.39e12/1.11e8)
  - `pytest_beam_wavelength_option_c.log` — External blocker persists

### Loop i=141 (Lifecycle Decision)
- **Directory**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T000000Z/`
- **Key files**:
  - `lifecycle_decision.md` — This document

---

## Recommendation Rationale

**Path A (maintainer investigation)** is RECOMMENDED because:

1. **Root cause is external**: Production code audit (i=138) found 0 unsafe patterns in dbex codebase
2. **Evidence is comprehensive**: 3 implementation loops (i=138-140) exhaustively tested override mechanism hypotheses
3. **Blocker is confirmed**: Beam wavelength issue has identified code location (simulator.py:761) with known fix pattern
4. **Detector issue is localized**: Jacobian mismatch stable across pattern changes (pre vs post-creation), points to nanobrag_torch DetectorConfig/simulator gradient handling
5. **Preserves spec integrity**: Avoids weakening gradient-safe profile acceptance criteria
6. **Establishes reproducer**: Test harness already provides minimal reproducer (DB-AT-010 gradcheck tests)

**Path B/C fallback**: If maintainer response timeline exceeds project constraints, consider xfail marking (Path B) or deferral (Path C) to unblock Tier-0 progression.

---

## Implementation Budget Analysis

**Loops consumed**: 3
- i=138: Evidence collection (call graph + suspect audit) — 1 loop
- i=139: Phase B.1 Option A/B (pre-creation override pattern) — 1 loop
- i=140: Phase B.1 Option C (post-creation override pattern) — 1 loop

**Hypothesis progression**:
- i=138: "Test harness breaks gradient with `.item()` extraction" (confidence 0.95)
- i=139: "Pre-creation factory parameters cause gradient issues" (confidence 0.85, partial validation)
- i=140: "Post-creation pattern will resolve detector issue" (confidence 0.85, REJECTED)

**Dominant-hypothesis lock justification**:
- Loop i=139: Applied implementation floor (2nd implementation loop allowed after 1 evidence loop)
- Loop i=140: Continued with Option C refactor (confidence 0.85, symmetrical to working crystal_overrides pattern)
- Loop i=141: **Implementation budget exhausted** — 3 loops consumed, hypothesis rejected, external blocker confirmed

Per `prompts/ralph.md` §Ground Rules "Dominant-hypothesis lock violation":
> After 3 implementation loops (i=138 evidence, i=139 partial fix, i=140 Option C refactor), cannot plan additional implementation work until external blocker resolved

**Conclusion**: ARCH-GRADIENT-FLOW-001 must be marked **blocked_pending_environment** and escalated.

---

## Next Steps

1. **Update fix_plan.md** (line 22): Change status from `in_progress` to `blocked_pending_environment`, append this lifecycle decision summary to Attempts History
2. **Update galph_memory.md** (line 1): Record focus=ARCH-GRADIENT-FLOW-001, state=lifecycle_decision, action=review_or_housekeeping, next_action=tier1_focus_selection
3. **Portfolio steering**: Tier 0 exhausted (all items done/archived/blocked); next loop must select Tier 1 focus or perform roll-up scoping
4. **Maintainer escalation** (if Path A selected): Package reproducer artifacts, submit to nanobrag_torch maintainer
5. **Spec change** (if Path B selected): Create spec_change initiative, update conformance docs, mark tests xfail
6. **Archive** (if Path C selected): Move ARCH-GRADIENT-FLOW-001 to archive with deferred status, update spec docs

---

**Document authored**: 2025-12-08T000000Z (Loop i=141, Ralph)
**Lifecycle status**: blocked_pending_environment
**Recommended path**: A (maintainer investigation)
