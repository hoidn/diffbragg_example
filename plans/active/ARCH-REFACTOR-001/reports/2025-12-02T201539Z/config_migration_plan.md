# Phase D.1: RefinementConfig Migration Plan

**Initiative:** ARCH-REFACTOR-001 Phase D.1
**Date:** 2025-12-02T201539Z
**Status:** Planning

## Objective

Relocate `RefinementConfig` dataclass from `dbex/nanobrag_refinement.py` (facade) to new module `dbex/refinement/config.py` before migrating consumers to RefinementEngine.

## Rationale: Option A (New Module) vs Option B (Inline to context.py)

### Option A: Create `dbex/refinement/config.py` ✅ **RECOMMENDED**

**Pros:**
1. **Separation of concerns:** Config (immutable job setup) vs Context (runtime state)
2. **Size management:** `context.py` already ~950+ lines; avoiding growth to 1050+
3. **Naming clarity:** `dbex.refinement.config.RefinementConfig` is self-documenting
4. **Future-proof:** Config likely to grow with Stage D/E/F options (warm cache policies, Stage D hyperparams, etc.)
5. **Import clarity:** Config has no dependencies on Engine/Stages; clean leaf node

**Cons:**
1. One additional file in `dbex/refinement/` (negligible)

### Option B: Inline to `dbex/refinement/context.py`

**Pros:**
1. Fewer files (marginally simpler directory structure)

**Cons:**
1. **Mixing concerns:** Config (job-level setup) mixed with Context (runtime dataclasses)
2. **File size bloat:** `context.py` crosses 1000-line threshold (cyclomatic risk)
3. **Less discoverable:** Config semantically distinct from runtime contexts like `StageAContext`, `StageCContext`

### Decision: **Option A**

Create `dbex/refinement/config.py` for semantic clarity, size management, and future extensibility.

## Source: RefinementConfig Location

**Current location:** `dbex/nanobrag_refinement.py:74-175` (~102 lines, including all fields + defaults)

**Contents to migrate:**
- `@dataclass` decorator
- `RefinementConfig` class with ~30 fields:
  * LBFGS hyperparameters (history_size, max_iter, tolerance_grad, tolerance_change)
  * ROI sampling (roi_sample_fraction, full_validation_interval)
  * Convergence guards (min_loss_improvement, early_stop_window, max_loss_increase)
  * Feature flags (enable_hkl_interpolation, use_u_matrix_parameterization, etc.)
  * Warm cache flags (enable_stage_a_warm_cache, enable_stage_a_roi_mode, etc.)
  * Stage B/C config (enable_stage_b, stage_b_mode, stage_b_n_shells, enable_stage_c, etc.)
  * Device/dtype (device: str, dtype: torch.dtype)
  * Physics parameters (sigma_floor_value, sigma_readout_provenance, sigma_readout_reference_value)
  * Calibration metadata (calibration_metadata: Optional[Dict])

**No logic:** Pure data container, no methods (safe to move).

## Target Module Structure

### File: `dbex/refinement/config.py`

```python
"""
Refinement job configuration for RefinementEngine.

Defines RefinementConfig dataclass encapsulating hyperparameters, feature flags,
and job-level metadata for Stage A/B/C LBFGS refinement.

See:
- docs/spec-db-workflow.md §§30-41 (Staging policy)
- docs/pytorch_runtime_checklist.md (device/dtype neutrality)
- ARCH-REFACTOR-001 Phase D.1 (config extraction from facade)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import torch


@dataclass
class RefinementConfig:
    """Configuration for Stage A/B/C LBFGS refinement.

    Job-scoped immutable setup; does not hold runtime state (see RefinementContext).
    Consumed by RefinementEngine, Stages, and CLI entry points.
    """
    # ... (all fields from nanobrag_refinement.py:78-175)
    # Copy verbatim with existing defaults and docstrings
```

**Imports required:**
- `dataclasses.dataclass, dataclasses.field`
- `typing.Any, Dict, Optional`
- `torch` (for `torch.dtype`)

**No imports from:**
- `dbex.refinement.engine` (avoid circular)
- `dbex.refinement.stage_*` (config is leaf node)
- `dbex.nanobrag_refinement` (being deleted)

## Migration Steps

### Step 1: Create `dbex/refinement/config.py`

1. Create file with module docstring (see above)
2. Copy `@dataclass` decorator + `RefinementConfig` class body from `nanobrag_refinement.py:74-175`
3. Add required imports (dataclasses, typing, torch)
4. Verify no dangling imports or references to facade

**Estimated size:** ~120 lines (module docstring + imports + dataclass)

### Step 2: Update Import Sites (7 files)

**Production (2 files):**

1. **dbex/refine_one.py:505**
   - Before: `from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig`
   - After:
     ```python
     from dbex.nanobrag_refinement import run_nanobrag_refinement  # Temporary until D.2
     from dbex.refinement.config import RefinementConfig
     ```
   - Validation: `python -m dbex.refine_one --help` (no ImportError)

2. **dbex/refinement/__init__.py:15**
   - Before: `from dbex.nanobrag_refinement import RefinementConfig`
   - After: `from dbex.refinement.config import RefinementConfig`
   - Validation: `python -c "from dbex.refinement import RefinementConfig"` (no ImportError)

