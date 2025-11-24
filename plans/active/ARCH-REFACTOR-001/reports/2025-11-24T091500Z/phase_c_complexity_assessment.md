# ARCH-REFACTOR-001 Phase C Complexity Assessment

**Date:** 2025-11-24T091500Z
**Loop:** Galph supervisor (i=255)
**Phase:** C — Incremental Engine Migration (Planning)
**Assessment:** Phase C is multi-loop initiative requiring significant scope reduction and staging

## Executive Summary

Phase C (Incremental Engine Migration) as specified in `implementation.md:133-190` is a **large-scale architectural refactor** (5 incremental steps: C1-C5) with complexity substantially beyond single-loop feasibility. **Decision:** DEFER Phase C in favor of completing remaining lower-complexity items (Phase D) or switching focus per Execution Roadmap priorities.

**Rationale:**
1. **Scope:** Phase C involves rewriting `run_nanobrag_refinement` closure-based architecture into class-based `RefinementEngine` with `SimulationContext` + `RefinementStage` ABC + 3 concrete stage implementations (StageA/B/C).
2. **Estimated Effort:** 5 multi-loop initiatives (C1: 2-3 loops, C2: 2-3 loops, C3: 2 loops, C4: 2 loops, C5: 1-2 loops) = **10-13 total loops** (~20-30 hours engineering time).
3. **Dependencies:** Phase C unblocks no current Tier 1/2 items; TORCH-API-ALIGN-001 already done, PERF-WARM-SIM-001 blocked by ENV-CUDA-001.
4. **Risk:** High regression risk (rewriting core refinement orchestration, state management migration from closure captures to explicit context).

## Phase C Breakdown (from implementation.md:133-190)

### C1: Bridge Pattern — Inject Context into Existing Closures
**Goal:** Introduce `SimulationContext` class (Detector, Crystal, Simulator, Masks, ROI cache) and pass into existing LBFGS closures as additional parameter.

**Checklist:**
- C1.1: Implement `SimulationContext` class
- C1.2: Update `run_nanobrag_refinement` to instantiate context and pass to closures
- C1.3: Validation: `test_stage_a_expansion` passes, cache logic unchanged

**Estimated Effort:** 2-3 loops (~4-6 hours)
**Complexity:** MEDIUM (dual-path validation: old closure captures + new context references must coexist)

### C2: Stage A Migration
**Goal:** Implement `RefinementStage` ABC and `StageAGeometry` class wrapping Stage A parameter init, LBFGS closure, telemetry.

**Checklist:**
- C2.1: Implement `RefinementStage` ABC (setup, step, teardown, get_telemetry)
- C2.2: Implement `StageAGeometry(RefinementStage)`
- C2.3: Update loop to delegate Stage A to class
- C2.4: Parity validation: telemetry JSON diff (chi² within 1e-6, CC within 1e-9)

**Estimated Effort:** 2-3 loops (~5-7 hours)
**Complexity:** HIGH (closure-to-class migration, state management, telemetry parity)

### C3: Stage B Migration
**Goal:** Implement `StageBStructure(RefinementStage)` wrapping shell modifiers logic.

**Checklist:**
- C3.1: Implement `StageBStructure(RefinementStage)`
- C3.2: Wire Stage B into engine
- C3.3: Validation: `test_stage_b_shell_modifiers` passes

**Estimated Effort:** 2 loops (~3-4 hours)
**Complexity:** MEDIUM-HIGH (CPU fallback logic per PERF-WARM-011, cache preservation)

### C4: Stage C Migration
**Goal:** Implement `StageCDetector(RefinementStage)` wrapping detector offset refinement.

**Checklist:**
- C4.1: Implement `StageCDetector(RefinementStage)`
- C4.2: Wire Stage C into engine
- C4.3: Validation: `test_stage_c_detector_microslip` passes

**Estimated Effort:** 2 loops (~3-4 hours)
**Complexity:** MEDIUM-HIGH (detector offset refinement, telemetry parity)

### C5: Facade Cleanup
**Goal:** Rewrite `run_nanobrag_refinement` as pure orchestrator, delete legacy closure code.

**Checklist:**
- C5.1: Rewrite as orchestrator (instantiate `RefinementEngine`, add stages, call `engine.run()`)
- C5.2: Final regression: full test suite
- C5.3: Performance benchmark (execution time within 5% of baseline)

