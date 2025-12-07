# Loop Summary — Galph i=140 (Planning)

**Initiative**: ARCH-GRADIENT-FLOW-001 (Gradient Flow Restoration)
**Phase**: B.1 Continuation (Option C Refactor — Post-Creation Override Pattern)
**Date**: 2025-12-07T230000Z
**Status**: ✅ **PLANNING COMPLETE** — DecisionStatus: patch_ready → implementation_in_progress

---

## Turn Summary

**Loop i=140 (Galph)**: Continued ARCH-GRADIENT-FLOW-001 Phase B.1 after Ralph's i=139 implementation showed mixed results (detector gradient flow restored but Jacobian mismatch, beam blocked by external nanobrag_torch.simulator.py:761). Applied implementation floor (2nd consecutive implementation loop allowed) + dominant-hypothesis lock (Option C refactor confidence 0.85). Scoped Phase B.1 continuation: refactor detector/beam overrides to **post-creation pattern** matching crystal_overrides (assign tensor values AFTER config object creation, not before). Revert i=139 factory parameter approach (wavelength_override removed from create_beam_config signature). Implementation estimated 30-50 LOC refactor + validation. Expected detector test PASS (Jacobian resolved), beam test FAIL (external blocker persists). Next: Ralph implements Option C refactor, validates with DB-AT-010 gradcheck tests.

**Artifacts**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/` (planning_notes.md, summary.md, input.md)

---

## Context

Ralph's i=139 Phase B.1 implementation (pre-creation override pattern) produced:
- **Detector distance**: Gradient flow RESTORED (analytical grad 1.14e8 non-zero) ✅ but Jacobian mismatch (~4590× magnitude error) ❌
- **Beam wavelength**: BLOCKED by external dependency (nanobrag_torch.simulator.py:761 uses `torch.tensor()` which detaches autograd graph) ❌

### Root Cause Hypothesis Refinement

**i=139 approach (pre-creation)**:
- Pass tensor to factory (`create_detector_config(..., distance_mm_override=tensor)`)
- Factory assigns override value during config construction
- **Issue**: Factory may perform type conversions/validations after receiving tensor, stripping gradients or introducing magnitude errors

**i=140 approach (post-creation, Option C)**:
- Create config with scalars from dxtbx (existing behavior)
- AFTER creation, assign tensor to config field directly (`detector_config.distance_mm = tensor`)
- **Rationale**: Matches working crystal_overrides pattern (lines 194-208); avoids factory-level type conversions
- **Confidence**: 0.85 (pattern precedent strong, but magnitude error could persist if DetectorConfig property setters perform conversions)

**Beam wavelength blocker**:
- nanobrag_torch.simulator.py:761: `self.wavelength = torch.tensor(self.beam_config.wavelength_A, ...)`
- External dependency (not in dbex codebase), cannot patch per environment freeze
- Option C refactor will NOT resolve beam test (external blocker persists)
- Documentation + escalation deferred to next loop if detector passes

---

## Planning Decisions

### Phase Continuation Justification

**Non-Negotiables Applied**:
- ✅ **Implementation floor**: i=139 was implementation, i=140 continuation allowed (max 2-3 implementation loops per Phase B budget)
- ✅ **Dwell enforcement**: 0 evidence/planning loops since last implementation (i=139)
- ✅ **Cliff avoidance**: i=139 showed gradient flow restored (not a cliff), Jacobian error addressable
- ✅ **Evidence→Action contract**: Ralph's phase_b1_analysis.md provides concrete next step (Option C refactor, lines 183-195)
- ✅ **Dominant-hypothesis lock**: Confidence ≥0.7 for Option C (pattern alignment strong) → must implement, no more probes

**Why continue (not escalate to blocked)?**
1. Detector test shows **partial progress**: gradient flow restored (analytical grad non-zero)
2. Option C identified by Ralph with high confidence (1-loop effort, pattern precedent)
3. Beam blocker is **separate issue** (external dependency), doesn't block detector fix
4. Incremental progress over big bangs: unblock detector first, then assess next steps

### Scope: Option C Refactor

**Reverts** (from i=139):
- Remove `wavelength_override` parameter from `create_beam_config` signature (dbex/refinement/config_factories.py lines 234, 249-250, 257-260)
- Restore factory to pre-i=139 state (scalar extraction from dxtbx only)

**New post-creation override logic** (dbex/physics/forward.py):
1. **Beam overrides** (after `beam_config = create_beam_config(beam)`):
   ```python
   if beam_overrides and 'wavelength_A' in beam_overrides:
       beam_config.wavelength_A = beam_overrides['wavelength_A']
   ```

2. **Detector overrides** (after `detector_configs = [create_detector_config(...) for panel in ...]`):
   ```python
   if detector_overrides and 'distance_mm' in detector_overrides:
       for panel_idx in range(len(detector_configs)):
           detector_configs[panel_idx].distance_mm = detector_overrides['distance_mm']
   ```

**Pattern symmetry**: Matches crystal_overrides precedent (dbex/physics/forward.py:194-208)

---

## Expected Outcomes

### Primary Scenario (Most Likely): Detector PASS, Beam FAIL
- ✅ Detector distance gradcheck PASSES (Jacobian mismatch resolved by post-creation pattern)
- ❌ Beam wavelength gradcheck FAILS (external blocker persists as expected)
- ⚠️ Crystal tests (3/5) status TBD (likely unchanged, may self-resolve)
- **Next loop i=141**: Phase B.1 closure (document detector fix, escalate beam blocker separately)

### Optimistic Scenario: Detector PASS, Beam PASS
- ✅ All 5/5 gradcheck tests PASS
- **Hypothesis**: BeamConfig field assignment bypasses simulator constructor OR nanobrag_torch.simulator.py:761 self-resolved
- **Next loop i=141**: Phase B.2 (enforcement test authoring)

### Failure Scenario: Detector FAIL (Same Signature)
- ❌ Detector distance gradcheck still FAILS with Jacobian mismatch (~4590× magnitude error)
- **Root cause hypothesis rejected**: Post-creation pattern does NOT resolve magnitude error
- **Next loop i=141**: Escalate ARCH-GRADIENT-FLOW-001 to blocked_pending_environment
- **Deliverables**: Minimal reproducer for nanobrag_torch maintainer (detector + beam gradient breaks combined)

### Regression Scenario: Detector FAIL (NEW Signature) or Crystal Regress
- ❌ Detector test fails with different error OR crystal tests change signature
- **Action**: Immediate revert of i=140 changes, audit forward.py call chain
- **Escalation**: Mark blocked_pending_architecture, deeper investigation required

---

## ARCH/SPEC Alignment

### ARCH Contracts Enforced

**GRADIENT-001** (Gradient Test Tensor Override Pattern):
- Post-creation override pattern restores alignment with crystal_overrides precedent
- Factories no longer receive tensor parameters (revert i=139 violation)
- Option C implements canonical owner API pattern (simulate_forward_torch lines 194-208)

**ARCH-ENGINE-002** (Config Factory Scalar Extraction Responsibility):
- Revert wavelength_override parameter from create_beam_config (restore scalar-only contract)
- Factories create configs with dxtbx scalars, caller applies tensor overrides post-creation
- Separation of concerns: factory constructs, caller overrides

### SPEC References

**docs/spec-db-conformance.md** §DB-AT-010:
- Gradcheck tolerance: eps=1e-6, atol=1e-5, rtol=0.05
- Partial satisfaction expected: 1/2 tests (detector), 3/5 total if crystal unaffected
- Full satisfaction deferred: beam blocker requires nanobrag_torch patch

**docs/spec-db-runtime.md** §Gradient Hygiene:
- Production code must preserve gradient graph
- Option C refactor maintains dbex gradient safety (no `.item()` / `.detach()` added)
- External blocker: nanobrag_torch.simulator.py:761 violates spec (out of dbex scope)

---

## Mapped Tests

**Primary validation** (must PASS post-refactor):
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_detector_distance`

