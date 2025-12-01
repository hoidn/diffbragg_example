# Implementation Plan — ARCH-REFINE-001

## Initiative
- ID: ARCH-REFINE-001
- Title: Dismantle `nanobrag_refinement.py` and finish engine modularization
- Owner: Codex
- Spec Owner: docs/spec-db-workflow.md
- Status: in_progress

## Goals
- Eliminate the inline monolith by moving Stage A/B/C logic into `dbex/refinement/stage_*.py` and running everything through `RefinementEngine`.
- Establish shared `RefinementContext`/`JobContext`, ensure forward-only simulator instantiation uses the unified factory, and keep Stage closures on direct Simulator construction so configuration, telemetry, and simulator state flow through well-defined APIs.

## Phases Overview
- Phase A — Stage Extraction: Relocate Stage A/B/C helpers into stage modules and wire engine-only execution.
- Phase B — Context + Factory: Introduce `RefinementContext`/`JobContext`, route forward-only simulator creation through the factory, and keep optimization closures on direct instantiation.
- Phase C — Telemetry + IO cleanup: Rationalize telemetry schema and centralize HDF5 writing/loss helpers.

## Exit Criteria
1. `run_nanobrag_refinement` instantiates `RefinementEngine` only (no inline closures) and Stage modules own their logic.
2. New `RefinementContext` (and `JobContext`) replace ad-hoc dict passing; forward-only simulator creation paths funnel through `create_unified_simulator` while Stage closures retain direct `Simulator` instantiation per ARCH-FACTORY-001.
3. `nanobrag_bridge` no longer hosts physics helpers; `compute_masked_mse_loss`, `simulate_forward_torch`, and related routines live in `dbex/physics/` or refinement helpers without circular dependencies.
4. HDF5 output for the torch backend is handled by a shared `io/writer.py` (or equivalent); the legacy diffBragg writer remains untouched but adapters/tests can consume both schemas.
5. Docs/spec/test collateral updated: relevant rows in `docs/fix_plan.md` and `docs/findings.md` reference the change, selectors in `docs/TESTING_GUIDE.md` remain valid with `pytest --collect-only` logs stored under `plans/active/ARCH-REFINE-001/reports/<timestamp>/`.

## Compliance Matrix
- [x] **Spec Constraint:** docs/spec-db-workflow.md §30‑41 (staging contract, telemetry flow)
- [x] **Spec Constraint:** docs/spec-db-core.md §32‑90 (sigma sourcing, variance floor, loss semantics)
- [x] **Fix-Plan Link:** docs/fix_plan.md entries covering TORCH-REFINE-002/003/004 and SCALE-005/008 obligations
- [x] **Finding/Policy ID:** POLICY-001 (Environment Freeze), CONFIG-ARCH-001 (engine must own stage orchestration)

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md, docs/spec-db-core.md
- **Key Clauses:** §33 (engine contract), §57‑68 (variance-weighted loss), §70‑75 (telemetry), §59 (HKL interpolation guardrails)

## Architecture / Interfaces
- **Key Data Types:**  
  `RefinementContext { inputs, detector, beam, crystal, hkl_grid, hkl_metadata, baseline_crystal, baseline_detector }`  
  `JobContext { args, DataLoad, calibration_metadata, refinement_config, sigma_info }`
- **Boundaries:** `[CLI refine_one] -> [JobContext] -> [RefinementEngine] -> [Stage modules] -> [physics/simulator] -> [IO writer]`.
- **Sequence:** CLI parses args → build `DataLoad` + `JobContext` → create `RefinementContext` → `RefinementEngine.run(refinement_inputs, context)` → per-stage LBFGS → telemetry dicts → writer emits HDF5 + diagnostics.
- **Data-Flow Notes:** `[DataLoad numpy tensors] -> RefinementInputs (numpy) -> torch tensors (device/dtype neutral) -> simulator outputs -> variance/loss stats -> telemetry/HDF5 artifacts`.
- **IDL Structure:** Every module touched by this plan must have an IDL contract under `docs/architecture/dbex/<module_path>/<module>.idl.md` (mirroring the implementation directory tree). Each IDL describes the public API (signature), direct + transitive dependencies, and behavior, and the corresponding code docstrings reference the IDL filename/section.

