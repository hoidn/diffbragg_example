# MAP-SCALE-003 Planning Summary — 2025-11-05T110000Z

## Context
- MAP-SCALE-002 landed CLI calibration plumbing (`--torch-config`, `--refined-mtz`) and calibration-positive regression tests.
- Current CLI diagnostics (HDF5 `/torch_diagnostics`) lack structure-factor provenance. Refined MTZ usage is invisible in artifacts, complicating SCALE-003/004 verification.
- `tests/dbex/test_refine_one_cli.py` exercises calibration path but not the refined MTZ branch; regressions could silently fall back to raw MTZ without detection.

## Evidence
- Inspected `dbex/refine_one.py:201-320`: refined MTZ loading logs to stdout but does not persist metadata or flag source in diagnostics.
- `_write_torch_outputs` currently records masked MSE, loss mask coverage, ROI count, target shape, backend. No hook for structure-factor metadata.
- `tests/dbex/test_refine_one_cli.py` lacks assertions around `load_refined_mtz` or telemetry; only calibration metadata path covered.
- DB_AT_024 artifacts (`plans/active/MAP-SCALE-002/reports/2025-11-05T030000Z/mapping_metrics.json`) rely on diagnostics from `simulate_forward_once`, not CLI telemetry.

## Decisions
- Add telemetry dict capturing:
  - `hkl_source`: `"refined_mtz"` or `"raw_mtz"`
  - `mtz_path`: CLI arg used (normalized path)
  - `reflection_count`: integer count of indices passed to grid builder
  - `mean_amplitude`: float mean of amplitudes (post-refined scaling)
- Pass telemetry from `run_nanobrag_backend` to `_write_torch_outputs`, persisting as attributes under `/torch_diagnostics`.
- Extend CLI regression to patch `_write_torch_outputs` and assert telemetry payload when `--refined-mtz` is provided.
- Re-run DB_AT_024 to confirm metrics unchanged and ensure telemetry presence documented in logs/docs.

## Next Steps
1. Implement telemetry wiring & tests (`B1-B3` of implementation plan).
2. Capture pytest (`tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_uses_refined_mtz`) + DB_AT_024 logs under `plans/active/MAP-SCALE-003/reports/<timestamp>/`.
3. Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` to reference telemetry and new selector artifacts.

## Artifacts
- Planning notes only (this file). Implementation artifacts to land under `plans/active/MAP-SCALE-003/reports/<timestamp>/`.
