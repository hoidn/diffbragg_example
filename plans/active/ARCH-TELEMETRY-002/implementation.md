# Implementation Plan — ARCH-TELEMETRY-002

## Initiative
- ID: ARCH-TELEMETRY-002
- Title: Telemetry & Probe Simplification
- Owner: Galph ↔ Ralph
- Spec Owner: docs/spec-db-core.md, docs/spec-db-workflow.md, docs/spec-db-tracing.md, docs/spec-db-vis.md
- Status: pending

## Goals
- Establish a telemetry ownership charter that defers semantics to Spec‑DB and IDLs, clearly identifies production vs diagnostic telemetry owners, and documents allowed surfaces.
- Inventory and safely prune unused, non‑normative telemetry fields while preserving all Spec‑DB, ARCH, and acceptance‑test contracts.
- Add static and process guardrails (AST checks, supervisor policy, review checklist) that prevent new ad‑hoc telemetry dict surfaces and shadow pipelines in plan‑local probes.

## Phases Overview
- Phase A — Charter & Inventory: Author telemetry charter, align it with Spec‑DB/IDLs, and catalog existing fields/consumers.
- Phase B — Enforcement & Diagnostic Policy: Introduce architecture tests and supervisor rules governing new telemetry surfaces and plan‑local scripts.
- Phase C — Cleanup & Closure: Prune unused telemetry, update docs/tests/manifests, and close out ARCH‑TELEMETRY debt for dict‑based surfaces.

## Exit Criteria
1. `docs/architecture/telemetry.md` (or equivalent section) exists, is wired into `docs/index.md`, and names primary/secondary telemetry owners with clear boundaries between production and diagnostic surfaces; it explicitly defers semantics to Spec‑DB (`spec-db-*.md`) and the existing IDLs (`docs/architecture/dbex/*/*.idl.md`, `dbex/io/writer.py`).
2. A telemetry inventory (either in `docs/architecture/telemetry.md` or `docs/data_dependency_manifest.md`) lists key `/torch_diagnostics` attributes, Stage telemetry dataclass fields, mapping/baseline diagnostics, and their code/test/plan consumers; at least one unused, non‑normative field is either removed or explicitly marked deprecated with evidence.
3. `tests/architecture/test_telemetry_surfaces.py` enforces that new long‑lived telemetry dict surfaces in `dbex/` are allowed only in chartered owner modules; new dict schemas must go through the charter + IDL + tests, and existing owner surfaces are covered by a small allow‑list.
4. `prompts/supervisor.md` `<diagnostic_script_policy>` (and any related probe contracts) explicitly constrain plan‑local scripts to views of existing telemetry and forbid creation of shadow telemetry pipelines intended for production; `tests/architecture/test_probe_contracts.py` and the new telemetry guard both pass.
5. `docs/fix_plan.md` and `docs/findings.md` record the change: ARCH‑TELEMETRY‑002 marked with updated status/Attempts History, and any relevant findings (ARCH‑STAGE‑CTX‑001/002, PHYSICS‑LOSS‑001/003, PROBE‑FREEZE‑001) cite the new guardrails; all tests in `docs/TESTING_GUIDE.md` that exercise telemetry/vis selectors pass under the new regime.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** `docs/spec-db-core.md` §Objective Function & Variance Model — telemetry must continue to expose variance‑weighted χ², sigma_readout, and sigma_floor provenance where specified.
- [ ] **Spec Constraint:** `docs/spec-db-workflow.md` §§Calibration & Unit Conventions, Stage/telemetry pipeline — `/torch_diagnostics` attributes for HKL, calibration, loss mask coverage, and stage telemetry remain Spec‑DB compliant.
- [ ] **Spec Constraint:** `docs/spec-db-tracing.md`, `docs/spec-db-vis.md` — mapping/tracing diagnostics exposed via plan‑local helpers remain aligned with normative tracing/visual diagnostics requirements.
- [ ] **Fix‑Plan Link:** `docs/fix_plan.md` — new row [ARCH-TELEMETRY-002] under Tier 3 Tooling & Observability, plus cross‑links from any relevant MAP‑SCALE‑00x, TOOLING‑VIS‑001, PHYSICS‑LOSS‑001 rows.
- [ ] **Finding/Policy ID:** ARCH-STAGE-CTX-001/002 (typed contexts & telemetry ownership), PHYSICS-LOSS-001/003 (variance/chi² telemetry), ARCH-PROBE-FREEZE-001 (probe freeze & shim rules), POLICY-001 (Environment Freeze — no package churn for tooling).

## Spec Alignment
- **Normative Spec:** `docs/spec-db-core.md`, `docs/spec-db-workflow.md`, `docs/spec-db-tracing.md`, `docs/spec-db-vis.md`, `docs/spec-db-interfaces.md`.
- **Key Clauses:** unit/variance model (§Unit Modes, §Variance Definition), calibration & telemetry (§Calibration & Unit Conventions), tracing schema (§Tracing Requirements), visual diagnostics (§Mapping‑aligned Stage‑A Visuals), and HDF5 output contracts.

