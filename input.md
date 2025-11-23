# Phase D1b: Extract _build_stage_c_lbfgs_closure Helper (Loop i=228)

## Summary
Extract the Stage C LBFGS closure helper function containing TWO nested functions (`compute_loss_stage_c` + `closure_stage_c`) from inline Stage C code. This is the second of three helper extraction loops following the proven Phase B/C multi-loop pattern.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase D1b: Stage C closure extraction)

## Branch
integration

## Mapped Tests
- **Primary Validation**: Compilation check via `python -c "import dbex.nanobrag_refinement"`
- **Regression Guard**: NOT REQUIRED (helper not wired, compilation-only verification)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1b/`

## Do Now

### Context Review
1. **Phase D1a Completion**: `_build_stage_c_params` helper extracted successfully (commit 331ee75)
   - 156 lines extracted, inserted at line 2737
   - 30 return keys matching specification
   - Compilation PASSED, regression guard PASSED (15.99s)
   - Decision: Path A → proceed to Phase D1b

2. **Inline Stage C Closure Location**: Lines 4078-4293 in `dbex/nanobrag_refinement.py` (~216 lines total)
   - Lines 4078-4247: `compute_loss_stage_c` nested function (~170 lines)
   - Lines 4249-4293: `closure_stage_c` nested function (~45 lines)

3. **Proven Pattern** (from Phase B1a-loop2 and C1a-loop2):
   - Extract BOTH nested functions together in single helper
   - Helper returns tuple `(compute_loss, closure)` with captured lexical scope
   - Lazy imports stay INSIDE nested functions (device-specific, conditional)
   - Helper signature: ~15 parameters (param_values dict, telemetry_state dict, stage_c_context dict, plus closure context params)

### Implement: dbex/nanobrag_refinement.py::_build_stage_c_lbfgs_closure

Extract lines 4078-4293 as a new helper function `_build_stage_c_lbfgs_closure` to be inserted **after** `_build_stage_c_params` (around line 2893, before `run_nanobrag_refinement`).

**Helper Signature**:
```python
def _build_stage_c_lbfgs_closure(
    param_values: Dict[str, Any],
    telemetry_state: Dict[str, Any],
    stage_c_context: Dict[str, Any],
    detector: Any,  # dxtbx.model.Detector
    beam: Any,  # dxtbx.model.Beam
    inputs: Any,  # RefinementInputs
    config: RefinementConfig,
    sigma_floor_sq_cache: Dict[str, torch.Tensor],
    device: torch.device,
    dtype: torch.dtype,
    crystal: Any,  # dxtbx.model.Crystal (Stage A final params)
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict[str, Any],
    stage_a_ctx: Optional[StageAContext],
    sampled_panel_ids: List[int]
) -> Tuple[Callable[[List[int], bool], Tuple[torch.Tensor, torch.Tensor]], Callable[[], torch.Tensor]]:
    """
    Build Stage C LBFGS closure for detector distance refinement.

    Returns tuple of (compute_loss_stage_c, closure_stage_c) with captured lexical scope
    for ~25 nonlocal variables extracted from input dicts.

    Both nested functions implement variance-weighted chi-squared loss with Stage C
    detector distance adjustments, freezing Stage A crystal parameters.

    Returns:
        Tuple of:
        - compute_loss_stage_c: Callable[[panel_ids, is_full], (chi_squared, mse)]
        - closure_stage_c: Callable[[], chi_squared_loss] (LBFGS closure contract)
    """
