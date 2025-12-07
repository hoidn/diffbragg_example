# Loop Summary — Ralph i=139 (Implementation)

**Date**: 2025-12-07T220000Z
**Phase**: ARCH-GRADIENT-FLOW-001 Phase B.1 Implementation
**Status**: ⚠️ **BLOCKED** — External dependency gradient break (nanobrag_torch.simulator.py:761)

---

## Turn Summary (Ralph i=139)

Implemented tensor-valued detector_overrides and beam_overrides parameters in simulate_forward_torch and config factories (85 LOC across 3 modules). Detector distance test now shows gradient flow restored (analytical gradient non-zero) but Jacobian mismatch indicates magnitude error (~4590× off). Beam wavelength test BLOCKED by external nanobrag_torch.simulator.py:761 gradient break (`torch.tensor()` detaches autograd graph). Committed partial implementation; recommend next loop refactor to post-creation override pattern (match crystal_overrides) OR escalate beam blocker to nanobrag_torch maintainer.

**Artifacts**: `phase_b1_analysis.md`, `pytest_detector_distance_post_fix.log`, `pytest_beam_wavelength_post_fix.log`

---

# Loop Summary — Galph i=139 (Planning)

**Initiative**: ARCH-GRADIENT-FLOW-001 (Gradient Flow Restoration)
**Phase**: B.1 Planning (Detector/Beam Test Harness Fix — Partial)
**Date**: 2025-12-07T220000Z
**Status**: ✅ **PLANNING COMPLETE** — DecisionStatus transition: exploring → patch_ready

---

## Context

Ralph's i=138 Phase A.1-A.2 evidence collection successfully identified root cause:
- **Production code is gradient-safe**: 0 UNSAFE patterns found in 4 audited modules
- **Test harness has 2 critical gradient breaks**:
  - `test_gradients.py:383` — detector distance test calls `.item()` to extract scalar
  - `test_gradients.py:496` — beam wavelength test calls `.item()` to extract scalar
- **Crystal tests unexplained**: Use correct tensor-preserving pattern but still fail (suspected external dependency)

## Planning Decisions

### Phase Transition: A → B.1 (Partial Fix)

**Non-Negotiables Applied**:
- ✅ **Evidence→Action contract**: Top hypothesis identified (test harness `.item()` calls), exact fix location known, confidence 0.95
- ✅ **Dominant-hypothesis lock**: Confidence ≥0.7 → must implement now, no more probes allowed
- ✅ **Implementation floor**: Prior loop was evidence-only, next must be implementation or switch focus
- ✅ **Dwell enforcement**: 1 turn in gathering_evidence, max 2 allowed → must implement or switch

**Partial Fix Rationale**:
- Fix 2/5 known issues immediately (detector + beam)
- Defer crystal test investigation to Phase A.3 probe if they still fail post-fix
- Incremental progress over big bangs: unblock detector/beam first, then assess residual failures
- Pragmatic approach: crystal tests may self-resolve (unlikely but possible)

### Scope for Phase B.1

**Production Changes** (40-60 LOC total):
1. **Detector distance override** (`dbex/refinement/config_factories.py::create_detector_config`):
   - Add `distance_mm_override: Optional[torch.Tensor] = None` parameter
   - Conditional logic: if override provided and tensor, use it; else extract scalar from dxtbx
   - Pattern reference: `dbex/physics/forward.py:158-163` (`crystal_overrides` mechanism)
   - Estimated: 20-30 LOC

2. **Beam wavelength override** (`dbex/refinement/config_factories.py::create_beam_config`):
   - Add `wavelength_override: Optional[torch.Tensor] = None` parameter
   - Conditional logic: if override provided and tensor, use it; else extract scalar from dxtbx
   - Estimated: 15-25 LOC

**Test Harness Changes** (10-20 LOC):
3. **Update detector distance test** (`tests/dbex/test_gradients.py:379-427`):
   - Replace `float(distance_tensor.item())` with tensor-valued config override
   - Estimated: 5-10 LOC

4. **Update beam wavelength test** (`tests/dbex/test_gradients.py:493-518`):
   - Replace `float(wavelength_tensor.item())` with tensor-valued config override
   - Estimated: 5-10 LOC

### Expected Outcomes

**Primary Scenario (Most Likely)**:
- ✅ Detector distance gradcheck PASSES
- ✅ Beam wavelength gradcheck PASSES
- ⚠️ Crystal cell_a/cell_gamma/misset_deg gradcheck still FAILING
- **Next loop i=140**: Phase A.3 probe to diagnose nanobrag_torch.models.Crystal gradient break

**Optimistic Scenario**:
- ✅ All 5/5 gradcheck tests PASS
- **Next loop i=140**: Phase B.2-B.3 (enforcement test + docs + closure)

**Failure Scenario**:
- ❌ Detector/beam tests still fail after fix
- **Next loop i=140**: Deeper call graph audit or mark blocked

