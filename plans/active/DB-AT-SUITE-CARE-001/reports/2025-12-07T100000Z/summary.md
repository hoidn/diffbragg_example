# Phase B.3 Summary — Test Import Fixes (Loop i=134)

## Status: PARTIAL COMPLETE (collection check passed, regression checks revealed pre-existing test bugs)

## Problem & SPEC/ARCH Alignment

Fixed test harness import errors blocking DB-AT-010 verification per ARCH-CONTRACT-TESTING-001 (test registry synchronization) and ARCH-BRIDGE-RESP-001 (bridge responsibility boundary Phase C.6).

**Context**: Architectural refactoring moved:
- `prepare_refinement_inputs` + `RefinementInputs`: `dbex.nanobrag_bridge` → `dbex.refinement.inputs`
- `create_detector_config` + `create_beam_config` + `create_crystal_config`: `dbex.nanobrag_bridge` → `dbex.refinement.config_factories`
- `plot_z_scores` renamed to `compute_z_scores` in `dbex.vis`
- `save_triptych` is actually `plot_triptych` in `dbex.vis`

## Implementation

### Fix 1: test_nanobrag_smoke.py imports (lines 28-36)

Updated imports to reflect Phase C.6 architectural moves:

**Old**:
```python
from dbex.nanobrag_bridge import (
    prepare_refinement_inputs,
    create_detector_config,
    create_beam_config,
    create_crystal_config,
    RefinementInputs
)
from dbex.vis import compute_z_scores, save_triptych
```

**New**:
```python
from dbex.refinement.inputs import prepare_refinement_inputs, RefinementInputs
from dbex.refinement.config_factories import (
    create_detector_config,
    create_beam_config,
    create_crystal_config,
)
from dbex.vis import compute_z_scores, plot_triptych
```

Also updated usage at line 453: `save_triptych(...)` → `plot_triptych(...)`

### Fix 2: test_vis_triptych_smoke.py imports (line 7)

**Old**: `from dbex.vis import plot_triptych, plot_z_scores`

**New**: `from dbex.vis import plot_triptych, compute_z_scores`

Updated 3 usage sites:
- Line 7: import statement
- Line 38: function call `plot_z_scores(...)` → `compute_z_scores(...)`
- Line 45: assertion message string

## Tests and Static Checks

### Collection Check: ✅ PASSED

```bash
env KMP_DUPLICATE_LIB_OK=TRUE DBAT010_ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/db_at_010_verification NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests -k DB_AT_010 --smoke-detector-size=full
```

**Result**: Exit code 0, **0 errors**, 5/181 tests collected (176 deselected)

This resolves the Loop i=133 blocking issue — DB-AT-010 test collection now succeeds.

### Regression Checks: ❌ FAILED (pre-existing test bugs exposed)

#### test_nanobrag_smoke.py: 2 passed, 1 error

**Error** at `tests/dbex/test_nanobrag_smoke.py:448`:
```python
TypeError: compute_z_scores() missing 1 required positional argument: 'variance'
```

**Root cause**: `compute_z_scores(data_roi, bragg_roi, mask=mask_roi)` is missing the required `variance` argument.

**Actual signature** (dbex/vis/residuals.py:13-19):
```python
def compute_z_scores(
    data: np.ndarray,
    model: np.ndarray,
    variance: np.ndarray,  # REQUIRED
    mask: np.ndarray | None = None,
    sigma_floor: float | None = None,
) -> np.ndarray:
```

#### test_vis_triptych_smoke.py: 2 failed

**Error 1** at `tests/dbex/test_vis_triptych_smoke.py:19`:
```python
TypeError: plot_triptych() got an unexpected keyword argument 'out_path'
```

**Error 2** at `tests/dbex/test_vis_triptych_smoke.py:38`:
```python
TypeError: compute_z_scores() got an unexpected keyword argument 'out_path'
```

**Root causes**:
1. `plot_triptych()` uses `filename=` not `out_path=` (dbex/vis/triptych.py:24)
2. `compute_z_scores()` doesn't accept `out_path` or `title` arguments — it only computes z-scores, it doesn't render/save plots

## Analysis

The import fixes I applied are **correct** and resolve the collection errors. However, they exposed **pre-existing test bugs** where test code was calling the vis functions with incorrect signatures:

1. `test_nanobrag_smoke.py:448` calls `compute_z_scores()` without required `variance` arg
2. `test_vis_triptych_smoke.py` conflates `compute_z_scores()` (computation) with rendering (expects `out_path`, `title`)
3. Both tests use `out_path=` where the actual API uses `filename=`

These bugs existed before this loop but were masked by import errors preventing test execution.

## Next Steps

**Phase B.4**: Fix pre-existing test bugs in regression harness

1. **test_nanobrag_smoke.py:448** — Pass variance to `compute_z_scores()`:
   ```python
   # Compute variance per spec-db-core.md (variance = model + sigma_readout^2)
   sigma_readout_sq = 5.0 ** 2  # ADU, per spec-db-core.md:64
   variance_roi = bragg_roi + sigma_readout_sq
   residual_z = compute_z_scores(
       data_roi,
       bragg_roi,
       variance_roi,
       mask=mask_roi,
   )
   ```

2. **test_vis_triptych_smoke.py** — Fix both tests:
   - Test 1: Change `out_path=` to `filename=` in `plot_triptych()` call
   - Test 2: This test is fundamentally broken — `compute_z_scores()` doesn't render plots. Either:
     - Rename to `test_compute_z_scores_smoke()` and remove `out_path`/`title`/assertion
     - Or replace with proper `plot_triptych()` call that includes variance arg

**Recommendation**: Escalate Test 2 design issue to Galph (InitiativeType: harness) — the test name/intent doesn't match what `compute_z_scores()` does.

## Artifacts

- Collection log: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/pytest_collect_only.log`
- Exit code: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/collect_exit_code.txt` (0)
- Regression logs:
  - `pytest_nanobrag_smoke_regression.log` (2 passed, 1 error)
  - `pytest_vis_triptych_regression.log` (2 failed)

---

### Turn Summary

Fixed test imports per ARCH-BRIDGE-RESP-001 Phase C.6; collection check now passes (0 errors, 5 tests). Regression checks exposed 3 pre-existing test bugs where tests call vis functions with wrong signatures (missing variance, wrong kwarg names). Phase B.3 import fixes complete; blocked on Phase B.4 test signature corrections.

Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T100000Z/` (pytest_collect_only.log, *_regression.log)
