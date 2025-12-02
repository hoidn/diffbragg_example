# Phase D.3/D.4: Test Harness Migration Plan

**Initiative:** ARCH-REFACTOR-001 Phase D.3 + D.4
**Date:** 2025-12-02T201539Z
**Status:** Planning

## Objective

Migrate all test files from `run_nanobrag_refinement()` facade to `RefinementEngine` pattern, following the CLI refactor blueprint (Phase D.2) as the reference implementation.

## Test Consumer Categories

### Category A: Full Facade Consumers (HIGH Priority)
Tests that call `run_nanobrag_refinement()` and must migrate to Engine pattern.

### Category B: Config-Only Imports (MEDIUM Priority)
Tests that only import `RefinementConfig` dataclass.

### Category C: Legacy Helper Imports (LOW Priority)
Tests that import helpers already relocated to canonical modules.

---

## Category A: Full Facade Consumers

### File 1: tests/dbex/test_torch_refine_smoke.py

**Impact:** 6 test functions (core acceptance tests)
**Risk:** HIGH (these are Stage A/B/C validation gates)

#### Function-by-Function Migration Strategy

**1. test_stage_a_expansion (lines 400-540)**
- **Current:** `run_nanobrag_refinement()` call at line 436
- **Migration Pattern:** Follow CLI blueprint (D.2)
  * Import: Add `RefinementEngine, StageA` from `dbex.refinement.*`
  * Context: Use existing `refinement_inputs` + `build_refinement_context()`
  * Engine: `engine = RefinementEngine([StageA()], config=config)`
  * Run: `telemetry_dict = engine.run({"context": refinement_context})`
  * Artifacts: `engine_artifacts = engine._artifacts`
  * Bragg: `bragg_refined = engine_artifacts["stage_a"].bragg_full`
- **Validation:** Gate at line 487 (min_loss_improvement) must still pass
- **Selector:** `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small`

**2. test_stage_a_engine_delegation_telemetry (lines 749-850)**
- **Current:** `run_nanobrag_refinement()` call at line 784
- **Migration Pattern:** Same as (1)
- **Special consideration:** Tests Engine delegation telemetry; migration makes this test redundant (Engine is now direct path)
  * Option A: Keep test, assert Engine telemetry format
  * Option B: Deprecate test (Engine delegation is now default)
  * **Recommendation:** Option A (keep for telemetry validation)
- **Selector:** `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry`

**3. test_stage_b_shell_modifiers (lines 947-1050)**
- **Current:** `run_nanobrag_refinement()` call at line 983
- **Migration Pattern:** Follow CLI blueprint with Stage B enabled
  * Engine: `engine = RefinementEngine([StageA(), StageB()], config=config)`
  * Bragg: `bragg_refined = engine_artifacts["stage_b"].bragg_full` (Stage B terminal)
- **Validation:** Stage B gates at lines 1030-1040 (shell modifier convergence)
- **Selector:** `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small`

**4. test_stage_c_detector_microslip (lines 1063-1200)**
- **Current:** `run_nanobrag_refinement()` call at line 1103
- **Migration Pattern:** Follow CLI blueprint with Stage C enabled
  * Engine: `engine = RefinementEngine([StageA(), StageB(), StageC()], config=config)`
  * Note: Stage B disabled in this test (config.enable_stage_b=False); Engine: `[StageA(), StageC()]`
  * Bragg: `bragg_refined = engine_artifacts["stage_c"].bragg_full` (Stage C terminal)
- **Validation:** Stage C gates at lines 1180-1190 (detector offset convergence)
- **Selector:** `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small`

**5. test_stage_b_asu_mapping_smoke (lines 1393-1600)**
- **Current:** `run_nanobrag_refinement()` call at line 1444
- **Migration Pattern:** Follow CLI blueprint with Stage B ASU mode
  * Config: `stage_b_mode="per_reflection"`, `stage_b_enable_asu_mapping=True`
  * Engine: `engine = RefinementEngine([StageA(), StageB()], config=config)`
- **Validation:** ASU mapping telemetry at lines 1550-1580
- **Selector:** `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_asu_mapping_smoke`

