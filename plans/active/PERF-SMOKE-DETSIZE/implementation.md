
# PERF-SMOKE-DETSIZE — Reduce GPU footprint for Stage smoke tests

## Initiative
- ID: PERF-SMOKE-DETSIZE
- Title: Introduce small-detector fixture for Stage A/B/C smoke tests
- Owner: Ralph
- Spec Owner: docs/spec-db-workflow.md
- Status: in_progress (2025-11-21 — canonical parity rerun outstanding)

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
- [x] A0: **Nucleus:** Probed refGeom geometry/ROI coverage to confirm a centered 1024×1024 crop preserves 87 ROIs (~31%) and archived the command/output in `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/summary.md`.
- [x] A1: Defined the crop window + ROI filtering strategy, codified it in `plans/active/PERF-SMOKE-DETSIZE/bin/crop_refgeom_to_small.py`, and documented bbox/pid handling (same artifact set).
- [x] A2: Generated `sp.proc/refGeom_small/{refGeom_small.expt,refGeom_small.refl,refGeom_small_mask.pkl}` with README + checksum report (`refGeom_small_report.json`), stashing assets per Phase A exit criteria.
- [x] A3: Validated `DataLoad`/`prepare_refinement_inputs` against the cropped assets (telemetry + Stage A run stored under `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/{collect_stage_a_small.log,telemetry_small.json}`).

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** dataset capture scripts, `tests/dbex/test_torch_refine_smoke.py`, `dbex/data_load.py` (if dataset selection is parameterized).
- **Circular Import Risks:** none.
- **State Migration:** Provide a knob (env flag or pytest marker) so engineers can switch between small/full fixtures.

### Notes & Risks
- Ensure Stage B/C still have meaningful ROI coverage; document coordinate transforms to avoid CONFIG-001 regressions.

## Phase B — Test Integration
### Checklist
- [x] B0: Captured a Stage A runtime probe on the cropped assets (telemetry + log under `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/collect_stage_a_small.log`) establishing the new baseline.
- [x] B1: Parameterized smoke fixtures via `tests/conftest.py::smoke_detector_size`/`smoke_dataset_paths`, defaulting to `"small"` while allowing `"full"` overrides; selectors honor `--smoke-detector-size` / env flags.
- [x] B2: Recalibrated Stage A/B/C strict gates for the small dataset (Stage A improvement ≥0.1%, Stage B non-regression ±1e-6, Stage C offset ≥80%) and archived telemetry in `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/`.
- [x] B3: Updated docs (`docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`) and added `pytest_runtest_setup` guard so DB-AT/workflow selectors enforce `--smoke-detector-size=full` before executing (artifacts: 2025-11-21T031620Z/ summary + logs).

### Notes & Risks
- Watch for coupling between Stage B shell counts and ROI distribution; adjust test assertions accordingly.

## Phase C — Documentation & Parity Guard
### Checklist
- [x] C1: Synced `docs/spec-db-workflow.md` and `docs/TESTING_GUIDE.md` with the small-detector smoke workflow, commands, and rationale plus canonical-detector override instructions.
- [x] C2: Logged the runtime/ROI deltas plus sigma-source mapping in `docs/fix_plan.md` Attempts History and `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/refGeom_small_report.json`.
- [x] C3: Updated supervisor/input templates (docs + guard rails) so parity selectors require `--smoke-detector-size=full`, preventing accidental small-fixture runs on DB-AT selectors.

### Notes & Risks
- Communicate clearly in `input.md` (via supervisor) when the small dataset is acceptable; avoid accidental use during parity investigations.

## Phase D — Canonical parity re-validation
### Checklist
- [ ] D1: Rerun Stage A/B/C smokes on the full detector (`--smoke-detector-size=full`) for both sigma sources (CLI override + metadata) now that REFINE-SMOKE-CANONICAL repaired Stage B/C, and archive pytest + telemetry logs under a new `plans/active/PERF-SMOKE-DETSIZE/reports/<timestamp>/`.
- [ ] D2: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` with the fresh canonical-detector telemetry/gates plus artifact pointers so parity operators know which logs to inspect.
- [ ] D3: Refresh `docs/fix_plan.md` Attempts History and supervisor input once the full-detector artifacts exist so exit criterion #4 can close.

## Artifacts Index
- Reports root: `plans/active/PERF-SMOKE-DETSIZE/reports/`
- Latest run: `2025-11-21T035150Z/`
- Stage B/C callchain snapshot + tap points (canonical detector analysis): `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T035150Z/{callchain/static.md,trace/tap_points.md}`
