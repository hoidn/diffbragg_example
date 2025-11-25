Summary: Force Stage A to reuse the mapping-adjusted log-scale baseline whenever the small-detector calibration disables N_cells so the reconstructed Bragg stack matches the mapping zero-point.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T010900Z/

Do Now (hard validity contract)
- Implement: dbex/vis/mapping.py::build_mapping_stage_a_context — guarantee the auto-adjuster sets `calibration_adjusted_for_n_cells` and `spot_scale_override_adjustment_factor` on both `diagnostics` and the calibration dict handed to Stage A (clone before mutation, retain fallback behavior when the guard does not trigger) so downstream code can reliably detect mapping-assisted baselines.
- Implement: dbex/nanobrag_refinement.py::_build_stage_a_params — detect the calibration-adjusted flag and swap the log-scale baseline to `log(inputs.global_scale_hint)` (recording `log_scale_baseline_source="mapping_global_scale_hint"` and threading `spot_scale_override_adjustment_factor` through param_deltas/telemetry) so Stage A LBFGS and `_build_final_bragg_from_stage_a_telemetry` both apply the same masked-mean baseline when N_cells is suppressed.
- Implement: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result — clone the calibration metadata before mutating it, persist `calibration_adjusted_for_n_cells` and `spot_scale_override_adjustment_factor` into the metrics JSON, and assert in-code that when the flag is set the new telemetry fields (`log_scale_baseline_source`, `scale_ratio_before`) match the mapping diagnostics; this keeps artifacts self-verifying.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T010900Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T010900Z/db_at_029 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" (collect-only first, then full run; failures on chi²/ROI gates are expected but logs/JSON must show the new baseline telemetry).

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T010900Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T010900Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1
3. After coding, run the collect-only gate:
   pytest --collect-only -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
     | tee plans/active/TOOLING-VIS-001/reports/2025-11-26T010900Z/pytest_db_at_028_029_collect.log
4. Run the full selector suite with logs tee’d to `.../pytest_db_at_028_029.log` (failures OK, artifacts mandatory).
5. Verify the metrics contain the new telemetry (example sanity script):
   python - <<'PY'
import json
from pathlib import Path
path = Path('plans/active/TOOLING-VIS-001/reports/2025-11-26T010900Z/db_at_029/db_at_029_metrics.json')
metrics = json.loads(path.read_text())
assert metrics["log_scale_baseline_source"] == "mapping_global_scale_hint", metrics.get("log_scale_baseline_source")
assert abs(metrics["scale_ratio_before"] - metrics["scale_ratio_mapping_masked"]) < 1e-3, metrics
assert metrics["spot_scale_override_adjustment_factor"] is not None, metrics
print("Stage A baseline telemetry verified:", metrics["scale_ratio_before"], metrics["log_scale_baseline_source"])
PY
6. List the mapping_context fixture to confirm calibration flags for provenance:
   cat plans/active/TOOLING-VIS-001/reports/2025-11-26T010900Z/db_at_028/mapping_context_fixture.json | rg "calibration" -n

Pitfalls To Avoid
- Do not mutate the on-disk calibration JSON; always deepcopy before injecting flags or adjustment factors.
- Guard the mapping baseline override behind `inputs.global_scale_hint > 0` so unadjusted runs still fall back to the calibrated sqrt(spot_scale) path.
- Keep telemetry schema backward compatible (optional fields only) so legacy selectors parsing RefinementTelemetry do not fail.
- Ensure device/dtype neutrality when touching Stage A tensors (no implicit CPU casts when running on CUDA).
- Maintain warm-cache performance by calculating the new baseline once per Stage A invocation rather than per ROI.
- When augmenting tests, keep artifacts deterministic (no random ordering) so supervisor diffs remain stable.

If Blocked
- If `mapping_context.calibration` still lacks `calibration_adjusted_for_n_cells` after the builder changes, dump the entire dict to `plans/active/TOOLING-VIS-001/reports/2025-11-26T010900Z/block_calibration.json`, note the missing keys in docs/fix_plan.md Attempts History, and stop before modifying Stage A.
- If pytest crashes before writing artifacts, capture the traceback to `.../block.log`, leave the workspace as-is, and alert the supervisor in the summary so we can reassess the approach.

Findings Applied (Mandatory)
- STAGEA-001 — Stage A must reuse the mapping calibration payload; the new baseline logic cannot diverge from the mapping zero-point contract.
- SCALE-004 — Refined MTZ + calibration pairing remains authoritative; baseline overrides must not bypass refined HKL usage.
- SCALE-005 — N_cells gating semantics stay intact (full-detector paths still apply SCALE-005, small-detector metadata fixtures gate it off).
- SCALE-008 — The mapping auto-adjust flag is the trigger for this work; telemetry must prove when the override engages.

Pointers
- docs/spec-db-conformance.md:280 — Acceptance criteria for DB-AT-028/029 chi² and ROI scale telemetry.
- dbex/vis/mapping.py:221 — Current spot_scale auto-adjust hook; extend it to set calibration flags consumed by Stage A.
- dbex/nanobrag_refinement.py:1042 & 1730 — Stage A parameter builder and LBFGS closure where log-scale baselines are selected.
- plans/active/TOOLING-VIS-001/reports/2025-11-25T235500Z/db_at_029/db_at_029_metrics.json — Evidence showing mapping scale=1.0 while Stage A still reports `scale_ratio_before≈2.0×10⁴`.

Next Up (optional)
- Once Stage A zero-iteration intensities match the mapping stack, revisit the DB-AT-028/029 chi² trace to determine whether the remaining failure is due to physics (variance model) or gate tolerances.
