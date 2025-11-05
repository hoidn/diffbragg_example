# TORCH-REFINE-001 Blocker Report

**Timestamp**: 2025-11-05T010747Z
**Loop**: Ralph implementation
**Focus**: Stage A LBFGS refinement nucleus - mask tensor coercion

## Original Task Status

**COMPLETED**: The original blocking issue has been resolved.

- **Original blocker**: `AttributeError: 'numpy.ndarray' object has no attribute 'to'` when instantiating `nanobrag_torch.Detector`
- **Fix applied**: Added tensor coercion for `detector_config.mask_array` in two locations (LBFGS closure at lines 182-188, final Bragg generation at lines 332-338)
- **Pattern**: Mirrored zero-iteration helper pattern from `dbex/nanobrag_bridge.py:998-1004`
- **Verification**: Simulator now initializes successfully and runs forward passes (confirmed by 6 successful "[HKL stats]" outputs)

## New Blocker Discovered

**Type**: NaN/Inf gradient in backward pass
**Severity**: Blocks test completion
**Status**: Out of scope for current Do Now (mask coercion only)

### Stack Trace

```
tests/dbex/test_torch_refine_smoke.py::test_loss_decreases FAILED

AssertionError: Refinement failed: NaN/Inf gradient detected in 89.86652374267578
assert 'error' != 'error'
 where 'error' = RefinementTelemetry(..., status='error', message='NaN/Inf gradient detected in 89.86652374267578').status
```

### Telemetry Snapshot

```python
RefinementTelemetry(
    optimizer='LBFGS',
    stage='A',
    history_size=10,
    max_iter=20,
    tolerance_grad=1e-07,
    tolerance_change=1e-09,
    roi_sample_fraction=0.15,
    roi_count_sampled=1,
    roi_count_total=1,
    loss_trace_sample=[976179.6875, 976177.4375, 976093.9375],
    loss_trace_full=[(0, 976179.6875)],
    best_loss_full=(976179.6875, 0),
    param_deltas={
        'log_scale': {'initial': 0.0, 'final': 0.0, 'delta': 0.0},
        'log_cell_a_delta': {'initial': 0.0, 'final': 0.0, 'delta': 0.0}
    },
    status='error',
    message='NaN/Inf gradient detected in 89.86652374267578'
)
```

### Analysis

1. **Forward pass is working**:
   - Loss values are finite and reasonable: [976179.69, 976177.44, 976093.94]
   - Loss is decreasing slightly over 3 iterations
   - Simulator executes successfully 6 times (3 sample iterations × 2 panels?)

2. **Backward pass fails**:
   - Gradient check at `dbex/nanobrag_refinement.py:256-259` detects NaN/Inf
   - Error message shows parameter value `89.866...` (misleading - should show gradient value)
   - Likely either `log_scale.grad` or `log_cell_a_delta.grad` contains NaN/Inf

3. **Possible root causes**:
   - Numerical instability in `nanobrag_torch` simulator backward pass
   - Division by zero in loss computation (line 242: `/ mask_subset.sum()`)
   - Large gradients from exp(log_scale) operation (line 234)
   - Missing gradient support in simulator for certain operations

4. **Not related to mask coercion fix**:
   - The original AttributeError is resolved
   - Simulator forward pass works correctly
   - This is a **separate issue** in the gradient computation path

### Artifacts

- Collect log: `plans/active/TORCH-REFINE-001/reports/2025-11-05T010747Z/collect_refine_smoke.log`
- Test log: `plans/active/TORCH-REFINE-001/reports/2025-11-05T010747Z/pytest_refine_smoke.log`

## Recommendation

**For current loop**: Mark original task (mask coercion) as DONE. The AttributeError is fixed and simulator initializes correctly.

**For next loop**: Create new focus item for "TORCH-REFINE-001b: Debug NaN/Inf gradients in LBFGS backward pass" with investigation tasks:
1. Add gradient value logging before the check (line 256-259)
2. Verify `mask_subset.sum() > 0` to avoid division by zero
3. Check if `nanobrag_torch` simulator supports autograd (may need `torch.enable_grad()` context)
4. Add gradient clipping or use `.detach()` selectively if needed
5. Test with smaller `log_scale` initial values to avoid large exp() values

## Exit Criteria Met (Original Do Now)

- [x] Mask tensor coercion implemented in LBFGS refinement path
- [x] Pattern matches zero-iteration helper (dbex/nanobrag_bridge.py:998-1004)
- [x] Device/dtype preserved (uses config.device and torch.float32)
- [x] Simulator initializes without AttributeError
- [ ] Test passes (blocked by unrelated gradient issue - out of scope)
