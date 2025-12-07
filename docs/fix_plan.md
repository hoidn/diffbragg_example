# DBEX Fix Plan Ledger

**Last Updated:** 2025-12-07 (Trimmed ledger; full snapshots including this date now live in `docs/fix_plan_archive.md`)

## Working Agreements
- Continue logging every loop in this ledger with status + artifact pointer; detailed Attempts History older than the sections below lives in `docs/fix_plan_archive.md`.
- Status values: `pending`, `in_progress`, `blocked`, `done`, `archived`.
- Citation rule remains: whenever you touch a selector or plan row, note the artifact path in both this file and the plan's reports directory.
- **Plan Directory Inventory:** Rerun `plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py` whenever a plan directory is added, removed, or marked for archival. Always run it with the rollup-config guard so roll-up coverage stays enforced and the appendix stays current:
  - `python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py --plans-root plans/active --fix-plan docs/fix_plan.md --rollup-config plans/active/PORTFOLIO-STATUS/rollups.json --out-dir plans/active/PORTFOLIO-STATUS/reports/<NEW_TIMESTAMP>/`
  - Do not skip `--rollup-config`; a missing rollup_report.md or any roll-up marked `✗ Missing section` invalidates the guard. Update the Plan Directory Inventory appendix with the new artifact path + counts each time the script runs.
- **Findings Ledger Cadence:** Rerun [FINDINGS-LEDGER-002] maintenance quarterly or when >10 findings are added/resolved. Follow `plans/active/FINDINGS-LEDGER-002/cadence_checklist.md` and commit artifacts to timestamped reports directory. Cross-reference cadence schedule in `docs/index.md` § Knowledge Base Ledger.

---

## Execution Roadmap
> **Agent Rule:** Prioritize initiatives in lower-numbered tiers. Within a tier, follow dependency chains. Do not start a Tier N+1 item if a Tier N item is unblocked.


### Tier 0: Refinement Architecture Finish
**Goal:** Finish the Protocol Engine refactor by removing legacy helpers/facades now that contexts and artifacts are in place, and align ARCH docs/contracts with implementation via enforcement tests.
- [ARCH-GRADIENT-FLOW-001] (Gradient Flow Restoration — DB-AT-010 Unblock) — **in_progress** (2025-12-07T220000Z: Phase A complete (i=138), Phase B.1 scoped (i=139). Evidence: 0 UNSAFE production patterns, 2 test harness gradient breaks identified (test_gradients.py:383 detector, :496 beam). Root cause: test harness calls `.item()` to extract scalars for dxtbx geometry construction. Fix scoped: implement tensor-valued overrides in config_factories.py (distance_mm_override, wavelength_override, 40-60 LOC), update test harness (remove `.item()` calls). Crystal tests deferred to Phase A.3 probe (suspected external dependency). DecisionStatus: exploring → patch_ready (dominant-hypothesis lock applied, confidence 0.95). Next: Ralph implements detector/beam fixes (i=139), expects 2/5 gradcheck PASS. Blocks: Gradient-Safe Profile conformance, DB-AT-SUITE-CARE-001 portfolio advancement. Artifacts: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/` (planning_notes.md, summary.md))
  - **Governed by:** GRADIENT-001, RUNTIME-001, TESTING-003
- [ARCH-IMPL-CONFORMANCE-001] (Architecture / Implementation contract alignment) — **done** (2025-12-07T054500Z: Phases A-B complete; ARCH-CONTRACT-002/003 delivered with enforcement tests; exit criteria 3.5/4 satisfied; artifacts under `archive/plans/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T054500Z/initiative_closure_summary.md`)
- [DIAG-NANOBRAGG-OVERSAMPLE-001] (nanobrag_torch oversample parameter investigation) — **done** (2025-12-09T153000Z: Phase F HKL stats + Stage-A instrumentation closed out diagnostics; artifacts under `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-09T153000Z/` now cover oversample, beam flux, and HKL evidence)
- [ARCH-SIM-HKL-BOUNDS-001] (Stage-A / mapping HKL alignment) — **done** (2025-12-03T154217Z: incident-beam sign fix restored 100% HKL coverage; DB-AT-028/029 intensity failure delegated to ARCH-SIM-CONSTRUCTION-001; artifacts under `plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/`)
- [ARCH-SIM-CONSTRUCTION-001] (Simulator Construction Convention Alignment) — **blocked_pending_environment** (**Blocked:** Omega hypothesis rejected (C.39 evidence proves deficit exists in raw subpixel sum before omega application). F_latt shows 11% of expected amplitude, but observed intensity is 9.4% of expected, suggesting sincg lattice factor computation bug in nanobrag_torch. Further instrumentation violates PROBE-FREEZE-001. Blocked pending: (a) nanobrag_torch maintainer investigation, (b) spec_change to relax DB-AT-028/029 criteria, or (c) harness-grade diagnostic initiative outside plan-local probes. Artifacts: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T150000Z/summary.md` (omega diagnosis correction), cross-refs to C.34-C.39 evidence.)
- [ARCH-PROBE-FREEZE-001] (Probe Freeze & Logging Consolidation) — **done** (2026-01-02T180000Z: All phases complete. Phase A: cataloged 53 plan-local scripts, classified 45 thin_wrappers, 7 shadow_pipelines, 1 retire_candidate, identified 16 scripts exceeding 400 LOC cap. Phase B: migrated shadow pipelines to owner APIs (dbex.tools), reduced key shims to <40 LOC thin wrappers. Phase C: delivered enforcement test `tests/architecture/test_probe_contracts.py` (C.1), expanded `prompts/supervisor.md::diagnostic_script_policy` + added `docs/findings.md::PROBE-FREEZE-001` (C.2/C.3). Problems Ledger directive "Freeze plan-local probe scripts" now resolved. Artifacts: `plans/active/ARCH-PROBE-FREEZE-001/reports/2026-01-01T010000Z/` (Phase C completion) + `plans/active/ARCH-PROBE-FREEZE-001/reports/2026-01-02T180000Z/` (closure verification).)
- [ARCH-REFACTOR-001] (Refinement Engine Modularization & Physics Separation) — *blocked_pending_architecture* (Phase D.3 blocked by ARCH-SIM-CONSTRUCTION-001; Phases A-C complete)
  - **Governed by:** REFINE-001, ARCH-ENGINE-002, ARCH-ENGINE-003, ARCH-FACTORY-001, ARCH-FACTORY-003
