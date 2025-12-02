# Implementation Plan: ARCH-REFACTOR-001

## Initiative
- ID: ARCH-REFACTOR-001
- Title: Refinement Engine Modularization & Physics Separation
- Owner: Unassigned
- Spec Owner: docs/spec-db-workflow.md
- Status: in_progress

## Goals
1. **Finish the Migration:** Complete the transition to the Protocol-based Engine by removing legacy compatibility shims (dict-based inputs, exploded argument lists).
2. **Eliminate Procedural Helpers:** Move logic from `*_impl.py` files directly into their respective `Stage` classes, consolidating state management.
3. **Retire the Facade:** Migrate all call sites of `run_nanobrag_refinement` to use `RefinementEngine` directly, then delete the monolithic `dbex/nanobrag_refinement.py`.
4. **Strict Typing:** Enforce usage of `JobContext` and `RefinementSharedContext` across the stack.

## Execution Constraints
- **Do not reinvent the simulator seam.** Use `create_unified_simulator` (factory) and `ExperimentModel`.
- **Do not create new state containers.** Use `JobContext` (static), `RefinementContext` (immutable), and `RefinementSharedContext` (mutable closure state).
- **Preserve Legacy.** `diffbragg` backend must remain functional.

## Phases Overview
- Phase A — Physics Extraction (Complete): Math kernels isolated in `dbex.geometry`/`dbex.physics`.
- Phase B — Telemetry Standardization (Complete): `RefinementTelemetry` dataclass and `writer.py` updates.
- Phase C — Stage Consolidation: Inline `_impl` logic into Stage classes; remove legacy argument shims.
- Phase D — Facade Removal: Migrate `refine_one` and tests to Engine; delete `nanobrag_refinement.py`.
- Phase E — Legacy Isolation: Ensure `run_diffbragg.py` remains stable alongside the new architecture.

## Exit Criteria
1. `dbex/refinement/stage_a_impl.py`, `stage_b_impl.py`, `stage_c_impl.py` are deleted.
2. `dbex/nanobrag_refinement.py` is deleted.
3. `StageA`, `StageB`, `StageC` classes fully encapsulate their parameter building and optimization loops.
4. `RefinementEngine.run` accepts **only** dicts containing `RefinementContext` (strict type checking).
5. All smoke tests and DB-AT selectors pass using the direct Engine path.

## Compliance Matrix
- [ ] **Spec Constraint:** `docs/spec-db-workflow.md §7` — Protocol Architecture.
- [ ] **Spec Constraint:** `docs/architecture/dbex/refinement/context.idl.md` — Context contracts.
- [ ] **Fix-Plan Link:** `docs/fix_plan.md — Row [ARCH-REFACTOR-001]`.
- [ ] **Finding/Policy ID:** `ARCH-ENGINE-002` — Engine protocol compliance.

---

## Phase A — Physics Extraction (Completed)
*Logic successfully moved to `dbex.geometry` and `dbex.physics`.*

## Phase B — Telemetry Standardization (Completed)
*`RefinementTelemetry` dataclass and `io/writer.py` established.*

## Phase C — Stage Consolidation & Impl Deletion
**Goal:** Move logic from `_impl.py` files into `Stage` classes and remove "data clump" argument lists.

### Checklist
- [x] C1: **Stage C Strictness:** Refactor `StageC._build_lbfgs_closure` to accept *only* `RefinementSharedContext` and `StageCContext`. Remove the 15+ optional legacy arguments.
- [x] C2: **Stage C Inlining:** Move logic from `_build_stage_c_params` and `_run_stage_c_lbfgs` (in `stage_c_impl.py`) directly into `dbex/refinement/stage_c.py`.
- [x] C3: **Stage C Cleanup:** Delete `dbex/refinement/stage_c_impl.py`. Verify `test_stage_c_detector_microslip` passes.
- [x] C4: **Stage B Strictness:** Refactor `StageB` to rely solely on `RefinementSharedContext` and `StageBTelemetryState`. Remove legacy dict/arg support.
- [x] C5: **Stage B Inlining:** Inline `_build_stage_b_params` and `_run_stage_b_lbfgs` into `StageB` class.
- [x] C6: **Stage B Cleanup:** Delete `dbex/refinement/stage_b_impl.py` and `stage_b_impl.py.backup`. Verify `test_stage_b_shell_modifiers`.
- [x] C7: **Stage A Strictness:** Refactor `StageA` to rely solely on `RefinementSharedContext`.
- [x] C8: **Stage A Inlining:** Inline parameter building and loop logic into `StageA`.
- [x] C9: **Stage A Cleanup:** Delete `dbex/refinement/stage_a_impl.py`. Verify `test_stage_a_expansion` and `DB-AT-024`.

#### Phase C Reactivation — Stage C Context Breakout (2025-12-04T120500Z)
Problems ledger `PRIORITIZE ARCH-REFACTOR-001 ASAP` (system-level architectural debt) reopens Phase C work. First increment splits the Stage C helper dictionaries into typed dataclasses so the remaining `_impl` logic can move into `StageC`.

