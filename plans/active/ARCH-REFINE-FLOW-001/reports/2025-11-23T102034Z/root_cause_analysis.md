# Phase C2.2 CPU Fallback Gradient Bug — Root Cause Analysis

## Executive Summary

**Status:** ROOT CAUSE IDENTIFIED with HIGH confidence (~95%)

**The Bug:** Shell modifier parameters are created on CUDA device, but when CPU fallback is active, they are moved to CPU via `.to(device=eval_device)` inside the LBFGS closure. This `.to()` operation **breaks the autograd gradient chain**, causing the error: "element 0 of tensors does not require grad and does not have a grad_fn".

**The Fix:** Create `shell_modifier_raw` parameters on CPU when `use_stage_b_cpu_fallback=True`, matching the `eval_device` that will be used in the closure.

## Detailed Analysis

### Evidence Chain

1. **Shell Modifier Parameter Creation** (dbex/nanobrag_refinement.py:2134-2138)
   ```python
   stage_b_param_device = torch.device(config.device)  # = "cuda:0"
   shell_modifier_raw = torch.zeros(
       config.stage_b_n_shells,
       device=stage_b_param_device,  # Created on CUDA
       dtype=dtype,
       requires_grad=True
   )
   ```

2. **CPU Fallback Activation** (lines 2178-2182, confirmed by diagnostics)
   ```python
   use_stage_b_cpu_fallback = (
       config.stage_b_full_eval_on_cpu
       and str(device).startswith("cuda")
       and not use_stage_a_roi_mode
   )
   # Result: use_stage_b_cpu_fallback=True for full detector test
   ```

3. **Closure Execution Device** (line 2383)
   ```python
   eval_device = torch.device("cpu") if use_stage_b_cpu_fallback else device
   # Result: eval_device="cpu" when fallback active
   ```

4. **Gradient Chain Break** (lines 2379-2436)
   ```python
   # Line 2379: shell_modifiers computed from CUDA tensor
   shell_modifiers = torch.nn.functional.softplus(shell_modifier_raw) * 2.0
   # shell_modifiers is on CUDA, has requires_grad=True

   # Lines 2433-2436: Device mismatch handling
   modifier_value = shell_modifiers[shell_idx]  # On CUDA
   if modifier_value.device != eval_device:      # CUDA != CPU
       modifier_value = modifier_value.to(device=eval_device)  # BREAKS GRADIENT!
   hkl_grid_modified[mask] = hkl_grid_local[mask] * modifier_value
   ```

### Why `.to(device=...)` Breaks Gradients

PyTorch's `.to(device=...)` creates a **copy** of the tensor on the new device. By default, this copy operation:
- Preserves `requires_grad` flag
- **BUT** creates a new tensor that is not part of the original computation graph
- The new tensor has no `grad_fn` linking it back to the original parameter

When LBFGS tries to call `optimizer.zero_grad()` and compute gradients, it cannot trace back through the `.to()` operation to find `shell_modifier_raw`, resulting in the error.

### Diagnostic Evidence

From `pytest_stage_b_full.log`:
```
CPU_FALLBACK_DIAGNOSTICS_PARAMS: {
    "use_stage_b_cpu_fallback": true,
    ...
}
CPU_FALLBACK_DIAGNOSTICS_CLOSURE: {
    "use_stage_b_cpu_fallback": true,
    "device_param": "cuda:0",    # Parameters on CUDA
    "eval_device": "cpu",         # Closure on CPU — MISMATCH!
}
```

From `telemetry_stage_b_full.json`:
```json
{
    "closure_evals": 1,           # Failed on first closure call
    "loss_trace_sample": [],      # Empty — optimizer never ran
    "status": "error",
    "message": "element 0 of tensors does not require grad and does not have a grad_fn"
}
```

## The Fix

### Change Required

In `_build_stage_b_params` (dbex/nanobrag_refinement.py:2134-2138), replace:

