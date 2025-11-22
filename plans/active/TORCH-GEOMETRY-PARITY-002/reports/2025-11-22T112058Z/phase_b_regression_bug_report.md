# Phase B Regression Bug Report

**Initiative:** TORCH-GEOMETRY-PARITY-002
**Date:** 2025-11-22T112058Z
**Phase:** B (Implementation) — Regression from commit 2793ba9
**Severity:** High (blocks Phase C validation)

## Summary

Commit 2793ba9 (Phase B1-B5 U-matrix quaternion parameterization) introduced a scoping bug causing `NameError: name 'misset_deg_for_crystal' is not defined` in the Stage A closure. The variable `misset_deg_for_crystal` is assigned at line 1015 using `misset_xyz_deg`, which is only defined inside the `else` branch (line 997, cell+misset path). In the U-matrix path (`if` branch), `misset_xyz_deg` does not exist.

## Error Signature

```
FAILED tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion - NameError: name 'misset_deg_for_crystal' is not defined
```

**Test selector:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
```

## Root Cause

**File:** `dbex/nanobrag_refinement.py`
**Function:** `build_stage_a_lbfgs_closure` (within the returned `closure()` function)

### Current Code (lines 968-1015, broken):

```python
# 3. Orientation perturbation via quaternion→XYZ misset (TORCH-REFINE-002)
# TORCH-GEOMETRY-PARITY-002 Phase B5: Branch on U-matrix vs cell+misset path
if config.use_u_matrix_parameterization:
    # U-matrix path: Normalize quaternion, convert to U, compute A*
    from dbex.nanobrag_bridge import quaternion_to_matrix
    q_norm = q_params / torch.norm(q_params)  # Enforce ||q|| = 1
    U = quaternion_to_matrix(q_norm)  # 3x3 rotation matrix
    A_star_new = U @ B_ideal_reciprocal_torch  # Compute updated A*

    # Convert A* to numpy for crystal_overrides
    A_star_np = A_star_new.detach().cpu().numpy()
    mosflm_a_star_tuple = tuple(A_star_np[:, 0].tolist())
    mosflm_b_star_tuple = tuple(A_star_np[:, 1].tolist())
    mosflm_c_star_tuple = tuple(A_star_np[:, 2].tolist())

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
else:
    # Existing cell+misset path (GEOMETRY-003)
    max_orientation_deg = 3.0  # degrees (per input.md pitfalls)
    bounded_orientation_vec = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
    quat = vec_to_unit_quaternion(bounded_orientation_vec)
    misset_xyz_deg = quaternion_to_xyz_euler(quat)  # <-- ONLY DEFINED HERE

    if baseline_misset_deg_tensor is not None:
        misset_xyz_deg = misset_xyz_deg + baseline_misset_deg_tensor

    crystal_overrides = {
        'cell_a': perturbed_cell_a,
        'cell_b': perturbed_cell_b,
        'cell_c': perturbed_cell_c,
        'cell_alpha': perturbed_alpha,
        'cell_beta': perturbed_beta,
        'cell_gamma': perturbed_gamma
    }

log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
beam_config_for_run = stage_a_ctx.beam_config if stage_a_ctx is not None else create_beam_config(beam)

# U-matrix path: misset_deg should be zero since MOSFLM A* is provided directly
misset_deg_for_crystal = None if config.use_u_matrix_parameterization else misset_xyz_deg
# <-- BUG: In U-matrix path, misset_xyz_deg is undefined, causing NameError
```

### Problem

Line 1015 references `misset_xyz_deg`, which only exists in the `else` branch (cell+misset path, line 997). When `config.use_u_matrix_parameterization=True`, the `if` branch is taken, `misset_xyz_deg` is never defined, and line 1015 raises `NameError`.

## Fix

Move the `misset_deg_for_crystal` assignment INSIDE each branch where the required variables are in scope:

### Corrected Code:

```python
# 3. Orientation perturbation via quaternion→XYZ misset (TORCH-REFINE-002)
# TORCH-GEOMETRY-PARITY-002 Phase B5: Branch on U-matrix vs cell+misset path
if config.use_u_matrix_parameterization:
    # U-matrix path: Normalize quaternion, convert to U, compute A*
    from dbex.nanobrag_bridge import quaternion_to_matrix
    q_norm = q_params / torch.norm(q_params)  # Enforce ||q|| = 1
    U = quaternion_to_matrix(q_norm)  # 3x3 rotation matrix
    A_star_new = U @ B_ideal_reciprocal_torch  # Compute updated A*

    # Convert A* to numpy for crystal_overrides
    A_star_np = A_star_new.detach().cpu().numpy()
    mosflm_a_star_tuple = tuple(A_star_np[:, 0].tolist())
    mosflm_b_star_tuple = tuple(A_star_np[:, 1].tolist())
    mosflm_c_star_tuple = tuple(A_star_np[:, 2].tolist())

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
    # U-matrix path: misset_deg should be None since MOSFLM A* is provided directly
    misset_deg_for_crystal = None  # <-- FIX: Define here in U-matrix branch
