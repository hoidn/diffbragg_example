# Ralph Input — Loop i=250

## Summary
Delete the `dbex/nanobrag_refinement.py` facade file (Phase D.5), completing ARCH-REFACTOR-001.

## Focus
ARCH-REFACTOR-001 — Phase D.5 Facade Deletion

## Branch
`integration`

## Mapped Tests
```
tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
```

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/`

---

## Do Now

**Focus Item:** ARCH-REFACTOR-001 Phase D.5
**Action Type:** Implementation (Facade Deletion)

### Implement: `dbex/nanobrag_refinement.py` — DELETE FILE

Execute the 12-step deletion checklist from `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/deletion_checklist.md`.

### Step-by-Step Execution

#### Pre-Deletion Verification (Steps 1-4)

1. **Step 1 — Import Verification:**
   ```bash
   rg "from.*nanobrag_refinement import|import.*nanobrag_refinement" --type py \
     | grep -v "^plans/" \
     | grep -v "^docs/" \
     | grep -v "^logs/" \
     | grep -v "^archive/" \
     > plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/remaining_imports.txt 2>&1
   cat plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/remaining_imports.txt
   ```
   **Expected:** Empty file (verified by supervisor — zero imports in dbex/ and tests/)

2. **Step 2 — Call Site Verification:**
   ```bash
   rg "run_nanobrag_refinement\(" --type py \
     | grep -v "^plans/" \
     | grep -v "^docs/" \
     | grep -v "^logs/" \
     | grep -v "^archive/" \
     | grep -v "^dbex/nanobrag_refinement.py:" \
     > plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/remaining_calls.txt 2>&1
   cat plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/remaining_calls.txt
   ```
   **Expected:** Empty file

3. **Step 3 — Module Dependency Check:**
   ```bash
   python -c "import dbex.refine_one; print('refine_one OK')" && \
   python -c "import dbex.refinement.engine; print('engine OK')" && \
   python -c "import dbex.refinement.stage_a; print('stage_a OK')" && \
   python -c "import dbex.refinement.stage_b; print('stage_b OK')" && \
   python -c "import dbex.refinement.stage_c; print('stage_c OK')" && \
   python -c "from dbex.refinement.config import RefinementConfig; print('config OK')" && \
   python -c "from dbex.refinement import RefinementConfig; print('__init__ re-export OK')"
   ```
   **Expected:** All 7 imports succeed

4. **Step 4 — Test Collection Verification:**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   pytest --collect-only tests/dbex/ 2>&1 \
     | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/collection_check_pre.log \
     | tail -5
   ```
   **Expected:** "collected X items" (no errors)

#### Deletion Execution (Step 5-6)

5. **Step 5 — Delete Facade:**
   ```bash
   git rm dbex/nanobrag_refinement.py
   ls -la dbex/nanobrag_refinement.py 2>&1 \
     | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/deletion_confirmation.txt
   ```
   **Expected:** "No such file or directory"

6. **Step 6 — Update Module Exports (if needed):**
   ```bash
   grep "nanobrag_refinement" dbex/__init__.py
   ```
   **If matches:** Remove those lines. **If empty:** No action needed.

#### Post-Deletion Verification (Steps 7-11)

7. **Step 7 — Static Import Verification (repeat Step 3):**
   Same 7 import checks — all must pass without ImportError

8. **Step 8 — CLI Smoke Test:**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata 2>&1 \
     | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/pytest_cli_post_deletion.log
   ```
   **Gate:** Test PASSED

9. **Step 9 — Stage Smoke Tests:**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv \
     tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
     tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
     tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
     --smoke-detector-size=small 2>&1 \
     | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/pytest_stage_smokes_post_deletion.log
   ```
   **Gate:** 3/3 tests PASSED

10. **Step 10 — Full Test Suite:**
    ```bash
    AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
    DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
    KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
    pytest -vv \
      tests/dbex/test_refine_one_cli.py \
      tests/dbex/test_refinement_engine.py \
      tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload \
      tests/dbex/test_physics_loss_current.py \
      --smoke-detector-size=small 2>&1 \
      | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/pytest_full_suite_post_deletion.log
    ```
    **Gate:** All tests PASSED

11. **Step 11 — Collection Verification (repeat Step 4):**
    ```bash
    AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
    KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
    pytest --collect-only tests/dbex/ 2>&1 \
      | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/collection_check_post.log \
      | tail -5
    ```
    **Expected:** "collected X items" (no errors)

12. **Step 12 — Documentation Grep (informational):**
    ```bash
    rg "nanobrag_refinement" docs/ \
      > plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/doc_references.txt
    ```
    **Note:** Non-blocking; docs updated in future cycle.

---

## Commit Message Template

```
ARCH-REFACTOR-001 Phase D.5: Delete nanobrag_refinement.py facade

All consumers migrated to RefinementEngine:
- CLI (refine_one.py)
- Test harness (test_torch_refine_smoke.py, test_stage_a_mapping_equiv.py)
- Tooling (stage_a_adam.py)
- Config imports (test_refinement_engine.py, test_stage_b_cpu_fallback.py)

Pre-deletion verification: PASSED (Steps 1-4)
Post-deletion verification: PASSED (Steps 7-11)

Exit Criteria #2 satisfied: Facade deleted, Engine is sole path.

Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-09T070000Z/

[Claude Code]
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Pitfalls To Avoid

1. **DO NOT** delete the file before completing Steps 1-4 pre-deletion checks
2. **DO** capture all verification output to artifact files
3. **DO** use the exact rollback command if ANY post-deletion check fails: `git checkout HEAD -- dbex/nanobrag_refinement.py`
4. **DO NOT** commit until ALL 11 verification steps pass
5. **DO** update `docs/fix_plan.md` ARCH-REFACTOR-001 status to `done` after successful deletion
6. **DO NOT** touch plan-local probe scripts — they are explicitly out of scope

---

## If Blocked

If any verification step fails:
1. Capture the full error output
2. Run rollback: `git checkout HEAD -- dbex/nanobrag_refinement.py`
3. Document which step failed and the error message
4. Mark Phase D.5 blocked with specific failure cause
5. Return to supervisor with findings

---

## Findings Applied (Mandatory)

- **ARCH-ENGINE-002**: RefinementEngine is the sole refinement path after deletion
- **ARCH-REFACTOR-001 Exit Criteria**: Criterion #2 requires facade deletion
- **RUNTIME-001**: Test env vars — use canonical `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
- **TESTING-003**: Mapped test selectors from `docs/TESTING_GUIDE.md`

---

## Pointers

- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/deletion_checklist.md` — Full 12-step procedure
- `plans/active/ARCH-REFACTOR-001/implementation.md:382-385` — Phase D.5 checklist reference
- `docs/fix_plan.md:136-141` — ARCH-REFACTOR-001 Exit Criteria

---

## Next Up

After successful Phase D.5 completion:
- Mark ARCH-REFACTOR-001 status `done` in `docs/fix_plan.md`
- Update `galph_memory.md` with initiative closure
- Consider Phase E (Legacy Isolation) if DiffBragg backend needs attention
