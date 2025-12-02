# Ralph Input — Loop i=432

## Summary
Delete `dbex/refinement/stage_a_impl.py` by relocating remaining dataclasses to `context.py` and updating imports.

## Mode
Parity

## InitiativeType
architecture

## Focus
ARCH-REFACTOR-001 Phase C.9 — Stage A Module Deletion

## Branch
integration

## Mapped tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry`
- `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`
- `tests/dbex/test_refgeom_integration.py::test_refgeom_integration`

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/`

## Do Now

### Context
Phase C.8 completed (commit 937f47d4): all Stage A private helpers (_sync_stage_a_crystal, _build_stage_a_params, _run_stage_a_lbfgs) have been inlined into the StageA class. Phase C.7 already extracted cross-stage helpers (quaternion utils, warm-cache helpers, loss/context builders) to `stage_a_utils.py`.

Only two dataclasses remain in `stage_a_impl.py`:
- `StageAROIEntry` (~15-20 lines)
- `StageAContext` (~30-40 lines)

These belong in `dbex/refinement/context.py` per ARCH-STAGE-CONTEXT-001 precedent (StageCContext was added there in Phase C.1).

### Implementation Steps

**Step 1: Relocate dataclasses to context.py**

1. Open `dbex/refinement/stage_a_impl.py` and locate `class StageAROIEntry:` and `class StageAContext:` definitions (search for `@dataclass` decorators).

2. Copy both complete dataclass definitions (including decorators, docstrings, all fields with type hints and defaults) to `dbex/refinement/context.py`.

3. Place them near other Stage contexts for consistency:
   - Find `class StageATelemetryState:` or `class StageCContext:` in context.py
   - Insert StageAROIEntry and StageAContext either after StageATelemetryState or before/after StageCContext

4. Ensure required imports are present at the top of `context.py`:
   - `import torch` (if not already present)
   - `from typing import Optional, List, Tuple, Callable` (add any missing types)
   - `from nanobrag_torch.simulator import Simulator` (for StageAContext.roi_entries field)

5. Add a cross-reference comment above the dataclasses:
   ```python
   # ARCH-REFACTOR-001 Phase C.9: Relocated from stage_a_impl.py (2025-12-02T235959Z)
   ```

**Step 2: Update all import sites (5 files)**

1. **dbex/refinement/stage_a_utils.py** (line ~28):
   - Find: `from dbex.refinement.stage_a_impl import StageAContext, StageAROIEntry`
   - Replace: `from dbex.refinement.context import StageAContext, StageAROIEntry`

2. **dbex/refinement/stage_c.py** (line ~42):
   - Find: `from dbex.refinement.stage_a_impl import StageAContext`
   - Replace: `from dbex.refinement.context import StageAContext`

3. **dbex/refinement/stage_a.py** (two import locations):
   - **Line ~39 (module-scope import):** BUGFIX - change:
     * Find: `from dbex.refinement.stage_a_impl import (_compute_variance_weighted_loss,)` or similar
     * Replace: `from dbex.physics.loss import _compute_variance_weighted_loss`
     * Reason: stage_a_impl re-exports this from physics.loss; import from the correct source

   - **Line ~1248 (inline import inside _build_lbfgs_closure):**
     * Find: `from dbex.refinement.stage_a_impl import StageAContext`
     * Replace: `from dbex.refinement.context import StageAContext`

4. **dbex/nanobrag_refinement.py** (lines ~58-62):
   - Find the import block importing quaternion helpers from `stage_a_impl`:
     ```python
     from dbex.refinement.stage_a_impl import (
         vec_to_unit_quaternion,
         quaternion_to_rotation_matrix,
         quaternion_to_xyz_euler,
     )
     ```
   - Replace with:
     ```python
     from dbex.refinement.stage_a_utils import (
         vec_to_unit_quaternion,
         quaternion_to_rotation_matrix,
         quaternion_to_xyz_euler,
     )
     ```

5. **dbex/tools/stage_a_adam.py** (lines ~22-25):
   - Same change as above: import quaternion helpers from `stage_a_utils` instead of `stage_a_impl`

**Step 3: Verify no remaining imports**

Run this command to verify zero remaining imports (excluding docs/logs/backups):
```bash
rg "from.*stage_a_impl import|import.*stage_a_impl" --type py | grep -v "docs/" | grep -v "\.log" | grep -v "backup" > plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/remaining_imports.txt
```

The output file should be empty. If not, update any remaining imports following the same pattern as Step 2.

**Step 4: Delete stage_a_impl.py**

If verification passes:
```bash
rm dbex/refinement/stage_a_impl.py
```

**Step 5: Validation**

Run all 6 mapped selectors with canonical environment flags and capture logs:

```bash
# Stage A expansion
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small 2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/pytest_stage_a_expansion.log

# Stage A engine delegation telemetry
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry 2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/pytest_stage_a_telemetry.log

# Stage B guard
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload 2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/pytest_stage_b_guard.log

# Stage B shell
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small 2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/pytest_stage_b_shell.log

# Stage C smoke
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small 2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/pytest_stage_c_smoke.log

