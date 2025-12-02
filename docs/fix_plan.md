# DBEX Fix Plan Ledger

**Last Updated:** 2025-12-02 (Trimmed ledger; full snapshots including this date now live in `docs/fix_plan_archive.md`)

## Working Agreements
- Continue logging every loop in this ledger with status + artifact pointer; detailed Attempts History older than the sections below lives in `docs/fix_plan_archive.md`.
- Status values: `pending`, `in_progress`, `blocked`, `done`, `archived`.
- Citation rule remains: whenever you touch a selector or plan row, note the artifact path in both this file and the plan’s reports directory.

---

## Execution Roadmap
> **Agent Rule:** Prioritize initiatives in lower-numbered tiers. Within a tier, follow dependency chains. Do not start a Tier N+1 item if a Tier N item is unblocked.


### Tier 0: Refinement Architecture Finish
**Goal:** Finish the Protocol Engine refactor by removing legacy helpers/facades now that contexts and artifacts are in place.
- [ARCH-REFACTOR-001] (Refinement Engine Modularization & Physics Separation) — *in_progress*
- [ARCH-TELEMETRY-001] (Telemetry Observer Refactor) — *in_progress*
- [ARCH-BRIDGE-RESP-001] (Writer / bridge responsibility split) — *in_progress* (2025-12-02T213000Z: initiative scaffolded from problems.md ledger; plan at `plans/active/ARCH-BRIDGE-RESP-001/implementation.md`.)
- [ARCH-LAZY-IMPORTS-001] (Lazy imports / process-noise hygiene) — *in_progress* (2025-12-02T082202Z: initiative created from problems.md ledger; plan at `plans/active/ARCH-LAZY-IMPORTS-001/implementation.md`.)

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
- [PERF-WARM-SIM-001] (Warm Simulator) — **blocked — Stage C panel-loss path diverges from Stage A, forcing +0.067 % χ² regression** (2025-12-01T214200Z: Full-detector telemetry shows `stage_a_final_chi2=2.10706464e+08` while every Stage C validation records `2.10848512e+08` even with zero detector offsets. Trusted-mask parity, ROI wiring, and best-snapshot persistence are now correct; the remaining drift comes from Stage C’s duplicated panel-mode loss computation. Stage A’s panel branch keeps evolving (trusted-mask intersection, mask ordering, telemetry), but Stage C’s forked copy lagged behind. Until Stage C reuses the exact Stage A helper for panel-mode loss, REFINE-007 can’t pass because Stage C effectively measures a different pixel population before detector offsets change. Phase F instrumentation (2025-12-02T173000Z) confirmed ROI simulators retarget correctly yet ROI-mode closures still run even when Stage A forces panel validations, so REFINE-012 remains unmet; next action is to disable ROI closures whenever `validation_scope=\"panel\"`, update smoketest assertions, and rerun Stage C small/full smokes under the new artifact set.)
- [ARCH-STAGE-CONTEXT-001] (Stage context + engine artifact boundary) — **done** (2025-12-02T160500Z: Phase E telemetry dataclass enforcement landed, Stage A/B/C smokes passed, and artifacts/writer consumers now rely solely on typed contexts; see `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/`). Stage helpers now own their closures/telemetry, RefinementEngine traffics typed artifacts, and the problems-ledger design-debt item is resolved.

### Tier 3: Tooling & Observability
**Goal:** Standardize visuals, documentation, and runtime guardrails.
- [DOC-RUNTIME-004] (Restore Runtime Checklist) — **Done** (2025-11-23T024449Z: all exit criteria met, runtime checklist restored with spec citations, references verified, validation artifacts complete)
- [TORCH-RUNTIME-002] (Runtime Harness Seed) — **Done** (2025-10-28T232744Z: all exit criteria satisfied, TESTING_GUIDE.md updated, selector registry synchronized)

---

## Active / Pending Initiatives