```

**Extraction Steps**:

1. **Create helper function** at line ~2893 (after `_build_stage_c_params`, before `run_nanobrag_refinement`)

2. **Unpack parameter dicts** at function start (to capture in nested function lexical scope):
   ```python
   # Extract from param_values dict
   distance_offset_raw = param_values['distance_offset_raw']
   stage_c_params = param_values['stage_c_params']
   stage_c_optimizer = param_values['stage_c_optimizer']

   # Extract from telemetry_state dict
   perf_closure_evals_c = telemetry_state['perf_closure_evals_c']
   perf_validation_runs_c = telemetry_state['perf_validation_runs_c']
   perf_forward_times_ms_c = telemetry_state['perf_forward_times_ms_c']
   loss_trace_sample_c = telemetry_state['loss_trace_sample_c']
   loss_trace_full_c = telemetry_state['loss_trace_full_c']
   best_loss_full_c = telemetry_state['best_loss_full_c']
   best_params_snapshot_c = telemetry_state['best_params_snapshot_c']
   iteration_count_c = telemetry_state['iteration_count_c']
   chi_squared_trace_sample_c = telemetry_state['chi_squared_trace_sample_c']
   chi_squared_trace_full_c = telemetry_state['chi_squared_trace_full_c']
   chi_squared_best_c = telemetry_state['chi_squared_best_c']
   masked_mse_trace_sample_c = telemetry_state['masked_mse_trace_sample_c']
   masked_mse_trace_full_c = telemetry_state['masked_mse_trace_full_c']
   masked_mse_best_c = telemetry_state['masked_mse_best_c']
   variance_floor_clamped_pixels_c = telemetry_state['variance_floor_clamped_pixels_c']
   variance_floor_masked_pixels_c = telemetry_state['variance_floor_masked_pixels_c']
   sigma_floor_sq_tensor_stage_c = telemetry_state['sigma_floor_sq_tensor_stage_c']

   # Extract from stage_c_context dict
   stage_c_use_warm_cache = stage_c_context['stage_c_use_warm_cache']
   stage_c_cache_mode = stage_c_context['stage_c_cache_mode']
   stage_c_roi_mode_active = stage_c_context['stage_c_roi_mode_active']
   stage_c_roi_mode_label = stage_c_context['stage_c_roi_mode_label']
   roi_slices_by_pid = stage_c_context['roi_slices_by_pid']
   n_panels = len(detector)
   ```

3. **Extract first nested function** `compute_loss_stage_c` (lines 4078-4247):
   - Preserve docstring
   - Preserve variance-weighted loss computation with sigma_floor guard
   - Preserve warm-cache branching (use stage_a_ctx if available)
   - Preserve ROI sampling logic
   - Preserve perf counter updates
   - Preserve all PHYSICS-LOSS-001/002 patterns (dual metrics, variance floor clamp stats)
   - Keep lazy imports INSIDE function (nanobrag_torch.models: Detector, Crystal; nanobrag_torch.simulator: Simulator)
   - Signature: `def compute_loss_stage_c(panel_ids: List[int], is_full: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:`

4. **Extract second nested function** `closure_stage_c` (lines 4249-4293):
   - Preserve docstring
   - Preserve LBFGS closure contract (zero_grad, compute loss, backward, return loss)
   - Preserve gradient NaN/Inf checks
   - Preserve periodic full validation logic
   - Preserve best snapshot updates with `nonlocal` declarations
   - Preserve iteration counter increment
   - Signature: `def closure_stage_c() -> torch.Tensor:`

5. **Return tuple** of both callables:
   ```python
   return compute_loss_stage_c, closure_stage_c
   ```

**DO NOT**:
- Wire the helper into `run_nanobrag_refinement` (no call site changes)
- Extract the `_run_stage_c_lbfgs` execution logic (that's D1c)
- Modify any Stage C inline logic beyond the extracted lines
- Change test behavior (helper not called, no regression test needed)
- Add new imports at module level (lazy imports only)

**Compilation Check**:
```bash
python -c "import dbex.nanobrag_refinement; print('Compilation PASSED')"
```

Expected: PASS (no syntax errors, helper exists but not called)

### Validation Protocol

1. **Compilation**: Import `dbex.nanobrag_refinement` successfully
2. **Helper Signature**: Verify function signature matches specification exactly
3. **Return Type**: Verify returns tuple of two callables `(compute_loss_stage_c, closure_stage_c)`
4. **Lines Extracted**: Verify approximately 216 lines extracted from inline code
5. **Nested Functions**: Verify TWO nested functions preserved with correct signatures

### Decision Synthesis (3-Path Template)

**Path A (Compilation PASS)**:
- Helper extraction SUCCESSFUL
- Proceed to Phase D1c next loop (extract `_run_stage_c_lbfgs` + wire all 3 helpers + regression guard)
- Update implementation.md checklist D1b complete
- Commit helper extraction with message: "ARCH-REFINE-FLOW-001 Phase D1b: Extract _build_stage_c_lbfgs_closure helper — tests: not run"

**Path B (Compilation FAIL)**:
- Syntax error or import error in helper
- Debug syntax, fix imports, check indentation, verify nonlocal declarations
- Retest compilation until clean
- Do NOT proceed to D1c until compilation PASS

**Path C (Helper signature mismatch)**:
- Return type incorrect (not tuple of callables)
- Nested function signatures don't match specification
- Fix helper to return `(compute_loss_stage_c, closure_stage_c)` tuple
- Verify both callables have correct signatures
- Retest compilation
- Do NOT proceed to D1c until signature correct

### Artifacts Capture

Save to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1b/`:

1. **compilation_check.log**: Output of `python -c "import dbex.nanobrag_refinement"`
2. **helper_diff.patch**: Git diff showing extracted helper (for reproducibility)
3. **decision.md**: 3-path synthesis with chosen path and rationale
4. **metrics.json**: Extract via T0 probe:
   ```python
   import json
   metrics = {
       "compilation_status": "PASS" or "FAIL",
       "helper_lines_extracted": 216,  # approximate count
       "helper_nested_functions_count": 2,
       "helper_signature_correct": True or False,
       "decision_path": "A"  # or "B", "C"
   }
   with open("plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1b/metrics.json", "w") as f:
       json.dump(metrics, f, indent=2)
   ```
5. **summary.md**: Turn Summary block (prepend to existing summary.md)

### Update Checklist

Mark complete in `plans/active/ARCH-REFINE-FLOW-001/implementation.md`:
- Update Phase D section (around line 229):
  ```markdown
  - [ ] D1: Implement `StageC` class managing detector offset parameters, baseline detector seeding, and telemetry.
    - [x] D1a: Extract `_build_stage_c_params` helper (~156 lines) ✓ COMPLETE (2025-11-23T150000Z)
    - [x] D1b: Extract `_build_stage_c_lbfgs_closure` helper (~216 lines) ✓ COMPLETE (2025-11-23T141817Z)
    - [ ] D1c: Extract `_run_stage_c_lbfgs` + wire all helpers + regression guard
  ```

### Commit and Push

```bash
git add -A
git commit -m "ARCH-REFINE-FLOW-001 Phase D1b: Extract _build_stage_c_lbfgs_closure helper — tests: not run"
git push
```

## How-To Map

### Compilation Check Command
```bash
python -c "import dbex.nanobrag_refinement; print('Compilation PASSED')" 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1b/compilation_check.log
```

### Git Diff Capture
```bash
git diff > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1b/helper_diff.patch
```

### Metrics Extraction (T0 Probe)
Inline Python after compilation check — save to `metrics.json` in artifacts directory.

## Pitfalls To Avoid

1. **DO NOT wire helper**: No call site changes in `run_nanobrag_refinement`. Helper extraction only.
2. **DO NOT extract LBFGS execution**: `stage_c_optimizer.step(closure_stage_c)` stays inline (that's Phase D1c).
3. **DO NOT run regression test**: Compilation check only (helper not wired, no behavior change).
4. **Preserve nonlocal declarations**: `closure_stage_c` uses `nonlocal best_loss_full_c, best_params_snapshot_c, chi_squared_best_c, masked_mse_best_c` (line 4281).
5. **Lazy imports**: Conditional imports (nanobrag_torch.models, nanobrag_torch.simulator) stay INSIDE `compute_loss_stage_c` warm/cold branching.
6. **Return tuple**: Helper MUST return `(compute_loss_stage_c, closure_stage_c)` NOT single callable.
7. **Lexical scope**: All ~25 variables unpacked from dicts at function start to allow nested functions to capture them.
8. **Device/dtype consistency**: Use `device` and `dtype` params passed to helper (no hardcoded `'cuda:0'`).
9. **Indentation**: TWO nested functions at same indentation level (4 spaces from function body start).
10. **Environment Freeze**: No package installs, no environment changes. Code-only extraction.

## If Blocked

If compilation fails:

1. **Capture error output** to `blocker.md` in artifacts directory
2. **Check common issues**:
   - Missing `nonlocal` declarations in `closure_stage_c`
   - Indentation errors in nested functions
   - Incomplete dict unpacking (missing variables from param_values/telemetry_state/stage_c_context)
   - Lazy imports moved to wrong location (must stay inside nested functions)
   - Return statement incorrect (must be tuple, not single callable)
3. **Debug systematically**:
   - Verify helper signature matches specification
   - Verify dict unpacking includes all required variables
   - Verify both nested functions extracted completely
   - Verify return statement returns tuple
4. **Update Attempts History** in `docs/fix_plan.md` with blocker signature
5. **Mark Phase D1b blocked** in `galph_memory.md`
6. **Escalate to Galph** with blocker report including:
   - Exact error message and traceback
   - Line numbers where helper was inserted
   - Hypothesis about root cause (syntax, scope, imports, etc.)

## Findings Applied (Mandatory)

- **REFINE-007** (docs/findings.md:43): Stage C gate is "stable detector offset" — closure preserves telemetry accumulators for offset tracking
- **PHYSICS-LOSS-001/002** (docs/findings.md:20,21): Variance-weighted loss + sigma_floor preserved in `compute_loss_stage_c`
- **POLICY-001** (docs/findings.md:66): Environment Freeze — helper extraction only, no env changes
- **PERF-WARM-011/012** (docs/findings.md:46,47): Warm cache + ROI sampling patterns preserved in `compute_loss_stage_c`
- **RUNTIME-001** (docs/findings.md:29): Lazy imports for nanobrag_torch stay INSIDE nested functions (compile conflicts)
- **TESTING-003** (docs/findings.md:56): Test registry updates deferred until D1c wiring complete (no selector changes this loop)

No relevant findings in knowledge base for closure extraction methodology (standard refactoring pattern from Stage A/B).

## Pointers

- **Spec**: docs/spec-db-workflow.md §7 (Refinement Protocol Architecture)
- **Architecture**: docs/architecture/pytorch_design.md (RefinementEngine contract)
- **Fix Plan**: docs/fix_plan.md `[ARCH-REFINE-FLOW-001]` line 28
- **Implementation Plan**: plans/active/ARCH-REFINE-FLOW-001/implementation.md Phase D (line 220)
- **Phase D1a Evidence**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T150000Z/phase_d1a/summary.md (helper 1 extracted successfully)
- **Stage A Closure Pattern**: plans/active/ARCH-REFINE-FLOW-001/implementation.md Phase B1a-loop2 (lines 93-100) — proven closure extraction methodology
- **Stage B Closure Pattern**: plans/active/ARCH-REFINE-FLOW-001/implementation.md Phase C1a-loop2 (lines 190-196) — similar TWO nested functions
- **Stage C Inline Code**: dbex/nanobrag_refinement.py lines 4078-4293
- **Commit Reference**: 331ee75 (Phase D1a completion)

## Next Up (Optional)

If Phase D1b completes successfully (Path A):
- **Phase D1c**: Extract `_run_stage_c_lbfgs` helper + wire all three helpers + validate Stage C smoke (small + full detectors) + full validation suite

If Phase D1b blocked (Path B/C):
- Debug compilation or signature issue
- Escalate to Galph with blocker report
- Do NOT proceed to D1c until D1b compilation clean and helper signature correct

## Doc Sync Plan (Conditional)

Not applicable this loop (no new tests authored, no selector changes). Test registry updates deferred to Phase D1c after full helper wiring and validation complete.

## Mapped Tests Guardrail

**Compilation check** (python import) always collects (N/A for pytest collection).

**Regression guard** NOT REQUIRED this loop (helper not wired, compilation-only verification per proven Phase B1a-loop2 pattern).

Phase D1c will require full regression guard (`test_stage_c_detector_microslip` small + full detectors) after helper wiring.

## Normative Math/Physics

Variance-weighted loss computation stays in `compute_loss_stage_c` nested function (extracted, not modified).

Reference docs/spec-db-core.md §Variance Definition for normative variance-floor clamping specification (implemented in `compute_loss_stage_c` lines 4132-4160, preserved in extraction).
