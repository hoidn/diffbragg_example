# Planning Notes — Loop i=140 (Galph)
**Initiative**: ARCH-GRADIENT-FLOW-001 (Gradient Flow Restoration)
**Phase**: B.1 Continuation (Post-Creation Override Refactor)
**Date**: 2025-12-07T230000Z
**Lifecycle Decision**: Implementation continuation (Option C from phase_b1_analysis.md)

---

## Context

Ralph's i=139 Phase B.1 implementation delivered mixed results:
- **Detector distance test**: Gradient flow RESTORED (analytical grad 1.14e8 non-zero) but Jacobian mismatch (~4590× magnitude error)
- **Beam wavelength test**: BLOCKED by external nanobrag_torch.simulator.py:761 gradient break (`torch.tensor()` detaches autograd graph)

### Root Cause Hypothesis (Updated)

**Detector Jacobian mismatch**:
- Current implementation: pre-creation override (pass tensor to factory before config creation)
- Factory may perform type conversions/validations that strip gradients or introduce magnitude errors
- Evidence: Crystal overrides use **post-creation pattern** (assign tensor AFTER config creation) and work correctly
- Confidence: 0.85 (pattern alignment strong, but magnitude error could be unit conversion)

**Beam wavelength blocker**:
- External dependency: nanobrag_torch.simulator.py:761 uses `torch.tensor(self.beam_config.wavelength_A, ...)` which detaches autograd
- Fix location: Outside dbex scope (requires nanobrag_torch patch)
- Confidence: 1.0 (pytest warning confirms, Ralph identified exact line)

---

## Phase B.1 Continuation: Option C Refactor

### Objective
Refactor detector/beam overrides to **post-creation pattern** matching crystal_overrides:
1. Create config object with scalars from dxtbx (existing behavior)
2. Override config fields AFTER creation with tensor values (new behavior)
3. Validate detector test gradient flow + Jacobian parity
4. Document beam wavelength external blocker for separate escalation

### Rationale

**Why post-creation pattern?**
- Crystal overrides work correctly using this pattern (evidence: DB-AT-010 crystal tests would fail otherwise)
- Avoids factory-level type conversions that may strip gradients
- Simplifies implementation: no factory signature changes needed
- Maintains separation of concerns: factory creates configs, caller overrides fields

**Why continue (not mark blocked)?**
- Detector test shows gradient flow restored (partial progress)
- Ralph's analysis identifies concrete next step (Option C) with 1-loop effort
- Beam blocker is separate issue (external dependency), doesn't block detector fix
- Implementation floor + dominant-hypothesis lock require completing detector path before escalating

**Risk mitigation**:
- If detector still fails post-refactor → escalate BOTH issues to blocked_pending_environment
- If detector passes → document beam blocker separately, partial Phase B.1 success (1/2 tests)

---

## Implementation Scope (Option C)

### Production Changes (30-50 LOC)

**dbex/physics/forward.py** (20-30 LOC):
1. **Revert factory parameter approach** (lines 184-188 beam overrides, 231-241 detector overrides):
   - Remove `distance_mm_override` parameter from `create_detector_config` calls
   - Remove `wavelength_override` parameter from `create_beam_config` calls
   - Create configs with dxtbx scalars (restore pre-i=139 behavior)

2. **Add post-creation override logic** (new lines after config creation):
   ```python
   # After detector_config = create_detector_config(...)
   if detector_overrides and 'distance_mm' in detector_overrides:
       for panel_idx in range(len(detector_configs)):
           detector_configs[panel_idx].distance_mm = detector_overrides['distance_mm']

   # After beam_config = create_beam_config(...)
   if beam_overrides and 'wavelength_A' in beam_overrides:
       beam_config.wavelength_A = beam_overrides['wavelength_A']
   ```

**dbex/refinement/config_factories.py** (10-15 LOC):
- **Revert wavelength_override parameter** from `create_beam_config` (lines 234, 249-250, 257-260)
- Restore function signature to pre-i=139 state
- (distance_mm_override revert deferred — may not have been added in i=139)

### Test Harness Changes (MINIMAL)

**tests/dbex/test_gradients.py** (0-5 LOC):
- Test already updated in i=139 to use `detector_overrides`/`beam_overrides` dicts
- No changes needed IF post-creation override pattern works
- Possible minor adjustment: ensure override dict keys match config field names exactly

---

## Validation Strategy

