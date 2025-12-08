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

- **Phase A — Telemetry Design** ✅ COMPLETE (2025-12-08T180000Z)
  - [x] A1: Audit current diagnostics emission (`_write_torch_outputs`) and decide metadata schema for structure-factor provenance.
  - [x] A2: Trace refined MTZ loading path to determine hook points for telemetry (post `load_refined_mtz`, pre `build_structure_factor_grid`); document in planning report.
  - [x] A3: Confirm downstream consumers (tests, DB_AT_024 metrics) can access telemetry without breaking existing artifacts.
  - **KEY FINDING:** Telemetry ALREADY IMPLEMENTED at `dbex/io/writer.py:196-200`. All SCALE-003 fields present.

- **Phase B — Implementation & Tests** ✅ NOT NEEDED (telemetry already exists)
  - [x] B1: Update `run_nanobrag_backend` — ALREADY DONE (`refine_one.py:646-651` constructs `hkl_telemetry` dict)
  - [x] B2: Extend `_write_torch_outputs` — ALREADY DONE (`writer.py:196-200` persists all 4 fields)
  - [x] B3: Add regression test — ALREADY EXISTS (`test_refine_one_cli.py:765, :1158, :1263` + `test_mapping_consistency.py:188`)

- **Phase C — Documentation & Artifact Sync** ✅ NOT NEEDED (documentation current)
  - [x] C1: Pytest logs — test coverage already exists (see downstream_consumers.md)
  - [x] C2: TESTING_GUIDE/TEST_SUITE_INDEX — fields already documented via existing tests
  - [x] C3: fix_plan Attempts History — updated 2025-12-08T190000Z with closure note

**STATUS: DONE** — Initiative closed 2025-12-08T190000Z. Structure-factor telemetry (SCALE-003) was already fully implemented. No new code required.

## Artifacts Index
- Reports root: `plans/active/MAP-SCALE-003/reports/`
- Planned scripts (if promoted): `plans/active/MAP-SCALE-003/bin/`
