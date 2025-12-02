# DBEX Fix Plan Ledger

**Last Updated:** 2025-12-02 (Trimmed ledger; full snapshots including this date now live in `docs/fix_plan_archive.md`)

## Working Agreements
- Continue logging every loop in this ledger with status + artifact pointer; detailed Attempts History older than the sections below lives in `docs/fix_plan_archive.md`.
- Status values: `pending`, `in_progress`, `blocked`, `done`, `archived`.
- Citation rule remains: whenever you touch a selector or plan row, note the artifact path in both this file and the plan’s reports directory.

---

## Execution Roadmap
> **Agent Rule:** Prioritize initiatives in lower-numbered tiers. Within a tier, follow dependency chains. Do not start a Tier N+1 item if a Tier N item is unblocked.


### Tier 1: Core Physics & Stability
**Goal:** Ensure the math is correct, the loss function is normative, Stage A/mapping parity holds (DB‑AT‑027/028/029), and the smoke tests are green.
- [ARCH-REFINE-001] (Refine Engine Modularization + Torch IO context) — **Done** (2025-12-01T161600Z: Phase A-E code landed; 2025-12-01T170500Z docs/finding wrap complete. Ready to archive once downstream initiatives pick up.)
- [ARCH-ENGINE-ARTIFACTS-001] (Engine artifact channel & Bragg unification) — *pending*

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
- [PERF-WARM-SIM-001] (Warm Simulator) — **blocked — Stage C panel-loss path diverges from Stage A, forcing +0.067 % χ² regression** (2025-12-01T214200Z: Full-detector telemetry shows `stage_a_final_chi2=2.10706464e+08` while every Stage C validation records `2.10848512e+08` even with zero detector offsets. Trusted-mask parity, ROI wiring, and best-snapshot persistence are now correct; the remaining drift comes from Stage C’s duplicated panel-mode loss computation. Stage A’s panel branch keeps evolving (trusted-mask intersection, mask ordering, telemetry), but Stage C’s forked copy lagged behind. Until Stage C reuses the exact Stage A helper for panel-mode loss, REFINE-007 can’t pass because Stage C effectively measures a different pixel population before detector offsets change.)
- [ARCH-STAGE-CONTEXT-001] (Stage context + engine artifact boundary) — **done** (2025-12-02T160500Z: Phase E telemetry dataclass enforcement landed, Stage A/B/C smokes passed, and artifacts/writer consumers now rely solely on typed contexts; see `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/`). Stage helpers now own their closures/telemetry, RefinementEngine traffics typed artifacts, and the problems-ledger design-debt item is resolved.

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
  * 2025-12-01T080903Z — Stage A helper relocation completed; Stage A/B smoke selectors passed using the new `stage_a_impl.py` module. Artifacts: `plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/`.
  * 2025-12-01T084505Z — Phase A.2 scope locked for Stage B helper extraction; parity tests queued per `docs/TESTING_GUIDE.md`. Artifacts: `plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z/`.
  * ... (see `docs/fix_plan_archive.md` and `plans/active/ARCH-REFINE-001/reports/` for full history, metrics, and future attempt logs.)

### [ARCH-ENGINE-ARTIFACTS-001] RefinementEngine Artifact Channel & Final-Bragg Unification
- Depends on: ARCH-REFINE-001 (engine modularization baseline), ARCH-REFINE-FLOW-001 (stage wrappers, telemetry contract)
- Status: pending
- Priority: High
- Tier: 1
- Owner/Date: Codex / 2025-12-02
- Exit Criteria:
  1. `RefinementEngine` exposes a documented artifact map populated by executed stages without private attribute access (docs/spec-db-workflow.md §33).
  2. Stage B and Stage C wrappers emit their final Bragg tensors via the artifact channel with ≤1e-6 relative MSE versus current reconstruction helpers (REFINE-FLOW-001).
  3. `run_nanobrag_refinement` uses a single engine path, reading the last stage’s artifact for final Bragg and no longer calling `_build_final_bragg_from_stage_b_telemetry` or `_stage_c_bragg_full`.