else:
    # Existing cell+misset path (GEOMETRY-003)
    max_orientation_deg = 3.0  # degrees (per input.md pitfalls)
    bounded_orientation_vec = torch.tanh(orientation_vec) * max_orientation_deg * (np.pi / 180.0)
    quat = vec_to_unit_quaternion(bounded_orientation_vec)
    misset_xyz_deg = quaternion_to_xyz_euler(quat)

    if baseline_misset_deg_tensor is not None:
        misset_xyz_deg = misset_xyz_deg + baseline_misset_deg_tensor

    crystal_overrides = {
        'cell_a': perturbed_cell_a,
        'cell_b': perturbed_cell_b,
        'cell_c': perturbed_cell_c,
        'cell_alpha': perturbed_alpha,
        'cell_beta': perturbed_beta,
        'cell_gamma': perturbed_gamma
    }
    # Cell+misset path: misset_deg comes from orientation_vec → quaternion → Euler
    misset_deg_for_crystal = misset_xyz_deg  # <-- FIX: Define here in cell+misset branch

log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
beam_config_for_run = stage_a_ctx.beam_config if stage_a_ctx is not None else create_beam_config(beam)
# <-- REMOVED: misset_deg_for_crystal = None if config.use_u_matrix_parameterization else misset_xyz_deg
```

**ALSO:** The same pattern appears in a second closure (Stage C closure, lines ~1404-1448). Apply the identical fix there.

### Locations to Edit

1. **First closure** (Stage A LBFGS closure, around line 968-1015):
   - Add `misset_deg_for_crystal = None` at the end of the `if` branch (after `crystal_overrides` dict, before closing brace).
   - Add `misset_deg_for_crystal = misset_xyz_deg` at the end of the `else` branch (after `crystal_overrides` dict, before closing brace).
   - Remove line 1015: `misset_deg_for_crystal = None if config.use_u_matrix_parameterization else misset_xyz_deg`

2. **Second closure** (Stage C closure, around line 1404-1448):
   - Same pattern: move `misset_deg_for_crystal` assignment into each branch.

## Test Validation

After fix, re-run the regression guard:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
```

Expected: `PASSED` (test runs with default `use_u_matrix_parameterization=False`, exercises cell+misset path).

## Impact

**Current state:**
- Phase B checklist items B1-B5 are conceptually complete (helpers, config, initialization, closure branching implemented).
- BUT: regression bug blocks test_stage_a_expansion, preventing validation that backward compatibility is preserved.
- Phase C validation (B6 parity probe extension, B7 gradcheck, C1-C7) cannot proceed until regression is fixed.

**After fix:**
- test_stage_a_expansion should pass (validates no regression in cell+misset path).
- Can proceed to Phase C: extend parity probe with --use-u-matrix flag, run C1 parity validation, C2/C3 Phase 5 convergence tests.

## Artifacts

- **Bug Report:** `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T112058Z/phase_b_regression_bug_report.md` (this file)
- **Prior Regression Test Log:** `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/pytest_stage_a_regression.log` (shows NameError)

## Next Steps

1. Ralph applies the scoping fix to both closures (Stage A and Stage C).
2. Ralph re-runs `test_stage_a_expansion` and confirms PASSED.
3. Ralph commits with message: `TORCH-GEOMETRY-PARITY-002 Phase B bugfix: Move misset_deg_for_crystal into if/else branches (tests: test_stage_a_expansion)`
4. Galph proceeds to Phase C Do Now (parity probe extension + validation).