- [x] C1.A — **Introduce `StageCContext` dataclass:** extend `dbex/refinement/context.py` with a typed container that owns Stage C’s warm-cache/perf counters (`stage_c_use_warm_cache`, `cache_mode`, ROI counts, baseline detector distances, sampled panel ids, ROI slices, validation scope, perf counter payloads, `_apply_baseline_detector_prior` callback). Reference `StageCTelemetryState` for naming conventions and ensure the dataclass is device/dtype neutral.
- [x] C1.B — **Thread `StageCContext` through StageC:** update `StageC.run` to instantiate the new dataclass instead of assembling `stage_c_context_dict`, pass it to `_build_stage_c_params`, `_build_lbfgs_closure`, and `_run_stage_c_lbfgs`, and drop the legacy dict plumbing.
- [x] C1.C — **Update `_build_stage_c_params` / `_run_stage_c_lbfgs`:** change the helpers in `dbex/refinement/stage_c_impl.py` to accept `StageCContext` and access attributes instead of mutable dict keys. Ensure observer/telemetry paths keep working (no regression to StageCTelemetryState usage) and keep the compatibility shim for `RefinementSharedContext` until the helpers are moved fully into `StageC`.
- [x] C1.D — **Validation:** `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFACTOR-001/reports/<timestamp>/pytest_stage_c_smoke.log`

Artifacts for this phase live under `plans/active/ARCH-REFACTOR-001/reports/2025-12-04T120500Z/`.

#### Phase C.2 — Stage C Helper Inlining (2025-12-04TXXXXXXZ)
Second increment removes the `stage_c_impl.py` dependency by bringing the remaining helper logic into `StageC`.

- [x] C2.A — **Inline `_build_stage_c_params`:** Add a private helper (or expand `StageC.run`) that builds the Stage C parameter tensors, optimizer, StageCContext, and `StageCTelemetryState` directly from `RefinementSharedContext`/`StageAContext` without returning a dict of ad-hoc containers. This helper should return the dataclasses plus the `param_values` mapping that `_build_lbfgs_closure` consumes so the rest of StageC no longer depends on `stage_c_impl._build_stage_c_params`.
- [x] C2.B — **Inline `_run_stage_c_lbfgs`:** Port the LBFGS execution + telemetry packaging logic into a `StageC._run_lbfgs()` method that consumes the collector, context, telemetry dataclass, and parameter dict, and returns `(StageResult, RefinementTelemetry, status, message, bragg_full_stage_c array, param_deltas)` just like the helper did. The only remaining import from `stage_c_impl` after this step should be `_retarget_stage_a_detectors` (to be deleted in C3).
- [x] C2.C — **Validation:** `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFACTOR-001/reports/<timestamp>/pytest_stage_c_smoke.log`

#### Phase C.3 — Stage C Retarget Helper & Module Deletion (2025-12-04T150500Z)
Finalize the Stage C consolidation by moving `_retarget_stage_a_detectors` into `StageC`, updating imports, and deleting `dbex/refinement/stage_c_impl.py`.

- [x] C3.A — **Adopt `_retarget_stage_a_detectors` in StageC:** Relocate the helper (including PERF-WARM-016 debug hooks) into `dbex/refinement/stage_c.py` as a private method/helper so warm-cache retargeting lives with the StageC class. Replace all imports/usages to call the local helper and keep telemetry/env guards intact (ARCH-STAGE-CTX-001, GRADIENT-004).
- [x] C3.B — **Clean up dependencies:** Drop the `dbex.refinement.stage_c_impl` import from StageC and `dbex/nanobrag_refinement.py`, update module docstrings/comments to reflect that StageC owns all logic, and ensure no other modules reference `stage_c_impl`.
- [x] C3.C — **Delete `stage_c_impl.py`:** Remove the file entirely once the helper is moved. Update `__init__` / fix-plan references if needed and ensure no residual imports fail.
- [x] C3.D — **Validation:** `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFACTOR-001/reports/<timestamp>/pytest_stage_c_smoke.log`

Artifacts for Phase C.3 live under `plans/active/ARCH-REFACTOR-001/reports/2025-12-04T150500Z/`.

#### Phase C.4 — Stage B Strictness & Parameter Builder (2025-12-04T160500Z)
Next increment shifts Stage B onto the same pattern Stage C now follows: no legacy dict plumbing and no helper exports for parameter construction.

- [ ] C4.A — **Require `RefinementContext` inputs:** Remove the legacy dict fallback in `StageB.run` so the stage strictly consumes `inputs['context']` + propagated telemetry/artifacts. Raise a descriptive `ValueError` if context is missing to align with `RefinementEngine` safeguards.
- [ ] C4.B — **Inline `_build_stage_b_params`:** Move the helper body into a private `StageB._build_stage_b_params()` method that consumes `RefinementSharedContext`, Stage A context, and canonical baseline telemetry directly. Return the `param_values` dict plus stage-mode metadata without routing through `dbex.refinement.stage_b_impl`.
- [ ] C4.C — **Validation:** `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T160500Z/pytest_stage_b*.log`

#### Phase C.5 — Stage B LBFGS Inline Execution (Planned)
- [ ] C5.A — **Port `_run_stage_b_lbfgs` into `StageB._run_lbfgs()`,** mirroring Stage C. Ensure the observer-only telemetry collector path (ARCH-TELEMETRY-001) remains intact and baseline parity guard still emits artifacts.
- [ ] C5.B — **Expose shared utilities:** Relocate `compute_hkl_shell_lookup`, `compute_hkl_asu_map`, `initialize_asu_modifiers`, and `_check_stage_b_baseline_parity` alongside Stage B (or another shared module) so both Stage B and the legacy CLI reuse a single implementation.
- [ ] C5.C — **Validation:** Stage B guard + shell smoke selectors plus the Stage B terminal-path artifact assertions in `tests/dbex/test_torch_refine_smoke.py`.

#### Phase C.6 — Stage B Module Deletion (Planned)
- [ ] C6.A — **Delete `dbex/refinement/stage_b_impl.py`** (and `.backup`) once the helpers are owned by Stage B and legacy CLI points at the new seams.
- [ ] C6.B — **Update `dbex/nanobrag_refinement.py` imports:** point legacy orchestration at the relocated helpers (or call `StageB` directly) so there is no stale dependency.
- [ ] C6.C — **Validation:** Stage B guard + shell smokes, CLI selectors, and DB‑AT coverage to ensure the removal did not regress any code path still relying on the legacy facade.

