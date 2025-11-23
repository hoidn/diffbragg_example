# Phase B1a Extraction — Nonlocal Variables and Boundaries

**Date:** 2025-11-23T032647Z
**Initiative:** ARCH-REFINE-FLOW-001
**Task:** Extract Stage A helper functions from inline LBFGS closure

## Extraction Boundaries

### Section 1: Parameter Initialization (`_build_stage_a_params`)
**Lines:** 761-935 (approximately 175 lines)
**Returns:** Dict with keys:
- `params`: List of trainable tensors for optimizer
- `param_values`: Dict mapping parameter names to tensors
- `telemetry_state`: Dict with accumulators
- `stage_a_context`: Dict with ROI sampling, warm-cache ctx, canonical baselines
- `optimizer`: torch.optim.LBFGS instance

**Responsibilities:**
1. Initialize trainable parameters (log_scale, cell deltas, angle deltas, orientation_vec)
2. Handle 3 parameterization modes:
   - Default cell+misset path (lines 770-786)
   - U-matrix quaternion path (lines 791-815, if `config.use_u_matrix_parameterization`)
   - Incremental UB path (lines 833-856, if `config.use_incremental_ub`)
3. Setup LBFGS optimizer (lines 878-886)
4. Initialize telemetry accumulators (lines 888-913)
5. Setup ROI/panel sampling (lines 915-969)
6. Build Stage A context (lines 971-988, if `config.enable_stage_a_warm_cache`)
7. Initialize lifecycle tracking (lines 990-996)

### Section 2: LBFGS Closure (`_build_stage_a_lbfgs_closure`)
**Lines:** 998-1573 (approximately 575 lines)
**Returns:** Tuple `(closure, compute_loss)`
- `closure`: LBFGS closure function (no args, returns chi_squared_loss)
- `compute_loss`: Nested compute_loss function (needed by _run_stage_a_lbfgs for final validation)

**Responsibilities:**
1. Define `compute_loss(work_item_ids, is_full)` nested function (lines 998-1406)
   - Variance-weighted chi-squared loss computation
   - Support for 3 parameterization modes
   - Warm/cold cache branches
   - Telemetry capture (U-matrix lifecycle, A* reconstruction)
   - Performance counters
2. Define `closure()` nested function (lines 1408-1573)
   - Zero gradients
   - Call compute_loss on sampled indices
   - Backward pass
   - Gradient validation (NaN/Inf check)
   - Gradient telemetry (if U-matrix mode)
   - Periodic full validation
   - Best params snapshot tracking
   - Lifecycle JSON emission

### Section 3: LBFGS Execution (`_run_stage_a_lbfgs`)
**Lines:** 1575-1685 (approximately 110 lines)
**Returns:** Tuple `(status, message, final_chi_squared_value, final_masked_mse_value)`
- status: "ok" | "early_stop" | "error"
- message: str (convergence message or error)
- final_chi_squared_value: Optional[float]
- final_masked_mse_value: Optional[float]

**Responsibilities:**
1. Execute `optimizer.step(closure)` (line 1583)
2. Final full validation (lines 1585-1625)
3. Convergence check (lines 1626-1634, ≥0.2% improvement gate per REFINE-006)
4. Exception handling with best params rollback (lines 1636-1648)
5. Fallback telemetry population (lines 1650-1684)

## Nonlocal Variables Accessed by Closures

### Inputs (from run_nanobrag_refinement signature)
- `inputs`: RefinementInputs (target, loss_mask, sigma_readout, panel_slices, etc.)
- `config`: RefinementConfig (all optimization/telemetry settings)
- `device`: torch.device
- `dtype`: torch.dtype
- `detector`: dxtbx Detector
- `beam`: dxtbx Beam
- `crystal`: dxtbx Crystal
- `hkl_grid`: torch.Tensor
- `hkl_metadata`: Dict
- `baseline_crystal`: Optional[dxtbx Crystal]
- `baseline_detector`: Optional[dxtbx Detector]

