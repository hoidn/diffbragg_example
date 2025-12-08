# Gradient Investigation Summary — Loop i=191

**Date**: 2025-12-08T162000Z
**Focus**: ARCH-GRADIENT-FLOW-001 Phase B.2 (Gradcheck Verification)

## Upstream Response Received

File: `inbox/nanobrag_torch_response_2025_12_08.md`

### Summary of Upstream Fixes
1. **Gradient blockers RESOLVED**: Wavelength, fluence, and detector distance gradient flow restored via:
   - `as_tensor_preserving_grad()` helper in `tensor_utils.py`
   - Detector `distance`, `pixel_size`, `close_distance` converted to properties reading from config

2. **SQUARE partiality NOT a bug**: DBEX expectation of N² scaling incorrect; should be N (linear) for integrated intensity

## Investigation Results

### Test Command
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests -k "DB_AT_010" --smoke-detector-size=full
```

### Results: 5/5 FAILED (GradcheckError - Jacobian mismatch)

| Parameter | Numerical Gradient | Analytical Gradient | Ratio | Notes |
|-----------|-------------------|---------------------|-------|-------|
| cell_a | -3.5542e+11 | 6.97e+07 | ~5096x | Sign flip |
| cell_gamma | 3.0524e+11 | 4.59e+07 | ~6645x | |
| distance | 1.3514e+12 | 1.06e+07 | ~127627x | |
| wavelength | Similar large | Similar small | ~10000x | |

### Key Finding: Partial Gradient Flow

The analytical gradients are **non-zero**, indicating the autograd graph IS connected (progress from pre-fix state where analytical=0). However, magnitudes are 3-5 orders of magnitude too small compared to numerical gradients.

### Verification Probes

1. **Isolated component tests PASS**:
   - `detector.distance` backprop: gradient flows correctly through mm→m conversion
   - `crystal.cell_a` backprop: gradient flows correctly through Crystal constructor
   - Config post-creation override preserves tensor identity and requires_grad

2. **End-to-end simulation**: `output.requires_grad=True` confirms graph connected

### Bug Found: DetectorConfig `__post_init__` tensor loss

In `nanobrag_torch/config.py:284-285`:
```python
if self.distance_mm == 100.0:  # Default value check
    self.distance_mm = self.close_distance_mm  # Replaces tensor with float!
```

When `close_distance_mm` is provided and `distance_mm` tensor equals 100.0, the tensor is replaced with a float, breaking gradient flow. **This bug is NOT triggered by DBEX tests** (distance=230mm), but should be fixed in nanobrag_torch.

### Hypothesis for Magnitude Mismatch

The 5000-127000x discrepancy suggests:
1. Missing chain rule factor(s) in the physics computation
2. Possible undifferentiated operations in B-matrix → q-vector → sincg lookup chain
3. Units conversion that isn't being differentiated (mm→m, deg→rad, Å→Å⁻¹)

Requires deeper inspection of `nanobrag_torch/models/crystal.py` B-matrix computation and `simulator.py` physics loop.

## Status

**ARCH-GRADIENT-FLOW-001**: Blocked — requires upstream fix for gradient magnitude

**Action Required**: Escalate to nanobrag_torch maintainers with evidence:
1. Gradient graph connected (analytical non-zero)
2. Magnitude mismatch (5000-127000x)
3. Isolated tests pass; integration fails
4. Need inspection of B-matrix / sincg gradient chain

## Artifacts

- `pytest_db_at_010.log`: Full test output
- `gradient_investigation_summary.md`: This file
