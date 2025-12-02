# Implementation Plan: ARCH-STAGE-CONTEXT-001

## Initiative
- ID: ARCH-STAGE-CONTEXT-001
- Title: Stage Context + Engine Artifact Boundary
- Owner: Galph ↔ Ralph
- Spec Owner: docs/spec-db-workflow.md
- Status: in_progress

## Goals
- Introduce typed refinement context objects so Stage A/B/C stop passing 10–15 loosely-typed arguments per helper and so telemetry/mask state no longer mutates anonymous dictionaries.
- Move Stage classes away from “anemic wrapper” status by letting them own their LBFGS closures, cached state, and telemetry serialization rather than delegating their entire implementation to `*_impl.py` functions.
- Standardize the RefinementEngine artifact interface so stage outputs are exchanged via a typed envelope instead of ad-hoc shell-edge caches, and so downstream consumers (writer/tests) stop re-running optimization or poking internals.

## Phases Overview
- Phase A — Context Envelope: Codify shared refinement context + telemetry dataclasses and thread them through Stage A without behavior changes.
- Phase B — Stage Ownership & Telemetry: Collapse helper closures into Stage classes, tame mutable telemetry dicts, and provide explicit artifact objects per stage.
- Phase C — Engine Artifact Contract & Writer Decoupling: Teach RefinementEngine to traffic typed artifacts (Bragg frames, cache hints) and update `dbex/io/writer.py` to consume them instead of recomputing optimizations.

## Exit Criteria
1. Stage A/B/C helpers accept dataclasses (e.g., `RefinementSharedContext`, `StageAExecutionContext`) instead of free-form dicts, and their signatures shrink to ≤5 positional parameters with type hints.
2. Each Stage class owns its optimizer/telemetry life cycle (`StageA.run` no longer peels apart dicts from helper returns) and emits a typed artifact (`StageArtifacts`) that the engine stores without stage-specific branches.
3. `dbex/io/writer.py` no longer runs Nelder–Mead to back-compute scales; it consumes the stage artifacts/telemetry produced by the engine and confines itself to serialization.
4. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any new/renamed selectors; `pytest --collect-only` logs for documented selectors are saved under `plans/active/ARCH-STAGE-CONTEXT-001/reports/<timestamp>/`. Do not close the initiative if any selector marked "Active" collects 0 tests.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** docs/spec-db-workflow.md §7 — Refinement stages must execute through the engine contract, accepting ordered Stage objects and emitting canonical telemetry/artifacts.
- [ ] **Spec Constraint:** docs/spec-db-core.md §§57-68 — Variance-weighted loss semantics and telemetry (sigma_floor clamp, chi-squared definition) must remain intact while refactoring.
- [ ] **Fix-Plan Link:** docs/fix_plan.md — Row [ARCH-STAGE-CONTEXT-001].
- [ ] **Finding/Policy ID:** ARCH-ENGINE-002 (Stage wrappers must comply with the RefinementStage protocol).
- [ ] **Finding/Policy ID:** ARCH-STAGE-CTX-001 (Data clumps + mutable dict state around Stage contexts).

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md §5–§8.
- **Key Clauses:** Stage contract (ordered stages, caching semantics), Calibration/variance notes from docs/spec-db-core.md, runtime guardrails per docs/spec-db-runtime.md (device/dtype neutrality when capturing shared contexts).

## Architecture / Interfaces
- **Key Data Types / Protocols:**
  - `RefinementSharedContext`: immutable dataclass holding `crystal`, `beam`, `detector`, `RefinementInputs`, HKL tensors, `RefinementConfig`, device/dtype, sigma_floor cache, baseline references.
  - `StageRuntimeState[T]`: typed container for stage-specific caches (e.g., StageAContext, StageB ASU cache) plus telemetry accumulators.
  - `StageArtifacts`: typed records of each stage’s final Bragg tensor / modifiers / detector offsets with metadata so downstream code never scrapes private dicts.
- **Boundary Definitions:** `[Entry CLI/DataLoad] -> [RefinementSharedContext builder] -> [RefinementEngine::run(StageA..C)] -> [StageArtifacts + RefinementTelemetry] -> [HDF5 writer/tests]`.
- **Sequence Sketch:** CLI builds shared context → Engine iterates `for stage in stages` calling `stage.setup(shared_ctx)` + `stage.run()` → stage returns `(telemetry, artifacts)` → Engine caches artifacts keyed by stage name → writer consumes artifacts/telemetry without calling helper internals.
- **Data-Flow Notes:** Shared tensors (masks, HKL grid, sigma caches) move once into `RefinementSharedContext` on the target device/dtype; Stage runtime state references those tensors instead of cloning them. Artifacts carry either full `[panel, slow, fast]` tensors or structured JSON (e.g., StageB modifier tables) written under the standard `/torch_diagnostics` schema.

