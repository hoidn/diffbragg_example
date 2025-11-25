Summary: Fix the scale-chain probe so calibrated permutations actually pass `calibration_config_path`, then rerun the probe and DB-AT-028/029 to capture trustworthy telemetry for the metadata smoke dataset.
Mode: none
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T114730Z/
Do Now:
- Implement: plans/active/TOOLING-VIS-001/bin/probe_scale_chain.py::compute_case_metrics — stop zeroing `dataload.args.calibration_config_path` for calibrated permutations (plumb the resolved path into the helper or accept it as a new argument) so `build_mapping_stage_a_context` loads `sp.proc/calibration/config_torch_smoke.json`; assert the resulting metrics JSON shows `calibration_path` and `spot_scale_override≈3.1e17` for calibrated cases while the raw case stays at 1.0.
- Validate: `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with the canonical metadata env after rerunning the probe so the refreshed `mapping_context_fixture.json` files and DB-AT metrics confirm calibrated telemetry is recorded even if the selectors still fail on chi²/ROI thresholds.
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T114730Z DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` (reuse the same block for both probe + pytest so telemetry lines up).
2. Edit `probe_scale_chain.py`: add a `calibration_path` parameter to `compute_case_metrics()` (or reuse the resolved string from `main()`), delete the unconditional assignment to `dataload.args.calibration_config_path = None`, and ensure calibrated cases set the attribute before calling `build_mapping_stage_a_context`. Retain the context restore logic in the `finally` block.
3. Re-run the CLI: `python plans/active/TOOLING-VIS-001/bin/probe_scale_chain.py --cases scaled_raw,scaled_calibrated,refined_calibrated --device cuda:0 --out-dir "$REPORT"/scale_chain_probe 2>&1 | tee "$REPORT"/scale_chain_probe/probe.log`.
4. Inspect `$REPORT/scale_chain_probe/scale_chain_metrics.json`: calibrated cases must show `calibration_path` pointing at the smoke config, `spot_scale_override≈3.1e17`, and non-zero `diff_block` deltas relative to the raw case; include the JSON in the artifacts even if ROI CC stays negative.
5. `export DBAT028_ARTIFACT_DIR="$REPORT"/db_at_028 DBAT029_ARTIFACT_DIR="$REPORT"/db_at_029`.
6. Guardrail: `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029_collect.log` (abort if either selector stops collecting.)
7. `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029.log` — ensure the refreshed `mapping_context_fixture.json` files echo the calibrated telemetry; failures on chi²/ROI thresholds are expected and should be archived verbatim.
8. Summarize probe deltas (raw vs calibrated spot-scale/scale ratios) plus current DB-AT failure signatures in `$REPORT/summary.md` and update docs/fix_plan.md Attempts History with this timestamped directory.
Pitfalls To Avoid:
- Do not touch production modules (`dbex/*`) in this loop; only the plan-local probe needs surgery.
- Preserve the `finally` block in `compute_case_metrics()` so `dataload.args` always return to their original values between permutations.
- Keep all three permutations targeting the metadata smoke dataset; avoid flipping to golden fixtures or cli_override sigma, or evidence becomes incomparable.
- When inspecting the JSON, differentiate masked vs unmasked metrics—the spec gates use the masked values (`scale_ratio_masked`, `roi_cc_median`).
- Ensure environment exports match the pytest fixtures (cropped sigma map, metadata calibration, scaled.mtz) so telemetry lines up with DB-AT logs.
- Capture both probe output and pytest logs even if nothing improves; CONFORMANCE-001 requires artifacts on failure.
If Blocked:
- If the probe still reports `spot_scale_override=1.0`, capture the JSON + stdout, note the failure reason in docs/fix_plan.md and `$REPORT/summary.md`, then stop — do not hand-wave the calibrated metrics.
- If pytest raises (not just fails assertions), save the traceback in `$REPORT/pytest_db_at_028_029.log`, set the focus to blocked in docs/fix_plan.md, and drop me a note explaining whether env resolution or code fix is required.
Findings Applied (Mandatory):
- STAGEA-001 — Mapping and Stage A diagnostics must share calibrated HKL/calibration assets; this fix ensures the probe reflects that contract.
- SCALE-004 — Refined calibration metadata pairs with the smoke MTZ; the probe must show spot-scale deltas when calibration is enabled.
- SCALE-005 — Masked vs unmasked scale ratios need to be reported explicitly; keep both fields intact after touching the probe.
Pointers:
- plans/active/TOOLING-VIS-001/bin/probe_scale_chain.py:72-150 (permutation plumbing & calibration handling).
- dbex/vis/mapping.py:144-210 (how `build_mapping_stage_a_context` consumes `calibration_config_path`).
- docs/data_dependency_manifest.md:78-110 (smoke calibration/HKL/sigma override contracts you must continue to honor).
- plans/active/TOOLING-VIS-001/reports/2025-11-25T170500Z/scale_chain_probe/scale_chain_metrics.json (baseline showing the calibration failure signature).
- docs/TESTING_GUIDE.md:136-166 (DB-AT-028/029 env requirements and artifact expectations).
Next Up (optional):
- After the probe telemetry is trustworthy, re-run the full geometry/scale analysis to isolate the physics root cause for the negative ROI correlations.
