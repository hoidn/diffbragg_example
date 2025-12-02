# Phase D Scope Summary — Facade Removal

**Initiative:** ARCH-REFACTOR-001 Phase D
**Planning Date:** 2025-12-02T201539Z
**Status:** Planning Complete, Ready for Implementation

## Executive Summary

**Goal:** Migrate all consumers from `run_nanobrag_refinement()` facade (~656 lines) to direct `RefinementEngine` usage, then delete the monolithic `dbex/nanobrag_refinement.py` file.

**Rationale:** Phase C completed Exit Criterion #1 (all `*_impl.py` deleted). Phase D completes Exit Criterion #2 (facade deleted), establishing RefinementEngine as the sole refinement path.

## Scope

### In-Scope (6 Production/Test + 1 Tooling Consumers)

**Production:**
1. `dbex/refine_one.py` — CLI entry point (1 call site)

**Test:**
2. `tests/dbex/test_torch_refine_smoke.py` — Stage A/B/C acceptance tests (6 functions, 6 call sites)
3. `tests/dbex/test_stage_a_smoke_parity.py` — Mapping parity test (1 function, 1 call site)
4. `tests/dbex/test_refinement_engine.py` — Engine tests (config-only, 2 imports)
5. `tests/dbex/test_stage_b_cpu_fallback.py` — Stage B CPU fallback (config-only, 3 imports)
6. `tests/dbex/test_physics_loss_current.py` — Physics loss tests (legacy helper import, 4 imports)

**Tooling:**
7. `dbex/tools/stage_a_adam.py` — Debug tooling (1 call site)

**Infrastructure:**
8. `dbex/refinement/__init__.py` — Module export (config re-export)

### Out-of-Scope

- **Research probes:** `plans/active/*/bin/*.py` (8 files) — Ad-hoc benchmarks/probes under active initiatives. Can break temporarily; migrate opportunistically.
- **Documentation:** `docs/*.md`, `logs/*.md`, `repomix-output.xml` — Update references in next doc refresh cycle.
- **Historical artifacts:** `galph_memory.md`, archived logs — Read-only, no action needed.

## Five-Phase Migration Plan

### Phase D.1: RefinementConfig Migration
**Deliverable:** New module `dbex/refinement/config.py` with RefinementConfig dataclass relocated from facade

**Files touched:** 1 created, 8 updated (imports)

**Validation:**
- Static checks (no ImportError)
- Config-only consumers (test_refinement_engine.py, test_stage_b_cpu_fallback.py)
- CLI smoke test (facade re-export bridge)

**Risk:** LOW (pure dataclass, no logic)

### Phase D.2: CLI Refactor (Critical Path)
**Deliverable:** `dbex/refine_one.py` migrated from facade to RefinementEngine instantiation

**Pattern:**
```python
refinement_context = build_refinement_context(...)
stages = [StageA()]
if config.enable_stage_b: stages.append(StageB())
if config.enable_stage_c: stages.append(StageC())
engine = RefinementEngine(stages, config)
telemetry_dict = engine.run({"context": refinement_context})
artifacts = engine._artifacts
Bragg_refined = artifacts["stage_c" or "stage_b" or "stage_a"].bragg_full
```

**Files touched:** 1 (refine_one.py)

**Validation:**
- CLI smoke tests (test_refine_one_cli.py: 2 tests)
- HDF5 output structure preserved (backward compatible)

**Risk:** MEDIUM (production entry point)

### Phase D.3: Test Harness Migration
**Deliverable:** `test_torch_refine_smoke.py` (6 functions) and `test_stage_a_smoke_parity.py` (1 function) migrated to Engine pattern

**Files touched:** 2 (test harness files)

**Validation:**
- All 6 Stage A/B/C smoke selectors (test_stage_a_expansion, test_stage_b_shell_modifiers, test_stage_c_detector_microslip, etc.)
- Parity test (test_stage_a_mapping_to_refine_roundtrip)

**Risk:** MEDIUM (core acceptance tests)

### Phase D.4: Import Cleanup
**Deliverable:** Fix remaining legacy imports (tooling + test bugfix)

**Files touched:** 2
- `dbex/tools/stage_a_adam.py` — Migrate to Engine + fix quaternion helper imports
- `tests/dbex/test_physics_loss_current.py` — Redirect `_compute_variance_weighted_loss` import from facade to `dbex.physics.loss`

**Validation:**
- Tooling tests (test_stage_a_adam_tooling.py: 8 tests)
- Physics loss tests (test_physics_loss_current.py: 4 tests)

**Risk:** LOW (import path fixes only)

### Phase D.5: Facade Deletion
**Deliverable:** Delete `dbex/nanobrag_refinement.py` after comprehensive verification

**Pre-deletion checks:**
1. Zero remaining imports (excluding docs/logs/archive)
2. Zero remaining call sites (excluding research probes)
3. Static imports succeed
4. Test collection clean

**Post-deletion checks:**
1. Static imports succeed (repeat)
2. CLI smoke test
3. Stage A/B/C smokes (3 tests)
4. Full test suite (20+ tests)
5. Test collection clean (repeat)

