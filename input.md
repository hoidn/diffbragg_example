# Phase C1a-loop3: Extract Stage B LBFGS Helper + Wire All 3 Helpers + Regression Guard

## Summary
Extract `_run_stage_b_lbfgs` helper (~100 lines) from Stage B inline code, wire all 3 helpers into `run_nanobrag_refinement`, and run regression guard test_stage_b_shell_modifiers to complete Phase C1a extraction.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C1a-loop3)

## Branch
integration

## Mapped tests
- pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -v (MANDATORY regression guard, MUST PASS)

## Artifacts
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T070000Z/
- phase_c1a_loop3_extraction_diff.patch
- compilation_check.log
- pytest_stage_b_shell_modifiers.log
- telemetry_comparison.md
- summary.md

## Do Now

**FINAL EXTRACTION LOOP: Extract `_run_stage_b_lbfgs` helper + wire all 3 helpers + MANDATORY regression guard**

### Phase C1a-loop3 Scope

This is the FINAL loop of Phase C1a multi-loop extraction, mirroring Phase B1a-loop3 pattern. Three objectives:

1. **Extract helper 3** (~100 lines): `_run_stage_b_lbfgs` (LBFGS execution + improvement gate + best snapshot restore)
2. **Wire all 3 helpers** into `run_nanobrag_refinement` Stage B branch (replace ~610 lines with ~50 lines orchestration)
3. **MANDATORY regression guard**: `test_stage_b_shell_modifiers` MUST PASS

### Target Helper Signature

```python
def _run_stage_b_lbfgs(
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    param_values: Dict[str, Any],
    closure_stage_b: Callable[[], torch.Tensor],
    compute_loss_stage_b: Callable[[List[int], bool, bool], Tuple[torch.Tensor, torch.Tensor]],
    n_panels: int,
) -> Dict[str, Any]:
    """
    Run LBFGS optimization for Stage B shell modifier refinement.

    Returns dict with status, message, final metrics, and best params snapshot.
    Mirrors Phase B1a-loop3 pattern for Stage A LBFGS execution.
    """
```

### Implementation Steps

#### Step 1: Extract `_run_stage_b_lbfgs` Helper (~100 lines)

**Insert helper at line 2589** (after `_build_stage_b_lbfgs_closure`, before `run_nanobrag_refinement`)

**Extract lines 3427-3490** from inline Stage B code:
- Initial full validation (lines 3431-3444)
- LBFGS optimizer.step() call (line 3447)
- Exception handler (lines 3449-3451)
- Final validation + best snapshot restore (lines 3453-3473)
- Final metrics assembly (lines 3475-3479)
- Improvement gate check (lines 3481-3490)

