# Input for Ralph — ARCH-REFACTOR-001 Phase D.3 Batch 2 (test_stage_a_smoke_parity.py migration)

## Summary
Migrate test_stage_a_smoke_parity.py fixture from run_nanobrag_refinement facade to direct RefinementEngine usage.

## Mode
Parity

## InitiativeType
architecture

## Focus
ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation (Phase D.3 Batch 2: test_stage_a_smoke_parity.py migration)

## Branch
integration

## Mapped tests
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity \
              tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity \
              --smoke-detector-size=small
```
Expected: 2/2 tests PASSED

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z/`
- `pytest_parity_batch2.log` — Full pytest output for both tests
- `import_verification.txt` — Confirm zero facade imports in this file
- `summary.md` — Turn summary (prepend to existing file if present)

---

## Do Now

**Context**: Phase D.4 import cleanup complete (commit fcc53a33, 4/4 tests PASSED). Proceeding with D.3 Batch 2 test migration to eliminate facade usage in test_stage_a_smoke_parity.py.

**Goal**: Migrate `stage_a_smoke_result` fixture (lines 68-269) from `run_nanobrag_refinement` facade to direct `RefinementEngine` usage following the D.2 CLI blueprint 5-step pattern.

**Why**: This file is one of 3 remaining facade consumers. Completing D.3 Batch 2 leaves only 2 files blocking facade deletion (D.5): test_torch_refine_smoke.py (dead import cleanup) and dbex/tools/stage_a_adam.py (Batch 3).

---

### Step 1: Read Current File

Read `tests/dbex/test_stage_a_smoke_parity.py` to confirm current structure.

**Expected findings**:
- Lines 13-16: Facade imports (RefinementConfig, run_nanobrag_refinement)
- Lines 68-269: Fixture `stage_a_smoke_result`
- Line 148: Facade call `bragg_final, telemetry_dict, _ = run_nanobrag_refinement(...)`
- Lines 296, 376: Test functions consuming the fixture

---

### Step 2: Update Imports

**File**: `tests/dbex/test_stage_a_smoke_parity.py`

**Old string** (lines 13-16):
```python
from dbex.nanobrag_refinement import (
    RefinementConfig,
    run_nanobrag_refinement,
)
```

**New string**:
```python
from dbex.refinement.config import RefinementConfig
from dbex.refinement.context import build_refinement_context
from dbex.refinement.engine import RefinementEngine
from dbex.refinement.stage_a import StageA
```

**Rationale**: Replace facade imports with Engine pattern imports per D.2 CLI blueprint.

---

### Step 3: Migrate Fixture to Engine Pattern

**File**: `tests/dbex/test_stage_a_smoke_parity.py`

**Old string** (lines 147-160, includes comment + facade call + telemetry extraction):
```python
    # ARCH-STAGE-CONTEXT-001 Phase B.4: run_nanobrag_refinement now returns artifacts
    bragg_final, telemetry_dict, _ = run_nanobrag_refinement(
        inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,
    )

    telemetry = telemetry_dict["A"]
```

**New string**:
```python
    # ARCH-REFACTOR-001 Phase D.3 Batch 2: Direct RefinementEngine usage
    refinement_context = build_refinement_context(
        refinement_inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,  # Stage C disabled (enable_stage_c=False)
    )
    stages = [StageA()]
    engine = RefinementEngine(stages, config=config)
    telemetry_dict = engine.run({"context": refinement_context})

    # Extract Bragg from Stage A artifacts
    bragg_final = engine._artifacts["stage_a"].bragg_full

    telemetry = telemetry_dict["A"]
```

**Rationale**: Follow D.2 CLI blueprint 5-step Engine pattern:
1. Import updates (Step 2 above)
2. Build RefinementContext from fixture inputs
3. Instantiate stages list (Stage A only, config already has enable_stage_b/c=False)
4. Run engine.run({"context": ...})
5. Extract artifacts from engine._artifacts["stage_a"].bragg_full

**Preserve**: All downstream logic unchanged. Fixture consumers expect `telemetry_dict["A"]`, `bragg_final`, etc. — all preserved.

