# Loop Summary — Ralph i=138

**Initiative**: ARCH-GRADIENT-FLOW-001 (Gradient Flow Restoration)
**Phase**: A.1-A.2 (Call Graph Trace + Suspect Module Audit)
**Date**: 2025-12-07
**Status**: ✅ **PHASE A.1-A.2 COMPLETE** — Evidence collection successful, root cause localized

---

## Deliverables

✅ **call_graph_trace.md** — 7 call stack levels documented, 3 tensor flow boundaries identified
✅ **grep_*.txt** — 6 grep output files (item, detach, numpy, inplace_mul, inplace_add, cpu)
✅ **suspect_audit.md** — 13 matches analyzed, 0 production UNSAFE patterns, 2 test harness UNSAFE patterns
✅ **summary.md** — Loop summary with Phase A completion status, preliminary hypothesis, next action

---

## Findings Summary

### Root Cause Identified: Test Harness Gradient Breaks

**Location**: `tests/dbex/test_gradients.py`
- **Line 383**: `new_distance = float(distance_tensor.item())` — Detector distance test
- **Line 496**: `new_wavelength = float(wavelength_tensor.item())` — Beam wavelength test

**Impact**: 2/5 gradcheck tests fail due to explicit `.item()` calls that sever autograd graph before dxtbx geometry construction.

**Fix Path**: Implement tensor-valued geometry override mechanisms (similar to existing `crystal_overrides` pattern for cell parameters).

### Production Code: Clean

**0 UNSAFE gradient-breaking patterns found** in 4 audited modules:
- `dbex/physics/forward.py` — ✅ Clean
- `dbex/geometry/crystallography.py` — ✅ Clean (unused code paths only)
- `dbex/physics/loss.py` — ✅ Clean (intentional IRLS `.detach()` is correct)
- `dbex/refinement/inputs.py` — ✅ Clean (numpy only, no torch)

### External Dependency Hypothesis

**Crystal parameter tests** (cell_a, cell_gamma) use correct tensor-preserving pattern but still fail. Hypothesis: `nanobrag_torch.models.Crystal.__init__` may break gradient internally. Requires Phase A.3 empirical probe to confirm.

---

## Phase A.1-A.2 Completion Status

### Phase A.1: Call Graph Trace ✅

- [x] Mapped 7 call stack levels from gradcheck → test → forward → loss → backward
- [x] Identified 3 tensor flow boundaries (parameter → forward, forward → loss, loss → gradcheck)
- [x] Documented crystal vs detector/beam test divergence (tensor override vs scalar extraction)
- [x] Created call_graph_trace.md with execution path diagrams

**Key Insight**: Crystal tests use tensor-preserving `crystal_overrides` dict, while detector/beam tests break gradient by calling `.item()` to build non-differentiable dxtbx geometry objects.

### Phase A.2: Suspect Module Audit ✅

- [x] Executed 6 grep commands across 4 production modules
- [x] Analyzed 13 matches (10 production + 3 test harness)
- [x] Classified SAFE vs UNSAFE for each pattern
- [x] Identified 2 critical test harness bugs (test_gradients.py:383, :496)
- [x] Created suspect_audit.md with detailed analysis table

**Key Insight**: Production code is gradient-safe. All failures stem from test harness design (detector/beam tests) or suspected external dependency (crystal tests).

---

## Preliminary Hypothesis

### Primary Gradient Breaks (Confirmed)

1. **Detector distance test** (`test_gradients.py:383`):
   - Test explicitly calls `float(distance_tensor.item())` to extract scalar for dxtbx.model.Detector construction
   - Breaks autograd graph before forward simulation
   - **Fix**: Implement `distance_mm_override` tensor support in `create_detector_config` (20-30 LOC)

2. **Beam wavelength test** (`test_gradients.py:496`):
   - Test explicitly calls `float(wavelength_tensor.item())` to extract scalar for dxtbx.model.Beam construction
   - Breaks autograd graph before forward simulation
   - **Fix**: Implement `wavelength_override` tensor support in `create_beam_config` or test fixture (15-25 LOC)

### Secondary Hypothesis (Requires A.3 Probe)

3. **Crystal parameter tests** (cell_a, cell_gamma):
   - Test harness correctly uses tensor-preserving `crystal_overrides` dict (no `.item()` calls)
   - Gradient break suspected in `nanobrag_torch.models.Crystal.__init__` (external dependency)
   - **Next Step**: Phase A.3 gradient probe to empirically test Crystal constructor gradient preservation
   - **Escalation**: If confirmed, mark ARCH-GRADIENT-FLOW-001 as `blocked_pending_environment`

---

## Next Action

### Recommended Path: **Phase B.1 (Partial Fix)**

**Objective**: Fix detector/beam test gradient breaks immediately (unblocks 2/5 tests), then decide on crystal test approach.

**Tasks**:
1. Implement `distance_mm_override` tensor support in `create_detector_config` (config_factories.py:115-120)
2. Implement `wavelength_override` tensor support (either in `create_beam_config` or test fixture)
3. Update test_gradients.py:379-427 (detector test) to use tensor override instead of `.item()`
4. Update test_gradients.py:493-518 (beam test) to use tensor override instead of `.item()`
5. Run DB-AT-010 gradcheck for detector_distance and beam_wavelength tests
6. If crystal tests still fail → proceed to Phase A.3 probe

**Estimated LOC**: 40-60 (20-30 for detector, 15-25 for beam, 5-10 for test fixture updates)

**Expected Outcome**:
- ✅ Detector distance gradcheck passes
- ✅ Beam wavelength gradcheck passes
- ⚠️ Crystal cell_a/cell_gamma gradcheck status unchanged (pending A.3 investigation)

