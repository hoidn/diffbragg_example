# ARCH-GRADIENT-FLOW-001 Loop i=157 Summary (Galph Review)

## Turn Summary

Reviewed Phase B execution results (Ralph i=153). **Partial success**: nanobrag_torch layer gradient flow FIXED (5/5 enforcement tests PASS), but DB-AT-010 still fails (5/5) due to DBEX-layer gradient breaks. Root cause has SHIFTED from nanobrag_torch (now fixed) to DBEX layer (`simulate_forward_torch` → `create_unified_simulator` → Crystal/Detector construction). Initiative marked **partial**; DBEX-layer work deferred as separate initiative scope.

## Problem & SPEC/ARCH Alignment

- **Problem**: DB-AT-010 gradcheck tests failing — gradient flow broken
- **SPEC alignment**: inbox/from_nanobragg.md (upstream fix integrated), GRADIENT-002 finding documented
- **Initiative type**: architecture
- **ActionType**: review_or_housekeeping (partial completion assessment)

## Phase B Execution Results (Ralph i=153)

### Completed Tasks
1. **B1 — Upstream fix integration** ✅
   - Created `nanobrag_torch/utils/tensor_utils.py::as_tensor_preserving_grad`
   - Updated `Simulator.__init__` for wavelength/fluence/kahn_factor

2. **B2 — Detector property conversion** ✅
   - Converted `Detector.distance`, `pixel_size`, `close_distance` to properties
   - Enables post-creation override pattern

3. **B3 — Enforcement tests** ✅
   - Authored `tests/architecture/test_gradient_contracts.py` (5 tests)
   - All tests PASS
   - Validates gradient flow through Simulator.wavelength, Simulator.fluence, Detector.distance

4. **B4 — Documentation** ✅
   - `docs/findings.md::GRADIENT-002` added
   - `docs/development/TEST_SUITE_INDEX.md` row for ARCH-GRADIENT-FLOW-001 tests

### Remaining Work (DBEX Layer)
- DB-AT-010 still fails (5/5): `GradcheckError: Numerical gradient for function expected to be zero`
- Root cause: `crystal_overrides` and `detector_overrides` in DBEX layer break gradient flow
- Per summary.md: "Next step: DBEX-layer gradient fixes (separate initiative scope)"

## Exit Criteria Assessment

| # | Criterion | Status |
|---|-----------|--------|
| 1 | DB-AT-010 gradcheck 5/5 PASS | ❌ NOT MET (5/5 FAIL — DBEX layer) |
| 2 | Root cause fixed | ⚠️ PARTIAL (nanobrag_torch fixed, DBEX blocked) |
| 3 | Enforcement test added | ✅ MET (5 tests PASS) |
| 4 | Documentation updated | ✅ MET (GRADIENT-002, TEST_SUITE_INDEX.md) |
| 5 | Regression validation | ❌ NOT MET (blocked on DBEX layer) |

**Overall**: 2/5 fully met, 1/5 partial → Initiative marked **partial**

## Decision

Per `non_negotiables::evidence→action`, the initiative has hit a **layer boundary**:
- nanobrag_torch layer: **FIXED** (enforcement tests prove gradient flow works)
- DBEX layer: **BLOCKED** (requires separate initiative to thread gradients through `simulate_forward_torch`)

**Action taken**:
- Initiative status → `partial`
- Phase B.5 (DBEX-layer work) deferred
- Portfolio steering: switch to next Tier 1 focus (SPEC-SQUARE-PARTIALITY-001)

## Next Loop Focus

**SPEC-SQUARE-PARTIALITY-001** — Align SQUARE lattice specs and tests with correct physics per `inbox/nanobrag_torch_response_2025_12_08.md`:
- Peak intensity ∝ `(Na×Nb×Nc)²`
- Integrated/summed intensity ∝ `Na×Nb×Nc` (linear)

This unblocks ARCH-SIM-CONSTRUCTION-001 by resolving the spec/expectation mismatch.

## Artifacts

- `galph_memory.md` — Updated with partial completion status
- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T060000Z/summary.md` — This file
- Prior artifacts: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T050000Z/` (Ralph execution results)