**Helper structure**:
```python
def _run_stage_b_lbfgs(...):
    """Run LBFGS optimization for Stage B shell modifier refinement."""

    # Extract param_values dict entries
    stage_b_optimizer = param_values['optimizer']
    shell_modifier_raw = param_values['shell_modifier_raw']
    log_scale = param_values['log_scale']
    loss_trace_full_b = param_values['loss_trace_full_b']
    chi_squared_trace_full_b = param_values['chi_squared_trace_full_b']
    masked_mse_trace_full_b = param_values['masked_mse_trace_full_b']
    chi_squared_best_b = param_values['chi_squared_best_b']
    masked_mse_best_b = param_values['masked_mse_best_b']
    best_loss_full_b = param_values['best_loss_full_b']
    best_params_snapshot_b = param_values['best_params_snapshot_b']
    stage_b_param_device = param_values['stage_b_param_device']
    best_loss_full = param_values['best_loss_full']  # Stage A final loss for improvement calc

    status_b = "ok"
    message_b = ""
    try:
        # Initial full validation (MANDATORY per TORCH-REFINE-004)
        with torch.no_grad():
            initial_chi_squared_b, initial_mse_b = compute_loss_stage_b(
                list(range(n_panels)), is_full=True, force_panel_eval=True
            )
            # Record initial metrics in traces
            loss_trace_full_b.append((0, float(initial_chi_squared_b.item())))
            chi_squared_trace_full_b.append((0, float(initial_chi_squared_b.item())))
            masked_mse_trace_full_b.append((0, float(initial_mse_b.item())))
            chi_squared_best_b[0] = float(initial_chi_squared_b.item())
            chi_squared_best_b[1] = 0
            masked_mse_best_b[0] = float(initial_mse_b.item())
            masked_mse_best_b[1] = 0
            best_loss_full_b[0] = float(initial_chi_squared_b.item())
            best_loss_full_b[1] = 0
            best_params_snapshot_b['shell_modifier_raw'] = shell_modifier_raw.data.clone()

        # Run LBFGS optimization
        stage_b_optimizer.step(closure_stage_b)

    except Exception as e:
        status_b = "error"
        message_b = f"Stage B error: {str(e)}"

    # Restore best snapshot (always, even on success, to ensure consistency)
    # PERF-WARM-009: Force panel evaluation for final validation to keep modifiers within ±1%
    final_step = len(loss_trace_sample_b)  # NOTE: Must access from param_values
    with torch.no_grad():
        candidate_final_chi2, candidate_final_mse = compute_loss_stage_b(
            list(range(n_panels)), is_full=True, force_panel_eval=True
        )
    candidate_loss_value = float(candidate_final_chi2.item())
    candidate_mse_value = float(candidate_final_mse.item())
    if candidate_loss_value < chi_squared_best_b[0]:
        chi_squared_best_b[0] = candidate_loss_value
        chi_squared_best_b[1] = final_step
        best_loss_full_b[0] = candidate_loss_value
        best_loss_full_b[1] = final_step
        best_params_snapshot_b['shell_modifier_raw'] = shell_modifier_raw.data.clone()
    if candidate_mse_value < masked_mse_best_b[0]:
        masked_mse_best_b[0] = candidate_mse_value
        masked_mse_best_b[1] = final_step

    if best_loss_full_b[0] < float('inf'):
        shell_modifier_raw.data = best_params_snapshot_b['shell_modifier_raw'].to(
            device=stage_b_param_device,
            dtype=dtype
        )

    final_loss_value = chi_squared_best_b[0] if chi_squared_best_b[0] < float('inf') else candidate_loss_value
    final_mse_value = masked_mse_best_b[0] if masked_mse_best_b[0] < float('inf') else candidate_mse_value
    loss_trace_full_b.append((final_step, final_loss_value))
    chi_squared_trace_full_b.append((final_step, final_loss_value))
    masked_mse_trace_full_b.append((final_step, final_mse_value))

    # Improvement gate check (REFINE-008)
    if status_b != "error" and best_loss_full[0] > 0:
        stage_a_final_loss = best_loss_full[0]
        improvement_b = (stage_a_final_loss - final_loss_value) / stage_a_final_loss
        if improvement_b < config.stage_b_min_loss_improvement:
            status_b = "early_stop"
            message_b = (
                f"Stage B improvement {improvement_b:.4%} < "
                f"{config.stage_b_min_loss_improvement:.4%} (calibrated gate per TORCH-REFINE-004, "
                "artifact: plans/active/TORCH-REFINE-004/reports/2025-11-05T190344Z/stage_b_improvement_probe.json)"
            )

    return {
        'status': status_b,
        'message': message_b,
        'final_loss_value': final_loss_value,
        'final_mse_value': final_mse_value,
    }
```

**Critical**: Access `loss_trace_sample_b` from `param_values` for `final_step` calculation, not from local scope.

#### Step 2: Refactor `run_nanobrag_refinement` Stage B Branch

**Replace lines ~3040-3540** (Stage B inline code ~500 lines) with helper orchestration (~50 lines):

