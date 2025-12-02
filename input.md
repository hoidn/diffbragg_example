# Input for Ralph — Loop i=430

## Summary
Delete `dbex/refinement/stage_b_impl.py` after migrating remaining imports to proper source modules.

## Mode
Parity

## InitiativeType
architecture

## Focus
ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation

## Branch
integration

## Mapped tests
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  --smoke-detector-size=small
```

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T190946Z/`

## Do Now

### Context
Phase C.5 successfully inlined `_build_stage_b_params`, `_run_stage_b_lbfgs`, and `_check_stage_b_baseline_parity` into `StageB` class methods, and extracted HKL utilities to `hkl_utils.py`. The `stage_b_impl.py` file now serves only as a pass-through for Stage A helpers (`_retarget_stage_a_simulators`, `_get_sigma_floor_sq_tensor`, `_build_stage_a_context`) that are actually defined in `stage_a_impl.py`. Phase C.6 completes the Stage B consolidation by updating imports to source from the correct modules and deleting `stage_b_impl.py`.

### Implementation Tasks

**C6.A — Update `dbex/refinement/stage_b.py` imports**
1. Change lines 32-37 to import the three Stage A helpers directly from `stage_a_impl`:
   ```python
   # ARCH-REFACTOR-001 Phase C.6: Import Stage A helpers from their actual source
   from dbex.refinement.stage_a_impl import (
       _retarget_stage_a_simulators,
       _get_sigma_floor_sq_tensor,
       _build_stage_a_context,
   )
   ```
2. Remove the `from dbex.refinement.stage_b_impl import (...)` block entirely
3. Preserve all other imports unchanged (hkl_utils, context, telemetry_collectors, etc.)

**C6.B — Update `dbex/nanobrag_refinement.py` imports**
1. Remove lines 67-70 (`from dbex.refinement.stage_b_impl import ...`) entirely
2. The facade no longer calls these helpers directly (uses RefinementEngine), so the imports are dead code
3. Preserve the comments at lines referencing the logic (lines ~2500-2530 mention `_build_stage_b_params` for documentation, leave those)

**C6.C — Verify no other consumers**
1. Run `rg "from.*stage_b_impl import" --type py` to confirm only tests remain
2. Check test files: `tests/dbex/test_stage_b_cpu_fallback.py` may patch `stage_b_impl._build_stage_b_params`
3. If tests patch `stage_b_impl` helpers, update them to patch `StageB._build_stage_b_params` or the Stage A source

**C6.D — Delete `dbex/refinement/stage_b_impl.py`**
1. Verify the above changes landed and imports resolve correctly: `python -c "from dbex.refinement import stage_b"`
2. Delete the file: `rm dbex/refinement/stage_b_impl.py`
3. Also delete `.backup` if it exists: `rm dbex/refinement/stage_b_impl.py.backup`

**C6.E — Validation**
1. Run the mapped tests (Stage B guard + shell smoke) with canonical env flags
2. Capture logs under `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T190946Z/`
   - `pytest_stage_b_guard.log`
   - `pytest_stage_b_shell.log`
3. Verify both tests PASS with no import errors or behavioral regressions

### How-To Map

**Import verification**
```bash
python -c "from dbex.refinement import stage_b; print('StageB imports OK')"
```

**Find remaining stage_b_impl consumers**
```bash
rg "from.*stage_b_impl import" --type py | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T190946Z/remaining_imports.txt
```

**Run mapped tests**
```bash
cd /home/ollie/Documents/diffbragg_example

# Stage B guard test
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T190946Z/pytest_stage_b_guard.log

# Stage B shell smoke
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  --smoke-detector-size=small \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T190946Z/pytest_stage_b_shell.log
```

### Pitfalls To Avoid

1. **Do not change Stage A helpers** — `_retarget_stage_a_simulators`, `_get_sigma_floor_sq_tensor`, `_build_stage_a_context` stay in `stage_a_impl.py` (they are Stage A internals reused by Stage B)
2. **Do not delete HKL utilities** — `hkl_utils.py` is the new shared module for ASU/shell helpers (TORCH-REFINE-004)
3. **Do not touch StageB class methods** — `_build_stage_b_params()`, `_run_lbfgs()`, `_check_baseline_parity()` are already correct inside StageB
4. **Preserve comment references** — `nanobrag_refinement.py` has documentation comments mentioning the old helper names for historical context; leave those intact
5. **Initiative type boundary** — This is pure architecture refactoring (moving code without changing behavior); do not adjust any physics, gates, or acceptance criteria

### If Blocked

If import errors occur after deleting `stage_b_impl.py`, check:
1. Did you update both `stage_b.py` and `nanobrag_refinement.py` imports?
2. Do test files still patch `@patch('dbex.refinement.stage_b_impl.*')`? Update to `@patch('dbex.refinement.stage_b.StageB.*')` or `@patch('dbex.refinement.stage_a_impl.*')`
3. Capture the error traceback under `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T190946Z/import_error.txt`
4. Note the block in galph_memory and switch focus if the root cause requires upstream changes

### Findings Applied (Mandatory)

- **ARCH-ENGINE-002** — StageA/B/C wrappers are the canonical seam; helpers extracted from `*_impl.py` modules now live inside Stage classes
- **ARCH-REFACTOR-001** — Phase C consolidation: delete implementation helpers after inlining logic into Stage classes
- **ARCH-STAGE-CTX-001** — Typed contexts replace ad-hoc dicts; Stage A helpers build `StageAContext` for cross-stage reuse
- **ARCH-TELEMETRY-001** — Collector-only telemetry path proven stable in Phase C.1; no regressions expected from import moves
- **ARCH-LAZY-IMPORTS-001** — Module-scope imports preferred; this change aligns with the eager-import refactoring completed in Phase B.3

### Pointers

- **Spec**: `docs/spec-db-workflow.md` §7 (Protocol Architecture)
- **Plan**: `plans/active/ARCH-REFACTOR-001/implementation.md` Phase C.6
- **Fix Plan**: `docs/fix_plan.md` ARCH-REFACTOR-001 row (Attempts History + exit criteria)
- **IDL**: `docs/architecture/dbex/refinement/context.idl.md` (StageAContext/StageBContext contracts)
- **Testing Guide**: `docs/TESTING_GUIDE.md` §2.1 (Stage B guard + shell smoke selectors)

## Next Up (optional)

1. **Phase C.7–C.9 (Stage A consolidation)** — Apply the same pattern to Stage A: inline helpers from `stage_a_impl.py` into `StageA` class and delete the impl module
2. **Phase D (Facade Removal)** — Migrate all `run_nanobrag_refinement` consumers to call `RefinementEngine` directly, then delete the monolithic facade
