# Phase D.4 Import Cleanup — Planning Notes

**Timestamp:** 2025-12-02T221500Z
**Focus:** ARCH-REFACTOR-001 Phase D.4 — Legacy Import Redirection

## Context

Phase D.3 Batch 1 validation complete (4/5 tests PASSED, commit 390daa14). Now proceeding with remaining Phase D work before facade deletion.

**Phase D.4 scope:** Fix legacy imports in `test_physics_loss_current.py` that import `_compute_variance_weighted_loss` from the facade (`dbex.nanobrag_refinement`) instead of the canonical location (`dbex.physics.loss`).

This is a config-only migration (no RefinementEngine pattern changes, just import path updates) and serves as a low-risk preparatory step before Phase D.5 facade deletion.

## Current State

**File:** `tests/dbex/test_physics_loss_current.py`
**Issue:** 4 inline imports reference the facade:
```python
from dbex.nanobrag_refinement import _compute_variance_weighted_loss
```

**Root cause:** These tests were written during Phase 0 (baseline validation) when `_compute_variance_weighted_loss` lived in `nanobrag_refinement.py`. Phase A.3 moved the function to `dbex/physics/loss.py` (commit from 2025-11-24T074500Z), but the tests continued working via facade re-export.

**Blocker for D.5:** The facade cannot be deleted until all imports are redirected to canonical modules.

## Strategy

### Approach: Replace-All Import Redirection

1. **Single-pass update:** Use `replace_all=True` to redirect all 4 occurrences in one Edit call
2. **Import path change:** `dbex.nanobrag_refinement` → `dbex.physics.loss`
3. **Function name unchanged:** `_compute_variance_weighted_loss` (no rename)
4. **Validation:** Run all 4 tests in the file to confirm no import errors or behavioral regression

### Files Touched

**Production code:** 0 (no source changes, test-only update)
**Test files:** 1 (`tests/dbex/test_physics_loss_current.py`)

### Expected Metrics

- Import paths redirected: 4/4 (all inline imports in test file)
- Tests validated: 4/4 (`test_variance_weighted_loss_sigma_floor`, `test_variance_weighted_loss_zero_mask`, `test_variance_weighted_loss_zero_floor`, `test_variance_weighted_loss_negative_model`)
- Files touched: 1
- Net change: 0 lines (same import statement length)

## Implementation Plan

### Step 1: Read Current Import Pattern

Read `tests/dbex/test_physics_loss_current.py` to confirm current import location and usage pattern.

**Expected finding:**
```python
from dbex.nanobrag_refinement import _compute_variance_weighted_loss
```
(Appears 4 times as inline imports in test functions)

### Step 2: Update Imports

Use Edit tool with `replace_all=True`:

**Old string:**
```python
from dbex.nanobrag_refinement import _compute_variance_weighted_loss
```

**New string:**
```python
from dbex.physics.loss import _compute_variance_weighted_loss
```

**Rationale for replace_all:**
- All 4 occurrences are identical
- Same function, just different module path
- No context-specific variations needed

### Step 3: Validation

Run all 4 tests in the file to confirm:
1. No import errors (function accessible from new path)
2. No behavioral changes (test assertions unchanged)
3. Same runtime characteristics (function implementation unchanged)

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/dbex/test_physics_loss_current.py
```

**Expected outcome:** 4/4 tests PASSED

### Step 4: Commit

**Commit message pattern:**
```
ARCH-REFACTOR-001 Phase D.4 import cleanup (tests: 4/4 pass)

Redirected 4 inline imports in test_physics_loss_current.py from facade
(dbex.nanobrag_refinement) to canonical module (dbex.physics.loss). No
behavioral changes; tests validate function still accessible from new path.

Phase D.4 complete. Next: Phase D.3 Batch 2 (test migration) or D.5 (facade deletion).

Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T221500Z/

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Risks & Mitigations

### Risk 1: Function Not Exported from physics.loss

**Likelihood:** Very low (function moved in Phase A.3, already validated)
**Impact:** Import error, tests fail
**Mitigation:** Phase A.3 validation (2025-11-24T074500Z) confirmed function accessible from new module with 4 passing tests. If import fails, revert Edit and investigate module exports.

### Risk 2: Facade Re-Export Changed Function Signature

**Likelihood:** Very low (re-export is pass-through)
**Impact:** Test assertions fail
**Mitigation:** Function signature unchanged since Phase A.3 extraction. No telemetry or behavioral changes between facade re-export and direct import.

### Risk 3: Missed Import Instances

**Likelihood:** Very low (grep confirms 4 instances)
**Impact:** Partial update, some imports still point to facade
**Mitigation:** Using `replace_all=True` ensures atomic update. Post-edit verification step checks for remaining facade imports.

## Success Criteria

**Phase D.4 complete when:**
1. Zero inline imports of `_compute_variance_weighted_loss` from `dbex.nanobrag_refinement` in test file
2. All 4 inline imports redirect to `dbex.physics.loss`
3. All 4 tests in `test_physics_loss_current.py` PASSED
4. Commit message documents D.4 completion

**Next steps after D.4:**
- Phase D.3 Batch 2: Migrate `test_stage_a_smoke_parity.py` (1 function) to Engine pattern
- Phase D.5: Facade deletion (12-step verification checklist)

## Artifacts

**Directory:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T221500Z/`

**Expected files:**
- `planning_notes.md` (this file)
- `pytest_phase_d4.log` (validation run output)
- `import_verification.txt` (grep output confirming zero remaining facade imports)
- `summary.md` (turn summary for this loop)

## Related Documentation

**Implementation plan:** `plans/active/ARCH-REFACTOR-001/implementation.md` Phase D.4 checklist (line ~378)
**Deletion checklist:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/deletion_checklist.md` (D.5 reference)
**Phase A.3 extraction:** `plans/active/ARCH-REFACTOR-001/implementation.md` lines ~143-153 (function move to dbex.physics.loss)
**Phase D.1 precedent:** Similar config-only import update pattern (RefinementConfig extraction)