- [ARCH-TELEMETRY-001] (Telemetry Observer Refactor) — **archived** (2025-12-04T235959Z: all phases complete, exit criteria satisfied)
- [ARCH-BRIDGE-RESP-001] (Writer / bridge responsibility split) — **archived** (2025-12-03T140000Z: all phases complete, moved to archive/plans/)
- [ARCH-LAZY-IMPORTS-001] (Lazy imports / process-noise hygiene) — **archived** (2025-12-05T024500Z: all phases complete, exit criteria satisfied; see `archive/plans/ARCH-LAZY-IMPORTS-001/reports/2025-12-05T024500Z/initiative_closure_summary.md`)
- [PORTFOLIO-STATUS] (Plan/Fix-Plan synchronization & archive hygiene) — **done**. All Phases A–F complete. Delivered inventory automation with roll-up-aware tracking, classification/archival of stale plans, comprehensive ledger coverage (Tier 0-4 initiatives + 13 roll-up sections), and Plan Directory Inventory appendix maintenance. Final inventory (`plans/active/PORTFOLIO-STATUS/reports/2025-12-07T220000Z/`) showed 100% ledger coverage: 55 total plans, 28 tracked directly, 34 via rollups, 0 active_missing, 0 missing_plan. Phase F (stale plan directory archival) complete: moved ARCH-LAZY-IMPORTS-001, ARCH-TELEMETRY-001, and ARCH-BRIDGE-RESP-001 to `archive/plans/`, updated all ledger references, verified zero untracked plans via guard automation. Closure artifacts: `plans/active/PORTFOLIO-STATUS/reports/2025-12-08T190000Z/`.

### Tier 1: Core Physics & Stability
**Goal:** Ensure the math is correct, the loss function is normative, Stage A/mapping parity holds (DB‑AT‑027/028/029), and the smoke tests are green.
- [ARCH-REFINE-001] (Refine Engine Modularization + Torch IO context) — **Done** (2025-12-01T161600Z: Phase A-E code landed; 2025-12-01T170500Z docs/finding wrap complete. Ready to archive once downstream initiatives pick up.)
- [ARCH-ENGINE-ARTIFACTS-001] (Engine artifact channel & Bragg unification) — **archived** (2025-12-02T185000Z, see docs/fix_plan_archive_2025-12-02.md)
- [DB-AT-SUITE-CARE-001] (Acceptance suite upkeep for DB-AT-002/010/020/021/022/023/024) — **pending**.
  - **Governed by:** TESTING-003, RUNTIME-001, DIAGNOSTICS-001, MASKING-001
  - The plan directories under `plans/active/DB-AT-002/`, `.../DB-AT-010/`, and `.../DB-AT-020` through `.../DB-AT-024/` already contain implementation plans, but none were represented in this ledger. Scope: keep the DB-AT selectors mapped to fix-plan items, document status per selector, and surface artifacts/blocked states in the Attempts History. Classification reference: `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T150000Z/classification.md`.
- [MAP-SCALE-SYNC-001] (Calibration ladder initiatives MAP-SCALE-001—005) — **pending**.
  - **Governed by:** SCALE-001, SCALE-002, SCALE-003, SCALE-004, SCALE-005, SCALE-006, SCALE-007
  - Plans live under `plans/active/MAP-SCALE-00X/` with November 2025 reports; ledger coverage will capture their goals (sigma provenance, spot-scale alignment) and unblock downstream physics/loss work.
- [PHYSICS-LOSS-001] (Variance-weighted loss parity and telemetry fixes) — **pending**. Plan exists under `plans/active/PHYSICS-LOSS-001/implementation.md`; add ledger tracking so variance, sigma-floor, and telemetry corrections remain visible.
- [PHYSICS-LOSS-CONSISTENCY] (Physics Loss Function Alignment) — **pending**.
  - **Governed by:** PHYSICS-LOSS-001, PHYSICS-LOSS-002, PHYSICS-LOSS-003, PHYSICS-LOSS-004, PHYSICS-LOSS-005
  - **Goal:** Align Stage A/B/C chi-squared computation, enforce sigma-floor guard, unify sigma-map ingestion contract, harvest DIALS external_lookup metadata.
  - **Exit Criteria:** All stages use identical variance-weighted denominator per spec-db-core.md:57-68; telemetry persists both chi_squared + masked_mse; sigma-floor enforcement validated via unit tests; sigma-map/external_lookup ingestion contracts tested.
  - **Dependencies:** ARCH-REFACTOR-001 (Stage A/B/C context + observer pattern provides hooks for unified loss computation).
- [TORCH-GEOMETRY-SYNC-001] (Geometry convergence/parity/UB realign initiatives) — **pending**.
  - **Governed by:** GEOMETRY-001, GEOMETRY-002, GEOMETRY-003, GEOMETRY-004, CONFIG-001, DXTBX-001, HKL-ORIENT-001, CONVERGENCE-001
  - Covers `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/`, `.../TORCH-GEOMETRY-PARITY-002/`, `.../TORCH-GEOMETRY-PARITY-003/`, and `.../TORCH-GEOMETRY-UB-REALIGN-001/`.
- [TORCH-REFINE-CLEANUP-001] (Stage A/B/C refinement probes TORCH-REFINE-001/002/002D/002E/003) — **pending**.
  - **Governed by:** REFINE-001, REFINE-002, REFINE-003, REFINE-006, REFINE-009, REFINE-010, GRADIENT-001, REFINE-016
  - Ledger entry will consolidate their status and dependencies so portfolio steering can decide which Phase C/D tasks to revive.
- [TORCH-CLI-BRIDGE-ROLLUP-001] (CLI + bridge backlog TORCH-CLI-003/004 and TORCH-BRIDGE-001) — **pending**. Ensures CLI/backend features and bridge refactors remain on the roadmap with artifact pointers.
- [FORWARD-EQUIV-COVERAGE-001] (Forward-equivalence harness + parity scaffolding) — **pending**.
  - **Governed by:** PARITY-001, MANIFEST-001
  - Covers `plans/active/FORWARD-EQUIV-001/`, `.../FORWARD-EQUIV-002/`, and `plans/active/PARITY-HARNESS-002/`.