### Primary Test (detector distance)
**Selector**: `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_detector_distance`
**Expected**: PASS (Jacobian mismatch resolved, gradcheck eps=1e-6 / atol=1e-5 / rtol=0.05 satisfied)
**Command**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  KMP_DUPLICATE_LIB_OK=TRUE \
  NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -vv tests/dbex/test_gradients.py::test_db_at_010_gradcheck_detector_distance \
  --smoke-detector-size=full \
  | tee plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/pytest_detector_distance_option_c.log
```

### Secondary Test (beam wavelength)
**Selector**: `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_beam_wavelength`
**Expected**: FAIL (external blocker persists, no change expected)
**Purpose**: Document that beam blocker is NOT resolved by post-creation pattern
**Command**: Same as detector test, replace selector

### Regression Check (deferred)
**Selector**: `pytest -v tests -k DB_AT_010 --smoke-detector-size=full`
**Condition**: Run ONLY if detector test PASSES
**Purpose**: Verify crystal tests remain unaffected by refactor

---

## Success Criteria (Phase B.1 Continuation)

**Minimum viable (1/2 tests passing)**:
- ✅ Detector distance gradcheck PASSES
- ⚠️ Beam wavelength gradcheck FAILS (documented external blocker)
- ✅ Crystal tests (3/5 total) remain PASSING or FAILING with same signature as pre-i=139
- **Next loop**: Phase B.1 closure (document detector fix, escalate beam blocker separately)

**Stretch goal (2/2 tests passing — unlikely)**:
- ✅ Detector distance gradcheck PASSES
- ✅ Beam wavelength gradcheck PASSES (external blocker self-resolves)
- **Next loop**: Phase B.2 (enforcement test + docs)

**Failure scenario (0/2 tests passing)**:
- ❌ Detector distance gradcheck still FAILS with Jacobian mismatch
- **Next loop**: Escalate ARCH-GRADIENT-FLOW-001 to blocked_pending_environment, create reproducer for nanobrag_torch maintainer

---

## ARCH/SPEC Alignment

### ARCH Contracts

**GRADIENT-001** (Gradient test patterns):
- Post-creation override pattern matches crystal_overrides precedent
- Preserves separation: config factories create objects, caller overrides fields
- Adherence: Option C refactor implements GRADIENT-001 pattern symmetry

**ARCH-ENGINE-002** (Config factory ownership):
- Factories no longer receive tensor parameters (revert i=139 changes)
- Override logic moves to `simulate_forward_torch` (caller scope)
- Adherence: Clean factory responsibilities, no test-specific backdoors

**RUNTIME-001** (Gradient execution):
- Canonical flags required: `NANOBRAGG_DISABLE_COMPILE=1` for gradcheck
- Adherence: All pytest commands in planning notes include compile guard

### SPEC References

**docs/spec-db-conformance.md** §DB-AT-010:
- Gradcheck tolerance: eps=1e-6, atol=1e-5, rtol=0.05
- Partial satisfaction expected: 1/2 tests (detector), 3/5 total if crystal unaffected
- Full satisfaction deferred: beam blocker requires nanobrag_torch patch

**docs/spec-db-runtime.md** §Gradient Hygiene:
- Production code must preserve gradient graph
- Adherence: Option C refactor maintains dbex gradient safety (no `.item()` / `.detach()` added)
- External blocker: nanobrag_torch.simulator.py:761 violates spec (out of dbex scope)

---

## Beam Wavelength Blocker Documentation

### Classification
**Status**: blocked_pending_environment
**Scope**: External dependency (nanobrag_torch submodule, NOT in dbex codebase)
**Fix location**: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:761`

### Recommended Patch (for nanobrag_torch maintainer)
```python
# Current (BREAKS gradients):
self.wavelength = torch.tensor(self.beam_config.wavelength_A, device=self.device, dtype=self.dtype)

# Recommended fix:
if isinstance(self.beam_config.wavelength_A, torch.Tensor):
    self.wavelength = self.beam_config.wavelength_A.to(device=self.device, dtype=self.dtype)
else:
    self.wavelength = torch.tensor(self.beam_config.wavelength_A, device=self.device, dtype=self.dtype)
```

### Reproducer (minimal)
```python
import torch
from nanobrag_torch import Simulator, BeamConfig

wavelength = torch.tensor(1.0, requires_grad=True)
beam_config = BeamConfig(wavelength_A=wavelength, ...)
simulator = Simulator(beam_config=beam_config, ...)  # Gradient detaches here
# Expected: simulator.wavelength.requires_grad == True
# Actual: simulator.wavelength.requires_grad == False
```

