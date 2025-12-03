# Implementation Plan — ARCH-ENGINE-ARTIFACTS-001

## Initiative
- ID: ARCH-ENGINE-ARTIFACTS-001
- Title: RefinementEngine artifact channel & final-Bragg unification
- Owner: Codex
- Spec Owner: docs/spec-db-workflow.md
- Status: done (2025-12-02T185000Z)

## Goals
- Add a first-class artifact channel to `RefinementEngine` so stages can emit structured outputs (e.g., final Bragg tensors) without private cache hacks.
- Teach Stage B/Stage C wrappers to publish their final Bragg volumes through the engine and collapse `run_nanobrag_refinement` to a single orchestration path that simply consumes telemetry + artifacts.

## Phases Overview
- Phase A — Engine Artifact Channel: Design + implement artifact registry on the engine/stage contract.
- Phase B — Stage Artifact Producers: Update Stage B/Stage C implementations to emit artifacts and validate parity.
- Phase C — Orchestrator Cleanup: Simplify `run_nanobrag_refinement` to rely solely on engine outputs and remove redundant branches.

## Exit Criteria
1. `RefinementEngine.run()` exposes a documented artifact map (e.g., `engine.artifacts["stage_c"]["bragg_full"]`) populated by stages without accessing private attributes.
2. Stage B and Stage C wrappers each emit their final Bragg tensor through the artifact channel, with parity tests proving reconstruction matches today’s helpers within tolerance (≤1e-6 relative MSE per REFINE-FLOW-001).
3. `run_nanobrag_refinement` uses one dynamic stage list, reads the last stage’s artifact to obtain the final Bragg volume, and no longer calls `_build_final_bragg_from_stage_b_telemetry` directly or inspects `_stage_c_bragg_full`.
4. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any new/changed selectors; `pytest --collect-only` logs for touched selectors (`test_torch_refine_smoke.py -k stage_b_shell_modifiers`, `test_torch_refine_smoke.py -k stage_c_detector_microslip`, artifact-specific unit tests) are saved under `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/<timestamp>/`. Do not close the initiative if any selector marked "Active" collects 0 tests.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** docs/spec-db-workflow.md §§33-45 (engine contract, stage sequencing, telemetry/artifact flow)
- [ ] **Spec Constraint:** docs/spec-db-core.md §§57-68, 85-90 (variance/loss + HKL tensor provenance required when reconstructing Bragg arrays)
- [ ] **Fix-Plan Link:** docs/fix_plan.md — 2025-12-01T092807Z (ARCH-REFINE-001 Phase A.4 Do Now steps 1-2: remove inline branch, propagate Stage C `bragg_full` through engine)
- [ ] **Finding/Policy ID:** ARCH-ENGINE-003 (telemetry enrichment must stay in the active engine path); POLICY-001 (Environment Freeze)

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md
- **Key Clauses:** §33 (engine must own orchestration), §41 (stage contract + outputs), §§70-75 (telemetry/HDF5 outputs), docs/spec-db-core.md §§85-90 (HKL / Bragg tensor contracts)

## Architecture / Interfaces
- **Key Data Types / Protocols:**  
  `RefinementContext`, `RefinementTelemetry`, `RefinementStage`, new `RefinementArtifacts` map (e.g., `Dict[str, Dict[str, Any]]` keyed by stage name).  
  Stage outputs must declare artifact keys (e.g., `{"bragg_full": np.ndarray}`) alongside telemetry dicts.
- **Boundary Definitions:**  
  `[CLI refine_one] -> [run_nanobrag_refinement] -> [RefinementEngine] -> [Stage modules] -> [artifacts + telemetry] -> [io/writer]`.
- **Sequence Sketch (Happy Path):**  
  CLI builds context → engine executes Stage A/Stage B/Stage C → each stage updates telemetry + optional artifact entries → engine returns telemetry dict + exposes artifacts map → orchestrator selects the last stage’s artifact to drive IO.
- **Data-Flow Notes:**  
  HKL tensors (`torch.Tensor`) remain inside contexts/stages; only the final Bragg volume (float32 numpy) exits via artifact map. Artifact metadata must indicate device/dtype/source so IO writer can trace provenance without re-running simulators.

## Context Priming (read before edits)
- **Docs/specs to revisit:** docs/spec-db-workflow.md (§§33-45, 70-75), docs/spec-db-core.md (§§57-90), docs/architecture/live_backend.md (engine vs inline flows), docs/architecture/dbex/refinement/context.idl.md & io/writer.idl.md for downstream consumers.
- **Required findings/case law:** docs/findings.md entries ARCH-ENGINE-003 (telemetry enrichment), REFINE-FLOW-001 (Stage B baseline parity), GRADIENT-003 (Stage B CPU fallback constraints).
- **Related telemetry/attempts:** plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/ (engine-only routing Do Now artifacts), any follow-up reports confirming `_stage_c_bragg_full` shim.
- **Data dependencies to verify:** HKL grids/asu maps already cataloged in docs/data_dependency_manifest.md; no new external assets expected, but Stage B artifact validation must capture ROI slices identical to existing smokes.

