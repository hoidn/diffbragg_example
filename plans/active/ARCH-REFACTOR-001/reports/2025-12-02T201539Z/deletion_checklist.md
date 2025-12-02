# Phase D.5: Facade Deletion Verification Checklist

**Initiative:** ARCH-REFACTOR-001 Phase D.5 (Final)
**Date:** 2025-12-02T201539Z
**Status:** Planning

## Objective

Safely delete `dbex/nanobrag_refinement.py` (~656 lines) after all consumers have migrated to RefinementEngine, ensuring no production or test code depends on the facade.

## Prerequisites

**Must be complete BEFORE attempting deletion:**
- ✅ Phase D.1: RefinementConfig migrated to `dbex/refinement/config.py`
- ✅ Phase D.2: CLI (`dbex/refine_one.py`) migrated to RefinementEngine
- ✅ Phase D.3: Test harness (`test_torch_refine_smoke.py`, `test_stage_a_smoke_parity.py`) migrated
- ✅ Phase D.4: Tooling (`stage_a_adam.py`) + legacy imports (`test_physics_loss_current.py`) migrated
- ✅ All migration validation tests PASSED

**If any prerequisite incomplete:** STOP. Do not proceed with deletion.

---

## Pre-Deletion Verification Steps

### Step 1: Import Verification

**Objective:** Confirm zero remaining imports from `dbex.nanobrag_refinement`

**Command:**
```bash
rg "from.*nanobrag_refinement import|import.*nanobrag_refinement" --type py \
  | grep -v "^docs/" \
  | grep -v "^logs/" \
  | grep -v "^plans/archive/" \
  | grep -v "^docs/fix_plan_archive.md" \
  | grep -v "^repomix-output.xml" \
  > plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/remaining_imports.txt
```

**Expected output:** Empty file (no matches excluding docs/logs/archive)

