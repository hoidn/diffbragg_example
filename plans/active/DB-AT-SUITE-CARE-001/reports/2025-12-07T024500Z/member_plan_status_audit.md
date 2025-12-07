# Member Plan Status Audit (DB-AT-SUITE-CARE-001 Phase A)

**Date**: 2025-12-07T024500Z
**Scope**: Audit of 7 DB-AT acceptance test initiatives

## Summary Table

| Plan ID | Title | Phases | Dependencies | Test File Status | Status | Blocker / Notes |
|---------|-------|--------|--------------|------------------|--------|-----------------|
| DB-AT-002 | Determinism Acceptance Harness | 0/3 (A, B, C) | FORWARD-EQUIV-002 artifacts; `tests/fixtures/golden_data/simple_cubic/` manifest | Not authored yet | pending | Phases A/B/C unchecked; requires FORWARD-EQUIV-002 canonical tensors + env rehearsal |
| DB-AT-010 | Gradient Correctness Guard | 3.75/4 (A, B, C, D partial) | `dbex.nanobrag_bridge` helpers; canonical refGeom assets | `tests/dbex/test_gradients.py` exists | blocked | Phase D regression: gradcheck failure for `crystal_cell_a` per MAP-SCALE-005 reports (2025-11-04/06); hypotheses documented in reports/2025-11-04T232350Z |
| DB-AT-020 | Reflection Ingestion Sanity | 0/3 (A, B, C) | refGeom assets (`scaled.mtz`, `refGeom.expt`, `refGeom.refl`); spec-db-core.md:22, dials_api.md:10-32 | Not authored yet | pending | Phases A/B/C unchecked; requires bbox exclusivity and panel alignment tests |
| DB-AT-021 | Mask semantics guard | 0/3 (A, B, C) | `DataLoad` mask wiring; canonical assets + `747_mask.pkl`; spec-db-core.md:29-55 | Not authored yet | pending | Phases A/B/C unchecked; requires trusted_mask hydration, polarity guard, `tests/dbex/test_mask_semantics.py` authoring |
| DB-AT-022 | Background sentinel guard | 0/3 (A, B, C) | DB-AT-020/021 prerequisites; `background_image` sentinel semantics | Not authored yet | pending | Phases A/B/C unchecked; requires sentinel coverage probes and `prepare_refinement_inputs` guard; `tests/dbex/test_background_semantics.py` authoring |
| DB-AT-023 | Calibration Policy Guard (ADU vs Photons) | 0/3 (A, B, C) | `dbex.refine_one` CLI + `DataLoad`/bridge ADU-per-photon wiring; spec-db-workflow.md §4 | Not authored yet | pending | Phases A/B/C unchecked; requires `--adu-per-photon` CLI arg, photon conversion path, `tests/dbex/test_calibration_policy.py` authoring |
| DB-AT-024 | Mapping Consistency Guard | 2/3 (A, B partial, C) | golden tensors; spec-db-conformance.md, forward_equivalence.md, spec-db-tracing.md | Phase A complete (assets confirmed, baseline captured); Phase B partial (`simulate_forward_once` helper planned, test scaffold not authored) | in_progress | Phase A artifacts in reports/2025-11-04T054053Z (baseline probes); Phase B blocked on helper extraction and `tests/dbex/test_mapping_consistency.py` authoring; Phase C docs sync pending |

## Detailed Findings

