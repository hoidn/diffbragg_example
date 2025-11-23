# Phase C1a-loop1 Planning Summary

## Objective
Extract `_build_stage_b_params` helper function ONLY (~140 lines) from Stage B inline code in `run_nanobrag_refinement`. Verify compilation. Commit partial progress.

## Scope Boundary
**CRITICAL:** This loop extracts ONLY helper 1. Helpers 2 and 3 come in subsequent loops (C1a-loop2, C1a-loop3).

## Strategy
Following proven Phase B multi-loop extraction pattern:
- Phase B1a-loop1: Extracted `_build_stage_a_params` (~335 lines) ✓ SUCCESS
- Phase B1a-loop2: Extracted `_build_stage_a_lbfgs_closure` (~716 lines) ✓ SUCCESS
- Phase B1a-loop3: Extracted `_run_stage_a_lbfgs` + refactored main function ✓ SUCCESS

Phase C mirrors this pattern:
- **Phase C1a-loop1 (THIS LOOP):** Extract `_build_stage_b_params` (~140 lines)
- Phase C1a-loop2 (NEXT): Extract `_build_stage_b_lbfgs_closure` (~260 lines, TWO nested functions)
- Phase C1a-loop3 (FUTURE): Extract `_run_stage_b_lbfgs` (~100 lines) + refactor main function

## Helper 1 Extraction Details

### Source Lines
Approximately lines 2570-2710 in `dbex/nanobrag_refinement.py` (Stage B initialization block)

### Key Components
1. **Shell Modifier Parameters:** `shell_modifier_raw` initialization
2. **Optimizer:** Adam with `config.stage_b_lr`
3. **Telemetry Accumulators:**
   - `chi_squared_trace_full_b`, `chi_squared_best_b`
   - `masked_mse_trace_sample_b`, `masked_mse_trace_full_b`, `masked_mse_best_b`
   - `default_f_fallback_count`
   - `variance_floor_clamped_pixels_b`, `variance_floor_masked_pixels_b`
4. **CPU Fallback Context (PERF-WARM-011/012):**
   - `use_stage_b_cpu_fallback` logic
   - `stage_b_eval_stage_a_ctx` (cloned CPU context or original CUDA context)
5. **ROI/Panel Mode Configuration:**
   - `use_stage_b_roi_mode`, `stage_b_roi_label`
   - `stage_b_total_work_items`, `sampled_stage_b_indices`, `full_stage_b_indices`
6. **Perf Counters:**
   - `perf_closure_evals_b`, `perf_validation_runs_b`, `perf_forward_times_ms_b`

### Function Signature
```python
def _build_stage_b_params(
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    stage_a_ctx: Optional[Dict[str, Any]],
    canonical_baseline: Dict[str, Any],
    n_panels: int,
    sampled_panel_ids: List[int],
    sigma_floor_sq_cache: Dict[torch.device, torch.Tensor],
    use_stage_a_roi_mode: bool,
) -> Dict[str, Any]:
```

### Return Dict Keys
All variables needed by Stage B LBFGS closure (helper 2):
- `params: List[torch.Tensor]`
- `optimizer: torch.optim.Adam`
- `telemetry_state: Dict` (all trace/counter lists)
- `stage_b_eval_stage_a_ctx: Optional[Dict]`
- `use_stage_b_cpu_fallback: bool`
- `stage_b_use_warm_cache: bool`
- `stage_b_cache_mode: str`
- `use_stage_b_roi_mode: bool`
- `stage_b_roi_label: str`
- `stage_b_total_work_items: int`
- `sampled_stage_b_indices: List[int]`
- `full_stage_b_indices: List[int]`
- `default_f_fallback_count: int`

## Validation Criteria
1. **Compilation:** `python -c "import dbex.nanobrag_refinement"` exits with code 0
2. **Diff Generated:** Patch file saved to artifacts directory
3. **No Runtime Changes:** Helper not wired yet, so NO test execution required
4. **Commit Clean:** git commit succeeds, git push succeeds

## Expected Outcomes
- New function `_build_stage_b_params` added at line ~2086
- File size increases by ~140 lines (new function definition)
- No behavior changes (helper not called yet)
- Clean compilation
- Partial progress committed

## Risk Mitigation
- **Scope Creep:** Explicitly bounded to helper 1 only
- **State Loss:** Commit immediately after compilation success
- **Complexity:** ~140 lines << 575 lines (Phase B helper 2), manageable in one loop
- **Dependencies:** All imports already present in file

## Next Loop Preview
Phase C1a-loop2 will extract `_build_stage_b_lbfgs_closure` (~260 lines with TWO nested functions: `compute_loss_stage_b` + `closure_stage_b`). This is the most complex extraction, mirroring Phase B1a-loop2.

---
Created: 2025-11-22T060833Z
Loop: i=202 (supervisor)