### [ARCH-REFACTOR-001] Refinement Engine Modularization & Physics Separation
- Depends on: ARCH-REFINE-FLOW-001, ARCH-REFINE-001, ARCH-STAGE-CONTEXT-001
- Status: in_progress
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

### [ARCH-TELEMETRY-001] Telemetry Observer Refactor
- Depends on: ARCH-STAGE-CONTEXT-001 (typed contexts), PHYSICS-LOSS-001 (telemetry χ² spec), problems.md observer directive
- Status: in_progress
- Priority: High
- Tier: 0
- Owner/Date: Galph ↔ Ralph / 2025-12-02
- Initiative Type: architecture
- Exit Criteria:
  1. Stage A/B/C no longer mutate `telemetry_state` or dict shims; closures emit observer callbacks captured in typed telemetry/result dataclasses.
  2. RefinementEngine + writer read `StageResult` artifacts (StageATelemetry/StageBTelemetry/StageCTelemetry) directly with no Nelder–Mead reruns or dict patching.
  3. Stage A/B/C smoketests and canonical Stage diagnostics keep REFINE-007/008/012 and PHYSICS-LOSS-001 gates green using the observer channel.
  4. `/torch_diagnostics` schema stays spec-compliant and test registry entries referencing telemetry selectors are updated.
- Working Plan: `plans/active/ARCH-TELEMETRY-001/implementation.md`
- Ledger tie-in: addresses problems.md entry “Refactor: Decouple Telemetry from Refinement Logic using Observer Pattern” (architectural issues 1.3/2.3). Plan captures Observer pattern, Stage-specific telemetry collectors, and writer simplification.
- Attempts History:
  * 2025-12-02T190000Z — Plan scaffolded, compliance matrix recorded, and observer prototype tasks defined. Next loop will implement Phase A.1 collector + Stage A wiring.
  * 2025-12-02T191500Z — Phase A.1/A.2 complete: Created `dbex/refinement/interfaces.py` (RefinementObserver protocol, StageResult/telemetry dataclasses), `dbex/refinement/telemetry_collectors.py` (StageATelemetryCollector/B/C with observer callbacks), added helper methods to StageATelemetryState. Modules import successfully and pass static checks. Stage A closure wiring deferred due to scope/complexity (requires extensive closure refactoring in 1600+ line stage_a.py; current loop focused on interface/collector scaffolding per Phase A Do Now). Next: Thread collector through _build_lbfgs_closure and update StageA.run() to return StageResult. Artifacts: `plans/active/ARCH-TELEMETRY-001/reports/2025-12-02T191500Z/`.
  * 2025-12-02T201500Z — Phase B.1 complete: Threaded StageATelemetryCollector through Stage A LBFGS closure, replacing direct telemetry_state mutations with collector.on_step/on_validation callbacks. Updated _build_lbfgs_closure signature to accept collector parameter, modified closure body to route per-iteration and periodic validation telemetry through collector, and extended _run_stage_a_lbfgs to accept optional collector and route baseline/final/exception validations through observer callbacks. Fixed best_loss_full initialization from tuple to list for collector compatibility and corrected tuple reassignment for chi_squared_best/masked_mse_best in collector. Both mapped test selectors PASSED: test_stage_a_engine_delegation_telemetry and test_stage_a_expansion (DBEX_SMOKE_DETECTOR_SIZE=small). Telemetry diffs: zero (observer path produces identical schema). Next: Stage B/C collector wiring (Phase C.1) and writer integration. Artifacts: `plans/active/ARCH-TELEMETRY-001/reports/2025-12-02T201500Z/` (pytest logs, commit 1eea725c).

