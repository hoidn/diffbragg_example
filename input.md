Summary: Wire DiffBragg sample clipping into the torch bridge so DB_AT_024 hits its correlation/localization thresholds.
Mode: none
Focus: MAP-SCALE-001 — Zero-iteration mapping scale alignment
Branch: integration
Mapped tests: tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z/{mapping_metrics.json,mapping_metrics.csv,pytest.log}
Do Now:
- MAP-SCALE-001:
  - Implement: `dbex/nanobrag_bridge.py::simulate_forward_once` (propagate `beam_config` into `nanobrag_torch.Simulator`, allow `create_crystal_config(..., apply_n_cells=True)` when calibration provides domain counts, keep `n_cells_applied` diagnostics) and adjust `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` expectations if the metrics schema changes.
  - Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1`
  - Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z/
How-To Map:
1. `mkdir -p plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z`
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1`
3. `jq '.corr_median, .localization_success_rate' plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z/mapping_metrics.json`
Pitfalls To Avoid:
- Do not double-apply √spot_scale; raw simulator output should only be scaled once per SCALE-002.
- Forward the exact calibration beam metadata (flux, beamsize, exposure) or sample clipping will zero the signal.
- Only apply `N_cells` when the calibration dict provides it; keep diagnostics proving the guard fired.
- Preserve device-neutral code paths (leave CPU default, no hardcoded CUDA tensors).
- Keep ROI artifact paths stable so the ledger references remain valid and avoid overwriting prior metrics.
Findings Applied (Mandatory):
- SCALE-002 — Ensure global √spot_scale is applied post-simulation exactly once.
- SCALE-003 — Consume DiffBragg calibration metadata (spot_scale_override, flux/exposure) for zero-iteration parity.
- SCALE-004 — Continue using refined MTZ + refined geometry to meet DB_AT_024 expectations.
- SCALE-005 — Enable `N_cells` only when beam sample clipping is forwarded through the simulator.
Pointers:
- docs/spec-db-conformance.md:43 — DB_AT_024 acceptance thresholds.
- docs/config_crosswalk.md:39-72 — Beam/crystal metadata mapping into torch configs.
- docs/nanobrag_api.md:18-67 — Sample clipping semantics for `BeamConfig` and `CrystalConfig`.
- docs/findings.md:18 — SCALE-005 guard details.
- plans/active/MAP-SCALE-001/implementation.md — Phase D checklist for sample-clipping integration.
If Blocked: Capture the exact simulator/calibration error, log it under Attempts History, leave a note in `plans/active/MAP-SCALE-001/reports/2025-11-04T190041Z/` (summary.md), and pause for supervisor guidance.