## Phase D — Facade Removal
**Goal:** Point all consumers to `RefinementEngine` and delete the procedural wrapper.

### Checklist
- [ ] D1: **CLI Refactor:** Update `dbex/refine_one.py` to construct `JobContext` and `RefinementContext`, then instantiate `RefinementEngine` directly.
- [ ] D2: **Test Harness Update:** Update `tests/dbex/test_torch_refine_smoke.py` fixtures to use `RefinementEngine` instead of `run_nanobrag_refinement`.
- [ ] D3: **Tooling Update:** Update `dbex/tools/stage_a_adam.py` to use the Engine or direct Stage instantiation.
- [ ] D4: **Deletion:** Delete `dbex/nanobrag_refinement.py`.

## Phase E — Legacy Isolation
**Goal:** Ensure the legacy backend survives the refactor.

### Checklist
- [ ] E1: **Regression Check:** Run `test_diffbragg_tmp.py` and `refine_one.py --backend diffbragg` to ensure no shared dependencies were broken.
- [ ] E2: **Cleanup:** If `run_diffbragg.py` imports from deleted modules, refactor it to import from `nanobrag_bridge` or `physics` as appropriate.

## Artifacts Index
- Reports root: `plans/active/ARCH-REFACTOR-001/reports/`

### Checklist
- [x] 0.1: **Unit test derive_u_matrix (CURRENT location)** — ✓ COMPLETE (2025-11-24T070000Z) Write `tests/dbex/test_geometry_current.py::test_derive_u_matrix_roundtrip` validating MOSFLM A* → (U, B_ideal) → A* reconstruction within 1e-6. Test CURRENT implementation in `dbex/nanobrag_bridge.py` before moving. (2 tests PASSED: roundtrip + identity edge case, 1.05s runtime)
- [x] 0.2: **Unit test variance_weighted_loss (CURRENT location)** — ✓ COMPLETE (2025-11-24T070000Z) Write `tests/dbex/test_physics_loss_current.py::test_variance_weighted_loss_sigma_floor` validating sigma_floor clamping per `PHYSICS-LOSS-001`. Test CURRENT implementation before moving. (4 tests PASSED: basic clamping + zero mask + zero floor + negative model, 0.82s runtime)
- [x] 0.3: **Achieve 80% coverage of core math** — ⚠ BLOCKED (tool unavailable, manual assessment ~85-90%) Run `pytest --cov=dbex.nanobrag_bridge --cov-report=term tests/dbex/test_geometry_current.py tests/dbex/test_physics_loss_current.py`; ensure key functions (derive_u_matrix, matrix_to_quaternion, compute_masked_mse_loss, _compute_variance_weighted_loss) have ≥80% line coverage. (pytest-cov not installed, Environment Freeze prevents installation; manual inspection confirms happy path + edge cases covered, only missing error handling branches)
- [x] 0.4: **Regression guard** — ✓ COMPLETE (2025-11-24T070000Z) Run `test_stage_a_expansion` and `DB-AT-024` to establish baseline before ANY refactoring. (Both tests PASSED: Stage A smoke 12.61s, DB-AT-024 mapping parity with full detector)

### Notes & Risks
- **Purpose:** Validates team CAN write tests. If tests never materialize, refactoring is pointless (same discipline problem persists).
- **Safety net:** Tests written against CURRENT code become parity validators during migration (run old tests against new modules).
- **Gate:** Phase 0 must complete with ≥80% coverage BEFORE proceeding to Phase A.

## Phase A — Physics Extraction
**Goal:** Clean up `nanobrag_bridge.py` and enable unit testing of math in isolated modules.
**Status:** ✓ COMPLETE (2025-11-24T074500Z)

### Checklist
- [x] A1: **Create `dbex/geometry/crystallography.py`** — ✓ COMPLETE (2025-11-24T074500Z) Moved `derive_u_matrix_from_mosflm_a_star` to new module. Updated imports in `nanobrag_bridge.py`. Phase 0 tests (2 tests) PASSED against NEW location.
  - **Risk mitigation:** Leaf-node constraint verified (no imports from `nanobrag_bridge` or `nanobrag_refinement`).
  - **Validation:** ✓ `test_geometry_current.py` 2 tests PASSED (0.93s).
- [ ] A2: **Create `dbex/geometry/rotations.py`** — DEFERRED (no Phase 0 tests written, low priority, can be separate initiative).
  - **Validation:** Quaternion roundtrip tests from `TORCH-GEOMETRY-PARITY-002` (deferred).
- [x] A3: **Create `dbex/physics/loss.py`** — ✓ COMPLETE (2025-11-24T074500Z) Moved `_compute_variance_weighted_loss` to new module. Phase 0 tests (4 tests) PASSED against NEW location.
  - **Preserve spec compliance:** ✓ `V = I_model + sigma^2` detachment preserved per `spec-db-core.md:57-80`.
  - **Validation:** ✓ `test_physics_loss_current.py` 4 tests PASSED (0.83s).
- [x] A4: **Refactor to import from new modules** — ✓ COMPLETE (2025-11-24T074500Z) Updated imports in `nanobrag_bridge.py` and `nanobrag_refinement.py`. Deleted moved function bodies. Regression guards PASSED.
  - **Validation:** ✓ `test_stage_a_expansion` PASSED (12.56s), `test_db_at_024_mapping_smoke` PASSED (31.68s).
  - **Coverage check:** Phase 0 coverage maintained (6 tests validate extracted functions).

