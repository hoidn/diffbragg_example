# ARCH-REFACTOR-001 Phase C.6 Planning Notes
**Loop**: i=430 (Galph)
**Timestamp**: 2025-12-02T190946Z
**Focus**: Delete `stage_b_impl.py` after migrating remaining imports

## Context

Ralph successfully completed Phase C.5 (commit 29978502) in loop i=429:
- Created `dbex/refinement/hkl_utils.py` (361 lines) with ASU/shell utilities
- Inlined `_check_stage_b_baseline_parity` → `StageB._check_baseline_parity()` (140 lines)
- Inlined `_run_stage_b_lbfgs` → `StageB._run_lbfgs()` (207 lines)
- Updated imports in `stage_b.py`, `nanobrag_refinement.py`, and test files
- Tests PASSED: Stage B guard (0.78s), Stage B shell smoke (22.69s)

## Current State Analysis

### `stage_b_impl.py` Status
File still exists (1025 lines) but now only re-exports Stage A helpers:
```python
from dbex.refinement.stage_a_impl import (
    _build_stage_a_context,
    _retarget_stage_a_simulators,
    _get_sigma_floor_sq_tensor,
)
```

All Stage B-specific logic has been moved:
- HKL utilities → `hkl_utils.py`
- Parameter builder → `StageB._build_stage_b_params()`
- LBFGS runner → `StageB._run_lbfgs()`
- Baseline parity → `StageB._check_baseline_parity()`

### Import Dependencies

**`dbex/refinement/stage_b.py` (lines 32-37):**
```python
from dbex.refinement.stage_b_impl import (
    _retarget_stage_a_simulators,
    _get_sigma_floor_sq_tensor,
    _build_stage_a_context,
)
```
These are Stage A helpers; should import from `stage_a_impl` directly.

**`dbex/nanobrag_refinement.py` (lines 67-70):**
```python
from dbex.refinement.stage_b_impl import (
    _build_stage_b_params,
    _run_stage_b_lbfgs,
)
```
Dead code - the facade uses RefinementEngine now, never calls these helpers directly.

**Test files:**
- `tests/dbex/test_stage_b_cpu_fallback.py` may patch `stage_b_impl._build_stage_b_params`
- `tests/dbex/test_stage_b_asu_mapping.py` already updated to use `hkl_utils`

## Phase C.6 Scope

### Tasks
1. Update `stage_b.py` to import Stage A helpers from `stage_a_impl`
2. Remove dead imports from `nanobrag_refinement.py`
3. Check and update test patches if needed
4. Delete `stage_b_impl.py` (and `.backup` if exists)
5. Validate via Stage B guard + shell smoke tests

### Exit Criteria
- `dbex/refinement/stage_b_impl.py` deleted
- All imports resolve correctly (`python -c "from dbex.refinement import stage_b"`)
- Stage B guard test PASSES
- Stage B shell smoke test PASSES
- No import errors or behavioral regressions

## Risk Assessment
**Low Risk**: This is purely import refactoring with no logic changes. The Stage A helpers are already proven stable and correctly sourced from `stage_a_impl.py`.

## Artifacts
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T190946Z/pytest_stage_b_guard.log`
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T190946Z/pytest_stage_b_shell.log`
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T190946Z/remaining_imports.txt`

## Next Steps After C.6
- Mark Phase C (Stage B consolidation) complete
- Plan Phase C.7–C.9 (Stage A consolidation using same pattern)
- Prepare for Phase D (Facade Removal)
