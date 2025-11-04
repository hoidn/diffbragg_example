Summary: Align simulate_forward_once with canonical nanobrag capture by propagating flux/beamsize/N_cells calibration so DB_AT_024 meets its correlation/localization thresholds.
Mode: Parity
Focus: MAP-SCALE-001 — Zero-iteration mapping scale alignment
Branch: integration
Mapped tests: tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T190000Z/
Do Now:
- Implement: dbex/nanobrag_bridge.py::simulate_forward_once (ingest beam flux/beamsize/exposure + crystal N_cells from calibration metadata and flow them through the bridge helpers before invoking nanobrag_torch).
- Pytest: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T190000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-001/reports/2025-11-04T190000Z/pytest_db_at_024.log
- Artifacts: plans/active/MAP-SCALE-001/reports/2025-11-04T190000Z/
How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. Extend `load_calibration_metadata` to parse `beam` (flux, beamsize, exposure) and `crystal.N_cells` from `config_torch.json`; return these alongside `spot_scale_override` so callers avoid re-reading the file.
3. Update `create_beam_config` and `create_crystal_config` to accept optional calibration overrides—set flux/beamsize/exposure on the BeamConfig and crystal `N_cells` when metadata is provided (fall back to existing defaults otherwise).
4. Refactor `simulate_forward_once` to take the calibration dict, route it into the helper calls, and keep applying √spot_scale post-sim; ensure detector instantiation still uses trusted mask tensors and stays device-neutral.
5. Adjust `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` to pass the calibration payload into `simulate_forward_once`, keep diagnostics up to date, and fail loudly if metadata is missing.
6. DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T190000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1 | tee plans/active/MAP-SCALE-001/reports/2025-11-04T190000Z/pytest_db_at_024.log
7. jq -r '.corr_median, .localization_success_rate, .calibration.spot_scale_override' plans/active/MAP-SCALE-001/reports/2025-11-04T190000Z/mapping_metrics.json > plans/active/MAP-SCALE-001/reports/2025-11-04T190000Z/mapping_metrics_summary.txt
Pitfalls To Avoid:
- Do not pre-scale structure factors—SCALE-001 mandates they stay unscaled; apply √spot_scale only after simulation.
- Preserve SCALE-002 semantics: a single post-sim global scale, no duplicate spot_scale multiplication.
- Keep calibration parsing tolerant but strict: raise useful errors if config_torch.json lacks flux/exposure/N_cells instead of silently defaulting.
- Maintain device neutrality in bridge helpers; avoid hard-coding CUDA or mixing torch/numpy without .to(device).
- Ensure trusted mask tensors remain float32 (0/1) when passed into DetectorConfig; no boolean tensors to dodge torch matmul issues.
- Capture pytest output via tee to populate the new report directory; missing logs break artifact expectations.
- Leave Environment Freeze intact—no package installs or conda tweaks while adjusting the bridge.
- Double-check ROI metrics after the run; median corr must be ≥0.2 and localization ≥0.90 before marking success.
If Blocked:
- Record failing metrics/logs under plans/active/MAP-SCALE-001/reports/2025-11-04T190000Z/, summarize the calibration values and error in docs/fix_plan.md Attempts History, and flag Galph with the assertion text.
Findings Applied (Mandatory):
- SCALE-001 — Bridge must leave |F| amplitudes unscaled until after nanobrag_torch completes.
- SCALE-002 — √spot_scale_override comes from DiffBragg metadata and is applied once post-sim.
- SCALE-003 — Zero-iteration helper must ingest refined DiffBragg calibration data for intensity parity.
- SCALE-004 — Use refined geometry plus refined structure factors together; plan keeps those fixtures in play.
- TESTING-003 — Maintain selector/docs sync after DB_AT_024 metrics change (update TESTING_GUIDE + INDEX once passing).
Pointers:
- docs/spec-db-conformance.md:43-46 — Mapping thresholds and acceptance wording.
- docs/architecture.md:82-109 — Bridge responsibilities and calibration surfaces.
- docs/nanobrag_api.md:18-67 — Required fields for nanobrag_torch configs (beam/crystal/detector).
- docs/development/testing_strategy.md:24-34 — Guidance for parity selectors + artifact expectations.
- plans/active/MAP-SCALE-001/reports/2025-11-04T175020Z/summary.md — Latest analysis proving missing flux/N_cells cause the divergence.
Next Up (optional):
- If DB_AT_024 passes quickly, capture a follow-up probe comparing simulate_forward_once output to canonical `bragg_torch.npy` to confirm correlation ≥0.8 and attach the delta plot.