```python
# OLD (INCORRECT for CPU fallback):
stage_b_param_device = torch.device(config.device)
shell_modifier_raw = torch.zeros(
    config.stage_b_n_shells,
    device=stage_b_param_device,
    dtype=dtype,
    requires_grad=True
)
```

With:

```python
# NEW (CORRECT for CPU fallback):
stage_b_param_device = torch.device("cpu") if use_stage_b_cpu_fallback else torch.device(config.device)
shell_modifier_raw = torch.zeros(
    config.stage_b_n_shells,
    device=stage_b_param_device,
    dtype=dtype,
    requires_grad=True
)
```

### Why This Fix Works

1. **Device Consistency:** When `use_stage_b_cpu_fallback=True`, parameters are created on CPU, matching `eval_device="cpu"` in the closure
2. **No Cross-Device Copies:** Lines 2434-2435 (`if modifier_value.device != eval_device: modifier_value = modifier_value.to(device=eval_device)`) become a no-op because devices match
3. **Gradient Chain Preserved:** No `.to()` operation means no gradient chain break; LBFGS can trace back to `shell_modifier_raw`
4. **Optimizer Works:** `optimizer.zero_grad()` can find the parameters and compute gradients correctly

### Validation Strategy

After applying the fix, verify:
1. **Small detector test:** PASS (ROI mode, no CPU fallback, should be unaffected)
2. **Full detector test:** PASS (panel mode, CPU fallback active, gradient bug fixed)
3. **Telemetry checks:**
   - `status='ok'` (not 'error')
   - `closure_evals > 1` (optimizer actually ran)
   - `loss_trace_sample` not empty
   - Shell modifiers show >0.2% delta from initial values
4. **Remove instrumentation:** Diagnostic prints at lines 2197, 2394 no longer needed

## Confidence Assessment

**ROOT CAUSE CONFIDENCE:** 95%
- Direct evidence from code path analysis
- Diagnostic logs confirm device mismatch
- PyTorch autograd behavior well-documented

**FIX CONFIDENCE:** 90%
- Addresses root cause directly
- Simple one-line change
- Consistent with PyTorch best practices for device-aware parameter initialization

**RISK ASSESSMENT:** LOW
- Fix is local to `_build_stage_b_params` helper
- Only affects CPU fallback path (full detector panel mode)
- Small detector ROI mode unaffected (devices already match)

## Implementation Notes

### Alternative Approaches Considered

1. **Use `.to(device=eval_device).requires_grad_(True)` in closure**
   - Rejected: Still breaks gradient chain; `requires_grad_()` on a copied tensor doesn't reconnect to original parameter
   - Would need to replace the original parameter in the optimizer, breaking LBFGS state

2. **Move entire optimizer to CPU when fallback active**
   - Rejected: More complex; requires optimizer state migration
   - Current fix is simpler and more surgical

3. **Disable CPU fallback and accept CUDA OOM**
   - Rejected: PERF-WARM-011 requires CPU fallback for canonical runs
   - Device routing fix (loop i=215) already resolves OOM; just need gradient fix

### Protected Assets

- **Loop i=215 device routing fix:** PRESERVE (OOM resolved, fix is correct)
- **Diagnostic instrumentation:** KEEP until this fix validates (lines 2197, 2394)
- **Stage A/B inline paths:** UNAFFECTED (use same device throughout)
- **Stage B ROI mode:** UNAFFECTED (uses CUDA, no CPU fallback)

## Next Steps

1. Apply one-line fix to `_build_stage_b_params` (line 2134)
2. Run full detector test (expected PASS)
3. Run small detector test (regression guard, expected PASS)
4. Extract metrics via T0 probe
5. Remove instrumentation if both tests PASS
6. Update implementation.md Phase C2.2 COMPLETE
7. Commit with message: "ARCH-REFINE-FLOW-001 Phase C2.2: fix Stage B CPU fallback gradient bug — create shell_modifier_raw on CPU when fallback active"
