# MAP-SCALE-001 Closure & CLI Gap Assessment (2025-11-04T233500Z)

## Reality Check
- Verified DB_AT_024 documentation sync landed in 2025-11-04T220000Z report; thresholds pass with sample clipping enabled.
- Inspected `dbex/refine_one.py::run_nanobrag_backend` (`dbex/refine_one.py:162-258`) and confirmed the CLI path still skips DiffBragg calibration metadata:
  - No `load_calibration_metadata` call; beam config built via `create_beam_config(DL.beam)` (line 226) with flux/exposure defaults.
  - `create_crystal_config(DL.crystal, DL.Expt)` (line 227) never enables `apply_n_cells`, so sample clipping guard from SCALE-005 cannot trigger.
  - CLI only respects `--spot-scale-override` and never sources refined structure factors; zero-iteration CLI runs remain under-scaled/over-scaled depending on manual flags.

## Findings / Decisions
- MAP-SCALE-001 exit criteria (diagnose, compare, draft Do Now) are satisfied; status can move to `done` after logging this assessment in fix_plan attempts.
- Identified new initiative need: wire DiffBragg calibration + refined MTZ plumbing into CLI to align actual user workflow with DB_AT_024 guardrails.
- Documented durable guardrail as SCALE-006: nanobrag CLI must ingest `config_torch.json` metadata (spot_scale, beam flux/exposure, beamsize, N_cells) and pass through to beam/crystal configs before enabling sample clipping.

## Next Actions
1. Close MAP-SCALE-001 in `docs/fix_plan.md` (status → done, add 2025-11-04T233500Z attempt referencing this report).
2. Spin up `MAP-SCALE-002 — Nanobrag CLI calibration parity` with implementation plan covering parser updates, calibration loading, refined MTZ IO, and DB_AT_024 regression guard.
3. Draft Do Now for Ralph: modify `dbex/refine_one.py::run_nanobrag_backend`/`create_parser` to load `config_torch.json` + optional refined MTZ, propagate beam_config + N_cells to simulator, and extend `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator` plus new targeted CLI smoke to assert calibration plumbing. Validate with `pytest -v tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator` and DB_AT_024 selector.

## Artifacts
- Summary: this file
- Evidence: code citations embedded above