- [TOOLING-VIS-001] (Mapping-aligned visualization tooling) — **pending**. Plan exists with recent reports; ledger coverage will document progress on canonical visuals.
- [DOCS-ROADMAP-001] (Roadmap documentation refresh) — **pending**. Needs ledger visibility so doc graph changes are tracked alongside implementation.
- [RUNTIME-VEC-001] (Runtime vectorization checklist enforcement) — **pending**. Adds ledger coverage for performance guardrails already planned under `plans/active/RUNTIME-VEC-001/`.
- [REPORT-NANOBRAG-STATUS-001] (Status reporting scripts) — **pending**. Keeps the reporting automation plan on the roadmap.
- [NANOBRAG-GOLDEN-001] (Golden dataset capture + maintenance) — **pending**. Ledger entry will document refresh cadence and outstanding action items.
- [FINDINGS-LEDGER-002] (Findings ledger upkeep and knowledge base maintenance) — **done** (2025-12-07T124500Z: All phases complete except deferred B.3+C.2. Exit criteria 4/4 satisfied. Closure summary: `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T124500Z/closure_summary.md`). Full implementation plan authored 2025-12-03: Phase A (ledger audit + citation fixes + inventory), Phase B (cross-linking findings ↔ fix-plan), Phase C (cadence/automation). **Phase A.2 complete (2025-12-03T120250Z)**: Fixed REFINE-005 duplicate entry to include code citations; achieved **100% path:line coverage (86/86 findings)**. Status breakdown: Active=74, Resolved=10, Deferred=1, Retracted=1. **Phase B.2 complete (2025-12-07T080000Z)**: Established reciprocal cross-links between `docs/findings.md` and `docs/fix_plan.md`. Updated 7 existing Tier 1 & Tier 2 initiatives with "Governed by" lines. Created 2 new initiatives: [PHYSICS-LOSS-CONSISTENCY] (Tier 1, 5 findings), [ARCH-STAGE-CONTEXT-CONSOLIDATION] (Tier 2, 2 findings). Annotated 58/74 Active findings (78.4%) with "**Consumers:** [INITIATIVE-ID]." metadata. **Coverage target met:** ≥78% ✅. Artifacts: `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T080000Z/{summary.md,consumer_map_v2.json,add_consumers.py}`. **Phase B.3 DEFERRED** (archive/retire candidates require pytest validation). **Phase C complete (2025-12-07T100000Z)**: Delivered cadence checklist template (`cadence_checklist.md`) with 5-phase quarterly maintenance workflow; updated `docs/index.md` § Knowledge Base Ledger and `docs/fix_plan.md` Working Agreements with cadence cross-references. C.2 (automation hook) deferred — manual cadence sufficient. Artifacts: `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T100000Z/{summary.md,planning_notes.md}`.

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
- [PERF-WARM-SIM-001] (Warm Simulator) — **blocked — Stage C panel-loss path diverges from Stage A, forcing +0.067 % χ² regression**.
  - **Governed by:** PERF-WARM-001, PERF-WARM-002, PERF-WARM-003, PERF-WARM-004, PERF-WARM-005, PERF-WARM-006, PERF-WARM-007, PERF-WARM-008, PERF-WARM-009, PERF-WARM-010, PERF-WARM-011, PERF-WARM-012, PERF-WARM-013, REFINE-007, REFINE-011, REFINE-012
  - (2025-12-01T214200Z: Full-detector telemetry shows `stage_a_final_chi2=2.10706464e+08` while every Stage C validation records `2.10848512e+08` even with zero detector offsets. Trusted-mask parity, ROI wiring, and best-snapshot persistence are now correct; the remaining drift comes from Stage C’s duplicated panel-mode loss computation. Stage A’s panel branch keeps evolving (trusted-mask intersection, mask ordering, telemetry), but Stage C’s forked copy lagged behind. Until Stage C reuses the exact Stage A helper for panel-mode loss, REFINE-007 can’t pass because Stage C effectively measures a different pixel population before detector offsets change. Phase F instrumentation (2025-12-02T173000Z) confirmed ROI simulators retarget correctly yet ROI-mode closures still run even when Stage A forces panel validations, so REFINE-012 remains unmet; next action is to disable ROI closures whenever `validation_scope=\"panel\"`, update smoketest assertions, and rerun Stage C small/full smokes under the new artifact set.)
- [ARCH-STAGE-CONTEXT-001] (Stage context + engine artifact boundary) — **done** (2025-12-02T160500Z: Phase E telemetry dataclass enforcement landed, Stage A/B/C smokes passed, and artifacts/writer consumers now rely solely on typed contexts; see `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/`). Stage helpers now own their closures/telemetry, RefinementEngine traffics typed artifacts, and the problems-ledger design-debt item is resolved.
- [ARCH-STAGE-CONTEXT-CONSOLIDATION] (Stage Context Parameter Consolidation) — **pending**.
  - **Governed by:** ARCH-STAGE-CTX-001, ARCH-STAGE-CTX-002
  - **Depends on:** ARCH-REFACTOR-001 (Phases A-C complete — Stage A/B/C helpers now own their logic)
  - **Goal:** Replace 10–15 positional arguments in Stage helper signatures with single typed `context` parameter (extend StageAContext/StageBContext/StageCContext dataclasses); eliminate telemetry dict mutations in Stage B baseline parity guard by exposing typed setter methods.
  - **Exit Criteria:** Stage A/B/C `_build_*_params` and `_run_*_lbfgs` accept single context parameter; telemetry updates use dataclass property assignment or setter methods; enforcement test validates context immutability guarantees.
  - **Working Plan:** to be created under `plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/implementation.md`

### Tier 3: Tooling & Observability
**Goal:** Standardize visuals, documentation, and runtime guardrails.
- [DOC-RUNTIME-004] (Restore Runtime Checklist) — **Done** (2025-11-23T024449Z: all exit criteria met, runtime checklist restored with spec citations, references verified, validation artifacts complete)
- [TORCH-RUNTIME-002] (Runtime Harness Seed) — **Done** (2025-10-28T232744Z: all exit criteria satisfied, TESTING_GUIDE.md updated, selector registry synchronized)

### Tier 4: Orchestration & Agent Ops
**Goal:** Harden orchestration tooling, submodule robustness, and agent operation workflows.
- [HARDEN-SUBMODULE-ROBUSTNESS] (Submodule Robustness Hardening) — **pending** (2025-11-04T165400Z: reports exist, needs scoping and ledger coverage)
- [ORCH-ROBUST-001] (Orchestration Robustness) — **in_progress** (2025-11-05T050500Z: orchestration resiliency work tracked)
- [ORCH-CLAUDE-PATH-FIX-001] (Claude Path Fix) — **pending** (orchestration tooling path resolution)
- [ORCH-CLI-FALLBACK-001] (CLI Fallback) — **pending** (CLI resilience and fallback handling)
- [SUPERVISOR] (Supervisor Agent Documentation & Roadmap) — **pending** (2025-11-24T153000Z: roadmap assessment complete, supervisor meta-documentation pending)

---

## Active / Pending Initiatives

### [ARCH-REFACTOR-001] Refinement Engine Modularization & Physics Separation
- **Governed by:** REFINE-001, ARCH-ENGINE-002, ARCH-ENGINE-003, ARCH-FACTORY-001, ARCH-FACTORY-003
- Depends on: ARCH-REFINE-FLOW-001, ARCH-REFINE-001, ARCH-STAGE-CONTEXT-001
- Status: blocked_pending_architecture (Phase D.3 blocked by ARCH-SIM-CONSTRUCTION-001; Phases A-C complete)
- Priority: Highest
- Tier: 0
- Owner/Date: Galph ↔ Ralph / 2025-12-02
- Exit Criteria:
  1. `dbex/refinement/stage_a_impl.py`, `stage_b_impl.py`, `stage_c_impl.py` are deleted and their logic lives in `StageA/B/C` classes.
  2. All torch refinement entrypoints (CLI, tools, tests) call `RefinementEngine` + `StageA/B/C` directly (no inline helpers).
  3. `dbex/nanobrag_refinement.py` is deleted after all call sites migrate to the Engine.
  4. `RefinementEngine.run` accepts only dict inputs containing `RefinementContext` under the `context` key.
  5. Stage A/B/C smoketests and DB‑AT selectors pass using the Engine path; DiffBragg backend continues to pass its smoketests.
