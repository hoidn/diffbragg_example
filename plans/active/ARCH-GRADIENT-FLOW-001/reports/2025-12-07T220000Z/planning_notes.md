# Planning Notes — Galph i=139

**Initiative**: ARCH-GRADIENT-FLOW-001 (Gradient Flow Restoration)
**Phase**: B.1 (Detector/Beam Test Harness Fix — Partial)
**Date**: 2025-12-07T220000Z
**DecisionStatus**: exploring → **patch_ready**

---

## Context

Ralph's i=138 evidence collection (Phase A.1-A.2) successfully localized root cause:
- **Production code is gradient-safe**: 0 UNSAFE patterns found in 4 audited modules
- **Test harness has 2 critical bugs**: test_gradients.py:383 (detector) and :496 (beam) break gradient via `.item()` calls
- **Crystal tests remain unexplained**: Use correct tensor-preserving pattern but still fail (suspected external nanobrag_torch dependency)

## Phase Transition Rationale

**From Phase A → Phase B.1**:
- Evidence→Action contract satisfied: top hypothesis identified, exact fix location known
- Dominant-hypothesis lock triggered: confidence 0.95 for detector/beam fixes
- Implementation floor: prior loop was evidence-only, next must be implementation
- Dwell enforcement: 1 turn in gathering_evidence, must implement or switch

**Partial Fix Strategy** (B.1 instead of full B):
- Fix 2/5 gradcheck tests immediately (detector + beam)
- Defer crystal test investigation to Phase A.3 probe if needed
- Pragmatic incremental progress: unblock known issues first, then assess residual failures

## Non-Negotiables Applied

✅ **Evidence→Action contract**: Top hypothesis (test harness `.item()` calls), exact next production edit (config factories + test harness)
✅ **Dominant-hypothesis lock**: Confidence ≥0.7 → must implement now
✅ **Implementation floor**: Cannot do another evidence/planning loop
✅ **Dwell enforcement**: Max 2 turns in evidence/planning per selector+signature
✅ **No stacking on cliff**: No catastrophic failures, safe to proceed

## Scope for Phase B.1

### Production Changes (40-60 LOC total)

1. **Detector distance override** (`dbex/refinement/config_factories.py`):
   - Add `distance_mm_override: Optional[torch.Tensor]` parameter to `create_detector_config`
   - Conditional logic: if override provided and tensor, use it; else extract scalar from dxtbx
   - Estimated: 20-30 LOC

2. **Beam wavelength override** (two options):
   - Option A: Add `wavelength_override: Optional[torch.Tensor]` to `create_beam_config`
   - Option B: Modify test fixture to use BeamConfig with tensor wavelength directly
   - Estimated: 15-25 LOC
   - **Recommendation**: Option A for symmetry with detector pattern

### Test Harness Changes (10-20 LOC)

3. **Update detector distance test** (`tests/dbex/test_gradients.py:379-427`):
   - Replace `float(distance_tensor.item())` with tensor-valued config override
   - Call `create_detector_config(..., distance_mm_override=distance_tensor)`
   - Estimated: 5-10 LOC

4. **Update beam wavelength test** (`tests/dbex/test_gradients.py:493-518`):
   - Replace `float(wavelength_tensor.item())` with tensor-valued config override
   - Call `create_beam_config(..., wavelength_override=wavelength_tensor)` or similar
   - Estimated: 5-10 LOC

### Validation

5. **Gradcheck verification** (DB-AT-010 subset):
   - Run: `pytest -v tests/dbex/test_gradients.py::test_db_at_010_gradcheck_detector_distance --smoke-detector-size=full`
   - Run: `pytest -v tests/dbex/test_gradients.py::test_db_at_010_gradcheck_beam_wavelength --smoke-detector-size=full`
   - Expected: Both tests PASS (2/5 gradcheck suite)
   - Capture pytest logs under `reports/2025-12-07T220000Z/`

6. **Regression check**:
   - Run full DB-AT-010 suite to assess crystal test status post-fix
   - If crystal tests still fail → document failure signature, plan Phase A.3 probe next loop
   - If crystal tests pass → proceed to full Phase B (enforcement test + docs) next loop

## Expected Outcomes

### Success Scenario (Primary)
- ✅ Detector distance gradcheck PASSES
- ✅ Beam wavelength gradcheck PASSES
- ⚠️ Crystal cell_a/cell_gamma gradcheck still FAILING (external dependency suspected)
- **Next loop**: Phase A.3 probe to diagnose nanobrag_torch.models.Crystal gradient break

### Surprise Success Scenario (Optimistic)
- ✅ All 5/5 gradcheck tests PASS
- **Next loop**: Skip Phase A.3, proceed directly to Phase B.2-B.4 (enforcement test + docs + closure)

### Failure Scenario (Requires Pivot)
- ❌ Detector/beam tests still fail after fix
- **Next loop**: Deeper call graph audit (missed gradient break in config factory chain), or mark blocked

## Risks and Mitigation

### Risk 1: Config Factory Override Complexity
**Probability**: Low-Medium
**Impact**: Implementation exceeds 60 LOC estimate, requires additional tensor/scalar branching
**Mitigation**: Follow existing `crystal_overrides` pattern from forward.py:158-163 as precedent

### Risk 2: dxtbx Geometry Construction Side Effects
**Probability**: Low
**Impact**: Tensor-valued overrides work in config but dxtbx geometry still requires scalar extraction elsewhere
**Mitigation**: Test harness calls simulate_forward_torch directly (bypasses dxtbx), so override happens at config layer only

