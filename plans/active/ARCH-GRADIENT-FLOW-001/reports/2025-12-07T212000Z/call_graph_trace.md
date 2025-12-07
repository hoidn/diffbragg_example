# Call Graph Trace — DB-AT-010 Gradient Flow

**Loop**: Ralph i=138 (ARCH-GRADIENT-FLOW-001 Phase A.1)
**Date**: 2025-12-07
**Objective**: Map full execution path from test → forward → loss → backward to identify module boundaries and tensor flow points.

---

## Executive Summary

Traced 7 call stack levels from gradcheck → test fixture → forward simulation → loss computation. Identified 3 tensor flow boundaries where `requires_grad=True` tensors cross module/function interfaces. Crystal parameter tests use tensor-valued overrides without `.item()` detachment. Detector/beam parameter tests break gradient by calling `.item()` to extract scalar values for dxtbx geometry object construction.

---

## Call Graph Diagram

### Test 1/4: Crystal cell_a (tensor override path)

```
tests/dbex/test_gradients.py::test_db_at_010_gradcheck_crystal_cell_a (line 168)
  ↓ (fixture setup)
  → refinement_inputs fixture (line 106): prepare_refinement_inputs()
    → dbex/refinement/inputs.py::prepare_refinement_inputs (line 60)
      [NO GRADIENT TENSORS: numpy arrays only, no torch involvement]

  ↓ (gradcheck invocation, line 230)
  → torch.autograd.gradcheck(loss_fn, (cell_a_param,), ...)
    → cell_a_param: torch.tensor(..., requires_grad=True) [TENSOR FLOW #1]

    ↓ (loss_fn closure, line 198)
    → crystal_overrides = {'cell_a': cell_a_tensor} [PRESERVES TENSOR, NO .item()]

    ↓ (forward simulation call, line 204)
    → dbex/physics/forward.py::simulate_forward_torch (line 73)
      → crystal_overrides dict passed as kwarg (line 215)
      → Manual override application (lines 183-208)
        → crystal_config.cell_a = crystal_overrides['cell_a'] [TENSOR ASSIGNMENT]

      ↓ (per-panel loop, lines 215-246)
      → dbex/refinement/helpers.py::create_unified_simulator (line 43)
        → crystal_config passed to Crystal constructor (line 198)
        → nanobrag_torch.models.Crystal(crystal_config, ...) [EXTERNAL BOUNDARY]
          [HYPOTHESIS: May break gradient here if Crystal.__init__ calls .item()]

      ↓ (simulation execution, line 239)
      → simulator.run() → bragg_torch [TENSOR FLOW #2: output tensor]

      ↓ (scaling, lines 243-244)
      → sqrt_scale_tensor * bragg_torch [PRESERVES GRADIENT]

    ↓ (loss computation, line 219)
    → dbex/physics/loss.py::compute_masked_mse_loss (line 70)
      → variance = prediction.detach() + sigma_readout**2 (line 147)
        [INTENTIONAL DETACH for IRLS, but numerator preserves gradient]
      → squared_error = (prediction - target) ** 2 (line 141)
      → weighted_squared_error = squared_error / variance (line 150)
      → loss = masked_weighted_error.sum() (line 154) [TENSOR FLOW #3: scalar loss]

    ↓ (gradcheck backward pass)
    → torch.autograd.backward(loss) → compares analytical vs numerical gradients
```

### Test 3/4: Detector distance_mm (scalar extraction path)

```
tests/dbex/test_gradients.py::test_db_at_010_gradcheck_detector_distance (line 344)
  ↓ (gradcheck invocation, line 433)
  → torch.autograd.gradcheck(loss_fn, (distance_param,), ...)
    → distance_param: torch.tensor(..., requires_grad=True) [TENSOR FLOW #1]

    ↓ (loss_fn closure, line 379)
    → **GRADIENT BREAK**: float(distance_tensor.item()) (line 383)
      [CONVERTS TENSOR TO PYTHON SCALAR, BREAKS AUTOGRAD GRAPH]

    → new_distance used to build dxtbx.model.Detector geometry (lines 387-409)
      [DXTBX GEOMETRY OBJECTS ARE NON-DIFFERENTIABLE]

    ↓ (forward simulation call, line 412)
    → dbex/physics/forward.py::simulate_forward_torch (line 73)
      [No crystal_overrides, detector is scalar-based dxtbx object]
      → create_detector_config(panel=new_detector[panel_id], ...)
        → DetectorConfig populated with scalar distance_mm

      ↓ (continues as in crystal path...)
      → loss computation (line 426)
        → **GRADCHECK FAILURE**: Numerical gradient ≠ 0, analytical gradient = 0
          [Because .item() severed autograd connection]
```

### Test 4/4: Beam wavelength_A (scalar extraction path)

```
tests/dbex/test_gradients.py::test_db_at_010_gradcheck_beam_wavelength (line 460)
  ↓ (gradcheck invocation, line 524)
  → torch.autograd.gradcheck(loss_fn, (wavelength_param,), ...)
    → wavelength_param: torch.tensor(..., requires_grad=True) [TENSOR FLOW #1]

    ↓ (loss_fn closure, line 493)
    → **GRADIENT BREAK**: float(wavelength_tensor.item()) (line 496)
      [CONVERTS TENSOR TO PYTHON SCALAR, BREAKS AUTOGRAD GRAPH]

    → new_wavelength used to build dxtbx.model.Beam geometry (lines 499-500)
      [DXTBX GEOMETRY OBJECTS ARE NON-DIFFERENTIABLE]

    ↓ (forward simulation call, line 503)
    → dbex/physics/forward.py::simulate_forward_torch (line 73)
      [No crystal_overrides, beam is scalar-based dxtbx object]
      → create_beam_config(beam=new_beam)
        → BeamConfig populated with scalar wavelength_A

      ↓ (continues as in crystal path...)
      → loss computation (line 517)
        → **GRADCHECK FAILURE**: Numerical gradient ≠ 0, analytical gradient = 0
          [Because .item() severed autograd connection]
```