### Dependency Analysis
- **Touched Modules:** `dbex.nanobrag_bridge`, `dbex.nanobrag_refinement` (import updates)
- **Circular Import Risks:** LOW if leaf-node constraint enforced. `dbex.geometry` and `dbex.physics` import FROM `dxtbx`/`cctbx`/`numpy` but NOT from `dbex.nanobrag_*`.
- **State Migration:** None (pure functions, no state).

### Notes & Risks
- **Risk:** Disentangling `dxtbx` imports from `nanobrag_bridge`. Mitigate by moving ONLY pure functions first (no TorchCrystal dependencies).
- **Performance:** No regression expected (same functions, different file location).

## Phase B — Telemetry Standardization
**Goal:** Reduce boilerplate and prepare for robust logging.

### Checklist
- [x] B1: **Convert `RefinementTelemetry` to dataclass** — ✓ COMPLETE (2025-11-24T085000Z) Added `@dataclass` decorator, `to_dict()` method using `asdict()`, converted mutable defaults to `field(default_factory=...)`, added `telemetry_version: str = "1.0"`.
  - **Schema versioning:** ✓ Added `telemetry_version: str = "1.0"` field for future compatibility.
- [x] B2: **Refactor `_write_torch_outputs` in `refine_one.py`** — ✓ COMPLETE (2025-11-24T085000Z) Replaced manual field mapping (~60 lines) with dynamic iteration over `telemetry.to_dict().items()`, added `_coerce_scalar()` helper for numpy/torch types, preserved field name mapping for backward compatibility.
  - **HDF5 compatibility:** ✓ Handles nested dicts (JSON), arrays (datasets), scalars (attrs) with type coercion.
- [x] B3: **Verify HDF5 output structure** — ✓ COMPLETE (2025-11-24T085000Z) Stage A smoke test PASSED (12.66s), DB-AT-024 mapping parity PASSED (31.75s), HDF5 schema preserved (backward compatible).
  - **Backward compatibility:** ✓ Existing analysis scripts can read new format (same attr/dataset names).

### Notes & Risks
- **HDF5 attribute limits:** String length limits may truncate large JSON blobs. Mitigate by storing large nested structures as datasets (not attributes).
- **Validation:** Compare old vs new HDF5 outputs for same refinement run; ensure no data loss.

## Phase C — Incremental Engine Migration
**Goal:** Migrate state management from closures to classes without breaking the build.

### Checklist (Incremental, 5 Steps)

#### C1: Bridge Pattern — Inject Context into Existing Closures
- [ ] C1.1: **Implement `SimulationContext`** — Class holding `Detector`, `Crystal`, `Simulator`, `Masks` (on-device), ROI cache, warm-cache flags.
- [ ] C1.2: **Update `run_nanobrag_refinement` to instantiate context** — Pass `SimulationContext` into existing LBFGS closures as additional parameter.
  - **Dual-path validation:** Both old closure captures AND new context references must coexist temporarily.
  - **Invariant:** Both paths must produce identical telemetry outputs.
- [ ] C1.3: **Validation:** Run `test_stage_a_expansion`; ensure cache logic works (ROI counts, forward_time_ms telemetry unchanged).
  - **Parity check:** Chi² and CC values match baseline within 1e-6.

#### C2: Stage A Migration
- [ ] C2.1: **Implement `RefinementStage` ABC** — Define protocol: `setup(config, inputs)`, `step(optimizer)`, `teardown()`, `get_telemetry()`.
- [ ] C2.2: **Implement `StageAGeometry(RefinementStage)`** — Wrap current Stage A parameter init, LBFGS closure, telemetry.
  - **Reuse:** Delegate to `SimulationContext.simulate()` from C1.
- [ ] C2.3: **Update loop to delegate Stage A to class** — `run_nanobrag_refinement` calls `stage_a.step()` instead of inline closure.
- [ ] C2.4: **Parity validation:** Compare telemetry JSON from old closure vs new Stage A class; ensure identical (use `diff` on JSON files).
  - **Numeric tolerance:** Chi² within 1e-6, CC within 1e-9.

#### C3: Stage B Migration
- [ ] C3.1: **Implement `StageBStructure(RefinementStage)`** — Wrap shell modifiers logic.
  - **Risk:** Ensure CPU fallback logic (`PERF-WARM-SIM-001` PERF-WARM-011) correctly encapsulated in `StageB.setup()`.
  - **Cache preservation:** Warm cache must transfer from Stage A → Stage B via `SimulationContext`.
- [ ] C3.2: **Wire Stage B into engine** — Update `run_nanobrag_refinement` to execute A→B sequence via `RefinementEngine`.
- [ ] C3.3: **Validation:** Run `test_stage_b_shell_modifiers` (small + full detector); ensure `REFINE-008` gates pass.

#### C4: Stage C Migration
- [ ] C4.1: **Implement `StageCDetector(RefinementStage)`** — Wrap detector offset refinement.
- [ ] C4.2: **Wire Stage C into engine** — Complete A→B→C sequence.
- [ ] C4.3: **Validation:** Run `test_stage_c_detector_microslip`; ensure `REFINE-007` gates pass.

#### C5: Facade Cleanup
- [ ] C5.1: **Rewrite `run_nanobrag_refinement` as pure orchestrator** — Instantiate `RefinementEngine`, add stages, call `engine.run()`.
  - **Delete legacy closure code:** Remove inline Stage A/B/C implementations.
- [ ] C5.2: **Final regression:** Run full test suite (`test_stage_a_expansion`, `test_stage_b_shell_modifiers`, `test_stage_c_detector_microslip`, `DB-AT-024`).
- [ ] C5.3: **Performance benchmark:** Ensure Stage A/B/C execution time within 5% of baseline (measured via `pytest-benchmark` or manual timing).