**Test (5 inline imports across 3 files):**

3. **tests/dbex/test_refinement_engine.py**
   - Lines 31, 148
   - Before: `from dbex.nanobrag_refinement import RefinementConfig`
   - After: `from dbex.refinement.config import RefinementConfig`
   - Validation: `pytest tests/dbex/test_refinement_engine.py -v`

4. **tests/dbex/test_stage_b_cpu_fallback.py**
   - Lines 40, 183, 291
   - Before: `from dbex.nanobrag_refinement import RefinementConfig`
   - After: `from dbex.refinement.config import RefinementConfig`
   - Validation: `pytest tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload -v`

5. **tests/dbex/test_torch_refine_smoke.py**
   - Lines 400, 749, 947, 1063, 1393, 1793 (6 inline imports)
   - Before: `from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig`
   - After:
     ```python
     from dbex.nanobrag_refinement import run_nanobrag_refinement  # Temporary until D.3
     from dbex.refinement.config import RefinementConfig
     ```
   - Validation: Full test suite (all 6 functions) in Phase D.3

### Step 3: Update Facade (Keep Re-export Temporarily)

**dbex/nanobrag_refinement.py:**
- Delete `RefinementConfig` dataclass body (lines 74-175)
- Add re-export for backward compatibility until Phase D.5:
  ```python
  # ARCH-REFACTOR-001 Phase D.1: RefinementConfig relocated to dbex.refinement.config
  # Re-export temporarily for consumers not yet migrated (will be removed in Phase D.5)
  from dbex.refinement.config import RefinementConfig
  ```
- Place re-export at top of file (after imports section, before `run_nanobrag_refinement()` definition)

**Rationale:** Allows incremental migration (D.1 → D.2 → D.3 → D.4) without breaking interim states.

### Step 4: Static Validation

Run static checks before committing:

```bash
# No import errors
python -c "from dbex.refinement.config import RefinementConfig; print('Config module OK')"
python -c "from dbex.refinement import RefinementConfig; print('__init__ re-export OK')"
python -c "from dbex.nanobrag_refinement import RefinementConfig; print('Facade re-export OK')"

# Type-check (if mypy available; skip if Environment Freeze prevents tooling)
# mypy dbex/refinement/config.py dbex/refinement/__init__.py
```

### Step 5: Test Validation

Run test selectors to confirm no behavioral regression:

```bash
# Config-only consumers
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_refinement_engine.py \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/pytest_refinement_engine.log

AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/pytest_stage_b_guard.log

# Smoke tests (facade still works)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  --smoke-detector-size=small \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/pytest_stage_a_smoke.log
```

**Gate:** All tests PASSED, no ImportError

## Risk Assessment

**Risk Level:** LOW

- **Pure data container:** No logic, no side effects
- **Leaf node:** Config imports only from stdlib + torch (no dbex internal dependencies)
- **Backward compatible:** Facade re-export prevents breakage during incremental migration
- **Well-isolated:** Tests validate config-only consumers (no Engine/Stage dependency)

**Rollback criteria:**
- If ImportError in any validation step → revert Step 1–3 and reassess

## Mapped Tests

Phase D.1 validation relies on:
- `tests/dbex/test_refinement_engine.py` (2 tests, RefinementEngine instantiation with config)
- `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload` (1 test, StageB config usage)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (1 test, facade smoke with RefinementConfig)

**Total:** 4 tests covering config-only and facade paths

## Implementation Artifacts

Artifacts for Phase D.1 implementation (follow-up loop) will be saved under:
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/` (D.1 implementation timestamp)

**Expected files:**
- `pytest_refinement_engine.log`
- `pytest_stage_b_guard.log`
- `pytest_stage_a_smoke.log`
- `summary.md` (Ralph loop summary)

## Dependencies & Sequencing

**Blocks:**
- Phase D.2 (CLI Refactor) — requires `dbex.refinement.config` to exist
- Phase D.3 (Test Harness Migration) — requires RefinementConfig import path stable
- Phase D.5 (Facade Deletion) — requires all consumers migrated away from `dbex.nanobrag_refinement.RefinementConfig`

**Unblocked by:**
- Phase C.9 complete (all `*_impl.py` deleted)
- RefinementEngine proven operational (ARCH-REFINE-FLOW-001)

**Can run in parallel with:**
- None (D.1 is foundational for all subsequent Phase D work)

## Success Criteria

Phase D.1 is **complete** when:
1. ✅ `dbex/refinement/config.py` exists with RefinementConfig dataclass
2. ✅ All 7 import sites updated to `from dbex.refinement.config import RefinementConfig`
3. ✅ `dbex/nanobrag_refinement.py` re-exports RefinementConfig (temporary bridge)
4. ✅ Static checks pass (no ImportError)
5. ✅ 4 validation tests PASS (config-only + facade smoke)
6. ✅ No circular import warnings or errors
7. ✅ Artifacts logged under D.1 implementation reports directory

**Sign-off:** Mark implementation.md Phase D.1 checklist item complete; proceed to D.2 (CLI Refactor).
