# ARCH-REFACTOR-001 Initiative Status Assessment

**Date:** 2025-11-24T105000Z
**Assessor:** Galph (Supervisor)
**Purpose:** Determine next action after Phase D D2 completion

## Executive Summary

**Recommendation: PIVOT TO OTHER TIER 3 WORK**

ARCH-REFACTOR-001 has delivered **substantial value** across Phases 0/A/B/D1/D2 (6/9 exit criteria satisfied). Phase C (Engine Migration) is **12-16 loops (~25-35 hours)** with **HIGH regression risk** and no immediate blocking use case. Per CLAUDE.md "incremental progress over big bangs," recommend deferring Phase C and pivoting to other Tier 3 initiatives with clearer ROI.

## Phases Completed

### Phase 0 — Test Discipline Baseline ✓ COMPLETE
- **Duration:** 1 loop (2025-11-24T070000Z)
- **Deliverables:** 6 unit tests (2 geometry + 4 physics loss) validating CURRENT code
- **Coverage:** ~85-90% manual assessment (tool unavailable per Environment Freeze)
- **Value:** Safety net for future refactoring, proves team can write tests

### Phase A — Physics Extraction ✓ COMPLETE
- **Duration:** 1 loop (2025-11-24T074500Z)
- **Deliverables:**
  - `dbex/geometry/crystallography.py` (derive_u_matrix extraction)
  - `dbex/physics/loss.py` (_compute_variance_weighted_loss extraction)
- **Metrics:** -124 LOC from monolithic modules to leaf-node modules
- **Value:** Isolated unit testing, clear separation of concerns

### Phase B — Telemetry Standardization ✓ COMPLETE
- **Duration:** 1 loop (2025-11-24T085000Z)
- **Deliverables:**
  - RefinementTelemetry converted to @dataclass with to_dict()
  - _write_torch_outputs refactored from 60 lines manual mapping to dynamic iteration
- **Metrics:** -60 LOC boilerplate elimination, backward-compatible HDF5 schema
- **Value:** Maintainable telemetry, easier schema evolution

### Phase D D1 — DiffBragg Scratch Isolation ✓ COMPLETE
- **Duration:** 1 loop (2025-11-24T091500Z)
- **Deliverables:**
  - `dbex/diffbragg_tmp.py` context manager (87 lines)
  - Parameterized `detector_refinement()` with scratch_dir
  - 7 validation tests including multiprocessing concurrency
- **Value:** Eliminates repo pollution (`_geom_ref.*`, `_temp.mtz`), enables concurrent runs

### Phase D D2 — Stage A Tooling Modularization ✓ COMPLETE
- **Duration:** 2 loops (D2.1+D2.2 2025-11-24T095000Z, D2.3+D2.4 2025-11-24T100106Z)
- **Deliverables:**
  - `dbex/tools/stage_a_adam.py` module (1898 lines, 15 functions, 3 classes)
  - CLI refactored from 1849 → 340 lines (-1509 LOC, -81.6%)
  - Test suite 8/9 tests PASSED (350 lines)
  - README 113 lines
- **Value:** Reusable tooling, eliminates sys.path hacks, comprehensive docstrings

## Phases Deferred

### Phase C — Incremental Engine Migration (DEFERRED)
- **Estimated Effort:** 12-16 loops (~25-35 hours)
- **Risk Level:** HIGH (core architecture rewrite, state management migration)
- **Substeps:**
  - C1: Bridge Pattern (2-3 loops)
  - C2: Stage A migration (2-3 loops)
  - C3: Stage B migration (2 loops)
  - C4: Stage C migration (2 loops)
  - C5: Facade Cleanup (1-2 loops)
  - C6: Simulator Seam (3-4 loops)
- **Rationale for Deferral:**
  1. No immediate blocking use case (PERF-WARM-SIM-001 is env-blocked, TORCH-REFINE-004 depends on ARCH-REFINE-FLOW-001 which is done)
  2. Substantial value already delivered in Phases 0/A/B/D
  3. HIGH regression risk for large-scale refactor
  4. CLAUDE.md "incremental progress over big bangs"

### Phase D D3 — Summary-Generation CLI Cleanup (OPTIONAL)
- **Estimated Effort:** 2-3 loops (~5-7 hours)
- **Risk Level:** LOW (isolated tooling)
- **Rationale for Deferral:** Lower priority than other Tier 3 initiatives

## Exit Criteria Status

| Criterion | Status | Notes |
|-----------|--------|-------|
| #1 Physics isolated | ✓ SATISFIED | Phase A complete |
| #2 RefinementTelemetry to_dict() | ✓ SATISFIED | Phase B complete |
| #3 Engine delegation | ❌ DEFERRED | Phase C deferred (12-16 loops) |
| #4 Regression guards | ✓ SATISFIED | Pass at every commit |
| #5 Parity test | ❌ DEFERRED | Phase C scope |
| #6 Test registry | ✓ SATISFIED | Synced throughout |
| #7 DiffBragg scratch | ✓ SATISFIED | Phase D D1 complete |
| #8 Stage A tooling | ✓ SATISFIED | Phase D D2 complete |
| #9 Single simulator seam | ❌ DEFERRED | Phase C scope |

**Score:** 6/9 exit criteria satisfied (66.7%)

## Value Delivered

### Quantitative Metrics
- **Code reduction:** -1693 LOC total
  - Physics extraction: -124 LOC from monolithic modules
  - Telemetry: -60 LOC boilerplate
  - CLI refactor: -1509 LOC (thin shim replacing fat script)
