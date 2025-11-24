# ARCH-REFACTOR-001 Focus Selection Decision: Phase D D1 Complete

**Date:** 2025-11-24T092000Z
**Loop:** Galph (i=256)
**Phase:** Post-D1 Focus Selection

## Summary

Phase D D1 (DiffBragg scratch isolation) completed successfully (commit e95a57d, all 7 tests PASSED, 0.17s runtime). Evaluating whether to continue with Phase D D2/D3 (tooling modularization) or close out ARCH-REFACTOR-001 with partial completion and pivot to other Tier 3 work.

## Phase D D1 Completion Status

**✓ COMPLETE** (2025-11-24T091500Z, Ralph loop i=255)

### Deliverables Shipped
1. **`dbex/diffbragg_tmp.py`** (87 lines): Context manager `diffbragg_scratch_dir()` with:
   - System temp directory mode (default, using `tempfile.TemporaryDirectory`)
   - User-provided directory mode with timestamped subdirectories
   - Cleanup with graceful error handling (`cleanup=True` default)

2. **`dbex/run_diffbragg.py`** updates:
   - Added `scratch_dir: Optional[Path] = None` parameter to `detector_refinement()`
   - Parameterized all 10 hardcoded scratch paths:
     - `_geom_ref.expt`, `_geom_ref.refl`, `_geom_ref.pkl`
     - `_geom_groups.txt`
     - `_geom.out/` directory (output)
     - `_geom.out/diffBragg_detector.expt` (read back)
   - Backward compatible: defaults to `Path.cwd()` if `scratch_dir=None`
   - Subdirectory creation: `geom_ref/`, `geom_out/`

3. **`tests/dbex/test_diffbragg_tmp.py`** (170 lines, 7 tests):
   - `test_scratch_dir_default`: System temp allocation
   - `test_scratch_dir_subdirectories`: geom_ref/geom_out creation
   - `test_scratch_dir_user_provided`: User directory mode + cleanup
   - `test_scratch_dir_keep_scratch`: Cleanup=False flag
   - **`test_concurrent_diffbragg_runs`**: CORE multiprocessing isolation (3 workers)
   - `test_scratch_cleanup`: Sequential cleanup validation
   - `test_scratch_dir_no_geom_out_pollution`: No _geom.out/ in working dir

### Validation: ALL PASS
```
============================= test session starts ==============================
collected 7 items

tests/dbex/test_diffbragg_tmp.py::test_scratch_dir_default PASSED
tests/dbex/test_diffbragg_tmp.py::test_scratch_dir_subdirectories PASSED
tests/dbex/test_diffbragg_tmp.py::test_scratch_dir_user_provided PASSED
tests/dbex/test_diffbragg_tmp.py::test_scratch_dir_keep_scratch PASSED
tests/dbex/test_diffbragg_tmp.py::test_concurrent_diffbragg_runs PASSED
tests/dbex/test_diffbragg_tmp.py::test_scratch_cleanup PASSED
tests/dbex/test_diffbragg_tmp.py::test_scratch_dir_no_geom_out_pollution PASSED

============================== 7 passed in 0.17s ===============================
```

### Production Benefit
- **Concurrency-safe:** Multiple DiffBragg runs can execute simultaneously without file collisions
- **Workspace hygiene:** No scratch file pollution in repo root
- **Developer experience:** Explicit `--keep-scratch` support for debugging

## ARCH-REFACTOR-001 Progress Summary

### Phases Complete
- **✓ Phase 0** (Test Discipline): 5 unit tests written against current code (2 geometry + 4 physics)
- **✓ Phase A** (Physics Extraction): `dbex.geometry.crystallography`, `dbex.physics.loss` modules created, -124 LOC reduction
- **✓ Phase B** (Telemetry Modernization): `RefinementTelemetry` @dataclass with `to_dict()`, dynamic HDF5 I/O
- **✓ Phase D D1** (Scratch Isolation): DiffBragg scratch file isolation with multiprocessing tests

### Phases Remaining
- **❌ Phase C** (Engine Migration): 12-16 loops, ~25-35 hours estimated, HIGH risk
- **❌ Phase D D2** (Stage A Tooling): Extract utilities from 1849-line `stage_a_mapping_adam_debug.py`
- **❌ Phase D D3** (Summary CLI): Convert 3 scripts to argparse-driven CLIs

