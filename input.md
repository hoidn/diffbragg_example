# Phase C1a-loop2: Extract Stage B LBFGS Closure Helper

## Summary
Extract `_build_stage_b_lbfgs_closure` helper (~247 lines) from Stage B inline code, mirroring Phase B1a-loop2 strategy.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C1a-loop2)

## Branch
integration

## Mapped tests
- none — evidence-only (compilation check, no regression guard until C1a-loop3 wiring)

## Artifacts
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T063000Z/
- phase_c1a_loop2_extraction_diff.patch
- compilation_check.log
- summary.md

## Do Now

**SINGLE TASK: Extract `_build_stage_b_lbfgs_closure` helper (~247 lines) — compilation check ONLY, NO wiring**

### Scope
Extract TWO nested functions from dbex/nanobrag_refinement.py:
1. `compute_loss_stage_b` (lines 2859-3061, ~203 lines)
2. `closure_stage_b` (lines 3063-3106, ~44 lines)

Total extraction: ~247 lines

### Target Signature
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
    """
    Build LBFGS closure for Stage B shell modifier refinement.

    Returns closure_stage_b callable that captures loss computation and gradient logic.
    Mirrors Phase B1a-loop2 pattern for Stage A closure extraction.
    """
```

### Implementation Steps

1. **Insert helper at line 2272** (after `_build_stage_b_params`, before `run_nanobrag_refinement`)

2. **Extract nested functions**:
   - Copy `compute_loss_stage_b` (lines 2859-3061) into helper body
   - Copy `closure_stage_b` (lines 3063-3106) into helper body
   - Return `closure_stage_b` callable

3. **Preserve lexical scope captures**:
   - Extract params from `param_values` dict:
     ```python
     shell_modifier_raw = param_values['shell_modifier_raw']
     stage_b_optimizer = param_values['optimizer']
     log_scale = param_values['log_scale']
     cell_a_tensor = param_values['cell_a_tensor']
     cell_b_tensor = param_values['cell_b_tensor']
     cell_c_tensor = param_values['cell_c_tensor']
     cell_alpha_tensor = param_values['cell_alpha_tensor']
     cell_beta_tensor = param_values['cell_beta_tensor']
     cell_gamma_tensor = param_values['cell_gamma_tensor']
     misset_xyz_deg = param_values['misset_xyz_deg']
     stage_b_params = param_values['stage_b_params']
     ```
   - Extract telemetry accumulators:
     ```python
     loss_trace_sample_b = param_values['loss_trace_sample_b']
     loss_trace_full_b = param_values['loss_trace_full_b']
     chi_squared_trace_sample_b = param_values['chi_squared_trace_sample_b']
     chi_squared_trace_full_b = param_values['chi_squared_trace_full_b']
     masked_mse_trace_sample_b = param_values['masked_mse_trace_sample_b']
     masked_mse_trace_full_b = param_values['masked_mse_trace_full_b']
     chi_squared_best_b = param_values['chi_squared_best_b']
     masked_mse_best_b = param_values['masked_mse_best_b']
     best_loss_full_b = param_values['best_loss_full_b']
     best_params_snapshot_b = param_values['best_params_snapshot_b']
     variance_floor_clamped_pixels_b = param_values['variance_floor_clamped_pixels_b']
     variance_floor_masked_pixels_b = param_values['variance_floor_masked_pixels_b']
     perf_closure_evals_b = param_values['perf_closure_evals_b']
     perf_validation_runs_b = param_values['perf_validation_runs_b']
     perf_forward_times_ms_b = param_values['perf_forward_times_ms_b']
     ```
   - Mark all mutable list references in closure_stage_b as nonlocal:
     ```python
     # Inside closure_stage_b nested function
     nonlocal chi_squared_best_b, masked_mse_best_b, best_loss_full_b, best_params_snapshot_b
     ```

4. **Preserve imports** (inside nested functions):
   - `from dbex.nanobrag_bridge import create_detector_config, create_crystal_config`
   - `from nanobrag_torch import Detector, Crystal, Simulator`
   - Keep lazy imports inside branches per PERF-WARM-011/012

5. **Verify compilation**: `python -c "import dbex.nanobrag_refinement"` (exit code 0)

6. **NO WIRING**: Do NOT call the helper yet — this is extraction-only (mirrors B1a-loop2)

7. **Save patch**: `git diff > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T063000Z/phase_c1a_loop2_extraction_diff.patch`

8. **Write summary.md**:
   - Helper signature
   - Line count (~247 lines)
   - Nested functions preserved (compute_loss_stage_b + closure_stage_b)
   - Compilation result (exit code)
   - Next step: C1a-loop3 (extract `_run_stage_b_lbfgs` + wire all 3 helpers + regression guard)

9. **Commit**: `ARCH-REFINE-FLOW-001 Phase C1a-loop2: Extract _build_stage_b_lbfgs_closure helper (~247 lines) — tests: not run`

10. **Update implementation.md**: Mark C1a-loop2 COMPLETE in Phase C checklist

## How-To Map

### Helper Extraction
```bash
# Insert helper function at line 2272 (after _build_stage_b_params)
# Extract lines 2859-3106 (compute_loss_stage_b + closure_stage_b)
# Total: ~247 lines
```

### Compilation Check
```bash
cd /home/ollie/Documents/diffbragg_example
python -c "import dbex.nanobrag_refinement" && echo "SUCCESS: Module imported without errors" || echo "FAILED: Import error"
echo "Exit code: $?"
```

### Artifacts
```bash
# Save patch
git diff > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T063000Z/phase_c1a_loop2_extraction_diff.patch

