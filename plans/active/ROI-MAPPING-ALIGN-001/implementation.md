# Implementation Plan — ROI-MAPPING-ALIGN-001

## Initiative
- ID: ROI-MAPPING-ALIGN-001
- Title: Stage-A / Mapping ROI Alignment & Parity
- Owner: (unassigned)
- Spec Owner: docs/spec-db-core.md, docs/spec-db-conformance.md, docs/spec-db-vis.md
- Status: pending

## Goals
- Determine whether the negative ROI correlation on the smoke fixtures (DB-AT-028/029) is caused or amplified by incorrect or inconsistent ROI calculation (bbox, mask, and background treatment) between golden mapping and Stage-A smoke paths.
- Align ROI generation for DB-AT-024/027/028/029 and Stage-A/mapping tooling so that, for a given canonical configuration, all paths use the same ROI set and mask semantics.
- Either (a) fix ROI generation / selection so it is self-consistent and spec-aligned, or (b) conclusively rule out ROI calculation as the primary cause of the DB-AT-028/029 negative CC, with evidence.

## Phases Overview
- Phase A — Evidence & ROI Parity Probes: Compare ROI sets and CC under different ROI regimes (golden vs smoke vs unified).
- Phase B — ROI Contract & Implementation Fix: Define and implement a canonical ROI contract for DB-AT selectors and Stage-A / mapping helpers.
- Phase C — Spec, Tests & Docs Alignment: Codify the ROI contract in specs and tests; wire DB-AT selectors to the canonical path.

## Exit Criteria
1. For at least one canonical configuration (golden simple_cubic), DB-AT-024 and the Stage-A DB-AT-027/028/029 paths are shown to use identical ROI definitions (same panel_id, bbox, and loss mask coverage) as measured by a dedicated ROI parity probe.
2. The ROI contract is documented in `docs/spec-db-core.md` and `docs/spec-db-conformance.md` (DB-AT-024/027/028/029 sections), including:
   - how ROIs are derived from reflection tables / experiment geometry,
   - the required mask semantics (background ≥ 0, trusted_mask polarity, mask coverage expectations),
   - and how Stage-A and mapping must reuse that contract.
3. A regression selector (or extension of existing DB-AT selectors) asserts ROI parity between mapping and Stage-A for the canonical configuration, and the probe shows either:
   - improved ROI CC on smoke when using the unified/golden ROI set, or
   - robust evidence that ROI calculation is not the dominant cause of the negative CC (i.e., CC remains negative even with perfect ROI parity and geometry alignment).
4. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any new/changed selectors; `pytest --collect-only` logs for documented selectors are saved under `plans/active/ROI-MAPPING-ALIGN-001/reports/<timestamp>/`.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** `docs/spec-db-core.md` — ROI / loss-mask and background sentinel contracts (array ordering, sentinel semantics, loss mask definition).
- [ ] **Spec Constraint:** `docs/spec-db-conformance.md` — DB-AT-024/027/028/029 acceptance criteria (ROI CC and chi²/pixel bounds).
- [ ] **Spec Constraint:** `docs/spec-db-vis.md` — Mapping-aligned Stage-A visuals and ROI visualization contract.
- [ ] **Fix-Plan Link:** `docs/fix_plan.md — Row [ROI-MAPPING-ALIGN-001]`
- [ ] **Finding/Policy ID:** `POLICY-001` (Environment Freeze), `CONFORMANCE-001` (DB-AT enforcement), `STAGEA-001` (Stage-A zero-point calibration).

## Spec Alignment
- **Normative Spec:** docs/spec-db-core.md  
  - ROI bbox semantics and loss-mask definition must match `prepare_refinement_inputs` and DataLoad / DIALS background contracts.
- **Normative Spec:** docs/spec-db-conformance.md  
  - DB-AT-024/027/028/029 definitions of ROI CC and chi²/pixel implicitly assume consistent ROIs across mapping and Stage-A paths.