### [ARCH-BRIDGE-RESP-001] Writer / bridge responsibility split
- Depends on: ARCH-REFINE-001 (shared writer path), DIAGNOSTICS-001 & PHYSICS-LOSS-001/002/003 findings, problems.md writer/bridge directive
- Status: in_progress
- Priority: High
- Tier: 0
- Owner/Date: Galph ↔ Ralph / 2025-12-02
- Initiative Type: architecture
- Exit Criteria:
  1. `dbex/io/writer.py` consumes typed ROI analysis payloads (scores/scales/triptychs) and no longer runs Nelder–Mead internally; ROI scoring helpers capture artifacts referenced in docs/TESTING_GUIDE.md selectors.
  2. ROI scoring artifacts plus interface docs (`docs/architecture/dbex/io/writer.idl.md`, `docs/data_dependency_manifest.md`) describe the new responsibilities and telemetry provenance.
  3. `dbex/nanobrag_bridge.py` is broken into focused modules (RefinementInputs builder, detector/crystal config factories, calibration guards) that preserve GEOMETRY-00x + CONFIG-001 findings while shrinking the orchestration shim.
  4. CLI + Stage smoke selectors touching the writer/bridge remain green (tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata, Stage A/B/C smoketests); new/updated selectors include collect-only logs under this initiative’s reports and registry updates per docs/TESTING_GUIDE.md §2.