## Context Priming
- **Docs/specs to revisit:** docs/spec-db-workflow.md (§§30‑41, 57‑70), docs/spec-db-core.md (§§20‑90), docs/config_crosswalk.md, docs/fix_plan.md (TORCH-REFINE rows).
- **Findings/case law:** docs/findings.md entries for TORCH-REFINE-002D, TORCH-REFINE-004, PHYSICS-LOSS-001/002.
- **Related telemetry/attempts:** review `reports/`, `STAGE_A_SUCCESSFUL_ARTIFACTS.md`, prior engine delegation plans under ARCH-REFINE-FLOW-001.
- **Data dependencies:** HKL grids, sigma assets, calibration payloads referenced in docs/data_dependency_manifest.md; update manifest if new contexts add requirements.

## Phase A — Stage Extraction
- [x] A0: Baseline tests — run `pytest tests/dbex/test_refine_one_cli.py -k stage_a`, the Stage B/C smokes (`tests/dbex/test_torch_refine_smoke.py::{test_stage_b_shell_modifiers,test_stage_c_detector_microslip}`), DB-AT-024 mapping, and CLI telemetry selectors to capture pre-refactor behavior/logs.
- [x] A1: Move `_build_stage_a_params`, `_build_stage_a_lbfgs_closure`, `_run_stage_a_lbfgs`, and telemetry assembly into `refinement/stage_a.py`; expose minimal helper APIs.
- [x] A2: Repeat migration for Stage B helpers into `refinement/stage_b.py`.
- [x] A3: Repeat migration for Stage C helpers into `refinement/stage_c.py`.
- [x] A4: Remove inline execution branch from `run_nanobrag_refinement`; route through `RefinementEngine` exclusively and update callers/tests (including scripts like `run_stage_a_refinement.py` or any tooling that depended on the inline helpers).

### Dependency Analysis
- **Touched Modules:** `dbex/nanobrag_refinement.py`, `dbex/refinement/stage_a.py`, `stage_b.py`, `stage_c.py`, `dbex/refinement/engine.py`, CLI/tests referencing `run_nanobrag_refinement`.
- **Circular Import Risks:** Break dependencies by moving shared utilities (telemetry structs, contexts) into neutral modules (`refinement/context.py`, `refinement/stage.py`). Stage modules must stop importing the monolith.
- **State Migration:** Replace `stage_a_ctx` dict hand-offs with structured context objects to carry cached simulators, ROI data, and telemetry.

### Notes & Risks
- Risk: moving helpers may expose hidden device/dtype assumptions; mitigate with incremental commits and regression tests after each stage migration.
- Risk: engine-only path may surface previously masked differences (e.g., CPU fallback); document and gate with feature flags if needed.

# Note on Simulator Factory Scope
The `create_unified_simulator` factory remains confined to forward-only paths
(CLI zero-iteration, bridge helpers, warm-cache/context initialization). Stage
closures (A/B/C) MUST continue constructing or reusing `nanobrag_torch.Simulator`
instances directly so their leaf tensors stay attached to the autograd graph
(ARCH-FACTORY-001). Any new context builders should pass pre-built detector/crystal
objects into the closures rather than re-instantiating them via the factory.

## Phase B — Context + Factory
### Checklist
- [x] B1: Add `refinement/context.py` defining `RefinementContext` and related builders; update stage signatures to accept context instead of loose dicts.
- [x] B2: Introduce `JobContext` that encapsulates CLI args, `DataLoad`, calibration metadata, sigma provenance, HKL grid metadata (halo flag, ASU map), and `RefinementConfig`; adjust `refine_one` to pass it downstream.
- [x] B3: Move HKL grid construction, halo padding, and ASU mapping out of stage helpers into the context builder so Stage A/B/C share the same experiment geometry (no stage-local recomputation). Document the context IDL under `docs/architecture/dbex/refinement/context.idl.md`.
- [x] B4: Use `refinement/helpers.create_unified_simulator` for forward-only paths (CLI, bridge helpers, warm-cache builders) while keeping Stage A/B/C closures on direct `Simulator` construction to preserve autograd (ARCH-FACTORY-001).
- [x] B5: Update tests/fixtures to construct the new contexts; capture device-switch behavior (Stage B CPU fallback) in unit tests.

### Notes & Risks
- Risk: context refactor may require significant fixture rewrites; plan for phased updates to test harnesses.
- Risk: enforcing a single simulator factory could expose calibration edge cases; add validation logs and fallbacks in factory.
- Risk: HKL halo/ASU mapping must remain validated against cctbx/canonical fixtures; add parity tests to ensure moving the logic out of Stage B doesn’t change Stage A outputs.

