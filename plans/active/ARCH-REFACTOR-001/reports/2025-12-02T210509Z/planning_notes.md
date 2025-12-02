# Phase D.3 Planning Notes — Test Harness Migration (Batch 1)

**Initiative:** ARCH-REFACTOR-001 Phase D.3
**Loop:** 2025-12-02T210509Z
**Status:** Planning → ready_for_implementation
**Actor:** Galph (supervisor)

## Context

Phase D.2 (CLI Refactor) completed successfully in commit 46389946:
- `dbex/refine_one.py::run_nanobrag_backend()` migrated from facade to RefinementEngine
- 2/2 CLI selectors PASSED (test_torch_diagnostics_metadata, test_nanobrag_backend_runs_simulator)
- CLI now serves as the canonical Engine adoption reference pattern

Phase D.3 migrates test harness files from `run_nanobrag_refinement()` facade to direct RefinementEngine usage.

## Scope Decision for This Loop

Per test_migration_plan.md, there are 3 file categories (A/B/C) spanning 7 files total:
- **Category A (High Priority):** Full facade consumers requiring Engine pattern (3 files, 8 functions)
- **Category B (Medium Priority):** Config-only imports (3 files, simple path updates)
- **Category C (Low Priority):** Legacy helper imports (1 file, bugfix)

**Decision:** This loop tackles **Category A, File 1 only** (`tests/dbex/test_torch_refine_smoke.py`, 6 functions).

**Rationale:**
1. **Highest risk:** Core Stage A/B/C acceptance tests; failure blocks entire Phase D
2. **Reference pattern validation:** Proves CLI blueprint works for test context
3. **Complexity:** 6 distinct migration patterns (Stage A-only, Stage A+B, Stage A+C, Stage A+B+C, ASU mode, baseline detector)
4. **WIP cap:** Keeps focus bounded; remaining files (2 Category A + 4 Category B/C) deferred to next 1-2 loops

**Out of scope this loop:**
- `test_stage_a_smoke_parity.py` (Category A, File 2)
- `dbex/tools/stage_a_adam.py` (Category A, File 3)
- Config-only imports (Category B, Files 4-6)
- Legacy helper imports (Category C, File 7)

## File 1: tests/dbex/test_torch_refine_smoke.py

**Impact:** 6 test functions
**Lines:** ~2000 (functions span lines 400-1950)
**Risk:** HIGH (Stage validation gates)

### Functions to Migrate

1. **test_stage_a_expansion** (lines 400-540)
   - Current call: `run_nanobrag_refinement()` at line 436
   - Pattern: Stage A only
   - Gate: min_loss_improvement (line 487)

2. **test_stage_a_engine_delegation_telemetry** (lines 749-850)
   - Current call: `run_nanobrag_refinement()` at line 784
   - Pattern: Stage A only
   - Special: Tests Engine delegation telemetry; keep for telemetry validation

3. **test_stage_b_shell_modifiers** (lines 947-1050)
   - Current call: `run_nanobrag_refinement()` at line 983
   - Pattern: Stage A + B (enable_stage_b=True)
   - Gate: Stage B shell modifier convergence (lines 1030-1040)

4. **test_stage_c_detector_microslip** (lines 1063-1200)
   - Current call: `run_nanobrag_refinement()` at line 1103
   - Pattern: Stage A + C (enable_stage_b=False, enable_stage_c=True)
   - Gate: Stage C detector offset convergence (lines 1180-1190)

5. **test_stage_b_asu_mapping_smoke** (lines 1393-1600)
   - Current call: `run_nanobrag_refinement()` at line 1444
   - Pattern: Stage A + B with ASU mode (stage_b_mode="per_reflection", stage_b_enable_asu_mapping=True)
   - Gate: ASU mapping telemetry (lines 1550-1580)

6. **test_stage_c_stage_a_baseline_detector_dist** (lines 1793-1950)
   - Current call: `run_nanobrag_refinement()` at line 1865
   - Pattern: Stage A + C with baseline detector (baseline_detector required for Stage C)
   - Gate: Baseline detector distance telemetry (lines 1920-1940)

