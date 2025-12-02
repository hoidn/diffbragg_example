Summary: Add an opt-in debug hook to Stage C’s warm-cache retarget helper so we can capture panel/ROI distance deltas in ROI mode and archive Stage C small/full traces for PERF-WARM-SIM-001.
Mode: none
InitiativeType: perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip (smoke-detector-size=small)
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip (smoke-detector-size=full, expected failure — run to capture artifacts)
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/

Do Now:
- FocusItem: PERF-WARM-SIM-001 Phase F — ROI-mode Simulator Trace
- Implement: `dbex/refinement/stage_c_impl.py::_retarget_stage_a_detectors` — gate the existing per-panel/ROI update loop with a new env var (`DBEX_STAGE_C_CACHE_DEBUG_PATH`). When the env var points to a directory, capture per-call JSON snapshots (call index, panel_id, ROI indices/bboxes, distance_before/after_mm, simulator ids) and write them into that directory (one file per call) without changing default behavior.
- Implement: `dbex/refinement/stage_c_impl.py` module scope — add the env-var plumbing/helper stub (Path/json imports, module-level call counter) used by the debug hook. Keep instrumentation cost effectively zero when the env var is unset.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_C_CACHE_DEBUG_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/cache_debug_small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/pytest_stage_c_small.log`
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_C_CACHE_DEBUG_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/cache_debug_full DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/pytest_stage_c_full.log || true` (full-detector run still fails the REFINE-007 gate; failure is expected, artifacts must still be produced).
- Post-process: `python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/telemetry_stage_c_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/telemetry_stage_c_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/stage_c_roi_summary.json | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/summarize_stage_c_roi.log`

How-To Map:
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_C_CACHE_DEBUG_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/cache_debug_small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/pytest_stage_c_small.log`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_C_CACHE_DEBUG_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/cache_debug_full DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/pytest_stage_c_full.log || true`
- `python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/telemetry_stage_c_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/telemetry_stage_c_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/stage_c_roi_summary.json | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/summarize_stage_c_roi.log`

Pitfalls To Avoid:
- Keep the new instrumentation fully opt-in; do not emit debug files when `DBEX_STAGE_C_CACHE_DEBUG_PATH` is unset and avoid storing tensors that hold references to autograd graphs (log detached scalars only).
- Name the cache-debug directories uniquely per run so panel-mode and ROI-mode traces do not overwrite each other.
- Stage C full smoketest will still fail the chi² regression gate; run it with `|| true` and clearly note the expected failure in the log rather than weakening REFINE-007.
- Preserve existing warm-cache behavior; the debug hook must not mutate detector/simulator state beyond the current retarget logic.
- Ensure the new directories/files end up under the artifacts path so they can be inspected offline (no writes to /tmp or repo root).

If Blocked: Save whichever cache-debug JSON files were produced plus the failing pytest logs under `plans/active/PERF-WARM-SIM-001/reports/2025-12-02T173000Z/blocked/`, cite the observed behavior (e.g., ROI entries never logged, env var ignored), and update docs/fix_plan.md with the new evidence before attempting code fixes.

Findings Applied (Mandatory):
- PERF-WARM-013 — Stage C warm-cache retargeting must mutate cached simulators instead of rebuilding cold ones; ROI-mode traces will show whether that happens.
- REFINE-011 / REFINE-016 — Stage C ROI vs panel validation scopes must remain faithful to Stage A telemetry, so instrumentation cannot bypass the trusted-mask/validation gates.

Pointers:
- plans/active/PERF-WARM-SIM-001/implementation.md#phase-f — scope for the ROI-mode trace.
- plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/summary.md — latest failure signature motivating this evidence loop.
- dbex/refinement/stage_c_impl.py:52-180 — `_retarget_stage_a_detectors` ROI retarget helper and current ROI cache handling.

Next Up (optional): Once the traces land, inspect the cache-debug JSON + telemetry to decide whether ROI entries require a dedicated retarget helper or a StageAContext clone before attempting another implementation loop.
