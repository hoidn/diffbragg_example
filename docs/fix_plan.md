# DBEX Fix Plan Ledger

**Last Updated:** 2025-11-24 (Active/pending initiatives only — older history snapshots live in `docs/fix_plan_archive.md`)

## Working Agreements
- Continue logging every loop in this ledger with status + artifact pointer; detailed Attempts History older than the sections below lives in `docs/fix_plan_archive.md`.
- Status values: `pending`, `in_progress`, `blocked`, `done`, `archived`.
- Citation rule remains: whenever you touch a selector or plan row, note the artifact path in both this file and the plan’s reports directory.

---

## Execution Roadmap
> **Agent Rule:** Prioritize initiatives in lower-numbered tiers. Within a tier, follow dependency chains. Do not start a Tier N+1 item if a Tier N item is unblocked.


### Tier 1: Core Physics & Stability
**Goal:** Ensure the math is correct, the loss function is normative, Stage A/mapping parity holds (DB‑AT‑027/028/029), and the smoke tests are green.
- [ARCH-REFINE-001] (Refine Engine Modularization + Torch IO context) — **in_progress** (Top priority; finalizing contexts/simulator seams and the torch writer so downstream Tier 1 work like SPEC-REALIGN-001 can proceed on a stable foundation)

### Tier 2: Architectural Maturity
**Goal:** Break the monolithic `run_nanobrag_refinement` into a maintainable Protocol Engine.
**Status:** ✓ COMPLETE (2025-11-24T004500Z)
- [ARCH-REFINE-FLOW-001] (Protocol Engine) — **Done** (2025-11-23T172000Z: Phases A-E complete, Stage A/B/C wrappers validated, engine delegation operational)
- [TORCH-API-ALIGN-001] (Adopt ExperimentModel, Unify Simulator Wiring, DIALS Mapping) — **Done** (2025-11-24T004500Z: Factory-only path complete, unified factory -79 lines, DIALS mapping validated, ExperimentModel adapter deferred due to upstream blocker)

### Tier 3: Feature Completeness
**Goal:** Implement normative spec features currently using fallback modes.
- [TORCH-REFINE-004] (Stage B Per-Reflection Mode) — **Done** (2025-11-24T140000Z: Phase 9 complete, all 4/4 exit criteria met, per-reflection mode operational with ASU mapping, shell mode fallback preserved)

### Tier 3: Architectural Maturity (Refactoring)
**Goal:** Refactor monolithic loops into maintainable engines with clear boundaries and testable seams.
- [PERF-WARM-SIM-001] (Warm Simulator) — **Blocked** (ENV-CUDA-001: environmental CUDA caching allocator error; return condition: env resolution OR test retry on different session/hardware; warm-cache implementation will resume after ARCH-REFINE-001 finalizes shared contexts/simulator seams)

### Tier 3: Tooling & Observability
**Goal:** Standardize visuals, documentation, and runtime guardrails.
- [DOC-RUNTIME-004] (Restore Runtime Checklist) — **Done** (2025-11-23T024449Z: all exit criteria met, runtime checklist restored with spec citations, references verified, validation artifacts complete)
- [TORCH-RUNTIME-002] (Runtime Harness Seed) — **Done** (2025-10-28T232744Z: all exit criteria satisfied, TESTING_GUIDE.md updated, selector registry synchronized)

---

## Active / Pending Initiatives

### [ARCH-REFINE-001] Refinement Engine Modularization & Torch IO
- Depends on: ARCH-REFINE-FLOW-001 (engine skeleton, telemetry contract)
- Status: in_progress
- Priority: High
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-01
- Exit Criteria:
  1. `dbex/refine_one.py` and `dbex/nanobrag_refinement.py` route every torch refinement through `RefinementEngine(StageA, StageB, StageC)` (no inline monolith), satisfying docs/spec-db-workflow.md §§30-41.
  2. `RefinementContext`/`JobContext` replace ad-hoc dict plumbing and Stage A/B/C helpers live under `dbex/refinement/stage_*.py` without importing `dbex.nanobrag_refinement`, keeping simulator/context seams reusable for SPEC-REALIGN-001.
  3. Torch HDF5 writer + telemetry schema stay unified with `/torch_diagnostics` (`dbex/io/writer.py` or equivalent) and Stage telemetry proves variance-weighted loss + sigma provenance per docs/spec-db-core.md §§57-68.
- Working Plan: `plans/active/ARCH-REFINE-001/implementation.md`
- Attempts History:
  * 2025-12-01T080903Z (implementation) — Relocated Stage A helpers to `dbex/refinement/stage_a_impl.py`:
    - Created stage_a_impl.py with all Stage A functions (quaternion helpers, StageAROIEntry/StageAContext dataclasses, _build_stage_a_context, _build_stage_a_params, _build_stage_a_lbfgs_closure, _run_stage_a_lbfgs, sync/retarget helpers, utility functions)
    - Removed old definitions from nanobrag_refinement.py and added imports from stage_a_impl
    - Updated dbex/refinement/stage_a.py and dbex/tools/stage_a_adam.py to import from new module
    - Resolved circular import by moving _clamp_log_cell_deltas and _get_sigma_floor_sq_tensor into stage_a_impl
    - Fixed type annotation (RefinementConfig → 'RefinementConfig') to avoid NameError
    - Metrics: test_stage_a_engine_delegation_telemetry PASSED, test_stage_b_shell_modifiers PASSED (1 test failure pre-existing, unrelated to refactoring)
    - Artifacts: `plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/` (pytest_stage_a_engine.log, pytest_stage_b_small.log, pytest_stage_a_helpers_collect.log)
    - Next Actions: Continue with Phase A.2 (create RefinementContext/JobContext dataclasses)
