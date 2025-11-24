# Implementation Plan: ARCH-SPLIT-001

## Initiative
- ID: ARCH-SPLIT-001
- Title: Split refinement/tooling monoliths into modular seams
- Owner: Unassigned
- Spec Owner: docs/spec-db-workflow.md
- Status: pending

## Goals
- Reduce oversized refinement/tooling modules to clear seams that align with the engine and unified simulator factory.
- Remove duplicate wiring and inline helpers to lower regression risk and make telemetry/test coverage simpler.
- Preserve existing behavior and selectors while shrinking blast radius for future changes.

## Phases Overview
- Phase A — Boundaries & Safety Net: Inventory seams and lock regression baselines.
- Phase B — Split Refinement Core: Modularize `nanobrag_refinement.py` around stage ops and telemetry.
- Phase C — Split CLI/Tooling Glue: Factor `refine_one.py` and `tools/stage_a_adam.py` into smaller units.

## Exit Criteria
1. `run_nanobrag_refinement` delegates to modular helpers; no duplicate simulator wiring paths remain outside `refinement/helpers.py`, and the inline path shares code with engine delegation (single seam).
2. `dbex/nanobrag_refinement.py` is reduced to orchestrating glue (≤ ~900 LOC) with stage-specific ops/telemetry in dedicated modules; public API unchanged.
3. `refine_one.py` separates CLI parsing from backend execution/HDF5 emit into importable helpers; backend dispatch shares code paths (no duplicated ROI scoring/variance logic).
4. `dbex/tools/stage_a_adam.py` splits dataclasses/config, probes, and I/O helpers into focused modules while preserving lazy imports and existing CLIs/tests.
5. Regression guards (`test_torch_refine_smoke.py::test_stage_a_expansion`, DB-AT-024/026, forward-equivalence, CLI smoke, stage_a_adam tests) pass; `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` updated with any selector changes and collect-only logs saved.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** docs/spec-db-workflow.md §§5–7 (staging, engine contract, variance handling)
- [ ] **Spec Constraint:** docs/spec-db-core.md (loss mask/sigma conventions)
- [ ] **Fix-Plan Link:** docs/fix_plan.md — Row [ARCH-SPLIT-001]
- [ ] **Finding/Policy ID:** POLICY-001 (Environment Freeze), CLAUDE incremental progress, single simulator seam (ARCH-REFACTOR-001 exit #9), layered-scope guard (stability first)

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md
- **Key Clauses:** staging (A/B/C), engine acceptance of ordered stages, variance model/Loss mask application, device/dtype neutrality.

## Architecture / Interfaces (optional)
- Key surfaces to preserve: `run_nanobrag_refinement(...)`, `RefinementConfig/Telemetry`, `RefinementEngine`/Stage wrappers, `prepare_refinement_inputs`, `create_unified_simulator`, `refine_one.main` CLI contract, stage_a_adam CLI entrypoints.
- Boundaries: `[CLI/DataLoad] -> [prep + simulator seam] -> [Stage ops] -> [Telemetry/HDF5]`.

## Context Priming (read before edits)
- docs/spec-db-workflow.md §§5–7; docs/spec-db-core.md (loss mask/sigma); docs/architecture/live_backend.md and data_telemetry_flow.md
- tests: DB-AT-024/026, forward-equivalence selectors, CLI smoke, stage_a_adam tests
- Findings: GEOMETRY-003/004, PHYSICS-LOSS-001, ARCH-REFACTOR-001 (exit #9 single seam), ENV freeze

## Phase A — Boundaries & Safety Net
### Checklist
- [ ] A0: Run baseline selectors (DB-AT-024/026, `test_torch_refine_smoke`, forward-equivalence, CLI smoke, stage_a_adam tests) with logs saved under `plans/active/ARCH-SPLIT-001/reports/<ts>/`.
- [ ] A1: Inventory `nanobrag_refinement.py` functions/closures and map to stage/telemetry responsibilities; note simulator wiring points.
- [ ] A2: Inventory `refine_one.py` responsibilities (parse, dispatch, scoring, HDF5/telemetry) and `tools/stage_a_adam.py` sections (dataclasses, probes, I/O).
- [ ] A3: Draft target module layout and dependency constraints (no new wiring seams; reuse `refinement/helpers.py`).

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** `nanobrag_refinement.py`, `refinement/helpers.py`, `refine_one.py`, `tools/stage_a_adam.py`, possibly `refinement/stage_*.py`.
- **Circular Import Risks:** High if stage ops import bridge/helpers; mitigate by keeping leaf math in `geometry`/`physics` and simulator seam in helpers.
- **State Migration:** None; APIs must stay stable while code moves.

### Notes & Risks
- Risk of wiring drift between inline and engine paths; mitigate by converging on single seam.

## Phase B — Split Refinement Core
### Checklist
- [ ] B1: Extract stage-specific ops/telemetry helpers from `nanobrag_refinement.py` into new modules (e.g., `refinement/stage_ops_a/b/c.py`), leaving the facade thin.
- [ ] B2: Route both inline and delegated paths through the same simulator seam and stage helpers; remove duplicate ROI sampling/telemetry assembly.
- [ ] B3: Keep `run_nanobrag_refinement` signature stable; add shims if needed for backward compat; run baselines and record collect-only logs.

### Notes & Risks
- Must preserve cache semantics and device/dtype neutrality; avoid new dependencies per Environment Freeze.

## Phase C — Split CLI/Tooling Glue
### Checklist
- [ ] C1: Factor `refine_one.py` into parse module + backend/HDF5 helpers; ensure ROI scoring/variance logic is single-sourced.
- [ ] C2: Split `tools/stage_a_adam.py` into config/dataclasses, probe runners, and I/O helpers while keeping lazy imports and existing CLIs intact.
- [ ] C3: Update docs/test registry; rerun CLI and tooling smokes; save collect-only logs.

### Notes & Risks
- Ensure no new wiring path bypasses the unified simulator seam; keep backward-compatible CLIs.

## Artifacts Index
- Reports root: `plans/active/ARCH-SPLIT-001/reports/`
- Latest run: `<YYYY-MM-DDTHHMMSSZ>/`