```python
# Stage B: Optional shell modifier refinement (REFINE-008)
if config.enable_stage_b:
    # Step 1: Build Stage B parameters (shell modifier + optimizer + telemetry accumulators + context)
    stage_b_params_result = _build_stage_b_params(
        config=config,
        device=device,
        dtype=dtype,
        stage_a_ctx=stage_a_ctx,
        canonical_baseline=canonical_baseline,
        n_panels=n_panels,
        sampled_panel_ids=sampled_panel_ids,
        sigma_floor_sq_cache=sigma_floor_sq_cache,
        use_stage_a_roi_mode=use_stage_a_roi_mode,
        crystal=crystal,
        hkl_metadata=hkl_metadata,
        hkl_grid=hkl_grid,
        detector=detector,
        beam=beam,
        inputs=inputs,
        panel_slices=panel_slices,
    )

    # Unpack param_values and context dicts from helper1
    stage_b_param_values = stage_b_params_result['param_values']
    stage_b_eval_stage_a_ctx = stage_b_params_result['stage_b_eval_stage_a_ctx']
    use_stage_b_cpu_fallback = stage_b_params_result['use_stage_b_cpu_fallback']
    stage_b_use_warm_cache = stage_b_params_result['stage_b_use_warm_cache']
    use_stage_b_roi_mode = stage_b_params_result['use_stage_b_roi_mode']
    sampled_stage_b_indices = stage_b_params_result['sampled_stage_b_indices']
    full_stage_b_indices = stage_b_params_result['full_stage_b_indices']

    # Add frozen Stage A tensors to param_values for closure access
    stage_b_param_values['log_scale'] = log_scale
    stage_b_param_values['cell_a_tensor'] = cell_a_tensor
    stage_b_param_values['cell_b_tensor'] = cell_b_tensor
    stage_b_param_values['cell_c_tensor'] = cell_c_tensor
    stage_b_param_values['cell_alpha_tensor'] = cell_alpha_tensor
    stage_b_param_values['cell_beta_tensor'] = cell_beta_tensor
    stage_b_param_values['cell_gamma_tensor'] = cell_gamma_tensor
    stage_b_param_values['misset_xyz_deg'] = misset_xyz_deg
    stage_b_param_values['best_loss_full'] = best_loss_full  # Stage A final loss for improvement calc

    # Step 2: Build Stage B LBFGS closure
    closure_stage_b = _build_stage_b_lbfgs_closure(
        config=config,
        device=device,
        dtype=dtype,
        param_values=stage_b_param_values,
        stage_a_ctx=stage_a_ctx,
        stage_b_eval_stage_a_ctx=stage_b_eval_stage_a_ctx,
        canonical_baseline=canonical_baseline,
        n_panels=n_panels,
        sampled_stage_b_indices=sampled_stage_b_indices,
        full_stage_b_indices=full_stage_b_indices,
        sigma_floor_sq_cache=sigma_floor_sq_cache,
        use_stage_b_cpu_fallback=use_stage_b_cpu_fallback,
        stage_b_use_warm_cache=stage_b_use_warm_cache,
        use_stage_b_roi_mode=use_stage_b_roi_mode,
        crystal=crystal,
        hkl_metadata=hkl_metadata,
        hkl_grid=hkl_grid,
        shell_indices=stage_b_params_result['shell_indices'],
        detector=detector,
        beam=beam,
        inputs=inputs,
        target_t=target_t,
        loss_mask_t=loss_mask_t,
        sigma_readout_t=sigma_readout_t,
        baseline_misset_deg_tensor=baseline_misset_deg_tensor,
        panel_shape=panel_shape,
    )

    # Extract compute_loss function from closure context (if returned by helper2)
    # NOTE: helper2 returns closure_stage_b only, NOT compute_loss. Need to adjust.
    # ACTUALLY: Looking at the code, compute_loss_stage_b is a nested function INSIDE helper2.
    # We need helper2 to return BOTH compute_loss_stage_b AND closure_stage_b.
    # This is a BLOCKER: helper2 signature needs adjustment.

    # REVISED APPROACH: helper2 must return tuple (compute_loss_stage_b, closure_stage_b)
    # Update helper2 signature to match Phase B1a-loop2 Stage A pattern.

    # Step 3: Run Stage B LBFGS optimization
    lbfgs_result = _run_stage_b_lbfgs(
        config=config,
        device=device,
        dtype=dtype,
        param_values=stage_b_param_values,
        closure_stage_b=closure_stage_b,
        compute_loss_stage_b=compute_loss_stage_b,  # Need to extract from helper2
        n_panels=n_panels,
    )

    status_b = lbfgs_result['status']
    message_b = lbfgs_result['message']
    final_loss_value_b = lbfgs_result['final_loss_value']
    final_mse_value_b = lbfgs_result['final_mse_value']

    # Keep existing final Bragg generation code AS-IS (lines ~3492-3600)
    # ...
```

**CRITICAL BLOCKER IDENTIFIED**: Helper2 `_build_stage_b_lbfgs_closure` currently returns ONLY `closure_stage_b` (line 2586), but helper3 `_run_stage_b_lbfgs` needs BOTH `closure_stage_b` AND `compute_loss_stage_b` for final validation.

**RESOLUTION**: Update helper2 signature to return tuple `(compute_loss_stage_b, closure_stage_b)` matching Phase B1a-loop2 Stage A pattern.

#### Step 3: Fix Helper2 Signature Bug