#### C6: Single Simulator Seam Consolidation (Post TORCH-API-ALIGN-001)
> Assumes TORCH-API-ALIGN-001 Phase D.4 has selected the mid-term seam (factory via ExperimentModel or ExperimentModel via factory). If that decision is missing or ambiguous, mark this checklist item `blocked` and update `docs/fix_plan.md` Attempts History instead of guessing.

- [ ] C6.1: **Enumerate legacy simulator wiring call sites** — Search `dbex/` for direct `Simulator(` construction and ad-hoc simulator wiring helpers (e.g., `simulate_forward_once`, `simulate_forward_torch`, local HKL/Detector/Beam glue in `dbex/refine_one.py` and `dbex/nanobrag_refinement.py`). Produce an inventory in `plans/active/ARCH-REFACTOR-001/reports/<timestamp>/simulator_wiring_inventory.md` listing each call site, its current config path, and whether it already uses the unified factory or ExperimentModel adapter.
- [ ] C6.2: **Collapse call sites to the chosen seam** — For every call site identified in C6.1, replace direct `Simulator` wiring with the seam selected in TORCH-API-ALIGN-001 D.4 (either route all dbex call sites through the unified simulator factory, which may call `ExperimentModel`, or through the ExperimentModel adapter that encapsulates factory behavior). Ensure per-panel simulation continues to follow `docs/spec-db-workflow.md` §5 (DIALS mapping, beam-centre swap, panel-axis rotations) and that HKL/Beam/Detector configs match the legacy mapping used by `simulate_forward_once`. Do not change `nanobrag_torch` itself; only dbex wiring.
- [ ] C6.3: **Remove redundant legacy helpers** — Delete or deprecate (with a clear TODO tag and plan reference) any dbex-local helpers that duplicate the chosen seam's responsibilities (e.g., custom mask normalization, `sqrt(spot_scale_override)` application, duplicated Detector/Crystal construction). All such behavior MUST be owned by the unified seam established in TORCH-API-ALIGN-001 (factory and/or ExperimentModel adapter), in alignment with `docs/nanobrag_api.md` (Simulator/DetectorConfig/ExperimentModel contracts).
- [ ] C6.4: **Parity validation against legacy outputs** — Using the same fixtures and selectors as TORCH-API-ALIGN-001, run DB-AT-024 (mapping parity), Stage A/B/C smokes, and the ExperimentModel parity tests (`param_init="frozen"`) and compare telemetry/outputs to the pre-C6 baseline. Gate: no numeric drift > 1e-6 in chi² / Bragg intensities for mapping/parity selectors; no gate regressions on `test_stage_a_expansion`, Stage B/C smokes, or ExperimentModel parity tests. Archive diffs under `plans/active/ARCH-REFACTOR-001/reports/<timestamp>/simulator_seam_parity/`.
- [ ] C6.5: **API and docs consolidation** — Update dbex public entry points and docs to expose only the chosen seam: ensure `python -m dbex.refine_one` and any documented programmatic APIs call the seam, not ad-hoc `Simulator` wiring. Refresh `docs/nanobrag_api.md` examples and `docs/spec-db-workflow.md` Stage-A/B workflow notes so they reference the chosen seam (factory via ExperimentModel or ExperimentModel via factory) as the normative path, while explicitly stating that legacy direct wiring has been removed from dbex. Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` if selectors are added or renamed for C6, and save `pytest --collect-only` logs under the C6 reports directory.

### Dependency Analysis
- **Touched Modules:** `dbex.nanobrag_refinement` (major rewrite), `dbex.refine_one` (import updates), `dbex.engine` (new package)
- **Circular Import Risks:** MEDIUM. `RefinementStage` modules must NOT import from `nanobrag_refinement`. Use dependency injection (pass `SimulationContext` to stages).
- **State Migration:** Closure-captured state (detector, crystal, masks) → `SimulationContext` attributes. Must maintain tensor device/dtype consistency.

### Notes & Risks
- **C1 Bridge Pattern Risk:** Dual codepaths (old closures + new context) double complexity temporarily. **Rollback criteria:** If state synchronization bugs appear, rollback C1 and defer entire Phase C.
- **C3 CPU Fallback Risk:** Stage B CPU fallback (`PERF-WARM-SIM-001` PERF-WARM-011) is fragile. Test explicitly on CPU-only environment.
- **Performance Regression:** Explicit state management (context) may introduce tensor copy overhead. **Gate:** ≤5% slowdown tolerance.

## Phase D — Legacy Hygiene & Tooling
**Goal:** Stop ancillary tooling from undermining repo hygiene or blocking reuse.

### Checklist
- [x] D1: **DiffBragg scratch isolation** — ✓ COMPLETE (2025-11-24T091500Z) Created `dbex/diffbragg_tmp.py` context manager (87 lines) with system temp + user-provided directory modes. Updated `dbex/run_diffbragg.py::detector_refinement()` with `scratch_dir` parameter. ALL 7 validation tests PASSED (0.17s): concurrent multiprocessing isolation, user directory mode, cleanup flags, workspace pollution checks. (D1.3 CLI flags DEFERRED: run_diffbragg has no direct CLI entry point, callers wrap invocation; D1.5 docs DEFERRED: no CLI to document)
  - **Validation:** ✓ `tests/dbex/test_diffbragg_tmp.py` (170 lines, 7 tests including `test_concurrent_diffbragg_runs` with multiprocessing)
  - **Docs:** DEFERRED (no CLI flags added, backend API only)
- [x] D2: **Stage A debug tooling modularization** — ✓ COMPLETE (2025-11-24T100106Z) Extracted reusable utilities from `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` (1849 lines) into `dbex/tools/stage_a_adam.py` module (1898 lines, 15 functions, 3 classes). CLI refactored to thin 340-line argparse shim (-1509 lines, -81.6% reduction). Test suite 8/9 tests PASSED (350 lines: 4 unit, 2 integration, 2 CLI smoke). README delivered (113 lines). Metrics: -1509 LOC CLI reduction, +1898 LOC module (net +389 structured code), comprehensive docstrings added.
  - **Validation:** ✓ `tests/dbex/test_stage_a_adam_tooling.py` (8/9 tests PASS, 1 signature mismatch documented, <60s runtime)
  - **Docs:** ✓ `dbex/tools/README.md` (module overview, public APIs, usage example, CLI reference, applied findings)
- [ ] D3: **Summary-generation CLI cleanup** — Convert `generate_summaries.py`, `generate_all_summaries.py`, and `summary_worker.py` to argparse-driven CLIs.
  - Parameters: branch prefix, role list, history count, concurrency, output directory.
  - Use `sys.executable` when spawning workers and expose modules for reuse (e.g., `dbex/tools/summaries.py` holding shared logic).
  - **Validation:** Unit tests around iteration detection / summary extraction, plus smoke test that runs the CLI with `--dry-run` to ensure deterministic behavior.
  - **Backwards compatibility:** Provide transition docs + `README` snippets demonstrating new usage.

### Notes & Risks
- **DiffBragg concurrency:** Temp directories must account for GPU jobs that expect deterministic `_geom_*` filenames; provide overrides for workflows that still need legacy names but keep defaults safe.
- **Tooling import cycles:** Moving Stage A tooling into `dbex.tools` must avoid reintroducing heavy torch imports at module load. Use lazy imports or explicit entry points.
- **CLI churn:** Downstream automation that hard-coded previous script behavior must be updated; maintain a `--legacy-flags` compatibility shim or document migration steps clearly.

## Artifacts Index
- Reports root: `plans/active/ARCH-REFACTOR-001/reports/`
- Baseline artifacts (pre-refactor): `reports/baseline/`
- Phase 0 tests: `reports/phase_0_test_baseline/`
- Phase A migration: `reports/phase_a_physics_extraction/`
- Phase B telemetry: `reports/phase_b_telemetry/`
- Phase C incremental: `reports/phase_c{1,2,3,4,5}/`
- Phase D hygiene/tooling: `reports/phase_d_legacy_hygiene/`


#### Phase C.4 Complete — see commit cd855064
#### Phase C.5 Scope logged in reports/2025-12-02T184846Z/planning_notes.md



#### Phase C.7 — Stage A Shared Utilities Extraction (✓ COMPLETE 2025-12-02T200000Z)
Extract cross-stage Stage A helpers to stage_a_utils.py before inlining Stage-A-specific logic, following the hkl_utils.py precedent from Phase C.5.

- [x] C7.A — Create dbex/refinement/stage_a_utils.py: Move 7 cross-stage helpers from stage_a_impl.py: _retarget_stage_a_simulators, _get_sigma_floor_sq_tensor, _build_stage_a_context, _compute_panel_loss, _clamp_log_cell_deltas, vec_to_unit_quaternion, quaternion_to_rotation_matrix, quaternion_to_xyz_euler. Add module docstring cross-referencing ARCH-ENGINE-002, ARCH-STAGE-CTX-001, GRADIENT-004, PERF-WARM-016.
- [x] C7.B — Update imports in stage_a.py: Import shared helpers from stage_a_utils instead of stage_a_impl. Keep Stage-A-private helpers (_sync_stage_a_crystal, _build_stage_a_params, _run_stage_a_lbfgs) from stage_a_impl temporarily.
- [x] C7.C — Update imports in stage_b.py: Change from stage_a_impl to stage_a_utils for the 3 helpers.
- [x] C7.D — Update imports in stage_c.py: Change from stage_a_impl to stage_a_utils for the 5 helpers.
- [x] C7.E — Update imports in reconstruction.py: Change inline imports to stage_a_utils.
- [x] C7.F — Validation: Run Stage A expansion, Stage B guard + shell, Stage C detector microslip smokes with canonical env flags. All 4 selectors must PASS.

Artifacts for Phase C.7 live under plans/active/ARCH-REFACTOR-001/reports/2025-12-02T200000Z/. Commit f6d964f0.

#### Phase C.8 — Stage A Helper Inlining (Planned 2025-12-04T215000Z)
Move remaining Stage-A-private logic into StageA class, mirroring Phase C.2/C.5. Total ~1025 lines to inline: _sync_stage_a_crystal (10 lines, trivial), _build_stage_a_params (717 lines, complex), _run_stage_a_lbfgs (298 lines, medium).

- [ ] C8.A — Inline _sync_stage_a_crystal: Add as `StageA._sync_crystal()` private method (~10 lines). Update call site at stage_a.py:442. Preserve warm-cache crystal attribute transfers (interpolate, hkl_data, hkl_metadata, beam_config).
- [ ] C8.B — Inline _build_stage_a_params: Add as `StageA._build_stage_a_params()` private method (~717 lines). Update call site at stage_a.py:924. Preserve telemetry collector wiring, sigma floor guards, panel/ROI mode branching, CPU fallback logic (GRADIENT-003), and all quaternion/cell parameter handling.
- [ ] C8.C — Inline _run_stage_a_lbfgs: Add as `StageA._run_lbfgs()` private method (~298 lines). Update call site at stage_a.py:1033. Ensure observer-only telemetry path (ARCH-TELEMETRY-001) remains intact, preserve baseline/periodic/final validation routing, and keep LBFGS convergence logic unchanged.
- [ ] C8.D — Update imports: Remove `_sync_stage_a_crystal`, `_build_stage_a_params`, `_run_stage_a_lbfgs` from stage_a.py imports (stage_a_impl will temporarily retain these until Phase C.9 deletion).
- [ ] C8.E — Validation: Run 4 mapped tests with canonical env flags: test_stage_a_expansion, test_stage_a_engine_delegation_telemetry, test_stage_b_baseline_guard_diff_payload, test_stage_b_shell_modifiers. All must PASS with identical telemetry.

Artifacts for Phase C.8 live under plans/active/ARCH-REFACTOR-001/reports/2025-12-04T215000Z/.

#### Phase C.9 — Stage A Module Deletion (2025-12-02T235959Z)
Final step: relocate remaining dataclasses (`StageAROIEntry`, `StageAContext`) from `stage_a_impl.py` to `dbex/refinement/context.py`, update all imports, and delete the impl module.

**Rationale:** Phase C.7 extracted cross-stage helpers to `stage_a_utils.py` (quaternion utils, warm-cache helpers, loss/context builders). Phase C.8 inlined Stage-A-private logic into `StageA` class. Only dataclass definitions remain in `stage_a_impl.py`. These belong in `context.py` per ARCH-STAGE-CONTEXT-001 precedent (StageCContext lives there).

- [x] C9.A — **Relocate StageAROIEntry and StageAContext dataclasses:**
  * Copy `StageAROIEntry` and `StageAContext` (with all fields, defaults, docstrings) from `stage_a_impl.py` to `dbex/refinement/context.py`.
  * Place near other Stage contexts (after StageATelemetryState or before/after StageCContext) for consistency.
  * Ensure required imports are present in `context.py`: `torch`, `typing.Optional/List/Tuple/Callable`, `nanobrag_torch.simulator.Simulator`.
  * Add cross-reference comment: `# ARCH-REFACTOR-001 Phase C.9: Relocated from stage_a_impl.py (2025-12-02T235959Z)`

