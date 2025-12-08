# ARCH-GRADIENT-FLOW-001 — Phase B Planning Notes

**Loop**: i=156 (Galph planning)
**Date**: 2025-12-08T050000Z
**Focus**: Phase B — Integration + Verification of upstream gradient fix

## Context

### Upstream Fix Landed
The `nanobrag_torch` maintainers have shipped fixes for DBEX-GRADIENT-001 blockers (documented in `inbox/from_nanobragg.md`):

1. **Wavelength gradient** — Fixed via `as_tensor_preserving_grad()` at simulator.py:574
2. **Fluence gradient** — Fixed via `as_tensor_preserving_grad()` at simulator.py:585
3. **Distance gradient** — Fixed by converting `Detector.distance` to a property that reads dynamically from config

These fixes enable both Pattern 1 (init-time tensor) and Pattern 2 (post-creation override for detector).

### Phase A Complete
Ralph's i=138 audit identified:
- 0 UNSAFE gradient-breaking patterns in DBEX production code
- Root cause was in `nanobrag_torch` internals, not DBEX
- Test harness previously had `.item()` calls but those were addressed in prior attempts

### Portfolio Impact
- DB-AT-SUITE-CARE-001: Phase C complete (Workflow Integration cluster CERTIFIED)
- Gradient-Safe Profile: Will be unblocked if DB-AT-010 passes
- ARCH-SIM-CONSTRUCTION-001: Separately blocked (spec/expectation mismatch, not gradient issue)

## Phase B Objectives

1. **B1**: Verify the environment has the updated `nanobrag_torch` with gradient-preserving changes
2. **B2**: Run DB-AT-010 gradcheck suite and validate 5/5 PASS
3. **B3**: Author enforcement test to prevent future gradient regressions
4. **B4**: Update documentation (GRADIENT-002 finding, TEST_SUITE_INDEX.md status)

## Technical Notes

### Environment Check (B1)
```python
# Check for as_tensor_preserving_grad utility
from nanobrag_torch.utils.tensor_utils import as_tensor_preserving_grad

# Check for Detector property pattern
from nanobrag_torch.models.detector import Detector
assert isinstance(type(Detector).distance, property)
```

### Gradcheck Expectations (B2)
Per `inbox/from_nanobragg.md`, the following should now work:
- Wavelength gradient: Pattern 1 required (init-time tensor)
- Fluence gradient: Pattern 1 required (init-time tensor)
- Distance gradient: Both Pattern 1 and Pattern 2 supported
- Crystal parameters: Should have been working (no upstream changes needed)

Tolerances per ARCH-CONTRACT-TESTING-002: eps=1e-6, atol=1e-5, rtol=0.05

### Enforcement Test Design (B3)
The enforcement test should:
1. Create a minimal experiment setup with `requires_grad=True` parameter
2. Call `simulate_forward_torch` through the production path
3. Compute a simple loss (e.g., `loss = output.sum()`)
4. Call `loss.backward()`
5. Assert that the gradient is non-None and non-zero

Location: `tests/architecture/test_gradient_contracts.py`
Pattern: Follow ARCH-IMPL-CONFORMANCE-001 precedent (test_*_contracts.py)

## Risks

1. **Environment mismatch**: If nanobrag_torch is not updated, B1 will catch this and document as blocker
2. **DBEX override patterns**: If DBEX is using Pattern 2 for wavelength/fluence (which requires Pattern 1), adjustments may be needed
3. **Crystal gradcheck**: Prior evidence showed crystal tests may have separate issues (confidence 0.6 per Phase A)

## Validation Criteria

- B1: Import check succeeds + property check passes
- B2: 5/5 gradcheck tests PASS (or document specific failure signatures if partial)
- B3: Enforcement test exists and PASSES
- B4: GRADIENT-002 finding added, TEST_SUITE_INDEX.md updated

---

**End of planning notes for Loop i=156**
