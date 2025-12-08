# Differentiability Guide: C-to-PyTorch Translation

This guide distills hard-won lessons from porting scientific C code to differentiable PyTorch. It is **required reading** before implementing or modifying any differentiable code path.

## 1. The C-to-PyTorch Translation Table

| Feature | C (Non-Differentiable) | PyTorch (Differentiable) | Rationale |
|---------|------------------------|--------------------------|-----------|
| **Parameters** | `double a;` scalar | `torch.tensor(..., requires_grad=True)` | Required for autograd tracking |
| **Lookups** | Discrete array indexing `Fhkl[h0][k0][l0]` | Differentiable interpolation (`grid_sample` or custom tricubic) | Discrete lookup has zero derivative almost everywhere |
| **Conditionals** | `if/else` | `torch.where(cond, x, y)` | Standard if/else creates dead ends in the computation graph |
| **State** | Pre-compute and store derived values | Re-compute inside forward pass | Pre-computing detaches derived values from their inputs |
| **Mutation** | In-place via pointers `unitize(v, v)` | Functional: `new_v = unitize(v)` | In-place ops can break autograd or produce incorrect gradients |
| **Iteration** | Nested for loops over pixels/sources/domains | Tensor broadcasting + `torch.sum()` | Enables efficient batched autodiff and GPU acceleration |

## 2. Gradient-Breaking Patterns

### 2.1 FORBIDDEN Operations on Differentiable Tensors

```python
# ❌ FORBIDDEN: These sever the computation graph

# .item() extracts a Python scalar — graph connection lost
config = Config(param=tensor.item())

# .numpy() requires detaching — graph connection lost
array = tensor.numpy()

# .detach() explicitly removes from graph
fixed = tensor.detach()

# torch.linspace doesn't propagate gradients to endpoints
range_t = torch.linspace(start_tensor, end_tensor, n)
```

### 2.2 CORRECT Alternatives

```python
# ✅ CORRECT: Preserve gradient flow

# Pass tensors directly to configs/functions
config = Config(param=tensor)

# For range generation with gradient-requiring endpoints:
range_t = start_tensor + (end_tensor - start_tensor) * torch.arange(n, device=start_tensor.device) / (n - 1)

# For conditionals, use torch.where instead of if/else:
result = torch.where(condition, value_if_true, value_if_false)
```

### 2.3 Verification

After any change to differentiable code:
```python
# Check that gradients propagate
assert output.requires_grad, "Output lost gradient tracking"
assert param.grad is not None, "Gradient did not flow to parameter"

# For thorough validation, use gradcheck (float64 required)
torch.autograd.gradcheck(func, inputs, eps=1e-6, atol=1e-4, rtol=1e-3)
```

## 3. Minimal Fix, Measured Impact

**Principle**: Reproduce → Fix minimally → Measure. Only harden math where a concrete failure exists.

### 3.1 Checklist for Helper Changes

Before merging any change to a hot numerical helper (e.g., `sincg`, `sinc3`, polarization):

- [ ] **Issue reproduced**: Link to failing gradcheck, NaN trace, or numerical error
- [ ] **Minimal change**: No speculative branches or "just in case" guards
- [ ] **Gradcheck passes**: float64 required; float32 if production-relevant
- [ ] **Microbenchmark**: ≥1e6 evaluations shows no regression (or regression justified with data)
- [ ] **Vectorization preserved**: No data-dependent Python control flow introduced
- [ ] **Tolerance rationale**: States dtype assumptions (float64 dev vs float32 prod)

### 3.2 Do/Don't for Analytic Limits

**Do**:
- Apply a single mask covering edge cases (e.g., near-integer for sincg covers n=0)
- Use at most one epsilon guard as cheap insurance against tiny denominators
- Back any extra branches with gradcheck + microbench numbers

**Don't**:
- Add separate zero branches or nested `torch.where` without measured need
- Duplicate masks or recompute trig unnecessarily in the hot path
- Assume float64 tolerances when production runs in float32

### 3.3 Example: sincg Lessons

What happened:
- Multiple special cases (zero and near-integer) and extra guards were added to "ensure" differentiability
- Later analysis showed the zero case can be merged into the near-integer mask, and the denominator guard is mostly redundant at the documented tolerance
- The extra branching slowed the hot path without improving gradients

Key lesson: Over-hardening is as harmful as under-hardening. Measure before adding complexity.

## 4. Common Gradient Debugging Patterns

### 4.1 Symptom: `param.grad is None` after `backward()`

**Causes**:
1. Parameter created without `requires_grad=True`
2. `.item()`, `.numpy()`, or `.detach()` used somewhere in the forward path
3. `torch.linspace` with tensor endpoints
4. In-place modification of a tensor that requires grad

**Diagnosis**:
```python
# Trace requires_grad through the computation
def check_grad_flow(tensor, name=""):
    print(f"{name}: requires_grad={tensor.requires_grad}, grad_fn={tensor.grad_fn}")
```

### 4.2 Symptom: `gradcheck` fails with large relative error

**Causes**:
1. Numerical instability at edge cases (division by near-zero)
2. Discontinuous operations (hard thresholds, `torch.clamp` at boundaries)
3. dtype mismatch (running gradcheck in float32)

**Diagnosis**:
```python
# Always run gradcheck in float64
inputs = inputs.double()
model = model.double()
torch.autograd.gradcheck(model, inputs, eps=1e-6, atol=1e-4, rtol=1e-3)
```

### 4.3 Symptom: "modified in-place" RuntimeError

**Cause**: A tensor needed for backward was modified after being used in a computation.

**Fix**: Use functional operations that return new tensors instead of modifying in-place.

```python
# ❌ In-place modification
x *= 2  # or x.mul_(2)

# ✅ Functional
x = x * 2
```

## 5. Runtime Environment for Gradient Tests

Gradient tests require specific environment setup:

```bash
# Required: Disable torch.compile (interferes with gradcheck)
export NANOBRAGG_DISABLE_COMPILE=1

# Required: Prevent MKL/BLAS conflicts
export KMP_DUPLICATE_LIB_OK=TRUE

# Recommended: Force CPU for determinism
export CUDA_VISIBLE_DEVICES=''

# Run gradient tests
pytest -v tests/test_gradients.py -k gradcheck
```

**Rationale**:
- `torch.compile` creates donated buffers that break gradient computation during numerical checks
- Test files should set `os.environ["NANOBRAGG_DISABLE_COMPILE"] = "1"` at module level, before importing torch

## 6. Integration with Existing Docs

Cross-references:
- **Runtime guardrails**: `docs/pytorch_runtime_checklist.md` — vectorization, device/dtype, compile hygiene
- **Spec requirements**: `docs/spec-db-runtime.md` §Differentiability — normative SHALL/MUST rules
- **Testing strategy**: `docs/development/testing_strategy.md` §4 — Tier 2 gradient testing
- **Architecture**: `docs/architecture/pytorch_design.md` §1.2 — Differentiability vs Performance

---

Last updated: 2025-12-08
Source: Lessons extracted from nanoBragg PyTorch port (3-6 months debugging experience distilled)