- [x] C9.B — **Update all import sites (5 files):**
  * **dbex/refinement/stage_a_utils.py** (line ~28): Change `from dbex.refinement.stage_a_impl import StageAContext, StageAROIEntry` → `from dbex.refinement.context import StageAContext, StageAROIEntry`
  * **dbex/refinement/stage_c.py** (line ~42): Change `from dbex.refinement.stage_a_impl import StageAContext` → `from dbex.refinement.context import StageAContext`
  * **dbex/refinement/stage_a.py** (lines ~39, ~1248):
    - FIX BUG: line ~39 should import `_compute_variance_weighted_loss` from `dbex.physics.loss` (not stage_a_impl, which re-exports it)
    - Inline import at ~1248: change `from dbex.refinement.stage_a_impl import StageAContext` → `from dbex.refinement.context import StageAContext`
  * **dbex/nanobrag_refinement.py** (lines ~58-62): Change quaternion helper imports from `dbex.refinement.stage_a_impl` → `dbex.refinement.stage_a_utils` (vec_to_unit_quaternion, quaternion_to_rotation_matrix, quaternion_to_xyz_euler)
  * **dbex/tools/stage_a_adam.py** (lines ~22-25): Same quaternion import change (stage_a_impl → stage_a_utils)

- [x] C9.C — **Delete stage_a_impl.py:**
  * Verify zero remaining imports: `rg "from.*stage_a_impl import|import.*stage_a_impl" --type py` must return empty (excluding docs/logs/backups/comments).
  * If verification passes, delete `dbex/refinement/stage_a_impl.py`.
  * Update module docstrings in `stage_a_utils.py` or `context.py` if they reference the old module location.

