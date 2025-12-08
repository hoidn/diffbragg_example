# Turn Summary — Phase B.6 Implementation

**Loop:** i=171
**Focus:** ARCH-GRADIENT-FLOW-001 Phase B.6 — Implement crystal_overrides passthrough
**Mode:** Parity (gradient flow restoration)
**ActionType:** implementation_ready
**DecisionStatus:** patch_ready → **PARTIAL SUCCESS / BLOCKED**

---

### Turn Summary

1. **Shipped:** Single-line fix at `forward.py:196` — added `crystal_overrides=crystal_overrides` to `create_crystal_config` call
2. **Progress:** Fix eliminated "disconnected graph" error; gradient now flows through Crystal cell parameter path
3. **New blocker:** Jacobian mismatch discovered — analytical gradient ~7e7, numerical gradient ~4.7e10 (≈640× difference with sign flip)
4. **Root cause hypothesis:** Gradient magnitude error in `nanobrag_torch/models/crystal.py::compute_cell_tensors()` chain
5. **Next step:** Escalate to nanobrag_torch gradient audit (Phase B.7 or new initiative)

---

### Exit Criteria Status

| Criterion | Expected | Actual | Status |
|-----------|----------|--------|--------|
| B.6.1 complete | forward.py:196 edited | ✓ `crystal_overrides=crystal_overrides` added | PASS |
| B.6.2 complete | crystal_cell_a PASS | ✗ Jacobian mismatch | FAIL |
| B.6.3 complete | all crystal tests PASS | N/A (blocked by B.6.2) | BLOCKED |
| B.6.4 complete | 5/5 DB-AT-010 PASS | N/A (blocked by B.6.2) | BLOCKED |
| B.6.5 complete | summary.md exists | ✓ This file | PASS |

---

### Key Findings

| Item | Value |
|------|-------|
| Fix implemented | `forward.py:196` — pass `crystal_overrides` to factory |
| Previous error | "Numerical gradient expected to be zero" (disconnected graph) |
| New error | `GradcheckError: Jacobian mismatch` |
| Numerical gradient | `-4.684e+10` (varies per run) |
| Analytical gradient | `7.267e+07` (stable) |
| Magnitude ratio | ~640× |
| Sign relationship | **Opposite signs** (critical) |
| Input cell_a | 27.3758 Å |

---

### Analysis

**What the fix accomplished:**
- `create_crystal_config` now receives `crystal_overrides={'cell_a': tensor}` from `simulate_forward_torch`
- Factory logic at `config_factories.py:353-357` sets `mosflm_a_star=None` when `crystal_overrides` is provided (without MOSFLM keys)
- This causes `Crystal.compute_cell_tensors()` to take the cell parameter path (lines 682-716) instead of the MOSFLM path
- The computational graph IS now connected (proven by non-zero gradients)

**Why the test still fails:**
- Analytical gradient (backprop): ~7.3e7
- Numerical gradient (finite diff): ~4.7e10
- Ratio: ~640× with sign flip
- This indicates a bug in the gradient computation, not the graph connectivity

**Suspected location:**
The gradient flows through `Crystal.compute_cell_tensors()` which performs complex crystallographic calculations:
- Cell parameter → reciprocal lattice vectors (a*, b*, c*)
- Reciprocal vectors → real-space vectors (a, b, c)
- Volume calculations
- Cross products and rescaling

The large magnitude and sign discrepancy suggests either:
1. Missing derivative chain in the crystallographic formulas
2. Numerical precision issue in the gradient accumulation
3. A non-differentiable operation (clamp, abs) affecting gradient flow

---

### Tensor Flow (Updated)

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
forward.py:220: crystal_config.cell_a = tensor (redundant but harmless)
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

---

### If Blocked Protocol Results

1. ✓ Document new failure mode: Jacobian mismatch (not disconnected graph)
2. ✓ Re-run with -vvv --tb=long: Captured in `pytest_crystal_cell_a_verbose.log`
3. ✓ Check other create_crystal_config call sites: Only `forward.py:196` in test path
4. → Mark blocked and spawn architecture follow-up

---

### Artifacts

- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/pytest_crystal_cell_a.log`
- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/pytest_crystal_cell_a_verbose.log`
- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/summary.md`

---

### Recommendation

**Immediate action:** Commit the single-line fix (it IS an improvement)

**Next initiative:** Create ARCH-GRADIENT-MAGNITUDE-001 to investigate the gradient magnitude mismatch in `nanobrag_torch/models/crystal.py::compute_cell_tensors()`. This requires:
1. Instrumenting the gradient flow through the crystallographic formulas
2. Comparing analytical vs numerical derivatives at each stage
3. Identifying the specific operation causing the ~640× discrepancy

**Note:** This is outside the scope of a bugfix initiative. The gradient computation involves complex physics (reciprocal lattice geometry) that may require physics/crystallography expertise to debug correctly.