### Exit Criteria Assessment (9 total)
| # | Criterion | Status | Phase |
|---|-----------|--------|-------|
| 1 | Core physics isolated + unit-tested | ✓ SATISFIED | A |
| 2 | RefinementTelemetry `to_dict()` + dynamic HDF5 | ✓ SATISFIED | B |
| 3 | `run_nanobrag_refinement` delegates to Engine | ❌ NOT SATISFIED | C (deferred) |
| 4 | Regression Guards pass | ✓ SATISFIED | All phases |
| 5 | Parity test confirms no drift | ⚠ DEFERRED | (no DB-AT-001 yet) |
| 6 | Test registry synchronized | ✓ SATISFIED | All phases |
| 7 | DiffBragg scratch isolation | ✓ SATISFIED | D1 |
| 8 | Stage-A tooling CLI + tests | ❌ NOT SATISFIED | D2/D3 (deferred) |
| 9 | Single simulator seam | ⚠ PARTIAL | (TORCH-API-ALIGN-001 factory) |

**Satisfied: 5/9 (56%), Deferred: 2/9, Not Satisfied: 2/9**

## Remaining Work Complexity Analysis

### Phase C: Engine Migration
**Scope:** 5 incremental steps (C1-C5), 12-16 loops estimated
- C1: Bridge Pattern - Inject `SimulationContext` into closures (3-4 loops)
- C2: Stage A Migration - Extract to `RefinementStage` ABC (3-4 loops)
- C3: Stage B Migration (2-3 loops)
- C4: Stage C Migration (2-3 loops)
- C5: Facade Cleanup - Deprecate old `run_nanobrag_refinement` (1-2 loops)

**Risks:**
- HIGH: Core architecture rewrite, dual codepaths temporarily, state synchronization bugs
- Rollback criteria: If state bugs appear, rollback entire Phase C
- Performance regression: ≤5% slowdown tolerance

**Estimated Effort:** 25-35 hours total

### Phase D D2: Stage A Tooling Modularization
**Scope:** Extract utilities from `stage_a_mapping_adam_debug.py` (1849 lines)
- Create `dbex/tools/stage_a_adam.py` with reusable functions
- CLI becomes thin argparse shim
- Unit/integration tests for zero-point + block-DoF flows

**Estimated Effort:** 2-3 loops (~6-8 hours)

### Phase D D3: Summary CLI Cleanup
**Scope:** Convert 3 scripts to argparse-driven CLIs
- `generate_summaries.py`, `generate_all_summaries.py`, `summary_worker.py`
- Parameters: branch prefix, role list, history count, concurrency, output directory
- Expose `dbex/tools/summaries.py` for reuse
- Unit tests + smoke test with `--dry-run`
- Transition docs

**Estimated Effort:** 2-3 loops (~6-8 hours)

## Options Analysis

### Option A: Continue with Phase D D2/D3 (Tooling Modularization)
**Pros:**
- Completes Phase D fully
- Improves developer experience (tooling reusability)
- Relatively low risk (isolated changes)
- Achieves Exit Criterion #8

**Cons:**
- Does NOT achieve Exit Criterion #3 (Engine Migration)
- Exit Criterion #3 requires Phase C (12-16 loops)
- Tooling improvements are "nice to have", not blocking
- Incremental effort 4-6 loops (~12-16 hours) for tooling alone

**Net Progress:** 6/9 exit criteria satisfied (67%), but still missing core Engine Migration

### Option B: Tackle Phase C (Engine Migration)
**Pros:**
- Achieves Exit Criterion #3 (core requirement)
- Foundational for future Stage refactoring work
- Unblocks TORCH-REFINE-004 (Stage B per-reflection mode) dependency

**Cons:**
- HIGH complexity (12-16 loops, ~25-35 hours)
- HIGH risk (core architecture rewrite, potential rollback)
- "Big bang" approach conflicts with CLAUDE.md incremental philosophy
- No current blocker requiring Engine pattern

**Dwell Impact:** Would require sustained multi-loop focus (risk of stalling)

### Option C: Mark ARCH-REFACTOR-001 Partially Complete, Pivot to Other Work
**Pros:**
- Substantial value already delivered (Phases 0/A/B/D1)
- Incremental progress philosophy honored
- Frees up capacity for other Tier 3 initiatives (TOOLING-VIS-001, TORCH-REFINE-004)
- Phases C/D2/D3 can be separate initiatives when ROI justifies

