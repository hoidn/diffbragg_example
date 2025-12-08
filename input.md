# Input — Loop i=156

## Summary
Execute ARCH-GRADIENT-FLOW-001 Phase B (integration + verification) — upstream nanobrag_torch gradient fix has landed; run DB-AT-010 gradcheck and add enforcement test.

## Mode
none

## ActionType
implementation_ready

## DecisionStatus
patch_ready

## InitiativeType
architecture

## Focus
ARCH-GRADIENT-FLOW-001 — Gradient Flow Restoration (Phase B)

## Branch
integration

## Mapped tests
- DB-AT-010 gradcheck suite: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=full pytest -v tests -k DB_AT_010` (5 tests, expect PASS with upstream fix)
- Enforcement test (after authoring): `pytest -v tests/architecture/test_gradient_contracts.py` (expect PASS)

## Artifacts
`plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T050000Z/`

## Findings Applied (Mandatory)
- **RUNTIME-001** (Runtime execution guardrails): DB-AT-010 requires `NANOBRAGG_DISABLE_COMPILE=1` per docs/pytorch_runtime_checklist.md:26
- **GRADIENT-001** (Gradient test patterns): Tests inject differentiable parameters via `crystal_overrides` to preserve autograd graph
- **TESTING-003** (Acceptance test registry maintenance): Update TEST_SUITE_INDEX.md when DB-AT-010 status changes FAILING → PASSING

## Pointers
- **Upstream Fix Documentation**: `inbox/from_nanobragg.md` — DBEX-GRADIENT-001 fixes (wavelength, fluence, distance)
- **Maintainer Response**: `inbox/nanobrag_torch_response_2025_12_08.md` — Gradient blockers RESOLVED section
- **SPEC**: `docs/spec-db-conformance.md:55-76` — Gradient-Safe Profile criteria
- **ARCH**: `plans/active/ARCH-GRADIENT-FLOW-001/implementation.md` — Phase B task list
- **Fix-plan**: `docs/fix_plan.md:246-265` — ARCH-GRADIENT-FLOW-001 Attempts History
- **Evidence from Phase A**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/` — call graph trace, suspect audit

## ARCH Contracts (mandatory)
1. **ARCH-CONTRACT-GRADIENT-001** (Gradient flow preservation): `simulate_forward_torch` must preserve `requires_grad=True` through the call path to allow backprop
   - Owner: `dbex/physics/forward.py::simulate_forward_torch`
   - Classify: implementation bug previously (upstream fix now available); verify fix resolves it

2. **ARCH-CONTRACT-TESTING-002** (Gradcheck tolerances): DB-AT-010 tests use documented tolerances (`eps=1e-6`, `atol=1e-5`, `rtol=0.05`)
   - Owner: `tests/dbex/test_gradients.py`
   - Classify: verify tolerances match spec; document any adjustments

## Do Now (hard validity contract)

**Focus**: ARCH-GRADIENT-FLOW-001 — Phase B (Integration + Verification)

**Implement**: Phase B tasks B1-B4

**Tasks**:

1. **B1 — Verify upstream fix integration**:
   - Check that the current environment has the nanobrag_torch version with gradient-preserving changes
   - Test command: `python -c "from nanobrag_torch.utils.tensor_utils import as_tensor_preserving_grad; print('OK')"`
   - If import fails: document as blocker (environment dependency issue)
   - If import succeeds: proceed to B2

