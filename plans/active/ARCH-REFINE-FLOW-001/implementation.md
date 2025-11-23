# ARCH-REFINE-FLOW-001 — Protocol-Based Refinement Engine

## Initiative
- ID: ARCH-REFINE-FLOW-001
- Title: Refactor to Protocol-based Refinement Engine
- Owner: Unassigned
- Spec Owner: docs/spec-db-workflow.md §7 (Refinement Protocol Architecture)
- Status: pending

## Goals
- Replace the monolithic `run_nanobrag_refinement` function with an extensible `RefinementEngine` that executes an ordered list of Stage objects (A, B, C).
- Make each Stage self-contained (parameters, closures, telemetry contract) so future modes (e.g., Stage B per-reflection parity) can be plugged in without rewriting the entire loop.
- Preserve existing Stage smoke + DB-AT selectors while providing hooks for alternative Stage implementations and telemetry provenance.
- Treat the stabilized Stage A implementation (variance-weighted loss, sigma_floor handling, warm-cache/perf counters, mapping-aligned zero point) as the canonical pattern for concrete Stage implementations, while keeping the engine API itself agnostic to Stage-specific physics.

## Phases Overview
- Phase A — Stage Interface & Engine Skeleton: define the data/telemetry contract and minimal engine loop.
- Phase B — Stage A Extraction: migrate Stage A implementation onto the engine.
- Phase C — Stage B Extraction: port shell-modifier logic into a Stage object and preserve gates.
- Phase D — Stage C Extraction: port detector-distance refinement and telemetry.
- Phase E — Orchestration Hooks & Mode Wiring: expose stage registry/config toggles and document how future Stage variants (per-reflection) attach.

## Exit Criteria
1. `dbex/refinement/engine.py` (or equivalent) exposes a `RefinementEngine` class that accepts an ordered list of `RefinementStage` instances and executes them sequentially with deterministic telemetry.
2. Stage A/B/C implementations live in dedicated Stage classes, and `run_nanobrag_refinement` simply assembles the standard protocol (A→B→C) plus configuration knobs (enable/disable stages, stage mode).
3. Stage smoke selectors (`tests/dbex/test_torch_refine_smoke.py::{test_stage_a_expansion,test_stage_b_shell_modifiers,test_stage_c_detector_microslip}`) and DB-AT selectors continue to pass unchanged on both small and full detectors; artifacts recorded for each migration phase.
4. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any new/changed tests; `pytest --collect-only` logs for documented selectors are saved under `plans/active/ARCH-REFINE-FLOW-001/reports/<timestamp>/`. Do not close the initiative if any selector marked "Active" collects 0 tests.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** docs/spec-db-workflow.md §7 — “Refinement Protocol Architecture”
- [ ] **Fix-Plan Link:** docs/fix_plan.md — `[ARCH-REFINE-FLOW-001]`
- [ ] **Finding/Policy ID:** REFINE-005 (Stage B halo/interpolation), REFINE-007/008 (Stage C/B telemetry gates), POLICY-001 (Environment Freeze), CONFIG-001 (Detector metadata contracts)

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md
- **Key Clauses:** §6 (Variance-weighted loss), §7 (Engine Contract & Stage definitions), Stage smoke dataset policy (detector split), Stage B physics (tricubic interpolation), Stage C detector offsets.

## Context Priming (read before edits)
- docs/spec-db-workflow.md §6–§7 (loss + staging)
- docs/spec-db-tracing.md §2 (telemetry requirements)
- docs/fix_plan.md entries for TORCH-REFINE-004/005 (Stage B roadmap) and PHYSICS-LOSS-001 (variance-weighted loss)
- logs/artifacts under plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/ (canonical Stage telemetry)
- plans/active/PERF-WARM-SIM-001/implementation.md (Stage A warm-cache, ROI sampling, and perf-telemetry contract)
- findings REFINE-005, REFINE-007, REFINE-008 (gates), SCALE-001/002 (scale handling)

## Phase A — Stage Interface & Engine Skeleton
**Status:** COMPLETE (2025-11-23T024449Z)
**Artifacts:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/