### DB-AT-002: Determinism Acceptance Harness
- **Implementation.md location**: `plans/active/DB-AT-002/implementation.md`
- **Phase structure**: A (Reality Check & Inputs), B (Harness Implementation), C (Documentation & Registry Sync)
- **Checklist status**: 0/9 tasks complete
- **Dependencies**: FORWARD-EQUIV-002 artifacts (`tests/fixtures/golden_data/simple_cubic/` manifest checksum `2d1f8d67…8567aee`); determinism env guards (`CUDA_VISIBLE_DEVICES=''`, `TORCHDYNAMO_DISABLE=1`, `NANOBRAGG_DISABLE_COMPILE=1`, `KMP_DUPLICATE_LIB_OK=TRUE`)
- **Recent reports**: reports/2025-11-04T050000Z/ contains `collect_db_at_002.log`, `pytest_db_at_002.log` (likely early probe or stub)
- **Test file**: `tests/dbex/test_forward_determinism.py` (not authored yet per implementation.md Phase B)
- **Blocking conditions**: None; awaiting Phase A execution (dependency audit, env rehearsal, metric spec alignment)
- **Notes**: Phases A1-A3 must confirm FORWARD-EQUIV-002 artifacts exist and thresholds reconcile with testing_strategy.md §2.7 (same-seed ≥0.9999999 corr, diff-seed ≤0.7, ≥50% differing pixels) before authoring Phase B test harness.

### DB-AT-010: Gradient Correctness Guard
- **Implementation.md location**: `plans/active/DB-AT-010/implementation.md`
- **Phase structure**: A (Evidence & Harness Design), B (Implementation & Tests), C (Validation & Documentation), D (Regression Recovery 2025-11)
- **Checklist status**: 9/12 tasks complete (A1-A3, B1-B3, C1-C3 checked; D1-D3 unchecked)
- **Dependencies**: canonical refGeom assets; `dbex.nanobrag_bridge` torch helpers (`prepare_refinement_inputs`, `simulate_forward_once`, `build_structure_factor_grid`)
- **Recent reports**: reports/2025-11-04T232350Z/, reports/2025-11-05T000200Z/ (Phase D regression investigation)
- **Test file**: `tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck` exists
- **Blocking conditions**: Phase D: gradcheck failure for `crystal_cell_a` resurfaced per MAP-SCALE-005 reports/2025-11-06T050000Z/pytest_full_suite.log; hypotheses documented in reports/2025-11-04T232350Z/summary.md
- **Status**: **BLOCKED** pending Phase D fix (patch `simulate_forward_torch` override path to preserve differentiable unit-cell params; guard against `.item()` coercions)
- **Notes**: Phases A-C complete; regression introduced after initial Phase C closure. D1-D3 require audit of TorchCrystal bridge override path, gradcheck tolerance updates, and ledger re-validation.

### DB-AT-020: Reflection Ingestion Sanity
- **Implementation.md location**: `plans/active/DB-AT-020/implementation.md`
- **Phase structure**: A (Reality Check & Inputs), B (Harness Implementation), C (Documentation & Registry Sync)
- **Checklist status**: 0/9 tasks complete
- **Dependencies**: refGeom assets (`scaled.mtz`, `refGeom.expt`, `refGeom.refl`); spec-db-core.md:22, dials_api.md:10-32, architecture.md:122 for bbox exclusivity and panel alignment requirements
- **Recent reports**: reports/2025-11-04T052000Z/ contains `collect_db_at_020.log`, `pytest_db_at_020.log` (likely stub or early probe)
- **Test file**: `tests/dbex/test_reflection_ingestion.py` (not authored yet per implementation.md Phase B)
- **Blocking conditions**: None; awaiting Phase A (dataset availability check, spec alignment, baseline probe)
- **Notes**: Phase A3 baseline probe should capture panels count, ROI tally, sample bbox deltas under reports/<timestamp>/summary.md before authoring Phase B bbox exclusivity checks (`x1 > x0`, `y1 > y0`, upper bounds within panel dims, slicing alignment).

