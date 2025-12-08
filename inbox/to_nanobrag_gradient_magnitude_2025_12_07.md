# Escalation: Gradient Magnitude Mismatch in Crystal.compute_cell_tensors()

**From:** DBEX Team (Galph/Ralph)
**To:** nanobrag_torch maintainers
**Date:** 2025-12-07
**Priority:** High (blocks DB-AT-010 gradcheck suite)
**Related:** ARCH-GRADIENT-FLOW-001

## Summary

After implementing the single-line fix at `dbex/physics/forward.py:196` to pass `crystal_overrides` to `create_crystal_config`, the "disconnected autograd graph" error has been resolved. However, a **new blocker** has emerged: **gradient magnitude mismatch** (~640× with sign flip).

## Evidence

**Test:** `tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a`

**Results (from i=171 Ralph):**
- **Analytical gradient (backprop):** ~7.267e+07
- **Numerical gradient (finite diff):** ~-4.684e+10
- **Magnitude ratio:** ~640×
- **Sign relationship:** **Opposite signs** (critical)
- **Input cell_a:** 27.3758 Å

## Tensor Flow (verified)

```
Test input tensor (cell_a, requires_grad=True)
    ↓
forward.py: crystal_overrides={'cell_a': tensor}
    ↓
forward.py:196: create_crystal_config(..., crystal_overrides=crystal_overrides) [FIX APPLIED]
    ↓
config_factories.py:321-322: a = crystal_overrides['cell_a'] (tensor flows)
config_factories.py:353-357: mosflm_a_star = None [MOSFLM BYPASSED]
    ↓
helpers.py:198: Crystal(crystal_config, ...)
    ↓
crystal.py:69-71: self.cell_a = torch.as_tensor(config.cell_a, ...) [TENSOR PRESERVED]
    ↓
crystal.py:660-663: mosflm_provided = False (mosflm_a_star is None)
    ↓
crystal.py:682-716: Cell parameter path constructs a_star from cell params [GRADIENT PATH]
    ↓
crystal.py:878-910: Real-space vectors computed from a_star [GRADIENT CONTINUES]
    ↓
Simulator forward pass → loss computation
    ↓
Output: Gradient EXISTS but magnitude is ~640× off with sign flip
```

## Hypothesis

The gradient computation in `Crystal.compute_cell_tensors()` (lines 682-716 and 878-910) involves complex crystallographic calculations:
1. Cell parameter → reciprocal lattice vectors (a*, b*, c*)
2. Reciprocal vectors → real-space vectors (a, b, c)
3. Volume calculations
4. Cross products and rescaling

The large magnitude and sign discrepancy suggests either:
1. Missing derivative chain in the crystallographic formulas
2. Numerical precision issue in the gradient accumulation
3. A non-differentiable operation (clamp, abs, or conditional) affecting gradient flow

## What We Need

1. **Audit** of `nanobrag_torch/models/crystal.py::compute_cell_tensors()` for gradient correctness
2. **Instrumented gradcheck** at intermediate boundaries (cell params → a_star → real vectors)
3. **Fix** for the gradient magnitude/sign mismatch

## Artifacts

- Test logs: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/pytest_crystal_cell_a.log`
- Verbose output: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/pytest_crystal_cell_a_verbose.log`
- Analysis: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/summary.md`

## Impact

- DB-AT-010 gradcheck suite: 0/5 PASS (blocked)
- DBEX gradient-based refinement: blocked for crystal cell parameters
- Upstream fix required before DBEX can validate differentiable crystal optimization

## Reproducer

```bash
cd /home/ollie/Documents/diffbragg_example
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
pytest -vvv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --tb=long
```

---

**Note:** This escalation follows the Environment Freeze exception protocol. DBEX has implemented its half of the fix (graph connectivity). The remaining blocker is in nanobrag_torch's crystallographic gradient computation.