- Working Plan: `plans/active/ARCH-ENGINE-ARTIFACTS-001/implementation.md`
- Attempts History:
  * 2025-12-02T000000Z — Initiative logged, specs cross-referenced, and plan scaffolded; no code yet lands until ARCH-REFINE-001 helpers stabilize. Working notes live in `plans/active/ARCH-ENGINE-ARTIFACTS-001/implementation.md`.
  * ... (see `docs/fix_plan_archive.md` and `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/` for upcoming engineering attempts.)

-### [ARCH-STAGE-CONTEXT-001] Stage Context + Engine Artifact Boundary
- Depends on: ARCH-REFINE-001 (helper extractions), ARCH-ENGINE-002/003 findings (engine protocol + telemetry enrichment)
- Status: done (2025-12-02T160500Z: Phase E telemetry dataclass enforcement completed; Stage A/B/C smoketests passed under `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/`)
- Priority: High (unblocks engine artifact work and removes ledger-flagged design debt)
- Tier: 3 (Architectural Maturity)
- Owner/Date: Galph ↔ Ralph / 2025-12-02
- Initiative Type: architecture
- Exit Criteria:
  1. Stage A/B/C helpers consume typed dataclasses (`RefinementSharedContext`, `StageAExecutionContext`, etc.) instead of raw dicts/parameter clumps; signatures shrink to ≤5 positional args with type hints and mypy coverage.
  2. Stage classes own their LBFGS closures/telemetry (`StageA.run` no longer unpacks dicts from `_build_stage_a_lbfgs_closure`), emit `StageArtifacts`, and RefinementEngine caches those artifacts without stage-specific branches.
  3. `dbex/io/writer.py::write_torch_outputs` no longer back-computes Nelder–Mead scales; it consumes the engine artifacts/telemetry and focuses on serialization per docs/spec-db-interfaces.md. ✅ (Phase B.4 complete)
- Working Plan: `plans/active/ARCH-STAGE-CONTEXT-001/implementation.md`
- Ledger tie-in: Addresses the unchecked "bad design patterns/code smells" entry in `problems.md` (2025-12-01), specifically items 1, 2, 4, 7, and 8 (data clumps, anemic Stage classes, mutable telemetry dicts, engine branching).
- Next Actions:
  * **None — exit criteria satisfied.** Keep PERF-WARM-SIM-001 open for the remaining Stage C chi² drift; Stage B per-reflection failure remains tracked under TORCH-REFINE-004. Stage context initiative can be archived after the next sync cycle.
- Attempts History:
  * 2025-12-02T030800Z — Phase B.1 established `StageResult` + artifact dataclasses and rewired the engine caches; Stage A telemetry + Stage B shell smokes PASSED (`reports/2025-12-02T030800Z/`).
  * 2025-12-02T063500Z — Phase B.2/B.2.3 completed StageB/StageC closure inlining; Stage C small-detector smoke PASSED while full-detector run reproduced the known PERF-WARM-SIM-001 regression (`reports/2025-12-02T063500Z/`).
  * 2025-12-02T150500Z — Phases D.3/D.3.1 propagated final Bragg artifacts and added enforcement tests across Stage A/B + CLI writer; see `reports/2025-12-02T141500Z/` and `reports/2025-12-02T150500Z/`.
  * ... (see `docs/fix_plan_archive.md` and `plans/active/ARCH-STAGE-CONTEXT-001/reports/` for full attempt logs, metrics, and divergence analyses.)

## Attempts History

Detailed engineering logs now live in `docs/fix_plan_archive.md` (append-only snapshots; latest recorded 2025-12-02) and in each initiative’s `plans/active/<ID>/reports/` directory. This active ledger keeps high-level milestones only so it remains <70 kB while still pointing to the authoritative artifacts for every attempt.
