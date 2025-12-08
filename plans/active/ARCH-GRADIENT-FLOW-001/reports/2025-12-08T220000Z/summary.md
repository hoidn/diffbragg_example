# Turn Summary — Phase B.5 DBEX Gradient Audit

**Loop:** i=170
**Focus:** ARCH-GRADIENT-FLOW-001 Phase B.5 — DBEX-layer gradient audit
**Mode:** Evidence collection (no production changes)
**Status:** ROOT CAUSE LOCALIZED (Confidence: 0.95)

---

### Turn Summary

1. **Shipped:** Evidence-only audit identifying root cause of DB-AT-010 gradcheck failure in DBEX layer
2. **Root cause:** `forward.py:196` calls `create_crystal_config(crystal, experiment)` WITHOUT passing `crystal_overrides`, causing MOSFLM A* injection from base crystal. When `compute_cell_tensors()` runs with `mosflm_provided=True`, it uses MOSFLM vectors instead of cell parameters and overwrites `self.cell_a` at `crystal.py:872`, disconnecting the computational graph.
3. **Proposed fix:** Single-line change — add `crystal_overrides=crystal_overrides` parameter to `create_crystal_config` call at `forward.py:196`
4. **Next step:** Implement fix in Phase B.6, run DB-AT-010 gradcheck test to validate

---

### Key Findings

| Item | Value |
|------|-------|
| Error type | "Numerical gradient for function expected to be zero" (disconnected graph) |
| Break location | `crystal.py:872` — `self.cell_a = torch.norm(a_vec)` |
| Root cause | MOSFLM orientation path takes precedence over cell parameter path |
| Fix complexity | 1 line (low risk) |
| Confidence | 0.95 |

---

### Tensor Flow Summary

```
Test input tensor (requires_grad=True)
    ↓
forward.py: crystal_overrides={'cell_a': tensor}
    ↓
forward.py:196: create_crystal_config(crystal, experiment) ← NO crystal_overrides!
    ↓
config_factories.py:342-347: mosflm_a/b/c_star set from base crystal
    ↓
forward.py:220: crystal_config.cell_a = tensor (override applied)
    ↓
helpers.py:198: Crystal(crystal_config, ...)
    ↓
crystal.py:660-663: mosflm_provided = True (because mosflm_a_star is not None)
    ↓
crystal.py:815-877: MOSFLM path executes
    ↓
crystal.py:872: self.cell_a = torch.norm(a_vec) ← OVERWRITES tensor!
    ↓
Output: no dependency on input tensor → disconnected graph
```

---

### Exit Criteria Validation

| Criterion | Expected | Actual |
|-----------|----------|--------|
| B.5.1 complete | Gradcheck log captured | ✓ `gradcheck_verbose.log` |
| B.5.2 complete | Code audit of tensor flow | ✓ Traced through 6 files |
| B.5.3 complete | dbex_gradient_audit.md exists | ✓ Hypothesis + confidence documented |
| B.5.4 complete | summary.md exists | ✓ This file |
| No production changes | git status clean | ✓ Evidence-only loop |

---

### Artifacts

- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z/gradcheck_verbose.log`
- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z/dbex_gradient_audit.md`
- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z/summary.md`