# Reconstruction integration
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refgeom_integration.py::test_refgeom_integration 2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/pytest_refgeom_integration.log
```

All 6/6 tests must PASS.

## How-To Map

**Task:** Relocate dataclasses and update imports

1. **Relocate dataclasses:**
   - Source: `dbex/refinement/stage_a_impl.py` (StageAROIEntry, StageAContext)
   - Destination: `dbex/refinement/context.py` (near StageATelemetryState or StageCContext)
   - Verify: Check that all field type hints and defaults are preserved

2. **Update imports (5 files):**
   - stage_a_utils.py: stage_a_impl → context (dataclasses)
   - stage_c.py: stage_a_impl → context (StageAContext only)
   - stage_a.py: Fix bug (physics.loss import) + update inline import (dataclass)
   - nanobrag_refinement.py: stage_a_impl → stage_a_utils (quaternion helpers)
   - tools/stage_a_adam.py: stage_a_impl → stage_a_utils (quaternion helpers)

3. **Verification:**
   - Run: `rg "from.*stage_a_impl import|import.*stage_a_impl" --type py | grep -v docs/ | grep -v log | grep -v backup`
   - Expected: Empty output (no remaining imports)

4. **Deletion:**
   - Delete: `dbex/refinement/stage_a_impl.py` (~1524 lines)
   - Confirm: File deletion reduces total codebase by ~1450-1470 lines

5. **Validation:**
   - Run all 6 mapped selectors (see Do Now Step 5)
   - Expected: 6/6 PASSED
   - Capture: All pytest logs under artifacts directory

## Pitfalls To Avoid

1. **Incomplete dataclass copy:** Ensure you copy the complete `@dataclass` decorator, all field definitions with type hints, all default values (including `field(default_factory=...)` patterns), and any docstrings. Do not truncate or modify field definitions.

2. **Missing imports in context.py:** After adding dataclasses to `context.py`, verify that `torch`, `Simulator`, and all typing imports (`Optional`, `List`, `Tuple`, `Callable`) are present at module scope. Missing imports will cause immediate ImportError.

3. **Incorrect import source for _compute_variance_weighted_loss:** In `stage_a.py`, this MUST be imported from `dbex.physics.loss`, not `stage_a_impl`. The impl file only re-exports it; the canonical source is physics.loss per Phase A (2025-11-24T074500Z).

4. **Partial import updates:** All 5 files MUST be updated. Missing even one will leave a broken import chain. Use the verification step (Step 3) to catch any missed imports.

5. **Protected Assets:** Do not modify LBFGS closure logic, telemetry collector paths, warm-cache semantics, or device/dtype handling. This is a pure refactor (moving definitions, updating imports). No behavioral changes.

6. **Deleting stage_a_impl.py too early:** Only delete the file AFTER Step 2 (all imports updated) AND Step 3 (verification passes). Deleting prematurely will break imports.

7. **Forgetting inline imports:** `stage_a.py` has an inline import of `StageAContext` inside `_build_lbfgs_closure` method (around line 1248). This must be updated in addition to the module-scope import.

8. **Initiative type boundaries:** This is an `architecture` initiative (module consolidation). Do not introduce spec changes, gate adjustments, or telemetry schema modifications.

## If Blocked

If any test fails or imports cannot be resolved:

1. Capture the failure signature in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/failure_signature.txt`
2. Note which step failed (dataclass relocation, import update, verification, deletion, validation)
3. Update fix_plan.md Attempts History with the failure details
4. Do NOT proceed with deletion if verification or tests fail
5. Return control to Galph for triage

## Findings Applied

**Mandatory:**
- ARCH-REFACTOR-001: Refinement Engine Modularization (Stage A impl deletion is Exit Criterion #1)
- ARCH-STAGE-CONTEXT-001: Typed context dataclasses live in `dbex/refinement/context.py` (StageCContext precedent)
- ARCH-LAZY-IMPORTS-001: Module-scope imports enforced (no inline imports except where documented)
- ARCH-ENGINE-002: Stage wrappers remain canonical seam (no logic changes in this refactor)

**No relevant findings in the knowledge base:** N/A (all relevant findings listed above)

## Pointers

- Implementation Plan: `plans/active/ARCH-REFACTOR-001/implementation.md` (Phase C.9, lines 295-335)
- Exit Criteria: `docs/fix_plan.md` (ARCH-REFACTOR-001, line 59 — stage_a_impl.py deletion)
- Phase C.7 completion: `docs/fix_plan.md` line 77 (stage_a_utils extraction, 2025-12-02T200000Z)
- Phase C.8 completion: `docs/fix_plan.md` line 78 (Stage A private helper inlining, 2025-12-04T215000Z)
- StageCContext precedent: `docs/fix_plan.md` line 66 (context.py as canonical home for Stage contexts)
- Spec: `docs/spec-db-workflow.md` §§30-41 (Staging policy, LBFGS optimizer)
- Testing Guide: `docs/TESTING_GUIDE.md` (canonical env flags, smoke selectors)

## Next Up

After Phase C.9 completion, Phase D (Facade Removal) will migrate all consumers from `run_nanobrag_refinement` to `RefinementEngine` and delete `dbex/nanobrag_refinement.py`, completing ARCH-REFACTOR-001 Exit Criterion #2.
