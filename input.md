# Input for Ralph — ARCH-REFACTOR-001 Phase C.7: Stage A Utilities Extraction

## Summary
Extract 7 cross-stage Stage A helpers to `stage_a_utils.py` and update imports across 5 files, following the `hkl_utils.py` precedent from Phase C.5.

## Mode
Parity

## InitiativeType
architecture

## Focus
[ARCH-REFACTOR-001] — Refinement Engine Modularization & Physics Separation (Phase C.7)

## Branch
integration

## Mapped tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T200000Z/`

## Do Now

### 1. Create dbex/refinement/stage_a_utils.py
Extract 7 cross-stage helpers from dbex/refinement/stage_a_impl.py (identified in planning notes):

Helpers to extract:
- _retarget_stage_a_simulators (used by Stage B, C, reconstruction)
- _get_sigma_floor_sq_tensor (used by Stage B)
- _build_stage_a_context (used by Stage B)
- _compute_panel_loss (used by Stage C)
- _clamp_log_cell_deltas (used by Stage C, reconstruction)
- Quaternion utilities: vec_to_unit_quaternion, quaternion_to_rotation_matrix, quaternion_to_xyz_euler (used by Stage C)

Module header with spec cross-references (ARCH-ENGINE-002, ARCH-STAGE-CTX-001, GRADIENT-004, PERF-WARM-016).

Copy the function implementations verbatim from stage_a_impl.py. Preserve all imports, type hints, and docstrings.

### 2. Update dbex/refinement/stage_a.py
Split imports: keep Stage-A-private helpers (_sync_stage_a_crystal, _build_stage_a_params, _run_stage_a_lbfgs, _compute_variance_weighted_loss) from stage_a_impl; import the 5 shared helpers from stage_a_utils.

### 3. Update dbex/refinement/stage_b.py
Change imports of _retarget_stage_a_simulators, _get_sigma_floor_sq_tensor, _build_stage_a_context from stage_a_impl to stage_a_utils.

### 4. Update dbex/refinement/stage_c.py
Change imports of vec_to_unit_quaternion, quaternion_to_xyz_euler, _clamp_log_cell_deltas, _retarget_stage_a_simulators, _compute_panel_loss from stage_a_impl to stage_a_utils.

### 5. Update dbex/refinement/reconstruction.py
Find and update all inline imports (3 locations) from stage_a_impl to stage_a_utils.

### 6. Validation
Run all 4 mapped selectors with canonical environment. All must PASS. Capture logs under artifacts directory.

## How-To Map
Extract helpers to new module, update imports across 5 files, verify compilation, run validation suite.

## Pitfalls To Avoid
- Do not modify function bodies — copy verbatim
- Do not delete stage_a_impl.py yet — it still has 3 Stage-A-private helpers for Phase C.8
- Environment Freeze — no package installs
- Device/dtype neutrality (GRADIENT-004)
- Collector-only telemetry (ARCH-TELEMETRY-001)

## If Blocked
Record error signature, file:line, root cause hypothesis in Attempts History.

## Findings Applied
- ARCH-ENGINE-002: Stage wrappers are canonical seams
- ARCH-REFACTOR-001: Follow hkl_utils.py precedent (Phase C.5)
- ARCH-STAGE-CTX-001: Typed contexts only
- ARCH-TELEMETRY-001: Collector-first telemetry
- GRADIENT-004: Device/dtype neutrality

## Pointers
- Planning notes: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T200000Z/planning_notes.md
- Implementation plan: plans/active/ARCH-REFACTOR-001/implementation.md Phase C.7
- Fix plan: docs/fix_plan.md — Row [ARCH-REFACTOR-001]
- Testing: docs/TESTING_GUIDE.md §2

## Next Up
Phase C.8: Inline Stage-A-private helpers into StageA class
Phase C.9: Delete stage_a_impl.py

## Doc Sync Plan
Not applicable
