# Input — Loop i=209 (Ralph) — ARCH-GRADIENT-FLOW-001 Phase B.7

## Summary
Fix crystal cell gradient flow: Replace cctbx-dependent B-matrix computation with pure-PyTorch implementation and remove `.detach()` calls in A* vector extraction.

## Focus
ARCH-GRADIENT-FLOW-001 — Gradient Flow Restoration (DB-AT-010 Unblock)

## Branch
integration

## Mapped Tests
`pytest -v tests -k DB_AT_010 --smoke-detector-size=full` — DB-AT-010 gradcheck suite (5 tests, expect improvements after fix)

## Artifacts
`plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T212500Z/`

---

## Context

**UPSTREAM RESPONSE RECEIVED** (Loop i=208): nanobrag_torch maintainers confirmed their cell parameter gradient tests pass (6/6). The issue is in DBEX integration layer.

**Root Cause Identified (This Loop — Galph Supervisor Analysis):**

Two gradient-breaking patterns found:

### Bug 1: `busing_levy_B_torch()` uses `.item()` (dbex/nanobrag_bridge.py:602-608)
```python
# Lines 602-608 break gradient graph
a_val = float(a.item() if hasattr(a, 'item') else a)  # BREAKS GRADIENT
b_val = float(b.item() if hasattr(b, 'item') else b)
...
uc = uctbx.unit_cell((a_val, b_val, ...))  # cctbx has no autograd
```

This function extracts scalars to pass to cctbx, which cannot compute gradients.

### Bug 2: A* vectors `.detach()` (dbex/refinement/stage_a.py:1183-1185)
```python
# Lines 1183-1185 break gradient graph
a_star = A_star_new[:, 0].detach().cpu().numpy()  # BREAKS GRADIENT
b_star = A_star_new[:, 1].detach().cpu().numpy()
c_star = A_star_new[:, 2].detach().cpu().numpy()
```

After computing `A_star_new = U_current @ B_current`, the code immediately detaches.

**Upstream-Verified Pattern**: nanobrag_torch expects `CrystalConfig` to receive torch.Tensor values for cell parameters. The `Crystal` model uses `torch.as_tensor()` which preserves `requires_grad`.

---

## Do Now

### B.7.1 — Implement pure-PyTorch Busing-Levy B-matrix

**Target**: `dbex/nanobrag_bridge.py::busing_levy_B_torch` (lines 558-622)

Replace cctbx dependency with pure PyTorch. The Busing-Levy fractionalization matrix formula is:

```
Given cell (a, b, c, α, β, γ):

cos_alpha = cos(α), cos_beta = cos(β), cos_gamma = cos(γ)
sin_gamma = sin(γ)

Volume_factor = sqrt(1 - cos²α - cos²β - cos²γ + 2·cos_α·cos_β·cos_γ)

Fractionalization matrix (upper triangular):
F = [[1/a,  -cos_γ/(a·sin_γ),  (cos_α·cos_γ - cos_β)/(a·Volume_factor·sin_γ)],
     [0,    1/(b·sin_γ),       (cos_β·cos_γ - cos_α)/(b·Volume_factor·sin_γ)],
     [0,    0,                  sin_γ/(c·Volume_factor)]]

B = F.T  (dxtbx convention: lower triangular)
```

**Implementation requirements:**
- Accept `torch.Tensor` inputs directly (no `.item()` conversion)
- Use `torch.deg2rad()` for angle conversion
- Use only PyTorch ops (`torch.cos`, `torch.sin`, `torch.sqrt`, tensor indexing)
- Return gradient-preserving `torch.Tensor`
- Backward compatibility: Keep function signature unchanged

### B.7.2 — Remove `.detach()` from A* extraction

**Target**: `dbex/refinement/stage_a.py:1183-1185`

The `crystal_overrides` dict accepts tensor values. Change:
```python
# BEFORE (gradient-breaking)
a_star = A_star_new[:, 0].detach().cpu().numpy()

# AFTER (gradient-preserving)
# Option A: Keep as tensors if crystal_config accepts them
a_star = A_star_new[:, 0]  # torch.Tensor with gradient
# Option B: If MOSFLM path doesn't use gradients, document why detach is safe
```

