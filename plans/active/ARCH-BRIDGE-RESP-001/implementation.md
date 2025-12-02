# Implementation Plan — ARCH-BRIDGE-RESP-001

## Initiative
- ID: ARCH-BRIDGE-RESP-001
- Title: Writer / Bridge Responsibility Split
- Owner: Galph ↔ Ralph
- Spec Owner: docs/spec-db-workflow.md
- Status: planned

## Goals
- Remove ROI scoring / Nelder–Mead optimization from the torch HDF5 writer so `dbex/io/writer.py` becomes a pure serialization boundary that consumes typed ROI analysis artifacts.
- Decompose `dbex/nanobrag_bridge.py` into explicit modules (inputs builder, detector/crystal config factories, calibration guards) to eliminate the current “god module” and make spec alignment/audits tractable.

## Phases Overview
- Phase A — Contracts & Boundaries: Capture desired seams, add typed ROI analysis dataclasses, and update the writer/bridge IDLs plus data manifest.
- Phase B — Writer Serialization Cleanup: Introduce reusable ROI scoring helper(s), route CLI/engine paths through them, and stop performing optimization inside `write_torch_outputs`.
- Phase C — Bridge Decomposition & Adoption: Relocate RefinementInputs builder + config hydration into focused modules, wire call sites, and retire the legacy monolith.

## Exit Criteria
1. `dbex/io/writer.py::write_torch_outputs` accepts typed ROI analysis payloads and no longer runs Nelder–Mead or mutates ROI data internally; ROI scoring happens in a dedicated helper or analysis tool whose artifacts are referenced in docs/TESTING_GUIDE.md selectors.
2. ROI scoring artifacts (scores, scales, residual diagnostics) are captured via the new helper and persisted under `plans/active/ARCH-BRIDGE-RESP-001/reports/.../`, and `docs/architecture/dbex/io/writer.idl.md` plus `docs/data_dependency_manifest.md` describe the new responsibilities.
3. `dbex/nanobrag_bridge.py` is reduced to an orchestration shim: RefinementInputs builder, detector/crystal config factories, and calibration guards live in dedicated modules with typed APIs, and dependent stages/CLI/tests import the new modules.
4. Updated tests/CLI paths continue to satisfy DIAGNOSTICS-001 + PHYSICS-LOSS findings; any new/renamed selectors are synced per template requirement (collect-only logs stored under this initiative’s reports).

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** docs/spec-db-core.md §§20-70 — array ordering, ROI/loss mask semantics, and variance model must remain unchanged.
- [ ] **Spec Constraint:** docs/spec-db-workflow.md §§30-75 — staging outputs + `/torch_diagnostics` schema and ROI scoring provenance.
- [ ] **Fix-Plan Link:** docs/fix_plan.md — Row [ARCH-BRIDGE-RESP-001] (Tier 0 problems-ledger follow-up).
- [ ] **Finding/Policy ID:** DIAGNOSTICS-001 (writer schema), PHYSICS-LOSS-001/002/003 (variance + telemetry), GEOMETRY-001/002 + CONFIG-001 (bridge mapping guards).

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md; docs/spec-db-core.md; docs/spec-db-interfaces.md.
- **Key Clauses:** Pipeline step 6 (loss + variance), staging outputs/HDF5 schema, calibration precedence, detector geometry mapping, ROI bbox semantics, and CLI contracts for sigma/sigma_floor.

## Architecture / Interfaces
- **Key Data Types / Protocols:**  
  - `ROITriptych` (new typed payload summarizing ROI data/background/bragg/scores).  
  - `ROIAnalysisResult` (per-ROI Nelder–Mead output + diagnostics).  
  - `RefinementInputs` (background-subtracted target + masks).  
  - `DetectorConfigFactory`, `CrystalConfigFactory` modules for geometry mapping.
- **Boundary Definitions:**  
  `[DataLoad] -> [RefinementInputs Builder] -> [RefinementEngine/Stages] -> [ROI Analysis Helper] -> [Writer]`.
- **Sequence Sketch (Happy Path):**  
  CLI loads DataLoad → builds RefinementInputs (new module) → runs refinement → ROI helper computes scales/scores (optional) → writer serializes bragg + ROI artifacts into HDF5.
- **Data-Flow Notes:**  
  ROI helper consumes numpy/tensor stacks `[panel, slow, fast]`, emits scalar diagnostics + cropped arrays; writer simply writes them. Bridge factories consume dxtbx metadata + calibration tensors, returning typed configs per panel without mutating global dicts.

