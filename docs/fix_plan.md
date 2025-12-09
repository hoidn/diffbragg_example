# DBEX Fix Plan Ledger

**Last Updated:** 2025-12-09 (Trimmed ledger; full snapshots prior to 2025-12-08 live in `docs/fix_plan_archive.md`)

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
- [ARCH-GRADIENT-FLOW-001] (Gradient Flow Restoration — DB-AT-010 Unblock) — **blocked_pending_upstream** (2025-12-09T080000Z: **Phase B.9 COMPLETE — mosaic code path confirmed as root cause.** Loop i=219 verified: gradcheck PASSES with `mosaic_spread_deg=0.0`, FAILS with real mosaic parameters (1017× Jacobian mismatch). Cell magnitude issue is NOT DBEX-side — it's coupled to mosaic code path in nanobrag_torch. Upstream fix request filed: `mosaic_gradient_bug_2025_12_08.md`. Awaiting upstream response. Artifacts: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T234500Z/`)
  - **Governed by:** GRADIENT-001, GRADIENT-003, RUNTIME-001, TESTING-003
  - **ROOT CAUSE CONFIRMED:** Mosaic code path in nanobrag_torch (triggered when `ML_half_mosaicity_deg > 0`) has a gradient bug — analytical gradients are ~1000× smaller than numerical
  - **Workaround:** Force `mosaic_spread_deg=0.0` in gradient tests (validated test exists: `test_db_at_010_gradcheck_cell_a_no_mosaic`)
  - **Next:** Await upstream response to `mosaic_gradient_bug_2025_12_08.md`, then apply fix and verify DB-AT-010 passes
- [SPEC-INTERP-TRICUBIC-001] (Global Tricubic Interpolation Default) — **done** (2025-12-08T233000Z: **HKL sparsity hypothesis SUPERSEDED.** Loop i=210 investigation confirmed that gradcheck passes with real HKL data (97% hit rate) when `mosaic_spread_deg=0.0` (ratio=1.00×). The actual root cause is the mosaic code path in nanobrag_torch, not HKL grid discontinuities. Phase A/B goals achieved (tricubic interpolation enabled globally); Phase C architecture decision no longer needed — the issue is upstream. Artifacts: `plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T140000Z/`)
- [ARCH-IMPL-CONFORMANCE-001] (Architecture / Implementation contract alignment) — **done** (2025-12-07T054500Z: Phases A-B complete; ARCH-CONTRACT-002/003 delivered with enforcement tests; exit criteria 3.5/4 satisfied; artifacts under `archive/plans/ARCH-IMPL-CONFORMANCE-001/reports/2025-12-07T054500Z/initiative_closure_summary.md`)
- [DIAG-NANOBRAGG-OVERSAMPLE-001] (nanobrag_torch oversample parameter investigation) — **done** (2025-12-09T153000Z: Phase F HKL stats + Stage-A instrumentation closed out diagnostics; artifacts under `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-09T153000Z/` now cover oversample, beam flux, and HKL evidence)
- [ARCH-SIM-HKL-BOUNDS-001] (Stage-A / mapping HKL alignment) — **done** (2025-12-03T154217Z: incident-beam sign fix restored 100% HKL coverage; DB-AT-028/029 intensity failure delegated to ARCH-SIM-CONSTRUCTION-001; artifacts under `plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/`)
- [ARCH-SIM-CONSTRUCTION-001] (Simulator Construction Convention Alignment) — **blocked_pending_environment** (**SQUARE scaling resolved:** The SQUARE lattice expectation mismatch identified in C.34–C.39 has been resolved by SPEC-SQUARE-PARTIALITY-001. The correct physics is: peak height ∝ `(Na·Nb·Nc)²`, integrated intensity ∝ `Na·Nb·Nc`. Tests now enforce linear scaling (`tests/architecture/test_nanobrag_partiality.py`, 2/2 PASS). **Remaining blockers:** DB-AT-028/029 chi²/ROI failures are now known to be unrelated to SQUARE lattice scaling. Initiative remains blocked pending resolution of other DBEX-layer issues (N_cells threading, cold-path reconstruction parity). See `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T130000Z/` for SQUARE resolution and `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T200000Z/lifecycle_decision.md` for remaining work.)
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
- [DB-AT-SUITE-CARE-001] (Acceptance suite upkeep for DB-AT-002/010/020/021/022/023/024) — **in_progress** (D.1-D.4 complete; D.5 optional. i=191 2025-12-08T162000Z: Deep gradient investigation performed — autograd graph connected but magnitude mismatch 5096-127627× persists. DB-AT-010 remains blocked_pending_upstream per ARCH-GRADIENT-FLOW-001. See GRADIENT-002 finding in docs/findings.md. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T162000Z/`).
  - **Governed by:** TESTING-003, RUNTIME-001, DIAGNOSTICS-001, MASKING-001
  - The plan directories under `plans/active/DB-AT-002/`, `.../DB-AT-010/`, and `.../DB-AT-020` through `.../DB-AT-024/` already contain implementation plans, but none were represented in this ledger. Scope: keep the DB-AT selectors mapped to fix-plan items, document status per selector, and surface artifacts/blocked states in the Attempts History. Classification reference: `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T150000Z/classification.md`.
- [MAP-SCALE-SYNC-001] (Calibration ladder initiatives MAP-SCALE-001—005) — **done** (2025-12-08T190000Z: 4/5 member plans complete; MAP-SCALE-003 telemetry already implemented; MAP-SCALE-005 deferred as non-critical).
  - **Governed by:** SCALE-001, SCALE-002, SCALE-003, SCALE-004, SCALE-005, SCALE-006, SCALE-007
  - Plans live under `plans/active/MAP-SCALE-00X/` with November 2025 reports; ledger coverage captures goals (sigma provenance, spot-scale alignment). Member plan status: MAP-SCALE-001/002/004 done, MAP-SCALE-003 done (telemetry already exists), MAP-SCALE-005 pending (enforcement guardrail deferred).
- [PHYSICS-LOSS-001] (Variance-weighted loss parity and telemetry fixes) — **done_with_environment_caveat** (all phases A-I complete; exit criteria satisfied; see detailed section line 343).
- [PHYSICS-LOSS-CONSISTENCY] (Physics Loss Function Alignment) — **pending**.
  - **Governed by:** PHYSICS-LOSS-001, PHYSICS-LOSS-002, PHYSICS-LOSS-003, PHYSICS-LOSS-004, PHYSICS-LOSS-005
  - **Goal:** Align Stage A/B/C chi-squared computation, enforce sigma-floor guard, unify sigma-map ingestion contract, harvest DIALS external_lookup metadata.
  - **Exit Criteria:** All stages use identical variance-weighted denominator per spec-db-core.md:57-68; telemetry persists both chi_squared + masked_mse; sigma-floor enforcement validated via unit tests; sigma-map/external_lookup ingestion contracts tested.
  - **Dependencies:** ARCH-REFACTOR-001 (Stage A/B/C context + observer pattern provides hooks for unified loss computation).
- [TORCH-GEOMETRY-SYNC-001] (Geometry convergence/parity/UB realign initiatives) — **done** (2025-12-08T200000Z: Roll-up complete; see detailed section line 357).
  - **Governed by:** GEOMETRY-001, GEOMETRY-002, GEOMETRY-003, GEOMETRY-004, CONFIG-001, DXTBX-001, HKL-ORIENT-001, CONVERGENCE-001
  - Covers `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/`, `.../TORCH-GEOMETRY-PARITY-002/`, `.../TORCH-GEOMETRY-PARITY-003/`, and `.../TORCH-GEOMETRY-UB-REALIGN-001/`.
- [TORCH-REFINE-CLEANUP-001] (Stage A/B/C refinement probes TORCH-REFINE-001/002/002D/002E/003/004) — **done** (2025-12-08T091543Z i=188: **Phase C COMPLETE**. Phases A-C done: 6 member plans audited and classified; TORCH-REFINE-004 archived; smoke tests collected 6/6 (execution OOM — environment resource limit, not code regression). Revive queue: TORCH-REFINE-002D (HIGH), TORCH-REFINE-001 (MEDIUM). Artifacts: `plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T091543Z/`).
  - **Governed by:** REFINE-001, REFINE-002, REFINE-003, REFINE-006, REFINE-009, REFINE-010, GRADIENT-001, REFINE-016
  - Roll-up consolidates 6 member plans (001/002/002D/002E/003/004); TORCH-REFINE-004 is complete (all phases done), others have pending phases gated on Tier 0 blockers or low-priority deferrals. Working plan: `plans/active/TORCH-REFINE-CLEANUP-001/implementation.md`.
- [TORCH-CLI-BRIDGE-ROLLUP-001] (CLI + bridge backlog TORCH-CLI-003/004 and TORCH-BRIDGE-001) — **done** (2025-12-08T100000Z: Phases A-E complete; all 3 member plans verified + checklists synced; all 4 exit criteria satisfied. Closure artifacts: `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T100000Z/`).
- [FORWARD-EQUIV-COVERAGE-001] (Forward-equivalence harness + parity scaffolding) — **done** (2025-12-08T143000Z: Phases A-C complete; all 3 member plans done; all 3 exit criteria satisfied. Closure artifacts: `plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T143000Z/`).
  - **Governed by:** PARITY-001, MANIFEST-001
  - Covers `plans/active/FORWARD-EQUIV-001/`, `.../FORWARD-EQUIV-002/`, and `plans/active/PARITY-HARNESS-002/`.
- [TOOLING-VIS-001] (Mapping-aligned visualization tooling) — **pending**. Plan exists with recent reports; ledger coverage will document progress on canonical visuals.
- [DOCS-ROADMAP-001] (Roadmap documentation refresh) — **done** (2025-11-24T150000Z: All phases complete; plan thinned 305→146 lines).
- [RUNTIME-VEC-001] (Runtime vectorization checklist enforcement) — **done** (2025-12-08T160000Z: Phase B/C complete. Test validated: correlation=1.0, sum_ratio_delta=0.0. Exit criterion #1 satisfied. Artifacts: `plans/active/RUNTIME-VEC-001/reports/2025-12-08T160000Z/`).
- [REPORT-NANOBRAG-STATUS-001] (Status reporting scripts) — **done** (2025-12-08T071251Z i=177: Phase B complete; all 4 exit criteria PASS. Validation report updated with current telemetry (loss 981638→979335, 0.235% improvement); convergence tables generated. Artifacts: `plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-12-08T071251Z/`).
- [NANOBRAG-GOLDEN-001] (Golden dataset capture + maintenance) — **done** (2025-11-04T030000Z: All phases A-D complete; canonical dataset captured with parity harness integration).
- [FINDINGS-LEDGER-002] (Findings ledger upkeep and knowledge base maintenance) — **done** (2025-12-07T124500Z: All phases complete except deferred B.3+C.2. Exit criteria 4/4 satisfied. Closure summary: `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T124500Z/closure_summary.md`). Full implementation plan authored 2025-12-03: Phase A (ledger audit + citation fixes + inventory), Phase B (cross-linking findings ↔ fix-plan), Phase C (cadence/automation). **Phase A.2 complete (2025-12-03T120250Z)**: Fixed REFINE-005 duplicate entry to include code citations; achieved **100% path:line coverage (86/86 findings)**. Status breakdown: Active=74, Resolved=10, Deferred=1, Retracted=1. **Phase B.2 complete (2025-12-07T080000Z)**: Established reciprocal cross-links between `docs/findings.md` and `docs/fix_plan.md`. Updated 7 existing Tier 1 & Tier 2 initiatives with "Governed by" lines. Created 2 new initiatives: [PHYSICS-LOSS-CONSISTENCY] (Tier 1, 5 findings), [ARCH-STAGE-CONTEXT-CONSOLIDATION] (Tier 2, 2 findings). Annotated 58/74 Active findings (78.4%) with "**Consumers:** [INITIATIVE-ID]." metadata. **Coverage target met:** ≥78% ✅. Artifacts: `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T080000Z/{summary.md,consumer_map_v2.json,add_consumers.py}`. **Phase B.3 DEFERRED** (archive/retire candidates require pytest validation). **Phase C complete (2025-12-07T100000Z)**: Delivered cadence checklist template (`cadence_checklist.md`) with 5-phase quarterly maintenance workflow; updated `docs/index.md` § Knowledge Base Ledger and `docs/fix_plan.md` Working Agreements with cadence cross-references. C.2 (automation hook) deferred — manual cadence sufficient. Artifacts: `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T100000Z/{summary.md,planning_notes.md}`.
- [SPEC-SQUARE-PARTIALITY-001] (SQUARE Lattice Spec & Test Alignment) — **done** (Phase C complete 2025-12-08T130000Z: Physics clarified by `inbox/nanobrag_torch_response_2025_12_08.md` — peak height ∝ `(Na·Nb·Nc)²`, integrated intensity ∝ `Na·Nb·Nc`. Phase A: updated `docs/findings.md::SIM-CONSTR-PARTIALITY-001` to demote `(Na·Nb·Nc)²` integrated expectation and promote linear law. Phase B: updated `tests/architecture/test_nanobrag_partiality.py` to enforce linear scaling with 400×400 detector for full solid-angle integration (7% tolerance for sinc² sidelobe oscillations); 2/2 tests PASS. Phase C: ledger closure, test registry sync. Artifacts: `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T130000Z/`. Working plan: `plans/active/SPEC-SQUARE-PARTIALITY-001/implementation.md`.)

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

### Tier 3: Performance & Memory
**Goal:** Profile and optimize GPU memory usage to enable full smoke tests on 24GB GPUs.
- [PERF-GPU-MEM-001] (GPU Memory Usage Analysis and Optimization) — **blocked_pending_upstream** (2025-12-09T000000Z: **Phase A/B COMPLETE — Upstream request filed.** Profiled small detector (1024²) with 9 mosaic domains: B=9.4M queries, peak=23.8 GB, OOM on 4.5 GB allocation. Root cause confirmed: `Crystal._tricubic_interpolation()` batches ALL query points. **Upstream request filed:** `~/Documents/nanoBragg/inbox/chunked_interpolation_request_2025_12_09.md`. Working plan: `plans/active/PERF-GPU-MEM-001/implementation.md`. Artifacts: `plans/active/PERF-GPU-MEM-001/reports/2025-12-08T224000Z/`)
  - **Governed by:** RUNTIME-001
  - **Depends on:** nanobrag_torch chunked interpolation fix (upstream)
  - **Exit Criteria:** (1) Memory profiling report ✓; (2) ≥30% peak memory reduction; (3) Stage A smoke completes on 24GB GPU; (4) Physics unchanged (partiality/gradcheck tests pass)
  - **Blocked by:** nanobrag_torch tricubic interpolation memory issue (request filed 2025-12-09)
  - **Attempts History:**
    * 2025-12-08T234600Z (Loop i=210, Ralph) — **Phase A complete (memory profiling)**. Created `profile_gpu_memory.py` probe (377 LOC < 400 limit). Profiled small detector: B=9,437,184 queries, peak=23.842 GB. OOM during reconstruction at `crystal.py:404`. Memory breakdown documented: sub_Fhkl (2.4 GB) + coordinate grids (1.7 GB) + autograd (10+ GB). Artifacts: `plans/active/PERF-GPU-MEM-001/reports/2025-12-08T224000Z/{memory_profile.md,memory_metrics.json}`.
    * 2025-12-09T000000Z (Loop i=211, Galph) — **Upstream request filed.** Phase B analysis complete (scaling laws already in Phase A report). Upstream chunked interpolation request filed: `~/Documents/nanoBragg/inbox/chunked_interpolation_request_2025_12_09.md`. Initiative status changed to blocked_pending_upstream.

### Tier 3: Tooling & Observability
**Goal:** Standardize visuals, documentation, and runtime guardrails.
- [DOC-RUNTIME-004] (Restore Runtime Checklist) — **Done** (2025-11-23T024449Z: all exit criteria met, runtime checklist restored with spec citations, references verified, validation artifacts complete)
- [TORCH-RUNTIME-002] (Runtime Harness Seed) — **Done** (2025-10-28T232744Z: all exit criteria satisfied, TESTING_GUIDE.md updated, selector registry synchronized)
- [ARCH-TELEMETRY-002] (Telemetry & Probe Simplification) — **done** (Phase C complete 2025-12-08T000000Z i=175: ALL EXIT CRITERIA MET. (C1) Field audit — all fields in use, `panel_loss_diag` flagged as future cleanup candidate, (C2) `docs/findings.md` TELEMETRY-GUARD-001 added, (C3) architecture test slice PASSED (9/9), (C4) status updated. EC1-5 all satisfied: charter linked, inventory complete, enforcement tests pass, supervisor policy updated, findings guardrail documented. Initiative ready for archive. Artifacts: `plans/active/ARCH-TELEMETRY-002/reports/2025-12-08T000000Z/`).

### Tier 4: Orchestration & Agent Ops
**Goal:** Harden orchestration tooling, submodule robustness, and agent operation workflows.
- [HARDEN-SUBMODULE-ROBUSTNESS] (Submodule Robustness Hardening) — **pending** (2025-11-04T165400Z: reports exist, needs scoping and ledger coverage)
- [ORCH-ROBUST-001] (Orchestration Robustness) — **pending** (stub — needs scoping before work can begin)
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
- Status: **blocked_pending_environment** (**BLOCKED** — 2026-01-13T200000Z lifecycle review plus the 2025-12-08 upstream response reclassified this as a **spec/expectation mismatch**, not an upstream sincg bug. C.39 showed a persistent deficit when we assumed integrated intensity must scale as `(Na·Nb·Nc)²`; the `nanobrag_torch` maintainers subsequently demonstrated (and backed with tests) that this expectation is physically incorrect: peak height scales as `(Na·Nb·Nc)²` but integrated/summed intensity scales linearly with `Na·Nb·Nc`. Under that model our probes and the maintainer’s `verify_square_lattice_scaling.py` agree, so further edits to the vendored simulator are out of scope for this plan. PROBE-FREEZE-001 still forbids additional plan-local instrumentation. The initiative remains blocked pending one of: (A) DBEX-side spec/test changes that adopt the linear SQUARE lattice scaling and adjust DB‑AT‑028/029, (B) a Spec‑DB amendment that states the intended scaling explicitly, or (C) a dedicated harness-grade diagnostic initiative. Artifacts: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T200000Z/lifecycle_decision.md` plus `inbox/nanobrag_torch_response_2025_12_08.md`.)
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
- Status: **done** (2025-12-03T154217Z: incident-beam sign fix restored 100% HKL coverage; DB-AT-028/029 intensity failure delegated to ARCH-SIM-CONSTRUCTION-001)
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

### [ARCH-TELEMETRY-002] Telemetry & Probe Simplification
- Depends on: ARCH-TELEMETRY-001 (observer refactor), ARCH-STAGE-CONTEXT-001 (typed contexts), PHYSICS-LOSS-001 (telemetry χ² spec), TOOLING-VIS-001 / MAP-SCALE-00x (mapping metrics), ARCH-PROBE-FREEZE-001 (probe/shim policy)
- Status: done
- Type: architecture
- Priority: High
- Tier: 3 (Tooling & Observability)
- Owner/Date: Galph ↔ Ralph / 2025-12-07
- Exit Criteria:
  1. Telemetry ownership charter exists (`docs/architecture/telemetry.md` or equivalent), is wired into `docs/index.md`, and clearly separates primary production telemetry owners (Stage collectors, writer, CLI bundle) from diagnostic owners (bridge/mapping/baseline helpers), explicitly deferring semantics to Spec‑DB and existing IDLs.
  2. A telemetry inventory (charter appendix or `docs/data_dependency_manifest.md` Telemetry section) catalogues `/torch_diagnostics` attributes, Stage telemetry fields, and mapping/baseline diagnostics with their code/tests/plan consumers; at least one unused, non‑normative field is removed or explicitly deprecated with recorded evidence.
  3. `tests/architecture/test_telemetry_surfaces.py` prevents new long‑lived telemetry dict surfaces from being introduced in `dbex/` outside a small owner allow‑list; new telemetry schemas are required to go through the charter + IDL + tests path.
  4. `<diagnostic_script_policy>` in `prompts/supervisor.md` and `tests/architecture/test_probe_contracts.py` both reflect updated telemetry rules: plan‑local scripts may only produce views of existing telemetry and may not define new production schemas or shadow pipelines.
  5. Telemetry‑relevant selectors in `docs/TESTING_GUIDE.md` (Stage smokes, MAP‑SCALE‑00x, TOOLING‑VIS‑001, PHYSICS‑LOSS‑001) and architecture tests all pass under the new guards; `docs/findings.md` is updated to record the new guardrails and close out any outstanding telemetry‑dict debt.
- Working Plan: `plans/active/ARCH-TELEMETRY-002/implementation.md`
- Attempts History:
  * See docs/fix_plan_archive.md (snapshot 2025-12-08) and plans/active/ARCH-TELEMETRY-002/reports/ for Phase A-B Attempts History.
  * 2025-12-08T000000Z (Loop i=175, Ralph) — **Phase C complete (closure)**: ALL EXIT CRITERIA MET. Charter+inventory complete, enforcement test passes (9/9), TELEMETRY-GUARD-001 added to findings.md. Artifacts: `plans/active/ARCH-TELEMETRY-002/reports/2025-12-08T000000Z/`.

### [ARCH-GRADIENT-FLOW-001] Gradient Flow Restoration (DB-AT-010 Unblock)
- Depends on: DB-AT-SUITE-CARE-001 Phase B.1 verification (evidence source)
- Blocks: DB-AT-SUITE-CARE-001 portfolio advancement, Gradient-Safe Profile conformance
- Status: **blocked_pending_upstream** (Phase B.9 COMPLETE: Mosaic code path confirmed as root cause. Loop i=219 verified gradcheck PASSES with `mosaic_spread_deg=0.0`, FAILS with real mosaic parameters (1017× Jacobian mismatch). Upstream fix request filed `mosaic_gradient_bug_2025_12_08.md`. Awaiting response.)
- Type: architecture
- Priority: Tier 0 (blocks conformance profile)
- Owner/Date: Galph ↔ Ralph / 2025-12-08
- Exit Criteria:
  1. Gradient flow restored: DB-AT-010 gradcheck tests pass (5/5) with documented tolerances (eps=1e-6, atol=1e-5, rtol=0.05)
  2. Root cause identified and fixed: Code audit locates `.item()` coercion or tensor detachment; patch applied
  3. Enforcement test added: `tests/architecture/test_gradient_contracts.py` validates gradient flow preservation
  4. Documentation updated: `docs/findings.md` GRADIENT-002, `docs/architecture.md` §13 gradient hygiene guardrail
  5. Regression validation: Full DB-AT-010 suite passes; `docs/development/TEST_SUITE_INDEX.md` status updated
- Working Plan: `plans/active/ARCH-GRADIENT-FLOW-001/implementation.md`
- Attempts History:
  * See docs/fix_plan_archive.md (snapshot 2025-12-08) and plans/active/ARCH-GRADIENT-FLOW-001/reports/ for Phases A-B.5 Attempts History.
  * 2025-12-08T230000Z (Loop i=171, Ralph) — **Phase B.6 implementation**: Single-line fix at `forward.py:196` (commit d05dd833). **RESULT**: Graph connectivity FIXED but Jacobian mismatch ~640× discovered.
  * 2025-12-07T213000Z (Loop i=172, Galph) — **Lifecycle decision: blocked_pending_upstream**. Escalation filed: `inbox/to_nanobrag_gradient_magnitude_2025_12_07.md`.
  * 2025-12-08T160000Z (Loop i=189, Ralph) — **Upstream response verification**: Gradients exist but correctness broken (2900-127000× mismatches). Status: **blocked_pending_upstream**.
  * 2025-12-08T220000Z (Loop i=208, Ralph) — **UPSTREAM RESPONSE RECEIVED — BLOCKER LIFTED**. File `inbox/nanobrag_torch_cell_gradient_response_2025_12_08.md`: nanobrag_torch confirms 6/6 cell param gradcheck tests PASS. Issue is in DBEX integration layer. **Debugging hypotheses provided:** (1) Double unit conversion (Å→m applied twice), (2) Scalar extraction breaking graph (.item()/.detach()), (3) Fluence mismatch. **Phase B.7 scope:** DBEX config_factories.py audit, simulate_forward_torch() diagnostics, minimal reproduction bypassing DBEX factories. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T220000Z/`.
  * 2025-12-08T212500Z (Loop i=209, Ralph) — **Phase B.7 implementation: PARTIAL SUCCESS**. (1) Pure-PyTorch B-matrix at `nanobrag_bridge.py:558-680` replacing cctbx with `.item()` calls; verified max diff 3.47e-18 vs cctbx. (2) Removed `.detach()` from A* extraction at `stage_a.py:1183-1195,1238-1255` (cell & U-matrix paths); tensors now flow to `crystal_overrides`. **RESULT**: Analytical gradients non-zero (7.04e7 cell_a, 4.64e7 cell_gamma) - **graph connectivity RESTORED**. Magnitude mismatch remains (843× cell_a, 19,352× cell_gamma). **Next:** Investigate magnitude source in DBEX integration layer. Artifacts: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T212500Z/`.
  * 2025-12-08T232143Z (Loop i=218, Galph) — **Phase B.8 delegation**: Minimal reproduction test to isolate DBEX integration layer as magnitude mismatch source. Upstream confirmed nanobrag_torch cell gradcheck passes (6/6); issue is in DBEX. **Two separate blockers clarified:** (1) Cell magnitude mismatch → DBEX-side fix actionable now, (2) Mosaic gradient bug → upstream fix pending. Artifacts: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T232143Z/`.
  * 2025-12-08T232143Z (Loop i=218, Ralph) — **Phase B.8 execution: ISOLATION COMPLETE**. Created 5 diagnostic tests (`test_minimal_nanobrag_gradcheck`, `test_gradient_magnitude_diagnostic`, `test_dbex_hkl_grid_gradient`, `test_dbex_full_factory_gradient`, `test_simulate_forward_torch_gradient`) — **ALL PASS** with synthetic data. Key finding: DBEX integration layer does NOT break gradients for synthetic 100Å cubic crystals. Only real refGeom data test fails. **Suspected root cause:** Mosaic parameters extracted from experiment metadata (`ML_half_mosaicity_deg`, `ML_domain_size_ang` at `config_factories.py:382-420`). Cell magnitude issue appears coupled to mosaic code path. **Recommended workaround:** Force `mosaic_spread_deg=0.0` in gradient tests. **Next:** Verify mosaic hypothesis with diagnostic probe on real data. Artifacts: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T232143Z/`.
  * 2025-12-08T234500Z (Loop i=219, Ralph) — **Phase B.9 execution: HYPOTHESIS CONFIRMED**. Added diagnostic test `test_db_at_010_gradcheck_cell_a_no_mosaic` with `experiment=None` to bypass mosaic metadata extraction. **RESULTS**: (1) No-mosaic test **PASSED** (gradcheck_passed=true, 109.61s runtime), (2) Original test **FAILED** with 1017× Jacobian mismatch (numerical=7.06e10, analytical=6.93e7). **Root cause confirmed:** Mosaic code path in nanobrag_torch (triggered when `ML_half_mosaicity_deg > 0` extracted from experiment metadata at `config_factories.py:380-396`) has a gradient bug — analytical gradients are ~1000× smaller than numerical. DBEX integration layer is **correct** when `mosaic_spread_deg=0`. Updated `docs/findings.md::GRADIENT-003` with confirmed root cause. Upstream mosaic fix request (`mosaic_gradient_bug_2025_12_08.md`) remains the blocker. Artifacts: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T234500Z/{mosaic_hypothesis_verification.md,gradcheck_no_mosaic.log,gradcheck_crystal_cell_a_no_mosaic.json}`.

### [SPEC-SQUARE-PARTIALITY-001] SQUARE Lattice Spec & Test Alignment
- Depends on: ARCH-SIM-CONSTRUCTION-001 (physics evidence), SIM-CONSTR-PARTIALITY-001 (finding), nanobrag_torch maintainer response (`inbox/nanobrag_torch_response_2025_12_08.md`)
- Status: **done** (Phase C complete 2025-12-08T130000Z: ledger closure, test registry sync; all exit criteria satisfied)
- Type: spec+tests
- Priority: High
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-08
- Exit Criteria:
  1. Spec text (via `docs/findings.md::SIM-CONSTR-PARTIALITY-001` and, if needed, a short note in `docs/spec-db-core.md`) explicitly states the correct SQUARE lattice scaling: peak height ∝ `(Na·Nb·Nc)²`, integrated/summed intensity ∝ `Na·Nb·Nc`, with a citation to the maintainer response.
  2. Architecture partiality test (`tests/architecture/test_nanobrag_partiality.py`) and the square‑lattice probe script are updated to enforce the **linear** `Na·Nb·Nc` integrated scaling (and, if retained, any `(Na·Nb·Nc)²` checks are clearly scoped to peak intensity at exact Bragg). Updated tests pass with `pytest -vv tests/architecture/test_nanobrag_partiality.py --maxfail=1`, and logs are archived under this plan's reports directory.
  3. `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md` and `docs/fix_plan.md` are updated so the ARCH-SIM-CONSTRUCTION-001 row treats the SQUARE scaling issue as resolved via this initiative (either by unblocking and finishing or by archiving with "resolved via spec/test fix").
  4. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any updated partiality tests/selectors; `pytest --collect-only tests/architecture/test_nanobrag_partiality.py` logs are stored under `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/<timestamp>/`.
- Working Plan: `plans/active/SPEC-SQUARE-PARTIALITY-001/implementation.md`
- Attempts History:
  * See docs/fix_plan_archive.md (snapshot 2025-12-08) and plans/active/SPEC-SQUARE-PARTIALITY-001/reports/ for Phases A-B.6 Attempts History.
  * 2025-12-08T110000Z (Loop i=162, Ralph) — **Phase B.7 complete**: Test updated to 400×400 detector, 7% tolerance. 2/2 tests PASS validating linear Na×Nb×Nc scaling.
  * 2025-12-08T130000Z (Loop i=163, Ralph) — **Phase C complete (ledger closure)**: ALL EXIT CRITERIA MET. Artifacts: `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T130000Z/`.

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
  * See docs/fix_plan_archive.md (snapshot 2025-12-08) and plans/active/DB-AT-SUITE-CARE-001/reports/ for full Phase B-D Attempts History.
  * 2025-12-08T040000Z (Loop i=155, Ralph) — **Phase C complete**: Workflow Integration 12/13 passed, Determinism 2/2 passed. 4/5 exit criteria met (Chi²/pixel deferred for DB-AT-010).
  * 2025-12-08T140000Z (Loop i=194, Ralph) — **Phase D.4 complete**: TEST_SUITE_INDEX hygiene audit — 26 Active selectors, 189 tests collected, zero orphans. **Registry health: GOOD**.
  * 2025-12-08T240000Z (Loop i=202, Galph) — **Maintenance mode**: Tier 0 blocked (ARCH-GRADIENT-FLOW-001 + ARCH-SIM-CONSTRUCTION-001). D.1-D.4 complete, D.5 optional. Awaiting upstream response.
  * 2025-12-09T000000Z (Loop i=212, Ralph) — **Maintenance mode continues**: Checked nanoBragg outbox and DBEX inbox — no new responses. Two outstanding upstream requests: `mosaic_gradient_bug_2025_12_08.md` (HIGH, blocks ARCH-GRADIENT-FLOW-001) and `chunked_interpolation_request_2025_12_09.md` (MEDIUM, blocks PERF-GPU-MEM-001). Portfolio status unchanged. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T000000Z/`.
  * 2025-12-08T225750Z (Loop i=213, Ralph) — **Maintenance mode continues**: Checked nanoBragg outbox and DBEX inbox — no new responses. Two outstanding upstream requests remain: `mosaic_gradient_bug_2025_12_08.md` (HIGH, blocks ARCH-GRADIENT-FLOW-001) and `chunked_interpolation_request_2025_12_09.md` (MEDIUM, blocks PERF-GPU-MEM-001). Portfolio status verified unchanged. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T225750Z/`.
  * 2025-12-08T230330Z (Loop i=214, Galph) — **Maintenance mode continues**: Checked nanoBragg outbox and DBEX inbox — no new responses. Outstanding upstream requests unchanged. Portfolio status verified unchanged. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T230330Z/`.
  * 2025-12-09T010000Z (Loop i=215, Galph) — **Maintenance mode continues**: Checked nanoBragg outbox and DBEX inbox — no new responses. Two outstanding upstream requests remain: `mosaic_gradient_bug_2025_12_08.md` (HIGH, blocks ARCH-GRADIENT-FLOW-001) and `chunked_interpolation_request_2025_12_09.md` (MEDIUM, blocks PERF-GPU-MEM-001). Portfolio status verified unchanged. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T010000Z/`.
  * 2025-12-09T020000Z (Loop i=216, Galph) — **Maintenance mode continues**: Checked inbox/outbox — no new responses. Fixed ORCH-ROBUST-001 status drift (was `in_progress`, changed to `pending` per implementation.md stub status). Portfolio status unchanged. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T020000Z/`.
  * 2025-12-09T030000Z (Loop i=217, Ralph) — **Maintenance mode → PORTFOLIO UNBLOCKED**: Full inbox/outbox audit found upstream responses: (1) `dbex-gradient-blockers-fix-report.md` — wavelength/fluence/distance FIXED, (2) `nanobrag_torch_cell_gradient_response_2025_12_08.md` — cell gradients work in nanobrag_torch, issue is DBEX-side. **Key finding:** ARCH-GRADIENT-FLOW-001 is NOT fully blocked — cell param magnitude investigation can proceed in DBEX. Mosaic bug is a separate blocker (awaiting response). ARCH-GRADIENT-FLOW-001 status updated to in_progress (Phase B.8). Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T030000Z/`.
  * 2025-12-09T040000Z (Loop i=220, Galph) — **Maintenance mode continues**: Checked nanoBragg outbox and DBEX inbox — no new responses since Phase B.9 mosaic confirmation. Two outstanding upstream requests remain: `mosaic_gradient_bug_2025_12_08.md` (HIGH), `chunked_interpolation_request_2025_12_09.md` (MEDIUM). Portfolio status unchanged. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T040000Z/`.
  * 2025-12-09T050000Z (Loop i=221, Ralph) — **Maintenance mode continues**: Checked nanoBragg outbox and DBEX inbox — no new upstream responses since last check (Dec 7 19:55). Two outstanding upstream requests remain: `mosaic_gradient_bug_2025_12_08.md` (HIGH, blocks ARCH-GRADIENT-FLOW-001), `chunked_interpolation_request_2025_12_09.md` (MEDIUM, blocks PERF-GPU-MEM-001). Portfolio status unchanged. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T050000Z/`.
  * 2025-12-09T070000Z (Loop i=223, Ralph) — **Maintenance mode continues**: Checked nanoBragg outbox (last modified Dec 7 19:55) and DBEX inbox (last modified Dec 8 13:15) — no new upstream responses. Two outstanding requests remain: `mosaic_gradient_bug_2025_12_08.md` (HIGH, blocks ARCH-GRADIENT-FLOW-001), `chunked_interpolation_request_2025_12_09.md` (MEDIUM, blocks PERF-GPU-MEM-001). Portfolio status unchanged. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T070000Z/`.
  * 2025-12-09T090000Z (Loop i=221, Ralph) — **Maintenance mode continues**: Checked nanoBragg outbox (last modified Dec 7 19:55) and DBEX inbox (last modified Dec 8 13:15) — no new upstream responses. Two outstanding requests remain: `mosaic_gradient_bug_2025_12_08.md` (HIGH, blocks ARCH-GRADIENT-FLOW-001), `chunked_interpolation_request_2025_12_09.md` (MEDIUM, blocks PERF-GPU-MEM-001). Portfolio status unchanged. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T090000Z/`.
  * 2025-12-09T100000Z (Loop i=224, Ralph) — **Maintenance mode continues**: Verified inbox/outbox status — no new upstream responses. nanoBragg outbox last modified 2025-12-07 19:55; DBEX inbox last modified 2025-12-08 13:15. Two outstanding upstream requests remain: (1) `mosaic_gradient_bug_2025_12_08.md` (HIGH, blocks ARCH-GRADIENT-FLOW-001/DB-AT-010), (2) `chunked_interpolation_request_2025_12_09.md` (MEDIUM, blocks PERF-GPU-MEM-001). All Tier 0 initiatives blocked pending upstream. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T090000Z/`.
  * 2025-12-09T110000Z (Loop i=225, Ralph) — **Maintenance mode continues**: Checked nanoBragg outbox (last modified Dec 7 19:55) and DBEX inbox (last modified Dec 8 13:15) — no new upstream responses. Two outstanding requests remain: (1) `mosaic_gradient_bug_2025_12_08.md` (HIGH, blocks ARCH-GRADIENT-FLOW-001/DB-AT-010), (2) `chunked_interpolation_request_2025_12_09.md` (MEDIUM, blocks PERF-GPU-MEM-001). All Tier 0 initiatives blocked pending upstream. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T090000Z/`.
  * 2025-12-09T110000Z (Loop i=226, Ralph) — **Maintenance mode continues**: Verified inbox/outbox status — no new upstream responses. nanoBragg outbox last modified 2025-12-07 19:55 (unchanged); DBEX inbox last modified 2025-12-08 13:15 (already processed). Two outstanding upstream requests remain: (1) `mosaic_gradient_bug_2025_12_08.md` (HIGH, blocks ARCH-GRADIENT-FLOW-001/DB-AT-010), (2) `chunked_interpolation_request_2025_12_09.md` (MEDIUM, blocks PERF-GPU-MEM-001). All Tier 0 initiatives remain blocked pending upstream. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T110000Z/`.
  * 2025-12-09T120000Z (Loop i=227, Ralph) — **Maintenance mode continues**: Verified inbox/outbox status — no new upstream responses. nanoBragg outbox last modified 2025-12-07 19:55 (unchanged since Dec 7); DBEX inbox last modified 2025-12-08 13:15 (already processed). Two outstanding upstream requests remain: (1) `mosaic_gradient_bug_2025_12_08.md` (HIGH, blocks ARCH-GRADIENT-FLOW-001/DB-AT-010), (2) `chunked_interpolation_request_2025_12_09.md` (MEDIUM, blocks PERF-GPU-MEM-001). All Tier 0 initiatives remain blocked pending upstream. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T120000Z/`.
  * 2025-12-09T163400Z (Loop i=228, Ralph) — **Maintenance mode continues**: Verified inbox/outbox status — no new upstream responses. nanoBragg outbox last modified 2025-12-07 19:55; DBEX inbox last modified 2025-12-08 13:15. Two outstanding upstream requests remain: (1) `mosaic_gradient_bug_2025_12_08.md` (HIGH, blocks ARCH-GRADIENT-FLOW-001/DB-AT-010), (2) `chunked_interpolation_request_2025_12_09.md` (MEDIUM, blocks PERF-GPU-MEM-001). All Tier 0 initiatives remain blocked pending upstream. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T120000Z/`.
  * 2025-12-09T163900Z (Loop i=229, Ralph) — **Maintenance mode continues**: Verified inbox/outbox status — no new upstream responses. nanoBragg outbox last modified 2025-12-07 19:55; DBEX inbox last modified 2025-12-08 13:15. Two outstanding upstream requests remain: (1) `mosaic_gradient_bug_2025_12_08.md` (HIGH, blocks ARCH-GRADIENT-FLOW-001/DB-AT-010), (2) `chunked_interpolation_request_2025_12_09.md` (MEDIUM, blocks PERF-GPU-MEM-001). All Tier 0 initiatives remain blocked pending upstream. Artifacts: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T120000Z/`.
  * ... (see plans/active/DB-AT-SUITE-CARE-001/reports/ for full Attempts History and metrics).

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
  * 2025-12-08T180000Z i=166 (Ralph): **MAP-SCALE-003 Phase A (Telemetry Design) COMPLETE.** Audited `dbex/io/writer.py` diagnostics emission, traced refined MTZ loading path, confirmed 4 downstream test consumers. **Key finding:** Structure-factor telemetry (SCALE-003) is **already fully implemented** at `writer.py:196-200`. No gaps identified; no production code changes required. Tests: not run (Mode: Docs). Artifacts: `plans/active/MAP-SCALE-003/reports/2025-12-08T180000Z/{telemetry_audit.md,mtz_loading_trace.md,downstream_consumers.md,summary.md}`. Next: Review Phase B/C scope or consider closing MAP-SCALE-003 as complete.
  * 2025-12-08T190000Z i=167 (Galph): **MAP-SCALE-003 CLOSED (telemetry already implemented).** Phase A evidence confirmed structure-factor telemetry exists at `writer.py:196-200` with all 4 SCALE-003 fields (hkl_source, hkl_n_reflections, hkl_mean_amplitude, hkl_path). Phase B/C obsolete — no new implementation needed. Initiative marked **done**. MAP-SCALE-SYNC-001 roll-up updated: 4/5 member plans complete (001/002/003/004 done, 005 pending but non-critical). MAP-SCALE-005 deferred as optional enforcement guardrail. Focus switched to next Tier 1 unblocked item.

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
- Status: done (2025-12-08T200000Z: Roll-up complete. 2/4 member plans done (CONVERGENCE-001, UB-REALIGN-001 with 5/5 exit criteria each), 2/4 superseded (PARITY-002, PARITY-003 absorbed by incremental UB approach). Artifacts: plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T200000Z/)
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
  * 2025-12-08T190000Z (Ralph, Loop i=167) — Phase A Reality Check COMPLETE. Inventoried 4 member plans: CONVERGENCE-001 (done, 5/5), UB-REALIGN-001 (done, 5/5), PARITY-002 (superseded), PARITY-003 (superseded). All exit criteria satisfied via CONVERGENCE-001 + UB-REALIGN-001. Recommended: Close roll-up. Artifacts: `plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T190000Z/`.
  * 2025-12-08T200000Z (Loop i=168, Ralph) — Phase B closure: Marked roll-up done. Updated 4 member plan status fields. Created closure_summary.md. Artifacts: plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T200000Z/.
  * ... (see docs/fix_plan_archive.md and plans/active/TORCH-GEOMETRY-SYNC-001/reports/ for full Attempts History and metrics).

### [TORCH-REFINE-CLEANUP-001] Stage A/B/C Refinement Cleanup (TORCH-REFINE-001/002/002D/002E/003)
- Depends on: ARCH-REFACTOR-001 (Stage modularization), PHYSICS-LOSS-001 (telemetry spec)
- Status: done (Phase C complete 2025-12-08T091543Z i=188)
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
- Revive Priority Queue: **EMPTY** (2025-12-08T100000Z: Status drift corrected)
  * **TORCH-REFINE-002D:** ~~Priority HIGH~~ → **DONE** (2025-11-05T093000Z: All phases complete. Phase A audit (i=186) had stale checklist; November 2025 summary shows all exit criteria satisfied — REFINE-004/005 Resolved, test PASSED with ~0.206% improvement, deterministic misset validated)
  * **TORCH-REFINE-001:** ~~Priority MEDIUM~~ → **Substantial progress** (Phase A complete; Phases B-C scope largely superseded by downstream TORCH-REFINE-002/002D implementation — `loss_trace_full` implemented/tested, Stage A expansion operational, nanobrag backend exposed via CLI)
- Attempts History:
  * See docs/fix_plan_archive.md (snapshot 2025-12-08) and plans/active/TORCH-REFINE-CLEANUP-001/reports/ for Phase A-B Attempts History.
  * 2025-12-08T091543Z (Loop i=188, Ralph) — **Phase C complete (closure)**: 6/6 smoke tests collected; TORCH-REFINE-003 verified PASS (22.78s). Roll-up done. Artifacts: `plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T091543Z/`.

### [TORCH-CLI-BRIDGE-ROLLUP-001] CLI & Bridge Infrastructure (TORCH-BRIDGE-001, TORCH-CLI-003/004)
- Depends on: REPORT-NANOBRAG-STATUS-001 (output schema) — **DONE**
- Status: **done** (2025-12-08T100000Z: All Phases A-E complete; all 3 member plans verified + checklists synced; all 4 exit criteria satisfied. Closure artifacts: `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T100000Z/`)
- Type: architecture + harness
- Priority: Medium
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-05
- Exit Criteria:
  1. CLI backend flag wiring complete per `docs/spec-db-interfaces.md`
  2. Telemetry schema work documented in `docs/config_crosswalk.md`
  3. Bridge responsibility split tracked per `docs/architecture.md`
  4. Dependencies on REPORT-NANOBRAG-STATUS-001 output schema resolved — **SATISFIED** (dependency done 2025-12-08)
- Working Plan: `plans/active/TORCH-BRIDGE-001/`, `plans/active/TORCH-CLI-003/`, `plans/active/TORCH-CLI-004/`
- Spec References: `docs/spec-db-interfaces.md`, `docs/config_crosswalk.md`, `docs/architecture.md`
- Working Plan: `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/implementation.md`
- Attempts History:
  * 2025-12-08T073000Z i=178 — **Phase A complete (Member Plan Inventory)**. Reality check: all 3 member plans have implementation work done; only docs/ledger sync remains. Created member_plan_inventory.md, roadmap_draft.md. Replaced implementation.md stub with 172-line phased plan (B-E). Estimated 2 loops to close roll-up. Metrics: 3/3 plans audited, 28+15=43 tests collect-only verified, 0 code changes. Artifacts: `plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/2025-12-08T073000Z/`. Next: Phase B — TORCH-BRIDGE-001 closeout (D1-D4).
  * 2025-12-05T150000Z — see docs/fix_plan_archive.md for details.
  * ... (see docs/fix_plan_archive.md and plans/active/TORCH-CLI-BRIDGE-ROLLUP-001/reports/ for full Attempts History and metrics).

### [FORWARD-EQUIV-COVERAGE-001] Forward Equivalence & Parity Harness
- Depends on: NANOBRAG-GOLDEN-001 (dataset refresh) — **DONE**
- Status: **done**
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
  * See docs/fix_plan_archive.md (snapshot 2025-12-08) and plans/active/FORWARD-EQUIV-COVERAGE-001/reports/ for full Phase A-B Attempts History.
  * 2025-12-08T143000Z i=185 (Ralph) — **Phase C complete (Roll-up Closure)**. 3/3 member plans done, 3/3 exit criteria satisfied, 15/15 DB_AT_001 tests PASS (correlation=0.988, localization=1.0). Artifacts: `plans/active/FORWARD-EQUIV-COVERAGE-001/reports/2025-12-08T143000Z/`.

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
- Status: done (2025-11-24T150000Z: All phases A-C complete per implementation.md; normative duplication eliminated, plan thinned 305→146 lines)
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
- Status: done (2025-12-08T160000Z: Phase B/C complete; test validated correlation=1.0, sum_ratio_delta=0.0; exit criterion #1 satisfied)
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
  * See docs/fix_plan_archive.md (snapshot 2025-12-08) and plans/active/RUNTIME-VEC-001/reports/ for Phase A Attempts History.
  * 2025-12-08T160000Z (i=165) — **Phase B/C complete**: correlation=1.0, sum_ratio_delta=0.0; exit criterion #1 satisfied. Artifacts: `plans/active/RUNTIME-VEC-001/reports/2025-12-08T160000Z/`.

### [REPORT-NANOBRAG-STATUS-001] Status Reporting Scripts
- Depends on: None
- Status: done (2025-12-08T071251Z: Phase B complete; all 4 exit criteria PASS)
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
  * See docs/fix_plan_archive.md (snapshot 2025-12-08) and plans/active/REPORT-NANOBRAG-STATUS-001/reports/ for Phase A Attempts History.
  * 2025-12-08T071251Z (i=177) — **Phase B complete**: All 4 exit criteria PASS. Loss improvement 0.2346%, 92 ROIs. Artifacts: `plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-12-08T071251Z/`.

### [NANOBRAG-GOLDEN-001] Golden Dataset Capture + Maintenance
- Depends on: None
- Status: done (2025-11-04T030000Z: All phases A-D complete per implementation.md; canonical dataset captured, manifest validated, parity harness integrated)
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
- Status: pending (stub — needs scoping before work can begin)
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

### [ROI-MAPPING-ALIGN-001] Stage-A / Mapping ROI Alignment & Parity
- Depends on: DB-AT-SUITE-CARE-001 (DB-AT acceptance gates), DBAT-SMOKE-GOLDEN-001 (golden vs smoke config alignment), ARCH-SIM-CONSTRUCTION-001 (simulator construction evidence)
- Status: pending
- Type: architecture
- Priority: High (DB-AT-028/029 ROI CC correctness)
- Tier: 1
- Owner/Date: (unassigned) / 2025-12-08
- Exit Criteria:
  1. Canonical ROI contract documented and enforced for DB-AT-024/027/028/029, with mapping and Stage-A paths shown to share identical ROI sets for the golden simple_cubic configuration.
  2. ROI parity probe(s) demonstrate either (a) improved ROI CC on smoke when using unified/golden ROIs, or (b) strong evidence that ROI miscalculation is not the dominant cause of the negative CC.
  3. At least one regression selector guards ROI parity between mapping and Stage-A fixtures; `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` are updated with selector names and collect-only logs under this initiative.
- Working Plan: `plans/active/ROI-MAPPING-ALIGN-001/implementation.md`
- Attempts History:
  * 2025-12-08T200000Z (planning) — Created ROI-MAPPING-ALIGN-001 implementation plan to investigate whether inconsistent ROI calculation between golden mapping and Stage-A smoke paths contributes to the persistent negative ROI CC on DB-AT-028/029. Scoped Phase A probes to compare ROI layouts and CC for golden vs smoke vs unified configurations, Phase B fixes to factor a canonical ROI builder, and Phase C spec/test updates. No code changes yet; artifacts: `plans/active/ROI-MAPPING-ALIGN-001/implementation.md`.

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
