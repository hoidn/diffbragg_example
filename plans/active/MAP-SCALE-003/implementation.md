# MAP-SCALE-003 — CLI Refined Structure Factor Telemetry

## Purpose
Expose structure-factor provenance (raw vs refined MTZ) through the nanobrag CLI, guarding SCALE-003/004 assumptions and enabling downstream tests to assert refined metadata is applied when `--refined-mtz` is provided.

## References
- `dbex/refine_one.py` — CLI backend orchestration and HDF5 writer
- `tests/dbex/test_refine_one_cli.py` — Existing CLI regression tests (calibration coverage)
- `docs/spec-db-workflow.md` §4 — Calibration & structure-factor workflow
- `docs/config_crosswalk.md` §2 — Structure-factor and calibration parameter mapping
- `docs/findings.md` — SCALE-003, SCALE-004, SCALE-006 guardrails
- `docs/TESTING_GUIDE.md` §2 — Selector registry & artifact expectations

## Exit Criteria (from fix_plan)
1. `run_nanobrag_backend` and `_write_torch_outputs` surface structure-factor telemetry (`hkl_source`, reflection count, mean amplitude, MTZ path) in torch diagnostics/HDF5 artifacts.
2. Regression coverage exercises the `--refined-mtz` path, asserting `load_refined_mtz` feeds `build_structure_factor_grid` and telemetry marks refined provenance.
3. CLI + DB_AT_024 selectors rerun with updated diagnostics captured under `plans/active/MAP-SCALE-003/reports/<timestamp>/`, and testing docs (TESTING_GUIDE/TEST_SUITE_INDEX) note the new telemetry fields with collect-only evidence.

## Phase Breakdown

- **Phase A — Telemetry Design**
  - [ ] A1: Audit current diagnostics emission (`_write_torch_outputs`) and decide metadata schema for structure-factor provenance.
  - [ ] A2: Trace refined MTZ loading path to determine hook points for telemetry (post `load_refined_mtz`, pre `build_structure_factor_grid`); document in planning report.
  - [ ] A3: Confirm downstream consumers (tests, DB_AT_024 metrics) can access telemetry without breaking existing artifacts.

- **Phase B — Implementation & Tests**
  - [ ] B1: Update `run_nanobrag_backend` to compute telemetry payload (source, reflection count, mean amplitude) and pass it into `_write_torch_outputs`.
  - [ ] B2: Extend `_write_torch_outputs` to persist telemetry under `/torch_diagnostics` attrs (or structured dataset) preserving backward compatibility.
  - [ ] B3: Add regression test `test_nanobrag_backend_uses_refined_mtz` verifying refined MTZ path calls `load_refined_mtz`, forwards amplitudes into `build_structure_factor_grid`, and writes telemetry.

- **Phase C — Documentation & Artifact Sync**
  - [ ] C1: Capture pytest logs for new CLI test and DB_AT_024 (collect + run) under `reports/<timestamp>/`.
  - [ ] C2: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` to mention telemetry fields and artifact locations.
  - [ ] C3: Record Attempts History entry in `docs/fix_plan.md` and add durable lessons to `docs/findings.md` if telemetry introduces new guardrails.

## Artifacts Index
- Reports root: `plans/active/MAP-SCALE-003/reports/`
- Planned scripts (if promoted): `plans/active/MAP-SCALE-003/bin/`
