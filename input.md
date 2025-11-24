# Ralph Input — ARCH-REFACTOR-001 Phase A (Physics Extraction)

## Summary
Extract core physics functions (`derive_u_matrix`, `_compute_variance_weighted_loss`) from monolithic modules to new `dbex.geometry.crystallography` and `dbex.physics.loss` modules, update imports, validate with Phase 0 tests.

## Mode
none

## Focus
ARCH-REFACTOR-001 — Phase A: Physics Extraction (Code Movement + Import Updates)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_geometry_current.py::test_derive_u_matrix_roundtrip` (Phase 0 geometry test, validates NEW location)
- `tests/dbex/test_physics_loss_current.py` (Phase 0 physics tests, 4 tests validate NEW location)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard, small detector)
- `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` (regression guard, full detector)

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/`
- `pytest_geometry_new.log` (geometry tests against NEW dbex.geometry.crystallography)
- `pytest_physics_new.log` (physics tests against NEW dbex.physics.loss)
- `regression_stage_a.log` (Stage A smoke after import updates)
- `regression_db_at_024.log` (DB-AT-024 mapping after import updates)
- `phase_a_decision.md` (Path A/B/C/D verdict, metrics summary)
- `summary.md` (Turn Summary with loop outcomes)

## Do Now

**Context:** ARCH-REFACTOR-001 Phase 0 ✓ COMPLETE (5 unit tests PASSED, manual coverage ~85-90% per 2025-11-24T070000Z). Phase A = pure code movement (NO logic changes), extract math kernels to leaf-node modules, validate with Phase 0 tests. Read `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/phase_a_planning_analysis.md` for comprehensive scope, risks, decision tree.

**Task:** Implement Phase A checklist (implementation.md:92-106): extract `derive_u_matrix_from_mosflm_a_star` (A1), `_compute_variance_weighted_loss` (A3), update imports (A4), validate with Phase 0 tests + regression guards.

### Steps (9 total)

1. **Read planning analysis:**
   - `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/phase_a_planning_analysis.md` (scope, risks, decision tree)
   - `plans/active/ARCH-REFACTOR-001/implementation.md:92-106` (Phase A checklist)

2. **Create new module structure:**
   ```bash
   mkdir -p dbex/geometry dbex/physics
   touch dbex/geometry/__init__.py dbex/physics/__init__.py
   ```

3. **A1: Extract derive_u_matrix_from_mosflm_a_star → dbex/geometry/crystallography.py:**
   - **Source:** `dbex/nanobrag_bridge.py:801-894` (94 lines, function + docstring)
   - **Target:** NEW `dbex/geometry/crystallography.py`
   - **Actions:**
     - Create `dbex/geometry/crystallography.py` with module docstring
     - Copy function verbatim (preserve all logic, signatures, comments)
     - Add imports: `import numpy as np`, `import torch`, `from nanobrag_torch.geometry import busing_levy_B_torch`
     - **Leaf-node constraint validation:** Ensure NO imports from `dbex.nanobrag_bridge` or `dbex.nanobrag_refinement` (external deps only)
   - **Validation after A1:**
     ```bash
     # Verify no circular imports
     python -c "from dbex.geometry.crystallography import derive_u_matrix_from_mosflm_a_star; print('Import OK')"
     ```

4. **A3: Extract _compute_variance_weighted_loss → dbex/physics/loss.py:**
   - **Source:** `dbex/nanobrag_refinement.py:447-480` (34 lines)
   - **Target:** NEW `dbex/physics/loss.py`
   - **Actions:**
     - Create `dbex/physics/loss.py` with module docstring
     - Copy function verbatim (preserve V = I_model + sigma^2 detachment per spec-db-core.md)
     - Add imports: `import torch`
     - **Leaf-node constraint validation:** Ensure NO imports from `dbex.nanobrag_*` (torch only)
   - **Validation after A3:**
     ```bash
     python -c "from dbex.physics.loss import _compute_variance_weighted_loss; print('Import OK')"
     ```

