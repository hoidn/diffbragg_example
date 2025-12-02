# Ralph Input — Loop i=435

## Summary
Implement ARCH-REFACTOR-001 Phase D.1: migrate RefinementConfig from facade to new module `dbex/refinement/config.py` and update all import sites.

## Mode
Parity

## InitiativeType
architecture

## Focus
ARCH-REFACTOR-001 Phase D.1 — RefinementConfig Migration

## Branch
integration

## Mapped tests
- `tests/dbex/test_refinement_engine.py::test_refinement_engine_stage_a_minimal`
- `tests/dbex/test_refinement_engine.py::test_refinement_engine_stage_a_b_c_integration`
- `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210000Z/`

## Do Now

### Context

**Phase C Complete:** All `*_impl.py` modules eliminated (Exit Criterion #1 satisfied).
**Phase D Planning Complete:** Comprehensive planning artifacts produced in loop i=434 (commit 2c948b40).
**Current Goal:** Phase D (Facade Removal) Step 1 — Extract RefinementConfig to enable subsequent consumer migrations.

**Strategy:**
Phase D.1 is low-risk preparation work: relocate a pure data container (no logic) from the facade to a new module so later phases can migrate consumers without breaking backward compatibility during the transition.

### Implementation Steps

**Step 1: Create `dbex/refinement/config.py`**

Create new module with comprehensive docstring:

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
```

Then copy the **entire** `RefinementConfig` dataclass from `dbex/nanobrag_refinement.py:74-175` verbatim (all ~30 fields with defaults).

**Step 2: Add Temporary Re-export in Facade**

At the top of `dbex/nanobrag_refinement.py` (after existing imports, around line 72), add:

```python
# Temporary backward compatibility re-export (Phase D.1)
# Remove after Phase D.5 facade deletion
from dbex.refinement.config import RefinementConfig  # noqa: F401
```

Then **delete** the original `RefinementConfig` definition (lines 74-175) but **keep the import**.

This ensures old code using `from dbex.nanobrag_refinement import RefinementConfig` continues working during incremental migration.

**Step 3: Update Production Import Sites**

**3a.** `dbex/refine_one.py` (line ~505)
- **Current:** `from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig`
- **New:**
  ```python
  from dbex.refinement.config import RefinementConfig
  from dbex.nanobrag_refinement import run_nanobrag_refinement
  ```

**Step 4: Update Infrastructure Import Sites**

**4a.** `dbex/refinement/__init__.py` (line ~15, conditional import)
- **Current:** `from dbex.nanobrag_refinement import RefinementConfig`
- **New:** `from dbex.refinement.config import RefinementConfig`

**Step 5: Update Test Import Sites**

**5a.** `tests/dbex/test_refinement_engine.py` (2 inline imports at lines 31, 148)
- **Current:** `from dbex.nanobrag_refinement import RefinementConfig`
- **New:** `from dbex.refinement.config import RefinementConfig`

**5b.** `tests/dbex/test_stage_b_cpu_fallback.py` (3 inline imports at lines 40, 183, 291)
- **Current:** `from dbex.nanobrag_refinement import RefinementConfig`
- **New:** `from dbex.refinement.config import RefinementConfig`

**5c.** `tests/dbex/test_torch_refine_smoke.py` (6 inline imports at lines 400, 749, 947, 1063, 1393, 1793)
- **Current:** `from dbex.nanobrag_refinement import RefinementConfig, run_nanobrag_refinement`
- **New:**
  ```python
  from dbex.refinement.config import RefinementConfig
  from dbex.nanobrag_refinement import run_nanobrag_refinement
  ```

**Step 6: Validation**

Run mapped tests with canonical environment flags:

```bash
# Set environment
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAG_TORCH_FALLBACK_DEVICE=cpu
export SMOKE_DETECTOR_SIZE=small

# Test suite (4 tests)
pytest -vv \
  tests/dbex/test_refinement_engine.py::test_refinement_engine_stage_a_minimal \
  tests/dbex/test_refinement_engine.py::test_refinement_engine_stage_a_b_c_integration \
  tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210000Z/pytest_phase_d1.log 2>&1
```

**Expected:** All 4 tests PASS. No import errors. RefinementConfig accessible from both old path (facade re-export) and new path (dbex.refinement.config).

**Step 7: Verification**

```bash
# Static import check (new path)
python -c "from dbex.refinement.config import RefinementConfig; print('OK: new path')"

# Static import check (old path, backward compat)
python -c "from dbex.nanobrag_refinement import RefinementConfig; print('OK: facade re-export')"

# Record both outputs
{
  echo "=== New path test ==="
  python -c "from dbex.refinement.config import RefinementConfig; print('OK: new path')"
  echo "=== Old path test (facade re-export) ==="
  python -c "from dbex.nanobrag_refinement import RefinementConfig; print('OK: facade re-export')"
} > plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210000Z/import_verification.txt 2>&1
```

**Expected:** Both imports succeed.

**Step 8: Metrics**

Capture metrics in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210000Z/metrics.txt`:

```bash
{
  echo "=== Phase D.1 Metrics ==="
  echo "Files created: 1 (dbex/refinement/config.py)"
  wc -l dbex/refinement/config.py
  echo "Import sites updated: 8 (refine_one + __init__ + 2 test_refinement_engine + 3 test_stage_b_cpu_fallback + 6 test_torch_refine_smoke split)"
  echo "Facade lines removed (definition):"
  # Estimate ~102 lines (RefinementConfig dataclass body)
  echo "~102 (dataclass definition relocated)"
  echo "Facade lines added (re-export): ~3"
  echo "Net facade change: ~-99 lines"
} > plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210000Z/metrics.txt
```

## How-To Map

**Task 1: Create config.py**
- Location: `dbex/refinement/config.py`
- Content: Module docstring + imports + full RefinementConfig dataclass copied from `nanobrag_refinement.py:74-175`

**Task 2: Update facade**
- File: `dbex/nanobrag_refinement.py`
- Action: Add `from dbex.refinement.config import RefinementConfig  # noqa: F401` after existing imports, then delete lines 74-175 (original definition)

**Task 3-5: Update imports**
- Tool: Use `Edit` with `replace_all=False` for single-instance replacements
- Targets: 8 import sites across 5 files (refine_one.py, __init__.py, test_refinement_engine.py 2×, test_stage_b_cpu_fallback.py 3×, test_torch_refine_smoke.py 6×)
- Pattern: Split multi-imports so RefinementConfig comes from new module, facade imports stay for run_nanobrag_refinement (where needed)

**Task 6: Run tests**
- Command: `pytest -vv <selectors>` (see Step 6 above)
- Capture: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210000Z/pytest_phase_d1.log`

**Task 7: Verify imports**
- Command: Static import checks (see Step 7 above)
- Capture: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210000Z/import_verification.txt`

**Task 8: Capture metrics**
- Command: Line counts + change summary (see Step 8 above)
- Capture: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210000Z/metrics.txt`

## Pitfalls To Avoid

1. **Do NOT delete facade yet:** This phase only extracts RefinementConfig. Facade (`run_nanobrag_refinement` function) must remain until Phase D.5.

2. **Preserve backward compatibility:** Keep the facade re-export (`from dbex.refinement.config import RefinementConfig` in nanobrag_refinement.py) so old import paths work during incremental migration.

3. **Copy verbatim:** RefinementConfig dataclass body must be copied exactly (all fields, defaults, types). Do not refactor or reorder fields.

4. **Split multi-imports carefully:** In files that import both `RefinementConfig` and `run_nanobrag_refinement`, split them into two lines (see Step 3a, 5c).

5. **Module-scope imports only:** Do not modify inline imports inside functions (e.g., test_torch_refine_smoke.py has 6 inline imports; update all 6).

6. **Environment Freeze:** Do not install packages. Use existing runtime.

7. **Initiative Type:** This is `architecture` (pure refactor, no spec/behavior changes).

8. **Parity Requirement:** Tests must pass with identical behavior. Any test failure is a blocker.

## If Blocked

**Blocker: Import circular dependency**
- Symptom: `ImportError: cannot import name 'RefinementConfig'`
- Diagnosis: Check if config.py accidentally imports from modules that import it
- Action: RefinementConfig is a leaf node (only imports torch/typing); if circular dependency appears, record in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210000Z/blocker.md` and return to Galph

**Blocker: Test failures**
- Symptom: Any of the 4 mapped tests FAIL or ERROR
- Diagnosis: Check if RefinementConfig fields changed or imports incorrect
- Action: Capture full pytest log + traceback in artifact directory, record in `blocker.md`, return to Galph

**Blocker: Facade re-export not working**
- Symptom: Old import path `from dbex.nanobrag_refinement import RefinementConfig` fails
- Diagnosis: Check if facade import line is correct (must be before original definition was deleted)
- Action: Verify facade still has `from dbex.refinement.config import RefinementConfig` at top, record issue in `blocker.md`

## Findings Applied

**Mandatory:**
- ARCH-REFACTOR-001: Exit Criterion #1 satisfied (Phase C complete); Exit Criterion #2 pending (Phase D in progress)
- ARCH-REFINE-FLOW-001: RefinementEngine proven operational
- ARCH-STAGE-CONTEXT-001: Context builders canonical
- ARCH-ENGINE-002: Engine protocol enforced

**No other relevant findings in the knowledge base.**

## Pointers

- Planning artifact: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/config_migration_plan.md` (Option A decision + import site analysis)
- Consumer analysis: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/consumer_analysis.md` (8 import sites cataloged)
- Implementation plan: `plans/active/ARCH-REFACTOR-001/implementation.md` (Phase D.1 checklist, line 365)
- Exit criteria: `docs/fix_plan.md` (ARCH-REFACTOR-001 Exit Criterion #2: facade deletion after consumer migration)
- Facade source: `dbex/nanobrag_refinement.py:74-175` (RefinementConfig dataclass definition)
- Test registry: `docs/TESTING_GUIDE.md` (canonical env flags for mapped tests)
- Spec: `docs/spec-db-workflow.md` §§30-41 (refinement staging policy, unchanged by this refactor)

## Next Up

After Phase D.1 completion (this loop):
- **Loop i=436:** Phase D.2 implementation (CLI refactor: migrate `dbex/refine_one.py` to RefinementEngine)
- **Loop i=437:** Phase D.3 implementation (Test harness migration: 6 functions in `test_torch_refine_smoke.py`)
- **Loop i=438:** Phase D.4 + D.5 implementation (Import cleanup + facade deletion with 12-step verification)

Then mark ARCH-REFACTOR-001 **done** (Exit Criteria #1 and #2 both satisfied).
