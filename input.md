Summary: Compute the Stage A zero-iteration masked mean on-device so the log-scale baseline matches the mapping stack and telemetry records the correction before rerunning DB-AT-028/029.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/

Do Now (hard validity contract)
- Implement: dbex/nanobrag_refinement.py::_build_stage_a_params Tensorize `inputs.target`/`inputs.loss_mask` onto the Stage A device, emit a zero-iteration Bragg stack from the warmed simulators, compute `log_scale_baseline = log(target_mean_masked / model_mean_masked)` whenever `calibration_adjusted_for_n_cells=True`, and stash both masked means plus the adjustment factor into `param_values`/Stage A telemetry so engine + inline callers share the baseline override.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" (collect-only first, then full run, and capture metrics/logs even though the gates fail).

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1
3. pytest --collect-only -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
     | tee plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/pytest_db_at_028_029_collect.log
4. pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
     | tee plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/pytest_db_at_028_029.log
5. python - <<'PY'
import json, math, pathlib
metrics = json.loads(pathlib.Path('plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/db_at_029/db_at_029_metrics.json').read_text())
scale_ratio_mapping = metrics["scale_ratio_mapping_masked"]
scale_ratio_before = metrics["scale_ratio_before"]
assert scale_ratio_mapping > 0
assert abs(scale_ratio_before - scale_ratio_mapping) / scale_ratio_mapping < 0.01, metrics
assert metrics["log_scale_baseline_source"] == "mapping_global_scale_hint", metrics
print("Stage A baseline telemetry aligned", scale_ratio_before)
PY
6. rg -n "stage_a_zero_iter_mean" plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/db_at_029/db_at_029_metrics.json

Pitfalls To Avoid
- Do not mutate the captured calibration JSON; clone metadata dicts before tagging adjustment flags or masked-mean stats.
- Keep tensor conversions device/dtype neutral (use torch.as_tensor on stage_a_ctx.device) so CUDA/CPU runs share the same logic.
- Guard masked means against zeros/NaNs and only fall back to the previous baseline path when tensors truly cannot be constructed.
- Persist `target_mean_masked`, `stage_a_zero_iter_mean`, and `spot_scale_override_adjustment_factor` in telemetry for both inline + engine paths (DB-AT-029 asserts on these fields).
- Leave ROI/panel warm-cache behavior intact—only the baseline computation should touch the zero-iteration simulator stack.
- Capture pytest stdout/stderr into the artifact directory even when selectors fail for chi²/ROI gates (CONFORMANCE-001 requirement).
- Keep the canonical metadata env vars in place; do not switch HKL/calibration overrides mid-run.
- Remove any debug prints before running pytest so logs stay clean for comparison across loops.

If Blocked
- If tensorizing the mask/target fails (device mismatch, memory) and you cannot resolve it without environment changes, save the traceback to plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/block_tensorization.log, stop after collect-only, and flag the blocker in docs/fix_plan.md + Turn Summary.
- If pytest cannot collect both selectors, archive the collect log showing the error, skip the full run, and note the new failure signature before exiting.

Findings Applied (Mandatory)
- STAGEA-001 — Stage A refinements must reuse mapping calibration payloads; zero-iteration telemetry needs the same assets before masked means are meaningful.
- SCALE-008 — Mapping-provided baseline corrections must propagate through Stage A telemetry; masked-mean adjustments replace the `log(sqrt(spot_scale_override))` fallback.

Pointers
- docs/spec-db-conformance.md:280 — DB-AT-028/029 chi² and ROI-scale requirements that remain red.
- docs/data_dependency_manifest.md:34 — Smoke calibration/HKL provenance, env vars, and telemetry expectations for these selectors.
- plans/active/TOOLING-VIS-001/implementation.md:320 — Phase D.E scope describing calibration-adjusted log-scale handling.
- docs/fix_plan.md:395 — Latest Attempts History describing the masked-mean failure signature and remediation plan.
- dbex/nanobrag_refinement.py:1324 — Current masked-mean baseline branch that still falls back to log(global_scale_hint).

Next Up (optional)
- If time remains after the baseline fix, rerun compare_mapping_dataset_metrics.py for the drop-N_cells case to confirm amplitude parity vs mapping diagnostics.

Mapped Tests Guardrail: `pytest --collect-only -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` must continue to collect 2 nodes; treat any collection failure as a blocker before implementation proceeds.

Hard Gate: Even on failing runs, persist `db_at_028` and `db_at_029` metrics plus mapping_context fixtures under `plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/` before exiting.

Normative Math/Physics: Derive masked means via the PHYSICS-LOSS variance-weighted Stage A targets per docs/spec-db-core.md §§57-74 so the new baseline honors the Stage A zero-point invariant.