**Edit `_build_stage_b_lbfgs_closure`** (line 2589):

Change:
```python
    return closure_stage_b
```

To:
```python
    return compute_loss_stage_b, closure_stage_b
```

Update signature docstring:
```python
def _build_stage_b_lbfgs_closure(
    ...
) -> Tuple[Callable[[List[int], bool, bool], Tuple[torch.Tensor, torch.Tensor]], Callable[[], torch.Tensor]]:
    """
    Build LBFGS closure for Stage B shell modifier refinement.

    Returns tuple of (compute_loss_stage_b, closure_stage_b).
    compute_loss_stage_b: Callable for manual loss evaluation (used for final validation).
    closure_stage_b: Callable for LBFGS optimizer.
    Mirrors Phase B1a-loop2 pattern for Stage A closure extraction.
    """
```

#### Step 4: Complete Stage B Wiring

After fixing helper2 signature, wire helpers into `run_nanobrag_refinement`:

```python
# Stage B: Optional shell modifier refinement (REFINE-008)
if config.enable_stage_b:
    # Build params
    stage_b_params_result = _build_stage_b_params(...)
    stage_b_param_values = stage_b_params_result['param_values']

    # Add frozen Stage A tensors
    stage_b_param_values['log_scale'] = log_scale
    stage_b_param_values['cell_a_tensor'] = cell_a_tensor
    # ... (all 8 frozen tensors)
    stage_b_param_values['best_loss_full'] = best_loss_full

    # Build closure (returns BOTH functions)
    compute_loss_stage_b, closure_stage_b = _build_stage_b_lbfgs_closure(
        config=config,
        device=device,
        dtype=dtype,
        param_values=stage_b_param_values,
        stage_a_ctx=stage_a_ctx,
        stage_b_eval_stage_a_ctx=stage_b_params_result['stage_b_eval_stage_a_ctx'],
        canonical_baseline=canonical_baseline,
        n_panels=n_panels,
        sampled_stage_b_indices=stage_b_params_result['sampled_stage_b_indices'],
        full_stage_b_indices=stage_b_params_result['full_stage_b_indices'],
        sigma_floor_sq_cache=sigma_floor_sq_cache,
        use_stage_b_cpu_fallback=stage_b_params_result['use_stage_b_cpu_fallback'],
        stage_b_use_warm_cache=stage_b_params_result['stage_b_use_warm_cache'],
        use_stage_b_roi_mode=stage_b_params_result['use_stage_b_roi_mode'],
        crystal=crystal,
        hkl_metadata=hkl_metadata,
        hkl_grid=hkl_grid,
        shell_indices=stage_b_params_result['shell_indices'],
        detector=detector,
        beam=beam,
        inputs=inputs,
        target_t=target_t,
        loss_mask_t=loss_mask_t,
        sigma_readout_t=sigma_readout_t,
        baseline_misset_deg_tensor=baseline_misset_deg_tensor,
        panel_shape=panel_shape,
    )

    # Run LBFGS optimization
    lbfgs_result = _run_stage_b_lbfgs(
        config=config,
        device=device,
        dtype=dtype,
        param_values=stage_b_param_values,
        closure_stage_b=closure_stage_b,
        compute_loss_stage_b=compute_loss_stage_b,
        n_panels=n_panels,
    )

    status_b = lbfgs_result['status']
    message_b = lbfgs_result['message']

    # KEEP existing final Bragg generation code AS-IS (lines 3492-3600)
    # Extract shell_modifier_raw from param_values
    shell_modifier_raw = stage_b_param_values['shell_modifier_raw']

    # Update bragg_full with Stage B result (using best params)
    with torch.no_grad():
        shell_modifiers_final = torch.nn.functional.softplus(shell_modifier_raw) * 2.0
        shell_modifiers_final = torch.clamp(shell_modifiers_final, max=config.stage_b_max_modifier)
        # ... (existing final Bragg generation logic)
```

#### Step 5: Compilation Check

```bash
python -c "import dbex.nanobrag_refinement" && echo "SUCCESS" || echo "FAILED"
```

MUST return exit code 0.

#### Step 6: MANDATORY Regression Guard

```bash
cd /home/ollie/Documents/diffbragg_example

# Run Stage B smoke test (small detector)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T070000Z/pytest_stage_b_shell_modifiers.log 2>&1

echo "Exit code: $?"
```

**MUST PASS** (exit code 0). If FAIL → document blocker, revert changes, escalate to Galph.

