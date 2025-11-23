# Phase C2.2 CPU Fallback Gradient Bug — Root Cause Analysis v2

## Status
**HIGH Confidence (85%)** — In-place HKL modification breaks gradient flow

## Executive Summary

Loop i=217 DISPROVED the warm cache hypothesis: both warm AND cold paths fail with the identical gradient error. The root cause is **in-place tensor modification at lines 2441-2447** that breaks PyTorch's autograd graph.

## Root Cause: In-Place HKL Grid Modification (Hypothesis A)

### Problem Code (lines 2441-2447)
```python
hkl_grid_modified = hkl_grid_local.clone()  # No gradients (source has no grad)
for shell_idx in range(config.stage_b_n_shells):
    mask = (shell_indices_local == shell_idx)
    modifier_value = shell_modifiers[shell_idx]  # HAS gradients
    hkl_grid_modified[mask] = hkl_grid_local[mask] * modifier_value  # In-place assignment
```

### Why It Breaks Gradients

1. `hkl_grid_local` comes from the fixed HKL grid with `requires_grad=False`
2. `hkl_grid_modified = hkl_grid_local.clone()` creates a new tensor WITHOUT gradients
3. In-place assignment `hkl_grid_modified[mask] = ...` does NOT automatically enable gradient tracking
4. Even though the RHS (`hkl_grid_local[mask] * modifier_value`) HAS gradients from `modifier_value`, PyTorch in-place operations on non-gradient tensors don't propagate `requires_grad=True`
5. Result: `hkl_grid_modified` remains without gradients → simulator receives gradient-free HKL data → loss tensor has no gradient → `backward()` fails

### Evidence from Diagnostics

Loop i=217 diagnostic output (line 157):
```
"shell_modifiers_grad_fn": "<ClampBackward1 object at 0x7a0c8c7e3880>"
```

This PROVES `shell_modifiers` HAS gradients at closure evaluation time. The break happens downstream during HKL grid construction.

## Fix: Out-of-Place Tensor Construction

Replace the in-place loop with `torch.where` to build a gradient-enabled tensor:

```python
# Create gradient-enabled HKL grid using out-of-place operations
hkl_grid_modified = hkl_grid_local.clone()
for shell_idx in range(config.stage_b_n_shells):
    mask = (shell_indices_local == shell_idx)
    modifier_value = shell_modifiers[shell_idx]
    # Out-of-place: creates NEW tensor with gradient graph
    hkl_grid_modified = torch.where(
        mask.unsqueeze(-1),  # Broadcast mask to match HKL grid shape
        hkl_grid_local * modifier_value,  # Gradient-enabled operation
        hkl_grid_modified  # Keep existing values for non-matching shells
    )
```

### Why This Works

1. `torch.where` creates a NEW tensor (not in-place modification)
2. The gradient graph flows from `modifier_value` through the multiplication
3. Each iteration builds on the previous `hkl_grid_modified`, accumulating gradient connections
4. Final `hkl_grid_modified` has `requires_grad=True` and a proper `grad_fn`

### Validation Strategy

After fix:
1. Run full detector test (CPU fallback active)
2. Run small detector test (CUDA, warm cache)
3. Add diagnostic BEFORE simulator creation:
   ```python
   print(f"[HKL_GRAD_CHECK] hkl_grid_modified.requires_grad={hkl_grid_modified.requires_grad}, grad_fn={hkl_grid_modified.grad_fn}")
   ```
4. Verify telemetry shows `status='converged'` and `loss_trace_sample` has >1 entry
5. Remove diagnostics and warm cache fix (line 2451)

## Alternative Hypothesis (Lower Confidence)

### Hypothesis B: nanobrag_torch Internal Issue (25%)

If out-of-place fix fails, the problem may be inside `simulator.run()`:
- Possible `.detach()` or `.no_grad()` context
- Tensor copying without gradient preservation
- Device-specific gradient handling bugs

Test: Add diagnostics around `simulator.run()`:
```python
print(f"[BEFORE RUN] crystal.hkl_data.requires_grad={simulator.crystal.hkl_data.requires_grad}")
bragg_panel = simulator.run()
print(f"[AFTER RUN] bragg_panel.requires_grad={bragg_panel.requires_grad}, grad_fn={bragg_panel.grad_fn}")
```

## Implementation Plan

**Loop i=218 Do Now:**
1. REVERT warm cache fix (line 2451: `use_warm_eval = stage_b_use_warm_cache and not use_stage_b_cpu_fallback` → `use_warm_eval = stage_b_use_warm_cache`)
2. Apply out-of-place HKL grid fix (lines 2441-2447)
3. Add HKL gradient diagnostic (before simulator creation)
4. Run full+small detector tests
5. Path A (both PASS): Remove diagnostics → Phase C2.2 COMPLETE
6. Path B (full FAIL): Escalate to Hypothesis B (nanobrag_torch inspection)

## Confidence Assessment

- **In-Place Operation (Hypothesis A):** 85% — Strong PyTorch autograd theory + diagnostic evidence
- **nanobrag_torch Internal (Hypothesis B):** 15% — Possible but less likely given diagnostic shows gradients present on shell_modifiers
- **Other causes:** <1%

## Finding Draft

**GRADIENT-002** (In-Place Tensor Modification Breaks Autograd)
- **Tags:** gradient, autograd, pytorch, stage-b
- **Summary:** In-place tensor assignment (`tensor[mask] = rhs`) on tensors without `requires_grad=True` does NOT automatically enable gradient tracking, even when the RHS has gradients. Use out-of-place operations (`torch.where`, `torch.cat`) to construct gradient-enabled tensors from operations involving trainable parameters.
- **Source:** dbex/nanobrag_refinement.py:2441-2447, loop i=217/218
- **Status:** Active
