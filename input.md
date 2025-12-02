# Input for Ralph — ARCH-REFACTOR-001 Phase D.4 Import Cleanup

## Summary
Redirect 4 inline imports in test_physics_loss_current.py from facade (dbex.nanobrag_refinement) to canonical module (dbex.physics.loss).

## Mode
Parity

## InitiativeType
architecture

## Focus
ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation (Phase D.4: Legacy Import Redirection)

## Branch
integration

## Mapped tests
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/dbex/test_physics_loss_current.py
```
Expected: 4/4 tests PASSED

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T221500Z/`
- `pytest_phase_d4.log` — Full pytest output for all 4 loss tests
- `import_verification.txt` — Grep output confirming zero remaining facade imports
- `summary.md` — Turn summary (prepend to existing file if present)

---

## Do Now

**Context**: Phase D.3 Batch 1 validation complete (4/5 tests PASSED, commit 390daa14). Proceeding with Phase D.4 import cleanup as preparatory step before facade deletion (D.5).

**Goal**: Redirect all inline imports of `_compute_variance_weighted_loss` from the facade (`dbex.nanobrag_refinement`) to the canonical module (`dbex.physics.loss`) in test file.

**Why**: The function was moved to `dbex.physics.loss` in Phase A.3 (2025-11-24T074500Z), but tests continued working via facade re-export. The facade cannot be deleted (D.5) until all imports redirect to canonical modules.

---

### Step 1: Create Artifacts Directory

```bash
mkdir -p plans/active/ARCH-REFACTOR-001/reports/2025-12-02T221500Z
```

---

### Step 2: Read Current Test File

Read `tests/dbex/test_physics_loss_current.py` to confirm current import pattern.

**Expected finding:** 4 inline imports at lines 63, 125, 160, 207:
```python
from dbex.nanobrag_refinement import _compute_variance_weighted_loss
```

---

### Step 3: Update Imports (Single Edit Call)

Use Edit tool with `replace_all=True` to redirect all 4 imports atomically:

**File:** `tests/dbex/test_physics_loss_current.py`

**Old string:**
```python
    from dbex.nanobrag_refinement import _compute_variance_weighted_loss
```

**New string:**
```python
    from dbex.physics.loss import _compute_variance_weighted_loss
```

**Parameters:**
- `replace_all=True` (all 4 occurrences identical)
- Preserve indentation (4 spaces before `from`)

**Rationale:** Same function, just different module path. No behavioral changes.

---

### Step 4: Verify Zero Remaining Facade Imports

Check that all imports redirected successfully:

```bash
grep -n "from dbex.nanobrag_refinement import" tests/dbex/test_physics_loss_current.py | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T221500Z/import_verification.txt
```

**Expected output:** Empty (zero matches)

If any matches remain, the Edit failed to update all instances. Investigate and rerun.

---

### Step 5: Run All Tests

Validate that function still accessible from new path with no behavioral changes:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/dbex/test_physics_loss_current.py \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T221500Z/pytest_phase_d4.log
```

**Expected outcome:** 4/4 tests PASSED
- `test_variance_weighted_loss_basic_clamping`
- `test_variance_weighted_loss_zero_mask`
- `test_variance_weighted_loss_zero_floor`
- `test_variance_weighted_loss_negative_model`

**If any test fails:**
1. Check import error message (function not found in dbex.physics.loss)
2. Verify function exported from module (check `dbex/physics/loss.py` exports)
3. If import error, revert Edit and mark blocked

---

### Step 6: Document Results

Create `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T221500Z/summary.md`:

```markdown
### Turn Summary
Redirected 4 inline imports in test_physics_loss_current.py from facade (dbex.nanobrag_refinement) to canonical module (dbex.physics.loss); all tests passed with no behavioral changes.
Phase D.4 import cleanup complete; facade re-exports no longer used by physics loss tests.
Next: Phase D.3 Batch 2 (test_stage_a_smoke_parity.py migration) or Phase D.5 (facade deletion).
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T221500Z/ (pytest_phase_d4.log, import_verification.txt)

---

## Implementation Notes

**File:** `tests/dbex/test_physics_loss_current.py`

**Changes:**
- Updated 4 inline imports (lines 63, 125, 160, 207)
- Old path: `dbex.nanobrag_refinement`
- New path: `dbex.physics.loss`
- Function name unchanged: `_compute_variance_weighted_loss`

**Validation:**
- All 4 tests PASSED
- Zero remaining facade imports confirmed
- No behavioral changes (function signature/behavior unchanged since Phase A.3)

**Metrics:**
- Import paths redirected: 4/4
- Tests validated: 4/4
- Files touched: 1
- Net change: 0 lines (same import statement length)
```

---

### Step 7: Commit

```bash
git add -A
git commit -m "$(cat <<'EOF'
ARCH-REFACTOR-001 Phase D.4 import cleanup (tests: 4/4 pass)

Redirected 4 inline imports in test_physics_loss_current.py from facade
(dbex.nanobrag_refinement) to canonical module (dbex.physics.loss). No
behavioral changes; tests validate function still accessible from new path.

Changes:
- Updated imports at lines 63, 125, 160, 207
- Old: from dbex.nanobrag_refinement import _compute_variance_weighted_loss
- New: from dbex.physics.loss import _compute_variance_weighted_loss

Validation:
- All 4 loss tests PASSED
- Zero remaining facade imports confirmed