2. **B2 — DB-AT-010 gradcheck verification**:
   - Run: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=full pytest -v tests -k DB_AT_010`
   - Expected: 5/5 tests PASS (wavelength, fluence, distance, crystal cell parameters)
   - Archive log to: `reports/2025-12-08T050000Z/gradcheck_verification_post_fix.log`
   - If tests FAIL: Document failure signature, assess whether DBEX-side changes needed (per `inbox/from_nanobragg.md` Pattern 1 vs Pattern 2)

3. **B3 — Enforcement test authoring**:
   - Create `tests/architecture/test_gradient_contracts.py::test_simulate_forward_torch_preserves_gradients`
   - Test requirements:
     1. Call `simulate_forward_torch` with `requires_grad=True` tensor parameter (use crystal_overrides pattern)
     2. Compute loss, call backward
     3. Assert `param.grad is not None` and `param.grad.abs().sum() > 0`
     4. Use minimal refGeom fixture (small detector size for speed)
   - Run: `pytest -v tests/architecture/test_gradient_contracts.py`
   - Expected: PASS

4. **B4 — Documentation updates**:
   - Add `docs/findings.md::GRADIENT-002` finding documenting:
     - Upstream fix location: `nanobrag_torch/utils/tensor_utils.py::as_tensor_preserving_grad`
     - DBEX patterns validated: Pattern 1 (init-time tensor) and Pattern 2 (post-creation override for detector)
     - Enforcement test cross-ref: `tests/architecture/test_gradient_contracts.py`
   - Update `docs/development/TEST_SUITE_INDEX.md` DB-AT-010 row to status=PASSING (if B2 succeeds)
   - Archive artifacts

**Validating pytest selectors**:
- `pytest -v tests -k DB_AT_010` (expect 5/5 PASS after fix)
- `pytest -v tests/architecture/test_gradient_contracts.py` (expect PASS after B3 authoring)

## Touched
Phase B tasks: B1, B2, B3, B4
Member plan: DB-AT-010 (status update)
Roll-up: DB-AT-SUITE-CARE-001 (Gradient-Safe Profile unblocked)

## Forbidden This Loop
- no new probes or plan-local diagnostic scripts
- do not extend shadow pipeline scripts
- do not modify ARCH-SIM-CONSTRUCTION-001 (blocked on different issue — spec/expectation mismatch)
- do not modify Tier 1+ initiatives unless directly impacted by gradient fix

## How-To Map

### Environment setup
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export DBEX_SMOKE_DETECTOR_SIZE=full
```

### B1 — Verify upstream fix
```bash
# Check nanobrag_torch has gradient-preserving utility
python -c "from nanobrag_torch.utils.tensor_utils import as_tensor_preserving_grad; print('as_tensor_preserving_grad available')"

# Check detector property pattern
python -c "from nanobrag_torch.models.detector import Detector; print('Detector.distance is property:', isinstance(type(Detector).distance, property))"
```

### B2 — Gradcheck verification
```bash
mkdir -p plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T050000Z

KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=full \
  pytest -v tests -k DB_AT_010 \
  2>&1 | tee plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T050000Z/gradcheck_verification_post_fix.log
```

### B3 — Enforcement test
Create `tests/architecture/test_gradient_contracts.py` with:
- `test_simulate_forward_torch_preserves_gradients` method
- Use existing `refgeom_dataload` fixture pattern
- Apply GRADIENT-001 finding: use `crystal_overrides` dict for differentiable parameters

### B4 — Documentation
- Update `docs/findings.md` with GRADIENT-002 entry
- Update `docs/development/TEST_SUITE_INDEX.md` DB-AT-010 row

### Artifact destinations
- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T050000Z/gradcheck_verification_post_fix.log`
- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T050000Z/summary.md`
- `tests/architecture/test_gradient_contracts.py` (new file)

## Pitfalls To Avoid
1. **Type discipline**: This is an architecture initiative; production code changes should be minimal (the fix is upstream in nanobrag_torch, not DBEX)
2. **No stacking on cliff**: If gradcheck still fails, document failure signature precisely — do not attempt multiple fixes in same loop
3. **Parity-first**: Verify upstream fix is integrated before attempting DBEX-side workarounds
4. **Shadow-pipeline guard**: Enforcement test should call production code path, not create parallel implementation
5. **Probe saturation**: No new instrumentation — Phase A audit is complete
6. **Evidence→Action**: If B1 shows nanobrag_torch is not updated, document as blocker (do not attempt manual patches)
7. **Tolerance discipline**: Use documented tolerances (eps=1e-6, atol=1e-5, rtol=0.05); do not relax without spec_change justification
8. **Pattern compliance**: Per `inbox/from_nanobragg.md`, wavelength/fluence require Pattern 1 (init-time tensor); distance supports Pattern 2 (post-creation)

## If Blocked
- **If nanobrag_torch lacks gradient fix**: Document as `blocked_pending_environment`; record exact import error; recommend vendored subrepo update or pip install from fixed branch
- **If gradcheck still fails after fix**: Document failure signature with file:line; compare against Phase A hypothesis; determine if DBEX-side override pattern needs adjustment (Pattern 1 vs Pattern 2)
- **If enforcement test cannot use minimal fixture**: Fallback to unit-level test (mock simulator output) with regression guard; document limitation

## Doc Sync Plan (Conditional)
If B2 succeeds (DB-AT-010 5/5 PASS):
1. Update `docs/development/TEST_SUITE_INDEX.md` DB-AT-010 row: status=PASSING, artifact path=`reports/2025-12-08T050000Z/gradcheck_verification_post_fix.log`
2. Add GRADIENT-002 finding to `docs/findings.md`
3. Cross-reference TESTING_GUIDE.md §1.4 for consistency

---

**End of input.md for Loop i=156**
