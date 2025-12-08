# Mosaic Hypothesis Verification Report

**Phase B.9 — ARCH-GRADIENT-FLOW-001**
**Date:** 2025-12-08T234500Z
**Status:** HYPOTHESIS CONFIRMED

---

## Summary

The hypothesis that the gradient magnitude mismatch is caused by the mosaic code path in nanobrag_torch has been **CONFIRMED**.

### Test Results

| Test | Experiment | Mosaic Path | Result | Jacobian Ratio |
|------|------------|-------------|--------|----------------|
| `test_db_at_010_gradcheck_cell_a_no_mosaic` | `None` | Bypassed | **PASSED** | 1.00× |
| `test_db_at_010_gradcheck_crystal_cell_a` | `experiment` | Active | **FAILED** | 1017× |

### Evidence

**Passing test (no-mosaic):**
```json
{
  "parameter": "crystal_cell_a_no_mosaic",
  "base_value": 27.3758389202232,
  "gradcheck_passed": true,
  "workaround": "experiment=None to bypass mosaic extraction",
  "eps": 1e-06,
  "atol": 1e-05,
  "rtol": 0.05,
  "device": "cpu",
  "dtype": "torch.float64"
}
```

**Failing test (with mosaic):**
```
GradcheckError: Jacobian mismatch for output 0 with respect to input 0,
numerical:tensor([[7.0588e+10]], dtype=torch.float64)
analytical:tensor([[69322120.5682]], dtype=torch.float64)
```

Ratio: 7.0588e+10 / 6.932e+07 = **1017×** mismatch

---

## Root Cause Analysis

### Mechanism

1. **refGeom.expt** contains crystal metadata including `ML_half_mosaicity_deg` (from DIALS indexing)
2. When `experiment` is passed to `simulate_forward_torch`:
   - `config_factories.py:380-396` extracts `ML_half_mosaicity_deg`
   - If > 0, sets `mosaic_spread_deg = ML_half_mosaicity_deg`
3. `mosaic_spread_deg > 0` triggers a different code path in `nanobrag_torch.Crystal`
4. This mosaic code path has a **gradient bug** — the analytical gradients are ~1000× smaller than numerical

### Code Path

```
experiment=experiment (refGeom.expt)
    ↓
config_factories.py:380-396 extracts ML_half_mosaicity_deg
    ↓
mosaic_spread_deg = 0.0398... (actual value from real data)
    ↓
nanobrag_torch.Crystal uses mosaic sampling loop
    ↓
Gradient bug in mosaic sampling backprop
    ↓
Jacobian mismatch ~1017×
```

### Workaround

```python
experiment=None  # Bypasses mosaic metadata extraction
    ↓
mosaic_spread_deg = 0.0 (default)
    ↓
nanobrag_torch.Crystal uses non-mosaic path
    ↓
Gradients correct (1.00× ratio)
```

---

## Implications

### For DBEX

1. **Gradient tests with `experiment=None` PASS** — DBEX integration layer is correct
2. **Cell parameter refinement works** when mosaic_spread_deg=0
3. **Current workaround viable:** Force `experiment=None` or `mosaic_spread_deg=0` for gradcheck tests

### For Upstream (nanobrag_torch)

The mosaic gradient bug request `mosaic_gradient_bug_2025_12_08.md` is **correctly scoped**:
- Affects: `Crystal._apply_mosaic_spread()` or related mosaic sampling loop
- Does NOT affect: Non-mosaic crystal simulation path
- Fix required: Ensure mosaic sampling derivatives flow correctly through autograd

---

## Recommendations

### Immediate (DBEX)

1. **Add diagnostic workaround test** to DB-AT-010 suite — DONE (this loop)
2. **Document workaround** in `docs/findings.md` as GRADIENT-003
3. **Do NOT modify tolerance** on original test — keep it as a regression detector

### Pending Upstream

1. **Wait for mosaic gradient fix** from nanobrag_torch maintainers
2. Once fixed, both tests should pass
3. Remove workaround test only after upstream fix verified

---

## Artifacts

- `gradcheck_no_mosaic.log` — Test execution log (PASSED)
- `gradcheck_crystal_cell_a_no_mosaic.json` — Metrics from passing test
- This report

---

## References

- `config_factories.py:380-396` — Mosaic metadata extraction
- `inbox/nanobrag_torch_cell_gradient_response_2025_12_08.md` — Upstream confirmation of cell gradients
- `mosaic_gradient_bug_2025_12_08.md` — Upstream request (HIGH priority)
- `docs/findings.md` GRADIENT-002 — Graph connectivity fix (Loop i=209)
