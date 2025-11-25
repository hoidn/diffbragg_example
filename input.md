Summary: Derive Stage A's log-scale baseline from its own warmed simulator output whenever mapping adjusts calibration so DB-AT-028/029 telemetry matches the mapping stack even though the gates still fail.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/

Do Now (hard validity contract)
- Implement: dbex/nanobrag_refinement.py::_build_stage_a_params  compute the Stage A zero-iteration masked Bragg mean from the warmed simulators when `config.calibration_metadata["calibration_adjusted_for_n_cells"]` is true, set `log_scale_baseline = log(target_mean/model_mean_stage_a)` (fallback to current behavior when ratios are invalid), stash the value plus `spot_scale_override_adjustment_factor` back into `param_values`, and update the warmed context so engine + inline callers share the same baseline telemetry.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" (collect-only first, then full run, and archive the new metrics/logs even though the chi²/ROI gates still fail).

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1
3. pytest --collect-only -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
     | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/pytest_db_at_028_029_collect.log
4. pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
     | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/pytest_db_at_028_029.log
5. python - <<'PY'
import json
from pathlib import Path
path = Path('plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/db_at_029/db_at_029_metrics.json')
metrics = json.loads(path.read_text())
assert metrics["log_scale_baseline_source"] == "mapping_global_scale_hint", metrics
assert abs(metrics["scale_ratio_before"] - metrics["scale_ratio_mapping_masked"]) / metrics["scale_ratio_mapping_masked"] < 0.01, metrics
print("Stage A baseline telemetry aligned", metrics["scale_ratio_before"])
PY
6. rg -n "calibration_adjusted" plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/db_at_029/mapping_context_fixture.json

Pitfalls To Avoid
- Do not mutate the on-disk calibration JSON; always deepcopy before adding adjustment flags so provenance hashes stay valid.
- Keep the new mean-estimation helper device/dtype neutral (no `.cpu()` unless the tensors require host access) to preserve CUDA parity.
- Guard against divide-by-zero or NaN signals when computing `target_mean/model_mean_stage_a`; fall back to the previous baseline path if either mean is invalid.
- Update both the inline and engine telemetry objects—if one path misses the new baseline the DB-AT selectors will regress again.
- Leave the chi²/ROI assertions untouched; even with the new baseline the selectors are expected to fail for physics reasons and we still need their artifacts.
- Avoid changing Stage B/C flags or interpolation settings; DB-AT-028/029 must remain Stage A only with nearest-neighbor HKL sampling.
- Preserve the `spot_scale_override_adjustment_factor` telemetry so SCALE-008 evidence continues to flow through the artifacts.
- Capture all stdout/stderr from pytest into the reserved report directory; we need the logs even on failure.

If Blocked
- If the warmed Stage A context cannot produce a raw model mean (e.g., simulator build fails), log the error to `plans/active/TOOLING-VIS-001/reports/2025-11-25T160828Z/block_stage_a_mean.log`, keep the workspace dirty, and note the failure signature in docs/fix_plan.md Attempts History before pausing.
- If pytest cannot collect either smoke selector, archive the collect log with the traceback, skip the full run, and flag the block in the Turn Summary so we can reassess.

Findings Applied (Mandatory)
- STAGEA-001 — Stage A must reuse the mapping calibration payload; the new baseline calculation is only valid when the warmed simulators consume the same assets recorded in telemetry.
- SCALE-004 — Refined HKL assets must stay paired with their calibration metadata; do not introduce alternate scale factors that bypass DiffBragg provenance.
- SCALE-005 — N_cells gating semantics remain authoritative; small-detector runs suppress them, but full-detector paths must keep SCALE-005 intact.
- SCALE-008 — Mapping-provided scale corrections need to flow into Stage A telemetry so DB-AT-029 can verify parity even on failing runs.

Pointers
- docs/spec-db-conformance.md:287 — DB-AT-028/029 acceptance criteria (chi²/pixel and ROI correlation expectations) referenced by the smoke selectors.
- docs/data_dependency_manifest.md:34 — Canonical metadata/HKL paths and telemetry requirements for the metadata smoke fixtures.
- plans/active/TOOLING-VIS-001/implementation.md:325 — Phase D/E narrative explaining why the Stage A baseline must match the mapping zero point.
- docs/fix_plan.md:390 — Latest Attempts History entry describing the telemetry alignment plus the new under-scale failure signature.
- dbex/nanobrag_refinement.py:1330 — Existing warm-cache mean estimation block you can extend for the new baseline calculation.

Next Up (optional)
- Once the baseline holds, plan a follow-up probe that compares Stage A chi² traces before/after the baseline fix to isolate the remaining convergence failure.

Mapped Tests Guardrail:
- `pytest --collect-only -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` must continue to discover 2 nodes; treat any collection failure as a blocker and stop.

Hard Gate:
- Even when the selectors fail on chi²/ROI thresholds, archive `db_at_028` and `db_at_029` metrics plus mapping_context fixtures under the new report directory before finishing.

Normative Math/Physics:
- When computing the new baseline, follow the variance-weighted loss and scale definitions in docs/spec-db-core.md §§57–74 so the masked means align with the canonical Stage A zero-point contract.
