# Phase C0 Planning — Stage B Extraction Strategy

**Loop:** i=200 (Galph planning)
**Date:** 2025-11-23T06:17:26Z
**Initiative:** ARCH-REFINE-FLOW-001 Phase C
**Mode:** planning

## Objective

Plan Phase C (Stage B extraction) following the proven multi-loop strategy from Phase B.

## Phase B Retrospective

Phase B spanned 7 loops total (B0 baseline → B1a 3-loop helper extraction → B1b/B2 wrapper+delegation → B3 validation):
- **B0**: Baseline artifacts + test infrastructure fix
- **B1a-loop1**: Extract `_build_stage_a_params` (~328 lines)
- **B1a-loop2**: Extract `_build_stage_a_lbfgs_closure` (~717 lines with TWO nested functions)
- **B1a-loop3**: Extract `_run_stage_a_lbfgs` + refactor main function (~692 lines reduced)
- **B1b**: StageA wrapper class calling helpers
- **B2**: Engine delegation logic in run_nanobrag_refinement
- **B3**: Full validation suite (4 tests, all PASSED)

**Key Success Factors:**
1. Multi-loop extraction reduced scope per loop (300-700 lines each)
2. Incremental commits after each helper (compile validation only, no regression)
3. Final regression guard only after all helpers wired
4. Clear helper signatures with explicit parameter lists
5. Nonlocal variable inventory tracked across loops

## Stage B Code Analysis

**Location:** dbex/nanobrag_refinement.py lines 2527-3137 (~610 lines)

**Structure:**
1. **Guards & Parameter Setup** (lines 2527-2580, ~53 lines):
   - HKL halo/interpolation guards (REFINE-005)
   - Freeze Stage A params
   - Compute frozen crystal tensors (cell, misset) from Stage A results
   - Compute shell lookup via `compute_hkl_shell_lookup`
   - Initialize shell modifiers (softplus parameterization)
   - Setup LBFGS optimizer

2. **Telemetry & Context Setup** (lines 2582-2672, ~90 lines):
   - Telemetry accumulators (loss traces, chi-squared, masked_mse)
   - Variance floor tracking (PHYSICS-LOSS-002)
   - CPU fallback context for canonical runs (PERF-WARM-011/012)
   - ROI mode configuration (PERF-WARM-SIM-001)
   - Sample ROIs/panels
   - Performance counters

3. **compute_loss_stage_b** (lines 2674-2876, ~202 lines):
   - Variance-weighted chi-squared loss with Stage B shell-modified structure factors
   - Args: work_item_ids, is_full, force_panel_eval
   - Returns: (chi_squared_loss, masked_mse_loss)
   - Branches: ROI mode vs panel mode (similar to Stage A closure)
   - Device routing: CPU fallback logic
   - Warm cache utilization

4. **closure_stage_b** (lines 2878-2921, ~43 lines):
   - LBFGS closure contract
   - Calls compute_loss_stage_b with sampled indices
   - Gradient NaN/Inf guard
   - Loss trace recording
   - Periodic full validation
   - Updates best snapshot

5. **LBFGS Optimization** (lines 2923-2987, ~64 lines):
   - Initial full-loss validation
   - optimizer.step(closure_stage_b)
   - Exception handling
   - Restore best snapshot
   - Final validation
   - Improvement gate (config.stage_b_min_loss_improvement)

6. **Final Bragg Regeneration** (lines 2988-3065, ~77 lines):
   - Regenerate bragg_full with Stage B shell modifiers
   - Warm vs cold path
   - Panel loop (similar pattern to Stage A final bragg)

7. **Telemetry Assembly** (lines 3067-3137, ~70 lines):
   - param_deltas_b (shell modifier deltas with d-spacing labels)
   - perf_counters_b (ROI counts, cache_mode, forward stats)
   - RefinementTelemetry(stage="B", ...)
   - telemetry_dict["B"] = telemetry_b

**Total:** ~610 lines (vs Stage A ~1000 lines)

## Phase C Multi-Loop Extraction Plan

Following the Phase B pattern, extract 3-4 helpers across multiple loops:

### C1a-loop1: Extract `_build_stage_b_params` helper (~140 lines)
**Scope:** Lines 2527-2580 + 2582-2672 (parameter setup + telemetry context)
**Signature:**
```python
def _build_stage_b_params(
    crystal: Crystal,
    hkl_metadata: Dict,
    config: RefinementConfig,
    params: List[torch.Tensor],  # Stage A params to freeze
    log_cell_a_delta: torch.Tensor,  # Stage A final deltas
    log_cell_b_delta: torch.Tensor,
    log_cell_c_delta: torch.Tensor,
    angle_alpha_raw: torch.Tensor,
    angle_beta_raw: torch.Tensor,
    angle_gamma_raw: torch.Tensor,
    orientation_vec: torch.Tensor,
    baseline_misset_deg_tensor: Optional[torch.Tensor],
    device: torch.device,
    dtype: torch.dtype,
    use_stage_a_roi_mode: bool,
    canonical_roi_count: int,
    n_panels: int,
    sampled_panel_ids: List[int],
    stage_a_ctx: Optional[Any],  # StageAContext
) -> Dict[str, Any]:
    """
    Build Stage B parameters, telemetry accumulators, and eval context.

    Returns dict with keys:
    - stage_b_params: List[torch.Tensor] (shell_modifier_raw)
    - optimizer: torch.optim.LBFGS
    - param_values: Dict with frozen crystal tensors, shell indices/edges, eval context
    - telemetry_state: Dict with trace accumulators, best snapshots, perf counters
    - stage_b_context: Dict with ROI/panel indices, cache config, device routing
    """
```

