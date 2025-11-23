# Phase C2.2 Blocker — Hypothesis B Escalation

## Status
**Path B**: Full detector FAILS, small detector PASSES → Out-of-place HKL fix applied but CPU fallback path still has gradient issues

## Executive Summary

Loop i=218 applied the out-of-place HKL grid fix (replacing in-place `hkl_grid_modified[mask] = ...` with `torch.where` construction). **Small detector test PASSED** (CUDA warm cache path), confirming the fix works correctly on CUDA. However, **full detector test FAILED** (CPU fallback path) with the same gradient error: `'element 0 of tensors does not require grad and does not have a grad_fn'`.

## Evidence

### HKL Gradient Diagnostics (Full Detector, CPU Fallback Path)

Three calls observed:
1. **Initial validation** (is_full=True, grad_enabled=False): `hkl_grid_modified.requires_grad=False, grad_fn=None, device=cpu`
2. **Closure call** (is_full=False, grad_enabled=True): `hkl_grid_modified.requires_grad=True, grad_fn=<WhereBackward0>, device=cpu` ✅ **Out-of-place fix IS working!**
3. **Final validation** (is_full=True, grad_enabled=False): `hkl_grid_modified.requires_grad=False, grad_fn=None, device=cpu`

### Key Insight

During the closure call (where gradients matter for `.backward()`), the HKL grid **DOES** have gradients (`requires_grad=True, grad_fn=<WhereBackward0>`). This proves the out-of-place fix is working correctly—the gradient graph is preserved from `shell_modifiers` through the `torch.where` operation.

However, the optimizer still fails with `'element 0 of tensors does not require grad'` when trying to compute gradients.

### Test Results

- **Full detector (CPU fallback)**: FAILED — same gradient error as loop i=217
- **Small detector (CUDA warm cache)**: PASSED — refinement completed successfully, shell modifiers converged

### CPU Fallback Diagnostics (from log)

```json
{
  "location": "_build_stage_b_lbfgs_closure",
  "use_stage_b_cpu_fallback": true,
  "is_full": true,
  "grad_enabled": false,
  "device_global": "cuda:0",
  "shell_modifier_raw_device": "cpu",
  "shell_modifiers_device": "cpu",
  "eval_device": "cpu",
  "eval_device_type": "cpu",
  "shell_modifier_raw_requires_grad": true,
  "shell_modifiers_requires_grad": false,
  "shell_modifiers_grad_fn": "None"
}
```

During closure execution (grad_enabled=True):
```json
{
  "grad_enabled": true,
  "shell_modifiers_requires_grad": true,
  "shell_modifiers_grad_fn": "<ClampBackward1 object at 0x7068bdc67280>"
}
```

## Root Cause Hypothesis B

**The gradient break is NOT in the HKL grid construction** (that's fixed). The break is **inside nanobrag_torch.Simulator.run() or related CPU evaluation paths**.

Possible causes:
1. CPU simulator uses `.detach()` or `.no_grad()` context internally
2. Tensor copying during CPU evaluation doesn't preserve gradients
3. CPU-specific code path in nanobrag_torch has gradient-breaking operations
4. Device transfers (CUDA → CPU → CUDA) for parameters break the gradient graph

## Hypothesis B Escalation Requirements

To investigate nanobrag_torch internals, need to:

1. **Add diagnostics around simulator.run()** in the CPU fallback path:
   ```python
   print(f"[BEFORE RUN] crystal.hkl_data.requires_grad={simulator.crystal.hkl_data.requires_grad}")
   print(f"[BEFORE RUN] crystal.hkl_data.grad_fn={simulator.crystal.hkl_data.grad_fn}")
   bragg_panel = simulator.run()
   print(f"[AFTER RUN] bragg_panel.requires_grad={bragg_panel.requires_grad}")
   print(f"[AFTER RUN] bragg_panel.grad_fn={bragg_panel.grad_fn}")
   ```

2. **Inspect nanobrag_torch.Simulator source** for:
   - `.detach()` calls
   - `with torch.no_grad():` contexts
   - `.cpu()` or `.to(device=...)` calls that might break gradients
   - Numpy conversions (`.numpy()`) that would break autograd

3. **Compare CUDA vs CPU simulator paths** to identify CPU-specific gradient-breaking operations

4. **Test minimal reproducer**: Create a standalone script that:
   - Builds a simple crystal with modified HKL grid (via `torch.where`)
   - Runs simulator.run() on CPU with autograd enabled
   - Attempts loss.backward()
   - Captures exact failure point

## Path Forward Options

### Option A: Fix nanobrag_torch CPU Evaluation
If investigation reveals a fixable bug in nanobrag_torch (e.g., unnecessary `.detach()` or `.no_grad()` context), apply targeted patch per CLAUDE.md Environment Freeze exception rules (local source bugfix with documented patch file).

### Option B: Alternative HKL Grid Construction
If nanobrag_torch CPU path is fundamentally incompatible with gradient tracking, explore alternative approaches:
- Pre-build modified HKL grid before Stage B (outside closure)
- Use CUDA-only evaluation for Stage B (skip CPU fallback)
- Implement custom gradient function for HKL modification

### Option C: Defer CPU Fallback Support
Mark CPU fallback path as unsupported for Stage B gradient-based refinement, document as known limitation, and require CUDA for Stage B. Full detector tests would run Stage A only.

## Artifacts

- `validation_metrics.json` — Decision path B evidence
- `pytest_stage_b_full_fixed.log` — Full detector failure with HKL grad diagnostics
- `pytest_stage_b_small_fixed.log` — Small detector success (CUDA path)
- `root_cause_analysis_v2.md` — Loop i=217 analysis that led to out-of-place fix

## Findings Draft

**GRADIENT-003** (CPU Fallback Path Breaks Gradients in Stage B)
- **Tags:** gradient, autograd, cpu-fallback, stage-b, nanobrag-torch
- **Summary:** After fixing in-place HKL modification (GRADIENT-002), Stage B refinement works correctly on CUDA but fails on CPU fallback path with identical gradient error. HKL grid construction preserves gradients (confirmed via diagnostic: `requires_grad=True, grad_fn=<WhereBackward0>`), suggesting the break occurs inside nanobrag_torch CPU evaluation paths.
- **Source:** Loop i=218, dbex/nanobrag_refinement.py:2441-2452 (fixed), nanobrag_torch internal paths (suspected)
- **Status:** Active — Requires nanobrag_torch inspection
- **Next Actions:** Add simulator-level diagnostics, inspect CPU vs CUDA simulator paths, consider minimal reproducer

## Decision

**DO NOT remove diagnostics** — Keep HKL_GRAD_CHECK and CPU_FALLBACK_DIAGNOSTICS blocks for Galph review.

**Commit message**: "ARCH-REFINE-FLOW-001 Phase C2.2: out-of-place HKL fix applied, full detector still fails — tests: fail"

**Next loop**: Galph reviews Hypothesis B escalation and decides investigation path (nanobrag_torch inspection, alternative architecture, or defer CPU fallback).
