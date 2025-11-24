# Implementation Plan: ARCH-REFACTOR-001

## Initiative
- ID: ARCH-REFACTOR-001
- Title: Refinement Engine Modularization & Physics Separation
- Owner: Unassigned
- Spec Owner: docs/spec-db-workflow.md
- Status: pending (Blocked by [TORCH-GEOMETRY-CONVERGENCE-001])

## Goals
1. **Decouple Physics:** Move pure crystallographic math/physics out of orchestration code to enable isolated unit testing.
2. **Standardize Telemetry:** Replace brittle string-mapping with data-driven schema handling.
3. **Incremental Architecture:** Evolve `run_nanobrag_refinement` into a class-based Engine without a big-bang rewrite, preserving regression guards at every step.
4. **Harden Tooling & Legacy Paths:** Remove repo-polluting scratch artifacts (`dbex/run_diffbragg.py`) and de-tangle plan tooling/summary scripts so they can be reused and tested.

## Execution Constraints & Timing
> **CRITICAL:** This initiative is **blocked** until `TORCH-GEOMETRY-CONVERGENCE-001` (Phase C) is complete and the Chi² convergence bug is resolved.
> 
> **Rule:** Do not move broken code. Fix the physics first, then refactor.
> 
> **Layered-Scope Discipline:** Per prompts/supervisor.md, "When higher-layer work exposes lower-layer defect, suspend higher layer and stabilize lower layer first." Refactoring is Tier 3 (Architecture). Convergence is Tier 1 (Core Physics). Fix convergence first.

## Phases Overview
- Phase 0 — Test Discipline Baseline: Prove team can write unit tests in CURRENT architecture before moving code.
- Phase A — Physics Extraction: Isolate math kernels (`dbex.geometry`, `dbex.physics`) to secure "leaf nodes".
- Phase B — Telemetry Standardization: Modernize `RefinementTelemetry` and HDF5 I/O.
- Phase C — Incremental Engine Migration: Introduce `SimulationContext` and `RefinementStage` patterns gradually, keeping existing facade alive.
  - Prerequisite: TORCH-API-ALIGN-001 Phase B completed (unified simulator factory + ExperimentModel adapter in parity-first mode). Stages should consume the unified factory seam; mid-term we may route the factory via ExperimentModel or vice versa to avoid two public paths.
- Phase D — Legacy Hygiene & Tooling: Fix DiffBragg scratch semantics and refactor brittle orchestration scripts into importable modules/CLIs.

## Exit Criteria
1. Core physics functions (`derive_u_matrix`, `compute_variance_weighted_loss`) are isolated in `dbex.geometry`/`dbex.physics` and unit-tested independently.
2. `RefinementTelemetry` supports `to_dict()` and dynamic HDF5 serialization.
3. `run_nanobrag_refinement` facade delegates to `RefinementEngine`.
4. **Regression Guards:** `test_stage_a_expansion` and `DB-AT-024` (Mapping) pass at every commit.
5. **Parity:** `test_db_at_001_parity.py` confirms no numeric drift > 1e-6 during migration.
6. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any new selectors; `pytest --collect-only` logs saved under `plans/active/ARCH-REFACTOR-001/reports/<timestamp>/`.
7. DiffBragg backend writes all intermediate artifacts into per-run temp directories or explicit paths (no `_geom_ref.*`/`_temp.mtz`/`_geom.out` leakage in repo root) and concurrency-safe tests cover the behavior.
8. Stage-A tooling/summary generation scripts expose CLI arguments instead of hard-coded constants, rely on shared helper modules, and ship basic regression/unit tests.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** `docs/spec-db-workflow.md §7` — Engine Contract: API must accept an ordered list of Stage objects.
- [ ] **Spec Constraint:** `docs/spec-db-core.md` — Variance Definition: `V = I_model + sigma^2` (detached) logic must be preserved in `dbex.physics`.
- [ ] **Spec Constraint:** `docs/spec-db-runtime.md` — Device neutrality: New classes must accept device/dtype configuration.
- [ ] **Fix-Plan Link:** `docs/fix_plan.md — Row [ARCH-REFACTOR-001]`
- [ ] **Fix-Plan Link (dependency):** `plans/active/TORCH-API-ALIGN-001` — Simulator wiring unification + ExperimentModel adapter
- [ ] **Finding/Policy ID:** `PERF-WARM-SIM-001` — Warm cache behavior must be preserved in the new `SimulationContext`.
- [ ] **Finding/Policy ID:** `REFINE-001` — LBFGS scale warm-start patterns must transfer to new architecture.
- [ ] **Policy:** Layered-Scope Guard — Do not refactor higher layers while lower layers (physics) are unstable.

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md
- **Key Clauses:** §7 (Refinement Protocol Architecture), §6 (Variance-weighted loss)

