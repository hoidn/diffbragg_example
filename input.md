Summary: Align the mapping dataset comparison probe with the canonical Stage A fixture so geometry/sigma overrides match reality before diagnosing the DB-AT-028/029 chi² gap.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T180500Z/
Do Now:
- Implement: plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py::{define_cases,build_dataload_for_case} — mirror tests/conftest.py’s canonical geometry + sigma_map logic (DBEX_SMOKE_GEOM_PATH/DBEX_SMOKE_SIGMA_MAP_PATH/DBEX_SMOKE_CALIB_PATH) so metadata cases reuse refGeom assets, pass sigma_map into DataLoad.args, and keep HKL/calibration overrides per case instead of swapping to idx-0000_sigma_metadata.expt.
- Validate: Re-run the probe under the canonical metadata env (AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T180500Z DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1) and capture mapping_dataset_metrics.json, then run `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with DBAT artifact dirs rooted at the same report path so telemetry stays in sync even if assertions still fail.
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T180500Z DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`.
2. Edit `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py`: reuse the canonical geometry resolution from tests/conftest (DBEX_SMOKE_GEOM_PATH fallback to refGeom_small/refGeom), plumb sigma_map_path into DataLoad args when DBEX_SMOKE_SIGMA_SOURCE=metadata, and keep HKL/calibration overrides per case without swapping experiments.
3. `python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py --cases metadata_scaled metadata_refined --out-dir "$REPORT"/mapping_dataset_metrics --device cuda:0 --default-sigma 3.0 | tee "$REPORT"/mapping_dataset_metrics/probe.log`.
4. Sanity-check `$REPORT/mapping_dataset_metrics/mapping_dataset_metrics.json` to confirm both cases log the canonical geometry path, sigma_map provenance, and updated scale ratios.
5. `export DBAT028_ARTIFACT_DIR="$REPORT"/db_at_028 DBAT029_ARTIFACT_DIR="$REPORT"/db_at_029`.
6. Guardrail: `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029_collect.log`.
7. `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029.log` and highlight that failures on chi²/ROI tolerances are expected but logs/metrics must be archived.
Pitfalls To Avoid:
- Do not revert the canonical geometry override logic in tests/fixtures; only the probe should change.
- Keep the sigma-map plumbing identical to refgeom_dataload (metadata cases should no longer swap experiments).
- Preserve MTZ column detection so refined structure factors still load via F(+)/SIGF(+).
- Ensure DataLoad args restore their original values between cases if you refactor helper code to avoid cross-case state leaks.
- Avoid introducing new dependencies; use existing dbex/data_load & mapping helpers only.
- Capture probe + pytest logs under the new $REPORT path even if assertions fail.
- Do not delete prior artifacts; append this run’s JSON/logs for comparison.
- Keep device/dtype neutral; default to cuda only if available but tolerate CPU fallback.
- Respect Environment Freeze (no pip installs, no dataset mutations beyond plan-local scripts).
- When editing the script, retain docstrings/usage so future loops can reference the new behavior.
If Blocked:
- If DataLoad raises due to missing sigma_map or geometry, capture the stack trace in `$REPORT/mapping_dataset_metrics/probe.log`, describe the missing asset in docs/fix_plan.md, and halt before running pytest.
- If pytest cannot collect the DB-AT selectors, archive the collect-only log, note the failure signature in `$REPORT/summary.md`, and mark the focus blocked pending fixture repair.
Findings Applied (Mandatory):
- STAGEA-001 — Mapping/Stage A diagnostics must share the same calibrated inputs; updating the probe keeps evidence aligned with the canonical refGeom fixture.
- SCALE-004 — Calibration metadata must pair with the intended HKL asset; keeping the probe’s HKL/calibration overrides explicit enforces this contract.
- SCALE-005 — Sigma-map provenance and ladder ordering must match the fixture; threading DBEX_SMOKE_SIGMA_MAP_PATH prevents silent fallbacks to scalars.
- CONFORMANCE-001 — Even on failure, DB-AT selectors must run and log artifacts under the report directory; the plan’s validate steps preserve this guard.
Pointers:
- plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py:1-320 — probe to modify so dataset comparisons reflect canonical geometry/sigma plumbing.
- tests/conftest.py:70-210 — canonical smoke_dataset_paths + refgeom_dataload logic to mirror (geometry + sigma + calibration overrides).
- docs/data_dependency_manifest.md:1-140 — authoritative env overrides for mapping/smoke helpers that the probe must honor.
- docs/TESTING_GUIDE.md:136-166 — DB-AT-028/029 selector instructions and required env exports.
- docs/spec-db-conformance.md:287-349 — DB-AT-028 (loss-scale sanity) and DB-AT-029 (structure parity) acceptance criteria driving this focus.
Next Up (optional): If the refreshed probe confirms calibrated vs raw discrepancies with canonical geometry, plan the follow-up loop to map Stage A’s calibration scaling (e.g., compare spot_scale_override vs global_scale_hint deltas) and scope the code changes needed to tame the chi² spike.