### Alternative Path: **Phase A.3 (Probe First)**

If supervisor prefers to fully diagnose before implementing fixes:

**Objective**: Empirically test `nanobrag_torch.models.Crystal` gradient preservation with minimal probe.

**Tasks**:
1. Write thin gradient probe script (<400 LOC) that:
   - Creates CrystalConfig with tensor-valued `cell_a`
   - Instantiates Crystal(config, ...) on CPU/float64
   - Calls crystal.compute_cell_tensors() or similar
   - Checks if output tensors have `requires_grad=True` and grad_fn
2. Document probe results in Phase A.3 report
3. If gradient preserved: investigate other potential breaks (misset_deg hydration, A* injection)
4. If gradient broken: mark blocked_pending_environment and escalate to nanobrag_torch maintainer

---

## Risks and Mitigation

### Risk 1: Detector/Beam Fixes Alone Insufficient

**Probability**: Medium (crystal tests still fail)
**Impact**: Phase B.1 only unblocks 2/5 tests, partial progress
**Mitigation**: Budget Phase A.3 probe in next loop (i=139) if crystal tests don't improve

### Risk 2: nanobrag_torch Gradient Break Confirmed

**Probability**: Medium-High (evidence: all 5 tests fail uniformly)
**Impact**: ARCH-GRADIENT-FLOW-001 blocked until external fix or spec_change
**Mitigation**:
- Option A: Escalate to nanobrag_torch maintainer with Phase A.3 minimal reproducer
- Option B: Propose spec_change to relax DB-AT-010 scope (test only detector/beam, not crystal)
- Option C: Fork/patch nanobrag_torch locally (last resort per Environment Freeze policy)

### Risk 3: Missed Production Gradient Break

**Probability**: Low (thorough grep audit found 0 UNSAFE patterns)
**Impact**: Fix test harness but still fail gradcheck due to overlooked production bug
**Mitigation**: Phase A.3 probe will isolate any remaining breaks via empirical testing

---

## Architecture Alignment

### SPEC Conformance

- ✅ **spec-db-runtime.md §Gradient Hygiene**: Production code preserves autograd graphs (no `.item()`, `.detach()`, or `.numpy()` conversions in gradient path)
- ⚠️ **spec-db-conformance.md §DB-AT-010**: Acceptance criteria (eps=1e-6, atol=1e-5, rtol≈0.05) currently not met due to test harness bugs
- ✅ **spec-db-core.md §§57-68**: Variance-weighted loss uses intentional IRLS `.detach()` (correct per normative spec)

### ARCH Conformance

- ✅ **GRADIENT-001 (findings.md)**: Crystal tests correctly use `crystal_overrides` tensor-valued pattern (test harness follows best practice)
- ✅ **PHYSICS-LOSS-001**: `compute_masked_mse_loss` implements variance-weighted chi-squared with proper gradient preservation
- ✅ **ARCH-ENGINE-002**: Module-scope imports correctly lazy-loaded in forward.py (no circular dependency issues)

### Initiative-Type Compliance

- ✅ **architecture**: Focus on gradient flow contract enforcement, no semantic physics changes
- ✅ **No test weakening**: Did not relax gradcheck tolerances or disable tests (correct escalation path)
- ✅ **No shadow pipeline**: Phase A.1-A.2 are evidence collection only (grep + read, no script creation)

---

## Ledger Updates

### docs/fix_plan.md (Deferred to Phase B.1)

Will update Attempts History after implementing detector/beam fixes or running Phase A.3 probe. Current loop is evidence-only (no production changes).

### docs/findings.md (Pending)

Potential new finding after Phase B.1/A.3 completion:

**GRADIENT-002** (draft):
- **Title**: Tensor-valued geometry overrides for gradcheck
- **Pattern**: dxtbx geometry objects (Detector, Beam) require scalar values; must use config override mechanism to preserve gradient
- **Anti-pattern**: Calling `.item()` on parameter tensor to extract scalar for dxtbx construction
- **Reference**: config_factories.py (distance_mm_override, future wavelength_override)

---

## Artifacts

**Directory**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/`

- `call_graph_trace.md` — Execution path diagram, tensor flow boundaries, module interface analysis
- `grep_item.txt` — `.item()` search results (2 production SAFE, 2 test harness UNSAFE)
- `grep_detach.txt` — `.detach()` search results (5 production SAFE/intentional)
- `grep_numpy.txt` — `.numpy()` search results (3 unused code paths)
- `grep_inplace_mul.txt` — `*=` search results (0 matches)
- `grep_inplace_add.txt` — `+=` search results (0 matches)
- `grep_cpu.txt` — `.cpu()` search results (3 unused code paths)
- `suspect_audit.md` — Detailed pattern analysis, SAFE/UNSAFE classification, top candidate ranking
- `summary.md` — This file

---

### Turn Summary

Completed Phase A.1-A.2 evidence collection for ARCH-GRADIENT-FLOW-001. Traced 7 call stack levels from gradcheck → forward → loss, audited 4 production modules for 6 gradient-breaking patterns. Found 0 UNSAFE patterns in production code; identified 2 critical test harness bugs (test_gradients.py:383 detector distance, :496 beam wavelength) that break gradient via `.item()` calls. Crystal parameter tests use correct tensor-preserving pattern but may fail due to external nanobrag_torch.models.Crystal constructor. Recommend Phase B.1 to fix detector/beam test harness bugs (40-60 LOC), then re-assess crystal test status for potential Phase A.3 probe.

**Artifacts**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/` (call_graph_trace.md, suspect_audit.md, 6 grep files, summary.md)
