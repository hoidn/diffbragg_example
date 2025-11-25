Summary: Ensure Stage A engine delegation consumes the mapping-adjusted baseline so DB-AT-029 telemetry matches mapping scale ratios even while the smoke gates keep failing.
Mode: Parity
Focus: TOOLING-VIS-001   Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T020500Z/

Do Now (hard validity contract)
- Implement: dbex/nanobrag_refinement.py::_build_stage_a_params   detect `calibration_adjusted_for_n_cells` and stash both the mapping-derived `log_scale_baseline` (log(inputs.global_scale_hint)) and `spot_scale_override_adjustment_factor` inside `param_values`/warm-cache state so every caller (inline + engine) applies the corrected baseline before building optimizers; remove the ad-hoc debug prints once the shared helper owns the logic.
- Implement: dbex/refinement/stage_a.py::StageA.run and dbex/nanobrag_refinement.py::run_nanobrag_refinement   plumb the new param metadata into `RefinementTelemetry` (engine + inline paths) and ensure `_build_final_bragg_from_stage_a_telemetry` sees the updated baseline, so DB-AT-029 metrics report `log_scale_baseline_source="mapping_global_scale_hint"` with `scale_ratio_before scale_ratio_mapping_masked` when calibration was adjusted.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T020500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T020500Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" (collect-only first, then full run; chi /ROI failures expected artifacts must show the new telemetry fields filled).

How-To Map
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T020500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-26T020500Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1
3. pytest --collect-only -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
     | tee plans/active/TOOLING-VIS-001/reports/2025-11-26T020500Z/pytest_db_at_028_029_collect.log
4. pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
     | tee plans/active/TOOLING-VIS-001/reports/2025-11-26T020500Z/pytest_db_at_028_029.log
5. python - <<'PY'
import json
from pathlib import Path
path = Path('plans/active/TOOLING-VIS-001/reports/2025-11-26T020500Z/db_at_029/db_at_029_metrics.json')
metrics = json.loads(path.read_text())
assert metrics["log_scale_baseline_source"] == "mapping_global_scale_hint", metrics
assert abs(metrics["scale_ratio_before"] - metrics["scale_ratio_mapping_masked"]) < 1e-3, metrics
assert metrics["spot_scale_override_adjustment_factor"] is not None
print("Stage A baseline telemetry verified", metrics["scale_ratio_before"], metrics["spot_scale_override_adjustment_factor"])
PY
6. cat plans/active/TOOLING-VIS-001/reports/2025-11-26T020500Z/db_at_028/mapping_context_fixture.json | rg -n "calibration_adjusted"

Pitfalls To Avoid
- Do not mutate the on-disk calibration JSON; always deepcopy before attaching adjustment flags so reproducibility stays intact.
- Keep Stage A engine and inline paths in lockstep any telemetry field added to one must be threaded through the other and through `_build_final_bragg_from_stage_a_telemetry`.
- Remove the temporary `[TOOLING-VIS-001-P1-*]` print statements once the helper owns the logic; stray stdout noise pollutes pytest logs.
- Preserve device/dtype neutrality inside `_build_stage_a_params` so CUDA runs do not cast tensors back to CPU.
- Ensure the new telemetry fields remain optional (default None) so legacy selectors parsing `RefinementTelemetry` dicts don t explode.
- Do not toggle Stage B/C flags or interpolation in these smoke runs; DB-AT-028/029 must stay nearest-neighbor with Stage A only.
- Avoid touching `docs/` or test tolerances unless the telemetry proves the fix worked; chi /ROI thresholds still enforce the known failure signature.
- When cloning calibration metadata, keep `N_cells` gating semantics (SCALE-005) intact for full-detector paths only the small-detector smoke fixture suppresses them.

If Blocked
- If `mapping_context.calibration` still lacks the adjustment flags after your edits, dump the dict to `plans/active/TOOLING-VIS-001/reports/2025-11-26T020500Z/block_calibration.json`, log the signature in docs/fix_plan.md Attempts History, and halt before modifying Stage A.
- If pytest cannot reach the assertions (e.g., crashes before artifacts), capture the traceback to `.../block.log`, keep the workspace dirty, and notify the supervisor in the summary so we can reassess.

Findings Applied (Mandatory)
- STAGEA-001   Stage A must reuse the mapping calibration payload; the new baseline logic can t diverge from the mapping zero-point contract.
- SCALE-004   Refined MTZ assets stay paired with their calibration metadata; baseline overrides must not bypass this precedence.
- SCALE-005   N_cells gating is still authoritative; the new helper only skips N_cells when the smoke fixture explicitly disables it.
- SCALE-008   Mapping-aware baseline adjustments must propagate into Stage A telemetry so DB-AT-029 scale ratios reflect the mapping stack.

Pointers
- docs/spec-db-conformance.md:280   DB-AT-028/029 chi , ROI, and scale ratio contracts we re still enforcing even on failing runs.
- docs/data_dependency_manifest.md:30   Canonical provenance for small-detector calibration/HKL assets plus telemetry expectations.
- plans/active/TOOLING-VIS-001/implementation.md:200   Phase D/E context for Stage A mapping alignment requirements.
- dbex/nanobrag_refinement.py:2470   Inline Stage A baseline selection that must be shared with engine delegation.
- dbex/refinement/stage_a.py:300   Engine Stage A telemetry assembly lacking the new baseline fields.

Next Up (optional)
- Once telemetry aligns, plan a follow-up probe comparing Stage A chi  traces before/after the baseline fix to isolate the remaining convergence failure.
