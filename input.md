Summary: Derive the Stage A log-scale baseline from the warmed zero-iteration simulator output so DB-AT-028/029 see scale_ratio_before≈scale_ratio_mapping_masked even though chi²/ROI gates still fail.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T034500Z/

Do Now (hard validity contract)
- Implement: dbex/nanobrag_refinement.py::_build_stage_a_params Convert the masked-mean branch to tensorize `inputs.target`/`inputs.loss_mask` onto `stage_a_ctx.device`, build a zero-iteration Bragg stack from the warmed simulators, compute `log_scale_baseline = log(target_mean_masked / model_mean_masked)` when `calibration_adjusted_for_n_cells=True`, and record both masked means plus the adjustment factor in `param_values`/Stage A telemetry so engine + inline callers share the baseline.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T034500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T034500Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" (collect-only first, then full run, and capture metrics/logs even though the gates fail).

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T034500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T034500Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1
3. pytest --collect-only -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
     | tee plans/active/TOOLING-VIS-001/reports/2025-11-26T034500Z/pytest_db_at_028_029_collect.log
4. pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
     | tee plans/active/TOOLING-VIS-001/reports/2025-11-26T034500Z/pytest_db_at_028_029.log
5. python - <<'PY'
import json, math, pathlib
metrics = json.loads(pathlib.Path('plans/active/TOOLING-VIS-001/reports/2025-11-26T034500Z/db_at_029/db_at_029_metrics.json').read_text())
scale_ratio_mapping = metrics["scale_ratio_mapping_masked"]
scale_ratio_before = metrics["scale_ratio_before"]
assert scale_ratio_mapping > 0
assert abs(scale_ratio_before - scale_ratio_mapping) / scale_ratio_mapping < 0.01, metrics
assert metrics["log_scale_baseline_source"] == "mapping_global_scale_hint", metrics
print("Stage A baseline telemetry aligned", scale_ratio_before)
PY
6. rg -n "stage_a_zero_iter_mean" plans/active/TOOLING-VIS-001/reports/2025-11-26T034500Z/db_at_029/db_at_029_metrics.json

Pitfalls To Avoid
- Do not mutate the on-disk calibration JSON; copy data before adding adjustment flags so manifests stay valid.
- Keep all tensor conversions device/dtype neutral; use torch.as_tensor on the Stage A device so CUDA runs remain supported.
- Guard masked-mean math against zero/NaN values and fall back to the previous baseline path only when absolutely necessary.
- Maintain `log_scale_baseline_source="mapping_global_scale_hint"` so DB-AT-029 asserts keep passing once the masked mean succeeds.
- Preserve `spot_scale_override_adjustment_factor` telemetry and plumb any new masked-mean fields into both engine and inline telemetry objects.
- Leave DB-AT-028/029 acceptance gates untouched; even with the baseline fix they are expected to fail on chi²/ROI.
- Keep ROI/panel warm-cache behavior unchanged—only the baseline computation should use the stacked zero-iteration tensors.
- Capture pytest stdout/stderr into the reserved artifact directory even on failure for CONFORMANCE-001 compliance.

If Blocked
- If tensorizing the loss mask or target raises a device mismatch that cannot be resolved without touching env/toolchain, archive the traceback under `plans/active/TOOLING-VIS-001/reports/2025-11-26T034500Z/block_tensorization.log`, stop after collect-only, and log the blocker in docs/fix_plan.md + Turn Summary.
- If pytest cannot collect both selectors, save the collect log with the failure, skip the full run, and flag the block so we can reassess before touching Stage A again.

Findings Applied (Mandatory)
- STAGEA-001 — Stage A must reuse mapping calibration payloads; the masked-mean computation only makes sense once both paths share HKL/calibration assets.
- SCALE-008 — Mapping-provided scale corrections must propagate through Stage A telemetry; the masked-mean fix enforces this contract instead of falling back to log(sqrt(spot_scale_override)).

Pointers
- docs/spec-db-conformance.md:280 — DB-AT-028/029 chi² and scale-ratio requirements that the selectors enforce.
- docs/data_dependency_manifest.md:34 — Metadata smoke calibration/HKL provenance and telemetry expectations for the fixtures we run.
- plans/active/TOOLING-VIS-001/implementation.md:320 — Phase D.E narrative on Stage A mapping alignment and baseline handling.
- docs/fix_plan.md:390 — Latest Attempts History entries describing the telemetry alignment work and current failure signature.
- dbex/nanobrag_refinement.py:1324 — Masked-mean baseline branch that currently mixes numpy masks with torch tensors.

Next Up (optional)
- Once baseline telemetry is stable, rerun `compare_mapping_dataset_metrics.py` with the drop-N_cells case to confirm amplitude parity vs mapping diagnostics.

Mapped Tests Guardrail: `pytest --collect-only -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` must continue to find 2 nodes; treat any collection failure as a blocker before implementation proceeds.

Hard Gate: Even on failing runs, persist `db_at_028` and `db_at_029` metrics plus mapping_context fixtures under `plans/active/TOOLING-VIS-001/reports/2025-11-26T034500Z/` before exiting.

Normative Math/Physics: Compute masked means using variance-weighted Stage A targets per docs/spec-db-core.md §§57‑74 so `log_scale_baseline` reflects the canonical Stage A zero-point invariant.