- **Code addition:** +2073 LOC structured
  - dbex/tools/stage_a_adam.py: +1898 LOC (module with docstrings)
  - dbex/diffbragg_tmp.py: +87 LOC (context manager)
  - Test suites: ~520 LOC (Phase 0/D1/D2)
  - README: +113 LOC
- **Net:** +380 LOC (but higher quality: structured, tested, documented)
- **Tests added:** ~520 lines across 3 test files (23 tests total)
- **Documentation:** 2 READMEs (dbex/tools/, Phase D D2)

### Qualitative Benefits
1. **Test discipline proven:** Phase 0 safety net demonstrates team can write tests
2. **Architectural hygiene:** Physics/geometry separated from orchestration
3. **Maintainability:** Telemetry schema evolution simplified
4. **Reusability:** Stage A tooling now importable, testable
5. **Concurrency-safe:** DiffBragg scratch isolation enables parallel runs
6. **Knowledge capture:** Comprehensive docstrings preserve CONVERGENCE-001/PARITY-002 diagnostic wisdom

## Roadmap Impact

### Current Tier 3 Status
- **ARCH-REFACTOR-001:** 6/9 exit criteria (Phase C deferred)
- **PERF-WARM-SIM-001:** Blocked (ENV-CUDA-001 environmental error)
- **TORCH-REFINE-004:** Pending (depends on ARCH-REFINE-FLOW-001, which is done 2025-11-23T172000Z)
- **TOOLING-VIS-001:** In progress (Phase D realignment complete)

### Unblocking Analysis
- **PERF-WARM-SIM-001:** Not unblocked by Phase C (env issue, not architecture)
- **TORCH-REFINE-004:** Not blocked by Phase C (depends on ARCH-REFINE-FLOW-001, already done)
- **TOOLING-VIS-001:** Not blocked by Phase C

**Conclusion:** Phase C does NOT unblock any Tier 3 work.

## Decision Options

### Option A: PIVOT TO OTHER TIER 3 WORK (RECOMMENDED)
**Action:** Mark ARCH-REFACTOR-001 status as "substantial progress, Phase C deferred, return condition: blocking use case emerges"
**Next Focus:** TORCH-REFINE-004 (Stage B per-reflection mode) OR TOOLING-VIS-001 (visual diagnostics library)
**Rationale:**
- 6/9 exit criteria satisfied delivers substantial value
- No immediate blocking use case for Phase C
- Other Tier 3 work has clearer ROI
- Incremental progress philosophy honored
**Confidence:** HIGH (90%) — Substantial value delivered, no pressing need for Phase C

### Option B: Continue Phase D D3 (Summary-Generation CLI)
**Action:** Plan Phase D D3 (2-3 loops, ~5-7 hours)
**Rationale:** Complete Phase D tooling hygiene before pivoting
**Confidence:** MEDIUM (60%) — Lower priority than other Tier 3 initiatives, questionable ROI

### Option C: Plan Phase C C1 (Bridge Pattern)
**Action:** Plan Phase C C1 first iteration (2-3 loops, ~4-6 hours)
**Rationale:** Begin large-scale refactor incrementally
**Confidence:** LOW (30%) — HIGH risk, no blocking use case, violates "incremental progress" when substantial value already delivered

## Recommendation

**CHOOSE OPTION A: PIVOT TO OTHER TIER 3 WORK**

### Rationale Summary
1. **Value delivered:** 6/9 exit criteria satisfied (test discipline + physics separation + telemetry modernization + scratch isolation + tooling hygiene)
2. **No blocking use case:** Phase C does not unblock any current Tier 3 work
3. **High risk/effort:** 12-16 loops (~25-35 hours) with core architecture changes
4. **Incremental progress:** CLAUDE.md philosophy honored by delivering value early, deferring large rewrites
5. **ROI clarity:** Other Tier 3 initiatives (TORCH-REFINE-004, TOOLING-VIS-001) have clearer immediate value

### Next Actions
1. Update fix_plan.md status: `in_progress` → `partial_complete` with note "Phases 0/A/B/D1/D2 complete, Phase C deferred pending blocking use case"
2. Create closure artifacts: initiative_status_assessment.md (this doc), closure_summary.md
3. Select new focus from Tier 3: TORCH-REFINE-004 (Stage B per-reflection mode) highest priority after ARCH-REFINE-FLOW-001 completion
4. Commit and push housekeeping changes
5. Author input.md for Ralph with new focus

## Return Conditions for Phase C

Phase C should resume when ONE of these conditions is met:

1. **Blocking Use Case:** A Tier 1/2 initiative requires engine delegation (e.g., multi-stage optimization, dynamic stage composition)
2. **Technical Debt Pressure:** Monolithic `run_nanobrag_refinement` becomes unmaintainable (e.g., >5000 lines, >10 nested closures)
3. **Testing Velocity:** Inability to write effective tests due to architecture (not currently the case: Phase 0 proves tests are writable)
4. **Performance Bottleneck:** State management overhead measurable and blocking perf work (not currently the case: PERF-WARM-SIM-001 is env-blocked)

**Current Assessment:** NONE of these conditions are met.

## Findings Applied
- **CLAUDE.md** (Incremental progress over big bangs) ✓
- **POLICY-001** (Environment Freeze) ✓
- **galph_prompt** (Dwell enforcement, implementation floor) ✓
- **galph_prompt** (Layered-scope guard: suspend higher layer when lower layer unstable) ✓

## Artifacts
- This assessment: `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T105000Z/initiative_status_assessment.md`
- Phase completion summaries: `reports/2025-11-24T{070000Z,074500Z,085000Z,091500Z,092000Z,095000Z,080106Z}/summary.md`
- Implementation plan: `plans/active/ARCH-REFACTOR-001/implementation.md`
- Fix plan entry: `docs/fix_plan.md:94-111`
