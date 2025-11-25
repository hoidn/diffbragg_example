Summary: Quantify how suppressing DiffBragg N_cells impacts Stage A amplitudes by extending the dataset probe with a drop-ncells case and capturing refreshed DB-AT-028/029 telemetry under the canonical metadata env.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T230500Z/

Do Now (hard validity contract)
- Implement: plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py::define_cases — add a metadata_calibrated_drop_ncells case (drop N_cells, retain spot_scale_override) and propagate n_cells_applied/n_cells_suppression_reason plus masked/unmasked target/model means into compute_case_metrics so every case records the calibrated amplitude context; rerun the probe for metadata_raw, metadata_calibrated, metadata_calibrated_drop_ncells, metadata_calibrated_spot1, and metadata_calibrated_spot1_drop_ncells with ROI artifacts under the new reports directory.
- Validate: pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" with the canonical metadata env/exported DBAT artifact dirs so DB-AT-028/029 logs in the same report directory capture the updated telemetry (failures on chi²/ROI gates remain acceptable but must match the selector signatures).

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json
3. mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-25T230500Z/mapping_dataset_metrics
4. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
   python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py \
   --cases metadata_raw metadata_calibrated metadata_calibrated_drop_ncells metadata_calibrated_spot1 metadata_calibrated_spot1_drop_ncells \
   --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T230500Z/mapping_dataset_metrics \
   --device cpu --emit-roi-artifacts --roi-count 16 \
   | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T230500Z/mapping_dataset_metrics/probe.log
5. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
   DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T230500Z/db_at_028 \
   DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T230500Z/db_at_029 \
   pytest --collect-only -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
   | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T230500Z/pytest_db_at_028_029_collect.log
6. Repeat the pytest command without --collect-only, teeing output to plans/active/TOOLING-VIS-001/reports/2025-11-25T230500Z/pytest_db_at_028_029.log (failures expected; ensure artifacts persist).

Pitfalls To Avoid
- Do not overwrite sp.proc calibration files; materialize drop-ncells variants under the report directory.
- Keep apply_calibration_n_cells default True for non _drop_ncells cases so DB-AT-024 behavior remains unchanged.
- Ensure new metrics fields are JSON-serializable floats (no numpy dtypes) to keep downstream diffs clean.
- Run the probe on CPU with NANOBRAG_DISABLE_COMPILE=1 to avoid CUDA allocator churn documented in POLICY-001.
- Preserve existing ROI artifact emission layout; only add the new case directories.
- Use tee when running commands so stdout is captured under the artifacts path for supervisor review.
- Don’t delete prior artifacts in plans/active/TOOLING-VIS-001/reports/; add new files only under the 2025-11-25T230500Z directory.

If Blocked
- If compare_mapping_dataset_metrics.py fails to build a case because a variant config is missing, capture the traceback in plans/active/TOOLING-VIS-001/reports/2025-11-25T230500Z/block.log, note the missing asset in docs/fix_plan.md Attempts History, and stop before touching pytest.
- If pytest cannot import nanobrag_torch or another dependency, record the error text verbatim in block.log, mark TOOLING-VIS-001 blocked in docs/fix_plan.md, and notify the supervisor instead of attempting environment changes.

Findings Applied (Mandatory)
- STAGEA-001 — ensure calibration/HKL telemetry stays in every artifact while modifying the probe.
- SCALE-004 — keep spot_scale_override handling identical when materializing variants so amplitude comparisons remain meaningful.
- SCALE-005 — record whether N_cells was applied or suppressed in the new metrics fields to audit the SCALE-005 guard.

Pointers
- docs/data_dependency_manifest.md:34 — canonical smoke fixture calibration/HKL defaults and telemetry requirements.
- docs/spec-db-conformance.md:315 — DB‑AT‑028/029 acceptance criteria (chi²/pixel ≤1e2, ROI CC ≥0.2) the selectors enforce.
- plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py:302 — current calibration variant cases to mirror when adding metadata_calibrated_drop_ncells.

Next Up (optional)
- Once amplitude deltas are quantified, consider adding a compensating scale factor or re-fitting spot_scale_override for the small-detector calibration so DB-AT-028/029 can regain magnitude without re-enabling N_cells.
