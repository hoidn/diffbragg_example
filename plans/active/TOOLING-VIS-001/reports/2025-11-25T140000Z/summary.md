### Turn Summary
Wired calibration_config_path through refgeom_dataload fixture; Stage A mapping diagnostics now record smoke calibration (sp.proc/calibration/config_torch_smoke.json) and spot_scale_override (3.1e+17).
DB-AT-028/029 selectors executed with metadata env and archived mapping_context_fixture.json showing correct calibration wiring; tests failed on chi²/pixel thresholds as expected (signatures unchanged from prior loops).
Identified pre-existing sigma provenance bug: _select_sigma_readout rejects "cli_map" source so metadata sigma tiles are ignored despite being loaded by DataLoad; mapping uses default scalar instead.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T140000Z/ (pytest_db_at_028_029.log, mapping_context_fixture.json for both selectors, check_calibration_path.log)