### Trainable Parameters (initialized in Section 1)
- `log_scale`: torch.Tensor (requires_grad=True)
- `log_cell_a_delta`, `log_cell_b_delta`, `log_cell_c_delta`: torch.Tensor
- `angle_alpha_raw`, `angle_beta_raw`, `angle_gamma_raw`: torch.Tensor
- `orientation_vec`: torch.Tensor (3D)
- `q_params`: Optional[torch.Tensor] (4D quaternion, U-matrix mode only)
- `B_ideal_reciprocal_torch`: Optional[torch.Tensor] (U-matrix mode only)
- `q_delta`: Optional[torch.Tensor] (4D quaternion, incremental UB mode only)
- `delta_log_a/b/c`: Optional[torch.Tensor] (incremental UB mode only)
- `delta_alpha/beta/gamma`: Optional[torch.Tensor] (incremental UB mode only)
- `U_baseline`: Optional[torch.Tensor] (3x3, incremental UB mode only)
- `cell_baseline`: Optional[torch.Tensor] (6D, incremental UB mode only)
- `params`: List[torch.Tensor] (all trainable params for optimizer)

### Telemetry Accumulators (initialized in Section 1)
- `loss_trace_sample`: List[float] (deprecated legacy field)
- `loss_trace_full`: List[Tuple[int, float]] (deprecated legacy field)
- `best_loss_full`: Tuple[float, int] (deprecated legacy field)
- `best_params_snapshot`: Optional[Dict]
- `iteration_count`: List[int] (mutable counter)
- `chi_squared_trace_sample`: List[float]
- `chi_squared_trace_full`: List[Tuple[int, float]]
- `chi_squared_best`: Tuple[float, int]
- `masked_mse_trace_sample`: List[float]
- `masked_mse_trace_full`: List[Tuple[int, float]]
- `masked_mse_best`: Tuple[float, int]
- `perf_closure_evals`: List[int]
- `perf_validation_runs`: List[int]
- `perf_forward_times_ms`: List[float]
- `variance_floor_clamped_pixels`: List[int]
- `variance_floor_masked_pixels`: List[int]
- `telemetry_step_counter`: List[int]
- `u_matrix_lifecycle_log`: List (U-matrix mode only)
- `a_star_lifecycle_log`: List (U-matrix mode only)

### Stage A Context (initialized in Section 1)
- `sigma_floor_sq_tensor`: torch.Tensor (cached via _get_sigma_floor_sq_tensor)
- `sigma_floor_sq_cache`: Dict (shared cache, passed from run_nanobrag_refinement)
- `canonical_roi_count`: int
- `canonical_detector_distances`: List[float]
- `canonical_baseline`: Dict (stage_label, chi_squared, iteration, roi_count, detector_distances_mm)
- `sampled_stage_a_indices`: List[int]
- `full_stage_a_indices`: List[int]
- `stage_a_ctx`: Optional[StageAContext] (warm-cache mode)
- `use_stage_a_roi_mode`: bool
- `stage_a_roi_label`: str ("roi" or "panel")
- `stage_a_total_work_items`: int

### Other Nonlocal State
- `n_panels`: int
- `panel_shape`: Tuple[int, int]
- `panel_slices`: List (from inputs)
- `baseline_detector_distances`: Optional[List[float]]
- `sampled_panel_ids`: List[int]

## Helper Function Signatures

### 1. `_build_stage_a_params`

```python
def _build_stage_a_params(
    crystal,
    detector,
    inputs: RefinementInputs,
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    sigma_floor_sq_cache: Dict,
    baseline_crystal=None,
    baseline_detector=None
) -> Dict[str, Any]:
    """
    Initialize Stage A trainable parameters and telemetry state.

    Returns dict with keys:
    - 'params': List of trainable tensors for optimizer
    - 'param_values': Dict mapping parameter names to tensors (for closure access)
    - 'telemetry_state': Dict with accumulators (loss_trace_*, iteration_count, etc.)
    - 'stage_a_context': Dict with ROI sampling, warm-cache ctx, canonical baselines
    - 'optimizer': torch.optim.LBFGS instance
    """
```

**Detailed Return Structure:**

`param_values` dict (for closure access):
- `log_scale`, `log_cell_a_delta`, `log_cell_b_delta`, `log_cell_c_delta`
- `angle_alpha_raw`, `angle_beta_raw`, `angle_gamma_raw`
- `orientation_vec`
- `q_params`, `B_ideal_reciprocal_torch` (U-matrix mode only)
- `q_delta`, `delta_log_a/b/c`, `delta_alpha/beta/gamma`, `U_baseline`, `cell_baseline` (incremental UB mode only)