### Implementation Strategy

**Per CLI blueprint (cli_refactor_blueprint.md):**

1. **Update imports (top of file):**
   - Remove: `from dbex.nanobrag_refinement import ...` (wherever inline)
   - Add (module scope):
     ```python
     from dbex.refinement.config import RefinementConfig
     from dbex.refinement.engine import RefinementEngine
     from dbex.refinement.stage_a import StageA
     from dbex.refinement.stage_b import StageB
     from dbex.refinement.stage_c import StageC
     from dbex.refinement.context import build_refinement_context
     ```

2. **For each function:**
   - Build `RefinementContext`:
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
         baseline_detector=baseline_detector  # Only for Stage C tests
     )
     ```

   - Instantiate stages list (conditional on config):
     ```python
     stages = [StageA()]
     if refine_config.enable_stage_b:
         stages.append(StageB())
     if refine_config.enable_stage_c:
         stages.append(StageC())
     ```

   - Instantiate and run Engine:
     ```python
     engine = RefinementEngine(stages, config=refine_config)
     telemetry_dict = engine.run({"context": refinement_context})
     ```

   - Extract artifacts:
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

3. **Preserve downstream logic:**
   - All telemetry assertions (e.g., `telemetry_dict["A"]`, `telemetry_dict["B"]`)
   - All gate checks (loss improvements, convergence thresholds)
   - All artifact extractions (ROI metadata, perf counters)

### Validation Plan

**Selectors (6 tests):**
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

**Artifacts:**
- `pytest_smoke_tests_all.log` — Full pytest output for all 6 tests
- `summary.md` — This loop's Turn Summary (per end_of_loop_hygiene)

### Risks & Mitigations

**Risk 1: Telemetry dict key changes**
- Mitigation: Engine uses same "A"/"B"/"C" labels as facade
- Verification: Check assertions like `telemetry_dict["A"]` in each test

**Risk 2: Artifact extraction differences**
- Mitigation: Engine `_artifacts` format matches facade return structure
- Verification: Check `engine_artifacts["stage_a"].bragg_full` access patterns

**Risk 3: Baseline detector handling (test #6)**
- Mitigation: Pass `baseline_detector` arg to `build_refinement_context()` only for Stage C tests
- Verification: Ensure `baseline_detector=None` for Stage A/B-only tests

**Risk 4: Incremental migration complexity**
- Mitigation: Migrate all 6 functions atomically in single commit (avoid partial state)
- Rollback: `git checkout HEAD -- tests/dbex/test_torch_refine_smoke.py` if any test fails

### Expected Metrics

- **Files touched:** 1 (`tests/dbex/test_torch_refine_smoke.py`)
- **Functions migrated:** 6
- **Import updates:** ~6 inline imports → 6 module-scope imports
- **Call sites replaced:** 6 (all `run_nanobrag_refinement()` → Engine pattern)
- **Net lines changed:** Minimal (pattern refactor, not logic change)
- **Tests validated:** 6/6 PASSED

## Next Actions

**This loop (2025-12-02T210509Z):**
- Ralph implements Phase D.3 Batch 1 (File 1 only)
- Validation: 6/6 smoke tests PASSED

**Next loop(s):**
- D.3 Batch 2: Files 2-3 (Category A remaining: parity test + tooling)
- D.3 Batch 3: Files 4-6 (Category B: config-only imports)
- D.4: File 7 (Category C: legacy helper imports)
- D.5: Facade deletion (after all consumers migrated)

## Sign-Off Criteria

Mark implementation.md D.3 **partially complete** when:
- ✅ `test_torch_refine_smoke.py` migrated (6 functions)
- ✅ 6/6 smoke tests PASSED
- ✅ No import errors or behavioral regression
- ✅ Artifacts logged under `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210509Z/`
- ⏸️ Remaining Category A/B/C files deferred to subsequent loops

**Completion note:** Phase D.3 spans multiple loops; this is Batch 1 of 3-4.
