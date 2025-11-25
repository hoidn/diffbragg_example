Summary: Capture raw vs calibrated ROI evidence inside the dataset-comparison probe so we can quantify how calibration alters Stage A inputs before re-running the failing smoke selectors.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T190500Z/
Do Now:
- Implement: plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py::{define_cases,compute_case_metrics,main} — add an explicit `scaled_raw` case (calibration disabled) alongside the calibrated presets, plumb `hkl_telemetry`/sigma provenance into the metrics, and add an `--emit-roi-artifacts/--roi-count` option that writes per-case ROI stacks (data/model/residual PNG+NPZ) so we can inspect how raw vs calibrated contexts differ.
- Validate: With AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T190500Z DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1, run the probe for `scaled_raw scaled_calibrated refined_calibrated` with ROI artifact emission (capture probe.log + JSON/NPZ under mapping_dataset_metrics/), then rerun `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` capturing collect-only + test logs even though assertions still fail.
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T190500Z DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`.
2. Update `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py` per the Implement bullet: add the raw case definitions, surface `diagnostics["hkl_telemetry"]` + `dataload.sigma_readout_map_source`, and wire the new ROI artifact emission flag that saves PNG/NPZ under `$REPORT/mapping_dataset_metrics/<case>/roi_diagnostics`.
3. `python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py --cases scaled_raw scaled_calibrated refined_calibrated --emit-roi-artifacts --roi-count 16 --out-dir "$REPORT"/mapping_dataset_metrics --device cuda:0 --default-sigma 3.0 | tee "$REPORT"/mapping_dataset_metrics/probe.log`.
4. Inspect `$REPORT/mapping_dataset_metrics/` (JSON and ROI artifacts) to confirm each case logs `hkl_source`, `sigma_provenance`, and that both raw vs calibrated ROI stacks were emitted.
5. `export DBAT028_ARTIFACT_DIR="$REPORT"/db_at_028 DBAT029_ARTIFACT_DIR="$REPORT"/db_at_029`.
6. Guardrail: `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029_collect.log`.
7. `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029.log`; expected FAIL, but metrics JSONs + fixtures must land under `$REPORT`.
Pitfalls To Avoid:
- Keep the new raw/calibrated case logic scoped to the probe; do not touch production `tests/conftest.py` plumbing.
- Preserve existing CLI defaults and backward compatibility for callers that only request the legacy cases.
- Ensure ROI artifact emission respects the existing loss mask; do not emit gigantic unmasked stacks that bloat artifacts.
- Fill `hkl_source`/`hkl_path` from `diagnostics["hkl_telemetry"]` so metadata stays accurate even when top-level keys are missing.
- Do not mutate repo datasets; ROI artifacts live only under the report directory.
- Use the same canonical metadata env for both the probe and pytest run so metrics remain comparable.
- Capture logs/JSON even when commands fail; never delete previous artifacts from other runs.
- Respect Environment Freeze (no new dependencies, no `pip install`).
- Guard for CUDA absence (fallback to CPU) but still note the device in metrics.
- Keep new CLI params documented in the script help text for future loops.
If Blocked:
- If the probe crashes (missing case definition, CLI parsing failure, DataLoad error), save the full stack trace to `$REPORT/mapping_dataset_metrics/probe.log`, record the failure signature in docs/fix_plan.md and `$REPORT/summary.md`, then stop before pytest.
- If pytest cannot collect the DB-AT selectors, archive the collect-only log, capture the error in summary.md, and mark the initiative blocked pending fixture repair.
Findings Applied (Mandatory):
- STAGEA-001 — Mapping/Stage A evidence must share calibrated inputs; emitting paired ROI stacks ensures we can inspect the exact deltas.
- SCALE-004 — Calibration metadata and HKL provenance must stay explicit; the new metrics/telemetry fields enforce this pairing.
- SCALE-005 — Sigma-map provenance needs to be traceable; logging the map source alongside ROI artifacts keeps sigma ladder compliance visible.
- CONFORMANCE-001 — DB-AT selectors must still run and log artifacts even on failure; pytest steps remain mandatory despite expected FAIL.
Pointers:
- plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py:1-360 — probe implementation to extend with the new case + ROI artifact logic.
- plans/active/TOOLING-VIS-001/bin/probe_mapping_roi_triptychs.py:1-300 — reference for how ROI triptychs and NPZ payloads are currently structured.
- tests/conftest.py:70-240 — canonical smoke dataset + calibration/sigma wiring that the probe must mirror.
- docs/data_dependency_manifest.md:1-140 — authoritative env/asset mapping for Stage A helpers to keep the probe aligned with reality.
- docs/TESTING_GUIDE.md:136-166 — DB-AT-028/029 selector expectations and env variables.
Next Up (optional): If the raw vs calibrated ROI evidence isolates a specific structural inversion, plan a follow-up loop to trace the offending callchain (e.g., run prompts/callchain.md on `simulate_forward_once` and the calibration loader).