**6. test_stage_c_stage_a_baseline_detector_dist (lines 1793-1950)**
- **Current:** `run_nanobrag_refinement()` call at line 1865
- **Migration Pattern:** Follow CLI blueprint with Stage C + baseline detector
  * Context: `baseline_detector=refgeom_dataload.Expt.detector` (required for Stage C)
  * Engine: `engine = RefinementEngine([StageA(), StageC()], config=config)`
- **Validation:** Baseline detector distance telemetry at lines 1920-1940
- **Selector:** `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_stage_a_baseline_detector_dist`

#### Implementation Steps (test_torch_refine_smoke.py)

1. **Update imports (top of file, after existing imports):**
   ```python
   from dbex.refinement.config import RefinementConfig
   from dbex.refinement.engine import RefinementEngine
   from dbex.refinement.stage_a import StageA
   from dbex.refinement.stage_b import StageB
   from dbex.refinement.stage_c import StageC
   from dbex.refinement.context import build_refinement_context
   ```

2. **For each function (1-6):**
   - Replace inline `from dbex.nanobrag_refinement import ...` with imports from step 1
   - Build `RefinementContext` using `build_refinement_context()`
   - Instantiate stages list based on `config.enable_stage_b`/`enable_stage_c`
   - Instantiate `RefinementEngine(stages, config)`
   - Run: `telemetry_dict = engine.run({"context": refinement_context})`
   - Extract artifacts: `engine_artifacts = engine._artifacts`
   - Extract final Bragg from terminal stage (same precedence as CLI: C > B > A)

3. **Validation:**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
                tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry \
                tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
                tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
                tests/dbex/test_torch_refine_smoke.py::test_stage_b_asu_mapping_smoke \
                tests/dbex/test_torch_refine_smoke.py::test_stage_c_stage_a_baseline_detector_dist \
     --smoke-detector-size=small \
     | tee plans/active/ARCH-REFACTOR-001/reports/<timestamp>/pytest_smoke_tests_all.log
   ```

   **Gate:** All 6/6 tests PASSED

### File 2: tests/dbex/test_stage_a_smoke_parity.py

**Impact:** 1 test function (`test_stage_a_mapping_to_refine_roundtrip`)
**Risk:** MEDIUM (parity validation)

#### Migration Strategy

**Function: test_stage_a_mapping_to_refine_roundtrip (lines 13-200)**
- **Current:** Imports `run_nanobrag_refinement, RefinementConfig` at line 13
- **Call site:** Line 148
- **Migration Pattern:** Follow CLI blueprint (Stage A only)
  * Import: Update to `RefinementEngine, StageA, RefinementConfig` from canonical modules
  * Engine: `engine = RefinementEngine([StageA()], config=config)`
- **Special consideration:** Also imports `build_structure_factor_grid` from `nanobrag_bridge` (line 10)
  * This is correct; `build_structure_factor_grid` was NOT moved (still in bridge)
  * No change needed for that import

#### Implementation Steps

1. **Update imports (line 13):**
   ```python
   # Before:
   from dbex.nanobrag_refinement import (
       RefinementConfig,
       run_nanobrag_refinement,
   )

   # After:
   from dbex.refinement.config import RefinementConfig
   from dbex.refinement.engine import RefinementEngine
   from dbex.refinement.stage_a import StageA
   from dbex.refinement.context import build_refinement_context
   ```

2. **Update call site (line 148):**
   - Build `RefinementContext` (before facade call)
   - Replace `run_nanobrag_refinement(...)` with Engine pattern
   - Extract artifacts: `bragg_final = engine._artifacts["stage_a"].bragg_full`

3. **Validation:**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_mapping_to_refine_roundtrip \
     | tee plans/active/ARCH-REFACTOR-001/reports/<timestamp>/pytest_parity.log
   ```

   **Gate:** Test PASSED

### File 3: dbex/tools/stage_a_adam.py (Tooling)

**Impact:** 1 function (`run_debug_refinement()`)
**Risk:** LOW (debug tooling, not production)

#### Migration Strategy

