# Helper 1 Extraction Summary

**Date:** 2025-11-23T040000Z
**Loop:** i=192 (ralph)
**Initiative:** ARCH-REFINE-FLOW-001 Phase B1a-loop1

## Extracted Helper

**Function:** `_build_stage_a_params`
**Location:** dbex/nanobrag_refinement.py:680-1007 (added before run_nanobrag_refinement)
**Line Range (Source):** ~761-996 (original inline location in run_nanobrag_refinement)
**Line Count:** ~328 lines (including docstring + return statement + dict building)

## Parameters (12 total)

1. crystal
2. detector
3. inputs
4. config: RefinementConfig
5. device
6. dtype
7. hkl_grid
8. hkl_metadata
9. sigma_floor_sq_cache
10. baseline_crystal
11. baseline_detector
12. beam (added per i=191 Attempt 1 fix for MOSFLM A* calculation)

## Return Value

Dict with 5 keys:
- `params`: List[torch.nn.Parameter] — trainable parameters for optimizer
- `param_values`: Dict[str, torch.Tensor] — mapping of parameter names to tensors
- `telemetry_state`: Dict[str, Any] — mutable telemetry accumulators
- `stage_a_context`: Dict[str, Any] — ROI sampling state, warm cache context
- `optimizer`: torch.optim.LBFGS — configured optimizer instance

## Parameterization Modes Preserved

- [x] Default: cell + misset (lines 705-730, 802-820 in extracted helper)
- [x] U-matrix: config.use_u_matrix_parameterization (lines 732-759 in extracted helper)
- [x] Incremental UB: config.use_incremental_ub (lines 761-800 in extracted helper)

## Telemetry Fields Initialized

### Legacy (deprecated but preserved for backward compatibility):
- loss_trace_sample
- loss_trace_full
- best_loss_full
- best_params_snapshot

### Active (PHYSICS-LOSS-001 dual metric tracking):
- chi_squared_trace_sample
- chi_squared_trace_full
- chi_squared_best
- masked_mse_trace_sample
- masked_mse_trace_full
- masked_mse_best

### Performance counters (PERF-WARM-SIM-001):
- perf_closure_evals
- perf_validation_runs
- perf_forward_times_ms

### Variance floor tracking (PHYSICS-LOSS-002):
- variance_floor_clamped_pixels
- variance_floor_masked_pixels
- sigma_floor_sq_tensor

### Lifecycle tracking (TORCH-GEOMETRY-CONVERGENCE-001):
- telemetry_step_counter
- u_matrix_lifecycle_log (U-matrix mode only)
- a_star_lifecycle_log (U-matrix mode only)

### General state:
- iteration_count

## Stage A Context Fields

- stage_a_ctx: StageAContext object (warm cache mode)
- sampled_panel_ids: ROI panel sampling
- canonical_baseline: baseline state dict
- use_stage_a_roi_mode: boolean flag
- stage_a_roi_label: "roi" or "panel"
- stage_a_total_work_items: total work items count
- sampled_stage_a_indices: sampled indices for optimization
- full_stage_a_indices: all indices for validation

## Compilation Check

Status: PASSED
Exit code: 0
Log: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/compilation_check.log

## Implementation Notes

1. **Pure extraction**: No logic changes, copied lines 761-996 exactly from run_nanobrag_refinement
2. **Return structure**: Built three dict structures (param_values, telemetry_state, stage_a_context) to organize the return value
3. **Helper not wired**: The helper exists but is NOT called by run_nanobrag_refinement yet (no behavior change)
4. **All 3 parameterization modes preserved**: cell+misset, U-matrix quaternion, incremental UB
5. **Comments preserved**: All TORCH-REFINE-*, PHYSICS-LOSS-*, PERF-* annotations kept intact
6. **No new imports**: All imports remain as they were in the original code

## Next Steps (Loop i=193)

Extract `_build_stage_a_lbfgs_closure` helper (~575 lines with TWO nested functions: compute_loss and closure).
This is more complex than helper 1 as it requires lexical scope preservation for ~30 nonlocal variables.
