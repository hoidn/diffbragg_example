# Input for Ralph — ARCH-REFACTOR-001 Phase D.3 (Batch 1)

## Summary
Migrate `tests/dbex/test_torch_refine_smoke.py` (6 test functions) from `run_nanobrag_refinement()` facade to direct RefinementEngine instantiation following CLI refactor blueprint pattern.

## Mode
Parity

## InitiativeType
architecture

## Focus
ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation (Phase D.3: Test Harness Migration, Batch 1)

## Branch
integration

## Mapped tests
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_asu_mapping_smoke \
  tests/dbex/test_torch_refine_smoke.py::test_stage_c_stage_a_baseline_detector_dist \
  --smoke-detector-size=small
```
Expected: All 6/6 tests PASSED

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210509Z/`
- `pytest_smoke_tests_all.log` — Full pytest output for all 6 smoke tests
- `summary.md` — Turn summary (prepend to existing file if present)

---

## Do Now

**Objective:** Migrate `tests/dbex/test_torch_refine_smoke.py` (6 test functions) from facade pattern to direct RefinementEngine pattern, following `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/cli_refactor_blueprint.md` as the reference implementation.

**Critical:** This is the highest-risk migration (core Stage A/B/C acceptance tests). All 6 functions must be migrated atomically in a single commit to avoid partial state. If any test fails, rollback entire file.

### Step 1: Update Module-Scope Imports

**File:** `tests/dbex/test_torch_refine_smoke.py`

**Action:** Add these imports near the top of the file (after existing imports, before first test function):

```python
from dbex.refinement.config import RefinementConfig
from dbex.refinement.engine import RefinementEngine
from dbex.refinement.stage_a import StageA
from dbex.refinement.stage_b import StageB
from dbex.refinement.stage_c import StageC
from dbex.refinement.context import build_refinement_context
```

**Note:** Remove any inline `from dbex.nanobrag_refinement import ...` statements in each test function as you migrate them (Step 2).

### Step 2: Migrate Each Test Function

For each of the 6 functions below, follow this pattern (based on CLI refactor blueprint):

1. **Remove inline facade import** (e.g., `from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig`)
2. **Build RefinementContext** (before facade call site):
   ```python
   refinement_context = build_refinement_context(
       inputs=refinement_inputs,
       detector=dataload.detector,
       beam=dataload.beam,
       crystal=dataload.crystal,
       hkl_grid=hkl_grid,
       hkl_metadata=hkl_metadata,
       config=refine_config,
       job_context=job_context,
       baseline_detector=baseline_detector  # Only for Stage C tests (functions 4, 6)
   )
   ```
   **Note:** For Stage A/B-only tests (functions 1, 2, 3, 5), omit `baseline_detector` argument or pass `baseline_detector=None`.

3. **Instantiate stages list** (conditional on config flags):
   ```python
   stages = [StageA()]
   if refine_config.enable_stage_b:
       stages.append(StageB())
   if refine_config.enable_stage_c:
       stages.append(StageC())
   ```

4. **Instantiate and run Engine**:
   ```python
   engine = RefinementEngine(stages, config=refine_config)
   telemetry_dict = engine.run({"context": refinement_context})
   ```

5. **Extract artifacts**:
   ```python
   engine_artifacts = engine._artifacts
   # Terminal stage Bragg (precedence: C > B > A)
   if "stage_c" in engine_artifacts:
       bragg_refined = engine_artifacts["stage_c"].bragg_full
   elif "stage_b" in engine_artifacts:
       bragg_refined = engine_artifacts["stage_b"].bragg_full
   else:
       bragg_refined = engine_artifacts["stage_a"].bragg_full
   ```

6. **Preserve all downstream logic unchanged:**
   - Telemetry assertions (e.g., `telemetry_dict["A"]`, `telemetry_dict["B"]`, `telemetry_dict["C"]`)
   - Gate checks (loss improvements, convergence thresholds)
   - Artifact extractions (ROI metadata, perf counters)
   - Comments and docstrings

---

#### Function 1: test_stage_a_expansion (~lines 400-540)

**Current call site:** Line ~436: `Bragg_refined, refine_telemetry_dict, _ = run_nanobrag_refinement(...)`