## Architecture / Interfaces
- **New Modules:**
  - `dbex/geometry/crystallography.py` (Pure functions: U-matrix derivation, cell recovery)
  - `dbex/geometry/rotations.py` (Pure functions: quaternion, matrix operations)
  - `dbex/physics/loss.py` (Pure functions: variance-weighted loss, masked MSE)
  - `dbex/engine/` (State management: RefinementEngine, RefinementStage, SimulationContext)
- **Key Types:**
  - `SimulationContext`: Holds `Detector`, `Crystal`, `Simulator`, `Masks` (on-device), ROI caching
  - `RefinementStage` (ABC): `setup()`, `step()`, `teardown()`
  - `RefinementEngine`: Orchestrates stages, aggregates telemetry
- **Boundary Definitions:**
  - `[CLI/DataLoad]` -> `[RefinementEngine]` -> `[RefinementStage]` -> `[SimulationContext/Simulator]`
- **Leaf-Node Constraint:**
  - "Leaf-like" means: `dbex.geometry` may import from `dxtbx`/`cctbx` (external deps) but MUST NOT import from `dbex.nanobrag_bridge` or `dbex.nanobrag_refinement` (internal deps that use geometry). This prevents circular imports.

## Context Priming
- Primary docs: `docs/spec-db-workflow.md` §6-§7, `docs/spec-db-core.md`, `docs/spec-db-runtime.md`
- Related code: `dbex/nanobrag_refinement.py` (current monolithic), `dbex/nanobrag_bridge.py` (math mix-in)
- Reference implementation: `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/` (telemetry patterns from successful diagnostic campaign)
- Findings: `REFINE-001` (LBFGS scale), `PHYSICS-LOSS-001` (variance), `PERF-WARM-SIM-001` (cache), `GRADIENT-001` (autograd)

## Phase 0 — Test Discipline Baseline
**Goal:** Prove test-writing discipline exists BEFORE refactoring. Tests in current architecture provide safety net.

### Checklist
- [ ] 0.1: **Unit test derive_u_matrix (CURRENT location)** — Write `tests/dbex/test_geometry_current.py::test_derive_u_matrix_roundtrip` validating MOSFLM A* → (U, B_ideal) → A* reconstruction within 1e-6. Test CURRENT implementation in `dbex/nanobrag_bridge.py` before moving.
- [ ] 0.2: **Unit test variance_weighted_loss (CURRENT location)** — Write `tests/dbex/test_physics_loss_current.py::test_variance_weighted_loss_sigma_floor` validating sigma_floor clamping per `PHYSICS-LOSS-001`. Test CURRENT implementation before moving.
- [ ] 0.3: **Achieve 80% coverage of core math** — Run `pytest --cov=dbex.nanobrag_bridge --cov-report=term tests/dbex/test_geometry_current.py tests/dbex/test_physics_loss_current.py`; ensure key functions (derive_u_matrix, matrix_to_quaternion, compute_masked_mse_loss, _compute_variance_weighted_loss) have ≥80% line coverage.
- [ ] 0.4: **Regression guard** — Run `test_stage_a_expansion` and `DB-AT-024` to establish baseline before ANY refactoring.

