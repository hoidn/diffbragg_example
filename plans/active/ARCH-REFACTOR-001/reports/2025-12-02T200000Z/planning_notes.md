# ARCH-REFACTOR-001 Phase C.7-C.9: Stage A Consolidation Planning
**Date**: 2025-12-02T200000Z
**Loop**: Galph planning (dwell=0, Problems ledger "PRIORITIZE ARCH-REFACTOR-001 ASAP")
**Outcome**: Ready for Phase C.7 implementation

## Context
Phase C.6 complete (Stage B impl deleted). Stage A remains as the final `*_impl.py` module. Must follow the same pattern as Stage B/C:
- Inline helpers into StageA class
- Update cross-stage import sites (Stage B, Stage C, reconstruction.py)
- Delete stage_a_impl.py

## Current State Analysis

### stage_a_impl.py Functions (11 total)
```
1. vec_to_unit_quaternion         — quaternion math utility
2. quaternion_to_rotation_matrix  — quaternion math utility
3. quaternion_to_xyz_euler        — quaternion math utility
4. _sync_stage_a_crystal          — warm-cache helper
5. _retarget_stage_a_simulators   — warm-cache helper (used by Stage B/C/reconstruction)
6. _build_stage_a_context         — context factory (used by Stage B)
7. _get_sigma_floor_sq_tensor     — variance helper (used by Stage B)
8. _clamp_log_cell_deltas         — parameter clamping (used by Stage C/reconstruction)
9. _build_stage_a_params          — parameter factory
10. _compute_panel_loss           — loss computation (used by Stage C)
11. _run_stage_a_lbfgs            — LBFGS loop
```

### Import Dependencies
- **stage_a.py**: imports all 11 functions (owns them)
- **stage_b.py**: imports `_retarget_stage_a_simulators`, `_get_sigma_floor_sq_tensor`, `_build_stage_a_context`
- **stage_c.py**: imports `vec_to_unit_quaternion`, `quaternion_to_xyz_euler`, `_clamp_log_cell_deltas`, `_retarget_stage_a_simulators`, `_compute_panel_loss`
- **reconstruction.py**: imports `_clamp_log_cell_deltas`, `_retarget_stage_a_simulators`

### Strategy: Two-Step Consolidation

#### Step 1: Extract Shared Utilities (Phase C.7)
Create `dbex/refinement/stage_a_utils.py` for cross-stage helpers:
- `_retarget_stage_a_simulators` (used by Stage B, C, reconstruction)
- `_get_sigma_floor_sq_tensor` (used by Stage B)
- `_build_stage_a_context` (used by Stage B)
- `_compute_panel_loss` (used by Stage C)
- `_clamp_log_cell_deltas` (used by Stage C, reconstruction)
- Quaternion utilities: `vec_to_unit_quaternion`, `quaternion_to_rotation_matrix`, `quaternion_to_xyz_euler` (used by Stage C)

Rationale: Following ARCH-REFACTOR-001 Phase C.5 precedent (hkl_utils.py extracted from Stage B impl), shared helpers get their own module before deletion to avoid circular dependencies.

#### Step 2: Inline Stage A-Specific Logic (Phase C.8)
Move into StageA class as private methods:
- `_sync_stage_a_crystal` → `StageA._sync_crystal()`
- `_build_stage_a_params` → `StageA._build_stage_a_params()`
- `_run_stage_a_lbfgs` → `StageA._run_lbfgs()`

#### Step 3: Clean Up (Phase C.9)
- Delete `dbex/refinement/stage_a_impl.py`
- Verify no stale imports remain

## Phase C.7 Implementation Plan

### Files to Create
1. `dbex/refinement/stage_a_utils.py` — Extract 7 shared helpers from stage_a_impl.py (lines TBD, ~600 lines)

### Files to Update
2. `dbex/refinement/stage_a.py` — Import shared helpers from stage_a_utils instead of stage_a_impl
3. `dbex/refinement/stage_b.py` — Update import from stage_a_impl → stage_a_utils
4. `dbex/refinement/stage_c.py` — Update import from stage_a_impl → stage_a_utils
5. `dbex/refinement/reconstruction.py` — Update import from stage_a_impl → stage_a_utils

### Validation Selectors
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (Stage A smoke)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (Stage B smoke, uses Stage A helpers)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (Stage C smoke, uses Stage A helpers)
- `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload` (Stage B guard, uses `_build_stage_a_context`)

### Spec/Finding Alignment
- ARCH-ENGINE-002: Stage wrappers are canonical seams
- ARCH-STAGE-CTX-001: Typed contexts only
- ARCH-TELEMETRY-001: Collector-first telemetry
- ARCH-REFACTOR-001: Delete impl modules after consolidation

## Risks & Mitigations
- **Risk**: Large file (1524 lines) increases likelihood of typos/import errors
  - **Mitigation**: Break into two phases (C.7 extract, C.8 inline, C.9 delete)

- **Risk**: Cross-stage dependencies create circular import risk
  - **Mitigation**: Follow hkl_utils.py precedent—extract shared helpers to standalone module first

- **Risk**: Reconstruction.py may have lazy imports or non-standard usage
  - **Mitigation**: Grep for inline imports before touching; preserve import semantics

## Exit Criteria (Phase C.7)
- [ ] `dbex/refinement/stage_a_utils.py` created with 7 shared helpers
- [ ] Stage A/B/C/reconstruction import from stage_a_utils (not stage_a_impl)
- [ ] All 4 mapped selectors PASSED (Stage A/B/C smokes + Stage B guard)
- [ ] stage_a_impl.py still exists but only exports 3 Stage-A-private helpers

## Next Actions
Phase C.7 Do Now:
1. Extract shared helpers to stage_a_utils.py
2. Update imports across 4 files
3. Run validation selectors
4. Capture artifacts under this directory