- Working Plan: `plans/active/ARCH-REFACTOR-001/implementation.md`
- Attempts History:
  * 2025-12-04T120500Z — see docs/fix_plan_archive.md for details.
  * 2025-12-02T233717Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/ARCH-REFACTOR-001/reports/ for full Attempts History and metrics).

### [ARCH-SIM-CONSTRUCTION-001] Simulator Construction Convention Alignment (Training vs Reconstruction)
- Depends on: None
- Blocks: ARCH-REFACTOR-001 Phase D.3
- Status: **blocked_pending_environment** (**BLOCKED** — 2026-01-13T200000Z: Omega hypothesis rejected (C.39) after deficit proven to exist in raw subpixel sum BEFORE omega application. F_latt at 11% of expected amplitude indicates sincg lattice factor bug in nanobrag_torch itself. PROBE-FREEZE-001 forbids further plan-local instrumentation. Lifecycle budget exceeded: 39 loops (C.1-C.39) vs 6-loop hard limit without validated first-divergence or monotonic improvement. Three unblock options: (A) maintainer investigation [RECOMMENDED], (B) spec_change to relax DB-AT-028/029, (C) harness-grade diagnostic initiative. Artifacts: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T200000Z/lifecycle_decision.md`)
- Type: architecture
- Priority: Highest (Tier 0 blocker)
- Tier: 0
- Owner/Date: Galph ↔ Ralph / 2025-12-02
- Exit Criteria:
  1. Reconstruction simulator raw output magnitude matches Stage A simulator raw output (within 1% for same parameters)
  2. DB-AT-028: `chi²/pixel initial ≤ 1e2`
  3. DB-AT-029: `median ROI correlation before ≥ 0.2`
  4. No external API changes (internal alignment only)
  5. Factory contract documentation updated
- Working Plan: `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md`
- Attempts History:
  * 2025-12-02T233717Z (Phase A.1 complete — see docs/fix_plan_archive.md for details.
  * 2026-01-13T150000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/ARCH-SIM-CONSTRUCTION-001/reports/ for full Attempts History and metrics).

### [ARCH-IMPL-CONFORMANCE-001] Architecture / Implementation Contract Alignment
- Depends on: None
- Blocks: None (architectural hygiene)
- Status: **done** (2025-12-07T054500Z: Phases A-B complete; ARCH-CONTRACT-002/003 delivered with enforcement tests; exit criteria 3.5/4 satisfied; artifacts under `archive/plans/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T054500Z/initiative_closure_summary.md`)
- Type: architecture
- Priority: High (Tier 0)
- Tier: 0
- Owner/Date: Galph ↔ Ralph / 2026-01-13
- Exit Criteria:
  1. Explicit ARCH-CONTRACTs defined for: (a) simulator factory scope, (b) post-run scaling pattern, (c) mapping → Stage A baseline override
  2. Canonical owner APIs created for duplicated scaling/calibration semantics
  3. Stage A and reconstruction refactored to use canonical APIs (duplicates removed)
  4. Enforcement tests added under `tests/architecture/` to prevent future drift
  5. Architecture docs updated with ARCH-CONTRACT definitions
- Working Plan: `archive/plans/ARCH-IMPL-CONFORMANCE-001/implementation.md`
- Working Plan: `plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md`
- Attempts History:
  * See docs/fix_plan_archive.md (snapshot 2025-12-07) and plans/active/ARCH-IMPL-CONFORMANCE-001/reports/ for full Attempts History.

### [DIAG-NANOBRAGG-OVERSAMPLE-001] nanobrag_torch Oversample Parameter Investigation
- Depends on: None
- Blocks: ARCH-SIM-CONSTRUCTION-001 (reconstruction magnitude discrepancy)
- Status: done (Phase F diagnostics closed 2025-12-09; remaining HKL/intensity work handed to ARCH-SIM-HKL-BOUNDS-001 + ARCH-SIM-CONSTRUCTION-001)
- Type: diagnostics
- Priority: Highest (Tier 0, unblocks ARCH-SIM-CONSTRUCTION-001)
- Tier: 0
- Owner/Date: Galph ↔ Ralph / 2025-12-02
- Exit Criteria:
  1. Debug instrumentation added to `nanobrag_torch/simulator.py` to log oversample parameter flow
  2. Patch file saved to `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/nanobrag_debug_instrumentation.patch`
  3. nanobrag_torch rebuilt successfully with debug instrumentation
  4. DB-AT-028 rerun with debug output captured in artifacts
  5. Root cause identified from debug logs (Case A/B/C)
  6. Findings documented in `docs/findings.md` with DIAG-NANOBRAGG-OVERSAMPLE-001 tag
  7. Environment state tagged (e.g., "nanobragg-debug-oversample-2025-12-03")
- Working Plan: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/implementation.md`
- Attempts History:
  * See docs/fix_plan_archive.md (snapshot 2025-12-07) and plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/ for full Attempts History.

### [ARCH-SIM-HKL-BOUNDS-001] Stage-A / Mapping HKL Alignment
- Depends on: DIAG-NANOBRAGG-OVERSAMPLE-001
- Status: in_progress (Phase A.1 complete, Phase B next)
- Priority: Highest (Tier 0)
- Tier: 0
- Owner/Date: Galph ↔ Ralph / 2025-12-03
- Exit Criteria:
  1. `probe_crystal_hkl_alignment.py` reports `max_abs_diff(A*_nanobrag, A*_dxtbx) ≤ 1e-6 Å⁻¹`.
  2. HKL stats for both mapping forward helper and Stage A warm cache show ≥99% in-bounds queries on refGeom smoke fixture; artifacts stored under plan reports.
  3. DB-AT-028/029 small-detector selectors PASS once HKL coverage is restored.
  4. `docs/findings.md` documents the fix and ARCH-SIM-CONSTRUCTION-001 is unblocked.
- Working Plan: `plans/active/ARCH-SIM-HKL-BOUNDS-001/implementation.md`
- Attempts History:
  * 2025-12-03T150219Z — see docs/fix_plan_archive.md for details.
  * 2025-12-03T152326Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/ for full Attempts History and metrics).

### [ARCH-REFINE-001] — **archived** (2025-12-01T161600Z, see docs/fix_plan_archive_2025-12-02.md)
- Refinement Engine Modularization + Torch IO context complete
- Full history: docs/fix_plan_archive_2025-12-02.md, plans/active/ARCH-REFINE-001/reports/
- Working Plan: `plans/active/ARCH-REFINE-001/implementation.md`

