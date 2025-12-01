# Physics Loss Functions IDL Contract

**Module**: `dbex.physics.loss`
**Status**: Active (ARCH-REFINE-001 Phase C.3, D.1)
**Normative References**:
- `docs/spec-db-core.md` §§57-68 (variance model: V = max(I_model + sigma_rdout^2, sigma_floor^2))
- `docs/spec-db-workflow.md` §§30-45 (forward helper + telemetry expectations)
- `docs/config_crosswalk.md` Arrays and loss mapping
- `docs/findings.md` PHYSICS-LOSS-001, PHYSICS-LOSS-003, SCALE-002

---

## Overview

`dbex.physics.loss` provides variance-weighted chi-squared and masked MSE loss functions for diffraction refinement. The module implements the normative variance model per spec-db-core.md §§57-68 with IRLS (detached denominator) to prevent "attraction to zero" during gradient-based optimization.

### Key Principles

1. **Variance Model**: `V = max(I_model.detach() + sigma_readout^2, sigma_floor^2)` per spec-db-core.md:57-68
2. **IRLS Semantics**: Denominator (variance) is detached to implement Iteratively Reweighted Least Squares (prevents division-by-zero gradient pathology)
3. **Device/Dtype Agnostic**: All functions work on CPU/CUDA with float32/float64
4. **Gradient Preservation**: No `.numpy()` or `.item()` calls that break autograd chains
5. **Shared Validation**: `_compute_variance_weighted_loss` provides reusable variance/clamp logic for both production and test paths

---

## API: _compute_variance_weighted_loss (Internal)

### Signature

```python
def _compute_variance_weighted_loss(
    bragg_tensor: torch.Tensor,
    target_tensor: torch.Tensor,
    loss_mask: torch.Tensor,
    sigma_tensor: torch.Tensor,
    sigma_floor_sq_tensor: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor, int, int]
```

### Inputs

| Parameter | Type | Shape | Contract |
|-----------|------|-------|----------|
| `bragg_tensor` | torch.Tensor | [panel, slow, fast] | Predicted Bragg intensities |
| `target_tensor` | torch.Tensor | [panel, slow, fast] | Target intensities (same shape as bragg_tensor) |
| `loss_mask` | torch.Tensor | [panel, slow, fast] | Boolean or numeric mask (1=trusted, 0=excluded) |
| `sigma_tensor` | torch.Tensor | [panel, slow, fast] or scalar | Readout noise (σ_rdout) in target units |
| `sigma_floor_sq_tensor` | torch.Tensor | [panel, slow, fast] or scalar | Variance floor (σ_floor²) |

### Outputs

| Output | Type | Content |
|--------|------|---------|
| `chi_squared_sum` | torch.Tensor (scalar) | Variance-weighted chi-squared: `Σ((I_model - I_obs)² / V)` over masked pixels |
| `masked_mse_value` | torch.Tensor (scalar) | Masked MSE: `Σ((I_model - I_obs)²) / N_masked` |
| `masked_pixels` | int | Count of trusted pixels (`loss_mask == True`) |
| `clamped_pixels` | int | Count of pixels where variance was clamped to floor (`V_raw < σ_floor²`) |

### Variance Computation

```python
variance_raw = bragg_tensor.detach() + sigma_tensor ** 2
variance = torch.maximum(variance_raw, sigma_floor_sq_tensor)
```

- **Detached denominator**: `bragg_tensor.detach()` implements IRLS, preventing pathological gradients
- **Max clamp**: Ensures variance ≥ σ_floor² per spec-db-core.md:86-90

---

## API: compute_masked_mse_loss (Public, TEST-ONLY)

### Signature

```python
def compute_masked_mse_loss(
    prediction: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    sigma_readout: Optional[torch.Tensor] = None
) -> torch.Tensor
```

### Inputs

| Parameter | Type | Shape | Required | Contract |
|-----------|------|-------|----------|----------|
| `prediction` | torch.Tensor | [panel, slow, fast] | Yes | Predicted Bragg intensities with autograd graph preserved |
| `target` | torch.Tensor | [panel, slow, fast] | Yes | Target intensities (same shape as prediction) |
| `mask` | torch.Tensor | [panel, slow, fast] | Yes | Loss mask (boolean or numeric 0/1) |
| `sigma_readout` | Optional[torch.Tensor] | [panel, slow, fast] or scalar | No | Readout noise (σ_rdout) in target units. When None, falls back to masked MSE (legacy). When provided, computes variance-weighted chi-squared per spec-db-core.md. |

### Outputs

| Output | Type | Content |
|--------|------|---------|
| `loss` | torch.Tensor (scalar) | Variance-weighted chi-squared when `sigma_readout` provided; masked MSE when `sigma_readout=None` |