---

## Tensor Flow Boundaries

### Boundary 1: Test → Forward Simulation
- **Location**: `tests/dbex/test_gradients.py:215` (crystal tests) or `:383, :496` (detector/beam tests)
- **Tensor**: Parameter tensor with `requires_grad=True`
- **Status (crystal tests)**: ✅ PRESERVES GRADIENT via `crystal_overrides` dict
- **Status (detector/beam tests)**: ❌ BREAKS GRADIENT via `.item()` call

### Boundary 2: Forward Simulation → Loss
- **Location**: `dbex/physics/forward.py:249` → `tests/dbex/test_gradients.py:219`
- **Tensor**: `bragg_torch` output from simulator (shape: [panel, slow, fast])
- **Status**: ✅ PRESERVES GRADIENT (no detach/numpy conversions)

### Boundary 3: Loss → Gradcheck
- **Location**: `dbex/physics/loss.py:154` → `torch.autograd.gradcheck`
- **Tensor**: Scalar loss tensor
- **Status**: ✅ PRESERVES GRADIENT (numerator path intact despite variance.detach())

---

## Key Module Boundaries

1. **Test Fixture → Production Code**:
   - File: `tests/dbex/test_gradients.py:204` (crystal) or `:383, :496` (detector/beam)
   - Interface: `simulate_forward_torch()` call
   - Gradient preservation: **DEPENDS ON PATH** (crystal: ✅, detector/beam: ❌)

2. **dbex → nanobrag_torch External Dependency**:
   - File: `dbex/refinement/helpers.py:198`
   - Interface: `Crystal(crystal_config, beam_config=beam_config, device=device, dtype=dtype)`
   - Gradient preservation: **UNKNOWN** (external code, hypothesis: may call `.item()` on cell parameters)

3. **Forward Simulation → Loss Computation**:
   - File: `dbex/physics/forward.py:251` → `dbex/physics/loss.py:70`
   - Interface: `compute_masked_mse_loss(bragg_torch, ...)`
   - Gradient preservation: ✅ (tensor returned from forward, variance detach is IRLS-intentional)

4. **Loss Computation → Autograd**:
   - File: `dbex/physics/loss.py:162` → `torch.autograd.gradcheck`
   - Interface: Scalar loss tensor return
   - Gradient preservation: ✅ (standard PyTorch backward path)

---

## Findings

### Critical Gradient Breaks (Confirmed)

1. **test_gradients.py:383** — Detector distance test
   - Pattern: `new_distance = float(distance_tensor.item())`
   - Impact: Severs autograd graph before dxtbx geometry construction
   - Classification: **TEST HARNESS BUG** (easy fix: use tensor-valued detector override mechanism)

2. **test_gradients.py:496** — Beam wavelength test
   - Pattern: `new_wavelength = float(wavelength_tensor.item())`
   - Impact: Severs autograd graph before dxtbx geometry construction
   - Classification: **TEST HARNESS BUG** (easy fix: use tensor-valued beam override mechanism)

### Suspected Gradient Break (External Dependency)

3. **nanobrag_torch.models.Crystal constructor** (called from helpers.py:198)
   - Hypothesis: May internally call `.item()` on `crystal_config.cell_a` (and other tensor-valued fields)
   - Evidence: Crystal tests (cell_a, cell_gamma) fail with same gradcheck signature despite using tensor-preserving override mechanism
   - Next Step: Phase A.3 gradient probe to empirically test if Crystal.__init__ breaks gradient

### Intentional Detach (Not a Bug)

4. **loss.py:147** — Variance denominator detach
   - Pattern: `variance = torch.clamp(prediction.detach() + sigma_readout**2, min=1e-12)`
   - Rationale: IRLS (Iteratively Reweighted Least Squares) — detached denominator prevents "attraction to zero"
   - Impact: **NO GRADIENT BREAK** because numerator `(prediction - target)**2` preserves gradient through division

---

## Next Steps (Phase A.2)

1. Grep audit: Search for `.item()`, `.detach()`, `.numpy()`, in-place ops, `.cpu()` in 4 key modules
2. Classify grep matches as SAFE (non-grad tensor) vs UNSAFE (breaks gradient)
3. Rank candidates by proximity to test entry point
4. Phase A.3 decision:
   - If detector/beam test fixes are sufficient: Proceed to Phase B.1 (implement tensor override for detector/beam)
   - If crystal tests still fail after harness fixes: Proceed to Phase A.3 (gradient probe to locate nanobrag_torch break)

---

## References

- `tests/dbex/test_gradients.py` — DB-AT-010 gradcheck test suite
- `dbex/physics/forward.py::simulate_forward_torch` — Forward simulation entry point
- `dbex/physics/loss.py::compute_masked_mse_loss` — Variance-weighted loss
- `dbex/refinement/helpers.py::create_unified_simulator` — Factory for nanobrag_torch objects
- `docs/spec-db-runtime.md` §Gradient Hygiene — Differentiability requirements
- `docs/findings.md::GRADIENT-001` — Tensor-valued override pattern

---

**Prepared by**: Ralph (Loop i=138)
**Phase**: ARCH-GRADIENT-FLOW-001 Phase A.1
**Deliverable**: Call graph trace with ≥5 call stack levels documented
