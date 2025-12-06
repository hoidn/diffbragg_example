# Implementation Plan — DBAT-SMOKE-GOLDEN-001

## Initiative
- ID: DBAT-SMOKE-GOLDEN-001
- Title: Align DB-AT-028/029 smoke path to golden simple_cubic mapping config
- Owner: (unassigned)
- Spec Owner: docs/spec-db-conformance.md, docs/spec-db-workflow.md
- Status: pending

## Goals
- Make DB-AT-027/028/029 and mapping-aligned Stage-A visuals run on the same canonical mapping configuration as DB-AT-024 (golden simple_cubic), not a separate “smoke” calibration snapshot.
- Eliminate hidden differences between “golden” and “smoke” mapping baselines (geometry, mask/ROI set, HKL, calibration, N_cells behavior) for DB-AT selectors and TOOLING-VIS-001 visuals.

## Phases Overview
- Phase A — Canonical Dataset Wiring: Route DB-AT-027/028/029 fixtures through the DB-AT-024 golden simple_cubic assets.
- Phase B — Config/Calibration Unification: Make HKL + calibration selection for DB-AT selectors mirror the DB-AT-024 mapping pipeline.
- Phase C — Spec/Docs/Tests Alignment: Update spec/architecture docs and test registry to reflect the unified “golden mapping” baseline; capture artifacts showing the new behavior.

## Exit Criteria
1. DB-AT-024 and DB-AT-027/028/029 all use the same canonical mapping configuration: `tests/fixtures/golden_data/simple_cubic/{refined.expt,refined.refl,refined_structure_factors.mtz,config_torch.json}` with `747_mask.pkl`, as reflected in `tests/conftest.py` fixtures and mapping helpers.
2. DB-AT-027 zero-point parity passes with the updated wiring, and DB-AT-028/029 selectors run against the golden mapping config without relying on sp.proc “smoke” calibration assets for canonical behavior.
3. Spec/docs are updated to describe DB-AT-024/027/028/029 as sharing a single canonical mapping baseline (golden simple_cubic), and `docs/TESTING_GUIDE.md` + `docs/development/TEST_SUITE_INDEX.md` reflect the new data/config story; a `pytest --collect-only` log for relevant selectors is saved under `plans/active/DBAT-SMOKE-GOLDEN-001/reports/<timestamp>/`.
4. Any remaining uses of `refGeom_small` + smoke calibration for Stage-A/B/C “smokes” are explicitly documented as perf/diagnostic (non-DB-AT) and do not affect DB-AT mapping parity or Stage-A mapping-aligned visuals.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** docs/spec-db-conformance.md — DB-AT-024/027/028/029 mapping and Stage-A parity definitions.
- [ ] **Spec Constraint:** docs/spec-db-workflow.md — Canonical mapping configuration and Stage Smoke Dataset Policy.
- [ ] **Spec Constraint:** docs/spec-db-vis.md — Mapping-aligned Stage-A visuals must use the DB-AT-024 mapping config.
- [ ] **Fix-Plan Link:** docs/fix_plan.md — ARCH-SIM-CONSTRUCTION-001 / TOOLING-VIS-001 Stage-A mapping alignment entries.
- [ ] **Finding/Policy ID:** STAGEA-001 (Stage-A zero-point calibration), CONFORMANCE-001 (DB-AT enforcement), POLICY-001 (Environment Freeze).

## Spec Alignment
- **Normative Spec:** docs/spec-db-conformance.md
  - DB-AT-024 mapping configuration (simple_cubic fixture).
  - DB-AT-027 Stage-A zero-point parity (must reuse DB-AT-024 mapping config).
  - DB-AT-028/029 Stage-A smoke/structure parity selectors.
- **Normative Spec:** docs/spec-db-workflow.md
  - Canonical mapping pipeline for `simulate_forward_once`.
  - Stage Smoke Dataset Policy (refGeom vs refGeom_small, smoke calibration assets).
- **Normative Spec:** docs/spec-db-vis.md
  - Mapping-aligned Stage-A visuals: “before” model must come from DB-AT-024 mapping config.