---

## Artifacts Delivered

**Directory**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/`

- ✅ `planning_notes.md` — Phase transition rationale, scope definition, risk analysis, next loop decision tree
- ✅ `summary.md` — This file (loop summary for galph_memory.md)

**Updated**:
- ✅ `input.md` — Comprehensive Do Now with 7 tasks (config factory changes, test harness updates, validation runs, analysis report)
- ✅ `galph_memory.md` — Added i=139 entry (DecisionStatus transition, Phase B.1 scope, next action)

---

## ARCH/SPEC Alignment

### ARCH Contracts Applied

1. **GRADIENT-001** (Test gradient preservation):
   - Test harness must use tensor-valued override mechanisms (e.g., `crystal_overrides` dict pattern)
   - Fix aligns with existing pattern (symmetry with crystal tests)

2. **ARCH-ENGINE-002** (Config factory ownership):
   - Geometry config construction logic lives in `config_factories.py`
   - Overrides flow through public API (no test-specific backdoors)

3. **RUNTIME-001** (Gradient execution environment):
   - Use canonical flags: `NANOBRAGG_DISABLE_COMPILE=1` for gradcheck
   - Per `docs/TESTING_GUIDE.md:161`

### SPEC References

- **docs/spec-db-conformance.md** §DB-AT-010: Gradcheck must pass with eps=1e-6, atol=1e-5, rtol≈0.05
  - Partial satisfaction expected: 2/5 tests post-fix
  - Full satisfaction deferred pending crystal test diagnosis

- **docs/spec-db-runtime.md** §Gradient Hygiene: Production code must preserve gradient graph
  - Production code already compliant (0 UNSAFE patterns found)
  - Test harness compliance restored via Phase B.1

---

## Mapped Tests

**Primary validation** (must PASS post-fix):
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_detector_distance`
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_beam_wavelength`

**Secondary assessment** (status unknown post-fix):
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_crystal_cell_a`
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_crystal_cell_gamma`
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_crystal_misset_deg`

**Regression check**:
- Full DB-AT-010 suite (`pytest -v tests -k DB_AT_010 --smoke-detector-size=full`)

---

## Risks and Mitigation

### Risk 1: Config Factory Override Complexity
- **Probability**: Low-Medium
- **Impact**: Implementation exceeds 60 LOC estimate
- **Mitigation**: Follow existing `crystal_overrides` pattern for precedent

### Risk 2: Crystal Tests Remain Unexplained (High Probability)
- **Probability**: High (evidence suggests external dependency)
- **Impact**: Phase B.1 only unblocks 2/5 tests
- **Mitigation**: Budget Phase A.3 probe (1 loop, thin wrapper <400 LOC) for next iteration

### Risk 3: Detector/Beam Fixes Insufficient
- **Probability**: Low (high confidence in hypothesis)
- **Impact**: Phase B.1 fails to unblock any tests
- **Mitigation**: Deeper call graph audit or pivot to spec_change

---

## Next Loop Planning

### If detector+beam PASS, crystal FAIL (Primary Scenario)
**Next loop i=140**: Phase A.3 (Crystal gradient probe)
- Write thin wrapper probe (<400 LOC) to test nanobrag_torch.models.Crystal gradient preservation
- Empirically determine if Crystal constructor breaks gradient
- If confirmed: mark ARCH-GRADIENT-FLOW-001 blocked_pending_environment

### If all 5 tests PASS (Optimistic Scenario)
**Next loop i=140**: Phase B.2-B.3 (Enforcement test + docs)
- Write `tests/architecture/test_gradient_contracts.py`
- Update docs/findings.md (GRADIENT-002), docs/architecture.md, TEST_SUITE_INDEX.md

### If detector+beam still FAIL (Failure Scenario)
**Next loop i=140**: Deeper audit or pivot
- Re-audit config factory call chain
- Consider spec_change to relax DB-AT-010 scope

---

## Turn Summary

**Loop i=139 (Galph)**: Transitioned ARCH-GRADIENT-FLOW-001 from Phase A (evidence) → Phase B.1 (partial fix). Ralph's i=138 evidence collection identified 2 critical test harness gradient breaks (detector distance, beam wavelength using `.item()` calls) with 0 production code issues. Applied dominant-hypothesis lock (confidence 0.95) + implementation floor → must implement now. Scoped Phase B.1: implement tensor-valued overrides in config_factories.py (distance_mm_override, wavelength_override, ~40-60 LOC), update test harness to remove `.item()` calls, validate 2/5 gradcheck tests. Crystal tests deferred to Phase A.3 probe if still failing (suspected external nanobrag_torch dependency). DecisionStatus: exploring → patch_ready. Next: Ralph implements detector/beam fixes, expects 2/5 PASS, assesses crystal test status for next loop decision tree.

**Artifacts**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/` (planning_notes.md, summary.md, input.md)