## Architecture / Interfaces
- **Key Data Types / Protocols:**
  - `RefinementContext`/`JobContext` (`docs/architecture/dbex/refinement/context.idl.md`) as the context boundary carrying telemetry‑relevant metadata (HKL, calibration, sigma provenance).
  - Stage telemetry dataclasses and collector interfaces in `dbex/refinement/telemetry_collectors.py` (StageATelemetry, StageBTelemetry, StageCTelemetry, StageResult, StagePerfCounters).
  - Torch writer IDL + implementation (`docs/architecture/dbex/io/writer.idl.md`, `dbex/io/writer.py`) as the single owner of `/torch_diagnostics` schema.
  - Mapping & baseline helpers (`dbex/vis/mapping.py`, `dbex/refinement/telemetry_baseline.py`) as diagnostic‑level owners for plan‑aligned telemetry.
- **Boundaries:** `[CLI/refine_one] -> [JobContext] -> [RefinementEngine + Stage collectors] -> [StageResult/RefinementTelemetry] -> [IO writer] -> [HDF5/JSON artifacts] -> [plan‑local probes/visuals]`.
- **Data‑Flow Notes:** Production telemetry flows only through typed contexts, collectors, and the writer; plan‑local scripts consume these surfaces to produce derived views, without defining new production schemas.

## Context Priming (read before edits)
- Primary docs/specs to re‑read: `docs/index.md` (Docs Hub), `docs/spec-db-core.md`, `docs/spec-db-workflow.md`, `docs/spec-db-tracing.md`, `docs/spec-db-vis.md`, `docs/architecture.md`, `docs/architecture/data_telemetry_flow.md`, `docs/architecture/dbex/refinement/context.idl.md`, `docs/architecture/dbex/io/writer.idl.md`.
- Required findings/case law: `docs/findings.md` entries for ARCH-STAGE-CTX-001/002, PHYSICS-LOSS-001/003, PROBE-FREEZE-001, DIAGNOSTICS-001, SCALE-003; any MAP‑SCALE‑00x and TOOLING‑VIS‑001 findings on mapping metrics.
- Related telemetry/attempts: `archive/plans/ARCH-TELEMETRY-001/` reports (observer refactor), `plans/active/ARCH-STAGE-CONTEXT-001/` (typed contexts), `plans/active/MAP-SCALE-004/` and `MAP-SCALE-005/` (mapping metrics), `plans/active/TOOLING-VIS-001/` (Stage‑A visuals).
- Data dependencies to verify: Telemetry‑relevant inputs in `docs/data_dependency_manifest.md` (HKL grids, sigma maps, calibration configs, mask assets); mapping metrics JSON and baseline metrics JSON as canonical artifacts for MAP‑SCALE‑00x and PHYSICS‑LOSS‑001.

## Phase A — Charter & Inventory

**Status:** COMPLETE (i=173, commit 744cea60)

### Checklist
- [x] A0: **Nucleus / Contract spike:** Sketch initial telemetry ownership map (owners, surfaces, consumers) for `/torch_diagnostics`, StageResult, mapping diagnostics, and baseline metrics, and validate it against `docs/architecture/data_telemetry_flow.md`. ✅ `reports/2025-12-07T215000Z/ownership_spike.md`
- [x] A1: Author `docs/architecture/telemetry.md` (or section in `docs/architecture.md`) that:
  - Names primary production owners (Stage collectors, writer, CLI telemetry bundle) and secondary diagnostic owners (bridge/mapping/baseline helpers).
  - Explicitly defers semantics to Spec‑DB and IDLs, and describes non‑owners/expansion rules for new telemetry. ✅ `docs/architecture/telemetry.md`
- [x] A2: Build a telemetry inventory covering:
  - `/torch_diagnostics` attributes from `dbex/io/writer.py`,
  - Stage telemetry fields from `dbex/refinement/telemetry_collectors.py`,
  - Mapping diagnostics from `dbex/vis/mapping.py`,
  - Baseline metrics from `dbex/refinement/telemetry_baseline.py`,
  and record where each field is consumed in code/tests/plans. ✅ `reports/2025-12-07T215000Z/telemetry_inventory.md`
- [x] A3: Extend `docs/data_dependency_manifest.md` (or the charter) with a "Telemetry" section that points to owner modules and canonical artifacts (e.g., mapping_metrics.json, baseline metrics JSON). ✅ `docs/data_dependency_manifest.md` §Telemetry Surfaces

