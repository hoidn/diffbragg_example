# Helper 2 Extraction Summary

**Date:** 2025-11-23T050000Z
**Loop:** i=193 (ralph)
**Initiative:** ARCH-REFINE-FLOW-001 Phase B1a-loop2

## Extracted Helper

**Function:** `_build_stage_a_lbfgs_closure`
**Location:** dbex/nanobrag_refinement.py:1010-1726 (added after _build_stage_a_params)
**Line Range (Source):** 1320-1903 (original inline location in run_nanobrag_refinement)
**Line Count:** ~717 lines (including variable unpacking, nested functions, return statement)

## Parameters (15 total)

1. param_values: Dict[str, Any]
2. telemetry_state: Dict[str, Any]
3. stage_a_context: Dict[str, Any]
4. crystal
5. detector
6. beam
7. inputs
8. hkl_grid: torch.Tensor
9. hkl_metadata: Dict
10. config: RefinementConfig
11. sigma_floor_sq_cache: Optional[Dict]
12. device
13. dtype
14. baseline_crystal

## Nonlocal Variables Captured (~35 total)

### From param_values:
- log_scale, log_cell_a/b/c_delta, angle_alpha/beta/gamma_raw
- orientation_vec (cell+misset mode)
- q_params, B_ideal_reciprocal_torch (U-matrix mode)
- delta_log_a/b/c, delta_alpha/beta/gamma, q_delta (incremental UB mode)
- U_baseline, cell_baseline (incremental UB mode)
- params (list of Parameter objects)

### From telemetry_state:
- iteration_count, loss_trace_sample/full, best_loss_full, best_params_snapshot
- chi_squared_trace_sample/full, chi_squared_best
- masked_mse_trace_sample/full, masked_mse_best
- perf_closure_evals, perf_validation_runs, perf_forward_times_ms
- variance_floor_clamped_pixels, variance_floor_masked_pixels, sigma_floor_sq_tensor
- telemetry_step_counter, u_matrix_lifecycle_log, a_star_lifecycle_log

### From stage_a_context:
- stage_a_ctx, sampled_panel_ids, use_stage_a_roi_mode
- sampled_stage_a_indices, full_stage_a_indices

### Additional context extracted in helper body:
- target_t, loss_mask_t, sigma_readout_t (from inputs)
- baseline_misset_deg_tensor (computed via compute_baseline_misset_deg)
- n_panels, panel_slices

## Nested Functions Preserved

- [x] `def compute_loss(work_item_ids, is_full=False)` (lines 1141-1556 in extracted helper)
- [x] `def closure()` (lines 1558-1724 in extracted helper)

## Parameterization Modes Preserved

- [x] Default: cell + misset (lines ~1276-1295 in extracted helper, orientation_vec)
- [x] U-matrix: config.use_u_matrix_parameterization (lines ~1218-1275 in extracted helper, q_params)
- [x] Incremental UB: config.use_incremental_ub (lines ~1179-1216 in extracted helper, q_delta + delta_log/delta_angles)

## Lazy Imports Preserved

- [x] `from dbex.nanobrag_bridge import derive_orientation_from_quaternion_delta, derive_B_from_cell_deltas` INSIDE `if config.use_incremental_ub:` branch (lines ~1181-1184 in extracted helper)
- [x] `from dbex.nanobrag_bridge import quaternion_to_matrix` INSIDE `elif config.use_u_matrix_parameterization:` branch (line ~1220 in extracted helper)
- [x] `from nanobrag_torch.models.crystal import Crystal` INSIDE cold path branches (multiple locations)
- [x] `from nanobrag_torch.models.detector import Detector` INSIDE cold path branches (multiple locations)
- [x] `from nanobrag_torch.simulator import Simulator` INSIDE cold path branches (multiple locations)

## Return Value

Tuple of (compute_loss, closure) callables

## Compilation Check

Status: PASSED
Exit code: 0
Log: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/compilation_check.log

## Implementation Notes

1. **Pure extraction**: No logic changes, copied lines 1320-1903 from run_nanobrag_refinement's inline closure
2. **Variable unpacking**: Added explicit unpacking of ~35 variables from param_values, telemetry_state, stage_a_context dicts at function start
3. **Additional context extraction**: Extracted target_t, loss_mask_t, sigma_readout_t, baseline_misset_deg_tensor, n_panels, panel_slices at helper start (needed by both nested functions)
4. **Helper not wired**: The helper exists but is NOT called by run_nanobrag_refinement yet (no behavior change)
5. **All 3 parameterization modes preserved**: cell+misset, U-matrix quaternion, incremental UB
6. **Comments preserved**: All TORCH-REFINE-*, PHYSICS-LOSS-*, PERF-*, TORCH-GEOMETRY-* annotations kept intact
7. **Lazy imports preserved**: All conditional imports remain INSIDE their respective branches
8. **No new imports**: All imports remain as they were in the original code
9. **TWO nested functions**: compute_loss (~415 lines) and closure (~167 lines) both extracted intact

## Next Steps (Loop i=194)

Extract `_run_stage_a_lbfgs` helper (~110 lines), refactor `run_nanobrag_refinement` to call all three helpers (~925→~50 lines), and run regression guard test_stage_a_expansion.