**Migration:**
- **Pattern:** Stage A only (no Stage B/C)
- **baseline_detector:** None (omit or pass None)
- **Stages list:** `[StageA()]`
- **Downstream:** Preserve gate at line ~487 (min_loss_improvement assertion)

**Example snippet:**
```python
# Before (line ~436):
Bragg_refined, refine_telemetry_dict, _ = run_nanobrag_refinement(
    inputs=refinement_inputs,
    detector=dataload.detector,
    beam=dataload.beam,
    crystal=dataload.crystal,
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    config=refine_config,
    job_context=job_context
)

# After (replace with):
refinement_context = build_refinement_context(
    inputs=refinement_inputs,
    detector=dataload.detector,
    beam=dataload.beam,
    crystal=dataload.crystal,
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    config=refine_config,
    job_context=job_context
)
stages = [StageA()]
engine = RefinementEngine(stages, config=refine_config)
telemetry_dict = engine.run({"context": refinement_context})
refine_telemetry_dict = telemetry_dict  # Alias for downstream compatibility
engine_artifacts = engine._artifacts
bragg_refined = engine_artifacts["stage_a"].bragg_full
Bragg_refined = bragg_refined  # Alias for downstream compatibility
```

---

#### Function 2: test_stage_a_engine_delegation_telemetry (~lines 749-850)

**Current call site:** Line ~784: `Bragg_refined, refine_telemetry_dict, _ = run_nanobrag_refinement(...)`

**Migration:**
- **Pattern:** Stage A only
- **baseline_detector:** None
- **Stages list:** `[StageA()]`
- **Special:** Tests Engine delegation telemetry; keep test as-is for telemetry validation

---

#### Function 3: test_stage_b_shell_modifiers (~lines 947-1050)

**Current call site:** Line ~983: `Bragg_refined, refine_telemetry_dict, _ = run_nanobrag_refinement(...)`

**Migration:**
- **Pattern:** Stage A + B (enable_stage_b=True)
- **baseline_detector:** None
- **Stages list:** `[StageA(), StageB()]` (conditional on `refine_config.enable_stage_b`)
- **Bragg extraction:** `engine_artifacts["stage_b"].bragg_full` (Stage B terminal)
- **Downstream:** Preserve gates at lines ~1030-1040 (shell modifier convergence)

---

#### Function 4: test_stage_c_detector_microslip (~lines 1063-1200)

**Current call site:** Line ~1103: `Bragg_refined, refine_telemetry_dict, _ = run_nanobrag_refinement(...)`

**Migration:**
- **Pattern:** Stage A + C (enable_stage_b=False, enable_stage_c=True)
- **baseline_detector:** Required for Stage C (pass `dataload.detector` or appropriate baseline)
- **Stages list:** `[StageA(), StageC()]` (note: Stage B disabled in this test)
- **Bragg extraction:** `engine_artifacts["stage_c"].bragg_full` (Stage C terminal)
- **Downstream:** Preserve gates at lines ~1180-1190 (detector offset convergence)

**Important:** Inspect the test to find where `baseline_detector` is defined (likely from `dataload.detector` or a fixture). Pass it to `build_refinement_context()`.

---

#### Function 5: test_stage_b_asu_mapping_smoke (~lines 1393-1600)

**Current call site:** Line ~1444: `Bragg_refined, refine_telemetry_dict, _ = run_nanobrag_refinement(...)`

**Migration:**
- **Pattern:** Stage A + B with ASU mode (stage_b_mode="per_reflection", stage_b_enable_asu_mapping=True)
- **baseline_detector:** None
- **Stages list:** `[StageA(), StageB()]`
- **Bragg extraction:** `engine_artifacts["stage_b"].bragg_full`
- **Downstream:** Preserve gates at lines ~1550-1580 (ASU mapping telemetry assertions)

---

#### Function 6: test_stage_c_stage_a_baseline_detector_dist (~lines 1793-1950)

**Current call site:** Line ~1865: `Bragg_refined, refine_telemetry_dict, _ = run_nanobrag_refinement(...)`

**Migration:**
- **Pattern:** Stage A + C with baseline detector
- **baseline_detector:** Required (inspect test for definition, likely `refgeom_dataload.Expt.detector` or similar)
- **Stages list:** `[StageA(), StageC()]`
- **Bragg extraction:** `engine_artifacts["stage_c"].bragg_full`
- **Downstream:** Preserve gates at lines ~1920-1940 (baseline detector distance telemetry)

