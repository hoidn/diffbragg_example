# ARCH-REFACTOR-001 Phase A Planning Analysis

**Date:** 2025-11-24T074500Z
**Loop:** Galph planning (i=253)
**Focus:** Phase A — Physics Extraction (4-step code movement + import updates)

## Executive Summary

**Decision:** APPROVE Phase A ready_for_implementation (single loop, ~3-4 hours estimated)

**Rationale:**
1. Phase 0 safety net established (5 unit tests PASSED, manual coverage ~85-90%)
2. Phase A is pure code movement (no logic changes)
3. Functions well-isolated (leaf-node property, no circular imports)
4. Clear validation path (re-run Phase 0 tests against NEW locations)
5. Low risk (regression guards DB-AT-024 + Stage A smoke protect production)

**Confidence:** HIGH (~90%) Phase A will succeed in single loop

## Phase A Scope

### A1: Extract `derive_u_matrix_from_mosflm_a_star` → `dbex/geometry/crystallography.py`
- **Current location:** `dbex/nanobrag_bridge.py:801-894` (94 lines)
- **Target module:** NEW `dbex/geometry/crystallography.py`
- **Function signature:** `derive_u_matrix_from_mosflm_a_star(a_star: torch.Tensor, ...) -> Tuple[torch.Tensor, torch.Tensor]`
- **Dependencies:** numpy, torch, nanobrag_torch.geometry (EXTERNAL only, leaf-node compliant)
- **Validation:** Re-run `tests/dbex/test_geometry_current.py::test_derive_u_matrix_roundtrip` (2 tests, 1.05s)

### A2: Extract quaternion helpers → `dbex/geometry/rotations.py` (DEFERRED)
- **Status:** SKIP for now (no Phase 0 tests written, low priority)
- **Rationale:** Phase 0 focused on derive_u_matrix only; quaternion extraction can be separate initiative if needed

### A3: Extract `_compute_variance_weighted_loss` → `dbex/physics/loss.py`
- **Current location:** `dbex/nanobrag_refinement.py:447-480` (34 lines)
- **Target module:** NEW `dbex/physics/loss.py`
- **Function signature:** `_compute_variance_weighted_loss(target, model, mask, sigma, variance_floor, ...) -> dict`
- **Dependencies:** torch (EXTERNAL only, leaf-node compliant)
- **Validation:** Re-run `tests/dbex/test_physics_loss_current.py` (4 tests, 0.82s)
- **Spec compliance:** Preserve `V = I_model + sigma^2` detachment per docs/spec-db-core.md

### A4: Update imports + regression guards
- **Import updates:**
  - `dbex/nanobrag_bridge.py`: Replace function def with `from dbex.geometry.crystallography import derive_u_matrix_from_mosflm_a_star`
  - `dbex/nanobrag_refinement.py`: Replace function def with `from dbex.physics.loss import _compute_variance_weighted_loss`
- **Regression guard:** Run `test_stage_a_expansion` (Stage A smoke, small detector, ~12.61s)
- **Parity guard:** Run `DB-AT-024` mapping test (full detector, confirms no forward model regression)

## Dependency Analysis

### Circular Import Risks: LOW
- **Leaf-node constraint:** `dbex.geometry.*` and `dbex.physics.*` import FROM external deps (dxtbx, cctbx, numpy, torch) but NOT from `dbex.nanobrag_*`
- **Import direction (safe):** `dbex.nanobrag_bridge` → `dbex.geometry.crystallography` (one-way)
- **Import direction (safe):** `dbex.nanobrag_refinement` → `dbex.physics.loss` (one-way)

### State Migration: NONE
- **Pure functions:** All target functions are stateless (no class attributes, no globals)
- **No API changes:** Function signatures unchanged, callers unaffected

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Circular import | HIGH | LOW | Enforce leaf-node constraint (no dbex.nanobrag_* imports in new modules) |
| Test failure after move | MEDIUM | LOW | Phase 0 tests validate CURRENT code; re-run against NEW location detects breakage |
| Missing import | LOW | LOW | Explicit import update step (A4) with regression guards |
| CUDA error carryover | LOW | LOW | Use `NANOBRAGG_DISABLE_COMPILE=1` for all tests (proven stable in Phase 0) |

## Validation Strategy

### Primary Validation (re-run Phase 0 tests against NEW locations)
1. **Geometry test:** `NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_geometry_current.py`
   - Expected: 2 tests PASS (roundtrip + identity), 1.05s runtime
2. **Physics test:** `NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_physics_loss_current.py`
   - Expected: 4 tests PASS (clamping + zero mask + zero floor + negative model), 0.82s runtime