5. **A4: Update imports in dbex/nanobrag_bridge.py:**
   - **Location:** Find `derive_u_matrix_from_mosflm_a_star` function definition (around line 801)
   - **Replace function def with import:**
     ```python
     from dbex.geometry.crystallography import derive_u_matrix_from_mosflm_a_star
     ```
   - **Delete:** Remove entire function body (lines 801-894)

6. **A4: Update imports in dbex/nanobrag_refinement.py:**
   - **Location:** Find `_compute_variance_weighted_loss` function definition (around line 447)
   - **Replace function def with import:**
     ```python
     from dbex.physics.loss import _compute_variance_weighted_loss
     ```
   - **Delete:** Remove entire function body (lines 447-480)

7. **Validation — Run Phase 0 tests against NEW locations:**
   ```bash
   # Geometry test (2 tests, expect PASS, 1.05s baseline)
   NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_geometry_current.py > plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/pytest_geometry_new.log 2>&1

   # Physics test (4 tests, expect PASS, 0.82s baseline)
   NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_physics_loss_current.py > plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/pytest_physics_new.log 2>&1

   # Regression guard: Stage A smoke (small detector, expect PASS, ~12.61s baseline)
   DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/regression_stage_a.log 2>&1

   # Regression guard: DB-AT-024 mapping (full detector, expect PASS, median corr ≥0.2)
   DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke > plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/regression_db_at_024.log 2>&1
   ```

8. **Decision synthesis — Path assessment:**
   - **Path A (All tests PASS):** Mark Phase A checklist (A1, A3, A4) complete in implementation.md, proceed to summary
   - **Path B (Phase 0 tests PASS, regression FAIL):** Investigate import/call-site error in same loop
   - **Path C (Phase 0 tests FAIL):** Debug code movement error (signature mismatch, missing dependency)
   - **Path D (Import error):** Check for circular import or missing leaf-node constraint
   - Write `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/phase_a_decision.md` (path verdict, test metrics, next actions)

9. **Summary + commit:**
   - Write `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T074500Z/summary.md` (Turn Summary: what shipped, main problem, next step, artifacts)
   - Update `plans/active/ARCH-REFACTOR-001/implementation.md`:
     - Phase A checklist items A1, A3, A4: mark `[x]` with completion timestamp
     - Phase A status: `✓ COMPLETE (2025-11-24T074500Z)` if Path A
   - Commit:
     ```bash
     git add -A
     git commit -m "ARCH-REFACTOR-001 Phase A: Physics extraction (derive_u_matrix, variance_weighted_loss) — tests: run"
     git push
     ```

## How-To Map

### Module Creation
```bash
# Create directory structure
mkdir -p dbex/geometry dbex/physics
touch dbex/geometry/__init__.py dbex/physics/__init__.py
```

### Code Extraction Template (A1 example)
```python
# dbex/geometry/crystallography.py
"""
Pure crystallographic math functions.

Leaf-node module: imports FROM external deps (numpy, torch, nanobrag_torch)
but NOT from dbex.nanobrag_* to avoid circular imports.
"""
import numpy as np
import torch
from nanobrag_torch.geometry import busing_levy_B_torch

def derive_u_matrix_from_mosflm_a_star(...):
    # [Copy function body from dbex/nanobrag_bridge.py:801-894 verbatim]
    ...
```

### Import Replacement Pattern (A4 example)
```python
# BEFORE (in dbex/nanobrag_bridge.py):
def derive_u_matrix_from_mosflm_a_star(a_star, ...):
    """Docstring..."""
    # [94 lines of implementation]
    ...

# AFTER:
from dbex.geometry.crystallography import derive_u_matrix_from_mosflm_a_star
```

### Validation Commands (exact)
```bash
# Test NEW locations (Phase 0 test suite)
NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_geometry_current.py
NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_physics_loss_current.py

# Regression guards (production smoke tests)
DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
```

