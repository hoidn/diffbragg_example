# Cell Parameterization Design

## Purpose
Specify the incremental cell parameterization (Δcell → B) for TORCH-GEOMETRY-UB-REALIGN-001, ensuring compliance with spec-db-core.md and dxtbx B-matrix conventions.

---

## §1. Baseline Cell State

### Extraction from dxtbx

```python
from dxtbx.model import ExperimentList

expt = ExperimentList.from_file("refGeom.expt")[0]
crystal = expt.crystal

# Baseline cell parameters (Angstroms, degrees)
a₀, b₀, c₀, α₀, β₀, γ₀ = crystal.get_unit_cell().parameters()

# Baseline B-matrix (reciprocal metric tensor)
B₀ = np.array(crystal.get_B()).reshape(3, 3)
```

**Authority:**
> "For any mapping-aligned refinement, the crystal state provided by dxtbx/DIALS SHALL be treated as authoritative: `B₀ = crystal.get_B()` (reciprocal metric tensor)." — spec-db-core.md:53

---

## §2. Incremental Parameterization

### Trainable Parameters (6-DOF)

1. **Log-length deltas** (3-DOF, unbounded):
   - `δlog_a`, `δlog_b`, `δlog_c` ∈ ℝ

2. **Angle deltas** (3-DOF, unbounded):
   - `Δα`, `Δβ`, `Δγ` ∈ ℝ (degrees)

**Rationale:**
- Spec says "unit cell logs/angles" (spec-db-workflow.md:36) — normative.
- Logs ensure `a, b, c > 0` without explicit constraints or bounded mappings (sigmoid/tanh).
- Unbounded angles: trust optimizer to stay in valid range `(0°, 180°)`. Physical invalid angles will cause B-matrix derivation to fail (natural guard).

**Alternative Considered:**
- Bounded angle deltas via `Δα_raw → tanh(Δα_raw) * 10°` (matching nanobrag_torch ExperimentModel).
- **Decision:** Use unbounded deltas for simplicity; defer bounded mapping to Phase B if refinement produces unphysical angles.

### Perturbed Cell Parameters

```python
a(params) = a₀ * exp(δlog_a)
b(params) = b₀ * exp(δlog_b)
c(params) = c₀ * exp(δlog_c)

α(params) = α₀ + Δα  # degrees
β(params) = β₀ + Δβ
γ(params) = γ₀ + Δγ
```

**Zero-Point Condition:**
At initialization, set all deltas to zero:
```python
δlog_a = δlog_b = δlog_c = 0.0
Δα = Δβ = Δγ = 0.0
```

Then:
```python
a(0) = a₀ * exp(0) = a₀
b(0) = b₀ * exp(0) = b₀
c(0) = c₀ * exp(0) = c₀
α(0) = α₀ + 0 = α₀
β(0) = β₀ + 0 = β₀
γ(0) = γ₀ + 0 = γ₀
```

Therefore: **`cell(0) = cell₀`** ✓

---

## §3. B-Matrix Derivation (Busing-Levy Convention)

### dxtbx B-Matrix Convention

dxtbx uses the **Busing-Levy** reciprocal metric tensor convention (standard crystallography):

> "`crystal.get_B()` → reciprocal metric" — docs/dxtbx_api.md:40

The B-matrix converts fractional coordinates `h` to reciprocal space vectors `q`:
```
q = B @ h
```

### Busing-Levy Formula (Standard Crystallography)

Reference: Busing & Levy (1967), Acta Cryst. 22, 457-464.

**Reciprocal lattice parameters:**
```python
import numpy as np

def compute_reciprocal_cell(a, b, c, α_deg, β_deg, γ_deg):
    """
    Compute reciprocal cell parameters from direct cell.

    Returns: (a_star, b_star, c_star, α_star_deg, β_star_deg, γ_star_deg)
    """
    α = np.deg2rad(α_deg)
    β = np.deg2rad(β_deg)
    γ = np.deg2rad(γ_deg)

    # Volume of unit cell
    V = a * b * c * np.sqrt(
        1 - np.cos(α)**2 - np.cos(β)**2 - np.cos(γ)**2
        + 2 * np.cos(α) * np.cos(β) * np.cos(γ)
    )

    # Reciprocal lengths (Angstroms^-1)
    a_star = (b * c * np.sin(α)) / V
    b_star = (a * c * np.sin(β)) / V
    c_star = (a * b * np.sin(γ)) / V

    # Reciprocal angles (radians)
    cos_α_star = (np.cos(β) * np.cos(γ) - np.cos(α)) / (np.sin(β) * np.sin(γ))
    cos_β_star = (np.cos(α) * np.cos(γ) - np.cos(β)) / (np.sin(α) * np.sin(γ))
    cos_γ_star = (np.cos(α) * np.cos(β) - np.cos(γ)) / (np.sin(α) * np.sin(β))

    α_star = np.rad2deg(np.arccos(cos_α_star))
    β_star = np.rad2deg(np.arccos(cos_β_star))
    γ_star = np.rad2deg(np.arccos(cos_γ_star))

    return a_star, b_star, c_star, α_star, β_star, γ_star
```

