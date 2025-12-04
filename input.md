Summary: Scale the mapping zero-iteration stack by the same masked-intensity ratio that Stage A now applies so Stage A and mapping baselines land on identical magnitudes before re-running the Stage A probe + DB-AT-028/029 evidence.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --device cuda:0 --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T180000Z/stage_a_baseline_probe_baseline.json
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T180000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T180000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T180000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T180000Z/

Do Now:
- Implement: `dbex/vis/mapping.py::build_mapping_stage_a_context` — after `simulate_forward_once` returns, compute the masked means of `inputs.target` and `bragg_zero_iter`, multiply the Bragg stack by `mean_target/mean_bragg` when both values are finite/positive, and persist the masked means, ratio, and a `log_scale_baseline_source` hint in `diagnostics` + `calibration` so Stage A can see that mapping already applied the adjustment. When the adjustment fires, reset `inputs.global_scale_hint` to 1.0 to avoid double-scaling at Stage A warm-starts.
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main` — surface the new diagnostic fields (masked means, ratio, log_scale_baseline_source) in the JSON/console output and fail the parity summary when `geometry_mode="baseline"` still shows |Δ| > 1 ADU so the evidence immediately calls out regressions.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --device cuda:0 --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T180000Z/stage_a_baseline_probe_baseline.json` (expect Stage A vs mapping max|Δ| < 1 ADU and RMSE ≈ numerical noise).
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T180000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T180000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T180000Z/pytest_db_at_028_029.log` (collect the updated failure signature once mapping baseline parity is restored).

How-To Map:
1. In `build_mapping_stage_a_context`, reuse the existing masked-mean computation that currently seeds `global_scale_hint`, but instead of only storing the ratio, multiply `bragg_zero_iter` in place (CPU float32) and update diagnostics/calibration to note the adjustment source.
2. When scaling occurs, set `diagnostics["target_mean_masked"]`, `diagnostics["bragg_mean_masked"]`, and `diagnostics["masked_mean_ratio"]` so downstream probes/tests can assert parity without recomputing statistics.
3. After the scale is applied, set `inputs.global_scale_hint = 1.0` (or None) so Stage A’s warm-start doesn’t reapply the ratio; retain the previous value in diagnostics if needed for forensic comparison.
4. Extend the baseline probe to print the new diagnostic block and to flag baseline-mode runs as failures whenever `max_abs_diff` or `chi²` relative differences exceed the DB-AT-027 tolerances, making parity regressions obvious.
5. Re-run the probe + DB-AT selectors with the new artifact root so we have synchronized evidence showing Stage A vs mapping parity is fixed before addressing the remaining Stage A vs target shape mismatch.

Pitfalls To Avoid:
- Do not scale `bragg_zero_iter` when the masked means are zero/negative/non-finite; fall back to the previous behavior and emit a warning in diagnostics instead.
- Keep the adjustment confined to mapping; Stage A already applies the ratio, so ensure we don’t double-scale by checking the diagnostics flag before modifying `inputs.global_scale_hint`.
- Preserve canonical diagnostics (HKL source/path, calibration_path, N_cells flags) when injecting the new fields so existing consumers remain unaffected.
- When updating the probe, avoid forcing baseline mode in the default execution path—engineers still need perturbed mode for Stage A smoke evidence.
- Capture both stdout and JSON artifacts for the probe/test commands (use `tee`) so parity deltas are reviewable even if pytest fails early.

If Blocked:
- If the masked means are zero or NaN for this dataset, log the values in diagnostics, leave `bragg_zero_iter` untouched, and stop after capturing the baseline probe/pytest artifacts; flag the situation in docs/fix_plan.md before attempting alternative fixes.
- If CUDA is unavailable, run the probe/tests on CPU, note the device change in the artifact filenames, and highlight potential perf differences in the report.

Findings Applied (Mandatory):
- SCALE-008 — Mapping and Stage A must reuse the warmed Stage A baseline; scaling `bragg_zero_iter` at mapping time enforces the warm-cache authority before tests read the data.
- SCALE-009 — Reconstruction/mapping consumers rely on consistent calibration threading; documenting the masked-mean ratio in diagnostics proves the simulator construction contract is being honored.

Pointers:
- dbex/vis/mapping.py:193-308 (simulate_forward_once + global_scale_hint logic to extend with masked-mean scaling)
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:360-520 (mapping comparison block that will consume the new diagnostics)
- docs/spec-db-conformance.md:265-389 (DB-AT-027/028/029 tolerances driving the parity assertions)
- docs/data_dependency_manifest.md:82-140 (Stage A smoke calibration/HKL provenance that the probe must continue to honor)
