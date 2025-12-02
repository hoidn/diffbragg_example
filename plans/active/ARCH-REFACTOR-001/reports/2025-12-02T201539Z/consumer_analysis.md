# Phase D Consumer Analysis — nanobrag_refinement.py Migration

**Initiative:** ARCH-REFACTOR-001 Phase D (Facade Removal)
**Date:** 2025-12-02T201539Z
**Status:** Planning

## Executive Summary

`dbex/nanobrag_refinement.py` has 3 distinct consumer categories:
1. **Production** (1 file): `dbex/refine_one.py` — CLI entry point
2. **Test** (4 files): Main test harness files using facade
3. **Tooling** (1 file): `dbex/tools/stage_a_adam.py` — debug tooling

Total: **6 production/test/tooling consumers** requiring migration.

Additional consumers import **only** `RefinementConfig` dataclass (reusable scaffolding) or legacy helpers that should be redirected to canonical modules.

## Classification by Import Pattern

### Category A: Full Facade Consumers (run_nanobrag_refinement + RefinementConfig)
**Priority: HIGH** — These call the monolithic facade function

1. **dbex/refine_one.py:505** (Production)
   - Import: `run_nanobrag_refinement, RefinementConfig`
   - Call site: line 546 (within `run_nanobrag_backend()`)
   - Migration: **D.2 CLI Refactor** — Replace with RefinementEngine instantiation
   - Validation: `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`, `test_nanobrag_backend_runs_simulator`

2. **tests/dbex/test_torch_refine_smoke.py** (Test Harness)
   - 6 inline imports (lines 400, 749, 947, 1063, 1393, 1793)
   - 6 call sites (lines 436, 784, 983, 1103, 1444, 1865)
   - Functions:
     * `test_stage_a_expansion` (line 400/436)
     * `test_stage_a_engine_delegation_telemetry` (line 749/784)
     * `test_stage_b_shell_modifiers` (line 947/983)
     * `test_stage_c_detector_microslip` (line 1063/1103)
     * `test_stage_b_asu_mapping_smoke` (line 1393/1444)
     * `test_stage_c_stage_a_baseline_detector_dist` (line 1793/1865)
   - Migration: **D.3 Test Harness** — Convert to RefinementEngine calls per CLI blueprint
   - Validation: All 6 test selectors must PASS after migration

3. **tests/dbex/test_stage_a_smoke_parity.py:13** (Test Harness)
   - Import: `RefinementConfig, run_nanobrag_refinement` (plus legacy helpers)
   - Call site: line 148 (within `test_stage_a_mapping_to_refine_roundtrip`)
   - Note: Also imports legacy `build_structure_factor_grid` from `nanobrag_bridge` (already relocated to correct module)
   - Migration: **D.4 Import Cleanup** — Update imports + Engine call
   - Validation: `test_stage_a_mapping_to_refine_roundtrip`

4. **dbex/tools/stage_a_adam.py:1634** (Tooling)
   - Import: Multi-line import including `RefinementConfig, run_nanobrag_refinement` plus quaternion helpers
   - Call site: line 1684 (within `run_debug_refinement()`)
   - Note: Quaternion helpers already relocated to `stage_a_utils` in Phase C.7
   - Migration: **D.4 Import Cleanup** — Update imports to stage_a_utils + RefinementEngine
   - Validation: `tests/dbex/test_stage_a_adam_tooling.py` (8 tests)

### Category B: Config-Only Imports (RefinementConfig dataclass)
**Priority: MEDIUM** — These only import the dataclass, no facade dependency

5. **tests/dbex/test_refinement_engine.py** (Test)
   - 2 inline imports (lines 31, 148)
   - No call sites (tests RefinementEngine directly)
   - Migration: **D.1 Config Migration** — Update import to `dbex.refinement.config`
   - Validation: `pytest tests/dbex/test_refinement_engine.py` (2 tests)

6. **tests/dbex/test_stage_b_cpu_fallback.py** (Test)
   - 3 inline imports (lines 40, 183, 291)
   - No call sites (uses StageB class directly)
   - Migration: **D.1 Config Migration** — Update import to `dbex.refinement.config`
   - Validation: `pytest tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`

7. **dbex/refinement/__init__.py:15** (Module Export)
   - Conditional import for lazy loading
   - Migration: **D.1 Config Migration** — Update to import from `dbex.refinement.config`
   - Validation: Static check (no ImportError when importing `dbex.refinement`)

### Category C: Legacy Helper Imports (Deprecated Re-exports)
**Priority: LOW** — These import helpers already relocated to canonical modules