**Rollback plan:** `git checkout HEAD -- dbex/nanobrag_refinement.py` if any check fails

**Risk:** HIGH (irreversible, requires comprehensive verification)

## Key Design Decisions

### RefinementConfig Relocation: Option A (New Module)
**Decision:** Create `dbex/refinement/config.py` instead of inlining to `context.py`

**Rationale:**
- Separation of concerns (config vs runtime context)
- Size management (context.py already ~950 lines)
- Future-proof (config likely to grow)
- Naming clarity (`dbex.refinement.config.RefinementConfig` self-documenting)

### Engine Pattern (from CLI Blueprint)
**Core contracts:**
1. Build `RefinementContext` with `build_refinement_context()`
2. Instantiate stages list based on config flags
3. Run `engine.run({"context": refinement_context})`
4. Extract artifacts from `engine._artifacts`
5. Extract final Bragg from terminal stage (C > B > A)

**This pattern is the reference for all test migrations.**

## Success Metrics

### Code Metrics
- **File deleted:** `dbex/nanobrag_refinement.py` (~656 lines)
- **Net change:** -656 lines (facade removed)
- **Consumers migrated:** 7 files (1 CLI + 5 tests + 1 tooling)
- **Import updates:** ~20 inline imports redirected
- **Engine adoption:** 10 call sites migrated

### Validation Metrics
- **Tests run:** 20+ (CLI + Stage smokes + Engine + Tooling + Physics)
- **Gate:** All PASSED (excluding documented xfail/skip)
- **Static checks:** 7 import checks PASSED
- **Collection:** No ImportError, all tests discoverable

### Architecture Metrics
- **Exit Criterion #1:** ✅ Complete (Phase C: all `*_impl.py` deleted)
- **Exit Criterion #2:** ✅ Complete (Phase D: facade deleted)
- **Code paths:** 1 (Engine only; facade eliminated)
- **Module separation:** Config / Engine / Stages cleanly separated

## Dependencies & Blocking

**Depends on:**
- Phase C.9 complete (all `*_impl.py` deleted)
- RefinementEngine proven operational (ARCH-REFINE-FLOW-001)
- Context builders available (ARCH-STAGE-CONTEXT-001)

**Blocks:**
- Phase E (Legacy Isolation, if needed)
- ARCH-REFACTOR-001 initiative completion

**Unblocks:**
- Future Stage extensions (Stage D, E) without touching monolithic facade
- Cleaner architecture for SPEC-REALIGN-001 work

## Risk Summary

**Overall Risk:** MEDIUM-HIGH (production CLI + irreversible deletion)

**Mitigation strategies:**
1. **Incremental migration:** D.1 → D.2 → D.3 → D.4 → D.5 (validate each before proceeding)
2. **CLI-first approach:** Validate production entry point (D.2) before test harness (D.3)
3. **Comprehensive verification:** 12-step deletion checklist (pre + post checks)
4. **Rollback plan:** Git revert if any verification fails
5. **Test coverage:** 20+ tests across all touched files

## Artifacts

All planning artifacts live under:
`plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/`

**Planning deliverables:**
1. ✅ `consumer_inventory.txt` — Raw grep output
2. ✅ `consumer_analysis.md` — Categorized consumer list
3. ✅ `config_migration_plan.md` — RefinementConfig relocation strategy
4. ✅ `cli_refactor_blueprint.md` — Detailed refine_one.py migration pattern
5. ✅ `test_migration_plan.md` — Per-file test migration strategy
6. ✅ `deletion_checklist.md` — 12-step verification procedure
7. ✅ `phase_d_scope.md` — This summary

**Implementation artifacts (future loops):**
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/` (D.1-D.5 implementation timestamps)
- Pytest logs for each validation step
- `summary.md` for each implementation loop

## Next Steps

1. **Update implementation.md:** Add Phase D checklist (D.1-D.5) with mapped tests and artifacts paths
2. **Notify supervisor:** Update `galph_memory.md` that Phase D planning is complete and ready for implementation
3. **Implementation sequence:** Execute D.1 → D.2 → D.3 → D.4 → D.5 in order, validating each before proceeding
4. **Final sign-off:** Mark ARCH-REFACTOR-001 `done` after Phase D.5 passes all 12 verification steps

## Exit Criteria

Phase D (and ARCH-REFACTOR-001 initiative) is **complete** when:
1. ✅ RefinementConfig lives in `dbex/refinement/config.py`
2. ✅ CLI uses RefinementEngine directly (no facade calls)
3. ✅ All tests use RefinementEngine directly (no facade calls)
4. ✅ `dbex/nanobrag_refinement.py` deleted
5. ✅ All validation tests PASSED (20+ tests)
6. ✅ No remaining facade imports (excluding docs/logs/archive/probes)
7. ✅ Exit Criteria #1 + #2 both satisfied

**Status after Phase D complete:**
- ARCH-REFACTOR-001: `done`
- Next initiative: Consider Phase E (Legacy Isolation) or close initiative per supervisor guidance