**Estimated Effort:** 1-2 loops (~2-4 hours)
**Complexity:** MEDIUM (cleanup + final validation)

### C6: Single Simulator Seam Consolidation
**Goal:** Post-TORCH-API-ALIGN-001: Consolidate all call sites to unified simulator factory or ExperimentModel adapter.

**Status:** BLOCKED (TORCH-API-ALIGN-001 Phase D4 seam decision deferred, ExperimentModel blocked by upstream ARCH-FACTORY-003)

**Checklist:**
- C6.1: Enumerate legacy simulator wiring call sites
- C6.2: Collapse to chosen seam (factory or ExperimentModel)
- C6.3: Remove redundant helpers
- C6.4: Parity validation (DB-AT-024, Stage A/B/C smokes)
- C6.5: API/docs consolidation

**Estimated Effort:** 3-4 loops (~6-8 hours)
**Complexity:** MEDIUM-HIGH (cross-cutting refactor, parity validation)

## Total Phase C Effort Estimate

**Loops:** C1 (2-3) + C2 (2-3) + C3 (2) + C4 (2) + C5 (1-2) + C6 (3-4) = **12-16 loops**
**Time:** ~25-35 hours engineering effort
**Risk Level:** HIGH (core architecture rewrite, multi-loop state management migration)

## Alternative: Phase D (Legacy Hygiene & Tooling)

**Phase D Scope (implementation.md:191-209):**
- D1: DiffBragg scratch isolation (per-run temp directories)
- D2: Stage A debug tooling modularization (extract utilities)
- D3: Summary-generation CLI cleanup (argparse-driven)

**Estimated Effort:** D1 (1 loop ~2h) + D2 (1-2 loops ~3-4h) + D3 (1-2 loops ~3-4h) = **3-5 loops total** (~8-10 hours)
**Complexity:** LOW-MEDIUM (localized tooling improvements, no core architecture changes)
**Risk Level:** LOW (isolated tooling changes, minimal regression risk)

## Roadmap Alignment Check

### Current Status (from fix_plan.md Execution Roadmap)

**Tier 1: Core Physics & Stability** — ✓ COMPLETE
- TORCH-GEOMETRY-CONVERGENCE-001 ✓ Done
- PHYSICS-LOSS-001 ✓ Done
- REFINE-SMOKE-CANONICAL ✓ Done

**Tier 2: Architectural Maturity** — ✓ COMPLETE
- ARCH-REFINE-FLOW-001 ✓ Done
- TORCH-API-ALIGN-001 ✓ Done (factory-only path, 2025-11-24T004500Z)

**Tier 3: Feature Completeness & Refactoring** — IN PROGRESS
- ARCH-REFACTOR-001 (current focus): Phase 0 ✓ done, Phase A ✓ done, Phase B ✓ done, Phase C/D PENDING
- PERF-WARM-SIM-001: blocked (ENV-CUDA-001)
- TORCH-REFINE-004: blocked (awaits ARCH-REFACTOR-001 completion)
- TOOLING-VIS-001: pending

### Priority Assessment

**Phase C (Engine Migration):** Foundational refactor, but NO current blockers depend on it. PERF-WARM-SIM-001 is blocked by environment (not ARCH-REFACTOR-001). TORCH-REFINE-004 Stage B per-reflection mode is blocked by "engine refactor complete" but unclear if Phase C is required vs just Phase A/B.

**Phase D (Tooling Hygiene):** Lower complexity, addresses technical debt in ancillary tooling (DiffBragg scratch files, Stage A debug scripts, summary generation). Improves developer experience but not on critical path.

**Alternative Tier 3 Foci:**
- TOOLING-VIS-001: Visualization tooling (pending, not blocking)
- TORCH-REFINE-004: Stage B per-reflection mode (blocked, unclear if Phase C required)

## Decision Tree

### Path A: Defer Phase C, Switch to Phase D (Tooling Hygiene)
**Rationale:**
- Phase C is 12-16 loop initiative (25-35 hours)
- No current Tier 1/2 blockers depend on Phase C
- Phase D is 3-5 loops (8-10 hours), LOW risk, improves DX
- CLAUDE.md incremental progress philosophy: deliver value frequently