## Context Priming (read before edits)
- Primary docs/specs:
  - docs/spec-db-conformance.md — DB-AT-024/027/028/029 sections.
  - docs/spec-db-workflow.md — Canonical mapping configuration & Stage Smoke Dataset Policy.
  - docs/spec-db-vis.md — Mapping-aligned Stage-A visuals.
  - docs/data_dependency_manifest.md — simple_cubic fixture vs sp.proc smoke assets.
  - docs/fix_plan.md — ARCH-SIM-CONSTRUCTION-001 + TOOLING-VIS-001 entries.
- Required findings/case law:
  - STAGEA-001 (Stage-A zero-point parity vs mapping).
  - SCALE-004/005/008/009 (calibration + N_cells behavior).
  - ARCH-SIM-CONSTRUCTION-001 (Stage-A baseline alignment).
  - TOOLING-VIS-001 (Stage-A/mapping context + visuals).
- Related telemetry/attempts:
  - plans/active/TOOLING-VIS-001/reports/* (parity probes, mapping metrics).
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/* (baseline stats, DB-AT-027/028/029 artifacts).
  - stage_a_engine_probe/* (DB-AT-027 zero-point PNGs/JSON).
- Data dependencies to verify:
  - Golden assets: `tests/fixtures/golden_data/simple_cubic/refined.expt`, `refined.refl`, `refined_structure_factors.mtz`, `config_torch.json`, `747_mask.pkl`.
  - Smoke assets: `sp.proc/refGeom_small/*`, `sp.proc/calibration/config_torch_smoke*.json`, `smoke_refined_structure_factors*.mtz`, metadata sigma experiments.

## Phase A — Canonical Dataset Wiring
### Objectives
- Make DB-AT-027/028/029 fixture wiring share the same geometry/mask/ROI set as DB-AT-024’s golden simple_cubic mapping config.
- Ensure DB-AT-027/028/029 no longer depend on sp.proc smoke geometry for their canonical behavior (only for perf smokes).

### Checklist
- [ ] A0: **Probing / Baseline Capture:** Collect current DB-AT-024/027/028/029 artifacts and record which .expt/.refl/.pkl assets they resolve to via `DataLoad` and `refgeom_dataload` (store under `plans/active/DBAT-SMOKE-GOLDEN-001/reports/<ts>/baseline_mapping_assets.json`).
- [ ] A1: Update `tests/conftest.py::smoke_dataset_paths` and/or env handling so that, for DB-AT selectors and TOOLING-VIS-001 mapping-aligned runs, geometry and reflections default to `tests/fixtures/golden_data/simple_cubic/refined.{expt,refl}` and `747_mask.pkl` (full detector), unless explicitly overridden.
- [ ] A2: Update `tests/conftest.py::refgeom_dataload` to treat the golden simple_cubic assets as the canonical geometry for DB-AT-027/028/029 (and mapping-aligned Stage-A visuals), with sp.proc refGeom_small reserved for perf smokes; record resolved geometry path in telemetry/fixtures.
- [ ] A3: Run `pytest --collect-only` for `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` and `tests/dbex/test_stage_a_mapping_equiv.py::test_db_at_027_zero_point_parity` to confirm selectors still collect with the new wiring; save logs.

### Notes & Risks
- Risk: Changing defaults in `smoke_dataset_paths` could break other smoke tests that rely on small-detector fixtures. Mitigation: gate behavior behind DB-AT-specific selectors or explicit env vars (e.g., `DBEX_SMOKE_USE_GOLDEN_SIMPLE_CUBIC=1`) to avoid surprising non-DB-AT code.

## Phase B — Config/Calibration Unification
### Objectives
- Make HKL and calibration selection for DB-AT-027/028/029 mirror DB-AT-024’s mapping config.
- Ensure N_cells behavior for DB-AT selectors matches the golden mapping story (no silent suppression/compensation in the canonical path).

### Checklist
- [ ] B1: Update `tests/conftest.py::refgeom_dataload` HKL/calibration resolution so that DB-AT-027/028/029 and mapping-aligned Stage-A visuals default to the golden simple_cubic pair (`refined_structure_factors.mtz`, `config_torch.json`) when no explicit smoke override is set.
- [ ] B2: For the DB-AT path, ensure `dataload.apply_calibration_n_cells=True` for the golden/simple_cubic configuration (no small+metadata suppression); document any remaining small-detector + metadata gates as perf-only behavior.
- [ ] B3: Re-run DB-AT-024, DB-AT-027, DB-AT-028, and DB-AT-029 with the unified config and capture:
      - Mapping vs data metrics (DB-AT-024),
      - Stage-A vs mapping zero-point metrics (DB-AT-027),
      - Stage-A loss-scale/structure parity metrics (DB-AT-028/029),
    under a new reports root (e.g., `plans/active/DBAT-SMOKE-GOLDEN-001/reports/<ts>/db_at_024_027_028_029/`).
- [ ] B4: If DB-AT-028/029 still fail, record the failure signature explicitly as “shared physics issue under golden config” rather than “smoke config mismatch”, updating `docs/fix_plan.md` to point at this initiative’s artifacts.

### Notes & Risks
- Risk: Unifying HKL/calibration may expose additional discrepancies between golden and smoke calibration bundles (e.g., sigma policy or beam flux differences). Mitigation: document any divergences in `docs/fix_plan.md` and treat them as follow-on initiatives rather than silently re-tuning tests.

## Phase C — Spec/Docs/Tests Alignment
### Objectives
- Update normative specs and architecture docs to assert a single canonical “golden mapping” configuration for DB-AT-024/027/028/029 and mapping-aligned Stage-A visuals.
- Synchronize testing docs so selectors are documented against the new data/config story.

### Checklist
- [ ] C1: Update `docs/spec-db-conformance.md` DB-AT-024/027/028/029 sections to:
      - Explicitly state that DB-AT-027/028/029 reuse the DB-AT-024 mapping configuration (golden simple_cubic) for geometry/mask/sigma/HKL/calibration.
      - Replace references to “Stage-A smoke dataset from sp.proc/refGeom_small” with language that distinguishes “golden DB-AT mapping baseline” from perf-only smoke fixtures.
- [ ] C2: Update `docs/spec-db-workflow.md`:
      - In the mapping configuration and Stage Smoke Dataset Policy sections, clarify that:
        - DB-AT selectors and TOOLING-VIS-001 mapping-aligned visuals MUST use the golden/simple_cubic mapping config,
        - `refGeom_small` and smoke calibration bundles are perf/diagnostic only unless explicitly called out as canonical for a future DB-AT.
- [ ] C3: Update `docs/spec-db-vis.md` Mapping-Aligned Stage-A Visuals to point at the unified golden mapping configuration as the only canonical “before” baseline (no sp.proc-specific caveats).
- [ ] C4: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` entries for:
      - DB-AT-024 Mapping,
      - DB-AT-027 Zero-Point Parity,
      - DB-AT-028/029 Stage-A smoke selectors,
      to reference the golden/simple_cubic assets and the new env story (e.g., `DBEX_SMOKE_GEOM_PATH`, `DBEX_SMOKE_HKL_PATH`, `DBEX_SMOKE_CALIB_PATH` when needed).
- [ ] C5: Run `pytest --collect-only` for all DB-AT and mapping-aligned selectors documented in the Testing Guide, and save the collect logs under `plans/active/DBAT-SMOKE-GOLDEN-001/reports/<ts>/collect/` per Exit Criterion #4.

### Notes & Risks
- Risk: Specs may currently imply that DB-AT-028/029 are tied to sp.proc smoke calibration assets. Mitigation: carefully reword those sections to avoid contradicting existing Findings; note in `docs/fix_plan.md` that DBAT-SMOKE-GOLDEN-001 establishes a unified “golden mapping” baseline going forward.

## Artifacts Index
- Reports root: `plans/active/DBAT-SMOKE-GOLDEN-001/reports/`
- Latest run: `<to be populated as phases execute>/`