**B-matrix (Upper Triangular):**

The Busing-Levy B-matrix is upper-triangular:

```python
def busing_levy_B(a, b, c, α_deg, β_deg, γ_deg):
    """
    Compute Busing-Levy B-matrix (reciprocal metric tensor).

    Returns: B (3x3 upper-triangular matrix, Angstroms^-1)
    """
    α = np.deg2rad(α_deg)
    β = np.deg2rad(β_deg)
    γ = np.deg2rad(γ_deg)

    # Compute reciprocal cell parameters
    a_star, b_star, c_star, α_star_deg, β_star_deg, γ_star_deg = \
        compute_reciprocal_cell(a, b, c, α_deg, β_deg, γ_deg)

    β_star = np.deg2rad(β_star_deg)
    γ_star = np.deg2rad(γ_star_deg)

    # Busing-Levy B-matrix (upper triangular)
    B = np.array([
        [a_star * np.sin(γ_star),  b_star * np.sin(α_star) * np.cos(γ_star),  c_star * np.cos(β_star)],
        [0,                        b_star * np.sin(α_star) * np.sin(γ_star),  -c_star * np.sin(β_star) * np.cos(α)],
        [0,                        0,                                          c_star * np.sin(β_star) * np.sin(α) / np.sin(α_star)]
    ])

    return B
```

**Note:** The exact formula may vary by convention (column vs row vectors, sign conventions). The **critical requirement** is:

> **At zero deltas, `B(0)` MUST match `B₀` from dxtbx exactly.**

### Validation Strategy

**Phase B validation:**
1. Extract `B₀ = crystal.get_B()` from dxtbx.
2. Extract `cell₀ = crystal.get_unit_cell().parameters()`.
3. Compute `B_derived = busing_levy_B(*cell₀)`.
4. Assert: `np.linalg.norm(B_derived - B₀) < 1e-12`.

**If mismatch occurs:**
- Extract dxtbx B-matrix computation source (cctbx.uctbx.unit_cell.fractionalization_matrix).
- Match formula exactly.
- **Fallback:** Use `cctbx.uctbx.unit_cell(params).fractionalization_matrix()` directly in Python, re-implement in PyTorch.

---

## §4. PyTorch Implementation

### Differentiable B-Matrix Derivation

```python
import torch

def busing_levy_B_torch(a, b, c, α_deg, β_deg, γ_deg, device=None, dtype=torch.float32):
    """
    Compute Busing-Levy B-matrix in PyTorch (differentiable).

    Args:
        a, b, c: Unit cell lengths (Angstroms), torch.Tensor or float.
        α_deg, β_deg, γ_deg: Unit cell angles (degrees), torch.Tensor or float.
        device, dtype: Target device/dtype.

    Returns:
        B: (3, 3) upper-triangular B-matrix, torch.Tensor.
    """
    # Convert to tensors if needed
    a = torch.as_tensor(a, device=device, dtype=dtype)
    b = torch.as_tensor(b, device=device, dtype=dtype)
    c = torch.as_tensor(c, device=device, dtype=dtype)
    α = torch.deg2rad(torch.as_tensor(α_deg, device=device, dtype=dtype))
    β = torch.deg2rad(torch.as_tensor(β_deg, device=device, dtype=dtype))
    γ = torch.deg2rad(torch.as_tensor(γ_deg, device=device, dtype=dtype))

    # Volume (differentiable)
    cos_α, cos_β, cos_γ = torch.cos(α), torch.cos(β), torch.cos(γ)
    sin_α, sin_β, sin_γ = torch.sin(α), torch.sin(β), torch.sin(γ)

    V = a * b * c * torch.sqrt(
        1 - cos_α**2 - cos_β**2 - cos_γ**2
        + 2 * cos_α * cos_β * cos_γ
    )

    # Reciprocal lengths
    a_star = (b * c * sin_α) / V
    b_star = (a * c * sin_β) / V
    c_star = (a * b * sin_γ) / V

    # Reciprocal angles
    cos_α_star = (cos_β * cos_γ - cos_α) / (sin_β * sin_γ)
    cos_β_star = (cos_α * cos_γ - cos_β) / (sin_α * sin_γ)
    cos_γ_star = (cos_α * cos_β - cos_γ) / (sin_α * sin_β)

    sin_α_star = torch.sqrt(1 - cos_α_star**2)
    sin_β_star = torch.sqrt(1 - cos_β_star**2)
    sin_γ_star = torch.sqrt(1 - cos_γ_star**2)

    # Busing-Levy B-matrix (upper triangular)
    B = torch.zeros(3, 3, device=device, dtype=dtype)
    B[0, 0] = a_star * sin_γ_star
    B[0, 1] = b_star * sin_α_star * cos_γ_star
    B[0, 2] = c_star * cos_β_star
    B[1, 1] = b_star * sin_α_star * sin_γ_star
    B[1, 2] = -c_star * sin_β_star * cos_α
    B[2, 2] = c_star * sin_β_star * sin_α / sin_α_star

    return B
```