- Working Plan: `plans/active/ARCH-BRIDGE-RESP-001/implementation.md`
- Ledger tie-in: Resolves problems.md bullet “Writer / bridge responsibility split” by relocating Nelder–Mead analysis to tooling and reducing the nanobrag bridge god object.
- Attempts History:
  * 2025-12-02T213000Z — Initiative registered per problems-ledger guard; plan drafted with Phase A (contracts/dataclasses), Phase B (writer serialization cleanup), and Phase C (bridge decomposition). Artifacts staged at `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T213000Z/`.
  * 2025-12-02T213000Z (Phase A.0/A.2/A.3) — Boundary audit complete: captured `write_torch_outputs` callers (dbex/refine_one.py:604, tests mocks) and `prepare_refinement_inputs` callers (CLI, vis tools, 14 test suites). Created `dbex/io/roi_analysis.py` with ROITriptych, ROIAnalysisPayload, and build_roi_payloads_from_arrays helper (numpy-only, no optimization logic per Do Now). Extended `docs/architecture/dbex/io/writer.idl.md` with "ROI Analysis Payload" section describing new typed parameter, dataset mapping, and Phase B wiring plan. Updated `docs/data_dependency_manifest.md` with ROI helper entry (inputs: target/background/bragg arrays + pids/bbox; outputs: List[ROIAnalysisPayload]; telemetry: roi_scoring_method, roi_checker, n_rois). Mapped tests PASSED: test_torch_diagnostics_metadata (2/2 passed, 0.90s), test_tensor_contract (1/1 passed, 0.80s). No behavior change this loop; new module is unused scaffolding for Phase B wiring. Artifacts: `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T213000Z/` (boundary_audit.md, writer_callers.txt, bridge_callers.txt, pytest logs). Next: Phase B.1 — implement dedicated ROI scoring helper and wire CLI/engine paths.
  * 2025-12-02T223500Z — Phase B.1 in scope: add `dbex/io/roi_scoring.py` helper that runs Nelder–Mead + `roiCheck` scoring, emits `ROIAnalysisPayload` instances (variance + model populated), updates writer IDL/manifest entries to describe the helper, and adds targeted unit tests under `tests/dbex/test_roi_analysis.py`. Artifacts reserved at `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T223500Z/`. Writer remains unchanged this loop; CLI/tests continue to call the legacy inline scoring while we validate the new helper in isolation.
  * 2025-12-02T223500Z (Phase B.1) — Implementation complete: Created `dbex/io/roi_scoring.py` with `score_roi_payloads` helper that accepts full-detector arrays + ROI metadata, runs scipy.optimize.minimize with roiCheck objective per legacy parity (dbex/io/writer.py:106-110), and returns typed `ROIAnalysisPayload` with populated score/optimal_scale/model/variance fields. Helper imports scipy/score_trainer locally (Environment Freeze), validates sigma parameters (sigma_readout >= 0, sigma_floor > 0), and coerces scores to float (TORCH-CLI-004). Created `tests/dbex/test_roi_analysis.py` with 5 unit tests covering scale recovery, variance floor enforcement, injected checker/log_fn hooks, multiple ROIs, and sigma validation (all PASSED, 1.74s). Updated `docs/architecture/dbex/io/writer.idl.md` with helper signature/algorithm/telemetry and `docs/data_dependency_manifest.md` with manifest entry (inputs: target/background/bragg/pids/bbox/sigma_readout/sigma_floor; outputs: List[ROIAnalysisPayload]; transitive deps: scipy, score_trainer, build_roi_payloads_from_arrays). Existing CLI metadata test PASSED (test_torch_diagnostics_metadata: 2/2, 0.89s). Collection check confirms 5 tests discoverable (pytest --collect-only). No writer or CLI changes this loop; helper is unused scaffolding for Phase B.2 wiring. Artifacts: `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T223500Z/` (pytest_roi_analysis.log, pytest_torch_writer_metadata.log, pytest_collect_roi_analysis.log). Next: Phase B.2 — wire CLI/engine paths to call score_roi_payloads and pass typed payloads to write_torch_outputs.
  * 2025-12-02T233500Z (Phase B.2) — Implementation complete: Wired CLI path to call `score_roi_payloads` before writer. In `dbex/refine_one.py::run_nanobrag_backend`, added import of `score_roi_payloads`, derived sigma values in target units (sigma_readout from mean of `inputs.sigma_readout` or fallback to `sigma_reference_target_units`; sigma_floor with ADU→photon conversion when `--adu-per-photon` is set), converted `DataLoad.pids` and `DataLoad.bbox` to Python lists, called helper, and passed resulting payloads via new `roi_payloads=` kwarg to `write_torch_outputs`. Extended `write_torch_outputs` signature/docstring with `roi_payloads` parameter (default None, currently unused until Phase B.3 consumes them and removes inline Nelder-Mead loop). Updated `tests/dbex/test_refine_one_cli.py` to patch `score_roi_payloads` in `test_nanobrag_backend_runs_simulator` and `test_nanobrag_backend_applies_calibration` with mock return values and assert writer received `roi_payloads` kwarg; updated `test_torch_diagnostics_metadata` to pass `roi_payloads=None` (legacy inline scoring path). Updated `docs/architecture/dbex/io/writer.idl.md` with new `roi_payloads` parameter entry and `docs/data_dependency_manifest.md` with CLI usage note. Nanobrag backend test failures unrelated to Phase B.2 changes (mock detector config missing attributes for unified simulator factory; test was already fragile). Phase B.2 payload threading complete; writer now receives typed payloads on every CLI invocation. Artifacts: `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T233500Z/` (pytest logs). Next: Phase B.3 — consume `roi_payloads` in writer and remove inline Nelder-Mead loop once payload plumbing is proven stable.
  * 2025-12-03T003500Z (Phase B.3) — Implementation complete: Modified `dbex/io/writer.py::write_torch_outputs` to require non-None `roi_payloads` parameter, removing inline Nelder-Mead loop (scipy/score_trainer imports eliminated from writer). Writer now extracts triptych arrays/scores/variance directly from pre-scored `ROIAnalysisPayload` instances. Added `/torch_diagnostics` telemetry attrs: `roi_scoring_method="nelder_mead"`, `roi_checker="score_trainer.roi_check.roiCheck"` to record scoring provenance per DIAGNOSTICS-001. Updated `test_torch_diagnostics_metadata` to build minimal `ROIAnalysisPayload` with typed fields and assert new attrs present (PASSED 2/2 parametrized cases, 1.02s). Removed scipy/score_trainer mocks from test (no longer needed). Updated `docs/architecture/dbex/io/writer.idl.md` Phase B status, parameter table, telemetry docs, and change log; updated `docs/data_dependency_manifest.md` writer entry with required roi_payloads and Phase B.3 telemetry. Mapped tests: test_torch_diagnostics_metadata PASSED (validates writer serialization + new attrs); test_nanobrag_backend_runs_simulator/test_nanobrag_backend_applies_calibration FAILED (pre-existing mock fixture issues: detector_config missing `distance_mm`, mask_array not handling Mock types; unrelated to Phase B.3 writer changes). Metrics: writer now focuses solely on HDF5 serialization; ROI scoring decoupled per architecture. Artifacts: `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T003500Z/` (pytest logs, summary.md). Next Actions: Phase B.4 if needed (test registry update after validating CLI smokes), or move to Phase C (bridge decomposition) once CLI test mocks are fixed.
  * 2025-12-02T091255Z — Supervisor planning pass: reviewed Phase B.3 writer change fallout and cataloged the two failing CLI selectors. Root cause: patched `create_detector_config` now returns `Mock` objects that lack `distance_mm`, `(s,f)` beam centers, and real `mask_array` tensors, so `create_unified_simulator` raises before writer telemetry assertions. Updated implementation plan (B3) to call out the need for typed `DetectorConfig` fixtures and logged this summary; queued a Do Now for Ralph to refactor `tests/dbex/test_refine_one_cli.py::{test_nanobrag_backend_runs_simulator,test_nanobrag_backend_applies_calibration}` so they build real configs (via `nanobrag_torch.config.DetectorConfig`) and rerun the targeted selectors alongside `test_torch_diagnostics_metadata`. Artifacts: `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T091255Z/`.
  * 2025-12-02T091255Z (Phase B.3 CLI fixture repair complete) — Refactored `test_nanobrag_backend_runs_simulator` and `test_nanobrag_backend_applies_calibration` to use real typed `DetectorConfig`, `BeamConfig`, and `CrystalConfig` instances instead of bare Mock objects. Created three helper functions (`_make_detector_config`, `_make_beam_config`, `_make_crystal_config`) in tests/dbex/test_refine_one_cli.py:18-101 that instantiate actual nanobrag_torch.config dataclasses with deterministic parameters (distance_mm=100.0, cell_a/b/c=79/79/38, beam beamsize_mm=0 or 1.0, mask_array as float32 torch tensor). Updated both CLI tests to use these helpers and added `has_halo: False` to hkl_metadata mocks (required by JobContext validator). Corrected patch decorator from `@patch('dbex.io.writer.write_torch_outputs')` to `@patch('dbex.refine_one.write_torch_outputs')` to patch where imported. All three mapped selectors PASSED (4/4 parametrized cases, 1.01s): test_nanobrag_backend_runs_simulator, test_nanobrag_backend_applies_calibration, test_torch_diagnostics_metadata. Logs confirm simulators ran successfully with typed configs ("Simulator complete. Bragg shape: (1, 100, 100)"), writer received roi_payloads, and all CLI-001 / SCALE-002 / ARCH-BRIDGE-RESP-001 Phase B.3 guards verified. Artifacts: `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T091255Z/` (pytest_cli_success.log). Next Actions: Phase B.4 (test registry update if needed) or move to Phase C (bridge decomposition).
  * 2025-12-03T020500Z — Phase C kickoff (planning): updated the implementation plan to mark B1–B3 complete and drafted the bridge split scope (new `dbex/refinement/inputs.py` + `dbex/refinement/config_factories.py`, manifest/doc touch-points, dependent selectors). Reserved `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T020500Z/` for the decomposition evidence and rebuilt input.md with a ready-for-implementation Do Now covering the module moves, import rewrites, CLI/bridge/Stage A smoketests, and doc updates. Next action: ready_for_implementation.
  * 2025-12-03T020500Z (Phase C.1–C.3) — Refactored `prepare_refinement_inputs` + the detector/beam/crystal config helpers into dedicated modules (`dbex/refinement/inputs.py`, `dbex/refinement/config_factories.py`), rewired all internal imports (stages, CLI, forward helpers, vis tooling), left compatibility re-exports under `dbex.nanobrag_bridge`, and revalidated the mapped selectors (`tests/dbex/test_nanobrag_bridge.py`, `tests/dbex/test_nanobrag_bridge_configs.py`, targeted CLI tests, Stage A smoke). Captured before/after responsibility notes in `bridge_split_summary.md` under `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T020500Z/`. Remaining work: refresh docs/manifest references (Phase C.4) and plan the re-export removal once external consumers migrate.