Phase D.4 complete. Next: Phase D.3 Batch 2 (test migration) or D.5 (facade deletion).

Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T221500Z/

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
git push
```

---

## Pitfalls To Avoid

1. **Do not modify test logic**: Only update import paths. Test function bodies, assertions, and fixtures remain unchanged.

2. **Preserve indentation**: Imports are indented 4 spaces (inline imports inside test functions). Ensure new import string matches exact indentation.

3. **Use replace_all=True**: All 4 imports are identical. Single Edit call updates all instances atomically.

4. **Verify zero remaining facade imports**: Grep step confirms all imports redirected. If grep finds matches, Edit failed.

5. **Function name unchanged**: `_compute_variance_weighted_loss` is the same in both modules. No rename needed.

6. **No production code changes**: This is test-only update. Do not modify `dbex/physics/loss.py` or any production modules.

7. **Environment Freeze**: Do not install/upgrade packages. If import fails, mark blocked with error signature.

8. **Initiative type: architecture**: This is import path cleanup (preparation for facade removal), not behavior change.

9. **Phase A.3 precedent**: Function was moved to canonical module in Phase A.3 (2025-11-24T074500Z) and validated with 4 tests. Current imports work via facade re-export.

10. **Success criteria**: 4/4 tests PASSED + zero facade imports = Phase D.4 complete. 3/4 or fewer = blocked.

---

## If Blocked

**Scenario 1: Import error (function not found in dbex.physics.loss)**
- Check `dbex/physics/loss.py` exports (should have `_compute_variance_weighted_loss`)
- Verify Phase A.3 extraction happened (function should exist in module)
- Check if function renamed during extraction (unlikely, but verify)
- Capture error message, mark blocked

**Scenario 2: Edit tool fails to update all instances**
- Verify `replace_all=True` parameter used
- Check if indentation mismatch (Edit matching exact string including spaces)
- Try manual verification: count grep matches before/after Edit
- If grep still shows 4 matches after Edit, Edit failed - rerun or try individual edits

**Scenario 3: Tests fail with different error (not import)**
- Check if function signature changed between facade and canonical module (unlikely)
- Verify Phase A.3 extraction preserved behavior (should be identical)
- Compare test assertions against function implementation
- Capture full traceback, mark blocked

**Scenario 4: Facade re-export removed already**
- Check if previous loop removed facade re-export prematurely
- Verify facade still exports function: `grep "_compute_variance_weighted_loss" dbex/nanobrag_refinement.py`
- If missing, this import cleanup should have happened earlier - document timing issue

**Fallback:** If any blocker occurs, capture evidence in artifacts, update Attempts History with failure signature, and mark ARCH-REFACTOR-001 Phase D.4 blocked pending investigation. Do not proceed to D.5 until D.4 complete.

---

## Findings Applied

**Relevant findings from `docs/findings.md`:**

- **ARCH-REFACTOR-001 Phase A.3**: Function `_compute_variance_weighted_loss` extracted to `dbex.physics.loss` (2025-11-24T074500Z), validated with 4 passing tests
- **Phase D.4 scope**: Import cleanup (config-only, no RefinementEngine migration)
- **Facade re-export pattern**: Facade re-exports moved functions for backward compatibility during migration phases
- **Environment Freeze**: Runtime is pre-provisioned; do not install/upgrade packages during loops
- **Initiative type: architecture**: Import path cleanup (preparation for facade removal), not behavior change

---

## Pointers

**Reference documents:**
- Implementation plan: `plans/active/ARCH-REFACTOR-001/implementation.md` Phase D.4 checklist (line ~378)
- Phase D planning: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/` (7 planning artifacts)
- Phase A.3 extraction: `plans/active/ARCH-REFACTOR-001/implementation.md` lines ~143-153 (function move to dbex.physics.loss)
- Deletion checklist: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/deletion_checklist.md` (D.5 reference)

**Code pointers:**
- Test file: `tests/dbex/test_physics_loss_current.py` (4 functions, 4 inline imports at lines 63, 125, 160, 207)
- Canonical module: `dbex/physics/loss.py` (contains `_compute_variance_weighted_loss`)
- Facade: `dbex/nanobrag_refinement.py` (re-exports function from physics.loss)

**Previous phases:**
- Phase D.1: RefinementConfig extraction (commit 43a70eae, similar config-only migration)
- Phase D.2: CLI refactor (commit 46389946, RefinementEngine adoption reference)
- Phase D.3 Batch 1: Test migration (commits 7b0a016d, a6f39bac, f3ab680d, validation 390daa14)

---

## Next Up

**After this loop (if 4/4 tests PASSED):**
1. Mark Phase D.4 complete in implementation.md
2. Update fix_plan.md Attempts History with D.4 completion
3. Two options for next loop:
   - **Option A:** Phase D.3 Batch 2 — Migrate `tests/dbex/test_stage_a_smoke_parity.py` (1 function) to Engine pattern
   - **Option B:** Phase D.5 — Facade deletion (12-step verification checklist)

**Recommendation:** Option A (D.3 Batch 2) before D.5. Rationale: Complete all test migrations before facade deletion ensures comprehensive validation coverage.

**Sign-off:** This is a config-only loop (import path updates). No production code changes. No RefinementEngine migration. Just redirecting imports from facade to canonical module.

---

## Doc Sync Plan

**Not applicable this loop** (no new tests added/renamed; import cleanup only).

---

## Mapped Tests Guardrail

All 4 mapped test functions exist and should collect:
- `test_variance_weighted_loss_basic_clamping` ✓
- `test_variance_weighted_loss_zero_mask` ✓
- `test_variance_weighted_loss_zero_floor` ✓
- `test_variance_weighted_loss_negative_model` ✓

If any test collects 0, this is an error (test was renamed or deleted by accident).