**Gradient Flow Validation:**
```python
# Test differentiability
a = torch.tensor(79.0, requires_grad=True)
b = torch.tensor(79.0, requires_grad=True)
c = torch.tensor(38.0, requires_grad=True)
α = torch.tensor(90.0, requires_grad=True)
β = torch.tensor(90.0, requires_grad=True)
γ = torch.tensor(90.0, requires_grad=True)

B = busing_levy_B_torch(a, b, c, α, β, γ)
loss = B.sum()
loss.backward()

assert a.grad is not None, "B-matrix must be differentiable w.r.t. cell parameters"
```

---

## §5. Integration with Incremental Parameterization

### Helper Function for Stage A Closure

```python
def derive_B_from_cell_deltas(
    δlog_a, δlog_b, δlog_c,
    Δα_deg, Δβ_deg, Δγ_deg,
    cell_baseline,  # (a₀, b₀, c₀, α₀, β₀, γ₀)
    device=None,
    dtype=torch.float32
):
    """
    Derive B-matrix from incremental cell parameterization.

    Args:
        δlog_a, δlog_b, δlog_c: Log-length deltas (unbounded).
        Δα_deg, Δβ_deg, Δγ_deg: Angle deltas (degrees, unbounded).
        cell_baseline: Tuple (a₀, b₀, c₀, α₀, β₀, γ₀).
        device, dtype: Target device/dtype.

    Returns:
        B: (3, 3) B-matrix, torch.Tensor.
    """
    a₀, b₀, c₀, α₀, β₀, γ₀ = cell_baseline

    # Perturbed cell parameters
    a = a₀ * torch.exp(δlog_a)
    b = b₀ * torch.exp(δlog_b)
    c = c₀ * torch.exp(δlog_c)
    α = α₀ + Δα_deg
    β = β₀ + Δβ_deg
    γ = γ₀ + Δγ_deg

    # Compute B-matrix
    B = busing_levy_B_torch(a, b, c, α, β, γ, device=device, dtype=dtype)

    return B
```

**Zero-Point Test:**
```python
# Extract baseline from dxtbx
cell_baseline = (79.1, 79.1, 38.4, 90.0, 90.0, 90.0)  # example
B₀ = crystal.get_B()

# Zero deltas
δlog_a = torch.tensor(0.0)
δlog_b = torch.tensor(0.0)
δlog_c = torch.tensor(0.0)
Δα = torch.tensor(0.0)
Δβ = torch.tensor(0.0)
Δγ = torch.tensor(0.0)

# Derive B(0)
B_params = derive_B_from_cell_deltas(δlog_a, δlog_b, δlog_c, Δα, Δβ, Δγ, cell_baseline)

# Validate zero-point invariant
assert torch.allclose(B_params, torch.tensor(B₀), atol=1e-12), "B(0) must equal B₀"
```

---

## §6. Constraints and Guards

### Physical Constraints

**Valid ranges:**
- Lengths: `a, b, c > 0` (enforced by log parameterization).
- Angles: `0° < α, β, γ < 180°` for physical crystals.

**Guard strategy:**
- **Unbounded deltas:** Trust optimizer to stay in valid range.
- **Natural guard:** If angles become unphysical (e.g., α > 180°), trigonometric functions will produce invalid values (NaN or extreme numbers), causing loss to explode.
- **Explicit guard (optional):** Add penalty term to loss if angles exit safe range:
  ```python
  penalty = 0.0
  for angle in [α, β, γ]:
      if angle < 5.0 or angle > 175.0:  # degrees
          penalty += 1e6 * (angle - 90.0)**2  # penalize deviation from 90°
  ```

**Defer to Phase B:** Implement explicit guards only if refinement produces unphysical angles in practice.