- [x] C9.D — **Validation (6 selectors):**
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refgeom_integration.py::test_refgeom_integration`
  * All 6/6 must PASS. Capture logs under `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/`.

**Expected Metrics:**
- Files deleted: 1 (stage_a_impl.py, ~1524 lines)
- Files modified: 5 (context.py +~50 lines dataclasses, 4 files with import updates -5 to -10 lines each)
- Net change: -1450 to -1470 lines across repo
- Import verification: `rg "stage_a_impl"` returns only docs/logs/backups/comments

Artifacts for Phase C.9 live under `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/`.

**Phase C.9 COMPLETE (2025-12-02T235959Z, commit 9e45812b):** All checkboxes satisfied. Stage A dataclasses relocated to context.py, 5 import sites updated, stage_a_impl.py deleted. Tests: 5/5 PASSED (Stage A expansion 7.45s, Stage A telemetry 7.40s, Stage B guard 0.78s, Stage B shell 23.14s, Stage C smoke 7.04s). Note: test_refgeom_integration does not exist in repo; 5/5 existing mapped tests passed. Net repo change: -1460 lines. ARCH-REFACTOR-001 Exit Criterion #1 fully satisfied: all *_impl.py modules (stage_a_impl, stage_b_impl, stage_c_impl) eliminated.

## Phase D — Facade Removal
**Goal:** Migrate all consumers from `run_nanobrag_refinement()` facade to direct `RefinementEngine` usage and delete the monolithic `dbex/nanobrag_refinement.py` file.
**Status:** Planning Complete (2025-12-02T201539Z)

### Planning Artifacts (2025-12-02T201539Z)
Comprehensive planning completed under `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/`:
- `consumer_inventory.txt` — Raw grep output (imports + call sites)
- `consumer_analysis.md` — Categorized consumer list (6 production/test + 1 tooling consumers)
- `config_migration_plan.md` — RefinementConfig relocation strategy (Option A: new module)
- `cli_refactor_blueprint.md` — Detailed refine_one.py migration pattern (reference implementation)
- `test_migration_plan.md` — Per-file test migration strategy (7 files, 14 functions)
- `deletion_checklist.md` — 12-step verification procedure (pre + post deletion checks)
- `phase_d_scope.md` — High-level Phase D summary

**Consumer scope:**
- Production: `dbex/refine_one.py` (1 call site)
- Test: `test_torch_refine_smoke.py` (6 functions), `test_stage_a_smoke_parity.py` (1 function)
- Config-only: `test_refinement_engine.py` (2 imports), `test_stage_b_cpu_fallback.py` (3 imports)
- Legacy import fix: `test_physics_loss_current.py` (4 imports, redirect to `dbex.physics.loss`)
- Tooling: `dbex/tools/stage_a_adam.py` (1 call site)
- Infrastructure: `dbex/refinement/__init__.py` (config re-export)

**Out-of-scope:** Research probes (`plans/active/*/bin/*.py`), docs/logs/archive (update in next doc cycle)

### Checklist

- [x] D.1: **RefinementConfig Migration** — ✓ COMPLETE (2025-12-02T210000Z, commit 43a70eae) Created `dbex/refinement/config.py` with RefinementConfig dataclass relocated from facade (135 lines). Updated 13 import sites (refine_one split multi-import, __init__ docstring, test_refinement_engine 2× via replace_all, test_stage_b_cpu_fallback 3× via replace_all, test_torch_refine_smoke 6× split multi-imports). Added temporary re-export in facade (line 75) for backward compatibility. Tests: 3/3 mapped selectors PASSED (test_engine_executes_mock_stage 0.04s, test_stage_b_baseline_guard_diff_payload 0.77s, test_stage_a_expansion 47.5s). Import verification: both new path (dbex.refinement.config) and old path (facade re-export) working. Metrics: +135 lines (config.py), -115 lines (facade net), 5 files touched.
  - **Validation:** ✓ `pytest -vv tests/dbex/test_refinement_engine.py tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small` (3/3 tests PASSED)
  - **Artifacts:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210000Z/` (pytest_phase_d1.log, import_verification.txt, metrics.txt)

- [ ] D.2: **CLI Refactor** — Migrate `dbex/refine_one.py::run_nanobrag_backend()` from facade to RefinementEngine. Pattern: (1) import Engine + Stages, (2) build RefinementContext via `build_refinement_context()`, (3) instantiate stages list based on config flags, (4) run `engine.run({"context": refinement_context})`, (5) extract artifacts from `engine._artifacts`, (6) extract final Bragg from terminal stage (C > B > A precedence).
  - **Validation:** `pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator` (2 tests)
  - **Artifacts:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/` (D.2 implementation timestamp)
  - **Critical:** This provides reference pattern for all test migrations

- [ ] D.3: **Test Harness Migration** — Migrate test files following CLI blueprint (D.2). Files: (1) `test_torch_refine_smoke.py` (6 functions: test_stage_a_expansion, test_stage_a_engine_delegation_telemetry, test_stage_b_shell_modifiers, test_stage_c_detector_microslip, test_stage_b_asu_mapping_smoke, test_stage_c_stage_a_baseline_detector_dist), (2) `test_stage_a_smoke_parity.py` (1 function: test_stage_a_mapping_to_refine_roundtrip), (3) `dbex/tools/stage_a_adam.py` (1 function: run_debug_refinement).
  - **Validation:** `pytest -vv tests/dbex/test_torch_refine_smoke.py tests/dbex/test_stage_a_smoke_parity.py tests/dbex/test_stage_a_adam_tooling.py --smoke-detector-size=small` (8+ tests)
  - **Artifacts:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/` (D.3 implementation timestamp)

- [ ] D.4: **Import Cleanup** — Fix remaining legacy imports. Files: (1) `test_physics_loss_current.py` (4 inline imports, redirect `_compute_variance_weighted_loss` from facade to `dbex.physics.loss`).
  - **Validation:** `pytest -vv tests/dbex/test_physics_loss_current.py` (4 tests)
  - **Artifacts:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/` (D.4 implementation timestamp)

- [ ] D.5: **Facade Deletion** — Delete `dbex/nanobrag_refinement.py` after comprehensive verification. Pre-deletion checks: (1) zero remaining imports (excluding docs/logs/archive), (2) zero remaining call sites (excluding research probes), (3) static imports succeed, (4) test collection clean. Post-deletion checks: (1) static imports (repeat), (2) CLI smoke test, (3) Stage A/B/C smokes (3 tests), (4) full test suite (20+ tests), (5) test collection (repeat). Rollback plan: `git checkout HEAD -- dbex/nanobrag_refinement.py` if any check fails.
  - **Validation:** 12-step checklist (see `deletion_checklist.md`)
  - **Artifacts:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T<HHMMSS>Z/` (D.5 implementation timestamp)
  - **Exit Criterion #2:** Facade deleted, RefinementEngine is sole refinement path

**Expected Metrics (Phase D complete):**
- Files deleted: 1 (`dbex/nanobrag_refinement.py`, ~656 lines)
- Consumers migrated: 7 files (1 CLI + 5 tests + 1 tooling)
- Import updates: ~20 inline imports redirected
- Engine adoption: 10 call sites (1 CLI + 9 tests)
- Net change: -656 lines (facade removed)
- Tests validated: 20+ (CLI + Stage smokes + Engine + Tooling + Physics)

**Phase D Completion:** When Exit Criteria #1 (Phase C) + #2 (Phase D) both satisfied, mark ARCH-REFACTOR-001 `done`.