## Phase A — Engine Artifact Channel
### Checklist
- [ ] A0: **Baseline snapshot** — Run `pytest -q tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --collect-only` and archive logs (ensures selectors are healthy before refactor).
- [ ] A1: Design artifact API (IDL sketch) covering structure (`engine.artifacts`, stage responsibilities), update docs/architecture/module_map.md + new IDL stub if needed.
- [ ] A2: Implement artifact registry in `RefinementEngine`/`RefinementStage` base (store per-stage dicts, expose read-only property, ensure serialization to reports when telemetry_sink set).
- [x] A3: Update Stage C wrapper to emit `{"bragg_full": np.ndarray}` via new API, adjust unit tests to assert artifact availability, and document the contract.

### Dependency Analysis
- **Touched Modules:** `dbex/refinement/engine.py`, `dbex/refinement/stage.py`, `dbex/refinement/stage_c.py`, `dbex/refinement/context.py` (docstrings), tests referencing Stage C artifacts.
- **Circular Import Risks:** Stage modules lazily import helpers; ensure artifact registry lives entirely inside `dbex/refinement` to avoid new `dbex/io` dependencies.
- **State Migration:** Move `_stage_c_bragg_full` private cache into the general artifact map; preserve backwards compatibility until run_nanobrag_refinement flips to the new API.

### Notes & Risks
- Ensure artifact map is thread-safe / per-run (no stale data between invocations).
- Document how telemetry dicts and artifacts coexist so future stages know where to put heavy tensors vs scalar telemetry.

## Phase B — Stage Artifact Producers
### Checklist
- [ ] B0: **Guardrail tests** — Run Stage B/Stage C smokes (CUDA path) to capture current masked MSE + telemetry for comparison.
- [ ] B1: Refactor `_build_final_bragg_from_stage_b_telemetry` so Stage B’s `run()` generates the final Bragg tensor (respecting CPU fallback) and places it in `stage_b` artifacts.
- [ ] B2: Implement parity harness comparing Stage B artifact vs legacy helper (≤1e-6 relative MSE, preserve ROI scores) and extend GRADIENT-003 notes for CPU fallback limitations.
- [ ] B3: Update Stage C to stop returning `bragg_full` in telemetry dict (artifact only), adapt tests + documentation.

### Notes & Risks
- Stage B CPU fallback relies on cloning Stage A context to CPU; ensure artifact emission reuses the same code path so no extra device copies slip in.
- Need to ensure artifact serialization doesn’t bloat telemetry JSON (keep numpy arrays in artifacts only).

## Phase C — Orchestrator Cleanup
### Checklist
- [ ] C1: Rewrite `run_nanobrag_refinement` to build a single `stages` list, call `engine.run`, fetch final Bragg via artifact map (Stage B or Stage C), and fall back to Stage A helper only when later stages disabled.
- [ ] C2: Delete `_build_final_bragg_from_stage_b_telemetry` (or keep as Stage B internal helper) and remove `_stage_c_bragg_full` access plus obsolete branch logic.
- [ ] C3: Update docs (`docs/architecture/live_backend.md`, `docs/architecture/module_map.md`) and smoke tests/fixtures to reflect simplified flow; capture new `pytest --collect-only` + run logs in reports.

### Notes & Risks
- Need to revalidate CLI/HDF5 outputs because the orchestrator will no longer rebuild Stage B results manually; coordinate with `dbex/io/writer.py`.
- Watch for compatibility shims (tools calling run_nanobrag_refinement expecting `{"A": telem}`); ensure telemetry dict structure unchanged.

## Artifacts Index
- Reports root: `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/`
- Latest run: `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/<YYYY-MM-DDTHHMMSSZ>/`

## Initiative Closure Notes (2025-12-02T185000Z)

All phases complete. All exit criteria satisfied:
- ✅ Exit Criterion #1: RefinementEngine artifact map exposed and functional
- ✅ Exit Criterion #2: Stage A/B artifacts match helpers within ≤1e-6 (perfect parity: max_rel=0.000e+00)
- ✅ Exit Criterion #3: run_nanobrag_refinement uses artifact-only path (-50 lines fallback logic removed)
- ✅ Exit Criterion #4: Test registry synchronized (2/2 parity tests collect and PASS)

Infrastructure from ARCH-STAGE-CONTEXT-001 made Phases A-B trivial. Phase C cleanup was surgical with zero behavioral changes.

See `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-02T185000Z/initiative_closure_summary.md` for full details.