**Cons:**
- Exit Criteria #3 (Engine) and #8 (Tooling CLI) remain unmet
- Initiative marked "incomplete" despite significant progress

**Net Progress:** 5/9 exit criteria satisfied (56%), 4 deferred/not satisfied

## Roadmap Context

### Tier 2: ✓ COMPLETE (2025-11-24T004500Z)
- ARCH-REFINE-FLOW-001: ✓ Done
- TORCH-API-ALIGN-001: ✓ Done (factory-only path)

### Tier 3: Feature Completeness
- **TORCH-REFINE-004** (Stage B Per-Reflection Mode): *Pending* (deferred until ARCH-REFINE-FLOW-001 complete — now unblocked)

### Tier 3: Architectural Maturity (Refactoring)
- **ARCH-REFACTOR-001**: *In Progress* (Phases 0/A/B/D1 done, C/D2/D3 remain)
- **PERF-WARM-SIM-001**: *Blocked* (ENV-CUDA-001 environmental issue)

### Tier 3: Tooling & Observability
- **TOOLING-VIS-001** (Standardized Triptychs): *In Progress*

## Recommendation: Option A (Continue Phase D D2)

**Rationale:**
1. **Momentum preservation**: Phases 0/A/B/D1 show consistent progress (4 phases complete in 4 loops)
2. **Low-hanging fruit**: D2/D3 are isolated, low-risk improvements (4-6 loops total)
3. **Exit Criteria improvement**: Achieving #8 brings us to 6/9 (67%) vs current 5/9 (56%)
4. **Defer Phase C decision**: Phase C (Engine Migration) can be evaluated after D2/D3 or as separate initiative
5. **Developer pain point**: `stage_a_mapping_adam_debug.py` is actively used but has 1849-line monolithic structure
6. **Incremental philosophy**: Complete Phase D before tackling large Phase C rewrite

**Alternative Path (if Phase D D2 proves complex):**
- Pivot to **TOOLING-VIS-001** or **TORCH-REFINE-004** after Phase D D2 planning reveals high complexity
- Defer Phase C to separate initiative "ARCH-ENGINE-001" with fresh planning

## Next Actions

1. **Phase D D2 Planning** (this loop):
   - Analyze `stage_a_mapping_adam_debug.py` structure
   - Identify reusable components for extraction
   - Design `dbex/tools/stage_a_adam.py` module API
   - Define validation strategy (unit tests + CLI smoke test)
   - Estimate complexity (1-3 loops?)

2. **Implementation** (next loop if approved):
   - Extract core utilities to `dbex/tools/stage_a_adam.py`
   - Refactor CLI to thin argparse shim
   - Write `tests/dbex/test_stage_a_adam_tooling.py`
   - Run CLI smoke test

3. **Housekeeping** (this loop):
   - Update `galph_memory.md` with Phase D D1 completion
   - Update `docs/fix_plan.md` Attempts History
   - Commit implementation.md D1 checklist update
   - Push sync marker

## Findings Applied

- **CLAUDE.md**: Incremental progress over big bangs ✓
- **galph_prompt**: Dwell enforcement (planning state, dwell=0) ✓
- **POLICY-001**: Environment Freeze compliance ✓

## Artifacts

- `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T092000Z/focus_selection_decision.md` (this file)
- Phase D D1 artifacts: `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T091500Z/`
  - `investigation_scratch_files.md`
  - `pytest_diffbragg_tmp.log`
  - `phase_d_d1_decision.md`
  - `summary.md`

## Decision: Approve Phase D D2 Planning

**Verdict:** Continue with Phase D D2 (Stage A debug tooling modularization) planning this loop.

**Confidence:** MEDIUM-HIGH (~75%)
- Phase D2 scope is well-defined (extract from known 1849-line script)
- Risk is LOW (isolated tooling changes, no production impact)
- ROI is MODERATE (developer convenience, not blocking)
- If complexity exceeds 2-3 loops during planning, can pivot to other Tier 3 work

**Next Loop:** Ralph ready_for_implementation (Phase D D2) if planning shows ≤3 loop complexity, else pivot decision.