### [ARCH-TELEMETRY-001] Telemetry Observer Refactor
- Depends on: ARCH-STAGE-CONTEXT-001 (typed contexts), PHYSICS-LOSS-001 (telemetry χ² spec), problems.md observer directive
- Status: archived (2025-12-04T235959Z — all exit criteria satisfied, see closure summary)
- Priority: High
- Tier: 0
- Owner/Date: Galph ↔ Ralph / 2025-12-02
- Initiative Type: architecture
- Exit Criteria:
  1. Stage A/B/C no longer mutate `telemetry_state` or dict shims; closures emit observer callbacks captured in typed telemetry/result dataclasses.
  2. RefinementEngine + writer read `StageResult` artifacts (StageATelemetry/StageBTelemetry/StageCTelemetry) directly with no Nelder–Mead reruns or dict patching.
  3. Stage A/B/C smoketests and canonical Stage diagnostics keep REFINE-007/008/012 and PHYSICS-LOSS-001 gates green using the observer channel.
  4. `/torch_diagnostics` schema stays spec-compliant and test registry entries referencing telemetry selectors are updated.
- Working Plan: `archive/plans/ARCH-TELEMETRY-001/implementation.md`
- Closure Summary: `archive/plans/ARCH-TELEMETRY-001/reports/2025-12-04T235959Z/initiative_closure_summary.md`
- Ledger tie-in: addresses problems.md entry "Refactor: Decouple Telemetry from Refinement Logic using Observer Pattern" (architectural issues 1.3/2.3). Plan captures Observer pattern, Stage-specific telemetry collectors, and writer simplification.
- Working Plan: `plans/active/ARCH-TELEMETRY-001/implementation.md`
- Attempts History:
  * See docs/fix_plan_archive.md (snapshot 2025-12-07) and plans/active/ARCH-TELEMETRY-001/reports/ for full Attempts History.

### [ARCH-GRADIENT-FLOW-001] Gradient Flow Restoration (DB-AT-010 Unblock)
- Depends on: DB-AT-SUITE-CARE-001 Phase B.1 verification (evidence source)
- Blocks: DB-AT-SUITE-CARE-001 portfolio advancement, Gradient-Safe Profile conformance
- Status: **in_progress** (Phase A planning complete, Phase A.1-A.2 execution next)
- Type: architecture
- Priority: Tier 0 (blocks conformance profile)
- Owner/Date: Galph ↔ Ralph / 2025-12-07
- Exit Criteria:
  1. Gradient flow restored: DB-AT-010 gradcheck tests pass (5/5) with documented tolerances (eps=1e-6, atol=1e-5, rtol=0.05)
  2. Root cause identified and fixed: Code audit locates `.item()` coercion or tensor detachment; patch applied
  3. Enforcement test added: `tests/architecture/test_gradient_contracts.py` validates gradient flow preservation
  4. Documentation updated: `docs/findings.md` GRADIENT-002, `docs/architecture.md` §13 gradient hygiene guardrail
  5. Regression validation: Full DB-AT-010 suite passes; `docs/development/TEST_SUITE_INDEX.md` status updated
- Working Plan: `plans/active/ARCH-GRADIENT-FLOW-001/implementation.md`
- Attempts History:
  * 2025-12-07T220000Z (Loop i=139, Galph) — Phase B.1 planning: Transitioned from Phase A (evidence) → Phase B.1 (partial fix). Applied dominant-hypothesis lock (confidence 0.95 for detector/beam fixes) + implementation floor (1 turn evidence, must implement). Scoped Phase B.1: implement tensor-valued overrides in config_factories.py (distance_mm_override, wavelength_override, ~40-60 LOC), update test harness (remove `.item()` calls at test_gradients.py:383, :496), validate 2/5 gradcheck tests PASS. Crystal tests deferred to Phase A.3 probe (suspected external dependency). DecisionStatus: exploring → patch_ready. Next: Ralph implements detector/beam fixes (i=139). Artifacts: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/` (planning_notes.md, summary.md).
  * 2025-12-07T212000Z (Loop i=138, Ralph) — Phase A.1-A.2 complete: Call graph trace (7 levels) + suspect module audit (4 modules, 6 grep patterns). Evidence: 0 UNSAFE production patterns, 2 critical test harness gradient breaks (test_gradients.py:383 detector distance, :496 beam wavelength using `.item()` to extract scalars). Hypothesis: dxtbx geometry construction requires scalars, test harness breaks gradient graph. Crystal tests use correct pattern but still fail (suspected external nanobrag_torch dependency). Top hypothesis confidence: 0.95 (detector/beam), 0.6 (crystal). Phase A.3 probe deferred. Artifacts: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/` (call_graph_trace.md, suspect_audit.md, 6 grep files, summary.md).
  * 2025-12-07T210000Z (Loop i=137, Galph) — Phase A planning: Created initiative in response to DB-AT-SUITE-CARE-001 Phase B.1 verification (Ralph i=136) showing DB-AT-010 gradcheck regression persists (5/5 tests FAILING, disconnected autograd graph). Authored implementation.md with Phases A/B/C (call graph trace, suspect audit, gradient probe, fix, enforcement test, closure). Scoped 4 suspect modules (forward.py, crystallography.py, loss.py, inputs.py). Estimated effort: 5-7 loops. Next: Phase A.1-A.2 (call graph + suspect audit). Artifacts: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T210000Z/` (implementation.md, planning_notes.md).
  * ... (see plans/active/ARCH-GRADIENT-FLOW-001/reports/ for continued Attempts History).

### [DB-AT-SUITE-CARE-001] Acceptance Suite Upkeep (DB-AT-002/010/020—024)
- Depends on: ARCH-GRADIENT-FLOW-001 (DB-AT-010 unblock for portfolio advancement)
- Status: in_progress (Phase B.1 complete — escalated to ARCH-GRADIENT-FLOW-001; Phase B.2-B.7 pending Tier-0 resolution)
- Type: harness
- Priority: High (Core acceptance gates)
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. All DB-AT-002/010/020/021/022/023/024 selectors mapped in `docs/TESTING_GUIDE.md` with current artifact pointers
  2. Median ROI correlation ≥ 0.2 per `docs/spec-db-conformance.md` §DB-AT acceptance criteria
  3. Chi²/pixel ≤ 1e2 per spec DB-AT-002/010 parity gates
  4. Determinism gates (DB-AT-023/024) pass with seed-locked runs
- Working Plan: `plans/active/DB-AT-SUITE-CARE-001/implementation.md`
  5. Latest test reports captured under member plan directories with status documented in Attempts History below
- Attempts History:
  * 2025-12-05T150000Z — see docs/fix_plan_archive.md for details.
  * 2025-12-07T100000Z — see docs/fix_plan_archive.md for details.
  * 2025-12-07T204336Z (Loop i=136, Ralph) — Phase B.1 complete (second attempt): DB-AT-010 verification executed (5 tests, exit code 1, 0/5 passed). All gradcheck tests fail with GradcheckError: disconnected autograd graph. Harness stable (no collection errors, Phase B.3/B.4 fixes successful). Tier-0 blocker confirmed: gradient flow break in simulate_forward_torch or TorchCrystal bridge. Escalated to ARCH-GRADIENT-FLOW-001 (Tier 0) per implementation.md Phase B.1 directive. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/` (verification report, pytest log, summary).
  * 2025-12-07T210000Z (Loop i=137, Galph) — Created ARCH-GRADIENT-FLOW-001 to execute Tier-0 escalation; DB-AT-SUITE-CARE-001 now blocked pending gradient flow fix. Portfolio advancement paused until ARCH-GRADIENT-FLOW-001 Phase B complete (gradcheck 5/5 PASS).
  * ... (see docs/fix_plan_archive.md and plans/active/DB-AT-SUITE-CARE-001/reports/ for full Attempts History and metrics).

