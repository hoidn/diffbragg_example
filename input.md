# Input for Ralph — ARCH-REFACTOR-001 Phase C.8: Stage A Helper Inlining

## Summary
Inline 3 remaining Stage-A-private helpers (~1025 lines total) into `StageA` class, mirroring Stage C/B consolidation pattern.

## Mode
Parity

## InitiativeType
architecture

## Focus
[ARCH-REFACTOR-001] — Refinement Engine Modularization & Physics Separation (Phase C.8)

## Branch
integration

## Mapped tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry`
- `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-04T215000Z/`

## Do Now

### 1. Inline _sync_stage_a_crystal → StageA._sync_crystal()

**Source:** `dbex/refinement/stage_a_impl.py` lines 238-247 (~10 lines, trivial)

**Target:** Add as private method in `dbex/refinement/stage_a.py` (class StageA)

**Action:**
- Copy the function body from stage_a_impl.py:238-247
- Add as `def _sync_crystal(self, stage_a_ctx: StageAContext, crystal_model):`
- Place it near the beginning of the StageA class (after `__init__` if present, or as first method)
- Keep docstring, preserve all attribute transfers (interpolate, hkl_data, hkl_metadata, beam_config)

**Update call site:**
- Line 442 in stage_a.py: Change `warm_crystal_model = _sync_stage_a_crystal(stage_a_ctx, warm_crystal_model)`
- To: `warm_crystal_model = self._sync_crystal(stage_a_ctx, warm_crystal_model)`

### 2. Inline _build_stage_a_params → StageA._build_stage_a_params()

**Source:** `dbex/refinement/stage_a_impl.py` lines 510-1226 (~717 lines, complex)

**Target:** Add as private method in `dbex/refinement/stage_a.py` (class StageA)

**Action:**
- Copy the entire function from stage_a_impl.py:510-1226
- Add as `def _build_stage_a_params(self, ...):`  (keep all parameters exactly as-is)
- Place after `_sync_crystal()` method
- **CRITICAL:** Preserve all indentation and logic:
  - Telemetry collector wiring
  - Sigma floor guards
  - Panel/ROI mode branching
  - CPU fallback logic (GRADIENT-003)
  - Quaternion/cell parameter handling
  - All type hints and docstrings

**Update call site:**
- Line 924 in stage_a.py: Change `helper1_result = _build_stage_a_params(...)`
- To: `helper1_result = self._build_stage_a_params(...)`

### 3. Inline _run_stage_a_lbfgs → StageA._run_lbfgs()

**Source:** `dbex/refinement/stage_a_impl.py` lines 1227-end (~298 lines, medium)

**Target:** Add as private method in `dbex/refinement/stage_a.py` (class StageA)

**Action:**
- Copy the entire function from stage_a_impl.py:1227-end
- Add as `def _run_lbfgs(self, ...):`  (keep all parameters exactly as-is)
- Place after `_build_stage_a_params()` method
- **CRITICAL:** Preserve all observer/telemetry logic:
  - ARCH-TELEMETRY-001 observer-only path
  - Baseline/periodic/final validation routing
  - LBFGS convergence checks
  - All exception handling
  - All type hints and docstrings

**Update call site:**
- Line 1033 in stage_a.py: Change `status, message, final_chi_squared_value, final_masked_mse_value, best_params_snapshot = _run_stage_a_lbfgs(...)`
- To: `status, message, final_chi_squared_value, final_masked_mse_value, best_params_snapshot = self._run_lbfgs(...)`

### 4. Update imports in stage_a.py

Remove these 3 helpers from the import statement (currently lines 36-40):
```python
from dbex.refinement.stage_a_impl import (
    _build_stage_a_params,
    _run_stage_a_lbfgs,
    _sync_stage_a_crystal,
)
```

After removal, this import should be deleted entirely (stage_a.py no longer imports from stage_a_impl).

**DO NOT** delete stage_a_impl.py or modify it — that's Phase C.9.

### 5. Validation

Run all 4 mapped tests with canonical environment:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T215000Z/pytest_stage_a_expansion.log

pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T215000Z/pytest_stage_a_telemetry.log

pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T215000Z/pytest_stage_b_guard.log

DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T215000Z/pytest_stage_b_shell.log
```

All 4 tests must PASS. Capture logs under artifacts directory.

## How-To Map
Copy function bodies verbatim from stage_a_impl.py, add as private methods in StageA class (with `self` parameter), update 3 call sites to use `self._*`, remove stage_a_impl imports, run validation suite.

## Pitfalls To Avoid
- **DO NOT modify function bodies** — copy verbatim, only add `self` parameter
- **DO NOT delete stage_a_impl.py** — it stays for Phase C.9
- **DO NOT change indentation/whitespace** inside copied functions — preserve exactly
- **Environment Freeze** — no package installs
- **Device/dtype neutrality (GRADIENT-004)** — preserve tensor handling
- **Collector-only telemetry (ARCH-TELEMETRY-001)** — keep observer callbacks unchanged
- **Warm cache (PERF-WARM-016)** — preserve simulator reuse logic

## If Blocked
Record error signature, file:line, root cause hypothesis in Attempts History (docs/fix_plan.md). If indentation errors occur, use `python -m compileall dbex/refinement/stage_a.py` to locate syntax errors.

## Findings Applied
- ARCH-ENGINE-002: Stage wrappers are canonical seams
- ARCH-REFACTOR-001: Follow Stage C.2/C.5 inlining precedent
- ARCH-STAGE-CTX-001: Typed contexts only
- ARCH-TELEMETRY-001: Collector-first telemetry, observer-only path
- GRADIENT-004: Device/dtype neutrality
- PERF-WARM-016: Warm cache performance optimization

## Pointers
- Planning notes: plans/active/ARCH-REFACTOR-001/reports/2025-12-04T215000Z/planning_notes.md
- Implementation plan: plans/active/ARCH-REFACTOR-001/implementation.md Phase C.8
- Fix plan: docs/fix_plan.md — Row [ARCH-REFACTOR-001]
- Testing: docs/TESTING_GUIDE.md §2

## Next Up
Phase C.9: Delete stage_a_impl.py entirely and verify zero remaining imports

## Doc Sync Plan
Not applicable (no new tests added; existing selectors validate behavior)

## Mapped Tests Guardrail
All 4 mapped selectors currently collect >0 tests. No new tests authored this loop.