**If non-empty:** Each remaining import must be:
- Documented in consumer_analysis.md as "Out-of-Scope" (e.g., plans/active/*/bin/*.py probes), OR
- Added to Phase D.4 migration list and completed

**Gate:** `remaining_imports.txt` is empty OR all matches are documented as intentionally excluded.

### Step 2: Call Site Verification

**Objective:** Confirm zero remaining calls to `run_nanobrag_refinement()`

**Command:**
```bash
rg "run_nanobrag_refinement\(" --type py \
  | grep -v "^docs/" \
  | grep -v "^logs/" \
  | grep -v "^plans/archive/" \
  | grep -v "^docs/fix_plan_archive.md" \
  | grep -v "^repomix-output.xml" \
  | grep -v "^dbex/nanobrag_refinement.py:" \
  > plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/remaining_calls.txt
```

**Expected output:** Empty file (no matches excluding docs/logs/archive and the definition itself)

**If non-empty:** Each remaining call site must be:
- Documented as "Out-of-Scope" research probe, OR
- Migrated to RefinementEngine pattern

**Gate:** `remaining_calls.txt` is empty OR all matches are documented as intentionally excluded.

### Step 3: Module Dependency Check

**Objective:** Verify production modules can import without facade

**Commands:**
```bash
# Check CLI entry point
python -c "import dbex.refine_one; print('refine_one OK')"

# Check RefinementEngine
python -c "import dbex.refinement.engine; print('engine OK')"

# Check Stages
python -c "import dbex.refinement.stage_a; print('stage_a OK')"
python -c "import dbex.refinement.stage_b; print('stage_b OK')"
python -c "import dbex.refinement.stage_c; print('stage_c OK')"

# Check Config
python -c "from dbex.refinement.config import RefinementConfig; print('config OK')"
python -c "from dbex.refinement import RefinementConfig; print('__init__ re-export OK')"
```

**Expected output:** All imports succeed with "OK" messages, no ImportError

**Gate:** All 7 import checks PASSED

### Step 4: Test Collection Verification

**Objective:** Ensure all tests are discoverable and no import errors during collection

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest --collect-only tests/dbex/ \
  > plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/collection_check.log 2>&1
```

**Expected output:** No ImportError, no collection errors, all tests discovered

**Gate:** Collection log shows "collected X items" (no errors)

---

## Deletion Execution

**After all pre-deletion checks PASSED:**

### Step 5: Delete Facade File

**Command:**
```bash
git rm dbex/nanobrag_refinement.py
```

**Artifact:** Save deletion confirmation
```bash
ls -la dbex/nanobrag_refinement.py 2>&1 \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/deletion_confirmation.txt
```

**Expected output:** `No such file or directory` (file deleted)

### Step 6: Update Module Exports (if needed)

**File:** `dbex/__init__.py`

**Check:** Does `dbex/__init__.py` re-export anything from `nanobrag_refinement`?

**Command:**
```bash
grep "nanobrag_refinement" dbex/__init__.py
```

**If matches found:** Remove those lines (facade no longer exists).

**If empty:** No action needed.

---

## Post-Deletion Verification

**After deletion, validate system still works:**

### Step 7: Static Import Verification (Repeat Step 3)

**Objective:** Confirm imports still work after deletion

**Commands:** Same as Step 3 (all 7 import checks)

**Gate:** All imports succeed, no ImportError mentioning `nanobrag_refinement`

### Step 8: CLI Smoke Test

**Objective:** Verify production CLI entry point works

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/pytest_cli_post_deletion.log
```

**Gate:** Test PASSED, no ImportError

### Step 9: Stage Smoke Tests (Full Suite)

**Objective:** Validate all Stage A/B/C acceptance tests pass

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  --smoke-detector-size=small \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/pytest_stage_smokes_post_deletion.log
```

**Gate:** All 3 tests PASSED

### Step 10: Full Test Suite (Comprehensive)

**Objective:** Run all tests touched during Phase D to confirm no regressions

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_refine_one_cli.py \
  tests/dbex/test_torch_refine_smoke.py \
  tests/dbex/test_stage_a_smoke_parity.py \
  tests/dbex/test_refinement_engine.py \
  tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload \
  tests/dbex/test_physics_loss_current.py \
  tests/dbex/test_stage_a_adam_tooling.py \
  --smoke-detector-size=small \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/pytest_full_suite_post_deletion.log
```

**Gate:** All tests PASSED (excluding documented xfail/skip)

**Expected metrics:**
- Tests run: 20+ (CLI + Stage smokes + Engine + Tooling + Physics)
- Duration: ~3-5 minutes (small detector mode)
- Failures: 0

### Step 11: Collection Verification (Repeat Step 4)

**Objective:** Confirm all tests still discoverable after deletion

**Command:** Same as Step 4

**Gate:** Collection succeeds, no ImportError

### Step 12: Documentation Grep (Informational)

**Objective:** Identify doc references to update in future doc refresh cycle

**Command:**
```bash
rg "nanobrag_refinement" docs/ \
  > plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/doc_references.txt
```

**Action:** Add note to `galph_memory.md` for next doc refresh:
> "Phase D complete: facade deleted. Update doc references from `run_nanobrag_refinement` to `RefinementEngine` pattern in next doc cycle."

**Note:** This is non-blocking; docs can be updated asynchronously.

---

## Rollback Plan

**If any post-deletion verification fails:**

1. **Immediate rollback:**
   ```bash
   git checkout HEAD -- dbex/nanobrag_refinement.py
   ```

2. **Identify failure:**
   - Which verification step failed?
   - What is the error message?
   - Is it a migration bug (Phase D.1-D.4 incomplete) or deletion issue?

3. **Document in fix_plan.md:**
   - Add to ARCH-REFACTOR-001 Attempts History: "Phase D.5 rollback due to [error]"
   - Tag as `blocked — incomplete_migration`
   - Reference failing verification step and log file

4. **Reassess:**
   - If migration incomplete: return to Phase D.2/D.3/D.4, fix consumer
   - If deletion issue: investigate why pre-deletion checks passed but post-deletion failed

**Do NOT proceed with commit if rollback required.**

---

## Success Criteria

Phase D.5 (and entire Phase D) is **complete** when:

1. ✅ Pre-deletion checks (Steps 1-4) all PASSED
2. ✅ Facade file deleted (Step 5)
3. ✅ Module exports updated (Step 6, if needed)
4. ✅ Post-deletion checks (Steps 7-11) all PASSED:
   - Static imports: 7/7 PASSED
   - CLI smoke: 1/1 PASSED
   - Stage smokes: 3/3 PASSED
   - Full suite: 20+/20+ PASSED
   - Collection: No errors
5. ✅ Documentation references logged (Step 12, informational)
6. ✅ Artifacts saved under `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/`:
   - `remaining_imports.txt` (empty)
   - `remaining_calls.txt` (empty)
   - `collection_check.log` (pre-deletion)
   - `deletion_confirmation.txt`
   - `pytest_cli_post_deletion.log`
   - `pytest_stage_smokes_post_deletion.log`
   - `pytest_full_suite_post_deletion.log`
   - `collection_check_post_deletion.log`
   - `doc_references.txt` (informational)

7. ✅ Commit message:
   ```
   ARCH-REFACTOR-001 Phase D.5: Delete nanobrag_refinement.py facade

   All consumers migrated to RefinementEngine:
   - CLI (refine_one.py)
   - Test harness (test_torch_refine_smoke.py, test_stage_a_smoke_parity.py)
   - Tooling (stage_a_adam.py)
   - Config imports (test_refinement_engine.py, test_stage_b_cpu_fallback.py)
   - Legacy helper imports (test_physics_loss_current.py)

   Pre-deletion verification:
   - Zero remaining imports (excluding docs/logs/archive)
   - Zero remaining call sites (excluding research probes)
   - All static imports succeed
   - Test collection clean

   Post-deletion verification:
   - CLI smoke test: PASSED
   - Stage A/B/C smokes: 3/3 PASSED
   - Full test suite: 20+ PASSED
   - No ImportError

   Exit Criteria #2 satisfied: Facade deleted, Engine is sole path.

   Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/
   ```

8. ✅ Fix_plan.md updated:
   - Mark ARCH-REFACTOR-001 Exit Criterion #2 SATISFIED
   - Update status to `done` (both Exit Criteria #1 and #2 complete)
   - Add final Attempts History entry with completion timestamp

---

## Metrics & Impact

**Deletion impact:**
- **File deleted:** `dbex/nanobrag_refinement.py` (~656 lines)
- **Net change:** -656 lines (facade removed, no replacement)
- **Consumers migrated:** 6 production/test files + 1 tooling file
- **Import updates:** ~20 inline imports redirected to canonical modules
- **Engine adoption:** 10 call sites (1 CLI + 9 tests) now use RefinementEngine

**Architecture improvement:**
- Facade pattern eliminated
- Protocol-based Engine is sole refinement path
- Typed contexts (RefinementContext, JobContext) replace ad-hoc dicts
- Stage A/B/C classes fully self-contained (no `*_impl.py` dependencies)

**Maintenance benefit:**
- Single code path (Engine) instead of dual facade/Engine paths
- Clearer separation: Config (dbex.refinement.config), Engine (dbex.refinement.engine), Stages (dbex.refinement.stage_*)
- Easier to extend (add Stage D/E without touching monolithic facade)

---

## Final Sign-Off

**ARCH-REFACTOR-001 Phase D.5 complete:**
- Mark implementation.md Phase D.5 checklist item complete
- Update fix_plan.md ARCH-REFACTOR-001 Status → `done`
- Notify supervisor (Galph) via `galph_memory.md`:
  > "ARCH-REFACTOR-001 COMPLETE: Both Exit Criteria satisfied. All `*_impl.py` deleted (Criterion #1), facade deleted (Criterion #2). RefinementEngine is sole refinement path. Next: Consider Phase E (Legacy Isolation) if needed, or close initiative."