### DB-AT-021: Mask semantics guard
- **Implementation.md location**: `plans/active/DB-AT-021/implementation.md`
- **Phase structure**: A (Baseline validation & probes), B (Implementation & testing), C (Documentation & artifact sync)
- **Checklist status**: 0/9 tasks complete
- **Dependencies**: canonical assets (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`); spec-db-core.md:29-55 mask polarity expectations (True=include, `(background >= 0) ∧ trusted_mask`)
- **Recent reports**: reports/2025-11-04T044251Z/, reports/2025-11-04T060900Z/ (timestamps suggest early investigation or dependency probes)
- **Test file**: `tests/dbex/test_mask_semantics.py` (not authored yet per implementation.md Phase B)
- **Blocking conditions**: None; awaiting Phase A (asset confirmation, DataLoad instantiation with mask, coverage metrics)
- **Notes**: Phase B1 must extend `dbex.data_load.DataLoad` to hydrate `args.maskFile`, expose detector/beam/crystal, enforce polarity guard (ValueError when majority False). Phase B2 tests: `test_DB_AT_021_trusted_mask_shape_and_polarity` and `test_DB_AT_021_loss_mask_consistency` using `prepare_refinement_inputs`.

### DB-AT-022: Background sentinel guard
- **Implementation.md location**: `plans/active/DB-AT-022/implementation.md`
- **Phase structure**: A (Asset validation & sentinel probes), B (Implementation & testing), C (Documentation & artifact sync)
- **Checklist status**: 0/9 tasks complete
- **Dependencies**: DB-AT-020/021 prerequisites (DataLoad bbox/mask wiring); `background_image` sentinel semantics (-1.0 outside ROIs)
- **Recent reports**: reports/ contains `pytest_db_at_022.log`, `roi_coverage.json`, `sentinel_metrics.json` (suggests Phase A probes completed or partial Phase B work)
- **Test file**: `tests/dbex/test_background_semantics.py` (not authored yet per implementation.md Phase B)
- **Blocking conditions**: None (DB-AT-020/021 can proceed in parallel; sentinel guard logic is independent of bbox/mask tests)
- **Notes**: Phase A3 probe should compute sentinel mask (`np.isclose(background, -1.0)`), ROI union mask from bbox/pids, coverage ratios. Phase B1 hardens `prepare_refinement_inputs` with explicit sentinel guard (raise ValueError on unexpected values); Phase B2 tests: `test_DB_AT_022_sentinel_complement`, `test_DB_AT_022_metrics_alignment`.

### DB-AT-023: Calibration Policy Guard (ADU vs Photons)
- **Implementation.md location**: `plans/active/DB-AT-023/implementation.md`
- **Phase structure**: A (Baseline validation & probes), B (Implementation & testing), C (Documentation & artifact sync)
- **Checklist status**: 0/10 tasks complete
- **Dependencies**: `dbex.refine_one.create_parser` CLI extension; `DataLoad`/`nanobrag_bridge.prepare_refinement_inputs` ADU-per-photon wiring; spec-db-workflow.md §4, architecture.md §13, config_crosswalk.md
- **Recent reports**: reports/2025-11-04T052222Z/, reports/2025-11-04T065500Z/ (timestamps suggest early investigation)
- **Test file**: `tests/dbex/test_calibration_policy.py` (not authored yet per implementation.md Phase B)
- **Blocking conditions**: None; awaiting Phase A (asset reality-check, calibration context instantiation, normative source cross-reference)
- **Notes**: Phase B requires CLI arg `--adu-per-photon` (float > 0), photon conversion in `prepare_refinement_inputs` when provided, ADU path with `global_scale_hint`, `target_representation` metadata surfacing. Phase B3 tests cover photon conversion, ADU path, invalid/non-positive guardrails.

### DB-AT-024: Mapping Consistency Guard
- **Implementation.md location**: `plans/active/DB-AT-024/implementation.md`
- **Phase structure**: A (Baseline validation & probes), B (Implementation & testing), C (Documentation & artifact sync)
- **Checklist status**: 6/10 tasks complete (A1-A3 checked; B1-B4 unchecked; C1-C3 unchecked)
- **Dependencies**: golden tensors; spec-db-conformance.md, forward_equivalence.md, spec-db-tracing.md; `refine_one.run_nanobrag_backend` zero-iteration helper extraction
- **Recent reports**: reports/2025-11-04T054053Z/, reports/2025-11-04T063053Z/, reports/2025-11-04T070000Z/ (Phase A baseline captured)
- **Test file**: Phase B1 planned: `tests/dbex/test_mapping_consistency.py` (not authored yet)
- **Blocking conditions**: Phase B: extract reusable `simulate_forward_once` helper from `run_nanobrag_backend` returning `(bragg, target_adu, target_photons, loss_mask, panel_slices, diagnostics)` without HDF5 writes; author test scaffold with canonical ROI sampling, correlation/localization math, metrics JSON/CSV emission
- **Status**: **IN_PROGRESS** (Phase A done; Phase B authoring and helper extraction pending)
- **Notes**: Phase A artifacts in reports/2025-11-04T054053Z/ (baseline metrics for `data - background`). Phase B1 helper must reuse `prepare_refinement_inputs`, honor ADU/photon metadata. Phase B2 test selector: `DB_AT_024`. Phase B3 integration with parity utilities to avoid metric drift; skip/xfail when assets missing. Phase C docs promotion to Active status.

## Cross-Plan Observations

1. **Common dependency cluster**: DB-AT-020, DB-AT-021, DB-AT-022, DB-AT-023, DB-AT-024 all require canonical refGeom assets (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`). Asset availability is a shared prerequisite; Phase A tasks verify existence before Phase B implementation.