## Phase C — Telemetry + IO Cleanup
 - [x] C1: Collapse duplicate `RefinementTelemetry` definitions into `refinement/stage.py`; ensure serialization remains backward compatible and stage-specific fields are scoped.
 - [x] C2: Move `compute_masked_mse_loss`, `simulate_forward_torch`, and related physics helpers out of `nanobrag_bridge` into purpose-built modules under `dbex/physics/` (e.g., `loss.py`, `forward.py`) so RefinementContext/Stage code can consume them without circular imports; adjust docs/tests accordingly.
 - [x] C3: Extract a torch-specific HDF5 writer into `dbex/io/writer.py` (or similar) and migrate the nanobrag backend (`refine_one`, torch tests) to use it; leave the legacy diffBragg writer untouched (add adapters/tests if needed for comparison tooling).
 - [x] C4: Update docs/fix_plan.md and docs/findings.md to document the architectural change; rerun CLI end-to-end test, store telemetry/output snapshots under `plans/active/ARCH-REFINE-001/reports/<timestamp>/`.
 - [x] C5: Regenerate `docs/TESTING_GUIDE.md` selectors or logs if test coverage shifts.

### Notes & Risks
- Risk: HDF5 schema unification might break downstream visualization; coordinate with `vis/*.py` maintainers and provide migration notes if attribute paths move.
- Risk: Telemetry restructuring may require updates to analytic scripts; audit `reports/` consumers.

## Phase D — Architecture Documentation Sync
- [x] D1: Update `docs/architecture/live_backend.md` (Entrypoints/Modes, Migration and Status, Implementation Interfaces) to describe the engine-only path, `RefinementContext`/`JobContext`, and the torch writer seam. Reference specific sections in the commit summary (e.g., §§6‑33).
- [x] D2: Retire stale `use_engine_delegation` references in Stage A tooling/docs so probes and selectors clearly describe RefinementEngine as the only execution path (updates to `docs/architecture/data_telemetry_flow.md`, Stage A Adam tooling, TOOLING-VIS-001 drivers, Testing Guide/Test Suite Index).
- [x] D3: Refresh `docs/architecture/module_map.md` with entries for `refinement/context.py`, `JobContext`, and `dbex/io/writer.py`, marking `dbex/nanobrag_refinement.py` as a legacy shim and `refinement/engine.py` as the active path.
- [x] D4: Create/update IDL files under `docs/architecture/dbex/...` mirroring the implementation tree (e.g., `docs/architecture/dbex/refinement/context.idl.md`, `docs/architecture/dbex/io/writer.idl.md`), covering signature/dependencies/behavior and cross-referencing them from implementation docstrings.
- [x] D5: Capture the documentation diffs in `plans/active/ARCH-REFINE-001/reports/<timestamp>/architecture_doc_update.md` and link the report from `docs/fix_plan.md`.

## Phase E — Stage B Baseline Parity (REFINE-FLOW-001)
- [x] E1: Instrument Stage B baseline evaluation to log Stage A canonical chi-squared, Stage B initial chi-squared, and per-panel deltas so we can reproduce the 9% offset reported in REFINE-FLOW-001. Dump the comparison into the current report directory and thread the canonical value through param_values for subsequent guards.
- [x] E2: Fix Stage B baseline reconstruction so `_run_stage_b_lbfgs` reuses the exact Stage A telemetry snapshot (scale, cell, misset, warm-cache sims). Once aligned, add a tolerance check (≤0.1% relative) that raises a targeted RuntimeError when the guard fails, citing REFINE-FLOW-001.
- [x] E3: Finalize Stage B baseline guard harness — factor the REFINE-FLOW-001 parity check/diff writer out of `_run_stage_b_lbfgs` so it can be unit-tested without constructing an optimizer, update `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload` to exercise the helper (JSON schema + RuntimeError) and keep the Stage B/C small-detector selectors asserting `stage_b_baseline_rel_diff ≤ 1e-6` with telemetry artifacts.

### Notes & Risks
- Risk: Stage B ROI sampling vs panel validations may mask baseline mismatches; always force panel-mode evaluation during the parity check (per PERF-WARM-009).
- Risk: Floating-point drift across device/dtype conversions (CPU fallback) can look like baseline mismatch; log per-panel stats to disambiguate true reconstruction bugs from tolerable noise.

### Notes & Risks
- Risk: Missing a doc section can leave downstream teams referencing outdated flows—track each edit against the sections listed above.
- Risk: Some architecture docs are labeled “current implementation”; clarify when a section is describing the new target vs the frozen diffBragg baseline.

## Artifacts Index
- Reports root: `plans/active/ARCH-REFINE-001/reports/`
- Latest run: `plans/active/ARCH-REFINE-001/reports/<YYYY-MM-DDTHHMMSSZ>/`
