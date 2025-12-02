# Input for Ralph — ARCH-REFACTOR-001 Phase C.5

## Summary
Finalize Stage B consolidation by inlining LBFGS execution logic and extracting HKL utilities to a dedicated module, enabling `stage_b_impl.py` deletion in Phase C.6.

## Mode
Parity

## InitiativeType
architecture

## Focus
[ARCH-REFACTOR-001] — Refinement Engine Modularization & Physics Separation

## Branch
integration

## Mapped tests
- `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T184846Z/`

## Do Now

**Context**: Ralph completed Phase C.4 (commit cd855064), inlining `_build_stage_b_params` into `StageB` as a 322-line private method. Stage B now requires strict `RefinementContext` inputs and owns its parameter building logic. Both acceptance gates passed (guard 0.77s, shell 22.84s).

**This loop (C.5)**: Complete the Stage B consolidation by:
1. Creating `dbex/refinement/hkl_utils.py` with ASU/shell utilities (no StageB dependencies)
2. Inlining `_run_stage_b_lbfgs` and `_check_stage_b_baseline_parity` into `StageB` class
3. Updating all import sites to reference the new locations
4. Validating via Stage B guard + shell smoke tests

**Implement**:

### Task 1: Create `dbex/refinement/hkl_utils.py`
1. Create new file `dbex/refinement/hkl_utils.py`
2. Copy these functions from `dbex/refinement/stage_b_impl.py` (lines 185-487):
   - `compute_hkl_shell_lookup` (lines 185-278)
   - `compute_hkl_asu_map` (lines 280-395)
   - `initialize_asu_modifiers` (lines 397-445)
   - `apply_asu_modifiers` (lines 447-487)
3. Add module docstring:
```python
"""
HKL utilities for ASU mapping and shell binning (Stage B refinement support).

Provides general-purpose reciprocal space utilities for multi-reflection refinement modes,
extracted from Stage B implementation helpers to enable cross-stage reuse.

References:
- TORCH-REFINE-004 (per-reflection mode)
- docs/spec-db-workflow.md §76-79 (Stage B structure factor modifiers)
- REFINE-005 (cctbx reuse guard for ASU mapping)
"""
```
4. Ensure all imports are at module scope (no lazy imports)
5. Remove any StageB/RefinementContext dependencies (these functions should be pure utilities)

### Task 2: Inline `_check_stage_b_baseline_parity` into `StageB._check_baseline_parity()`
1. In `dbex/refinement/stage_b.py`, add a private method `_check_baseline_parity()` containing the body of `_check_stage_b_baseline_parity` from `stage_b_impl.py` (lines 44-183)
2. Keep the exact signature:
```python
def _check_baseline_parity(
    self,
    canonical_baseline: Dict[str, Any],
    initial_chi_squared_b: torch.Tensor,
    collector: StageBTelemetryCollector,
    param_values: Dict[str, Any],
    compute_loss_stage_b: Callable,
    n_panels: int,
) -> None:
```
3. Preserve the collector-only telemetry path (ARCH-TELEMETRY-001 Phase C.1)
4. Keep JSON diff emission logic intact
5. Update any references to use `self._check_baseline_parity()`

### Task 3: Inline `_run_stage_b_lbfgs` into `StageB._run_lbfgs()`
1. In `dbex/refinement/stage_b.py`, add a private method `_run_lbfgs()` containing the body of `_run_stage_b_lbfgs` from `stage_b_impl.py` (lines 819-1025)
2. Mirror the Stage C pattern from ARCH-REFACTOR-001 Phase C.2
3. Signature should match current helper but as an instance method:
```python
def _run_lbfgs(
    self,
    param_values: Dict[str, Any],
    compute_loss_stage_b: Callable,
    initial_chi_squared_b: torch.Tensor,
    telemetry_state: StageBTelemetryState,
    collector: StageBTelemetryCollector,
    canonical_baseline: Dict[str, Any],
    n_panels: int,
    job_context: 'JobContext',
    shared_context: RefinementSharedContext,
    stage_a_context: 'StageAContext',
) -> Tuple[StageResult, RefinementTelemetry, str, str, Optional[np.ndarray], Optional[Dict[str, np.ndarray]]]:
```
4. Update the call to baseline parity to use `self._check_baseline_parity(...)`
5. Ensure observer-only telemetry collector path remains intact
6. Return signature matches existing helper

### Task 4: Update `dbex/refinement/stage_b.py` imports
1. At module scope, add:
```python
from dbex.refinement.hkl_utils import (
    compute_hkl_shell_lookup,
    compute_hkl_asu_map,
    initialize_asu_modifiers,
    apply_asu_modifiers,
)
```
2. Remove the import of `_run_stage_b_lbfgs` and `_check_stage_b_baseline_parity` from `stage_b_impl`
3. Update `StageB.run()` to call `self._run_lbfgs(...)` instead of the module-level helper
4. Update any other internal references

### Task 5: Update `dbex/nanobrag_refinement.py` imports
1. Change:
```python
from dbex.refinement.stage_b_impl import (
    compute_hkl_shell_lookup,
    compute_hkl_asu_map,
```
To:
```python
from dbex.refinement.hkl_utils import (
    compute_hkl_shell_lookup,
    compute_hkl_asu_map,
```