### [ARCH-LAZY-IMPORTS-001] Lazy imports / process-noise hygiene
- Depends on: ARCH-REFINE-001 (Stage helpers stabilized), ARCH-STAGE-CONTEXT-001 (typed contexts), ARCH-ENGINE-002 finding (lazy-import staging rules)
- Status: in_progress
- Priority: High
- Tier: 0
- Owner/Date: Galph ↔ Ralph / 2025-12-02
- Initiative Type: architecture
- Exit Criteria:
  1. Geometry/physics leaf modules and Stage helper seams import their dependencies at module scope (with explicit optional guards) so diagnostics/tests see drift immediately; remaining lazy imports are documented exceptions.
  2. Docstrings/comments reference normative specs/findings instead of historical ticket IDs, reducing process-noise diffs.
  3. Import hygiene selector(s) cover these modules; docs/TESTING_GUIDE.md and TEST_SUITE_INDEX.md record them with collect-only logs under this initiative.
  4. Problems ledger entry "Lazy imports / process noise" links to this initiative and is marked done once the above hold.
- Working Plan: `plans/active/ARCH-LAZY-IMPORTS-001/implementation.md`
- Attempts History:
  * 2025-12-02T082202Z — Initiative created from problems.md ledger after two loops without ledger mention. Authored phased implementation plan (inventory, leaf cleanup, process-noise guards) and reserved artifacts directory `plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-02T082202Z/`. Next action: Phase A Do Now to inventory remaining lazy imports and dependency hotspots before code edits.
  * 2025-12-02T082202Z (Phase A complete) — Scanned repo for lazy imports (229 instances), created audit document identifying top offenders. Updated dbex/geometry/crystallography.py to move torch/nanobrag_torch imports to module scope with guarded try/except (_TORCH_AVAILABLE sentinel, _require_torch_crystal helper), preserving ImportError messages and updating docstrings with ARCH-ENGINE-002 references. Updated dbex/physics/forward.py to move torch/nanobrag_torch imports to module scope with guards (_require_torch_forward helper); kept dbex.* imports lazy per leaf-module constraint (circular dependency with nanobrag_bridge). Module imports PASSED (python -c import test). Mapped tests: test_nanobrag_backend_runs_simulator FAILED (pre-existing mock issue unrelated to imports, modules loaded successfully), test_db_at_027_zero_point_parity FAILED (pre-existing unpacking issue in test tooling, simulator initialized successfully proving imports work). Exit criteria 1 partially met (geometry/physics leaf modules done); exit criteria 2 partially met (geometry docstrings updated with GEOMETRY-001/003/ARCH-ENGINE-002). Artifacts: plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-02T082202Z/ (lazy_import_audit.md, lazy_import_rg.txt, pytest logs). Next: Phase B (Stage helper import cleanup after ARCH-REFACTOR-001 stabilizes).

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

### [PERF-WARM-SIM-001] Attempts History
  * 2025-12-02T173000Z — Phase F.1 debug hook implemented in `_retarget_stage_a_detectors`; small-detector (panel-mode) smoketest PASSED with 18 retarget calls capturing panel updates only, full-detector (ROI-mode) smoketest FAILED (expected) but produced 17 retarget calls with ~92 ROI entries per call showing simulator ID changes. Debug artifacts captured under `DBEX_STAGE_C_CACHE_DEBUG_PATH` for offline analysis. Next: Supervisor analyzes cache-debug JSONs to identify ROI simulator staleness root cause. Artifacts: `plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/`.