`telemetry_state` dict:
- `loss_trace_sample`, `loss_trace_full`, `best_loss_full` (deprecated)
- `best_params_snapshot`, `iteration_count`
- `chi_squared_trace_sample`, `chi_squared_trace_full`, `chi_squared_best`
- `masked_mse_trace_sample`, `masked_mse_trace_full`, `masked_mse_best`
- `perf_closure_evals`, `perf_validation_runs`, `perf_forward_times_ms`
- `variance_floor_clamped_pixels`, `variance_floor_masked_pixels`
- `telemetry_step_counter`
- `u_matrix_lifecycle_log`, `a_star_lifecycle_log` (U-matrix mode only)

`stage_a_context` dict:
- `sigma_floor_sq_tensor`
- `canonical_roi_count`, `canonical_detector_distances`, `canonical_baseline`
- `sampled_stage_a_indices`, `full_stage_a_indices`
- `stage_a_ctx` (StageAContext or None)
- `use_stage_a_roi_mode`, `stage_a_roi_label`, `stage_a_total_work_items`
- `n_panels`, `panel_shape`, `baseline_detector_distances`, `sampled_panel_ids`

### 2. `_build_stage_a_lbfgs_closure`

```python
def _build_stage_a_lbfgs_closure(
    param_values: Dict[str, torch.Tensor],
    telemetry_state: Dict[str, Any],
    stage_a_context: Dict[str, Any],
    inputs: RefinementInputs,
    detector,
    beam,
    crystal,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    optimizer: torch.optim.Optimizer,
    sigma_floor_sq_cache: Dict,
    baseline_crystal=None,
    baseline_detector=None
) -> Tuple[Callable[[], torch.Tensor], Callable[[List[int], bool], Tuple[torch.Tensor, torch.Tensor]]]:
    """
    Build LBFGS closure function for Stage A optimization.

    Returns tuple: (closure_fn, compute_loss_fn)
    - closure_fn: LBFGS closure that calls compute_loss + backward, returns chi_squared_loss
    - compute_loss_fn: The nested compute_loss function, needed by _run_stage_a_lbfgs for final validation

    The returned closure captures all parameters and state via lexical scope
    (following original inline pattern).

    Closure structure:
    1. Defines nested `compute_loss(work_item_ids, is_full)` function
    2. Defines nested `closure()` function that calls compute_loss + backward
    3. Returns tuple (closure, compute_loss)
    """
```

### 3. `_run_stage_a_lbfgs`

```python
def _run_stage_a_lbfgs(
    optimizer: torch.optim.Optimizer,
    closure: Callable[[], torch.Tensor],
    compute_loss_fn: Callable[[List[int], bool], Tuple[torch.Tensor, torch.Tensor]],
    param_values: Dict[str, torch.Tensor],
    telemetry_state: Dict[str, Any],
    stage_a_context: Dict[str, Any],
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype
) -> Tuple[str, str, Optional[float], Optional[float]]:
    """
    Execute LBFGS optimization and final validation.

    Returns tuple: (status, message, final_chi_squared_value, final_masked_mse_value)
    where status is "ok" | "early_stop" | "error"
    """
```

## Parameterization Mode Branching

The helpers must support 3 mutually exclusive geometry parameterization modes:

1. **Default cell+misset** (lines 770-786, 1040-1110):
   - Trainable: `log_scale`, `log_cell_a/b/c_delta`, `angle_alpha/beta/gamma_raw`, `orientation_vec`
   - Branch condition: `not config.use_u_matrix_parameterization and not config.use_incremental_ub`

2. **U-matrix quaternion** (lines 791-815, 1112-1149):
   - Trainable: `log_scale`, `q_params`
   - Branch condition: `config.use_u_matrix_parameterization`
   - Additional state: `B_ideal_reciprocal_torch`, `u_matrix_lifecycle_log`, `a_star_lifecycle_log`

3. **Incremental UB** (lines 833-856, 1036-1073):
   - Trainable: `log_scale`, `q_delta`, `delta_log_a/b/c`, `delta_alpha/beta/gamma`
   - Branch condition: `config.use_incremental_ub`
   - Additional state: `U_baseline`, `cell_baseline`

**Critical:** Each parameterization mode has different:
- Parameter initialization (Section 1)
- `params` list for optimizer (Section 1)
- Geometry construction inside `compute_loss` (Section 2)
- Best params snapshot structure (Section 2, lines 1540-1550)
- Best params rollback (Section 3, lines 1640-1648)

## Telemetry Field Access After Extraction

After extraction, the remaining code (lines ~1686-1900, final Bragg generation + telemetry packaging) needs access to:

