Summary: Isolate which DiffBragg calibration field is flipping Stage-A ROI correlations negative by extending the dataset-metrics probe with calibration variants and rerunning DB-AT-028/029 under the metadata env.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T133505Z/

Do Now:
- Implement: plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py::compute_case_metrics — add calibration_variant handling (define_cases/build_dataload_for_case/materialization helpers) so cases can rewrite config_torch_smoke.json into per-variant copies (spot_scale forced to 1, optional N_cells removal) stored under the report dir before building the DataLoad, and propagate the derived calibration path/spot_scale into the metrics JSON/log output.
- Validate: `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` under the canonical metadata env so both selectors archive telemetry while the new probe evidence lives beside the refreshed failure signatures (failures expected on chi²/ROI gates).

How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T133505Z DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` and `mkdir -p "$REPORT"/{calibration_variants,mapping_dataset_metrics,db_at_028,db_at_029}`.
2. After updating the probe, run `python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py --cases metadata_raw metadata_calibrated metadata_calibrated_spot1 metadata_calibrated_spot1_drop_ncells --emit-roi-artifacts --roi-count 16 --default-sigma 3.0 --device cuda:0 --out-dir "$REPORT"/mapping_dataset_metrics | tee "$REPORT"/mapping_dataset_metrics/probe.log`; confirm stdout lists each derived calibration path and spot_scale_override.
3. Export DB-AT artifact env: `export DBAT028_ARTIFACT_DIR="$REPORT"/db_at_028 DBAT029_ARTIFACT_DIR="$REPORT"/db_at_029`.
4. `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029_collect.log`.
5. `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029.log`; failures are fine if telemetry for calibration variant + HKL path + sigma provenance is captured in both `mapping_context_fixture.json` files.

Pitfalls To Avoid:
- Keep variant files scoped to `$REPORT/calibration_variants` so git stays clean and prior loops’ configs are not reused accidentally.
- Do not relax the override precedence—explicit env vars must still beat any auto-resolved calibration/HKL.
- Validation runs remain evidence-only; do not try to “fix” chi²/ROI gates within the tests this loop.
- Ensure ROI artifact emission reflects the new cases; missing PNG/NPZ bundles make it impossible to inspect divergence visually.
- Avoid mutating production calibration configs; always write derived JSON copies for spot_scale/N_cells experiments.
- Maintain deterministic logging so follow-up analysis can diff metrics across cases.

If Blocked:
- If the probe cannot materialize a variant (e.g., JSON schema or file-permission issue), log the stack trace to `$REPORT/mapping_dataset_metrics/probe.log`, stop, and record the blocker in docs/fix_plan.md + summary.md.
- If pytest selectors stop collecting, capture `pytest_db_at_028_029_collect.log`, triage briefly, and if unresolved mark TOOLING-VIS-001 blocked with the failure signature; do not revert probe changes.

Findings Applied (Mandatory):
- STAGEA-001 — Stage A/mapping tooling must consume identical calibration/HKL provenance before judging physics metrics; variant sweep guards that invariant.
- SCALE-004 — Refined structure factors must pair with the calibration metadata, so every new case still resolves the refined MTZ unless an explicit override is set.
- SCALE-005 — Calibration provenance must stay auditable; emit the derived calibration path/spot_scale per case so telemetry proves which bundle was used.

Pointers:
- docs/data_dependency_manifest.md:34-102 — canonical smoke fixture inputs and override precedence to mirror while adding calibration variants.
- docs/architecture/calibration_scaling.md:1-120 — explains how spot_scale, N_cells, and beam metadata are expected to influence simulate_forward_once.
- plans/active/TOOLING-VIS-001/implementation.md:1-200 — initiative goals and Phase D acceptance gates for DB-AT-027/028/029 that this evidence feeds.
- docs/fix_plan.md:330-380 — latest TOOLING-VIS-001 attempts plus today’s calibration-variant plan for traceability.

Next Up (optional):
- If forcing spot_scale to 1 immediately restores positive ROI CC, follow up with a Stage A/calibration scaling bugfix plan (either sanitize capture output or adjust simulate_forward_once scaling) before re-running the selectors.