#### Step 7: Telemetry Comparison

Extract telemetry from test run and compare with Phase C0 baseline (2025-11-23T061726Z).

**Baseline metrics** (from C0):
- Initial chi²: ~660M (small detector, Stage A final loss)
- Stage B improvement: typically 0.001-0.01% (below REFINE-008 gate, expect early_stop)
- Status: "early_stop" or "ok"

**Validation**:
- Status matches baseline ("early_stop" or "ok")
- Telemetry structure complete (stage_b_params, optimizer, traces)
- No regressions in chi² or MSE traces

#### Step 8: Update implementation.md

Mark Phase C1a checklist items complete:
- [x] C1a-loop1: Extract `_build_stage_b_params` ✓
- [x] C1a-loop2: Extract `_build_stage_b_lbfgs_closure` ✓
- [x] C1a-loop3: Extract `_run_stage_b_lbfgs` + wire all 3 helpers + regression guard ✓

#### Step 9: Write summary.md

Include Turn Summary block at top (per supervisor requirement):
```markdown
### Turn Summary
Extracted _run_stage_b_lbfgs helper (~100 lines LBFGS execution + improvement gate), fixed helper2 signature bug (return tuple not scalar), wired all 3 helpers into run_nanobrag_refinement (~610 lines → ~50 lines orchestration), regression guard test_stage_b_shell_modifiers PASSED.
Phase C1a COMPLETE (3-loop multi-stage extraction strategy SUCCESS per Phase B precedent).
Next: Phase C1b (StageB wrapper class calling extracted helpers).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T070000Z/ (pytest log, telemetry comparison, patch)
```

Then full implementation summary:
- Helper signature
- Line count reduction
- Wiring changes
- Regression guard result
- Next steps (Phase C1b)

#### Step 10: Commit

```bash
git add -A
git commit -m "ARCH-REFINE-FLOW-001 Phase C1a-loop3: Extract _run_stage_b_lbfgs + wire all 3 helpers (~610→~50 lines), fix helper2 signature, regression guard PASSED — tests: pytest test_stage_b_shell_modifiers"
git push
```

## How-To Map

### Helper Extraction
```bash
# Insert _run_stage_b_lbfgs at line 2589 (after helper2)
# Extract lines 3427-3490 (~64 lines of LBFGS execution)
# Total helper: ~100 lines (including signature, param extraction, return dict)
```

### Helper2 Signature Fix
```bash
# Edit line 2586 in _build_stage_b_lbfgs_closure
# Change: return closure_stage_b
# To: return compute_loss_stage_b, closure_stage_b
```

### Stage B Wiring
```bash
# Replace lines ~3040-3540 (~500 lines inline code)
# With ~50 lines helper orchestration (3 helper calls + frozen tensor injection)
# Keep final Bragg generation AS-IS (lines 3492-3600)
```

### Compilation Check
```bash
python -c "import dbex.nanobrag_refinement" && echo "SUCCESS: exit code 0" || echo "FAILED"
```

### Regression Guard
```bash
cd /home/ollie/Documents/diffbragg_example

AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T070000Z/pytest_stage_b_shell_modifiers.log 2>&1

echo "Regression guard exit code: $?"
```

### Artifacts
```bash
# Save patch
git diff > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T070000Z/phase_c1a_loop3_extraction_diff.patch

# Compilation log already saved above

# Pytest log already saved above

# Telemetry comparison
echo "Compare with Phase C0 baseline: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/telemetry_small.json"
```

## Pitfalls To Avoid