**Actions:**
1. Mark Phase C status in implementation.md as "DEFERRED (multi-loop complexity, no current dependencies)"
2. Plan Phase D (D1: DiffBragg scratch isolation) as next ready_for_implementation
3. Update fix_plan.md Attempts History with Phase C deferral decision

**Confidence:** HIGH (~90%) — Phase D is lower-hanging fruit with clear DX benefit

### Path B: Defer Phase C, Switch to Alternative Tier 3 Focus
**Rationale:**
- PERF-WARM-SIM-001 blocked by ENV-CUDA-001 (cannot resolve per Environment Freeze)
- TORCH-REFINE-004 blocked awaiting "engine refactor" (unclear if Phase C required)
- TOOLING-VIS-001 visualization tooling (no urgent need)

**Actions:**
1. Mark Phase C deferred
2. Review TORCH-REFINE-004 blocking condition (does it actually require Phase C or just Phase A/B?)
3. If Phase A/B sufficient, unblock TORCH-REFINE-004 planning

**Confidence:** MEDIUM (~70%) — Requires investigation into TORCH-REFINE-004 dependencies

### Path C: Proceed with Phase C (NOT RECOMMENDED)
**Rationale:**
- Complete ARCH-REFACTOR-001 per original plan
- Foundational refactor enables cleaner Stage A/B/C implementation

**Risk:**
- 12-16 loop commitment (25-35 hours)
- High regression risk (core architecture rewrite)
- No immediate unblocking benefit for Tier 1/2 items
- Violates CLAUDE.md incremental progress principle (deliver value frequently, not big bang)

**Confidence:** LOW (~30%) — Phase C is architecturally desirable but not tactically urgent

## Recommended Action: Path A (Defer Phase C, Switch to Phase D)

**Verdict:** Defer Phase C (Engine Migration) in favor of Phase D (Tooling Hygiene) for the following reasons:

1. **Incremental Progress:** Phase D delivers DX value in 3-5 loops vs Phase C's 12-16 loops
2. **Risk Mitigation:** Phase D has LOW regression risk (isolated tooling) vs Phase C's HIGH risk (core refactor)
3. **No Current Blockers:** Phase C doesn't unblock any Tier 1/2 items; PERF-WARM-SIM-001 is env-blocked
4. **Technical Debt Reduction:** Phase D addresses known DX pain points (DiffBragg scratch files, debug tooling)
5. **CLAUDE.md Alignment:** "Incremental progress over big bangs" — deliver smaller, testable changes

### Next Steps (Phase D D1: DiffBragg Scratch Isolation)

**Objective:** Create utilities under `dbex/diffbragg_tmp.py` for per-run temporary directories, isolate `_geom_ref.*`, `_temp.mtz`, `_geom.out/` artifacts.

**Checklist (implementation.md:195-197):**
- D1.1: Implement `dbex/diffbragg_tmp.py` with temp directory allocation
- D1.2: Update `run_diffbragg_backend` to use per-run temp dirs
- D1.3: Add validation tests (multiprocessing spawn, artifact isolation)
- D1.4: Update docs (CLI flags, environment variables)

**Estimated Effort:** 1 loop (~2-3 hours)
**Risk:** LOW (isolated tooling change, clear validation path)
**Confidence:** HIGH (~90%) — Straightforward implementation

## Findings Applied

- **POLICY-001** (Environment Freeze): No env changes, dbex-only refactoring ✓
- **CLAUDE.md Incremental Progress**: "Incremental progress over big bangs" — Phase D preferred over Phase C ✓
- **galph_prompt Implementation Floor**: Max 1 docs-only loop, next loop MUST be ready_for_implementation ✓
- **galph_prompt Dwell Enforcement**: Last loop (i=254) Ralph implementation, this loop (i=255) Galph planning (dwell=0), next loop MUST be ready_for_implementation ✓

## Artifacts

- `phase_c_complexity_assessment.md` (this document)
- `phase_d_d1_planning_analysis.md` (next: DiffBragg scratch isolation planning)

## References

- Implementation Plan: `plans/active/ARCH-REFACTOR-001/implementation.md:133-209`
- Phase B Completion: `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T085000Z/phase_b_decision.md`
- Fix Plan: `docs/fix_plan.md` ARCH-REFACTOR-001 entry (line 118)
- CLAUDE.md: `/home/ollie/Documents/diffbragg_example/CLAUDE.md` (incremental progress philosophy)
