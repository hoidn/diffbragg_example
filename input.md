# Input for Ralph — Loop i=134

**Summary**: DB-AT-SUITE-CARE-001 Phase B.3 — Fix test harness import errors blocking DB-AT-010 verification

**Mode**: none

**ActionType**: implementation_ready

**DecisionStatus**: patch_ready

**InitiativeType**: harness

**Focus**: [DB-AT-SUITE-CARE-001] — Acceptance Suite Upkeep (DB-AT-002/010/020—024)

**Branch**: integration

**Mapped tests**:
- `env KMP_DUPLICATE_LIB_OK=TRUE DBAT010_ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/db_at_010_verification NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests -k DB_AT_010 --smoke-detector-size=full` (validation: 0 errors, ≥5 tests collected)
- `env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_nanobrag_smoke.py` (regression check)
- `env KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_vis_triptych_smoke.py` (regression check)

**Artifacts**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/`

**Findings Applied (Mandatory)**:
- **TESTING-003** — Test harness broken imports violate ARCH-CONTRACT-TESTING-001; fixing imports restores test registry synchronization
- **ARCH-BRIDGE-RESP-001** (via problems.md) — Architectural refactoring moved `prepare_refinement_inputs` to `dbex.refinement.inputs` per Phase C.6
- **RUNTIME-001** — DB-AT-010 requires NANOBRAGG_DISABLE_COMPILE=1 + --smoke-detector-size=full per workflow spec

**ARCH Contracts (mandatory)**:
1. **ARCH-CONTRACT-TESTING-001** (Test registry synchronization)
   - **Owner**: `docs/development/TEST_SUITE_INDEX.md`, `tests/` module imports
   - **Failure**: Implementation bug (test imports lag architectural refactoring)
   - **Fix**: Update test imports to reflect current module structure

2. **ARCH-CONTRACT-BRIDGE-001** (Bridge responsibility boundary)
   - **Owner**: `dbex.refinement.inputs::prepare_refinement_inputs` (canonical location per ARCH-BRIDGE-RESP-001 Phase C)
   - **Forbidden duplicates**: Old path `dbex.nanobrag_bridge.prepare_refinement_inputs` (moved in Phase C.6)
   - **Enforcement**: This loop fixes import path violations; no mechanical enforcement test needed (standard Python import checking)

**Do Now**:

Fix test harness import errors blocking DB-AT-010 verification (Phase B.3 escalation from Loop i=133).

**Context**: Loop i=133 (Ralph) discovered 2 collection errors when running DB-AT-010 verification:
1. `tests/dbex/test_nanobrag_smoke.py:30` imports `prepare_refinement_inputs` from `dbex.nanobrag_bridge` (moved to `dbex.refinement.inputs` per ARCH-BRIDGE-RESP-001 Phase C.6)
2. `tests/dbex/test_vis_triptych_smoke.py:7` imports `plot_z_scores` from `dbex.vis` (renamed to `compute_z_scores`)

**Implementation**:

**Fix 1**: Update test_nanobrag_smoke.py import

```bash
# Read current import block
# Lines 28-36 currently import from dbex.nanobrag_bridge

# Replace with correct imports:
# - prepare_refinement_inputs: dbex.nanobrag_bridge → dbex.refinement.inputs
# - Other bridge helpers (create_detector_config, create_beam_config, create_crystal_config, RefinementInputs) remain in dbex.nanobrag_bridge
```

Edit `tests/dbex/test_nanobrag_smoke.py`:
- **old_string** (lines 28-36):
  ```python
  # DataLoad and bridge helpers
  from dbex.data_load import DataLoad
  from dbex.nanobrag_bridge import (
      prepare_refinement_inputs,
      create_detector_config,
      create_beam_config,
      create_crystal_config,
      RefinementInputs
  )
  ```

- **new_string**:
  ```python
  # DataLoad and bridge helpers
  from dbex.data_load import DataLoad
  from dbex.refinement.inputs import prepare_refinement_inputs, RefinementInputs
  from dbex.nanobrag_bridge import (
      create_detector_config,
      create_beam_config,
      create_crystal_config,
  )
  ```

**Fix 2**: Update test_vis_triptych_smoke.py import

Edit `tests/dbex/test_vis_triptych_smoke.py`:
- **old_string** (line 7):
  ```python
  from dbex.vis import plot_triptych, plot_z_scores
  ```

- **new_string**:
  ```python
  from dbex.vis import plot_triptych, compute_z_scores
  ```

Also update the function call in the test body:
- **old_string** (line 38):
  ```python
      result_path = plot_z_scores(
  ```

- **new_string**:
  ```python
      result_path = compute_z_scores(
  ```

And update the assertion message:
- **old_string** (line 45):
  ```python
      assert result_path.exists(), "plot_z_scores must write an artifact"
  ```

- **new_string**:
  ```python
      assert result_path.exists(), "compute_z_scores must write an artifact"
  ```

**Validation**:

1. **Collection check** (must complete before committing):
   ```bash
   mkdir -p plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/

   env KMP_DUPLICATE_LIB_OK=TRUE \
       DBAT010_ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/db_at_010_verification \
       NANOBRAGG_DISABLE_COMPILE=1 \
       pytest --collect-only tests -k DB_AT_010 --smoke-detector-size=full \
       > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/pytest_collect_only.log 2>&1

   echo $? > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/collect_exit_code.txt
   ```

   **Exit criteria**: Exit code 0, "0 errors" in log, ≥5 tests collected

2. **Regression checks** (both must PASS):
   ```bash
   env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
       pytest -v tests/dbex/test_nanobrag_smoke.py \
       > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/pytest_nanobrag_smoke_regression.log 2>&1

   env KMP_DUPLICATE_LIB_OK=TRUE \
       pytest -v tests/dbex/test_vis_triptych_smoke.py \
       > plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/pytest_vis_triptych_regression.log 2>&1
   ```

**Summary Report**:

Create `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/summary.md` documenting:
- Phase B.3 complete (test import fixes applied)
- Collection check outcome (0 errors, N tests collected)
- Regression check outcomes (test_nanobrag_smoke: PASS/FAIL, test_vis_triptych_smoke: PASS/FAIL)
- Next steps (Phase B.4: Re-run DB-AT-010 full verification now that collection errors resolved)

**Forbidden This Loop**:
- No production code changes (harness fixes only)
- No DB-AT-010 full pytest execution (defer to Phase B.4 after collection validation)
- No member plan Phase A/B tasks beyond this harness fix

**Pitfalls**:
1. `prepare_refinement_inputs` moved to `dbex.refinement.inputs` but `RefinementInputs` dataclass also moved (import both from same module)
2. Other bridge helpers (`create_detector_config`, `create_beam_config`, `create_crystal_config`) remain in `dbex.nanobrag_bridge` (do NOT change those imports)
3. `plot_z_scores` was RENAMED to `compute_z_scores` (not moved), so only change the function name in import + 3 usage sites (line 7, 38, 45)
4. Must update BOTH the import statement AND the function calls/assertions in test bodies
5. Run `pytest --collect-only` before committing to ensure imports valid

**If Blocked**:
- If collect-only still shows errors: Document the signature, update summary.md with blocked status, escalate to Galph
- If regression tests fail: Bisect to identify which fix caused the failure, document in summary.md, mark Phase B.3 partial complete

**Doc Sync Plan (Conditional)**:
Not applicable (no new tests added, existing test imports fixed). TEST_SUITE_INDEX.md unchanged.