---

### Step 3: Validation

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_asu_mapping_smoke \
  tests/dbex/test_torch_refine_smoke.py::test_stage_c_stage_a_baseline_detector_dist \
  --smoke-detector-size=small \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210509Z/pytest_smoke_tests_all.log
```

**Gate:** All 6/6 tests PASSED

**If any test fails:**
1. Inspect failure signature in pytest log
2. Verify Engine pattern matches CLI blueprint exactly
3. Check telemetry dict key access (`telemetry_dict["A"]` etc.)
4. Check artifact extraction (`engine_artifacts["stage_a"].bragg_full` etc.)
5. If >2 attempts needed, capture failure evidence in artifacts and mark blocked in fix_plan

**Rollback plan:** `git checkout HEAD -- tests/dbex/test_torch_refine_smoke.py` if migration fails

### Step 4: Commit

**Message template:**
```
ARCH-REFACTOR-001 Phase D.3 Batch 1: Migrate test_torch_refine_smoke.py to RefinementEngine (tests: 6/6 pass)

Migrated tests/dbex/test_torch_refine_smoke.py (6 test functions) from run_nanobrag_refinement
facade to direct RefinementEngine instantiation following CLI refactor blueprint.

Functions migrated:
- test_stage_a_expansion (Stage A only)
- test_stage_a_engine_delegation_telemetry (Stage A only)
- test_stage_b_shell_modifiers (Stage A + B)
- test_stage_c_detector_microslip (Stage A + C)
- test_stage_b_asu_mapping_smoke (Stage A + B ASU mode)
- test_stage_c_stage_a_baseline_detector_dist (Stage A + C baseline detector)

Implementation:
- Added module-scope imports (RefinementEngine, StageA/B/C, build_refinement_context)
- Built RefinementContext for each test (baseline_detector conditional on Stage C)
- Instantiated stages list based on config.enable_stage_b/c flags
- Ran engine.run({"context": ...}) and extracted artifacts from engine._artifacts
- Preserved all downstream logic (telemetry assertions, gates, perf counters)

Tests: 6/6 smoke selectors PASSED
- test_stage_a_expansion
- test_stage_a_engine_delegation_telemetry
- test_stage_b_shell_modifiers
- test_stage_c_detector_microslip
- test_stage_b_asu_mapping_smoke
- test_stage_c_stage_a_baseline_detector_dist

Metrics: 1 file touched, 6 call sites replaced (facade → Engine), no behavioral regression
Phase D.3 Batch 1 complete; remaining test files deferred to next loop(s).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Pitfalls To Avoid

1. **Device/dtype neutrality:** Engine pattern already handles this via `RefinementConfig`; do not hardcode device strings or dtype conversions.

2. **Telemetry dict keys:** Engine uses same "A"/"B"/"C" labels as facade; ensure downstream assertions like `telemetry_dict["A"]` remain unchanged.

3. **Artifact extraction:** Use `engine._artifacts["stage_a"].bragg_full` (not `bragg_refined` from facade return tuple). Terminal stage precedence: C > B > A.

4. **baseline_detector handling:** Only pass `baseline_detector` to `build_refinement_context()` for Stage C tests (functions 4, 6). Omit or pass `None` for Stage A/B-only tests.

5. **Partial migration:** Do NOT migrate functions incrementally across multiple commits; all 6 must be migrated atomically to avoid test suite breakage.

6. **Downstream logic preservation:** Do NOT change any telemetry assertions, gate checks, or artifact extractions beyond the facade → Engine pattern replacement.

7. **Environment Freeze:** Do not install/upgrade packages. If an import fails, mark blocked.

8. **Initiative type boundaries:** This is an architecture initiative; do not change test semantics, acceptance criteria, or gates (spec_change requires separate initiative).

9. **Test collection:** After migration, run `pytest --collect-only tests/dbex/test_torch_refine_smoke.py` to verify all 6 tests are discovered.

10. **Rollback readiness:** If >1 test fails after migration, rollback entire file and capture failure evidence before re-attempting.

---

## If Blocked

**Scenario 1: Import errors**
- Verify module-scope imports are spelled correctly
- Check that `build_refinement_context` is imported from `dbex.refinement.context`
- Capture import traceback in artifacts, mark blocked in fix_plan