## Context Priming (read before edits)
- Primary docs/specs to re-read: docs/spec-db-workflow.md §5–§8, docs/spec-db-core.md §§20–80, docs/spec-db-runtime.md (device/dtype guardrails), docs/config_crosswalk.md (detector + crystal mapping), docs/data_dependency_manifest.md (Stage smoke fixtures + sigma/calibration provenance).
- Required findings/case law: ARCH-ENGINE-002 / ARCH-ENGINE-003 (engine protocol requirements), REFINE-FLOW-001 (Stage A/B baseline parity contract), ARCH-STAGE-CTX-001 (data clumps + mutable telemetry dicts).
- Related telemetry/attempts: plans/active/ARCH-REFINE-001/reports/2025-12-01T170500Z/ (latest stage helper extraction), plans/active/PERF-WARM-SIM-001/reports/* (StageAContext usage + warm-cache behavior), plans/active/ARCH-ENGINE-ARTIFACTS-001 (engine artifact backlog).
- Data dependencies to verify: Stage smokes (`tests/dbex/test_torch_refine_smoke.py` small/full datasets) per docs/data_dependency_manifest.md; Stage B/C rely on `DBEX_SMOKE_SIGMA_SOURCE=cli_override` and canonical calibrations, so context refactors must preserve the existing deterministic fixtures.

## Phase A — Context Envelope
### Checklist
- [ ] A0: **Callchain inventory:** Produce a short report enumerating every function that currently accepts (crystal, detector, beam, inputs, hkl_grid, hkl_metadata, config, sigma_floor_cache, device, dtype, baseline_crystal). Use `prompts/callchain.md` to capture the dictionary/parameter flow so migrations do not miss latent call sites.
- [x] A1: Add `dbex/refinement/context.py` with `RefinementSharedContext`, `StageTelemetryState`, and helper constructors that freeze device/dtype + reference counts. ✅ Completed 2025-12-02T010500Z — shared context builder + Stage A telemetry dataclasses landed; see `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T010500Z/`.
- [x] A2: Update `_build_stage_a_lbfgs_closure`, `_run_stage_a_lbfgs`, and `StageA.run` to consume the new dataclasses while keeping backward compatibility shims (dict inputs for external callers). ✅ Stage A expansion + guard tests executed under 2025-12-02T010500Z, telemetry now advertises `context_schema_version="v1"`.
- [ ] A3: Thread `RefinementSharedContext` through `_build_stage_b_lbfgs_closure` and `StageB.run`, collapsing the 11-parameter clump (config/device/dtype + crystal/detector/beam/inputs/hkl_grid/hkl_metadata/sigma_floor cache/panel geometry) into the dataclass while preserving the optional `context` hook for ASU metadata. Refresh Stage B smoketests (`test_stage_b_shell_modifiers`, `test_stage_b_per_reflection_smoke`) so both shell/per-reflection modes hit the new shim.
- [ ] A4: Apply the same pattern to Stage C detector retarget helpers, then update Stage A/B/C smoketests + `test_stage_a_engine_delegation_telemetry` expectations to assert that typed contexts propagate through the engine (context marker present in telemetry) before starting the Stage artifact work.

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** dbex/refinement/stage_a_impl.py, stage_b_impl.py, stage_c_impl.py, dbex/refinement/stage_a.py/b.py/c.py, dbex/refinement/engine.py, dbex/nanobrag_refinement.py (context construction), dbex/io/writer.py (telemetry expectations).
- **Circular Import Risks:** Introducing `dbex/refinement/context.py` must avoid importing stage modules; limit it to dataclasses + torch typing. Stage modules may import the context module, but the context module must not import stage implementations.
- **State Migration:** Move `telemetry_state` dicts into dataclasses with typed lists/counters. Shared context should hold the only reference to `RefinementInputs` / HKL tensors; stage runtime state references them rather than copying.

### Notes & Risks
- Breaking StageAContext warm cache semantics would immediately regress PERF-WARM-SIM-001; maintain device/dtype invariants and existing ROI caching flags.
- Engine/test harnesses currently expect plain dicts; provide compatibility adaptors until all call sites migrate.

## Phase B — Stage Ownership & Telemetry
### Checklist
- [ ] B1: Introduce `StageArtifacts` protocol + concrete implementations for Stage A (Bragg tensors), Stage B (modifier table), Stage C (detector offsets).
- [ ] B2: Move LBFGS closure construction into `StageA.run` (and StageB/StageC equivalents), eliminating `_build_*_lbfgs_closure` exports once tests pass.
- [ ] B3: Replace mutable telemetry dicts with dataclasses that expose typed appenders plus `.to_refinement_telemetry()` adapters, ensuring schema parity.
- [ ] B4: Update engine + writer to consume `StageArtifacts` and typed telemetry while keeping JSON schema stable.

### Notes & Risks
- LBFGS closures capture a large amount of lexical state; migrating them requires careful benchmarking to avoid retaining references that block garbage collection.
- Telemetry dataclasses must serialize to the same `/torch_diagnostics` layout to keep downstream comparison tooling intact.

## Phase C — Engine Artifact Contract & Writer Decoupling
### Checklist
- [ ] C1: Extend `RefinementEngine` to cache `StageArtifacts` generically, delete stage-specific caches (`_stage_b_shell_edges`, `_stage_c_bragg_full`), and expose a single `artifacts()` API.
- [ ] C2: Update `dbex/io/writer.py::write_torch_outputs` to consume engine artifacts (no Nelder–Mead); document any new CLI flags or telemetry fields introduced.
- [ ] C3: Refresh tests/fixtures (Stage B/C smokes, CLI integration tests) so they assert writer no longer triggers optimization and the artifact payloads match expectations.

### Notes & Risks
- Writer decoupling touches HDF5 schema; ensure `docs/spec-db-interfaces.md` remains accurate and update if new telemetry fields are added.
- Stages may need to persist artifact tensors on disk when they exceed practical in-memory reuse; plan for streaming/zero-copy options if necessary.

## Artifacts Index
- Reports root: `plans/active/ARCH-STAGE-CONTEXT-001/reports/`
- Latest run: `<timestamp>/`
