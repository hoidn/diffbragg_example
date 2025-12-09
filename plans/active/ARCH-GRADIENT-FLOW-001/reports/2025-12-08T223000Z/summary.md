### Turn Summary
Resolved DB-AT-010 gradcheck failures by identifying two root causes: (1) upstream mosaic seed fix already available in `1df032c2`, (2) DBEX test fixtures used variance-weighted chi-squared loss with IRLS (detached variance), which is correct physics but incompatible with `torch.autograd.gradcheck`.
Fix: Changed test fixtures to use `sigma_readout=None` (MSE loss path) for gradcheck validation. All 6 DB-AT-010 tests now PASS (619s total runtime).
Next: Update galph_memory, commit changes, push.
Artifacts: plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T223000Z/ (gradcheck_mse_path.log)

## Root Cause Analysis

### Root Cause #1: Upstream Mosaic Gradient Bug (RESOLVED)
- Mosaic code path in `nanobrag_torch/models/crystal.py` used `torch.randn()` without deterministic seeding
- Fixed in upstream commit `1df032c2` via `torch.Generator` with seed + reparameterization trick
- Verified: `mosaic_seed` defaults to `-12345678` when None, ensuring deterministic behavior

### Root Cause #2: DBEX Variance-Weighted Loss Incompatible with Gradcheck (RESOLVED)
- `compute_masked_mse_loss()` with `sigma_readout` uses IRLS approach:
  ```python
  variance = torch.clamp(prediction.detach() + sigma_readout**2, min=1e-12)
  weighted_squared_error = squared_error / variance
  ```
- The `.detach()` is intentional physics (prevents "attraction to zero")
- However, this breaks `torch.autograd.gradcheck` because numerical gradients:
  - `f(x+eps)` uses variance based on `prediction_plus.detach()`
  - `f(x-eps)` uses variance based on `prediction_minus.detach()`
  - These are different values, causing Jacobian mismatch
- Fix: Test fixtures use `sigma_readout=None` (MSE loss path) for gradcheck

## Test Results
```
tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a PASSED
tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_gamma PASSED
tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_cell_a_no_mosaic PASSED
tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_detector_distance PASSED
tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_beam_wavelength PASSED
tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck PASSED
================== 6 passed, 4 warnings in 619.44s (0:10:19) ===================
```

## Changes Made
1. `tests/dbex/test_gradients.py`:
   - Updated `refinement_inputs` fixture to use `sigma_readout=None`
   - Updated all `TestDB_AT_010_Gradcheck` test methods to use MSE loss path
   - Added docstring explaining why variance-weighted loss is incompatible with gradcheck

2. `docs/findings.md`:
   - Added GRADIENT-004 finding documenting root cause and resolution

3. `docs/fix_plan.md`:
   - Updated ARCH-GRADIENT-FLOW-001 status to **done**
   - Documented both root causes and the fix