**Scenario 2: Telemetry structure mismatch**
- Verify Engine uses "A"/"B"/"C" labels (inspect `engine.run()` return value)
- Check CLI refactor blueprint for reference telemetry structure
- Capture telemetry diff in artifacts, mark blocked

**Scenario 3: Artifact extraction failure**
- Verify `engine._artifacts` contains expected stage keys ("stage_a", "stage_b", "stage_c")
- Check terminal stage precedence logic (C > B > A)
- Capture artifact structure in artifacts, mark blocked

**Scenario 4: baseline_detector undefined**
- Inspect test to find where `baseline_detector` is defined (likely from DataLoad fixture or explicit setup)
- Pass to `build_refinement_context()` only for Stage C tests
- Capture variable scope in artifacts, mark blocked

**Fallback:** Capture all evidence (pytest logs, tracebacks, variable dumps) in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210509Z/`, update Attempts History in `docs/fix_plan.md`, and switch focus per loop_discipline.

---

## Findings Applied

**Relevant findings from `docs/findings.md`:**

- **ARCH-REFACTOR-001 Phase D reference:** CLI refactor blueprint (`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/cli_refactor_blueprint.md`) establishes the canonical Engine adoption pattern.
- **Test migration plan:** Category A, File 1 scope defined in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/test_migration_plan.md` (lines 24-123).
- **Initiative type: architecture:** Per ARCH-REFACTOR-001, this work does NOT change external behavior, specs, or acceptance gates; purely structural refactor from facade to Engine.
- **Environment Freeze:** Runtime is pre-provisioned; do not install/upgrade packages during loops.

---

## Pointers

**Reference documents:**
- CLI refactor blueprint: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/cli_refactor_blueprint.md`
- Test migration plan: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/test_migration_plan.md`
- Implementation plan: `plans/active/ARCH-REFACTOR-001/implementation.md` (lines 365-395)
- Fix plan ledger: `docs/fix_plan.md` (lines 52-88, ARCH-REFACTOR-001 Attempts History)

**Spec/arch references:**
- Workflow spec: `docs/spec-db-workflow.md` §§30-41 (Engine protocol)
- Context contracts: `docs/architecture/dbex/refinement/context.idl.md`
- Testing guide: `docs/TESTING_GUIDE.md` (selectors, env flags)

**Code pointers:**
- Target file: `tests/dbex/test_torch_refine_smoke.py`
- Reference implementation: `dbex/refine_one.py::run_nanobrag_backend()` (lines 505-595, commit 46389946)
- Engine class: `dbex/refinement/engine.py::RefinementEngine`
- Context builder: `dbex/refinement/context.py::build_refinement_context()`
- Stage classes: `dbex/refinement/stage_a.py::StageA`, `stage_b.py::StageB`, `stage_c.py::StageC`

---

## Next Up

**After this loop (D.3 Batch 1 complete):**
1. Phase D.3 Batch 2: Migrate `test_stage_a_smoke_parity.py` (1 function) + `dbex/tools/stage_a_adam.py` (1 function)
2. Phase D.3 Batch 3: Config-only import updates (3 files: `test_refinement_engine.py`, `test_stage_b_cpu_fallback.py`, `refinement/__init__.py`)
3. Phase D.4: Legacy helper import fix (`test_physics_loss_current.py`, 4 inline imports → `dbex.physics.loss`)
4. Phase D.5: Facade deletion after all consumers migrated

**Sign-off:** Mark implementation.md D.3 **partially complete** (Batch 1 of 3-4), proceed to D.3 Batch 2 next loop.

---

## Doc Sync Plan

**Not applicable this loop** (no new tests added/renamed; existing tests migrated to Engine pattern).

**Note:** If any test selector changes, update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` in a follow-up docs-only loop.

---

## Mapped Tests Guardrail

All 6 mapped selectors already exist and collect >0:
- `test_stage_a_expansion`
- `test_stage_a_engine_delegation_telemetry`
- `test_stage_b_shell_modifiers`
- `test_stage_c_detector_microslip`
- `test_stage_b_asu_mapping_smoke`
- `test_stage_c_stage_a_baseline_detector_dist`

Verified via pytest collection in CLI refactor loop (Phase D.2). No new tests authored this loop.