### Notes & Risks
- **Purpose:** Validates team CAN write tests. If tests never materialize, refactoring is pointless (same discipline problem persists).
- **Safety net:** Tests written against CURRENT code become parity validators during migration (run old tests against new modules).
- **Gate:** Phase 0 must complete with ≥80% coverage BEFORE proceeding to Phase A.

## Phase A — Physics Extraction
**Goal:** Clean up `nanobrag_bridge.py` and enable unit testing of math in isolated modules.

### Checklist
- [ ] A1: **Create `dbex/geometry/crystallography.py`** — Move `derive_u_matrix_from_mosflm_a_star`, `recover_cell_from_a_star`, `compute_baseline_misset` to new module. Update imports in `nanobrag_bridge.py` to import from `dbex.geometry.crystallography`.
  - **Risk mitigation:** Ensure no imports from `nanobrag_bridge` or `nanobrag_refinement` (maintain leaf-node property).
  - **Validation:** Re-run Phase 0 tests (`test_geometry_current.py`) against NEW location; ensure 100% pass rate.
- [ ] A2: **Create `dbex/geometry/rotations.py`** — Move `matrix_to_quaternion`, `quaternion_to_matrix`, `quaternion_multiply` to new module.
  - **Validation:** Run quaternion roundtrip tests from `TORCH-GEOMETRY-PARITY-002`.
- [ ] A3: **Create `dbex/physics/loss.py`** — Move `compute_masked_mse_loss`, `_compute_variance_weighted_loss` to new module.
  - **Preserve spec compliance:** Ensure `V = I_model + sigma^2` detachment per `spec-db-core.md`.
  - **Validation:** Re-run Phase 0 loss tests against NEW location.
- [ ] A4: **Refactor `nanobrag_bridge.py` to import from new modules** — Update all call sites. Delete moved functions from `nanobrag_bridge.py`.
  - **Validation:** Run `test_stage_a_expansion` (full regression guard).
  - **Coverage check:** Re-run coverage on NEW modules; ensure ≥80% maintained.

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
- [ ] B1: **Convert `RefinementTelemetry` to dataclass** — Add `@dataclass` decorator, implement `to_dict()` method handling nested numpy/torch types.
  - **Schema versioning:** Add `telemetry_version: str = "1.0"` field for future compatibility.
- [ ] B2: **Refactor `_write_torch_outputs` in `refine_one.py`** — Replace manual field mapping with dynamic iteration over `telemetry.to_dict().items()`.
  - **HDF5 compatibility:** Handle nested dicts, arrays, scalars per `spec-db-interfaces.md`.
- [ ] B3: **Verify HDF5 output structure** — Run `test_stage_a_expansion`, inspect output HDF5 files, confirm structure matches spec.
  - **Backward compatibility:** Ensure existing analysis scripts can read new format.

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
- [ ] D1: **DiffBragg scratch isolation** — Create utilities under `dbex/diffbragg_tmp.py` (or similar) that allocate per-run temporary directories (using `tempfile.TemporaryDirectory` or user-provided `--out-dir`) and ensure `_geom_ref.*`, `_temp.mtz`, `_geom.out/` live under that scope.
  - **Validation:** Update `run_diffbragg_backend` tests (or add `tests/dbex/test_diffbragg_tmp.py`) that spawn two runs simultaneously via `multiprocessing` and confirm artifacts stay in unique directories and are cleaned afterwards.
  - **Docs:** Update `README.md` / `docs/spec-db-workflow.md` CLI sections describing new flags/environment variables.
- [ ] D2: **Stage A debug tooling modularization** — Extract reusable utilities from `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` into `dbex/tools/stage_a_adam.py`. The CLI script becomes a thin shim that only parses args and calls library functions; drop direct `sys.path` hacking.
  - **Validation:** Add unit/integration tests (`tests/dbex/test_stage_a_adam_tooling.py`) that import the new module and exercise zero-point + block-DoF flows without invoking the CLI.
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