### [MAP-SCALE-SYNC-001] Calibration Ladder Synchronization (MAP-SCALE-001—005)
- Depends on: None
- Status: done
- Type: spec_change (calibration conventions)
- Priority: High (unblocks PHYSICS-LOSS-001)
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. Calibration precedence documented per `docs/spec-db-workflow.md` "Calibration & Unit Conventions"
  2. Sigma provenance work tracked with artifact pointers
  3. Spot-scale alignment complete per `docs/config_crosswalk.md`
  4. Telemetry provenance gates documented in member plans with test selectors
- Working Plan: `plans/active/MAP-SCALE-SYNC-001/implementation.md`
- Attempts History:
  * See docs/fix_plan_archive.md (snapshot 2025-12-07) and plans/active/MAP-SCALE-SYNC-001/reports/ for full Attempts History.

### [PHYSICS-LOSS-001] Variance-Weighted Loss Parity and Telemetry
- Depends on: MAP-SCALE-SYNC-001 (calibration precedence)
- Status: done_with_environment_caveat
- Type: bugfix
- Priority: High (loss correctness)
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. Variance-weighted loss implementation matches `docs/spec-db-core.md` §Objective Function
  2. Sigma-floor telemetry corrections validated per `docs/TESTING_GUIDE.md` §1.4
  3. Completed phases documented in `plans/active/PHYSICS-LOSS-001/implementation.md`
- Attempts History:
  * See docs/fix_plan_archive.md (snapshot 2025-12-07) and plans/active/PHYSICS-LOSS-001/reports/ for full Attempts History.

### [TORCH-GEOMETRY-SYNC-001] Geometry Convergence & Parity Alignment
- Depends on: ARCH-REFINE-001 (Stage helpers stabilized)
- Status: pending
- Type: architecture
- Priority: High (zero-point correctness)
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. Zero-point invariants documented per `docs/spec-db-core.md` §Baseline Crystal State
  2. UB realignment complete per `docs/spec-db-workflow.md` §Stage A
  3. Convergence/parity probes pass with artifacts under member plan directories
  4. Dependencies on ARCH-REFINE-001 resolved and documented