**Function: run_debug_refinement() (lines 1634-1700)**
- **Current:** Multi-line import at line 1634 including `run_nanobrag_refinement, RefinementConfig`, quaternion helpers
- **Call site:** Line 1684
- **Migration Pattern:** Follow CLI blueprint (Stage A only)

#### Implementation Steps

1. **Update imports (lines 1634-1650):**
   ```python
   # Before:
   from dbex.nanobrag_refinement import (
       RefinementConfig,
       run_nanobrag_refinement,
       vec_to_unit_quaternion,
       quaternion_to_rotation_matrix,
       quaternion_to_xyz_euler,
   )

   # After:
   from dbex.refinement.config import RefinementConfig
   from dbex.refinement.engine import RefinementEngine
   from dbex.refinement.stage_a import StageA
   from dbex.refinement.context import build_refinement_context
   from dbex.refinement.stage_a_utils import (
       vec_to_unit_quaternion,
       quaternion_to_rotation_matrix,
       quaternion_to_xyz_euler,
   )
   ```

2. **Update call site (line 1684):**
   - Build `RefinementContext`
   - Replace facade call with Engine pattern
   - Extract telemetry: `telemetry = telemetry_dict["A"]` (Stage A label)

3. **Validation:**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_stage_a_adam_tooling.py \
     | tee plans/active/ARCH-REFACTOR-001/reports/<timestamp>/pytest_adam_tooling.log
   ```

   **Gate:** 8/9 tests PASSED (1 known signature mismatch documented in test file)

---

## Category B: Config-Only Imports

### File 4: tests/dbex/test_refinement_engine.py

**Impact:** 2 inline imports (lines 31, 148)
**Risk:** LOW (no facade dependency)

#### Migration Strategy

**Functions:**
- `test_refinement_engine_instantiation` (line 31)
- `test_engine_stage_ordering` (line 148)

**Migration:** Simple import path update

```python
# Before:
from dbex.nanobrag_refinement import RefinementConfig

# After:
from dbex.refinement.config import RefinementConfig
```

**Validation:**
```bash
pytest -vv tests/dbex/test_refinement_engine.py \
  | tee plans/active/ARCH-REFACTOR-001/reports/<timestamp>/pytest_engine.log
```

**Gate:** 2/2 tests PASSED

### File 5: tests/dbex/test_stage_b_cpu_fallback.py

**Impact:** 3 inline imports (lines 40, 183, 291)
**Risk:** LOW (no facade dependency)

#### Migration Strategy

**Functions:**
- `test_stage_b_baseline_guard_diff_payload` (line 40)
- `test_stage_b_full_eval_on_cpu_smoke` (line 183)
- `test_stage_b_cpu_fallback_guard` (line 291)

**Migration:** Simple import path update (same as File 4)

**Validation:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload \
  | tee plans/active/ARCH-REFACTOR-001/reports/<timestamp>/pytest_stage_b_guard.log
```

**Gate:** 1/1 test PASSED (other tests may remain skipped/xfail per test file status)

### File 6: dbex/refinement/__init__.py

**Impact:** 1 conditional import (line 15)
**Risk:** LOW (module export)

#### Migration Strategy

**Before:**
```python
try:
    from dbex.nanobrag_refinement import RefinementConfig
except ImportError:
    pass
```

**After:**
```python
try:
    from dbex.refinement.config import RefinementConfig
except ImportError:
    pass
```

**Validation:**
```bash
python -c "from dbex.refinement import RefinementConfig; print('OK')"
```

**Gate:** No ImportError

---

## Category C: Legacy Helper Imports

### File 7: tests/dbex/test_physics_loss_current.py

**Impact:** 4 inline imports (lines 63, 125, 160, 207)
**Risk:** LOW (helper import fix)
**BUG:** Importing `_compute_variance_weighted_loss` from facade (should be from `dbex.physics.loss`)

#### Migration Strategy

**Functions:**
- `test_variance_weighted_loss_sigma_floor` (line 63)
- `test_variance_weighted_loss_zero_mask` (line 125)
- `test_variance_weighted_loss_zero_floor` (line 160)
- `test_variance_weighted_loss_negative_model` (line 207)