**Secondary validation** (expected FAIL, document blocker):
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_beam_wavelength`

**Regression check** (conditional on detector PASS):
- `pytest -v tests -k DB_AT_010 --smoke-detector-size=full` (assess crystal tests, beam expected FAIL)

---

## Lifecycle Tracking

**Dwell**: 2 consecutive loops on ARCH-GRADIENT-FLOW-001 (i=139 implementation, i=140 continuation)
**Budget**: Phase B allowed 2-3 loops; this is loop 2/3
**DecisionStatus**: patch_ready (i=139) → patch_ready (i=140, refactor approach)
**Next Transition**:
  - `localized` if detector PASSES (beam external blocker understood, 1/2 tests working)
  - `blocked` if detector FAILS (escalate both issues to blocked_pending_environment)

**Non-Negotiables Compliance**:
- ✅ Implementation floor: 2nd implementation loop allowed before mandatory evidence/switch
- ✅ Dwell enforcement: No evidence/planning loops since i=139
- ✅ Cliff avoidance: Partial progress (gradient flow restored), addressable Jacobian error
- ✅ Evidence→Action: Concrete next step (Option C) from Ralph's analysis
- ✅ Type discipline: Architecture (gradient hygiene), not bugfix (semantic change)

---

## Risks

**Risk 1: Post-creation field assignment type conversion** (Probability: Low 0.15)
- **Issue**: DetectorConfig/BeamConfig property setters may coerce tensor to scalar on assignment
- **Impact**: Jacobian mismatch persists despite pattern change
- **Mitigation**: If failed, inspect config dataclass definitions, create minimal reproducer

**Risk 2: Crystal tests regress** (Probability: Very Low 0.05)
- **Issue**: Refactor breaks existing working pattern
- **Impact**: 3/5 tests FAIL with new signatures
- **Mitigation**: Immediate revert if crystal tests change signature; crystal pattern lines 194-208 must remain unchanged

**Risk 3: Beam blocker self-resolves unexpectedly** (Probability: Very Low 0.05)
- **Issue**: Post-creation assignment bypasses simulator constructor gradient break
- **Impact**: Both detector + beam PASS (optimistic scenario)
- **Mitigation**: Validate with full suite, proceed to Phase B.2 if 5/5 PASS

---

## Beam Wavelength Blocker Documentation

**Classification**: blocked_pending_environment
**Scope**: External dependency (nanobrag_torch submodule, not in dbex codebase)
**Fix location**: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:761`