- [x] A0: **TDD nucleus** — author a minimal unit test (`tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage`) validating that a dummy Stage object runs and emits telemetry via the engine. ✓ COMPLETE (test PASSED)
- [x] A1: Implement `RefinementStage` protocol/dataclass capturing required hooks: `name`, `configure(config)`, `run(inputs, telemetry_sink)`, `telemetry_schema`. ✓ COMPLETE (dbex/refinement/stage.py:21-76)
- [x] A2: Implement `RefinementEngine` with deterministic execution order, stage registration, and shared telemetry aggregation (`Dict[str, RefinementTelemetry]`). ✓ COMPLETE (dbex/refinement/engine.py)
- [x] A3: Extract shared helpers for simulator instantiation (`create_panel_simulator(detector_config, crystal_config, hkl_grid, config)`) and Bragg regeneration (`emit_bragg_frame(stage_params, inputs, config)`), and ensure stages call into these utilities rather than duplicating panel loops. ✓ COMPLETE (dbex/refinement/helpers.py, stubs for Phase B-D)
- [x] A4: Update `RefinementTelemetry` (if necessary) to include a `stage_type`/`mode` field so future variants can be distinguished without branching. ✓ COMPLETE (stage_type/mode fields added, backward compatible)
- [x] A5: Register the new engine unit test in `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md`, archive `pytest --collect-only tests/dbex/test_refinement_engine.py` logs under the phase report, and note the selector in the ledger per Exit Criterion #4. ✓ COMPLETE (ARCH-ENGINE-001 registered)
- [x] A6: Produce compliance evidence: confirm doc/spec alignment (docs/spec-db-workflow.md §7) in the report, and update `docs/fix_plan.md` `[ARCH-REFINE-FLOW-001]` entry with the new plan scope plus referenced findings (REFINE-005/007/008) before moving to Phase B. ✓ COMPLETE (phase_a_compliance_evidence.md)
- [x] A7: Document the interface + shared helpers in `docs/architecture/pytorch_design.md` and `plans/active/ARCH-REFINE-FLOW-001/reports/<timestamp>/summary.md`. ✓ COMPLETE (phase_a_implementation_summary.md)

**Key Results:**
- RefinementStage protocol defined with clean interface (name, configure, run)
- RefinementEngine skeleton validates contract via TDD nucleus test (PASSED)
- Shared helper stubs created (create_panel_simulator, emit_bragg_frame)
- Telemetry schema extended (stage_type, mode fields) backward-compatible
- Regression guard PASSED (test_stage_a_expansion unaffected)
- Test registry updated (ARCH-ENGINE-001 active)
- Spec alignment verified (spec-db-workflow.md §7)
- **All Phase A exit criteria SATISFIED**

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** dbex/nanobrag_refinement.py, dbex/refine_one.py (imports), dbex/refinement (new package)
- **Circular Import Risks:** ensure `RefinementStage` module does not import heavy simulator modules at import time to avoid recursive imports when stages instantiate detectors/crystals.
- **State Migration:** Stage objects must capture only the parameters they own; global tensors (sigma_readout, sigma_floor) remain in shared context.

### Notes & Risks
- Enforce Environment Freeze by reusing existing tensors/config; Stage classes must not import optional deps.
- Telemetry contract must stay backward compatible while new fields (stage type/mode) are added.
- Shared simulator/Bragg helpers centralize detector/crystal instantiation; audit them once to avoid reintroducing the duplication highlighted in the recent code review.
- Stage A’s current implementation is the most heavily debugged; when defining the Stage interface, ensure it is generic, and rely on shared helpers (loss/telemetry/caching) that are proven in Stage A so later Stage implementations naturally follow the same patterns without hard-coding Stage-specific behavior into the engine.

## Phase B — Stage A Extraction
**Status:** in_progress (B0 complete 2025-11-23T030000Z, B1a next)
**Strategy:** Multi-loop extraction (approved 2025-11-23T030000Z per blocker report)
**Estimated:** 3-4 loops total

- [x] B0: Record baseline artifacts for Stage A smoke (`test_stage_a_expansion`, collect-only + pytest logs) under `plans/active/ARCH-REFINE-FLOW-001/reports/<timestamp>/baseline/`. ✓ COMPLETE (2025-11-23T030000Z)
- [ ] B1a: **Extract helper functions from inline LBFGS closure** (Loop 1):
  - `_build_stage_a_params()`: Initialize trainable parameters (lines ~761-876)
  - `_build_stage_a_lbfgs_closure()`: Create LBFGS closure with compute_loss nested function (lines ~998-1574)
  - `_run_stage_a_lbfgs()`: Execute optimizer.step(closure) and collect telemetry (lines ~1575-1700)
  - Verify: test_stage_a_expansion regression guard PASSES with extracted helpers
- [ ] B1b: **Wrap helpers in StageA.run()** (Loop 2):
  - Implement StageA class calling extracted helpers in sequence
  - Package telemetry with stage_type/mode fields per Phase A schema
  - Return dict per RefinementStage protocol
  - Verify: StageA.run() produces identical telemetry to inline implementation
- [ ] B2: **Update run_nanobrag_refinement for engine delegation** (Loop 3):
  - Detect Stage A-only mode (not enable_stage_c)
  - Instantiate RefinementEngine([StageA()])
  - Delegate to engine.run()
  - Keep Stage B/C inline temporarily
  - Verify: Engine delegation path passes test_stage_a_expansion
- [ ] B3: Rerun Stage A smoke (small + full detector) and capture logs + telemetry JSON verifying no regression (telemetry states, perf counters, chi-squared traces).
- [ ] B4: Run the relevant DB-AT selector(s) impacted by Stage A (DB-AT-010 Gradcheck plus DB-AT-024 mapping) in collect-only and pytest modes; archive logs/telemetry alongside smoke artifacts to satisfy Exit Criterion #3 for this phase.
- [ ] B5: Update docs/tests to reference the new Stage A class where appropriate (e.g., developer docs showing class layout).