- **Normative Spec:** docs/spec-db-vis.md  
  - Mapping-aligned Stage-A visuals (“before” model) must use the same ROIs as the mapping reference for fair visual comparison.

## Context Priming (read before edits)
- Primary docs/specs to re-read:
  - `docs/spec-db-core.md` — core data structures, ROI / loss-mask, sentinel semantics.
  - `docs/spec-db-conformance.md` — DB-AT-024/027/028/029 sections.
  - `docs/spec-db-vis.md` — triptychs / residuals and ROI visualization.
  - `docs/data_dependency_manifest.md` — golden simple_cubic vs smoke assets.
- Required findings/case law:
  - STAGEA-001 — Stage-A zero-point parity expectations.
  - SCALE-004/005/008/009 — calibration and N_cells behavior that interacts with ROI CC.
  - ARCH-SIM-CONSTRUCTION-001, ARCH-SIM-HKL-BOUNDS-001 — HKL and simulator construction issues (to avoid mis-attributing lattice/partiality bugs to ROIs).
  - TOOLING-VIS-001 — mapping context and visual tooling contracts.
- Related telemetry/attempts:
  - `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/*` — DB-AT-028/029 metrics, baseline probes, ROI-level diagnostics.
  - `plans/active/TOOLING-VIS-001/reports/*` — mapping metrics and ROI CC evidence on golden/simple_cubic and smoke.
  - `stage_a_engine_probe/*` — DB-AT-027 zero-point PNGs / JSON for Stage-A vs mapping parity.
  - `scripts/generate_simple_cubic_golden.py` — golden ROI capture pipeline.
- Data dependencies to verify:
  - Golden mapping assets: `tests/fixtures/golden_data/simple_cubic/refined.{expt,refl}`, `refined_structure_factors.mtz`, `config_torch.json`, `747_mask.pkl`.
  - Smoke assets: `refGeom.expt/refl`, `sp.proc/idx-0000_sigma_metadata.expt`, `sp.proc/refGeom_small/*.expt`, `sp.proc/refGeom_small/*.refl`, `sp.proc/refGeom_small/*_mask.pkl`.
  - Reflection tables and ROI metadata consulted by `simtbx.diffBragg.utils.get_roi_background_and_selection_flags`.

## Phase A — Evidence & ROI Parity Probes

### Checklist
- [ ] A0: **Nucleus / Test-first gate:** Add a small, CPU-only probe script under `plans/active/ROI-MAPPING-ALIGN-001/bin/` (e.g., `compare_roi_layouts.py`) that:
  - loads both the golden mapping configuration (DB-AT-024 fixtures) and the smoke configuration resolved by `refgeom_dataload`, and
  - writes JSON/CSV summaries of ROI bbox sets (`panel_id, x0, x1, y0, y1`) and mask coverage for each path under `plans/active/ROI-MAPPING-ALIGN-001/reports/<timestamp>/`.
- [ ] A1: On golden simple_cubic, compare ROI sets between:
  - `scripts/generate_simple_cubic_golden.py`’s ROI capture and
  - DB-AT-024’s `prepare_refinement_inputs` / `TestDB_AT_024_Mapping::canonical_assets`,
  ensuring they are identical (or quantifying any differences) for the same refined.expt/refl fixture.
- [ ] A2: For the smoke path, run the ROI probe in two modes:
  - (a) the current smoke configuration (idx-0000_sigma_metadata.expt / refGeom_small),
  - (b) smoke selectors forced through the golden simple_cubic assets (via `DBEX_SMOKE_USE_GOLDEN_SIMPLE_CUBIC` and/or `DBEX_SMOKE_GEOM_PATH`),
  and compare ROI layouts vs golden mapping to see whether geometry/fixture choices alone explain the “wrong-looking” ROIs.
