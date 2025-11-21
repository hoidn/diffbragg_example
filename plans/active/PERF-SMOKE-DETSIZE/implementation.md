
# PERF-SMOKE-DETSIZE — Reduce GPU footprint for Stage smoke tests

## Initiative
- ID: PERF-SMOKE-DETSIZE
- Title: Introduce small-detector fixture for Stage A/B/C smoke tests
- Owner: Ralph
- Spec Owner: docs/spec-db-workflow.md
- Status: pending

## Goals
- Provide a cropped/small detector dataset for Stage smoke tests to reduce runtime and VRAM while preserving spec coverage.
- Keep full-detector assets for parity/acceptance; document which fixtures use which dataset.

## Phases Overview
- Phase A — Dataset Capture: Produce a new refGeom_small.expt/refGeom_small.refl with consistent ROIs/masks.
- Phase B — Test Integration: Wire Stage A/B/C smoke tests + CLI fixtures to use the small dataset; recalibrate gates.
- Phase C — Documentation & Parity Guard: Update docs/tests to ensure parity tests stick with full detector and describe the new fixture.

## Exit Criteria
1. `refGeom_small.expt/.refl` exists under `sp.proc/` with documented provenance and ROI counts.
2. Smoke tests default to the small dataset, parameterized fixtures still accept the full dataset, and gates pass on CPU+GPU.
3. `docs/spec-db-workflow.md` and `docs/TESTING_GUIDE.md` document the small-detector smoke suite vs full-detector parity suite; collect-only artifacts cover both.
4. Parity/acceptance selectors continue to run on the full refGeom dataset with no telemetry regressions.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** docs/spec-db-workflow.md §§Stage A/B/C smoke requirements.
- [ ] **Fix-Plan Link:** docs/fix_plan.md — Row [PERF-SMOKE-DETSIZE].
- [ ] **Finding/Policy ID:** CONFIG-001 (bridge guards), PERF-WARM-001 (telemetry), CONFORMANCE-001 (DB-AT selectors).

## Spec Alignment
- **Normative Spec:** docs/spec-db-workflow.md
- **Key Clauses:** Stage smoke validations, ROI masking rules.

## Context Priming (read before edits)
- docs/spec-db-workflow.md §3
- docs/TESTING_GUIDE.md §Smoke selectors
- plans/active/PERF-WARM-SIM-001/implementation.md
- docs/findings.md entries CONFIG-001, PERF-WARM-001

## Phase A — Dataset Capture
### Checklist
- [ ] A0: **Nucleus:** Run a `dials.slice_sweep`/`reindex` probe on refGeom to verify we can crop detectors while preserving ROI metadata (capture command + log).
- [ ] A1: Define the crop/decimation strategy (e.g., central 512×512 region, maintain ≥50 ROIs) and update ROI bbox/pid mapping script.
- [ ] A2: Emit `refGeom_small.expt/.refl` (+ masks) under `sp.proc/` with README capturing provenance and ROI counts; compute checksums.
- [ ] A3: Validate `DataLoad`/`prepare_refinement_inputs` on refGeom_small (mask polarity, sentinel guards) and archive artifacts under `plans/active/PERF-SMOKE-DETSIZE/reports/<ts>/`.

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** dataset capture scripts, `tests/dbex/test_torch_refine_smoke.py`, `dbex/data_load.py` (if dataset selection is parameterized).
- **Circular Import Risks:** none.
- **State Migration:** Provide a knob (env flag or pytest marker) so engineers can switch between small/full fixtures.

### Notes & Risks
- Ensure Stage B/C still have meaningful ROI coverage; document coordinate transforms to avoid CONFIG-001 regressions.

## Phase B — Test Integration
### Checklist
- [ ] B0: **Nucleus:** Add a temporary micro-test to assert Stage A LBFGS on the small dataset runs ≤5 s on CPU.
- [ ] B1: Parameterize smoke test fixtures (e.g., `@pytest.mark.parametrize("detector_size", ["small","full"], ids=...)`) and default Stage smoke tests to `small`.
- [ ] B2: Recalibrate Stage A/B/C improvement gates based on the small dataset (document telemetry); ensure GPU + CPU runs pass.
- [ ] B3: Update CLI/test docs to show how to force full-detector runs (env flag, pytest marker); add guard to prevent DB-AT selectors from accidentally using the small fixture.

### Notes & Risks
- Watch for coupling between Stage B shell counts and ROI distribution; adjust test assertions accordingly.

## Phase C — Documentation & Parity Guard
### Checklist
- [ ] C1: Update `docs/spec-db-workflow.md` and `docs/TESTING_GUIDE.md` with the new fixture, commands, and rationale.
- [ ] C2: Log fix-plan attempt capturing runtime/VRAM deltas and reference artifacts.
- [ ] C3: Update supervisor prompt / How-To Map templates to mention the small smoke dataset vs full parity dataset; ensure parity selectors assert full detector dimensions.

### Notes & Risks
- Communicate clearly in `input.md` (via supervisor) when the small dataset is acceptable; avoid accidental use during parity investigations.

## Artifacts Index
- Reports root: `plans/active/PERF-SMOKE-DETSIZE/reports/`
- Latest run: `<YYYY-MM-DDTHHMMSSZ>/`
