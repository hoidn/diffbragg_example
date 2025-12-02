# ARCH-REFACTOR-001 Phase D Planning Notes
**Timestamp:** 2025-12-02T201539Z
**Loop:** i=433 (Galph supervisor review)

## Context

Phase C is COMPLETE. Exit Criterion #1 fully satisfied:
- ✅ stage_a_impl.py deleted (commit 9e45812b)
- ✅ stage_b_impl.py deleted (commit ee3f7fc8)
- ✅ stage_c_impl.py deleted (commit f5ac1a01)

All Stage logic now lives within StageA/StageB/StageC classes. Helpers are extracted to:
- `dbex/refinement/stage_a_utils.py` (cross-stage quaternion/warm-cache/context helpers)
- `dbex/refinement/hkl_utils.py` (ASU/shell utilities for Stage B)
- `dbex/refinement/context.py` (all Stage dataclasses: StageAContext, StageCContext, StageAROIEntry, etc.)

## Phase D Goal

**Facade Removal:** Migrate all consumers from `run_nanobrag_refinement` (dbex/nanobrag_refinement.py:202-656) to `RefinementEngine` directly, then delete the monolithic facade.

This achieves Exit Criterion #2: "`dbex/nanobrag_refinement.py` is deleted"

## Scope Analysis

### Current Consumers of `run_nanobrag_refinement`:

1. **dbex/refine_one.py** (line 505, 546):
   - `from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig`
   - Calls `run_nanobrag_refinement(...)` within `run_nanobrag_backend()`
   - Returns `(Bragg_refined, refine_telemetry_dict, engine_artifacts)`

2. **tests/dbex/test_torch_refine_smoke.py** (5 test functions):
   - Imports `run_nanobrag_refinement` for Stage A/B/C smokes
   - Used in: `test_stage_a_expansion`, `test_stage_a_engine_delegation_telemetry`, `test_stage_b_shell_modifiers`, `test_stage_c_detector_microslip`

3. **tests/dbex/test_stage_a_smoke_parity.py**:
   - Imports multiple helpers from dbex.nanobrag_refinement (old pattern)

4. **tests/dbex/test_refinement_engine.py**:
   - Imports `RefinementConfig` from dbex.nanobrag_refinement

5. **tests/dbex/test_stage_b_cpu_fallback.py** (3 functions):
   - Imports `RefinementConfig` for parity guard tests

6. **tests/dbex/test_physics_loss_current.py** (4 functions):
   - Imports `_compute_variance_weighted_loss` from dbex.nanobrag_refinement (should use dbex.physics.loss)

### What Needs to Happen:

#### D.1 — Move RefinementConfig
- **From:** `dbex/nanobrag_refinement.py::RefinementConfig` dataclass (lines 73-124)
- **To:** `dbex/refinement/config.py` (new module) OR inline into `dbex/refinement/context.py`
- **Why:** Config is reusable scaffolding, not facade logic
- **Impact:** Update all imports (6 files)

#### D.2 — CLI Migration (refine_one.py)
- **Task:** Refactor `run_nanobrag_backend()` to:
  1. Build `JobContext` and `RefinementContext` from args/DL
  2. Instantiate `RefinementEngine(StageA, StageB, StageC)`
  3. Call `engine.run(inputs)` directly
  4. Extract results from returned artifacts
- **Validation:** Run CLI smoke tests (test_torch_diagnostics_metadata, test_nanobrag_backend_runs_simulator)

#### D.3 — Test Harness Migration
- **Task:** Update test fixtures in `test_torch_refine_smoke.py` to use `RefinementEngine` instead of `run_nanobrag_refinement`
- **Files:** tests/dbex/test_torch_refine_smoke.py (5 test functions)
- **Validation:** Rerun all mapped selectors (Stage A expansion/telemetry, Stage B shell, Stage C microslip)

#### D.4 — Cleanup Old Imports
- **Task:** Fix stale imports in tests:
  - `test_physics_loss_current.py`: change `_compute_variance_weighted_loss` import to `dbex.physics.loss`
  - `test_stage_a_smoke_parity.py`: update to use new module paths
  - `test_refinement_engine.py`, `test_stage_b_cpu_fallback.py`: update `RefinementConfig` imports

#### D.5 — Delete Facade
- **Task:** After all consumers are migrated and validated, delete `dbex/nanobrag_refinement.py` (~656 lines)
- **Verification:** `rg "from.*nanobrag_refinement|import.*nanobrag_refinement" --type py` must return empty (excluding docs/logs/backups)

## Risk Assessment

**Low Risk:**
- RefinementEngine is already proven via ARCH-REFINE-FLOW-001 (all Stage smokes pass using Engine path)
- Phase C consolidation means Engine consumers have stable, well-tested Stage interfaces
- Config migration is straightforward (pure dataclass move)

**Medium Risk:**
- CLI refactor touches production path (refine_one.py), but test coverage is solid
- Test harness changes require updating 5+ test functions, potential for missed edge cases

**Mitigation:**
- **Incremental:** Do D.1-D.2 in one loop, D.3-D.4 in second loop, D.5 only after full validation
- **Rollback-friendly:** Keep facade file until final loop, so any blocker can revert cleanly
- **Test-first:** Map full selector suite (CLI + Stage smokes) before deletion

## Next Actions (for input.md)

**Loop i=434 (Next):** Phase D.1-D.2 planning + implementation prep
- **Action Type:** planning
- **Mode:** Parity (preserve exact telemetry/HDF5 schema)
- **Deliverables:**
  1. Relocate `RefinementConfig` to `dbex/refinement/config.py`
  2. Draft CLI refactor plan with explicit RefinementContext/JobContext builders
  3. Identify all RefinementConfig import sites and update them
  4. Reserve artifacts directory for upcoming implementation loop

**Loop i=435 (Projected):** Phase D.1-D.2 implementation
- **Action Type:** implementation
- **Mapped Tests:**
  - `test_torch_diagnostics_metadata` (CLI HDF5 schema validation)
  - `test_nanobrag_backend_runs_simulator` (CLI simulator invocation)
  - `test_stage_a_expansion` (Engine path validation)
- **Artifacts:** pytest logs, CLI diff comparison (telemetry before/after)

**Loop i=436 (Projected):** Phase D.3-D.4 (test harness migration)

**Loop i=437 (Projected):** Phase D.5 (facade deletion + final verification)

## Dependencies

- **Blocking:** None (Phase C complete, Engine proven)
- **Blocked By:** None
- **Parallel Work:** ARCH-TELEMETRY-001 can continue in parallel (observer refactor is orthogonal to facade removal)

## Compliance

- **Spec:** docs/spec-db-workflow.md §§30-41 (Staging policy remains unchanged)
- **Finding:** ARCH-ENGINE-002 (Protocol Engine compliance, already satisfied by ARCH-REFINE-FLOW-001)
- **Initiative Type:** architecture (no spec changes, pure refactor)

## Expected Metrics

- Files deleted: 1 (dbex/nanobrag_refinement.py, ~656 lines)
- Files created: 1 (dbex/refinement/config.py, ~60 lines for RefinementConfig)
- Files modified: ~8 (refine_one.py, 5 test files, 2 other tests)
- Net change: -550 to -600 lines across repo
- Import verification: `rg "nanobrag_refinement"` returns only docs/logs/archive references