8. **tests/dbex/test_physics_loss_current.py** (Test)
   - 4 inline imports (lines 63, 125, 160, 207)
   - Import: `_compute_variance_weighted_loss`
   - **BUG:** Should import from `dbex.physics.loss` (canonical source, relocated in Phase A.3)
   - Migration: **D.4 Import Cleanup** — Change to `dbex.physics.loss`
   - Validation: `pytest tests/dbex/test_physics_loss_current.py` (4 tests)

## Migration Priority Order

### Phase D.1: RefinementConfig Migration
**Deliverable:** New module `dbex/refinement/config.py` with RefinementConfig dataclass
**Files:** 4 (config-only consumers + __init__.py)
**Risk:** LOW (pure data container, no logic)

### Phase D.2: CLI Refactor (Critical Path)
**Deliverable:** `dbex/refine_one.py` migrated to RefinementEngine
**Files:** 1
**Risk:** MEDIUM (production entry point)
**Validation:** CLI smoke tests

### Phase D.3: Test Harness Migration
**Deliverable:** `tests/dbex/test_torch_refine_smoke.py` migrated to RefinementEngine
**Files:** 1 (6 functions)
**Risk:** MEDIUM (core acceptance tests)
**Validation:** All 6 Stage A/B/C smoke selectors

### Phase D.4: Import Cleanup
**Deliverable:** Remaining files updated to canonical imports
**Files:** 3 (test_stage_a_smoke_parity, test_physics_loss_current, stage_a_adam tooling)
**Risk:** LOW (mostly import path fixes)
**Validation:** Individual test selectors

### Phase D.5: Facade Deletion
**Deliverable:** `dbex/nanobrag_refinement.py` deleted
**Files:** 1
**Risk:** HIGH (irreversible)
**Validation:** Full test suite + comprehensive verification checklist

## Out-of-Scope Consumers (Archive/Tooling/Docs)

The following files also import from `nanobrag_refinement` but are **excluded** from Phase D migration:

- **plans/active/*/bin/*.py** (8 files): Ad-hoc probes/benchmarks under active initiatives
  - Rationale: These are research artifacts, not production code. Can break temporarily.
  - Action: Add TODO comments + migrate opportunistically when touched.

- **docs/*.md, logs/*.md, repomix-output.xml**: Documentation/historical references
  - Rationale: Not executable code.
  - Action: Update references in next doc refresh cycle.

- **galph_memory.md**: Supervisor notes
  - Rationale: Historical context only.
  - Action: None (read-only artifact).

## Dependency Analysis

### RefinementConfig Relocation Impact
**Current:** `dbex/nanobrag_refinement.py:74-175` (~102 lines)
**Target:** `dbex/refinement/config.py` (new module)

**Reasons for Option A (new module) over Option B (inline to context.py):**
1. `context.py` is already ~950+ lines (large)
2. RefinementConfig is job-scoped configuration, not runtime context
3. Separation of concerns: config (immutable job setup) vs context (runtime state)
4. Future-proof: Likely to grow with Stage D/E config options
5. Naming clarity: `dbex.refinement.config.RefinementConfig` is self-documenting

**Files Affected:**
- Create: `dbex/refinement/config.py` (+102 lines + imports + module docstring ~120 lines)
- Update imports: 7 files (refine_one, __init__, test_refinement_engine 2×, test_stage_b_cpu_fallback 3×)

### Circular Import Risk Assessment
**Risk:** LOW

- `RefinementConfig` is a pure dataclass (no imports from dbex.refinement.*)
- `dbex.refinement.config` will only import: `dataclasses.dataclass, dataclasses.field, torch.dtype`
- No back-references to Engine/Stages
- Safe to import from both production and tests

### Validation Strategy

Each phase must validate:
1. **Static checks:** No ImportError when importing affected modules
2. **Unit tests:** Per-file test selectors (see Categories A/B/C above)
3. **Integration tests:** CLI smoke tests + Stage A/B/C acceptance tests
4. **Collection check:** `pytest --collect-only` for new/renamed tests

Final verification (Phase D.5) requires:
- `rg "from.*nanobrag_refinement import|import.*nanobrag_refinement"` → Empty (excluding docs/logs/archive)
- Full test suite: `pytest -v tests/dbex/` → All PASSED
- CLI smoke: `python -m dbex.refine_one --help` → No ImportError

## Artifacts Cross-References

- **Consumer Inventory (raw):** `consumer_inventory.txt` (this directory)
- **Config Migration Plan:** `config_migration_plan.md` (next deliverable)
- **CLI Refactor Blueprint:** `cli_refactor_blueprint.md` (next deliverable)
- **Test Migration Plan:** `test_migration_plan.md` (next deliverable)
- **Deletion Checklist:** `deletion_checklist.md` (final deliverable)
