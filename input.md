# Ralph Loop Input — TORCH-GEOMETRY-PARITY-002 Phase B Regression Fix

## Summary
Fix scoping bug in Phase B U-matrix implementation causing `NameError: name 'misset_deg_for_crystal' is not defined` in test_stage_a_expansion.

## Mode
none

## Focus
TORCH-GEOMETRY-PARITY-002 — Direct U-Matrix Parameterization for Stage A Geometry Refinement

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard, must PASS)
- `tests/dbex/test_u_matrix_gradcheck.py::test_quaternion_roundtrip` (already PASSED, verify no regression)

## Artifacts
`plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T112058Z/`

Expected artifacts after fix:
- `pytest_stage_a_regression_fixed.log` (test_stage_a_expansion PASSED)
- `pytest_quaternion_roundtrip.log` (test_quaternion_roundtrip still PASSED)

## Do Now

**Scope:** Fix scoping bug introduced in commit 2793ba9 where `misset_deg_for_crystal` references `misset_xyz_deg` before it's defined, causing NameError in the U-matrix code path.

**Root Cause:**
- File: `dbex/nanobrag_refinement.py`
- Two closures contain identical scoping bug:
  1. Stage A LBFGS closure (around lines 968-1015)
  2. Stage C closure (around lines 1404-1448)

**Problem:** At line 1015 (Stage A) and similar line in Stage C, code tries:
```python
misset_deg_for_crystal = None if config.use_u_matrix_parameterization else misset_xyz_deg
```

But `misset_xyz_deg` is only defined INSIDE the `else` branch (cell+misset path, line 997). In the U-matrix path (`if` branch), `misset_xyz_deg` never gets defined, so line 1015 raises NameError.

### Tasks

1. **Fix Stage A LBFGS closure scoping bug** (`dbex/nanobrag_refinement.py` around lines 968-1015):

   a) **Add `misset_deg_for_crystal = None` at end of U-matrix `if` branch** (after `crystal_overrides` dict closing brace, before `else:`):
   ```python
   if config.use_u_matrix_parameterization:
       # ... existing U-matrix code ...
       crystal_overrides = {
           'cell_a': perturbed_cell_a,
           'cell_b': perturbed_cell_b,
           'cell_c': perturbed_cell_c,
           'cell_alpha': perturbed_alpha,
           'cell_beta': perturbed_beta,
           'cell_gamma': perturbed_gamma,
           'mosflm_a_star': mosflm_a_star_tuple,
           'mosflm_b_star': mosflm_b_star_tuple,
           'mosflm_c_star': mosflm_c_star_tuple,
       }
       # FIX: Define misset_deg_for_crystal here in U-matrix branch
       misset_deg_for_crystal = None  # MOSFLM A* is provided directly
   ```

   b) **Add `misset_deg_for_crystal = misset_xyz_deg` at end of cell+misset `else` branch** (after `crystal_overrides` dict):
   ```python
   else:
       # Existing cell+misset path (GEOMETRY-003)
       # ... existing code computing misset_xyz_deg ...
       crystal_overrides = {
           'cell_a': perturbed_cell_a,
           'cell_b': perturbed_cell_b,
           'cell_c': perturbed_cell_c,
           'cell_alpha': perturbed_alpha,
           'cell_beta': perturbed_beta,
           'cell_gamma': perturbed_gamma
       }
       # FIX: Define misset_deg_for_crystal here in cell+misset branch
       misset_deg_for_crystal = misset_xyz_deg
   ```

   c) **Remove line 1015** (the assignment outside the if/else block):
   ```python
   # REMOVE THIS LINE:
   # misset_deg_for_crystal = None if config.use_u_matrix_parameterization else misset_xyz_deg
   ```

2. **Fix Stage C closure scoping bug** (same pattern around lines 1404-1448):
   - Apply identical fix: move `misset_deg_for_crystal` assignment into each branch
   - U-matrix branch: `misset_deg_for_crystal = None`
   - Cell+misset branch: `misset_deg_for_crystal = misset_xyz_deg`
   - Remove the assignment that references `misset_xyz_deg` outside the branches

