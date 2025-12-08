# DBEX Gradient Blockers Fix Report

**Date:** 2025-12-07
**Issue:** DBEX-GRADIENT-001
**Status:** RESOLVED

---

## Executive Summary

This report documents the fixes implemented to resolve gradient flow blockers that affected differentiable rendering experiments (DBEX). The core issue was that `torch.tensor()` was being used to convert parameters, which **detaches** tensors from the computation graph, breaking gradient flow for optimization.

All identified gradient blockers have been fixed. DBEX can now optimize `wavelength`, `fluence`, and `distance` parameters with full gradient support.

---

## Issues Identified and Fixed

### Issue 1: Wavelength Gradient Blocked (simulator.py:571)

**Problem:**
```python
# OLD CODE - BROKEN
self.wavelength = torch.tensor(self.beam_config.wavelength_A, device=self.device, dtype=self.dtype)
```

When `beam_config.wavelength_A` was a tensor with `requires_grad=True`, `torch.tensor()` would create a **new tensor** without gradient tracking, severing the computation graph.

**Solution:**
```python
# NEW CODE - FIXED
self.wavelength = as_tensor_preserving_grad(
    self.beam_config.wavelength_A, device=self.device, dtype=self.dtype
)
```

### Issue 2: Fluence Gradient Blocked (simulator.py:579)

**Problem:** Same pattern as wavelength.

**Solution:** Same fix applied.

### Issue 3: Detector Distance Post-Override Pattern (detector.py)

**Problem:**
DBEX creates a `Detector` with float distance, then later overwrites `config.distance_mm` with a differentiable tensor. The old implementation stored `self.distance = config.distance_mm / 1000.0` at init time, so post-creation changes to `config.distance_mm` were not reflected.

**Solution:**
Converted `distance`, `pixel_size`, and `close_distance` from instance variables to **properties** that dynamically read from the config:

```python
@property
def distance(self) -> torch.Tensor:
    """Detector distance in meters, dynamically read from config."""
    return as_tensor_preserving_grad(
        self.config.distance_mm / 1000.0, device=self.device, dtype=self.dtype
    )
```

This enables the DBEX post-override pattern to work correctly.

---

## New Utility: `as_tensor_preserving_grad`

A new utility function was added at `src/nanobrag_torch/utils/tensor_utils.py`:

```python
def as_tensor_preserving_grad(
    x: Union[float, int, torch.Tensor],
    device: torch.device,
    dtype: torch.dtype
) -> torch.Tensor:
    """
    Convert scalar or tensor to tensor while preserving gradient graph.

    Uses x.to(device, dtype) if tensor, else torch.tensor(x, device, dtype).
    """
    if isinstance(x, torch.Tensor):
        return x.to(device=device, dtype=dtype)
    return torch.tensor(x, device=device, dtype=dtype)
```

---

## How to Use These Fixes in DBEX

### Pattern 1: Tensor at Init Time (Recommended)

Pass differentiable tensors directly when creating configs:

```python
import torch
from nanobrag_torch.config import BeamConfig, DetectorConfig, CrystalConfig
from nanobrag_torch.models.crystal import Crystal
from nanobrag_torch.models.detector import Detector
from nanobrag_torch.simulator import Simulator

# Create differentiable parameters
wavelength = torch.tensor(6.2, dtype=torch.float64, requires_grad=True)
distance = torch.tensor(100.0, dtype=torch.float64, requires_grad=True)

# Pass tensors directly to configs
beam_config = BeamConfig(wavelength_A=wavelength, fluence=1e28)
detector_config = DetectorConfig(
    distance_mm=distance,
    pixel_size_mm=0.1,
    spixels=256,
    fpixels=256,
)

# Create components
crystal_config = CrystalConfig(cell_a=100.0, cell_b=100.0, cell_c=100.0, ...)
crystal = Crystal(config=crystal_config, device="cpu", dtype=torch.float64)
detector = Detector(config=detector_config, device="cpu", dtype=torch.float64)

# Create simulator
simulator = Simulator(
    crystal=crystal,
    detector=detector,
    crystal_config=crystal_config,
    beam_config=beam_config,
    device="cpu",
    dtype=torch.float64,
)

# Run forward pass
result = simulator.run()
loss = result.sum()

# Backward pass - gradients now flow!
loss.backward()

print(f"wavelength.grad = {wavelength.grad}")  # Non-zero gradient
print(f"distance.grad = {distance.grad}")      # Non-zero gradient
```