### Phase A Gap (to fix in B0)
- Charter not yet linked in `docs/index.md` (Exit Criterion 1 partial) — addressed as B0 task in Phase B.

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** `docs/architecture.md`, `docs/architecture/data_telemetry_flow.md`, `docs/architecture/telemetry.md` (new), `docs/data_dependency_manifest.md`.
- **Circular Import Risks:** None at code level (docs only); ensure any new architecture references point at existing modules/IDLs rather than adding new code dependencies.
- **State Migration:** Telemetry “ownership” moves from implicit conventions in tests/docs into an explicit charter; no runtime state changes in this phase.

### Notes & Risks
- Risk: Mis‑classifying a diagnostic field as non‑normative when it is actually referenced by Spec‑DB, MAP‑SCALE‑00x, or TOOLING‑VIS‑001; mitigate via grep across specs/tests/plans before tagging any field as removable.
- Risk: Charter drifting from IDLs over time; mitigate by cross‑linking and keeping the charter descriptive, not normative.

## Phase B — Enforcement & Diagnostic Policy

**Status:** COMPLETE (i=174, 2025-12-07T220000Z)

### Checklist
- [x] B0: **(Housekeeping)** Wire telemetry charter into `docs/index.md` Architecture section. Completes Exit Criterion 1. ✅ `docs/index.md` (telemetry charter entry added)
- [x] B1: Implement `tests/architecture/test_telemetry_surfaces.py` that:
  - Walks production `dbex/` modules (excluding tests, plans, archive, scripts).
  - Flags new long‑lived telemetry dict surfaces (dict literals or `dict(...)`) returned from public functions or passed into known sinks (writer, JSON/HDF5 helpers) unless they are in the owner allow‑list defined in the charter.
  - Maintains a minimal allow‑list for existing dict surfaces (bridge diagnostics, mapping diagnostics, baseline metrics).
  ✅ `tests/architecture/test_telemetry_surfaces.py` (3 tests: `test_telemetry_owners_exist`, `test_no_unchartered_telemetry_exports`, `test_charter_link_exists`)
- [x] B2: Extend `<diagnostic_script_policy>` in `prompts/supervisor.md` to:
  - Allow plan‑local scripts to compute small derived metrics and write JSON/CSV views of existing telemetry.
  - Forbid creation of new production telemetry schemas (dict shapes intended for future tests/production consumers) outside owner modules.
  ✅ `prompts/supervisor.md` (`<telemetry_charter_compliance>` section added at lines 331-342)
- [x] B3: Align `tests/architecture/test_probe_contracts.py` with the updated policy by:
  - Referencing the telemetry charter from probe contract docs/tests.
  - Ensuring shim scripts remain thin wrappers around owner APIs and do not introduce new telemetry shapes.
  ✅ `tests/architecture/test_probe_contracts.py` (cross-reference comments added at lines 19-20)

### Test Results (Phase B)
```
pytest -v tests/architecture/test_telemetry_surfaces.py tests/architecture/test_probe_contracts.py::test_probe_shims_delegate_to_owner_clis
4 passed in 0.03s
```

### Notes & Risks
- Risk: Over‑aggressive AST rules may flag benign internal dicts; mitigate by scoping the guard to long‑lived/exported surfaces and by maintaining a small allow‑list in code + charter.
- Risk: Policy divergence between `prompts/supervisor.md` and tests; mitigate by updating both together and cross‑referencing sections.

## Phase C — Cleanup & Closure

### Checklist
- [ ] C1: Using the Phase A inventory, identify telemetry fields that are:
  - Not referenced in Spec‑DB, IDLs, tests, `docs/findings.md`, `docs/data_dependency_manifest.md`, or active plan artifacts,
  and either remove them (with evidence recorded in the charter/manifest) or explicitly mark them deprecated.
- [ ] C2: Update any affected mapping/baseline helpers and regeneration scripts to reflect the pruned schemas; regenerate canonical artifacts (e.g., mapping_metrics.json) and ensure MAP‑SCALE‑00x / PHYSICS‑LOSS‑001 selectors remain green.
- [ ] C3: Run the full telemetry‑relevant test slice (Stage smokes, mapping selectors, TOOLING‑VIS‑001 probes, PHYSICS‑LOSS‑001 selectors, architecture tests) and capture logs under `plans/active/ARCH-TELEMETRY-002/reports/<timestamp>/`. Update `docs/fix_plan.md` and `docs/findings.md` with closure notes and mark relevant compliance matrix items as satisfied.

### Notes & Risks
- Risk: Telemetry schema changes accidentally weaken observability or masking regressions; mitigate with before/after comparisons on mapping metrics and Stage telemetry traces for at least one golden dataset.
- Risk: Cleanup loops turning into open‑ended probes; mitigate via clear exit criteria and by deferring any deeper spec/arch redesign to separate initiatives.

## Artifacts Index
- Reports root: `plans/active/ARCH-TELEMETRY-002/reports/`
- Latest run: `plans/active/ARCH-TELEMETRY-002/reports/<YYYY-MM-DDTHHMMSSZ>/`