1. **Helper2 signature bug**: MUST fix helper2 to return tuple `(compute_loss, closure)` not just `closure`, else helper3 cannot access compute_loss_stage_b for final validation
2. **Frozen tensor injection**: MUST add all 8 frozen Stage A tensors (log_scale, 6 cell tensors, misset_xyz_deg) PLUS best_loss_full to param_values BEFORE calling helper2
3. **param_values dict consistency**: Ensure helper1 populates all keys that helper2/helper3 expect; missing keys cause NameError (learned from Phase B1a-loop3 bug)
4. **Final step calculation**: Access `loss_trace_sample_b` from param_values, not local scope (it's a list mutated by closure)
5. **Trace mutation bug**: chi_squared_best_b, masked_mse_best_b, best_loss_full_b are 2-tuples [value, step], NOT lists; use tuple assignment `chi_squared_best_b = (value, step)` not `[0] = value`
6. **Device routing**: Preserve CPU fallback logic (PERF-WARM-011/012) and eval_device routing in helper3
7. **Best snapshot restore**: Always restore best params AFTER final validation, even on success (existing logic at lines 3469-3473)
8. **Improvement gate**: Check `best_loss_full[0] > 0` before computing improvement_b to avoid division by zero
9. **Regression guard MANDATORY**: If test FAILS, REVERT all changes and document blocker — do NOT commit broken code
10. **NO early optimization**: Pure extraction + wiring — do NOT refactor, rename, or optimize; preserve exact logic

## If Blocked

### Blocker Scenarios

1. **Compilation error**: Check lazy imports, param_values dict keys, helper2 signature fix
2. **NameError in regression guard**: Missing param_values dict entry — check helper1 output, add missing keys
3. **Regression guard FAIL (wrong chi²/telemetry)**: Wiring bug — verify frozen tensor injection, trace mutation, final Bragg generation preserved
4. **Tuple assignment error**: chi_squared_best_b is 2-tuple, use `(value, step)` not `[value, step]`
5. **Helper2 signature mismatch**: Verify helper2 returns tuple `(compute_loss, closure)` not just `closure`

### Escalation

If any blocker persists after 2 attempts:
1. Document error signature (first 100 chars of traceback)
2. Record attempted fixes
3. Revert changes: `git checkout dbex/nanobrag_refinement.py`
4. Write blocker report in plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T070000Z/phase_c1a_loop3_blocker.md
5. Commit blocker artifacts and push
6. Next action: Galph reviews blocker and decides (debug, simplify scope, escalate to multi-loop)

## Findings Applied

**Relevant Findings from Knowledge Base:**

- **REFINE-008**: Stage B calibrated gate ≥0.002% improvement; helper3 must check improvement_b vs config.stage_b_min_loss_improvement
- **PERF-WARM-009**: Force panel evaluation for initial/final Stage B validations to keep modifiers within ±1% gate
- **PERF-WARM-011**: CPU fallback for Stage B panel-mode runs (config.stage_b_full_eval_on_cpu + CUDA + no ROI)
- **PERF-WARM-012**: Clone Stage A context to CPU when fallback active; helper3 must preserve device routing
- **PHYSICS-LOSS-001**: Dual metric tracking (chi_squared + masked_mse); helper3 must record BOTH in final traces
- **PHYSICS-LOSS-002**: Variance floor statistics tracked via compute_loss call
- **POLICY-001**: Environment Freeze — no new imports, no signature changes (except helper2 fix)
- **Phase B precedent**: B1a-loop3 extracted `_run_stage_a_lbfgs` (~156 lines), wired 3 helpers, regression guard PASSED (commit caa510e)

## Pointers

- **Spec**: docs/spec-db-workflow.md §7 (Stage B physics)
- **Implementation Plan**: plans/active/ARCH-REFINE-FLOW-001/implementation.md:179-196 (Phase C checklist)
- **Fix Plan**: docs/fix_plan.md:181 (ARCH-REFINE-FLOW-001 Attempts History)
- **Phase B1a-loop3 Precedent**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060500Z/summary.md (helper3 extraction, wiring, bugfix, regression guard SUCCESS)
- **Phase C0 Baseline**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/telemetry_small.json (baseline metrics for comparison)
- **Phase C1a-loop1**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/summary.md (helper1, param_values dict structure)
- **Phase C1a-loop2**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T063000Z/summary.md (helper2, closure structure, CURRENT signature bug)

## Next Up

**Phase C1b** (next loop after C1a-loop3 succeeds):
- Implement StageB wrapper class (dbex/refinement/stage_b.py)
- StageB.run() calls 3 extracted helpers directly (mirroring Phase B1b pattern)
- Package telemetry with RefinementTelemetry fields + stage_type="B" + mode="shell_modifiers"
- Regression guard: test_stage_b_shell_modifiers MUST PASS
- Engine contract test: test_engine_executes_mock_stage with StageB stub

## Doc Sync Plan

**NOT APPLICABLE** — No tests added/renamed this loop (wiring-only, existing test_stage_b_shell_modifiers used as regression guard).

## Mapped Tests Guardrail

**SATISFIED** — Mapped test `test_stage_b_shell_modifiers` collects >0 (verified in Phase C0). Regression guard MANDATORY for this loop.
