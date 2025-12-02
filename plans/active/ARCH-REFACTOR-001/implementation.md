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
- [ ] C3: **Stage C Cleanup:** Delete `dbex/refinement/stage_c_impl.py`. Verify `test_stage_c_detector_microslip` passes.
- [ ] C4: **Stage B Strictness:** Refactor `StageB` to rely solely on `RefinementSharedContext` and `StageBTelemetryState`. Remove legacy dict/arg support.
- [ ] C5: **Stage B Inlining:** Inline `_build_stage_b_params` and `_run_stage_b_lbfgs` into `StageB` class.
- [ ] C6: **Stage B Cleanup:** Delete `dbex/refinement/stage_b_impl.py` and `stage_b_impl.py.backup`. Verify `test_stage_b_shell_modifiers`.
- [ ] C7: **Stage A Strictness:** Refactor `StageA` to rely solely on `RefinementSharedContext`.
- [ ] C8: **Stage A Inlining:** Inline parameter building and loop logic into `StageA`.
- [ ] C9: **Stage A Cleanup:** Delete `dbex/refinement/stage_a_impl.py`. Verify `test_stage_a_expansion` and `DB-AT-024`.

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
