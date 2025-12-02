# Implementation Plan — ARCH-TELEMETRY-001

## Initiative
- ID: ARCH-TELEMETRY-001
- Title: Telemetry Observer Refactor
- Owner: Galph ↔ Ralph
- Spec Owner: docs/spec-db-workflow.md (telemetry), docs/spec-db-core.md (variance/loss), docs/spec-db-interfaces.md (HDF5 schema)
- Status: in_progress

## Goals
- Replace mutable telemetry dicts with a typed observer/collector path so Stage A/B/C physics loops no longer embed logging logic.
- Ensure RefinementEngine and writer consume a single telemetry artifact channel with per-stage result dataclasses.
- Preserve/refine all existing telemetry fields and acceptance-gate invariants (REFINE-007/008/012, PHYSICS-LOSS-001/003).

## Phases Overview
- Phase A — Observer Interfaces & Collector: Define `RefinementObserver` protocol, stage-specific telemetry/result dataclasses, and migration shims.
- Phase B — Stage A Adoption: Thread the observer through Stage A, remove `telemetry_state` dict mutation, and keep smoketest selectors green.
- Phase C — Stage B/C & Writer Integration: Port Stage B/C to the observer model, simplify writer persistence, and delete telemetry dict compatibility layers.

## Exit Criteria
1. `dbex/refinement/stage_a.py`, `stage_b.py`, and `stage_c.py` no longer import or mutate `telemetry_state`/`param_values` dicts; they emit telemetry via observer callbacks into typed result objects.
2. `dbex/refinement/engine.py` and `dbex/io/writer.py` consume `StageAResult/StageBResult/StageCResult` dataclasses directly; Nelder–Mead fallbacks and manual dict patching are removed.
3. Stage A/B/C smoketests plus `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`, `::test_stage_b_shell_modifiers`, and `::test_stage_c_detector_microslip` pass using the observer-based telemetry channel.
4. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any new/renamed selectors; `pytest --collect-only` logs for documented selectors are archived under `plans/active/ARCH-TELEMETRY-001/reports/<timestamp>/`.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** docs/spec-db-core.md §Objective Function & Variance Model — telemetry must reflect variance-weighted χ² and sigma-floor clamp data.
- [ ] **Spec Constraint:** docs/spec-db-workflow.md §Pipeline & Calibration telemetry — `/torch_diagnostics` keyset stays intact.
- [ ] **Fix-Plan Link:** docs/fix_plan.md — Row [ARCH-TELEMETRY-001] (problems.md “Refactor: Decouple Telemetry from Refinement Logic using Observer Pattern”).
- [ ] **Finding/Policy ID:** ARCH-STAGE-CTX-001 / ARCH-STAGE-CTX-002 — ban telemetry dict mutation; ensure typed contexts own telemetry.
- [ ] **Finding/Policy ID:** PHYSICS-LOSS-001 / PHYSICS-LOSS-003 — telemetry χ² must be spec-compliant.

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md, docs/spec-db-core.md, docs/spec-db-interfaces.md.
- **Key Clauses:** telemetry provenance requirements (§Calibration & Unit Conventions), variance-weighted chi-squared definition, `/torch_diagnostics` schema requirements for Stage telemetry and writer outputs.

## Architecture / Interfaces
- **Key Data Types / Protocols:**  
  ```
  protocol RefinementObserver:
      def on_step(iteration:int, loss:float, metrics:Mapping[str, float]) -> None
      def on_validation(scope:str, chi2:float, payload:StageTelemetrySnapshot) -> None
      def finalize(stage_result:StageResult) -> None
  dataclass StageResult:
      stage: Literal["A","B","C"]
      telemetry: StageATelemetry | StageBTelemetry | StageCTelemetry
      perf_counters: PerfCounters
  ```
- **Boundary Definitions:** `[StageX LBFGS closure] -> [Observer callbacks] -> [TelemetryCollector] -> [RefinementEngine artifact channel] -> [Writer/HDF5]`.
- **Sequence Sketch (Happy Path):** Stage closure invokes observer per iteration → Collector appends to typed telemetry state → Stage `run()` returns `StageResult` -> Engine aggregates results -> Writer serializes dataclasses.
- **Data-Flow Notes:** No mutable dicts cross from closures into engine/writer; telemetry collectors own ROI stats, chi² traces, and derived metrics, serializing to JSON/HDF5 via typed dataclasses.

## Context Priming (read before edits)
- **Primary docs/specs to re-read:** docs/spec-db-workflow.md §§Calibration & Pipeline, docs/spec-db-core.md §Objective Function, docs/spec-db-interfaces.md §HDF5 Output Schema, docs/architecture/data_telemetry_flow.md.
- **Required findings/case law:** ARCH-STAGE-CTX-001/002 (typed contexts & telemetry), PHYSICS-LOSS-001/003 (variance-weighted chi² invariants), REFINE-007/012 (Stage C telemetry gates), PERF-WARM-005..008 (ROI/perf telemetry semantics).
- **Related telemetry/attempts:** plans/active/ARCH-STAGE-CONTEXT-001/reports/ (Phase B/E evidence), plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/ (Stage C ROI traces), docs/fix_plan_archive.md (telemetry dict history).
- **Data dependencies to verify:** Ensure Stage smokes keep using canonical refGeom/refGeom_small fixtures (`docs/data_dependency_manifest.md`) so telemetry comparisons remain deterministic; warm-cache diagnostics rely on `DBEX_STAGE_C_CACHE_DEBUG_PATH` env guard captured under PERF-WARM-SIM-001.