**Migration:** Redirect to canonical module

```python
# Before (WRONG):
from dbex.nanobrag_refinement import _compute_variance_weighted_loss

# After (CORRECT):
from dbex.physics.loss import _compute_variance_weighted_loss
```

**Rationale:** Phase A.3 relocated this function; facade re-exports it temporarily.

**Validation:**
```bash
pytest -vv tests/dbex/test_physics_loss_current.py \
  | tee plans/active/ARCH-REFACTOR-001/reports/<timestamp>/pytest_physics_loss.log
```

**Gate:** 4/4 tests PASSED

---

## Sequencing & Dependencies

### Phase D.1 (Config Migration) → Phase D.2 (CLI) → Phase D.3 (Test Harness)

**Order:**
1. D.1: Create `dbex/refinement/config.py` and update config-only imports (Files 4-6)
2. D.2: Migrate CLI (`dbex/refine_one.py`) to Engine pattern
3. D.3: Migrate test harness (Files 1-3) using CLI as reference
4. D.4: Fix legacy helper imports (File 7)

### Parallelization Opportunities

**Can run in parallel:**
- Category B (Files 4-6) + Category C (File 7) after D.1 completes
- Category A (Files 1-3) are sequential (validate incrementally)

**Critical path:**
1. D.1 (Config) → Unblocks all
2. D.2 (CLI) → Provides reference pattern for D.3
3. D.3 (Test Harness) → Validates Engine pattern across all Stage combinations

---

## Comprehensive Validation Gate

**After all migrations complete:**

```bash
# Full test suite (all Phase D-touched files)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_torch_refine_smoke.py \
  tests/dbex/test_stage_a_smoke_parity.py \
  tests/dbex/test_refinement_engine.py \
  tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload \
  tests/dbex/test_physics_loss_current.py \
  tests/dbex/test_stage_a_adam_tooling.py \
  --smoke-detector-size=small \
  | tee plans/active/ARCH-REFACTOR-001/reports/<timestamp>/pytest_phase_d_full.log
```

**Expected:** All tests PASSED (except documented xfail/skip)

**Metrics:**
- Files touched: 7
- Functions migrated: 14
- Import updates: ~20 inline imports
- Engine pattern adopted: 9 call sites (1 CLI + 8 tests)

---

## Risk Mitigation

### High-Risk Items

1. **test_torch_refine_smoke.py (6 functions):** Core acceptance tests
   - Mitigation: Migrate incrementally (1 function at a time), validate each before proceeding
   - Rollback: Git stash/revert per function if gate fails

2. **Telemetry dict key changes:** Tests assert on telemetry structure
   - Mitigation: Engine uses same "A"/"B"/"C" labels as facade
   - Validation: Check assertions at end of each test function

3. **Artifact extraction differences:** Tests assert on artifact fields
   - Mitigation: Engine `_artifacts` format matches facade return
   - Validation: Check `engine_artifacts["stage_a"].bragg_full` access patterns

### Medium-Risk Items

1. **stage_a_adam.py tooling:** External CLI used by researchers
   - Mitigation: Keep backward compatibility; update imports only
   - Validation: Run existing test suite (test_stage_a_adam_tooling.py)

### Low-Risk Items

1. **Config-only imports (Files 4-6):** No logic changes
2. **Legacy helper imports (File 7):** Pure import path fix

---

## Success Criteria

Phase D.3 + D.4 are **complete** when:
1. ✅ All 7 files updated (imports + call sites)
2. ✅ Full test suite PASSED (15+ tests across all files)
3. ✅ No facade calls remaining (excluding docs/logs/archive)
4. ✅ Engine pattern adopted consistently (follow CLI blueprint)
5. ✅ Telemetry dict structure preserved ("A"/"B"/"C" labels)
6. ✅ Artifact extraction working (bragg_full from terminal stage)
7. ✅ Collection check: `pytest --collect-only` discovers all tests
8. ✅ Artifacts logged under D.3/D.4 implementation reports directories

**Sign-off:** Mark implementation.md Phase D.3/D.4 checklist items complete; proceed to D.5 (Facade Deletion).