### Task 6: Update test imports
1. In `tests/dbex/test_stage_b_cpu_fallback.py`, check for any direct imports from `stage_b_impl` and update them
2. In `tests/dbex/test_stage_b_asu_mapping.py`, update ASU utility imports to use `hkl_utils`
3. If tests patch `stage_b_impl` functions, update patches to target new locations (`StageB._check_baseline_parity`, `hkl_utils.*`)

### Task 7: Validation
Run both mapped test selectors with canonical environment flags:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload \
| tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T184846Z/pytest_stage_b_guard.log
```

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small \
| tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T184846Z/pytest_stage_b_shell.log
```

**Expected**: Both tests PASS with no behavioral regression. Telemetry, baseline parity guard, and observer-only collector path should produce identical results to Phase C.4.

## How-To Map

1. **Create hkl_utils module**: Copy 4 functions from stage_b_impl.py (lines 185-487) into new `dbex/refinement/hkl_utils.py` with module docstring
2. **Inline baseline parity**: Copy `_check_stage_b_baseline_parity` (lines 44-183) as `StageB._check_baseline_parity()` private method in stage_b.py
3. **Inline LBFGS runner**: Copy `_run_stage_b_lbfgs` (lines 819-1025) as `StageB._run_lbfgs()` private method in stage_b.py
4. **Update StageB imports**: Import from hkl_utils, remove stage_b_impl imports for relocated functions, update internal calls to use `self._run_lbfgs()` and `self._check_baseline_parity()`
5. **Update legacy facade imports**: Change `dbex/nanobrag_refinement.py` to import from `hkl_utils` instead of `stage_b_impl`
6. **Update test imports**: Change `tests/dbex/test_stage_b_cpu_fallback.py` and `tests/dbex/test_stage_b_asu_mapping.py` to import from new locations
7. **Run tests**: Execute both validation commands above, save logs to artifacts directory

## Pitfalls To Avoid

1. **Do not change any logic**: This is a pure code motion refactor. Function bodies should be copied verbatim.
2. **Preserve collector-only path**: Ensure `_check_baseline_parity` and `_run_lbfgs` continue using `StageBTelemetryCollector` (ARCH-TELEMETRY-001)
3. **Keep JSON diff emission**: Baseline parity guard must still write diff files when parity fails
4. **No circular imports**: hkl_utils must not import from StageB or RefinementContext
5. **Test both selectors**: Both guard and shell smoke must pass before considering this complete
6. **Environment Freeze**: Do not install packages or modify the runtime environment
7. **Signature preservation**: Inlined methods should keep the same parameters and return types as the original helpers
8. **Import order**: Put hkl_utils imports at module scope, not nested in functions

## If Blocked

If imports create circular dependencies:
1. Check that hkl_utils has no StageB imports
2. Ensure hkl_utils only imports torch, numpy, and leaf modules (no refinement/context)
3. Capture the import error in the artifacts directory and note it in summary.md

If tests fail:
1. Compare telemetry output between Phase C.4 and C.5 runs
2. Check that `self._run_lbfgs()` is called with the same arguments as the old helper
3. Verify baseline parity guard still emits JSON diffs on failure
4. Save failure logs to artifacts directory and note the specific failure signature

## Findings Applied

- ARCH-TELEMETRY-001 Phase C.1: Collector-only telemetry path must remain intact in baseline parity guard and LBFGS runner
- ARCH-STAGE-CTX-001: StageB owns its execution logic, no procedural helpers outside the class
- ARCH-ENGINE-002: Stage wrappers are the canonical seam for multi-stage orchestration
- REFINE-005: ASU mapping utilities preserve cctbx reuse guard to avoid redundant computation
- TORCH-REFINE-004: Per-reflection and shell modes rely on ASU/shell utilities in hkl_utils

## Pointers

- Implementation plan: `plans/active/ARCH-REFACTOR-001/implementation.md` (Phase C.5 checklist, lines ~97-141)
- Planning notes: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T184846Z/planning_notes.md`
- Spec: `docs/spec-db-workflow.md` §76-79 (Stage B structure factor modifiers)
- Finding: `docs/findings.md`:REFINE-FLOW-001 (Stage B baseline parity guard)
- Phase C.4 completion: commit cd855064, artifacts `plans/active/ARCH-REFACTOR-001/reports/2025-12-04T160500Z/`
- Current stage_b_impl.py: 1025 lines total
  - Functions to move to hkl_utils: lines 185-487 (~303 lines)
  - Functions to inline in StageB: lines 44-183 (~140 lines baseline parity) + lines 819-1025 (~207 lines LBFGS) = ~347 lines total

## Next Up

After Phase C.5 completion:
- Phase C.6: Delete `dbex/refinement/stage_b_impl.py` and `.backup` once all imports are migrated and tests pass
- Phase C.7-C.9: Repeat the same pattern for Stage A (strictness, inlining, cleanup)
- Phase D: Migrate all consumers to RefinementEngine and delete `dbex/nanobrag_refinement.py` facade