2. **Sequential dependencies**:
   - DB-AT-022 (Background sentinel) logically follows DB-AT-020 (bbox/ROI) + DB-AT-021 (mask polarity), but can proceed in parallel since sentinel logic is DataLoad-level.
   - DB-AT-023 (Calibration) and DB-AT-024 (Mapping) both consume `prepare_refinement_inputs` output; 024's helper extraction may inform 023's photon conversion path.

3. **Blocked plan escalation**: DB-AT-010 Phase D regression is the only current blocker requiring supervisor attention. Gradcheck failure for `crystal_cell_a` is a hard gate violation; cannot promote to Active until Phase D1-D3 complete.

4. **Phase pattern uniformity**: All 7 plans follow A/B/C structure (Reality Check → Implementation → Docs Sync). DB-AT-010 added Phase D for regression recovery; DB-AT-024 has partial Phase B (helper extraction scope creep). Standard phasing enables portfolio-level progress tracking.

5. **Test authoring gap**: 5 of 7 plans (DB-AT-002, 020, 021, 022, 023) have unchecked Phase B tasks requiring test scaffold authoring. Test file creation is the critical path item for portfolio advancement.

6. **Artifact evidence**: Recent reports/ timestamps (2025-11-04 to 2025-11-05) indicate probing/diagnostic activity across all plans, but only DB-AT-010 and DB-AT-024 have progressed beyond Phase A. Remaining 5 plans are in pending state awaiting Phase A/B execution.

## Recommendations for Roll-up Coordination

1. **Unblock DB-AT-010 Phase D** as Tier-0 priority (gradcheck regression blocks Gradient-Safe conformance profile).
2. **Parallelize Phase A tasks** for DB-AT-002, 020, 021, 022, 023 (asset availability checks + baseline probes are independent).
3. **Sequence Phase B** based on dependency order: 020 (bbox) → 021 (mask) → 022 (sentinel) || 023 (calibration) || 024 (mapping helper extraction).
4. **Centralize asset management**: consider a shared Phase A artifact capturing refGeom availability + checksum validation to avoid redundant file checks across 5 plans.
5. **Test authoring sprint**: Phase B test scaffold creation is the primary blocking task for portfolio closure; recommend dedicated Phase B loop(s) to author 5 missing test files in batch.

---

**Audit completed**: 2025-12-07T024500Z
**Next artifact**: dependency_chain.md