### C1a-loop2: Extract `_build_stage_b_lbfgs_closure` helper (~260 lines)
**Scope:** Lines 2674-2921 (compute_loss_stage_b + closure_stage_b)
**Signature:**
```python
def _build_stage_b_lbfgs_closure(
    param_values: Dict,
    telemetry_state: Dict,
    stage_b_context: Dict,
    # Closure context params (similar to Stage A):
    crystal: Crystal,
    detector: Detector,
    beam: Beam,
    inputs: RefinementInputs,
    config: RefinementConfig,
    sigma_floor_sq_cache: Dict,
    device: torch.device,
    dtype: torch.dtype,
    log_scale: torch.Tensor,
    target_t: torch.Tensor,
    loss_mask_t: torch.Tensor,
    sigma_readout_t: torch.Tensor,
    n_panels: int,
) -> Tuple[Callable, Callable]:
    """
    Build Stage B LBFGS closure with nested compute_loss and closure functions.

    Returns: (compute_loss_stage_b, closure_stage_b)
    """
```

### C1a-loop3: Extract `_run_stage_b_lbfgs` + Refactor (~100 lines extraction + ~610 lines refactor)
**Scope:** Lines 2923-2987 (LBFGS execution)
**Signature:**
```python
def _run_stage_b_lbfgs(
    optimizer: torch.optim.LBFGS,
    closure: Callable,
    compute_loss: Callable,
    telemetry_state: Dict,
    param_values: Dict,
    stage_b_context: Dict,
    config: RefinementConfig,
    n_panels: int,
    best_loss_full_stage_a: float,  # For improvement gate
) -> Dict[str, Any]:
    """
    Run Stage B LBFGS optimization and return results.

    Returns dict with keys:
    - status: str ("ok"/"early_stop"/"error")
    - message: str
    - best_params_snapshot: Dict
    - final_loss_value: float
    - final_mse_value: float
    """
```

### C1b: Implement `_build_final_bragg_from_stage_b` helper (~77 lines)
**Scope:** Lines 2988-3065 (final Bragg regeneration)
**Signature:**
```python
def _build_final_bragg_from_stage_b(
    param_values: Dict,
    best_params_snapshot: Dict,
    stage_b_context: Dict,
    crystal: Crystal,
    detector: Detector,
    beam: Beam,
    inputs: RefinementInputs,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    config: RefinementConfig,
    log_scale: torch.Tensor,
    n_panels: int,
    panel_shape: Tuple,
    stage_a_ctx: Optional[Any],
    device: torch.device,
    dtype: torch.dtype,
) -> np.ndarray:
    """
    Regenerate final Bragg tensor with Stage B best shell modifiers.

    Returns: bragg_full_stage_b [n_panels, H, W]
    """
```

### C2: Implement StageB class calling 4 helpers
**Location:** dbex/refinement/stage_b.py
**Pattern:** Similar to StageA, implements RefinementStage protocol

### C3: Engine delegation logic for Stage B
**Location:** run_nanobrag_refinement detection logic
**Condition:** `enable_stage_b=True AND enable_stage_c=False` (Stage A+B only mode)

### C4: Full validation suite
**Tests:**
- test_stage_b_shell_modifiers (small + full detector)
- DB-AT-024 mapping (if applicable)
- Regression guards

**Estimated Total:** 6-7 loops (C0 planning, C1a 3 loops, C1b/C2/C3, C4 validation)

## Decision Criteria

**Path A (Multi-loop approved):** Proceed with C1a-loop1 (extract `_build_stage_b_params` ONLY, ~140 lines)
**Path B (Single-loop attempt):** Try extracting all 3 helpers + refactor in one loop (RISKY per Phase B blocker)
**Path C (Defer):** Switch to different initiative

**Recommendation:** Path A (multi-loop) — proven strategy from Phase B

## Key Findings Applied

- **REFINE-005**: Stage B requires halo-padded HKL grid + interpolation
- **REFINE-008**: Shell modifier ±1% gate, effectively zero improvement expected
- **PHYSICS-LOSS-001/002**: Variance-weighted loss + sigma_floor guard
- **PERF-WARM-011/012**: CPU fallback for canonical runs to avoid GPU OOM
- **PERF-WARM-SIM-001**: ROI mode configuration
- **PERF-WARM-008/009**: ROI mode expectations + panel validation forcing

## Next Step

Author Do Now for Ralph to execute C1a-loop1 (extract `_build_stage_b_params` ONLY).