### Numerical Stability

**Division by zero:**
- B-matrix derivation involves `sin(α)`, `sin(β)`, `sin(γ)` in denominators.
- If angles → 0° or 180°, `sin(angle) → 0`, causing division by zero.
- **Mitigation:** Physical constraint (0° < angle < 180°) ensures `sin(angle) > 0`.

**Volume calculation:**
- Volume `V` involves square root of determinant term.
- If determinant becomes negative (unphysical cell), `sqrt` produces NaN.
- **Guard:** Check `1 - cos²α - cos²β - cos²γ + 2cosαcosβcosγ > 0`.

**Torch implementation note:**
- Use `torch.clamp(determinant_term, min=1e-12)` before `sqrt` to avoid NaN gradients.

---

## §7. Alignment with nanobrag_torch API

From `docs/nanobrag_api.md:136-138`:

> "CrystalStageAParams:
> - `δ_log_a/δ_log_b/δ_log_c`: log cell‑length deltas.
> - `Δα_raw/Δβ_raw/Δγ_raw`: bounded angle deltas via `tanh` (±10°)."

**Our design vs nanobrag_torch API:**

| Parameter | Our Design | nanobrag_torch API | Compatibility |
|-----------|------------|--------------------|---------------|
| Length deltas | `δlog_a` (unbounded) | `δ_log_a` (unbounded) | ✓ Direct match |
| Angle deltas | `Δα` (unbounded) | `Δα_raw → tanh(...) * 10°` (bounded) | ⚠️ Minor difference |

**Compatibility strategy:**
- **Option 1 (current design):** Use unbounded `Δα` directly; trust optimizer.
- **Option 2 (bounded):** Add `tanh` mapping to match nanobrag_torch API:
  ```python
  Δα = torch.tanh(Δα_raw) * 10.0  # degrees
  ```

**Recommendation:**
- Start with **Option 1 (unbounded)** for simplicity.
- If refinement produces large angle deltas (>10°) or unphysical values, switch to **Option 2 (bounded)** in Phase B.

---

## §8. Testing Plan (DB-AT-026 Subset)

### Unit Test: Zero-Point B-Matrix Validation

**Test:** `tests/dbex/test_ub_parameterization_roundtrip.py::test_cell_zero_point`

```python
def test_cell_zero_point():
    """Validate B(0) = B₀ for zero cell deltas."""
    import torch
    from dxtbx.model import ExperimentList

    # Load baseline
    expt = ExperimentList.from_file("refGeom.expt")[0]
    cell_baseline = expt.crystal.get_unit_cell().parameters()
    B₀ = np.array(expt.crystal.get_B()).reshape(3, 3)

    # Zero deltas
    δlog_a = torch.tensor(0.0, dtype=torch.float64)
    δlog_b = torch.tensor(0.0, dtype=torch.float64)
    δlog_c = torch.tensor(0.0, dtype=torch.float64)
    Δα = torch.tensor(0.0, dtype=torch.float64)
    Δβ = torch.tensor(0.0, dtype=torch.float64)
    Δγ = torch.tensor(0.0, dtype=torch.float64)

    # Derive B(0)
    B_params = derive_B_from_cell_deltas(
        δlog_a, δlog_b, δlog_c, Δα, Δβ, Δγ,
        cell_baseline, dtype=torch.float64
    )

    # Validate
    B_params_np = B_params.detach().cpu().numpy()
    error = np.linalg.norm(B_params_np - B₀)

    assert error < 1e-12, f"B(0) must equal B₀: error={error:.3e}"
```

**Expected:** PASS with error < 1e-12.

---

## §9. References

- `docs/spec-db-core.md:60` — Cell parameterization via Busing-Levy metric tensor (normative)
- `docs/spec-db-workflow.md:36` — Trainable "unit cell logs/angles" (normative)
- `docs/dxtbx_api.md:35-41` — Crystal unit cell and B-matrix extraction
- `docs/config_crosswalk.md:53-63` — Cell parameter mapping conventions
- Busing & Levy (1967), Acta Cryst. 22, 457-464 — B-matrix formula

---

**Summary:**
- Lengths: log-perturbations `a = a₀ * exp(δlog_a)` (ensures positivity).
- Angles: direct deltas `α = α₀ + Δα` (unbounded, trust optimizer).
- B-matrix: Busing-Levy formula (differentiable PyTorch implementation).
- Zero-point: `B(0) = B₀` validated via unit test.
- Alignment: Compatible with nanobrag_torch API (minor difference in angle bounding, easily adjusted).

**Next:** Implement `busing_levy_B_torch` and `derive_B_from_cell_deltas` in Phase B.