3. **Run regression guard**:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
     > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T112058Z/pytest_stage_a_regression_fixed.log 2>&1
   ```
   **Expected:** `PASSED` (validates backward compatibility with cell+misset path since default `use_u_matrix_parameterization=False`)

4. **Verify quaternion roundtrip still passes**:
   ```bash
   pytest -vv tests/dbex/test_u_matrix_gradcheck.py::test_quaternion_roundtrip \
     > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T112058Z/pytest_quaternion_roundtrip.log 2>&1
   ```
   **Expected:** `PASSED` (no regression in B2 quaternion ops)

5. **Commit the bugfix**:
   ```bash
   git add dbex/nanobrag_refinement.py
   git add plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T112058Z/*.log
   git commit -m "$(cat <<'COMMIT_MSG'
TORCH-GEOMETRY-PARITY-002 Phase B bugfix: Move misset_deg_for_crystal into if/else branches (tests: test_stage_a_expansion)

Fixes scoping bug from commit 2793ba9 where `misset_deg_for_crystal` assignment
at line 1015 (Stage A) and ~1428 (Stage C) referenced `misset_xyz_deg` before it was defined.

Root cause: `misset_xyz_deg` is only defined inside the cell+misset else-branch,
but the assignment `misset_deg_for_crystal = None if use_u_matrix else misset_xyz_deg`
occurred OUTSIDE the if/else block, causing NameError when U-matrix path was taken.

Fix: Moved `misset_deg_for_crystal` assignment into each branch:
- U-matrix path (if): `misset_deg_for_crystal = None`
- Cell+misset path (else): `misset_deg_for_crystal = misset_xyz_deg`

Validated:
- test_stage_a_expansion: PASSED (regression guard)
- test_quaternion_roundtrip: PASSED (no regression in quaternion ops)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
COMMIT_MSG
)"
   git push
   ```

## How-To Map

1. **Locate scoping bug in Stage A closure:**
   - File: `dbex/nanobrag_refinement.py`
   - Search for: `if config.use_u_matrix_parameterization:` (around line 968)
   - Find assignment: `misset_deg_for_crystal = None if config.use_u_matrix_parameterization else misset_xyz_deg` (around line 1015)

2. **Apply fix pattern:**
   - Inside `if` branch (after `crystal_overrides` dict): add `misset_deg_for_crystal = None`
   - Inside `else` branch (after `crystal_overrides` dict): add `misset_deg_for_crystal = misset_xyz_deg`
   - Remove the assignment outside the if/else block

3. **Repeat for Stage C closure** (search for similar pattern around line 1404-1448)

4. **Test validation:**
   - Run test_stage_a_expansion with default config (use_u_matrix_parameterization=False) to validate cell+misset path unaffected
   - Run test_quaternion_roundtrip to validate B2 quaternion ops remain stable

## Pitfalls To Avoid

1. **Do not** introduce any other changes to the closures—this is a targeted scoping bugfix only
2. **Do not** change the logic of when `misset_deg_for_crystal` is None vs set—only move the assignments into proper scope
3. **Do not** modify the U-matrix or cell+misset parameterization logic—the bug is purely variable scoping
4. **Do not** skip the regression guard—we must verify backward compatibility preserved
5. **Environment:** Frozen. This is a local source bugfix (allowed per Environment Freeze exception). No package installs.

## If Blocked

If the fix doesn't resolve the NameError or introduces new failures:
1. Check that both closures (Stage A line ~968-1015 AND Stage C line ~1404-1448) were fixed
2. Verify `misset_deg_for_crystal` appears exactly twice in each branch (once in `if`, once in `else`)
3. Verify the line outside the if/else block was removed
4. Capture full pytest traceback in artifacts
5. Record the blocker in `docs/fix_plan.md` Attempts History with error signature

## Findings Applied

**Relevant findings from `docs/findings.md`:**
- (None directly relevant—this is a regression bug from Phase B implementation, not a known pattern)

**GEOMETRY-003** (baseline misset path) remains the default; U-matrix path is opt-in via config flag per Phase B design.

## Pointers

- **Bug Report:** `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T112058Z/phase_b_regression_bug_report.md` (comprehensive diagnosis with code examples)
- **Prior Regression Log:** `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/pytest_stage_a_regression.log` (shows original NameError)
- **Implementation Plan:** `plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md` (Phase B checklist B1-B5 conceptually complete pending this bugfix)
- **Fix Plan Entry:** `docs/fix_plan.md` — Row `[TORCH-GEOMETRY-PARITY-002]`

## Next Up

After this bugfix lands and test_stage_a_expansion PASSED:
1. **Phase C Parity Validation** — Extend `probe_crystal_matrix_parity.py` with `--use-u-matrix` flag (Phase B6)
2. **Phase C1 Parity Test** — Run parity probe with U-matrix mode, verify `max_abs_diff < 1e-6`
3. **Phase C2/C3 Convergence** — Run Phase 5 validation (scale-only + full-DoF variants), verify CC ≥ 0.99
4. **Phase C Findings Update** — Add GEOMETRY-004 to `docs/findings.md` documenting U-matrix parameterization