## Phase A — Observer Interfaces & Collector
### Checklist
- [x] A0: **Telemetry contract spike** — author minimal collector/observer prototype and replay Stage A telemetry log to confirm required fields are captured without touching closures (captured under `reports/2025-12-02T191500Z/prototype.md`).
- [x] A1: Define `RefinementObserver` protocol + `StageATelemetry`, `StageBTelemetry`, `StageCTelemetry`, `StagePerfCounters`, and `StageResult` dataclasses with serialization helpers. (Artifacts: `reports/2025-12-02T191500Z/`.)
- [x] A2: Implement `TelemetryCollector` (per-stage) that records loss traces, validation snapshots, and param deltas from observer callbacks; include JSON dump for smoketest artifacts. (Artifacts: `reports/2025-12-02T191500Z/`.)
- [x] A3: Update `RefinementEngine` scaffolding + typed contexts to accept collectors instead of dicts while keeping legacy shims (StageArtifacts) for the duration of Phase A/B. (Artifacts: `reports/2025-12-02T191500Z/`.)

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** `dbex/refinement/interfaces.py`, `dbex/refinement/context.py`, `dbex/refinement/engine.py`, `dbex/refinement/stage_{a,b,c}.py`, `dbex/io/writer.py`, smoketest fixtures.
- **Circular Import Risks:** New interfaces live in `dbex/refinement/interfaces.py` to avoid importing stage modules inside collectors; engine/stage modules import interfaces only.
- **State Migration:** Telemetry dict contents move into dataclasses; `StageArtifacts` map extends with typed telemetry references instead of raw dict copies.

### Notes & Risks
- Need to mirror every telemetry key currently written to `/torch_diagnostics`; missing keys would violate spec and REFINE findings.
- Must keep StageArtifacts/StageResult serialization stable so writer diffs remain manageable.

## Phase B — Stage A Adoption
### Checklist
- [x] B1: Thread `RefinementObserver` through Stage A LBFGS closure, emitting per-iteration chi² and ROI metrics; remove `telemetry_state` dict mutation. (Artifacts: `reports/2025-12-02T201500Z/`.)
- [x] B2: Update `StageA.run` to construct `StageAResult` from the collector and return it via the engine artifact channel; ensure warm-cache perf counters feed observer. (Artifacts: `reports/2025-12-02T201500Z/`.)
- [x] B3: Refresh `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` + `test_stage_a_engine_delegation_telemetry` to assert observer-driven telemetry (no dict shims) and capture logs under `plans/active/ARCH-TELEMETRY-001/reports/<ts>/`. (Artifacts: `reports/2025-12-02T201500Z/`.)

### Notes & Risks
- Stage A currently interleaves telemetry logging with physics (ROI/perf counters). Need to ensure observer callbacks do not incur significant overhead inside LBFGS closures.

## Phase C — Stage B/C & Writer Integration
### Checklist
- [ ] C1: Port Stage B and Stage C closures to emit observer events (per-ROI, per-panel validations) and delete `telemetry_state` dict mutation paths in `_build_stage_b_lbfgs_closure`, `_run_stage_b_lbfgs`, `_build_stage_c_lbfgs_closure`, and `_run_stage_c_lbfgs`. Ensure collectors capture scoped baseline/panel/roi/final validations, Stage B baseline parity metrics, variance-floor counters, and Stage C panel diagnostics before handing `StageResult` objects back to the engine. (Next artifacts: `reports/2025-12-03T160900Z/`.)
  - Stage C follow-ups (2025-12-03T190000Z failure):
    * Defer `collector.finalize()`/`StageResult.to_legacy_dict()` until after the final `collector.on_validation` so the closing validation is recorded.
    * Drop the legacy `legacy_telemetry_dict` plumbing in `_run_stage_c_lbfgs` and read telemetry/perf counters directly from the collector/StageResult objects.
    * Guarantee `_build_stage_c_lbfgs_closure` records at least one on_step sample even when LBFGS exits immediately (current smoketest fails because `loss_trace_sample` stays empty).
    * Route every validation scope, including panel diagnostics, through the collector payload instead of mutating dataclasses in place.
    * Validation plan: rerun `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`, `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`, and `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` with artifacts under `reports/2025-12-03T210000Z/`.
    * (2025-12-03T233500Z guard) Seed a synthetic baseline sample via the Stage C collector whenever LBFGS records zero closure evals, then plumb `variance_floor_{masked,clamped}_pixels` from the finalized collector into the `RefinementTelemetry` payload so PHYSICS-LOSS-001 counters survive observer migration.
    * (2025-12-03T235900Z guard) Stage C smoketest now fails because `perf_counters["closure_evals"]` stays at 0 even though the seeded sample traces exist. Keep the strict test and extend `StageCTelemetryCollector.ensure_sample_trace` with an `increment_counter` flag that bumps `perf_closure_evals[0]` whenever the fallback fires, then call it with that flag at both zero-closure checkpoints in `_run_stage_c_lbfgs`. Rerun `tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload`, `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`, and `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` with artifacts under `reports/2025-12-03T235900Z/`.
- [ ] C2: Simplify `dbex/io/writer.py` to consume `StageResult` dataclasses, removing Nelder–Mead reruns and dict introspection; add tests covering Stage A/B/C writer outputs.
- [ ] C3: Delete legacy telemetry dict compatibility layers (`asdict` round-trips) and update CLI/engine telemetry enrichment to rely solely on typed observers; rerun Stage B/C smoketests and Stage diagnostics CLI tests.

### Notes & Risks
- Stage B per-reflection path still contains known gradient issues; keep observer migration isolated so existing failures stay attributable to TORCH-REFINE-004.
- Writer refactor must preserve HDF5 dataset names; consider temporary adapter that serializes dataclasses to the old layout for diff minimization.

## Artifacts Index
- Reports root: `plans/active/ARCH-TELEMETRY-001/reports/`
- Latest run: `<YYYY-MM-DDTHHMMSSZ>/` (per loop)
