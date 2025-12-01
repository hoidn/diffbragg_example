Summary: Disable Stage C ROI-mode closures whenever Stage A enforces panel-scope validations so the full-detector smoke stops regressing chi², then rerun the Stage C smokes (small + full) with telemetry capture.
Mode: Parity
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/
Do Now:
- Implement: dbex/refinement/stage_c_impl.py::_build_stage_c_params — gate `stage_c_roi_mode_active` (and telemetry/perf counters) on `force_panel_validation` so Stage C closures drop ROI-mode whenever Stage A reports `validation_scope="panel"`, and include a `roi_mode_reason` tag proving why panel mode was enforced (REFINE-012).
- Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip — adjust the ROI-mode expectation helper to follow the Stage A panel-validation heuristic (Stage B or Stage C enabled, explicit override, or ROI count ≤ threshold) while keeping the existing detector-offset and chi² gates untouched.
- Validate: `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small` and `--smoke-detector-size=full` (collect-only + full runs with telemetry capture), then rerun the warm-cache summarizer so PERF-WARM-SIM-001 Phase D.4 artifacts contain the aligned ROI counters.
How-To Map:
1. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/collect_stage_c_small.log
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/pytest_stage_c_small.log
3. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/collect_stage_c_full.log
4. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/pytest_stage_c_full.log
5. python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/telemetry_stage_c_small.json --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/telemetry_stage_c_full.json --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/stage_c_warm_cache_report.json
Pitfalls To Avoid:
- Do not relax the REFINE-007 chi² or detector-offset gates; the fix must make canonical panel metrics pass without changing thresholds.
- Leave small-detector ROI behavior intact when Stage C is disabled; only the "Stage C enabled + panel validation" scenarios should force panel closures.
- Retain the warm-cache code paths (stage_a_ctx reuse) and avoid touching simulator factories; scope stays inside Stage C + smoketest plumbing.
- Keep telemetry/log paths rooted in the new timestamped directory so previous evidence remains immutable.
- Conservatively update tests—only adjust the ROI-mode expectation helper, not unrelated assertions or fixtures.
- Maintain `KMP_DUPLICATE_LIB_OK=TRUE` and `NANOBRAGG_DISABLE_COMPILE=1`; missing env vars invalidate perf counters.
- Record any failure signatures immediately in docs/fix_plan.md and galph_memory instead of rerunning blindly.
If Blocked:
- Capture the failing pytest log + telemetry JSON in the artifact dir, summarize the regression signature in docs/fix_plan.md Attempts History, set galph_memory state=blocked with the selector/error text, and stop so we can rescope before another code change.
Findings Applied (Mandatory):
- REFINE-010 — Stage A auto-panel threshold (≤32 ROIs or Stage B/C enabled) defines when panel validations are required; mirror this logic in Stage C ROI-mode handling.
- REFINE-011 — Stage C full validations must share the same pixel population as Stage A; bypass ROI sampling for any `is_full` evaluation whenever Stage A forced panel scope.
- REFINE-012 — Stage C MUST also drop ROI-mode closures entirely when Stage A validation scope is panel so LBFGS optimizes the same dataset the gate inspects.
Pointers:
- docs/fix_plan.md:903 — latest PERF-WARM-SIM-001 D.4 plan + exact command block for this loop.
- docs/findings.md:72 — REFINE-010/011/012 guardrails explaining why panel validation overrides are mandatory.
- docs/TESTING_GUIDE.md:30 — Stage smoke policy and canonical Stage C χ²/offset tolerances referenced by the smokes.
Next Up (optional): If time remains, prep PERF-WARM-SIM-001 benchmarking notes for D.5 once the Stage C gate is green again.