### Risk 3: Crystal Tests Remain Unexplained
**Probability**: High (evidence suggests external dependency)
**Impact**: Phase B.1 only unblocks 2/5 tests, portfolio advancement partial
**Mitigation**: Budget Phase A.3 probe (1 loop, thin wrapper <400 LOC) for next iteration if needed

## ARCH/SPEC Alignment

### ARCH Contracts
- **GRADIENT-001 (findings.md)**: Test harness must use tensor-valued overrides to preserve autograd graph
  - Current violation: detector/beam tests use `.item()` scalar extraction
  - Fix aligns with GRADIENT-001 pattern (similar to existing `crystal_overrides`)

- **ARCH-ENGINE-002**: Config factories own geometry construction; overrides must flow through canonical API
  - Fix adds override parameters to `create_detector_config` / `create_beam_config`
  - No duplication: test harness calls public config factory API

### SPEC References
- **docs/spec-db-conformance.md** §DB-AT-010: Gradcheck must pass with eps=1e-6, atol=1e-5, rtol≈0.05
  - Partial satisfaction: 2/5 tests expected to pass post-fix
  - Full satisfaction deferred pending crystal test diagnosis

- **docs/spec-db-runtime.md** §Gradient Hygiene: Production code must preserve gradient graph
  - Production code already compliant (0 UNSAFE patterns found)
  - Test harness compliance restored via this fix

## Decision Justification

**Why Phase B.1 (Partial) instead of Phase A.3 (Probe First)?**

1. **Incremental progress over big bangs**: Fix known issues immediately (2/5 tests), then assess residual failures
2. **Evidence→Action contract**: Top hypothesis for detector/beam tests has 0.95 confidence, exact fix location known
3. **Implementation floor**: Cannot do another evidence loop without violating dwell rules
4. **Pragmatic approach**: Crystal tests may self-resolve after detector/beam fixes (unlikely but possible)
5. **Thin wrapper budget**: Phase A.3 probe would consume plan-local script budget for marginal diagnostic value

**Why not full Phase B (enforcement test + docs)?**

1. **Unknown crystal test status**: Don't want to document partial success if all 5 tests eventually pass
2. **Enforcement test scope unclear**: If crystal tests fail, enforcement test should cover detector/beam only OR escalate to external dependency fix
3. **Defer full closure**: Wait until all 5 tests pass OR crystal tests confirmed blocked before writing GRADIENT-002 finding

## Mapped Tests (Phase B.1)

**Primary validation** (must PASS post-fix):
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_detector_distance` (1 test)
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_beam_wavelength` (1 test)

**Secondary assessment** (status unknown post-fix):
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_crystal_cell_a` (1 test)
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_crystal_cell_gamma` (1 test)
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_crystal_misset_deg` (1 test)

**Regression check** (must remain PASSING):
- Full DB-AT-010 suite (`pytest -v tests -k DB_AT_010 --smoke-detector-size=full`)

## Artifacts Plan

**Directory**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/`

Required deliverables:
- `planning_notes.md` — This file
- `pytest_detector_distance_post_fix.log` — Detector gradcheck pytest log
- `pytest_beam_wavelength_post_fix.log` — Beam gradcheck pytest log
- `pytest_db_at_010_full_suite_post_fix.log` — Full suite regression check
- `phase_b1_analysis.md` — Fix implementation notes, crystal test status assessment, next action recommendation
- `summary.md` — Loop summary for galph_memory.md

## Next Loop Planning

### If detector+beam PASS, crystal FAIL (Primary Scenario)
**Next loop i=140**: Phase A.3 (Crystal gradient probe)
- Write thin wrapper probe (<400 LOC) to test nanobrag_torch.models.Crystal gradient preservation
- Empirically determine if Crystal constructor breaks gradient
- If confirmed: mark ARCH-GRADIENT-FLOW-001 blocked_pending_environment, escalate to maintainer
- If not confirmed: audit misset_deg / A* hydration for missed gradient breaks

### If all 5 tests PASS (Optimistic Scenario)
**Next loop i=140**: Phase B.2-B.3 (Enforcement test + docs)
- Write `tests/architecture/test_gradient_contracts.py::test_simulate_forward_torch_preserves_gradients`
- Update docs/findings.md (GRADIENT-002), docs/architecture.md (§13), TEST_SUITE_INDEX.md
- Prepare for Phase C closure (i=141)

### If detector+beam still FAIL (Failure Scenario)
**Next loop i=140**: Deeper audit or pivot
- Re-audit config factory call chain for missed gradient breaks
- Check if override mechanism itself has issues (tensor/scalar coercion in config layer)
- If stuck after 2nd implementation attempt: mark blocked, open spec_change to relax DB-AT-010 scope

## Notes for Ralph

**Focus**: Detector + beam test harness gradient breaks (test_gradients.py:383, :496)
**Goal**: Implement tensor-valued override mechanisms in config factories, update test harness to use them
**Expected outcome**: 2/5 gradcheck tests PASS, crystal test status TBD

**Do NOT**:
- Attempt to fix crystal tests this loop (defer to Phase A.3 probe)
- Write enforcement test yet (defer to Phase B.2 after all tests passing OR crystal confirmed blocked)
- Create plan-local diagnostic scripts (Phase B.1 is production fix only)

**DO**:
- Keep changes minimal (<60 LOC total)
- Follow existing `crystal_overrides` pattern for symmetry
- Capture pytest logs for all 3 validation runs (detector, beam, full suite)
- Document crystal test failure signature if they remain failing

---

**Planning complete**: 2025-12-07T220000Z (Galph i=139)
**Next action**: Delegate Phase B.1 implementation to Ralph