### Next Steps (beam blocker)
1. If detector test passes this loop → document beam blocker in findings.md (GRADIENT-003)
2. Create thin wrapper reproducer script under `plans/active/ARCH-GRADIENT-FLOW-001/bin/`
3. Escalate to nanobrag_torch maintainer OR mark DB-AT-010 beam test as xfail with blocker note
4. Continue ARCH-GRADIENT-FLOW-001 Phase B completion with 1/2 test coverage (detector only)

---

## Lifecycle Tracking

**Dwell**: 2 consecutive loops on ARCH-GRADIENT-FLOW-001 (i=139 implementation, i=140 continuation)
**Budget**: Phase B allowed 2-3 loops; this is loop 2/3
**DecisionStatus**: patch_ready → implementation_in_progress → will transition to:
  - `localized` if detector PASSES (beam external blocker understood)
  - `blocked` if detector FAILS (escalate both issues)

**Non-Negotiables Applied**:
- ✅ Implementation floor: continuing same focus (2nd implementation loop allowed)
- ✅ Dwell enforcement: 0 evidence/planning loops since last implementation (i=139)
- ✅ Cliff avoidance: i=139 restored gradient flow (not a cliff), Jacobian error addressable
- ✅ Evidence→Action: Ralph's analysis provides concrete next step (Option C refactor)

---

## Risks

**Risk 1: Post-creation override fails (magnitude error persists)**
- **Probability**: Low-Medium (0.25)
- **Impact**: Detector test still fails, must escalate to blocked_pending_environment
- **Mitigation**: If failed, create minimal reproducer for nanobrag_torch maintainer (both detector + beam)

**Risk 2: Config field assignment type conversion**
- **Probability**: Low (0.15)
- **Impact**: Post-creation assignment coerces tensor to scalar (same as factory)
- **Mitigation**: Inspect DetectorConfig/BeamConfig dataclass definitions; validate field types accept tensors

**Risk 3: Crystal tests regress**
- **Probability**: Very Low (0.05)
- **Impact**: Refactor breaks existing working pattern
- **Mitigation**: Run full DB-AT-010 suite if detector passes; revert if crystal regresses

---

## Artifacts Plan

**Directory**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/`

**Deliverables (Ralph i=140)**:
1. `pytest_detector_distance_option_c.log` — Detector test validation post-refactor
2. `pytest_beam_wavelength_option_c.log` — Beam test validation (expected FAIL, document blocker persistence)
3. `option_c_implementation_summary.md` — Code changes summary (modules touched, LOC metrics, git diff snippets)
4. `summary.md` — Loop summary for galph_memory.md

**Optional (if detector PASSES)**:
5. `pytest_db_at_010_full_suite.log` — Regression check (5 tests)

---

## Next Loop Decision Tree

### If detector PASSES + beam FAILS (Primary Scenario)
**Next loop i=141 (Galph)**: Phase B.1 Closure + Beam Blocker Escalation
- Update implementation.md: mark B.1 partial complete (detector fixed, beam external blocker)
- Create findings.md::GRADIENT-003 (beam wavelength external blocker + reproducer)
- Create thin wrapper reproducer script for nanobrag_torch maintainer
- Decide: Continue Phase B.2-B.3 with 1/2 test coverage OR mark ARCH-GRADIENT-FLOW-001 blocked pending beam fix

### If detector PASSES + beam PASSES (Optimistic Scenario)
**Next loop i=141 (Galph)**: Phase B.2 (Enforcement Test)
- Proceed to enforcement test authoring (`tests/architecture/test_gradient_contracts.py`)
- Full Phase B completion (all 5 DB-AT-010 tests expected to pass)

### If detector FAILS (Failure Scenario)
**Next loop i=141 (Galph)**: Escalation to blocked_pending_environment
- Mark ARCH-GRADIENT-FLOW-001 blocked_pending_environment
- Create combined reproducer for detector + beam gradient breaks
- Document both issues in findings.md
- Switch Tier 0 focus to next unblocked item

---

**Planning notes authored**: 2025-12-07T230000Z (Loop i=140, Galph)
**Phase**: ARCH-GRADIENT-FLOW-001 Phase B.1 Continuation (Option C Refactor)
**Next**: Ralph implements post-creation override pattern for detector/beam configs