**Current (BREAKS gradients)**:
```python
self.wavelength = torch.tensor(self.beam_config.wavelength_A, device=self.device, dtype=self.dtype)
```

**Recommended patch**:
```python
if isinstance(self.beam_config.wavelength_A, torch.Tensor):
    self.wavelength = self.beam_config.wavelength_A.to(device=self.device, dtype=self.dtype)
else:
    self.wavelength = torch.tensor(self.beam_config.wavelength_A, device=self.device, dtype=self.dtype)
```

**Escalation strategy** (if detector PASSES):
1. Document blocker in findings.md::GRADIENT-003
2. Create minimal reproducer script for nanobrag_torch maintainer
3. Decide: continue Phase B with 1/2 test coverage OR mark ARCH-GRADIENT-FLOW-001 blocked pending beam fix

---

## Artifacts Delivered

**Directory**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/`

- ✅ `planning_notes.md` — Phase B.1 continuation rationale, Option C scope, risk analysis, decision tree
- ✅ `summary.md` — This file (loop summary for galph_memory.md)

**Updated**:
- ✅ `input.md` — Comprehensive Do Now with 10 tasks (factory revert, post-creation override logic, validation commands, artifacts, commit)
- ✅ `galph_memory.md` — Will be updated after this summary (i=140 entry with DecisionStatus, Phase B.1 continuation scope, next action)

---

## Next Loop Decision Tree

### If detector PASSES + beam FAILS (Primary Scenario — Probability 0.75)
**Next loop i=141 (Galph)**: Phase B.1 Closure + Beam Blocker Escalation
- Update implementation.md: mark B.1 partial complete (detector fixed, beam external blocker)
- Create findings.md::GRADIENT-003 (beam wavelength external blocker + reproducer pointer)
- Decide: Continue Phase B.2-B.3 with 1/2 test coverage OR mark ARCH-GRADIENT-FLOW-001 blocked pending beam fix
- Document beam blocker for nanobrag_torch maintainer (reproducer script under plan bin/)

### If detector PASSES + beam PASSES (Optimistic Scenario — Probability 0.15)
**Next loop i=141 (Galph)**: Phase B.2 (Enforcement Test Authoring)
- Proceed to enforcement test authoring (`tests/architecture/test_gradient_contracts.py`)
- Full Phase B completion (all 5 DB-AT-010 tests expected to pass)
- Validate hypothesis: BeamConfig field assignment bypasses simulator constructor

### If detector FAILS (Same Jacobian Mismatch) (Failure Scenario — Probability 0.08)
**Next loop i=141 (Galph)**: Escalation to blocked_pending_environment
- Mark ARCH-GRADIENT-FLOW-001 blocked_pending_environment
- Create combined reproducer for detector + beam gradient breaks
- Document both issues in findings.md::GRADIENT-003 (detector Jacobian) + GRADIENT-004 (beam wavelength)
- Switch Tier 0 focus to next unblocked item

### If detector FAILS (NEW Signature) or Crystal Regress (Regression Scenario — Probability 0.02)
**Next loop i=141 (Galph)**: Revert + Deeper Audit
- Immediate revert of all i=140 changes
- Re-run detector test to confirm pre-i=140 signature
- If revert restores i=139 signature → document Option C failure, escalate to blocked
- If revert shows NEW signature → audit forward.py call chain, escalate to blocked_pending_architecture

---

**Planning notes authored**: 2025-12-07T230000Z (Loop i=140, Galph)
**Phase**: ARCH-GRADIENT-FLOW-001 Phase B.1 Continuation (Option C Refactor)
**Next**: Ralph implements post-creation override pattern for detector/beam configs, validates with DB-AT-010 gradcheck tests