---

### Step 4: Verify Zero Remaining Facade Imports

Check that all facade imports removed successfully:

```bash
grep -n "from dbex.nanobrag_refinement import" tests/dbex/test_stage_a_smoke_parity.py | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z/import_verification.txt
```

**Expected output**: Empty (zero matches)

If any matches remain, the Edit failed to update all instances. Investigate and rerun.

---

### Step 5: Run Mapped Tests

Run both test functions (they consume the migrated fixture):

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity \
              tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity \
              --smoke-detector-size=small \
              2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z/pytest_parity_batch2.log
```

**Expected outcome**: 2/2 tests PASSED

**Success criteria**:
- test_db_at_028_loss_scale_sanity validates loss/scale sanity (chi² reduction, log_scale range, masked pixels)
- test_db_at_029_structure_parity validates structure parity (ROI correlations, U-matrix norms)
- No import errors
- No Engine-specific failures (telemetry/artifacts structure preserved)

**If tests fail**:
- If Engine-specific errors (missing keys, wrong artifact structure), debug and fix
- If Stage A physics regression (chi² increased, correlations degraded), mark blocked and open separate bugfix initiative
- Capture full traceback and failure signature in pytest log

---

### Step 6: Update Artifacts

Write Turn Summary to `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z/summary.md`:

```markdown
### Turn Summary
Migrated test_stage_a_smoke_parity.py fixture from run_nanobrag_refinement facade to direct RefinementEngine usage; both DB-AT tests passed with no behavioral changes.
Phase D.3 Batch 2 complete; facade usage reduced to 2 files (dead import in test_torch_refine_smoke.py, active call in dbex/tools/stage_a_adam.py).
Next: Clean up dead import in test_torch_refine_smoke.py or proceed to D.3 Batch 3 (stage_a_adam.py migration).
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z/ (pytest_parity_batch2.log, import_verification.txt)
```

If the file already exists, **prepend** this block above existing content.

---

## How-To Map

All commands listed above. Key steps:

1. **Read file**: `tests/dbex/test_stage_a_smoke_parity.py`
2. **Update imports** (lines 13-16): Edit tool, replace facade imports with Engine imports
3. **Migrate fixture** (lines 147-160): Edit tool, replace facade call with 5-step Engine pattern
4. **Verify imports**: `grep -n "from dbex.nanobrag_refinement import" tests/dbex/test_stage_a_smoke_parity.py`
5. **Run tests**: pytest command above (2 selectors)
6. **Write summary**: Create or prepend to summary.md

---

## Pitfalls To Avoid

1. **DO NOT** change fixture signature or return values — downstream tests expect exact same structure
2. **DO NOT** modify mapping_context or calibration threading — TOOLING-VIS-001 requirement (fixture uses mapping_context.inputs, config.calibration_metadata, config.apply_calibration_n_cells)
3. **DO NOT** change Stage A physics logic — this is pure migration (facade → Engine), not physics bugfix
4. **DO NOT** modify test functions test_db_at_028 or test_db_at_029 — they consume fixture unchanged
5. **DO NOT** forget to extract bragg_final from engine._artifacts["stage_a"].bragg_full (not engine.run() return value)
6. **DO** preserve telemetry_dict["A"] extraction (line 160) — downstream code expects this
7. **DO** preserve all downstream reconstruction logic (build_final_bragg_from_stage_a_telemetry calls) — unchanged
8. **DO** use Edit tool (not Write) — this is an existing file, not a new one
9. **DO** verify zero facade imports after migration — required for D.5 facade deletion
10. **DO** use --smoke-detector-size=small — fixture expects this parametrization

**Environment Freeze Reminder**: Assume frozen runtime. If import errors occur, record signature in fix_plan.md and mark blocked; do not attempt pip installs or package upgrades.

---

## If Blocked

**Scenario 1: Import errors (missing RefinementEngine, StageA, etc.)**
- **Action**: Record error signature, mark blocked, update Attempts History with block reason
- **Do NOT**: Attempt environment changes or package installs

**Scenario 2: Tests fail with Engine-specific errors (telemetry keys missing, artifacts structure wrong)**
- **Action**: Debug and fix within this loop if trivial (e.g., wrong artifact key)
- **If non-trivial**: Mark blocked, document failure signature, update Attempts History
- **Do NOT**: Silently swallow failures or skip tests

**Scenario 3: Tests fail with Stage A physics regression (chi² increased, correlations degraded)**
- **Action**: Verify migration logic is correct (Engine pattern matches D.2 blueprint)
- **If migration correct but physics regressed**: Mark blocked, open separate bugfix initiative per spec_change_flow
- **Do NOT**: Attempt physics fixes within this migration loop

**Scenario 4: Fixture uses mapping_context in unexpected way**
- **Action**: Read mapping_context construction code, verify build_refinement_context consumes it correctly
- **If incompatible**: Mark blocked, document incompatibility, update Attempts History
- **Do NOT**: Change mapping_context or fixture logic beyond facade → Engine migration

---

## Findings Applied (Mandatory)

**Relevant findings from docs/findings.md**:

- **ARCH-REFACTOR-001 Phase D.2 CLI Blueprint** (2025-12-02T220000Z): 5-step Engine pattern validated in CLI refactor; use as canonical reference for all test migrations.
- **TOOLING-VIS-001** (mapping context requirements): Fixture uses mapping_context.inputs (not standard refinement_inputs construction), config.calibration_metadata from mapping_context.calibration, and config.apply_calibration_n_cells flag. All preserved in Engine pattern.
- **CONFORMANCE-001**: Tests require KMP_DUPLICATE_LIB_OK=TRUE (handled by pytest fixtures, no changes needed).
- **RUNTIME-001**: Tests require NANOBRAGG_DISABLE_COMPILE=1 (handled by pytest fixtures, no changes needed).

No relevant findings contradict this migration approach.

---

## Pointers

- **Plan**: `plans/active/ARCH-REFACTOR-001/implementation.md` (Phase D checklist, D.3 description)
- **Planning notes**: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220618Z/planning_notes.md` (detailed migration strategy, validation plan, risks)
- **CLI blueprint reference**: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220000Z/cli_refactor_blueprint.md` (canonical 5-step Engine pattern)
- **D.2 completion summary**: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220000Z/summary.md` (CLI migration success, pattern validated)
- **D.4 completion summary**: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T221500Z/summary.md` (import cleanup complete, 4/4 tests passed)
- **Fixture source**: `tests/dbex/test_stage_a_smoke_parity.py:68-269` (stage_a_smoke_result fixture)
- **Test functions**: `tests/dbex/test_stage_a_smoke_parity.py:296` (test_db_at_028_loss_scale_sanity), `tests/dbex/test_stage_a_smoke_parity.py:376` (test_db_at_029_structure_parity)

---

## Next Up (optional)

**After 2/2 tests PASSED**:
1. **Option A (cleanup)**: Remove dead facade import in test_torch_refine_smoke.py (inline import at ~line 1700 within test_stage_b_asu_mapping_smoke that was missed during Batch 1 migration)
2. **Option B (continue migrations)**: Proceed to D.3 Batch 3 (dbex/tools/stage_a_adam.py migration)
3. **Option C (if blocked)**: Debug failure, open bugfix initiative if needed

**After completion of D.3 Batches 1-3 + cleanup**: Proceed to D.5 (facade deletion) with comprehensive 12-step verification checklist.

---

## Doc Sync Plan (Conditional)

Not applicable this loop (no new tests added, no test renames). Existing test selectors unchanged.

---

## Mapped Tests Guardrail

Both mapped selectors collect and pass per fixture contract:
- `test_db_at_028_loss_scale_sanity` — consumes fixture, validates loss/scale sanity
- `test_db_at_029_structure_parity` — consumes fixture, validates structure parity via ROI correlations

No new tests created this loop, so no --collect-only validation required.

---

## Hard Gate

N/A (no selector changes this loop; both tests pre-existing and validated).

---

## Normative Math/Physics

N/A (no physics or math changes this loop; pure facade → Engine migration preserving existing behavior).
