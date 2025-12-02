# Ralph Input — Loop i=434

## Summary
Plan Phase D (Facade Removal): migrate CLI + tests from `run_nanobrag_refinement` to `RefinementEngine` and prepare for deletion of `dbex/nanobrag_refinement.py`.

## Mode
none

## InitiativeType
architecture

## Focus
ARCH-REFACTOR-001 Phase D.1 — Facade Removal Planning

## Branch
integration

## Mapped tests
- `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
- `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/`

## Do Now

### Context

**Phase C COMPLETE (Exit Criterion #1 Satisfied):**
All `*_impl.py` modules have been deleted:
- ✅ stage_c_impl.py (commit f5ac1a01)
- ✅ stage_b_impl.py (commit ee3f7fc8)
- ✅ stage_a_impl.py (commit 9e45812b)

All Stage logic now lives in StageA/StageB/StageC classes. Helpers are extracted to:
- `dbex/refinement/stage_a_utils.py` (cross-stage utilities)
- `dbex/refinement/hkl_utils.py` (ASU/shell utilities)
- `dbex/refinement/context.py` (all Stage dataclasses)

**Next Milestone: Phase D (Facade Removal)**

`RefinementEngine` is proven and operational (ARCH-REFINE-FLOW-001). The monolithic facade `dbex/nanobrag_refinement.py` (~656 lines) still exists for backward compatibility but is no longer needed now that Stages are self-contained.

**Phase D Goal:** Migrate all consumers from `run_nanobrag_refinement()` to `RefinementEngine` and delete the facade, achieving Exit Criterion #2.

### Planning Steps

This is a **planning-only** loop. No production code changes. Produce detailed planning artifacts for the upcoming implementation loops.

**Step 1: Consumer Inventory**

Perform a comprehensive audit of all `run_nanobrag_refinement` consumers:

```bash
# Find all imports
rg "from.*nanobrag_refinement import|import.*nanobrag_refinement" --type py > plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/consumer_inventory.txt