# Record compilation result
python -c "import dbex.nanobrag_refinement" > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T063000Z/compilation_check.log 2>&1
echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T063000Z/compilation_check.log
```

## Pitfalls To Avoid

1. **Lexical scope preservation**: Extract ALL param_values dict entries used by nested functions; missing keys will cause NameError in C1a-loop3 wiring (learned from Phase B1a-loop3 bug)
2. **Nonlocal mutations**: Mark all mutable accumulators as `nonlocal` in closure_stage_b
3. **Device neutrality**: Preserve CPU fallback logic (PERF-WARM-011/012) and eval_device routing
4. **Lazy imports**: Keep nanobrag_bridge/nanobrag_torch imports inside nested functions and branches
5. **No ad-hoc changes**: Pure extraction — do NOT refactor, rename, or optimize; preserve exact logic
6. **NO wiring**: Do NOT call the helper yet — this is extraction-only, mirrors Phase B1a-loop2 pattern
7. **Protected Assets**: Do not touch Stage A code, engine classes, or telemetry schema
8. **Signature stability**: Helper signature must match param_values keys populated by `_build_stage_b_params` (C1a-loop1)
9. **Cache mode telemetry**: Preserve `cache_mode`, `roi_mode`, and perf counters per PERF-WARM-SIM-001
10. **Vectorization**: No changes to panel/ROI loops or loss aggregation logic

## If Blocked

1. **Import error**: Check lazy imports are inside nested functions (not at helper top level)
2. **NameError**: Add missing param_values dict entries (reference C1a-loop1 helper output)
3. **Indentation**: Preserve exact indentation from source (4 spaces per level)
4. **Line count mismatch**: Verify extraction range (2859-3106, ~247 lines total)
5. **Document blocker** in Attempts History:
   - Error signature (first 100 chars of traceback)
   - Missing param_values keys
   - Next action: review C1a-loop1 helper output, add missing entries

## Findings Applied

**Relevant Findings from Knowledge Base:**

- **REFINE-005**: Stage B requires halo-padded HKL grid and tricubic interpolation; closure must preserve `hkl_grid_modified` computation with shell modifiers applied to haloed grid
- **REFINE-008**: Stage B calibrated gate is ≥0.002% improvement; closure telemetry must track chi_squared improvement for LBFGS loop
- **PHYSICS-LOSS-001**: Dual metric tracking (chi_squared + masked_mse); closure must record BOTH metrics in sample/full traces
- **PHYSICS-LOSS-002**: Variance floor clamp statistics; closure must track `variance_floor_clamped_pixels_b` and `variance_floor_masked_pixels_b` via `_compute_variance_weighted_loss`
- **PERF-WARM-011**: CPU fallback for Stage B panel-mode runs (config.stage_b_full_eval_on_cpu + CUDA + no ROI); closure must route to `eval_device` correctly
- **PERF-WARM-012**: Clone Stage A context to CPU when fallback active; closure must use `stage_b_eval_stage_a_ctx` (CPU or CUDA) for warm cache
- **PERF-WARM-SIM-001**: ROI mode telemetry (cache_mode, roi_mode, roi_count); closure must preserve perf counters and ROI sampling logic
- **PERF-WARM-009**: Force panel evaluation for periodic/initial/final validations to keep modifiers within ±1% gate; closure must respect `force_panel_eval` flag
- **SCALE-001**: log_scale clamping to [-10, 10] prevents exp overflow; closure must apply clamp before scaling Bragg frames
- **CONFIG-001**: Detector metadata contracts; closure must preserve detector/beam/crystal config creation per nanobrag_bridge API
- **POLICY-001**: Environment Freeze — do NOT add imports, do NOT change signatures; pure extraction only

## Pointers

- **Spec**: docs/spec-db-workflow.md §7 (Refinement Protocol Architecture — Stage B physics)
- **Implementation Plan**: plans/active/ARCH-REFINE-FLOW-001/implementation.md:179-196 (Phase C checklist)
- **Fix Plan**: docs/fix_plan.md:181 (ARCH-REFINE-FLOW-001 entry, Attempts History)
- **Phase B Precedent**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050000Z/summary.md (B1a-loop2 closure extraction, ~617 lines)
- **Phase C1a-loop1**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/summary.md (helper1 extraction, param_values dict structure)
- **Testing Guide**: docs/TESTING_GUIDE.md (NO selectors for evidence-only loops)
- **Architecture**: docs/architecture/pytorch_design.md (refinement engine multi-loop strategy)

## Next Up

**C1a-loop3** (next loop after helper2 extraction succeeds):
- Extract `_run_stage_b_lbfgs` helper (~100 lines: LBFGS execution + improvement gate)
- Wire all 3 helpers into `run_nanobrag_refinement` Stage B branch
- Add `stage_b_params`, `optimizer`, telemetry accumulators, and frozen Stage A tensors to param_values dict
- Run regression guard: `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -v`
- Capture selector logs + telemetry JSON under 2025-11-22T0700XXZ artifacts

## Doc Sync Plan

**NOT APPLICABLE** — No tests added/renamed this loop (evidence-only, compilation check).

## Mapped Tests Guardrail

**NOT APPLICABLE** — Evidence-only loop, no selectors mapped (compilation check only per multi-loop strategy).