### Pattern 2: Post-Creation Override (DBEX Pattern)

If you need to create components first and override parameters later, this now works for detector geometry:

```python
# Step 1: Create detector with float distance
detector_config = DetectorConfig(distance_mm=100.0, ...)
detector = Detector(config=detector_config, device="cpu", dtype=torch.float64)

# Step 2: Later, override with differentiable tensor
distance = torch.tensor(100.0, dtype=torch.float64, requires_grad=True)
detector_config.distance_mm = distance

# Step 3: Create simulator and run
simulator = Simulator(crystal=crystal, detector=detector, ...)
result = simulator.run()
loss = result.sum()
loss.backward()

# Gradient flows correctly!
print(f"distance.grad = {distance.grad}")
```

**Note:** For `wavelength` and `fluence`, the pattern 1 (init-time) approach is required because the Simulator copies these values at construction time. The post-override pattern only works for detector geometry parameters.

---

## Environment Requirements

For gradient tests and debugging, disable torch.compile:

```bash
export NANOBRAGG_DISABLE_COMPILE=1
export KMP_DUPLICATE_LIB_OK=TRUE
```

Or in Python:
```python
import os
os.environ["NANOBRAGG_DISABLE_COMPILE"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
```

---

## Test Coverage

New tests added in `tests/test_gradients.py::TestDBEXGradientBlockers`:

| Test | Description | Status |
|------|-------------|--------|
| `test_wavelength_gradient_at_init` | Wavelength tensor preserves requires_grad | PASS |
| `test_wavelength_gradcheck` | Numerical gradient verification | PASS |
| `test_fluence_gradient_at_init` | Fluence tensor preserves requires_grad | PASS |
| `test_distance_gradient_at_init` | Distance tensor at init time | PASS |
| `test_distance_post_override_gradient` | DBEX post-override pattern | PASS |
| `test_distance_gradcheck` | Numerical gradient verification | PASS |

Run the tests:
```bash
env NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE \
    pytest tests/test_gradients.py::TestDBEXGradientBlockers -v
```

---

## Files Changed

1. **`src/nanobrag_torch/utils/tensor_utils.py`** (NEW)
   - Added `as_tensor_preserving_grad()` helper function

2. **`src/nanobrag_torch/config.py`**
   - Updated type hints for `BeamConfig.wavelength_A` and `BeamConfig.fluence` to accept `Union[float, torch.Tensor]`

3. **`src/nanobrag_torch/simulator.py`**
   - Fixed `wavelength` initialization (line ~574)
   - Fixed `fluence` initialization (line ~585)
   - Fixed `kahn_factor` initialization (line ~592)

4. **`src/nanobrag_torch/models/detector.py`**
   - Converted `distance`, `pixel_size`, `close_distance` to properties
   - Added `_close_distance_cached` backing field for r-factor calculations

5. **`tests/test_gradients.py`**
   - Added `TestDBEXGradientBlockers` test class with 6 new tests

---

## Backward Compatibility

All changes are backward compatible:
- Float values continue to work exactly as before
- Existing code that passes floats will see no behavior change
- Only code that passes tensors with `requires_grad=True` will see the new gradient flow behavior

---

## Contact

For questions about this fix, refer to:
- Plan document: `plans/active/dbex-gradient-blockers.md`
- Verification script: `scripts/verify_dbex_gradient_bugs.py`
