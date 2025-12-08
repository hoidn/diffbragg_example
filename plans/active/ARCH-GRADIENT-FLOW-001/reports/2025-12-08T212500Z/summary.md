### Turn Summary
Processed upstream response confirming nanobrag_torch cell gradients work (6/6 PASS); identified two DBEX-side bugs breaking gradient flow.
Root cause: `busing_levy_B_torch()` uses `.item()` for cctbx (nanobrag_bridge.py:602-608), and A* extraction uses `.detach()` (stage_a.py:1183-1185).
Next: Ralph implements pure-PyTorch B-matrix and removes gradient-breaking `.detach()` calls.
Artifacts: plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T212500Z/ (upstream_response_analysis)

## Upstream Response Summary

**File:** `inbox/nanobrag_torch_cell_gradient_response_2025_12_08.md`

**Key Points:**
1. nanobrag_torch cell param gradcheck tests: **6/6 PASS**
2. Issue location: **DBEX integration layer** (NOT nanobrag_torch)
3. Upstream-provided debugging hypotheses:
   - H1: Double unit conversion (Å→m applied twice)
   - H2: Scalar extraction breaking graph (.item()/.detach())
   - H3: Fluence mismatch (1e28 expected)

## Root Cause Analysis (Galph Supervisor)

### Bug 1: `busing_levy_B_torch()` breaks gradient graph
**Location:** `dbex/nanobrag_bridge.py:602-608`
```python
a_val = float(a.item() if hasattr(a, 'item') else a)  # BREAKS GRADIENT
# ... same pattern for b, c, alpha, beta, gamma
uc = uctbx.unit_cell((a_val, ...))  # cctbx has no autograd support
```

**Problem:** Cell parameters are converted to Python floats via `.item()` before being passed to cctbx's `unit_cell()`. cctbx cannot compute gradients.

### Bug 2: A* extraction uses `.detach()`
**Location:** `dbex/refinement/stage_a.py:1183-1185`
```python
a_star = A_star_new[:, 0].detach().cpu().numpy()  # BREAKS GRADIENT
b_star = A_star_new[:, 1].detach().cpu().numpy()
c_star = A_star_new[:, 2].detach().cpu().numpy()
```

**Problem:** Even if B-matrix computation preserved gradients, A* vectors are immediately detached before being passed to crystal_overrides.

## Fix Strategy (Phase B.7)

1. **B.7.1:** Implement pure-PyTorch Busing-Levy B-matrix using explicit formulas (no cctbx)
2. **B.7.2:** Investigate MOSFLM a_star path vs direct cell parameter injection
3. **B.7.3:** Run gradcheck verification

## Upstream-Verified Working Pattern

```python
# From nanobrag_torch response - this pattern preserves gradients
cell_a = torch.tensor(100.0, dtype=torch.float64, requires_grad=True)
crystal_config = CrystalConfig(cell_a=cell_a, ...)  # torch.as_tensor() preserves requires_grad
```
