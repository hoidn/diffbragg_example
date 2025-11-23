### Turn Summary
Extracted _build_stage_b_lbfgs_closure helper (~317 lines including signature/docstring) with TWO nested functions (compute_loss_stage_b ~203 lines + closure_stage_b ~44 lines).
Helper not yet wired into runtime (no behavior change, compilation check PASSED).
Lexical scope preserved for ~24 param_values dict entries (params + telemetry accumulators), all PERF-WARM-SIM-001/011/012 modes intact, nonlocal mutations marked for 4 mutable accumulators.
Next loop (C1a-loop3) will extract _run_stage_b_lbfgs (~100 lines), wire all 3 helpers, and run regression guard test_stage_b_shell_modifiers.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T063000Z/ (phase_c1a_loop2_extraction_diff.patch, compilation_check.log)

---

# Phase C1a-loop2: Extract _build_stage_b_lbfgs_closure Helper

## Helper Signature

```python
def _build_stage_b_lbfgs_closure(
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    param_values: Dict[str, Any],
    stage_a_ctx: Optional[Dict[str, Any]],
    stage_b_eval_stage_a_ctx: Optional[Dict[str, Any]],
    canonical_baseline: Dict[str, Any],
    n_panels: int,
    sampled_stage_b_indices: List[int],
    full_stage_b_indices: List[int],
    sigma_floor_sq_cache: Dict[Tuple[str, str], torch.Tensor],
    use_stage_b_cpu_fallback: bool,
    stage_b_use_warm_cache: bool,
    use_stage_b_roi_mode: bool,
    crystal: Any,
    hkl_metadata: Dict[str, Any],
    hkl_grid: torch.Tensor,
    shell_indices: torch.Tensor,
    detector: Any,
    beam: Any,
    inputs: Any,
    target_t: torch.Tensor,
    loss_mask_t: torch.Tensor,
    sigma_readout_t: torch.Tensor,
    baseline_misset_deg_tensor: Optional[torch.Tensor],
    panel_shape: Tuple[int, int],
) -> Callable[[], torch.Tensor]:
```

## Line Count

- **Total helper function**: ~317 lines (including signature, docstring, param extraction, and both nested functions)
- **compute_loss_stage_b**: ~203 lines (lines 2336-2541 in final file)
- **closure_stage_b**: ~44 lines (lines 2543-2586 in final file)
- **Signature + param extraction**: ~70 lines
- **Patch file**: 339 lines total (including context and import change)

## Nested Functions Preserved

1. **compute_loss_stage_b** (lines 2336-2541):
   - Computes variance-weighted chi-squared loss with shell-modified structure factors
   - Handles ROI vs panel mode branching (PERF-WARM-SIM-001)
   - CPU fallback routing (PERF-WARM-011)
   - Warm cache support with eval-device context (PERF-WARM-012)
   - Force panel evaluation for validations (PERF-WARM-009)
   - Returns tuple of (chi_squared_loss, masked_mse_loss) for dual metric tracking (PHYSICS-LOSS-001)

2. **closure_stage_b** (lines 2543-2586):
   - LBFGS closure with gradient computation
   - Samples ROIs/panels for efficiency
   - Periodic full validation at `full_validation_interval`
   - Tracks best params snapshot for both chi_squared and masked_mse
   - NaN/Inf gradient guard
   - Returns chi_squared_loss for LBFGS optimizer

## Compilation Result

**Exit code**: 0 (SUCCESS)

Module imports cleanly with no errors.

## Next Step (C1a-loop3)

Extract `_run_stage_b_lbfgs` helper (~100 lines), wire all 3 helpers, and run regression guard test_stage_b_shell_modifiers.