# Find all call sites
rg "run_nanobrag_refinement\(" --type py >> plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/consumer_inventory.txt
```

Document in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/consumer_analysis.md`:
- File path + line number for each import
- What is being imported (run_nanobrag_refinement, RefinementConfig, helpers, etc.)
- Classification: Production (refine_one.py) vs Test (test_*.py) vs Tooling (tools/*.py)

**Step 2: RefinementConfig Migration Plan**

`RefinementConfig` dataclass (dbex/nanobrag_refinement.py:73-124) is reusable scaffolding, not facade logic. Decision matrix:

Option A: Move to `dbex/refinement/config.py` (new module)
- Pros: Clean separation, future-proof for additional configs
- Cons: One more file

Option B: Inline into `dbex/refinement/context.py`
- Pros: Fewer files, config lives near contexts
- Cons: context.py is already large (~900+ lines)

**Recommendation:** Option A (new module). Document rationale in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/config_migration_plan.md`.

List all RefinementConfig import sites and update strategy.

**Step 3: CLI Refactor Blueprint**

Draft detailed implementation plan for `dbex/refine_one.py::run_nanobrag_backend()` refactor:

**Current pattern** (line 505-546):
```python
from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig
...
Bragg_refined, refine_telemetry_dict, engine_artifacts = run_nanobrag_refinement(...)
```

**Target pattern:**
```python
from dbex.refinement.config import RefinementConfig
from dbex.refinement.engine import RefinementEngine
from dbex.refinement.stage_a import StageA
from dbex.refinement.stage_b import StageB
from dbex.refinement.stage_c import StageC
from dbex.refinement.inputs import prepare_refinement_inputs
from dbex.refinement.context import build_refinement_context, build_job_context

# Build typed contexts
refinement_inputs = prepare_refinement_inputs(...)
job_context = build_job_context(...)
refinement_context = build_refinement_context(...)

# Instantiate Engine
engine = RefinementEngine(StageA, StageB, StageC)

# Run refinement
inputs = {"context": refinement_context, ...}
artifacts = engine.run(inputs)

# Extract results
Bragg_refined = artifacts["final_bragg"]  # or similar
refine_telemetry_dict = artifacts["telemetry"].to_dict()
```

Document in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/cli_refactor_blueprint.md`:
1. Exact imports to add/remove
2. Context builders: which args map to JobContext vs RefinementContext fields
3. Engine inputs dict structure
4. Artifact extraction logic (final Bragg, telemetry, stage results)
5. Validation plan: which CLI tests prove the refactor is correct

**Step 4: Test Harness Migration Plan**

For each test file importing `run_nanobrag_refinement`, document the migration strategy:

**tests/dbex/test_torch_refine_smoke.py** (5 functions):
- `test_stage_a_expansion`
- `test_stage_a_engine_delegation_telemetry`
- `test_stage_b_shell_modifiers`
- `test_stage_c_detector_microslip`
- Migration: Replace `run_nanobrag_refinement()` calls with `RefinementEngine.run()` per CLI blueprint pattern
- Validation: Rerun all 4 selectors, ensure telemetry/Bragg outputs identical

**tests/dbex/test_refinement_engine.py**:
- Only imports `RefinementConfig` → update to `dbex.refinement.config`

**tests/dbex/test_stage_b_cpu_fallback.py** (3 functions):
- Only imports `RefinementConfig` → update to `dbex.refinement.config`

**tests/dbex/test_physics_loss_current.py** (4 functions):
- BUG: Imports `_compute_variance_weighted_loss` from `dbex.nanobrag_refinement`
- FIX: Change to `dbex.physics.loss` (canonical source)

**tests/dbex/test_stage_a_smoke_parity.py**:
- Audit: may import old helpers that are now in stage_a_utils/hkl_utils
- Update: migrate to new module paths

Document each file's migration steps in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/test_migration_plan.md`.

**Step 5: Deletion Verification Plan**

After all consumers are migrated, the facade can be deleted. Verification checklist:

1. Import verification:
   ```bash
   rg "from.*nanobrag_refinement import|import.*nanobrag_refinement" --type py
   ```
   Expected: Empty output (excluding docs/logs/backups/archive)

2. Call verification:
   ```bash
   rg "run_nanobrag_refinement\(" --type py
   ```
   Expected: Empty output (excluding docs/logs/backups/archive)

3. Module dependency check:
   ```bash
   python -c "import dbex.refine_one; import dbex.refinement.engine"
   ```
   Expected: No ImportError

4. Full test suite:
   ```bash
   # CLI smokes
   pytest -vv tests/dbex/test_refine_one_cli.py

   # Stage smokes
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
   ```
   Expected: All PASSED

Document in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/deletion_checklist.md`.

**Step 6: Update Implementation Plan**

Update `plans/active/ARCH-REFACTOR-001/implementation.md`:
1. Mark Phase C.9 complete (already done in prior loop)
2. Add Phase D checklist with 5 subtasks:
   - D.1: RefinementConfig migration
   - D.2: CLI refactor (refine_one.py)
   - D.3: Test harness migration (test_torch_refine_smoke.py + others)
   - D.4: Cleanup old imports (test_physics_loss_current.py bugfix, etc.)
   - D.5: Facade deletion + verification

Each subtask should reference its planning artifact and list mapped tests.

**Step 7: Reserve Future Artifacts Directories**

Create placeholder directories for upcoming implementation loops:

```bash
mkdir -p plans/active/ARCH-REFACTOR-001/reports/2025-12-02T{210000,220000,230000}Z
```

(Adjust timestamps as needed for actual loop execution times)

### Deliverables

At the end of this planning loop, the following artifacts must exist under `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/`:

1. `consumer_inventory.txt` — Raw grep output of all nanobrag_refinement imports/calls
2. `consumer_analysis.md` — Categorized consumer list with migration priority
3. `config_migration_plan.md` — RefinementConfig relocation decision + rationale
4. `cli_refactor_blueprint.md` — Detailed refine_one.py refactor steps
5. `test_migration_plan.md` — Per-file test migration strategy
6. `deletion_checklist.md` — Final verification steps before facade deletion
7. `phase_d_scope.md` — High-level Phase D summary for docs/fix_plan.md

Additionally:
- Update `plans/active/ARCH-REFACTOR-001/implementation.md` with Phase D checklist
- Create summary in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/summary.md`

## How-To Map

**Task:** Comprehensive Phase D planning

1. **Consumer Inventory:**
   - Run: `rg "from.*nanobrag_refinement import|import.*nanobrag_refinement" --type py > plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/consumer_inventory.txt`
   - Run: `rg "run_nanobrag_refinement\(" --type py >> plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/consumer_inventory.txt`
   - Analyze output and write `consumer_analysis.md`

2. **Config Migration Decision:**
   - Read current `RefinementConfig` (dbex/nanobrag_refinement.py:73-124)
   - Evaluate Option A (new config.py) vs Option B (inline to context.py)
   - Write `config_migration_plan.md` with recommendation

3. **CLI Blueprint:**
   - Read current `run_nanobrag_backend()` (dbex/refine_one.py:277-...)
   - Map args to JobContext/RefinementContext fields
   - Draft Engine instantiation + invocation pattern
   - Write `cli_refactor_blueprint.md`

4. **Test Migration Strategy:**
   - For each test file in consumer inventory:
     - Classify: config-only import vs full facade usage
     - Draft migration steps
   - Write `test_migration_plan.md`

5. **Deletion Checklist:**
   - List verification commands
   - Define success criteria
   - Write `deletion_checklist.md`

6. **Implementation Plan Update:**
   - Edit `plans/active/ARCH-REFACTOR-001/implementation.md`
   - Add Phase D section with 5 subtasks (D.1-D.5)
   - Link each subtask to planning artifacts

7. **Summary:**
   - Write `phase_d_scope.md` (high-level overview for fix_plan.md)
   - Write `summary.md` (Turn Summary format per end_of_loop_hygiene)

## Pitfalls To Avoid

1. **No production code changes:** This is a planning-only loop. Do not edit refine_one.py, tests, or nanobrag_refinement.py. Only create planning artifacts and update implementation.md.

2. **Environment Freeze:** Do not run tests or execute code. Planning analysis only. Test execution happens in implementation loops.

3. **Initiative Type Boundaries:** This is an `architecture` initiative (pure refactor). Do not propose spec changes, gate adjustments, or telemetry schema modifications.

4. **Protected Assets:** RefinementEngine, StageA/B/C classes, and context builders are proven and stable (ARCH-REFINE-FLOW-001). Do not propose changes to those modules; only show how to use them.

5. **Missing Artifacts:** All 7 planning deliverables must exist before ending the loop. Missing artifacts block the next implementation loop.

6. **Incomplete Consumer Inventory:** Must catalog ALL imports, not just obvious ones. Use grep/rg exhaustively.

7. **Vague Migration Steps:** CLI blueprint must be implementation-ready (exact imports, exact context builder calls, exact artifact extraction). No hand-waving.

## If Blocked

If consumer inventory reveals unexpected dependencies or edge cases:

1. Capture the blocker in `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/blockers.md`
2. Note which deliverable is blocked and why
3. Update fix_plan.md Attempts History with blocker details
4. Return control to Galph for triage
5. Do NOT proceed with incomplete planning

## Findings Applied

**Mandatory:**
- ARCH-REFACTOR-001: Exit Criterion #1 satisfied (all *_impl.py deleted); Exit Criterion #2 pending (facade deletion)
- ARCH-REFINE-FLOW-001: RefinementEngine proven operational, Stage wrappers validated
- ARCH-STAGE-CONTEXT-001: Context builders (`build_refinement_context`, `build_job_context`) are canonical
- ARCH-ENGINE-002: Engine protocol compliance enforced

**No relevant findings in the knowledge base:** All relevant findings listed above.

## Pointers

- Implementation Plan: `plans/active/ARCH-REFACTOR-001/implementation.md` (Phase C complete, Phase D to be added)
- Exit Criteria: `docs/fix_plan.md` (ARCH-REFACTOR-001, lines 57-62 — facade deletion is #2)
- Phase C.9 completion: `docs/fix_plan.md` line 80 (stage_a_impl deleted, 2025-12-02T235959Z)
- RefinementEngine: `dbex/refinement/engine.py` (proven via ARCH-REFINE-FLOW-001)
- Context builders: `dbex/refinement/context.py` (build_refinement_context, build_job_context)
- Spec: `docs/spec-db-workflow.md` §§30-41 (Staging policy unchanged)
- Testing Guide: `docs/TESTING_GUIDE.md` (canonical env flags, CLI + Stage smoke selectors)

## Next Up

After Phase D planning (this loop), the sequence is:

1. **Loop i=435:** Phase D.1 + D.2 implementation (RefinementConfig migration + CLI refactor)
2. **Loop i=436:** Phase D.3 + D.4 implementation (Test harness migration + import cleanup)
3. **Loop i=437:** Phase D.5 implementation (Facade deletion + full verification)

Then move to Phase E (Legacy Isolation) if needed, or mark ARCH-REFACTOR-001 **done** once Exit Criteria #1 and #2 are both satisfied.
