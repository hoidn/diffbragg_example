Summary: Override the Stage A log-scale baseline when mapping auto-adjusts spot_scale so zero-iteration intensities stay aligned before re-running DB-AT-028/029.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T003000Z/

Do Now (hard validity contract)
- Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — add a mapping-aware log-scale baseline override (fed via RefinementConfig and RefinementInputs.global_scale_hint) that takes precedence whenever `diagnostics["calibration_adjusted_for_n_cells"]` is true so Stage A no longer re-applies the auto-adjusted `spot_scale_override`; record telemetry fields (e.g., `log_scale_baseline_source`, `spot_scale_override_adjustment_factor`) to prove when the override is active.
- Implement: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result — when the mapping diagnostics flag `calibration_adjusted_for_n_cells`, clone the calibration payload passed to Stage A, set the new log-scale override flag/value on RefinementConfig, and persist the newly emitted telemetry (log-scale source, masked scale ratios) into `db_at_028/db_at_029` metrics so artifacts show Stage A matching the mapping stack.
- Validate: pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" (first `--collect-only`, then full run) under the canonical metadata env; failures on chi²/ROI gates are acceptable but artifacts must show `scale_ratio_before≈scale_ratio_mapping_masked≈1` and the new telemetry fields proving the override engaged.

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json
3. mkdir -p plans/active/TOOLING-VIS-001/reports/2025-11-26T003000Z/{mapping_dataset_metrics,db_at_028,db_at_029}
4. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 \
   DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
   python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py \
   --cases metadata_raw metadata_calibrated metadata_calibrated_drop_ncells --device cpu --emit-roi-artifacts --roi-count 16 \
   --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-26T003000Z/mapping_dataset_metrics \
   | tee plans/active/TOOLING-VIS-001/reports/2025-11-26T003000Z/mapping_dataset_metrics/probe.log
5. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 \
   DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
   DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T003000Z/db_at_028 \
   DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T003000Z/db_at_029 \
   pytest --collect-only -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
   | tee plans/active/TOOLING-VIS-001/reports/2025-11-26T003000Z/pytest_db_at_028_029_collect.log
6. Repeat the pytest command without --collect-only, teeing output to plans/active/TOOLING-VIS-001/reports/2025-11-26T003000Z/pytest_db_at_028_029.log (failures expected; ensure db_at_* metrics/mapping_context fixtures persist the new telemetry fields).

Pitfalls To Avoid
- Do not mutate the on-disk calibration JSON; clone dicts before adjusting spot scale or log-scale metadata.
- Keep the override guard keyed to `diagnostics["calibration_adjusted_for_n_cells"]` so standard runs still use DiffBragg’s log-scale baseline.
- Guard against missing/zero `global_scale_hint` by falling back to the calibrated baseline; log which source was selected.
- Maintain telemetry schema stability (plain floats/bools) so downstream tooling can diff JSONs without schema changes.
- Ensure the new RefinementConfig flag is device/dtype agnostic and works for both CPU/GPU.
- Avoid suppressing the existing `n_cells_applied` diagnostics when wiring the override.
- Preserve Stage A warm-cache performance by avoiding per-iteration clones or conversions in the hot path.
- Keep compare_mapping_dataset_metrics output unchanged aside from additional telemetry fields so historical diffs stay meaningful.

If Blocked
- If the new override causes Stage A to crash before telemetry writes, capture the traceback to plans/active/TOOLING-VIS-001/reports/2025-11-26T003000Z/block.log, update docs/fix_plan.md with the failure signature, and stop before attempting alternate fixes.
- If pytest cannot import modified modules due to environment/library errors, log the error text to block.log and notify the supervisor instead of modifying the environment.

Findings Applied (Mandatory)
- STAGEA-001 — Stage A must reuse mapping calibration payloads; new override cannot break canonical log-scale plumbing.
- SCALE-004 — Refined MTZ + calibration pairing remains mandatory; override only touches log-scale baseline, not HKL provenance.
- SCALE-005 — Detector-size-specific calibration (small bundle, N_cells handling) stays intact; override is conditional on that gate.
- SCALE-008 — Newly logged finding mandates avoiding double application of the adjusted spot-scale when N_cells suppression is active.

Pointers
- docs/spec-db-conformance.md:287 — DB-AT-028/029 acceptance thresholds and telemetry expectations for log-scale/ROI evidence.
- docs/data_dependency_manifest.md:34 — Canonical smoke asset defaults and telemetry fields that must remain accurate.
- dbex/nanobrag_refinement.py:2460 — Current log-scale baseline selection logic to be extended with the mapping-aware override.
- plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/db_at_029/db_at_029_metrics.json — Evidence of the double-scaled Stage A baseline guiding this fix.

Next Up (optional)
- If the override lands cleanly and Stage A now matches the mapping stack, plan a follow-up loop to inspect the remaining Stage A chi² trace (chi²/pixel≈1.5e5) and decide whether the residual failure is pure physics vs gradient/tolerance.