- Working Plan: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/`, `plans/active/TORCH-GEOMETRY-PARITY-002/`, `plans/active/TORCH-GEOMETRY-PARITY-003/`, `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/`
- Spec References: `docs/spec-db-core.md` §Baseline Crystal State, `docs/spec-db-workflow.md` §Stage A
- Working Plan: `plans/active/TORCH-GEOMETRY-SYNC-001/implementation.md`
- Attempts History:
  * 2025-12-05T150000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/TORCH-GEOMETRY-SYNC-001/reports/ for full Attempts History and metrics).

### [TORCH-REFINE-CLEANUP-001] Stage A/B/C Refinement Cleanup (TORCH-REFINE-001/002/002D/002E/003)
- Depends on: ARCH-REFACTOR-001 (Stage modularization), PHYSICS-LOSS-001 (telemetry spec)
- Status: pending
- Type: architecture + perf
- Priority: Medium
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. Stage A/B/C telemetry cleanups complete per `docs/spec-db-workflow.md` §Stage B/C
  2. Stage B ASU gradient issues documented with mitigation plans
  3. Vectorization gates pass per `docs/spec-db-runtime.md` §Vectorization
  4. Gating selectors mapped in `docs/TESTING_GUIDE.md`
- Working Plan: `plans/active/TORCH-REFINE-001/`, `plans/active/TORCH-REFINE-002/`, `plans/active/TORCH-REFINE-002D/`, `plans/active/TORCH-REFINE-002E/`, `plans/active/TORCH-REFINE-003/`
- Spec References: `docs/spec-db-workflow.md` §Stage B/C, `docs/spec-db-runtime.md` §Vectorization
- Working Plan: `plans/active/TORCH-REFINE-CLEANUP-001/implementation.md`
- Attempts History:
  * 2025-12-05T150000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/TORCH-REFINE-CLEANUP-001/reports/ for full Attempts History and metrics).

### [TORCH-CLI-BRIDGE-ROLLUP-001] CLI & Bridge Infrastructure (TORCH-BRIDGE-001, TORCH-CLI-003/004)
- Depends on: REPORT-NANOBRAG-STATUS-001 (output schema)
- Status: pending
- Type: architecture + harness
- Priority: Medium
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. CLI backend flag wiring complete per `docs/spec-db-interfaces.md`
  2. Telemetry schema work documented in `docs/config_crosswalk.md`
  3. Bridge responsibility split tracked per `docs/architecture.md`
  4. Dependencies on REPORT-NANOBRAG-STATUS-001 output schema resolved
- Working Plan: `plans/active/TORCH-BRIDGE-001/`, `plans/active/TORCH-CLI-003/`, `plans/active/TORCH-CLI-004/`
- Spec References: `docs/spec-db-interfaces.md`, `docs/config_crosswalk.md`, `docs/architecture.md`
- Working Plan: `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md`
- Attempts History:
  * 2025-12-05T150000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/ for full Attempts History and metrics).

### [FORWARD-EQUIV-COVERAGE-001] Forward Equivalence & Parity Harness
- Depends on: NANOBRAG-GOLDEN-001 (dataset refresh)
- Status: pending
- Type: diagnostics
- Priority: Medium
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. Parity thresholds documented: median ROI correlation ≥ 0.2, localization ≥ 90% per `docs/spec-db-conformance.md` DB-AT-001
  2. Forward equivalence harness traces artifact requirements per `docs/forward_equivalence.md`
  3. Ties to NANOBRAG-GOLDEN-001 dataset refreshes documented
- Working Plan: `plans/active/FORWARD-EQUIV-001/`, `plans/active/FORWARD-EQUIV-002/`, `plans/active/PARITY-HARNESS-002/`
- Spec References: `docs/forward_equivalence.md`, `docs/spec-db-conformance.md` DB-AT-001
- Working Plan: `plans/active/FORWARD-EQUIV-COVERAGE-001/implementation.md`
- Attempts History:
  * 2025-12-05T150000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/FORWARD-EQUIV-COVERAGE-001/reports/ for full Attempts History and metrics).

### [TOOLING-VIS-001] Mapping-Aligned Visualization Tooling
- Depends on: None
- Status: pending
- Type: diagnostics
- Priority: Medium
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. Canonical triptychs/residual plots documented per `docs/spec-db-vis.md`
  2. Z-score histograms within ±3σ validated
  3. Radial profile overlays tested with artifacts under plan directory
- Working Plan: `plans/active/TOOLING-VIS-001/`
- Spec References: `docs/spec-db-vis.md`
- Working Plan: `plans/active/TOOLING-VIS-001/implementation.md`
- Attempts History:
  * 2025-12-05T150000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/TOOLING-VIS-001/reports/ for full Attempts History and metrics).

### [DOCS-ROADMAP-001] Roadmap Documentation Refresh
- Depends on: PORTFOLIO-STATUS (archive hygiene)
- Status: pending
- Type: docs
- Priority: Low
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. Publication cadence documented
  2. Dependencies on portfolio archive moves resolved
  3. Exit criteria for roadmap freshness defined in plan
- Working Plan: `plans/active/DOCS-ROADMAP-001/`
- Spec References: `docs/index.md`, `docs/development/testing_strategy.md`
- Working Plan: `plans/active/DOCS-ROADMAP-001/implementation.md`
- Attempts History:
  * 2025-12-05T150000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/DOCS-ROADMAP-001/reports/ for full Attempts History and metrics).

### [RUNTIME-VEC-001] Runtime Vectorization Checklist Enforcement
- Depends on: None
- Status: pending
- Type: perf
- Priority: Medium
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. Required smoke selectors (vectorization tests) mapped in `docs/TESTING_GUIDE.md`
  2. Dyno guardrails enforced per `docs/spec-db-runtime.md`
  3. Environment flags validated per `docs/pytorch_runtime_checklist.md`
- Working Plan: `plans/active/RUNTIME-VEC-001/`
- Spec References: `docs/pytorch_runtime_checklist.md`, `docs/spec-db-runtime.md`
- Working Plan: `plans/active/RUNTIME-VEC-001/implementation.md`
- Attempts History:
  * 2025-12-05T150000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/RUNTIME-VEC-001/reports/ for full Attempts History and metrics).

### [REPORT-NANOBRAG-STATUS-001] Status Reporting Scripts
- Depends on: None
- Status: pending
- Type: tooling
- Priority: Low
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. Scope for reporting scripts (status dashboards, parity metrics) documented
  2. CLI artifacts and scriptization policy referenced per `docs/TESTING_GUIDE.md`
  3. Exit criteria tied to `docs/development/testing_strategy.md`
- Working Plan: `plans/active/REPORT-NANOBRAG-STATUS-001/`
- Spec References: `docs/TESTING_GUIDE.md`, `docs/development/testing_strategy.md`
- Working Plan: `plans/active/REPORT-NANOBRAG-STATUS-001/implementation.md`
- Attempts History:
  * 2025-12-05T150000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/REPORT-NANOBRAG-STATUS-001/reports/ for full Attempts History and metrics).

### [NANOBRAG-GOLDEN-001] Golden Dataset Capture + Maintenance
- Depends on: None
- Status: pending
- Type: harness
- Priority: Medium
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. Golden dataset refresh cadence documented per `docs/development/testing_strategy.md` §2.5
  2. Trace outputs (images + trace logs) captured with artifact pointers
  3. Gating selectors consuming the dataset mapped in `docs/TESTING_GUIDE.md`
- Working Plan: `plans/active/NANOBRAG-GOLDEN-001/`
- Spec References: `docs/development/testing_strategy.md` §2.5, `docs/prompt_sources_map.json` (spec sources)
- Working Plan: `plans/active/NANOBRAG-GOLDEN-001/implementation.md`
- Attempts History:
  * 2025-12-05T150000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/NANOBRAG-GOLDEN-001/reports/ for full Attempts History and metrics).

### [ARCH-SPLIT-001] Architecture Interface Split
- Depends on: None
- Status: pending (review for archival)
- Type: architecture
- Priority: Low
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. Clarify whether initiative remains active or should be archived
  2. Exit criteria revolve around interface split ADR per `docs/architecture.md`
- Working Plan: `plans/active/ARCH-SPLIT-001/implementation.md`
- Spec References: `docs/architecture.md`, `plans/active/ARCH-SPLIT-001/implementation.md`
- Attempts History:
  * 2025-12-05T150000Z — see docs/fix_plan_archive.md for details.
  * 2025-12-03T021140Z (Phase C.3.2) — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/ARCH-SPLIT-001/reports/ for full Attempts History and metrics).

### [HARDEN-SUBMODULE-ROBUSTNESS] Submodule Robustness Hardening
- Depends on: CLAUDE.md orchestration guidelines, scripts/orchestration tooling
- Status: pending
- Type: architecture
- Priority: Medium (Orchestration infrastructure)
- Tier: 4
- Owner/Date: Galph ↔ Ralph / 2025-12-07
- Exit Criteria:
  1. Submodule dependency chains documented and tracked in orchestration tooling
  2. Resiliency tests demonstrate graceful degradation when submodules fail
  3. Tracked output patterns documented in `scripts/orchestration/README.md`
  4. Integration with orchestrator pre-pull/post-pull hooks validated
- Working Plan: `plans/active/HARDEN-SUBMODULE-ROBUSTNESS/implementation.md`
- Spec References: CLAUDE.md environment freeze policy, `scripts/orchestration/README.md`
- Attempts History:
  * 2025-11-04T165400Z — see docs/fix_plan_archive.md for details.
  * 2025-12-07T220000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/HARDEN-SUBMODULE-ROBUSTNESS/reports/ for full Attempts History and metrics).

### [ORCH-ROBUST-001] Orchestration Robustness
- Depends on: AGENTS.md, scripts/orchestration tooling
- Status: in_progress
- Type: architecture
- Priority: Medium (Orchestration infrastructure)
- Tier: 4
- Owner/Date: Galph ↔ Ralph / 2025-12-07
- Exit Criteria:
  1. Orchestration failure modes documented with recovery procedures
  2. Timeout handling and graceful degradation tested
  3. Loop resilience validated under concurrent agent execution
  4. Documentation in `scripts/orchestration/README.md` updated
- Working Plan: `plans/active/ORCH-ROBUST-001/implementation.md`
- Spec References: AGENTS.md orchestration rules, `scripts/orchestration/README.md`
- Attempts History:
  * 2025-11-05T050500Z — see docs/fix_plan_archive.md for details.
  * 2025-12-07T220000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/ORCH-ROBUST-001/reports/ for full Attempts History and metrics).

### [ORCH-CLAUDE-PATH-FIX-001] Claude Path Fix
- Depends on: CLAUDE.md, orchestration scripts
- Status: pending
- Type: harness
- Priority: Low (Tooling hygiene)
- Tier: 4
- Owner/Date: Galph ↔ Ralph / 2025-12-07
- Exit Criteria:
  1. Path resolution issues in orchestration scripts identified and fixed
  2. All orchestration tooling uses canonical paths per CLAUDE.md conventions
  3. Regression tests ensure paths remain stable across loop executions
- Working Plan: `plans/active/ORCH-CLAUDE-PATH-FIX-001/implementation.md`
- Spec References: CLAUDE.md file path conventions, `scripts/orchestration/README.md`
- Attempts History:
  * 2025-12-07T220000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/ORCH-CLAUDE-PATH-FIX-001/reports/ for full Attempts History and metrics).

### [ORCH-CLI-FALLBACK-001] CLI Fallback
- Depends on: CLAUDE.md, CLI tooling
- Status: pending
- Type: harness
- Priority: Low (Tooling robustness)
- Tier: 4
- Owner/Date: Galph ↔ Ralph / 2025-12-07
- Exit Criteria:
  1. CLI fallback paths documented for orchestration failure modes
  2. Manual recovery procedures tested and documented
  3. Graceful degradation when automated orchestration unavailable
- Working Plan: `plans/active/ORCH-CLI-FALLBACK-001/implementation.md`
- Spec References: CLAUDE.md, `scripts/orchestration/README.md`
- Attempts History:
  * 2025-12-07T220000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/ORCH-CLI-FALLBACK-001/reports/ for full Attempts History and metrics).

### [SUPERVISOR] Supervisor Agent Documentation & Roadmap
- Depends on: AGENTS.md supervisor rules, prompts/supervisor.md
- Status: pending
- Type: docs
- Priority: Medium (Meta-documentation)
- Tier: 4
- Owner/Date: Galph / 2025-12-07
- Exit Criteria:
  1. Supervisor operational guide documented with decision trees
  2. Roadmap assessment methodology captured in `plans/active/SUPERVISOR/`
  3. Integration between Galph and Ralph workflows clarified
  4. Meta-analysis patterns documented for portfolio steering
- Working Plan: `plans/active/SUPERVISOR/implementation.md`
- Spec References: AGENTS.md, prompts/supervisor.md
- Attempts History:
  * 2025-11-24T153000Z — see docs/fix_plan_archive.md for details.
  * 2025-12-04T050000Z (Phase C.3.1 implementatio... — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/SUPERVISOR/reports/ for full Attempts History and metrics).

### [ARCH-BRIDGE-RESP-001] — **archived** (2025-12-03T093500Z, see docs/fix_plan_archive_2025-12-02.md)
- Writer / bridge responsibility split complete
- Full history: docs/fix_plan_archive_2025-12-02.md, archive/plans/ARCH-BRIDGE-RESP-001/reports/
- Working Plan: `plans/active/ARCH-BRIDGE-RESP-001/implementation.md`

### [ARCH-LAZY-IMPORTS-001] Lazy imports / process-noise hygiene
- Depends on: ARCH-REFINE-001 (Stage helpers stabilized), ARCH-STAGE-CONTEXT-001 (typed contexts), ARCH-ENGINE-002 finding (lazy-import staging rules)
- Status: archived (2025-12-05T024500Z: all phases complete, exit criteria satisfied)
- Priority: High
- Tier: 0
- Owner/Date: Galph ↔ Ralph / 2025-12-02
- Initiative Type: architecture
- Exit Criteria:
  1. Geometry/physics leaf modules and Stage helper seams import their dependencies at module scope (with explicit optional guards) so diagnostics/tests see drift immediately; remaining lazy imports are documented exceptions.
  2. Docstrings/comments reference normative specs/findings instead of historical ticket IDs, reducing process-noise diffs.
  3. Import hygiene selector(s) cover these modules; docs/TESTING_GUIDE.md and TEST_SUITE_INDEX.md record them with collect-only logs under this initiative.
  4. Problems ledger entry "Lazy imports / process noise" links to this initiative and is marked done once the above hold.
- Working Plan: `archive/plans/ARCH-LAZY-IMPORTS-001/implementation.md`
- Working Plan: `plans/active/ARCH-LAZY-IMPORTS-001/implementation.md`
- Attempts History:
  * See docs/fix_plan_archive.md (snapshot 2025-12-07) and plans/active/ARCH-LAZY-IMPORTS-001/reports/ for full Attempts History.

### [ARCH-ENGINE-ARTIFACTS-001] — **archived** (2025-12-02T185000Z, see docs/fix_plan_archive_2025-12-02.md)
- RefinementEngine artifact channel & Bragg unification complete
- Full history: docs/fix_plan_archive_2025-12-02.md, plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/
- Working Plan: `plans/active/ARCH-ENGINE-ARTIFACTS-001/implementation.md`

### [ARCH-STAGE-CONTEXT-001] — **archived** (2025-12-02T160500Z, see docs/fix_plan_archive_2025-12-02.md)
- Stage context + engine artifact boundary complete
- Full history: docs/fix_plan_archive_2025-12-02.md, plans/active/ARCH-STAGE-CONTEXT-001/reports/
- Working Plan: `plans/active/ARCH-STAGE-CONTEXT-001/implementation.md`


## Attempts History

Detailed engineering logs now live in `docs/fix_plan_archive.md` (append-only snapshots; latest snapshot 2025-12-07) and in each initiative's `plans/active/<ID>/reports/` directory. This section keeps only high-level pointers so the live ledger stays within the size budget.

### [PORTFOLIO-STATUS] Attempts History
* See docs/fix_plan_archive.md (snapshot 2025-12-07) and `plans/active/PORTFOLIO-STATUS/reports/` for full Attempts History, inventory metrics, and roll-up coverage reports.

* For additional initiative-specific attempts previously inlined here (including ARCH-TELEMETRY-001 Phase C.2), refer to the same archive snapshots and the corresponding `plans/active/<ID>/reports/` trees.

## Plan Directory Inventory

**Latest Report:** 2025-12-07T220000Z (Phase E — Tier 4 ledger coverage complete; initiative closure 2025-12-08T190000Z)
**Artifacts:** `plans/active/PORTFOLIO-STATUS/reports/2025-12-07T220000Z/`
**Script:** `plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py`
**Roll-up Config:** `plans/active/PORTFOLIO-STATUS/rollups.json`

### Summary (Latest Report: 2025-12-07T220000Z)
- **Total plan directories:** 55 — Final count after Phase E Tier 4 coverage and ARCH-REFRACTOR-001 stub removal
- **Tracked in this ledger (direct):** 28 (≈51%) — All active initiatives have ledger entries
- **Covered via roll-ups:** 34 (≈62%) — Plans listed in roll-up member directories counted as tracked
- **Active missing:** 0 — 100% ledger coverage achieved
- **Missing implementation.md:** 0 — No missing plans
- **Roll-ups configured:** 13 (DB-AT-SUITE-CARE-001, MAP-SCALE-SYNC-001, PHYSICS-LOSS-001, TORCH-GEOMETRY-SYNC-001, TORCH-REFINE-CLEANUP-001, TORCH-CLI-BRIDGE-ROLLUP-001, FORWARD-EQUIV-COVERAGE-001, TOOLING-VIS-001, DOCS-ROADMAP-001, RUNTIME-VEC-001, REPORT-NANOBRAG-STATUS-001, NANOBRAG-GOLDEN-001, ARCH-SPLIT-001)
- **Roll-up Validation:** All 13 roll-up sections show "✓ Section exists" in rollup_report.md (100% coverage)

- See reports under `plans/active/PORTFOLIO-STATUS/reports/` and snapshots in `docs/fix_plan_archive.md` for full roll-up coverage, bucket classification, and inventory details.