### Validation Rules

1. `prediction`, `target`, and `mask` must have identical shapes
2. `mask` must have at least one valid pixel (sum > 0)
3. If `sigma_readout` provided, must be broadcastable to prediction shape
4. No NaN or Inf values allowed in any input tensor

### Exceptions

- `ValueError`: If shapes don't match, mask has no valid pixels, or inputs contain NaN/Inf

---

## Usage Patterns

### Pattern 1: DB-AT-010 gradcheck with variance-weighted loss

```python
from dbex.physics.loss import compute_masked_mse_loss
from dbex.physics.forward import simulate_forward_torch
import torch

# Gradcheck requires float64 and sigma_readout
bragg_torch = simulate_forward_torch(..., dtype=torch.float64)
target = inputs.target.to(torch.float64)
mask = inputs.loss_mask.bool()
sigma_readout = torch.tensor([1.0], dtype=torch.float64)

loss = compute_masked_mse_loss(bragg_torch, target, mask, sigma_readout)

# Gradcheck validation
torch.autograd.gradcheck(
    lambda x: compute_masked_mse_loss(
        simulate_forward_torch(..., crystal_overrides={"cell_a": x}),
        target, mask, sigma_readout
    ),
    cell_a_tensor,
    atol=1e-5, rtol=1e-3
)
```

### Pattern 2: Production Stage A LBFGS closure (internal helper)

```python
# Stage A uses _compute_variance_weighted_loss directly
chi_squared_sum, masked_mse, n_masked, n_clamped = _compute_variance_weighted_loss(
    bragg_tensor=bragg_torch,
    target_tensor=inputs.target,
    loss_mask=inputs.loss_mask,
    sigma_tensor=sigma_readout_tensor,
    sigma_floor_sq_tensor=sigma_floor_sq_tensor,
)
# Minimize chi_squared_sum in LBFGS
```

### Pattern 3: Forward-only MSE (no variance weighting)

```python
# Legacy masked MSE (no sigma_readout)
mse_loss = compute_masked_mse_loss(
    prediction=bragg_torch,
    target=target,
    mask=loss_mask,
    sigma_readout=None,  # Falls back to MSE
)
```

---

## Dependencies

### Direct Imports
- `torch` (autograd, tensor ops)
- `typing.Optional, typing.Tuple` (type hints)

### Transitive Dependencies
- **External data**: None (pure tensor computation)
- **Spec alignment**: Variance model per spec-db-core.md:57-68, loss semantics per spec-db-workflow.md:30-45

---

## Validation & Testing

### Primary Selectors
- `pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck` (DB-AT-010 gradcheck with `compute_masked_mse_loss`)
- `pytest -vv tests/dbex/test_physics_loss_current.py` (unit tests for variance model, IRLS, clamp counts)
- `pytest -vv tests/dbex/test_torch_refine_smoke.py` (Stage A/B/C integration with `_compute_variance_weighted_loss`)

### Validation Rules
1. Variance must satisfy `V = max(I_model.detach() + σ_rdout², σ_floor²)`
2. Chi-squared sum must equal `Σ((I_model - I_obs)² / V)` over masked pixels
3. Clamped pixel count must match pixels where `I_model.detach() + σ_rdout² < σ_floor²`
4. Gradient flow must be preserved (no `.item()` or `.numpy()` on autograd-enabled tensors)
5. MSE fallback (when `sigma_readout=None`) must compute `Σ((I_model - I_obs)²) / N_masked`

---

## Maintenance Notes

- **IRLS semantics**: The `.detach()` on `bragg_tensor` in variance computation is intentional (IRLS); do not remove
- **Variance model**: Any changes to the variance formula must update spec-db-core.md:57-68 first
- **Shared validation**: If adding new loss variants, reuse `_compute_variance_weighted_loss` logic for consistency
- **Test-only scope**: `compute_masked_mse_loss` is for DB-AT-010 gradcheck; production LBFGS closures call `_compute_variance_weighted_loss` directly
- **Gradient preservation**: Never add `.item()`, `.numpy()`, or `.detach()` calls on prediction/target/mask tensors

---

## Change Log

- **2025-12-01 (Phase D.1)**: IDL contract published; docstrings updated to reference this file
- **2025-12-01 (Phase C.3)**: Relocated `compute_masked_mse_loss` from `dbex.nanobrag_bridge` (lines 2231-2358) to `dbex.physics.loss`; extended module with spec-db-core.md §57-68 variance model (IRLS detached denominator); reused shared validation/clamp logic from `_compute_variance_weighted_loss`; added TEST-ONLY warning in docstring
