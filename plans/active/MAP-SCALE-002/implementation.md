# MAP-SCALE-002 — Nanobrag CLI calibration parity

## Purpose
Bring the `dbex.refine_one` nanobrag backend up-to-date with MAP-SCALE-001 guardrails so zero-iteration CLI runs ingest DiffBragg calibration metadata (spot_scale_override, beam flux/exposure, beamsize, `N_cells`) and refined structure factors before invoking `nanobrag_torch.Simulator`.

## References
- docs/spec-db-workflow.md §4 — calibration policy and global scale application
- docs/config_crosswalk.md §2 — beam/crystal parameter mapping from dxtbx to torch configs
- docs/findings.md (SCALE-003, SCALE-004, SCALE-005, SCALE-006) — calibration + sample clipping requirements
- tests/dbex/test_mapping_consistency.py — acceptance thresholds and fixture loading
- plans/active/MAP-SCALE-001/reports/2025-11-04T233500Z/summary.md — CLI gap assessment

## Exit Criteria (from fix_plan)
1. Extend CLI parser to accept DiffBragg calibration metadata (`--torch-config`) and optional refined structure-factor path; document defaults/environment flags.
2. Update `run_nanobrag_backend` to load calibration via `load_calibration_metadata`, propagate overrides through `create_beam_config`/`create_crystal_config`, gate `apply_n_cells`, and fall back gracefully when metadata missing.
3. Add regression coverage so CLI smoke tests assert calibration plumbing and DB_AT_024 selector artifacts capture CLI-parity metrics with passing pytest + collect-only logs archived under `plans/active/MAP-SCALE-002/reports/<timestamp>/`.

## Phase Outline

- **Phase A — Gap confirmation & fixture alignment**
  - [x] A1: Inspect existing CLI backend for calibration/sample clipping omissions (2025-11-04T233500Z summary).
  - [x] A2: Inventory CLI-accessible fixtures (config_torch.json, refined MTZ) and confirm expected workspace locations.

- **Phase B — CLI plumbing**
  - [x] B1: Add parser arguments (`--torch-config`, `--refined-mtz`) with validation and docs cross-links.
  - [x] B2: Load calibration metadata + refined structure factors inside `run_nanobrag_backend`, defaulting to legacy behavior when omitted.
  - [x] B3: Propagate calibration to `create_beam_config`/`create_crystal_config`, toggling `apply_n_cells` only when metadata includes domain counts; attach diagnostics to `_write_torch_outputs` payload.

- **Phase C — Regression coverage**
  - [x] C1: Update `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator` to assert calibration forwarding (mock `load_calibration_metadata`, beam_config arguments, `apply_n_cells`).
  - [x] C2: Author targeted CLI smoke (fixture-driven) or reuse DB_AT_024 to confirm thresholds after CLI path changes; capture artifacts under `plans/active/MAP-SCALE-002/reports/<timestamp>/`.
  - [ ] C3: Run mapped pytest selectors and `--collect-only`, archive logs with environment flags noted.

- **Phase D — Documentation sync & closeout**
  - [ ] D1: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` with new CLI regression selectors.
  - [ ] D2: Append fix_plan attempts + findings if new lessons emerge; mark status `done` after artifacts validated.

## Artifacts Index
- Reports root: `plans/active/MAP-SCALE-002/reports/`
- Scripts (if promoted): `plans/active/MAP-SCALE-002/bin/`