### Regression Guards
1. **Stage A smoke:** `DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
   - Expected: PASS, ~12.61s runtime (baseline from Phase 0)
2. **DB-AT-024 mapping:** `DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`
   - Expected: PASS, median correlation ≥0.2, localization ≥90%

### Decision Tree
- **Path A (All tests PASS):** Mark Phase A checklist complete (A1+A3+A4), update implementation.md, commit, proceed to Phase B planning
- **Path B (Phase 0 tests PASS, regression FAIL):** Investigate import/call-site error, fix in same loop, retry
- **Path C (Phase 0 tests FAIL):** Code movement error (signature mismatch, missing dependency), debug and fix
- **Path D (Import error):** Circular import or missing leaf-node constraint, refactor imports

## Implementation Steps (9 total)

1. **Read planning analysis** (this document) + implementation.md Phase A checklist
2. **Create new modules:**
   - `mkdir -p dbex/geometry dbex/physics`
   - `touch dbex/geometry/__init__.py dbex/physics/__init__.py`
3. **A1: Extract derive_u_matrix to dbex/geometry/crystallography.py** (~100 lines)
   - Copy function from `dbex/nanobrag_bridge.py:801-894`
   - Add module docstring + imports (numpy, torch, nanobrag_torch.geometry)
   - Validate NO imports from dbex.nanobrag_*
4. **A3: Extract _compute_variance_weighted_loss to dbex/physics/loss.py** (~40 lines)
   - Copy function from `dbex/nanobrag_refinement.py:447-480`
   - Add module docstring + imports (torch)
   - Validate spec compliance (V = I_model + sigma^2 detachment preserved)
5. **A4: Update imports in nanobrag_bridge.py**
   - Replace derive_u_matrix function def with `from dbex.geometry.crystallography import derive_u_matrix_from_mosflm_a_star`
   - Delete moved function code
6. **A4: Update imports in nanobrag_refinement.py**
   - Replace _compute_variance_weighted_loss function def with `from dbex.physics.loss import _compute_variance_weighted_loss`
   - Delete moved function code
7. **Validation:** Run Phase 0 tests + regression guards (4 pytest commands)
8. **Decision synthesis:** Path A/B/C/D assessment based on test results
9. **Commit + Summary:** Update implementation.md Phase A status, write summary.md, commit with "ARCH-REFACTOR-001 Phase A: Physics extraction (tests: run)"

## Estimated Effort

- **Code movement:** 1 hour (straightforward copy/paste + import updates)
- **Validation:** 1 hour (4 pytest commands + logs)
- **Debugging buffer:** 1-2 hours (if Path B/C/D)
- **Total:** 3-4 hours (single loop feasible)

## Findings Applied

- **POLICY-001:** Environment Freeze (no package installs, dbex-only changes)
- **PHYSICS-LOSS-001:** Variance-weighted loss formula (preserve V = I_model + sigma^2 detachment)
- **GEOMETRY-003:** B_ideal convention (MOSFLM A* = U @ B_ideal, validated in Phase 0)
- **GRADIENT-001:** Autograd graph preservation (no .detach() changes during code movement)
- **REFINE-001:** LBFGS scale warm-start patterns (regression guards protect production)

## References

- **Implementation Plan:** plans/active/ARCH-REFACTOR-001/implementation.md (Phase A checklist lines 92-106)
- **Phase 0 Evidence:** plans/active/ARCH-REFACTOR-001/reports/2025-11-24T070000Z/phase_0_decision.md (tests PASSED, manual coverage ~85-90%)
- **Spec:** docs/spec-db-core.md (variance definition), docs/spec-db-workflow.md (refinement protocol)
- **Code Locations:**
  - derive_u_matrix: dbex/nanobrag_bridge.py:801-894
  - _compute_variance_weighted_loss: dbex/nanobrag_refinement.py:447-480
- **Test Files:**
  - tests/dbex/test_geometry_current.py (2 tests, 1.05s)
  - tests/dbex/test_physics_loss_current.py (4 tests, 0.82s)

## Artifacts (this loop)

- `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/`
  - `phase_a_planning_analysis.md` (this document)
  - `pytest_geometry_new.log` (Phase 0 geometry tests against NEW location)
  - `pytest_physics_new.log` (Phase 0 physics tests against NEW location)
  - `regression_stage_a.log` (test_stage_a_expansion after Phase A)
  - `regression_db_at_024.log` (DB-AT-024 after Phase A)
  - `phase_a_decision.md` (Path A/B/C/D verdict + metrics)
  - `summary.md` (Turn Summary)

## Confidence Assessment

**HIGH (~90%)** Phase A will succeed in single loop based on:
1. Phase 0 established safety net (tests validate CURRENT code correctness)
2. Pure code movement (no logic changes, low regression risk)
3. Leaf-node constraint enforced (no circular import risk)
4. Clear validation path (re-run Phase 0 tests detects any breakage immediately)
5. Regression guards protect production (Stage A smoke + DB-AT-024)
6. Estimated 3-4 hours fits single loop (similar to Phase 0 which completed successfully)

## Next Actions

Ralph executes 9-step implementation protocol:
1. Read planning analysis + implementation.md Phase A
2. Create new module structure (dbex/geometry/, dbex/physics/)
3. Extract derive_u_matrix → dbex/geometry/crystallography.py (A1)
4. Extract _compute_variance_weighted_loss → dbex/physics/loss.py (A3)
5. Update imports in nanobrag_bridge.py (A4)
6. Update imports in nanobrag_refinement.py (A4)
7. Run validation (Phase 0 tests + regression guards)
8. Decision synthesis (Path A expected: all tests PASS)
9. Commit + summary.md

**Expected Outcome:** Path A (all tests PASS), Phase A checklist complete, proceed to Phase B planning next loop.