## Pitfalls To Avoid

1. **Circular imports:** DO NOT import from `dbex.nanobrag_bridge` or `dbex.nanobrag_refinement` in new modules (leaf-node constraint)
2. **Logic changes:** DO NOT modify function bodies during extraction (pure code movement only)
3. **Signature changes:** DO NOT change function signatures, parameter names, or return types
4. **Spec compliance:** PRESERVE `V = I_model + sigma^2` detachment in `_compute_variance_weighted_loss` (spec-db-core.md)
5. **Import locations:** UPDATE imports in BOTH `nanobrag_bridge.py` AND `nanobrag_refinement.py` (A4 has 2 sub-steps)
6. **Environment:** USE `NANOBRAGG_DISABLE_COMPILE=1` for all tests (proven stable in Phase 0, avoids CUDA carryover risk)
7. **Device neutrality:** DO NOT add device-specific code (functions are device-agnostic)
8. **Autograd:** DO NOT add/remove `.detach()` calls during code movement (preserve gradient flow)
9. **Coverage:** Phase 0 established ~85-90% manual coverage; code movement should NOT degrade coverage
10. **Regression guards:** BOTH Stage A smoke AND DB-AT-024 must PASS (forward model parity critical)

**Environment:** Assume frozen per POLICY-001. If missing dependencies detected (e.g., import errors), mark blocked with error signature in artifacts; DO NOT attempt to install packages.

## If Blocked

**Import Error (circular dependency):**
- Log error message in `phase_a_decision.md`
- Check if new modules imported from `dbex.nanobrag_*` (violates leaf-node constraint)
- Refactor imports to external deps only, retry validation

**Test Failure (Phase 0 tests):**
- Capture full pytest output in artifact logs
- Compare function signatures in OLD vs NEW locations (must be identical)
- Check for missing imports or typos in module paths
- Document failure mode in `phase_a_decision.md`, Path C/D assessment

**Regression Failure (Stage A smoke, DB-AT-024):**
- Capture full pytest output
- Verify import statements are correct (no missing modules)
- Check call sites in `nanobrag_bridge.py` and `nanobrag_refinement.py` (ensure they import from new modules)
- Document failure in `phase_a_decision.md`, Path B assessment

## Findings Applied (Mandatory)

**Relevant Finding IDs from docs/findings.md:**
- **POLICY-001:** Environment Freeze compliance (test-only + code movement, no package installs, no env modifications)
- **PHYSICS-LOSS-001:** Variance-weighted loss formula (preserve V = I_model + sigma^2 detachment per spec-db-core.md:57-80)
- **GEOMETRY-003:** B_ideal convention (MOSFLM A* = U @ B_ideal reconstruction, validated in Phase 0 tests)
- **GRADIENT-001:** Autograd graph preservation (no .detach() changes during code movement, preserve gradient flow)
- **REFINE-001:** LBFGS scale warm-start patterns (regression guards protect Stage A refinement behavior)

**Adherence Notes:**
- POLICY-001: Code movement only, no production logic changes, no env modifications
- PHYSICS-LOSS-001: `_compute_variance_weighted_loss` extraction preserves variance formula exactly
- GEOMETRY-003: `derive_u_matrix_from_mosflm_a_star` extraction preserves B_ideal convention
- GRADIENT-001: No gradient-related changes (pure code movement)
- REFINE-001: Regression guards (Stage A smoke) validate LBFGS behavior unchanged

## Pointers

**Spec Documents:**
- docs/spec-db-core.md:57-80 — Variance definition (V = I_model + sigma^2)
- docs/spec-db-workflow.md:§7 — Refinement protocol architecture
- docs/spec-db-runtime.md — Device neutrality requirements

**Implementation Plan:**
- plans/active/ARCH-REFACTOR-001/implementation.md:92-106 — Phase A checklist (A1, A3, A4)
- plans/active/ARCH-REFACTOR-001/implementation.md:77-89 — Phase 0 baseline (tests PASSED, manual coverage ~85-90%)

