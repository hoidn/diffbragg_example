Summary: Auto-adjust spot_scale when `N_cells` is suppressed so the mapping zero-iteration stack matches the masked data scale before rerunning DB-AT-028/029.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/

Do Now (hard validity contract)
- Implement: dbex/vis/mapping.py::build_mapping_stage_a_context — when `apply_calibration_n_cells=False` and diagnostics show an extreme `target_bragg_mean_ratio`, clone the calibration dict, multiply `spot_scale_override` by `(target/bragg)^2`, re-run `simulate_forward_once` with the adjusted calibration, and record telemetry fields (e.g., `spot_scale_override_adjustment_factor`, `calibration_adjusted_for_n_cells`). Ensure the updated calibration dict is stored on the returned MappingStageAContext so Stage A uses the corrected scale.
- Validate: pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" under the canonical metadata env with DBAT artifact dirs pointed at the new report directory; failures are acceptable but telemetry must reflect `n_cells_applied=false`, positive ROI CC, and the scale adjustment fields.

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json
3. mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/mapping_dataset_metrics
4. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
   python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py \
   --cases metadata_raw metadata_calibrated metadata_calibrated_drop_ncells metadata_calibrated_spot1 metadata_calibrated_spot1_drop_ncells \
   --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/mapping_dataset_metrics \
   --device cpu --emit-roi-artifacts --roi-count 16 \
   | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/mapping_dataset_metrics/probe.log
5. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
   DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/db_at_028 \
   DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/db_at_029 \
   pytest --collect-only -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
   | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/pytest_db_at_028_029_collect.log
6. Repeat the pytest command without --collect-only, teeing output to plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/pytest_db_at_028_029.log (failures expected; ensure artifacts persist).

Pitfalls To Avoid
- Clone the calibration dict before mutating `spot_scale_override`; never modify the on-disk config.
- Guard the resimulation with a finite/high ratio threshold (e.g., >1e3) so typical runs do not re-run `simulate_forward_once`.
- Keep `apply_calibration_n_cells` set to False for the second pass so we do not reintroduce the oversampling behavior.
- Emit adjustment metadata as plain floats/booleans so downstream JSON serialisation (mapping probes, DB-AT fixtures) stays stable.
- Do not delete or overwrite earlier evidence; keep all new outputs under the 2025-11-25T235500Z directory.

If Blocked
- If the re-run logic raises or cannot import `nanobrag_torch`, log the full traceback to `plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/block.log`, update docs/fix_plan.md with the blocker signature, and halt before editing calibration assets.
- If pytest aborts before assertions (e.g., missing env vars), capture the error in block.log, archive whatever artifacts exist, and notify the supervisor instead of attempting environment changes.

Findings Applied (Mandatory)
- STAGEA-001 — telemetry for HKL/calibration must remain accurate even when we mutate spot scale.
- SCALE-004 — refined MTZ + calibration pairing is mandatory; only adjust the scalar intensity term.
- SCALE-005 — keep `n_cells_applied`/suppression_reason telemetry intact to audit the guard.

Pointers
- docs/data_dependency_manifest.md:34 — canonical smoke fixture calibration/HKL defaults and telemetry requirements.
- docs/spec-db-conformance.md:315 — DB‑AT‑028/029 acceptance criteria (chi²/pixel ≤1e2, ROI CC ≥0.2) for interpreting test output.
- dbex/vis/mapping.py:130-240 — current build_mapping_stage_a_context implementation where the scale adjustment must be inserted.

Next Up (optional)
- If the scale adjustment yields positive ROI CC with realistic amplitudes, plan a follow-up loop to evaluate whether Stage A refinement (with engine delegation) now improves DB-AT-028/029 chi²/pixel instead of plateauing.