## Context Priming (read before edits)
- Primary docs/specs: docs/spec-db-workflow.md §§30-75, docs/spec-db-core.md §§20-90, docs/spec-db-interfaces.md (CLI + HDF5 schema), docs/config_crosswalk.md (geometry mapping), docs/data_dependency_manifest.md (DataLoad + writer entries), docs/architecture/dbex/io/writer.idl.md, docs/architecture/live_backend.md (torch backend data flow).
- Findings to enforce: DIAGNOSTICS-001, PHYSICS-LOSS-001/002/003, GEOMETRY-001/002/003, CONFIG-001.
- Related telemetry/attempts: writer extraction artifacts under `plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/`, warm-cache ROI/skor logs in `plans/active/PERF-WARM-SIM-001/reports/2025-11-*`.
- Data dependencies: DataLoad assets (refGeom.expt/refl, 747_mask.pkl, sigma tiles), HKL grids per docs/data_dependency_manifest.md, ROI scoring reliance on `score_trainer.roi_check`.

## Phase A — Contracts & Boundaries
### Checklist
- [x] **A0:** Capture current ROI scoring + writer call graph (trace `write_torch_outputs` callers, Nelder–Mead usage) and record in `reports/…/boundary_audit.md`.
- [x] **A1:** Update `docs/architecture/dbex/io/writer.idl.md` with the new “analysis-first” interface and add/extend an IDL doc for the bridge modules (detector/crystal factories + inputs builder).
- [x] **A2:** Introduce typed ROI analysis dataclasses (e.g., `dbex/io/roi_analysis.py`) plus serialization helpers; ensure they carry dataset names + dtype info mandated by DIAGNOSTICS-001.
- [x] **A3:** Extend `docs/data_dependency_manifest.md` to describe the new helper inputs/outputs and any additional artifacts (ROI logs).

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** `dbex/io/writer.py`, `dbex/refine_one.py`, `dbex/nanobrag_bridge.py`, future helper modules under `dbex/io` or `dbex/refinement`.
- **Circular Import Risks:** Moving RefinementInputs builder into `dbex/refinement/inputs.py` risks circular imports with stages; plan to keep factories lightweight (no torch imports) and let stages inject dependencies.
- **State Migration:** ROI scoring state currently implicit inside writer; new helper must own Nelder–Mead options and pass immutable results into writer; bridging dataclasses need to carry calibration metadata without relying on global dicts.

### Notes & Risks
- SciPy dependency (Nelder–Mead) must remain optional; ensure helper runs under the same Environment Freeze constraints.
- Typed dataclasses must remain numpy-compatible for h5py; avoid torch tensors inside writer boundary.

## Phase B — Writer Serialization Cleanup
### Checklist
- [x] **B1:** Implement ROI scoring helper (`dbex/io/roi_scoring.py` or similar) that ingests ROI crops + variance info, runs Nelder–Mead once per ROI, and emits typed payloads plus JSON/log artifacts. *(Complete — 2025-12-02T223500Z artifacts)*
- [x] **B2:** Update CLI (`dbex/refine_one.py`) and RefinementEngine call sites to invoke the helper (guarded by flag) before calling `write_torch_outputs`, passing the typed payload instead of raw arrays. *(Complete — 2025-12-02T233500Z artifacts)*
- [ ] **B3:** Remove optimization loop from `write_torch_outputs`, require non-None `roi_payloads`, populate ROI datasets from payload triptychs/model/variance, and re-run `tests/dbex/test_refine_one_cli.py::{test_nanobrag_backend_runs_simulator,test_nanobrag_backend_applies_calibration,test_torch_diagnostics_metadata}` plus writer IDL manifest updates.
- [ ] **B4:** Capture `pytest --collect-only` + execution logs for affected selectors under `reports/<timestamp>/pytest_writer_cleanup.log` and sync docs/TESTING_GUIDE.md + docs/development/TEST_SUITE_INDEX.md if selectors change.

### Notes & Risks
- Keep writer backward-compatible (accept `None` or legacy data until all call sites migrate); document removal timeline in fix plan.
- ROI helper must not degrade performance; consider caching ROI crops already held in Stage artifacts.

## Phase C — Bridge Decomposition & Adoption
### Checklist
- [ ] **C1:** Move `RefinementInputs` dataclass + builder into `dbex/refinement/inputs.py`, keeping guards/tests intact; update imports across CLI/tests/stages.
- [ ] **C2:** Extract detector/crystal/beam config hydration into `dbex/refinement/config_factories.py`, factoring out repeated square-pixel/beam-center logic with typed return values.
- [ ] **C3:** Delete deprecated sections from `dbex/nanobrag_bridge.py`, leaving only orchestration glue and docstrings pointing to new modules; re-run smoke selectors that rely on the bridge (`tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`, CLI tests).
- [ ] **C4:** Archive before/after LOC + responsibilities in `reports/.../bridge_split_summary.md`.

### Notes & Risks
- Decomposition must not introduce new import chains that break Stage warm-cache contexts (monitor `dbex/refinement/stage_*` for path updates).
- Need to maintain GEOMETRY-00x guards (square pixels, rotation matrix validation) inside the new factories with unit tests.

## Artifacts Index
- Reports root: `plans/active/ARCH-BRIDGE-RESP-001/reports/`
- Latest run: `2025-12-02T213000Z/`