**Code Locations:**
- dbex/nanobrag_bridge.py:801-894 — `derive_u_matrix_from_mosflm_a_star` (SOURCE for A1)
- dbex/nanobrag_refinement.py:447-480 — `_compute_variance_weighted_loss` (SOURCE for A3)

**Test Files:**
- tests/dbex/test_geometry_current.py — Phase 0 geometry tests (2 tests, 1.05s baseline)
- tests/dbex/test_physics_loss_current.py — Phase 0 physics tests (4 tests, 0.82s baseline)
- tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — Stage A regression guard
- tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke — Mapping regression guard

**Fix Plan:**
- docs/fix_plan.md:118-136 — ARCH-REFACTOR-001 status (in_progress, Phase 0 complete, Phase A next)
- docs/fix_plan.md:32-40 — Execution Roadmap Tier 3 (ARCH-REFACTOR-001 highest priority after Tier 2 complete)

**Findings Ledger:**
- docs/findings.md — POLICY-001, PHYSICS-LOSS-001, GEOMETRY-003, GRADIENT-001, REFINE-001

## Next Up (optional, if Phase A finishes early)

**Phase B Planning (Telemetry Standardization):**
- If Phase A completes with Path A (all tests PASS) and time remains, return to Galph for Phase B planning
- Phase B scope: Convert `RefinementTelemetry` to dataclass, implement `to_dict()`, refactor HDF5 serialization
- Estimated effort: 2-3 loops (Phase B is more complex than Phase A)

**Alternative:** Return to Galph for retrospective or focus switch assessment

## Doc Sync Plan

**Conditional (only if tests added/renamed this loop):**
- NOT APPLICABLE for Phase A (no new tests, re-running existing Phase 0 tests against new locations)
- Phase 0 tests remain in `tests/dbex/test_geometry_current.py` and `tests/dbex/test_physics_loss_current.py` (no renames)
- Test registry updates deferred to Phase A completion (docs/TESTING_GUIDE.md §2 already includes Phase 0 test references)

## Mapped Tests Guardrail

**Collection Verification (Phase 0 tests remain valid):**
```bash
# Verify Phase 0 tests still collect (should show 2 geometry + 4 physics = 6 tests total)
pytest --collect-only tests/dbex/test_geometry_current.py tests/dbex/test_physics_loss_current.py
```

**Expected Output:**
- `tests/dbex/test_geometry_current.py::test_derive_u_matrix_roundtrip` (1 test)
- `tests/dbex/test_geometry_current.py::test_derive_u_matrix_identity` (1 test, if authored)
- `tests/dbex/test_physics_loss_current.py` (4 tests: basic clamping, zero mask, zero floor, negative model)

**Hard Gate:** All 6 Phase 0 tests must collect and PASS after Phase A import updates. If any test fails to collect or run, Phase A is BLOCKED (mark in `phase_a_decision.md`).

## Normative Math/Physics

**Variance-Weighted Loss (PHYSICS-LOSS-001):**
- **Normative Source:** docs/spec-db-core.md:57-80 (Variance Definition)
- **Formula:** V = max(I_model + sigma², variance_floor²)
- **Implementation:** `_compute_variance_weighted_loss` in dbex/nanobrag_refinement.py:447-480 (SOURCE)
- **DO NOT paraphrase:** Refer Ralph to spec-db-core.md §Variance Definition for exact semantics

**Crystallographic U-Matrix Derivation (GEOMETRY-003):**
- **Normative Source:** docs/config_crosswalk.md (Crystal Geometry Mapping), MOSFLM convention
- **Formula:** A* = U @ B_ideal (U is rotation from ideal to real orientation)
- **Implementation:** `derive_u_matrix_from_mosflm_a_star` in dbex/nanobrag_bridge.py:801-894 (SOURCE)
- **DO NOT paraphrase:** Refer Ralph to config_crosswalk.md for B_ideal / MOSFLM A* conventions
