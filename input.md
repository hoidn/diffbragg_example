Summary: Toggle sigma-map sources inside the mapping dataset probe so we can see whether metadata tiles are the reason calibrated runs stay anti-correlated before touching Stage A physics.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T200500Z/

Do Now:
- Implement: plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py::{define_cases,build_dataload_for_case,compute_case_metrics,main} — add sigma_source-aware presets (metadata_* plus cli_*), ensure cli cases drop the metadata sigma-map, and persist the resolved sigma_source in the metrics JSON/log output.
- Validate: With AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T200500Z DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1, run the updated probe for `metadata_raw metadata_calibrated cli_raw cli_calibrated` with ROI artifact emission (tee logs/JSON under $REPORT/mapping_dataset_metrics/), then rerun `pytest --collect-only` and `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` capturing collect-only + runtime logs even though assertions still fail.

How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T200500Z DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` and `mkdir -p "$REPORT"/mapping_dataset_metrics`.
2. Update `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py` per the Implement bullet: add `cli_raw`/`cli_calibrated` cases, wire `sigma_source` through define_cases → build_dataload_for_case → compute_case_metrics, skip sigma_map usage whenever `sigma_source="cli_override"`, and include the sigma source in printed/logged metrics.
3. `python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py --cases metadata_raw metadata_calibrated cli_raw cli_calibrated --emit-roi-artifacts --roi-count 16 --default-sigma 3.0 --device cuda:0 --out-dir "$REPORT"/mapping_dataset_metrics | tee "$REPORT"/mapping_dataset_metrics/probe.log`.
4. Inspect `$REPORT/mapping_dataset_metrics/mapping_dataset_metrics.json` plus the per-case ROI artifacts to confirm both metadata and cli cases logged their sigma sources, HKL provenance, and ROI CCs.
5. `export DBAT028_ARTIFACT_DIR="$REPORT"/db_at_028 DBAT029_ARTIFACT_DIR="$REPORT"/db_at_029` then `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029_collect.log`.
6. `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029.log`; leave the failures in place but ensure metrics JSON + mapping_context fixtures land under the artifact dirs.

Pitfalls To Avoid:
- Do not let the new cli_* cases accidentally load the metadata sigma-map; `build_dataload_for_case` must drop sigma_map when sigma_source="cli_override".
- Keep the existing metadata_* cases intact so older selectors/scripts stay compatible; add aliases if you rename case keys.
- Preserve ROI artifact generation semantics (loss-mask slices only) so the report directory doesn’t explode with full-frame dumps.
- Record the resolved sigma_source in both stdout and `mapping_dataset_metrics.json`; downstream loops need that telemetry without re-running the probe.
- Don’t alter Stage A production fixtures in this loop; the point is evidence only.
- Continue to export canonical metadata env vars before running pytest so DB-AT-028/029 keep the known failure signature.
- Capture probe/pytest logs even on failure; never delete prior artifacts from the reports tree.
- If CUDA is unavailable, rerun the probe on CPU but note the device change in the report summary.

If Blocked:
- If the probe crashes (e.g., KeyError from new case definitions), archive the stack trace in `$REPORT/mapping_dataset_metrics/probe.log`, note the failure in summary.md, update docs/fix_plan.md Attempts History with the blocker, and stop before pytest.
- If pytest cannot collect DB-AT-028/029 (import error, fixture setup failure), save the collect-only log, describe the error in summary.md, and mark TOOLING-VIS-001 blocked pending fixture repair.

Findings Applied (Mandatory):
- STAGEA-001 — Mapping and Stage A diagnostics must share calibrated inputs; comparing metadata vs cli sigma cases keeps provenance explicit.
- SCALE-004 — Calibration metadata and HKL provenance need to stay coupled; each probe case still records the HKL path/count alongside the sigma source.
- SCALE-005 — Sigma ladder transparency is required; emitting the sigma_source + sigma_map_path in metrics JSON ensures the ladder remains auditable.

Pointers:
- plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py:1-380 — probe implementation to update with sigma-source aware cases.
- tests/conftest.py:80-260 — reference for how smoke fixtures currently resolve sigma maps and calibration inputs.
- docs/data_dependency_manifest.md:1-180 — canonical mapping of DBEX_SMOKE_* env vars and sigma/calibration assets.
- docs/TESTING_GUIDE.md:130-190 — DB-AT-028/029 env requirements and artifact expectations.

Next Up (optional):
- If CLI sigma restores positive ROI CC while metadata remains negative, plan the follow-up loop around repairing the metadata sigma capture/cropping path; otherwise pivot to HKL/calibration alignment.