**Investigation needed:** Check if `crystal_overrides['mosflm_a_star']` flows to `CrystalConfig` and whether nanobrag_torch's Crystal model can accept tensor-valued MOSFLM vectors.

**Alternative approach (if MOSFLM doesn't support gradients):**
Consider using `crystal_overrides` dict with cell parameters directly (not MOSFLM a_star vectors). The upstream response shows `CrystalConfig(cell_a=tensor, ...)` works.

### B.7.3 — Run gradcheck verification

After fixes, run:
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
    pytest -v tests -k DB_AT_010 --smoke-detector-size=full 2>&1 | \
    tee plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T212500Z/gradcheck_post_fix.log
```

Expected: Improvement in cell parameter gradcheck tests. Full 5/5 PASS may require additional work.

---

## How-To Map

### Verify cctbx formula equivalence
```bash
# Test that pure-PyTorch B matches cctbx B for same inputs
python -c "
import torch
from cctbx import uctbx
import numpy as np

# Test cell
a, b, c = 100.0, 100.0, 100.0
alpha, beta, gamma = 90.0, 90.0, 90.0

# cctbx reference
uc = uctbx.unit_cell((a, b, c, alpha, beta, gamma))
B_cctbx = np.array(uc.fractionalization_matrix()).reshape(3,3).T
print('cctbx B:')
print(B_cctbx)

# Your pure-PyTorch implementation should match
"
```

### Check gradient flow after fix
```python
import torch
# After implementing pure-torch B-matrix:
a = torch.tensor(100.0, dtype=torch.float64, requires_grad=True)
# ... (call your new implementation)
B = busing_levy_B_torch(a, b, c, alpha, beta, gamma)
loss = B.sum()
loss.backward()
print(f"a.grad = {a.grad}")  # Should be non-zero
```

---

## Pitfalls To Avoid

1. **DO NOT** use `.item()`, `.numpy()`, or `.detach()` on gradient-tracked tensors in the forward path
2. **DO NOT** use cctbx in the gradient path — it doesn't support autograd
3. **Environment Freeze:** No package installs
4. **Test with float64:** Gradcheck requires double precision for numerical stability
5. **Preserve backward compatibility:** Keep function signatures unchanged
6. **Angle units:** B-matrix formula uses radians internally; convert degrees to radians

---

## If Blocked

If MOSFLM a_star vector path fundamentally requires detaching (nanobrag_torch doesn't support tensor-valued MOSFLM vectors):

1. Document in `docs/findings.md::GRADIENT-003` why cell gradients require direct cell parameter injection (not MOSFLM path)
2. Consider alternative gradient path via `crystal_overrides = {'cell_a': tensor, 'cell_b': tensor, ...}` per upstream's verified pattern
3. Update ARCH-GRADIENT-FLOW-001 implementation.md with findings

---

## Findings Applied

- **GRADIENT-001** (Gradient test patterns): Tests must inject differentiable parameters via `crystal_overrides` dict to preserve autograd graph.
  - Adherence: B.7.2 ensures A* vectors preserve gradient flow.

- **GRADIENT-002** (Current finding): Graph connectivity exists but magnitude mismatch 1000-76000×.
  - Adherence: B.7.1 addresses potential unit conversion issues by using pure-PyTorch implementation.

- **RUNTIME-001** (Runtime execution guardrails): DB-AT-010 requires `NANOBRAGG_DISABLE_COMPILE=1`.
  - Adherence: B.7.3 uses canonical flags.

---

## Pointers

- Upstream response: `inbox/nanobrag_torch_cell_gradient_response_2025_12_08.md`
- Bug location 1: `dbex/nanobrag_bridge.py:602-608` (`.item()` calls)
- Bug location 2: `dbex/refinement/stage_a.py:1183-1185` (`.detach()` calls)
- Implementation plan: `plans/active/ARCH-GRADIENT-FLOW-001/implementation.md`
- Exit criteria: Phase B.2 — DB-AT-010 gradcheck suite 5/5 PASS

---

## Next Up (if B.7 completes early)

1. B.7.4 — Add enforcement test `tests/architecture/test_gradient_contracts.py::test_busing_levy_preserves_gradients`
2. B.7.5 — Update `docs/findings.md::GRADIENT-002` with fix details
