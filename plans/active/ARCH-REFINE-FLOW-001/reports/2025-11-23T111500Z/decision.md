# Phase C2.2 Decision — Path B (Full FAIL, Small PASS)

## Decision Path: B

**Outcome**: Full detector test FAILED, small detector test PASSED

## Summary

The out-of-place HKL grid fix (replacing in-place assignment with `torch.where` construction) was successfully applied and works correctly on CUDA (small detector PASSED). However, the CPU fallback path (full detector) still fails with the identical gradient error from loop i=217.

## Validation Results

### Full Detector (CPU Fallback Path)
- **Test**: FAILED
- **Telemetry Status**: error
- **Error Message**: `'element 0 of tensors does not require grad and does not have a grad_fn'`
- **HKL Gradient Diagnostics**:
  - Initial validation: `requires_grad=False` (expected, grad_enabled=False)
  - **Closure call**: `requires_grad=True, grad_fn=<WhereBackward0>` ✅ **Fix working!**
  - Final validation: `requires_grad=False` (expected, grad_enabled=False)

### Small Detector (CUDA Warm Cache Path)
- **Test**: PASSED
- **Telemetry Status**: converged
- **Runtime**: 13.75s
- **Shell Modifiers**: Converged successfully (telemetry shows non-zero deltas)

## Key Findings

1. **Out-of-place fix IS working**: During closure execution (grad_enabled=True), HKL grid has `requires_grad=True` and `grad_fn=<WhereBackward0>`, confirming the gradient graph is preserved from `shell_modifiers` through the `torch.where` operation.

2. **CUDA path is healthy**: Small detector test passed completely, validating that the fix resolves the issue on CUDA.

3. **CPU fallback path has deeper issue**: Even with correct HKL grid gradients, the optimizer fails with the same error. This suggests the gradient break occurs **downstream** from HKL grid construction, likely inside `nanobrag_torch.Simulator.run()` or CPU-specific evaluation paths.

## Root Cause Re-Assessment

**Hypothesis A (In-Place HKL Modification)**: **CONFIRMED BUT INSUFFICIENT**
- The out-of-place fix correctly preserves gradients in the HKL grid construction (diagnostic evidence)
- Fix resolves the issue on CUDA (small detector passes)
- However, CPU fallback path has an additional gradient-breaking operation downstream

**Hypothesis B (nanobrag_torch CPU Internals)**: **ELEVATED TO PRIMARY**
- Strong evidence that CPU simulator or evaluation paths break gradients
- Possible causes: `.detach()`, `torch.no_grad()` contexts, gradient-unsafe device transfers
- Requires inspection of nanobrag_torch source code

## Actions Taken (Per input.md Path B Protocol)

1. ✅ HKL diagnostic shows `requires_grad=True` on both paths during closure execution
2. ✅ Wrote `blocker_hypothesis_b.md` documenting nanobrag_torch inspection requirements
3. ✅ DO NOT remove diagnostics (HKL_GRAD_CHECK, CPU_FALLBACK_DIAGNOSTICS blocks preserved)
4. ✅ Wrote `decision.md` (this file)
5. ✅ Saved `validation_metrics.json` with decision path B evidence

## Commit Message

```
ARCH-REFINE-FLOW-001 Phase C2.2: out-of-place HKL fix applied, full detector still fails — tests: fail

Root cause update: Out-of-place torch.where HKL grid construction (lines 2448-2452)
successfully preserves gradients on CUDA (small detector test PASSED). However, CPU
fallback path (full detector) still fails with identical gradient error, indicating
the break occurs downstream in nanobrag_torch CPU evaluation paths.

Evidence: HKL_GRAD_CHECK diagnostic confirms requires_grad=True and grad_fn=<WhereBackward0>
during closure execution, proving HKL fix works. Small detector converged successfully
on CUDA in 13.75s. Full detector fails with "element 0 of tensors does not require grad"
despite correct HKL gradients.

Escalation: Hypothesis B (nanobrag_torch internal CPU issue) now primary. Requires
inspection of Simulator.run() and CPU-specific evaluation paths for gradient-breaking
operations (.detach(), torch.no_grad(), unsafe device transfers).

Path B artifacts: blocker_hypothesis_b.md, validation_metrics.json, decision.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Next Loop

Galph reviews `blocker_hypothesis_b.md` and decides escalation path:
- **Option A**: Inspect nanobrag_torch source for CPU-specific gradient issues
- **Option B**: Alternative HKL grid construction approach
- **Option C**: Defer CPU fallback support for Stage B (document as known limitation)

## Artifacts

- `blocker_hypothesis_b.md` — Hypothesis B escalation document with investigation plan
- `validation_metrics.json` — Test results and decision path evidence
- `decision.md` — This file (4-path synthesis)
- `pytest_stage_b_full_fixed.log` — Full detector failure log with diagnostics
- `pytest_stage_b_small_fixed.log` — Small detector success log
- `root_cause_analysis_v2.md` — Loop i=217 analysis (in-place HKL hypothesis)