### From `param_values` dict:
- `log_scale.item()` → `param_values['log_scale'].item()`
- `log_cell_a_delta.item()` → `param_values['log_cell_a_delta'].item()` (if cell+misset mode)
- `orientation_vec.detach().cpu().tolist()` → `param_values['orientation_vec'].detach().cpu().tolist()` (if cell+misset mode)
- `q_params` → `param_values.get('q_params')` (if U-matrix mode)
- `q_delta`, `delta_log_a/b/c`, `delta_alpha/beta/gamma` → `param_values.get('...')` (if incremental UB mode)

### From `telemetry_state` dict:
- `chi_squared_trace_full` → `telemetry_state['chi_squared_trace_full']`
- `masked_mse_trace_full` → `telemetry_state['masked_mse_trace_full']`
- `iteration_count[0]` → `telemetry_state['iteration_count'][0]`
- `perf_closure_evals[0]` → `telemetry_state['perf_closure_evals'][0]`
- `best_params_snapshot` → `telemetry_state['best_params_snapshot']`
- etc.

### From `stage_a_context` dict:
- `canonical_roi_count` → `stage_a_context['canonical_roi_count']`
- `canonical_baseline` → `stage_a_context['canonical_baseline']`
- `stage_a_roi_label` → `stage_a_context['stage_a_roi_label']`
- `use_stage_a_roi_mode` → `stage_a_context['use_stage_a_roi_mode']`
- `perf_forward_times_ms` → `telemetry_state['perf_forward_times_ms']` (telemetry state, not stage context)
- `stage_a_ctx` → `stage_a_context['stage_a_ctx']`

### From `_run_stage_a_lbfgs` return:
- `status`, `message`, `final_chi_squared_value`, `final_masked_mse_value`

## Extraction Strategy

1. **Preserve all logic exactly** — no simplification, no refactoring
2. **Lexical scope captures** — nested functions in `_build_stage_a_lbfgs_closure` access variables via closure, not parameters
3. **Mutable list pattern** — preserve `[0]` indexing for counters (iteration_count, perf_*, variance_floor_*)
4. **Comments** — preserve all TORCH-REFINE-*, PHYSICS-LOSS-*, PERF-WARM-SIM-* annotations
5. **Lazy imports** — keep nanobrag_bridge imports INSIDE nested functions (not at module level)
6. **Optimizer behavior** — LBFGS(params, history_size, ..., line_search_fn="strong_wolfe") must stay identical

## Risks and Mitigation

1. **Missing nonlocal variable** → Test with regression guard immediately after extraction
2. **Broken lexical scope** → Ensure nested functions in `_build_stage_a_lbfgs_closure` capture variables from outer scope
3. **Parameter flow bug** → Verify `param_values` dict is properly populated and accessed
4. **Telemetry field name drift** → Compare telemetry JSON structure with baseline
5. **Circular import** → Keep lazy imports inside nested functions
6. **Optimizer state reset** → Ensure optimizer is created in `_build_stage_a_params`, not inside closure

## Validation Checklist

- [ ] All 3 parameterization modes initialize correctly (cell+misset, U-matrix, incremental UB)
- [ ] `test_stage_a_expansion` PASSES with default config (cell+misset mode)
- [ ] Telemetry structure matches baseline (chi_squared_trace_full, masked_mse_trace_full, iteration_count)
- [ ] Performance counters populated (perf_closure_evals, perf_validation_runs, perf_forward_times_ms)
- [ ] Warm-cache context works (stage_a_ctx created and used in compute_loss)
- [ ] Final Bragg generation accesses params via `param_values` dict
- [ ] Telemetry packaging accesses state via `telemetry_state` dict
- [ ] No circular imports (nanobrag_bridge stays lazy)
- [ ] No linter/formatter warnings

## Next Steps

1. Extract `_build_stage_a_params` helper (lines ~761-935) → place before `run_nanobrag_refinement` (around line 650)
2. Extract `_build_stage_a_lbfgs_closure` helper (lines ~998-1573) → place after `_build_stage_a_params` (around line 900)
3. Extract `_run_stage_a_lbfgs` helper (lines ~1575-1685) → place after `_build_stage_a_lbfgs_closure` (around line 1400)
4. Refactor `run_nanobrag_refinement` to call helpers (replace lines ~761-1685 with ~20 lines of helper calls)
5. Update final Bragg generation + telemetry packaging to use dicts (lines ~1686-1900)
6. Run regression guard `test_stage_a_expansion`
7. Compare telemetry with baseline
8. Commit if all tests pass