- [ ] A3: For each configuration in A2, compute per-ROI CC vs data for:
  - mapping forward (`simulate_forward_once`),
  - Stage-A zero-point (DB-AT-027 / Stage-A engine probe),
  using the *same* ROI set, and record distributions (median, tails) to see how CC changes under unified vs current ROIs.

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** `tests/conftest.py`, `dbex/data_load.py`, `dbex/refinement/inputs.py`, `scripts/generate_simple_cubic_golden.py`, `tests/dbex/test_mapping_consistency.py`, `tests/dbex/test_stage_a_smoke_parity.py`.
- **Circular Import Risks:** Low — ROI work lives in fixtures and simple probes; no new imports into core engine modules planned in Phase A.
- **State Migration:** None in Phase A — probe scripts are read-only over existing fixtures; no persistent state changes.

### Notes & Risks
- Risk: Early probes might conflate geometry drift with ROI generation bugs. Mitigation: always run golden and smoke through the same expt/refl/mask where possible, to isolate ROI logic from geometry.

## Phase B — ROI Contract & Implementation Fix

### Checklist
- [ ] B1: Based on Phase A evidence, define an explicit ROI contract:
  - how `bbox` and ROI selection are derived from reflection tables and experiment geometry,
  - acceptable ROI sizes / shapes (shoebox parameters),
  - how background sentinels and trusted masks interact with ROI coverage.
- [ ] B2: If discrepancies between golden and smoke ROI generation are found:
  - factor a small ROI-builder helper (e.g., `dbex.roi.build_rois(...)`) that wraps `get_roi_background_and_selection_flags` with explicit parameters and invariants,
  - update `DataLoad`-based ROI consumers (DB-AT-024 mapping, `refgeom_dataload`, Stage-A smoke tests) to use that helper so they share a single source of truth.
- [ ] B3: Add a narrow architecture or DB-AT enforcement test that:
  - for the canonical golden configuration, asserts ROI parity between:
    - DB-AT-024 mapping inputs, and
    - Stage-A DB-AT-027/028/029 fixtures (using `refgeom_dataload` forced to golden),
  - and fails if any ROI bbox or mask coverage drifts.

### Notes & Risks
- Risk: ROI fixes might expose more severe simulator physics defects by removing “accidental” cancellation from bad boxes. Mitigation: treat this as success; document in ARCH-SIM-CONSTRUCTION-001 / related plans and keep ROI contract clean.

## Phase C — Spec, Tests & Docs Alignment

### Checklist
- [ ] C1: Update `docs/spec-db-core.md` to:
  - describe the canonical ROI contract (bbox semantics, mask polarity, background sentinel handling),
  - and reference ROI parity expectations for DB-AT selectors.
- [ ] C2: Update `docs/spec-db-conformance.md` (DB-AT-024/027/028/029) and `docs/spec-db-vis.md` to:
  - state that mapping, Stage-A, and mapping-aligned visuals must share the same ROI set for the canonical configuration,
  - and explicitly clarify how smoke fixtures relate to the golden mapping baseline.
- [ ] C3: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` to:
  - document any new ROI parity selector or modified DB-AT selector behavior,
  - and capture `pytest --collect-only` logs for those selectors under `plans/active/ROI-MAPPING-ALIGN-001/reports/<timestamp>/`.
- [ ] C4: Re-run DB-AT-024/027/028/029 in the unified golden configuration and record:
  - ROI CC and χ²/pixel metrics before/after any ROI fixes,
  - and a short analysis (e.g., `roi_alignment_summary.md`) stating whether ROI calculation was a primary or secondary contributor to the negative CC on smoke.

### Notes & Risks
- Risk: Spec changes may need to acknowledge legacy ROI behavior for archived artifacts. Mitigation: clearly mark legacy behavior as historical, and define the new contract as canonical going forward, with references to this initiative’s artifacts.

## Artifacts Index
- Reports root: `plans/active/ROI-MAPPING-ALIGN-001/reports/`
- Latest run: `<YYYY-MM-DDTHHMMSSZ>/`