### Notes & Risks
- Ensure Stage A ROI sampling + warm-cache options remain available and configurable (StageA should accept `sampled_panel_ids`, cache flags) and continue to follow the PERF-WARM-SIM-001 telemetry contract (`roi_count_*`, `cache_mode`, `roi_mode`, `forward_time_ms`). If you discover gaps in that contract, extend it inside PERF-WARM-SIM-001 (or a successor perf initiative) rather than introducing a new cache or perf schema in this plan.
- Regression risk: orientation/quaternion handling must remain inside the stage.
- Stage A’s final design (after TORCH-REFINE-002D/002E) is the reference implementation for geometry + loss plumbing; later Stage implementations (including B/C) should reuse the same shared helpers (loss closure, sigma_floor plumbing, telemetry serialization) rather than re-inventing variants.

## Phase C — Stage B Extraction
- [ ] C0: Baseline Stage B artifacts (full-detector run + telemetry) recorded before refactor.
- [ ] C1: Implement `StageB` class supporting both shell modifiers and future per-reflection mode (stub enum for `stage_b_mode`).
- [ ] C2: Wire Stage B into the engine (A→B sequence), dropping the legacy inline code from `run_nanobrag_refinement`.
- [ ] C3: Ensure Stage B telemetry includes `stage_b_mode`, shell modifier stats, and uses canonical Stage A metadata propagated through the engine context.
- [ ] C4: Rerun `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (small + full detectors). Capture collect-only logs and telemetry JSON; verify REFINE-008 gates still apply.
- [ ] C5: Execute DB-AT selectors sensitive to Stage B (e.g., DB-AT-024 mapping) in collect-only + pytest modes, recording artifacts that show parity thresholds remain satisfied after the extraction.

### Notes & Risks
- Stage B must respect REFINE-005 (tricubic interpolation + halo). When moving code, ensure HKL grid caching remains correct.
- Expose switches for future per-reflection implementation (TORCH-REFINE-005) but keep default as shell modifiers.
- Concrete Stage B implementations should wire loss, variance, and telemetry through the same helpers used by Stage A (PHYSICS-LOSS-001)—including sigma_floor handling, chi-squared vs masked-MSE reporting, and perf counters—so the engine sees a uniform contract across stages.

## Phase D — Stage C Extraction
- [ ] D0: Baseline Stage C artifacts (full-detector run + telemetry) recorded pre-refactor.
- [ ] D1: Implement `StageC` class managing detector offset parameters, baseline detector seeding, and telemetry.
- [ ] D2: Plug Stage C into the engine (A→B→C). Remove Stage C inline code from `run_nanobrag_refinement`.
- [ ] D3: Ensure Stage C telemetry keeps canonical Stage A metadata and detector offset reduction stats.
- [ ] D4: Rerun `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (small + full) and archive logs/telemetry proving REFINE-007 gates still succeed.
- [ ] D5: Execute DB-AT selectors that depend on Stage C detector alignment (e.g., DB-AT-021/DB-AT-024 as applicable) in collect-only + pytest modes and capture artifacts confirming canonical gates remain within tolerance post-refactor.

### Notes & Risks
- Stage C must maintain baseline detector seeding behavior and variance-floor clamp telemetry.
- Watch for device/dtype transitions (detector configs currently re-instantiated per panel).
- Concrete Stage C implementations should mirror Stage A’s pattern for parameter deltas, canonical chi-squared fields, and perf counters, so downstream tooling can reason about all stages via the unified schema established by the Stage A-backed helpers, not by Stage-specific engine special cases.

## Phase E — Orchestration Hooks & Mode Wiring
- [ ] E1: Expose stage registry/config knobs in `RefinementEngine`/`run_nanobrag_refinement` (e.g., enable/disable Stage B, set Stage B mode = shell|per_reflection).
- [ ] E2: Update CLI/config surfaces (`RefinementConfig`, `dbex/refine_one.py`) to accept stage enablement flags and pass them into the engine.
- [ ] E3: Add telemetry fields capturing the active stage list and modes (`engine_protocol`, `stage_modes`).
- [ ] E4: Update docs (`docs/architecture/pytorch_design.md`, `docs/spec-db-workflow.md` annotations, `docs/TESTING_GUIDE.md`) describing how to configure alternative stage sequences.
- [ ] E5: Run a combined Stage A/B/C smoke suite plus DB-AT selectors, demonstrating the engine-based protocol is the default path. Archive artifacts under `plans/active/ARCH-REFINE-FLOW-001/reports/<timestamp>/`.

### Notes & Risks
- Ensure CLI defaults replicate current behavior (Stage B shell modifiers enabled, per-reflection disabled until TORCH-REFINE-005 lands).
- Provide guardrails in `docs/fix_plan.md` to keep TORCH-REFINE-005 blocked until Phase E is done.

## Artifacts Index
- Reports root: `plans/active/ARCH-REFINE-FLOW-001/reports/`
- Latest run: `<timestamp>/`
