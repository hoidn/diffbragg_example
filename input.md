Summary: Thread Stage A’s calibrated log-scale baseline through the Stage C wrapper so the LBFGS closure and final reconstruction reproduce the Stage A χ² before detector offsets move, then rerun both Stage C smoketests plus the telemetry summarizer to validate REFINE-007.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests:
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/
Do Now:
- Implement: dbex/refinement/stage_c.py::StageC.run — read `stage_a_telemetry['log_scale_baseline_source']` and `param_deltas['log_scale_baseline']['final']` when calibration metadata supplied the baseline, build a tensor on `config.device/dtype`, and stash it in `param_values_c['log_scale_baseline']` alongside the existing `log_scale` delta so frozen Stage A parameters mirror Stage A’s clamp logic.
- Implement: dbex/refinement/stage_c_impl.py::{_build_stage_c_lbfgs_closure,_run_stage_c_lbfgs} — replace the hard-coded `torch.clamp(log_scale, -10, 10)` calls with the Stage A rule (`log_scale_baseline + clamp(delta, ±config.log_scale_max_delta)` when a baseline exists, otherwise `clamp(delta, ±config.log_scale_max_delta_uncalibrated)`), and reuse that combined tensor both inside the LBFGS closure (ROI + panel branches) and when scaling the final Bragg reconstruction so telemetry reports the Stage A-matched χ² before detector offsets change.
- Validate: rerun the Stage C detector microslip smoketests for small + full detector sizes with telemetry capture (`DBEX_SMOKE_TELEMETRY_PATH`) plus `summarize_stage_c_warm_cache.py`, ensuring REFINE-007 gates (≤0.05% χ² regression, ≥80% offset reduction or ≤±0.05 mm absolute) pass for both telemetry files.
How-To Map:
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/collect_stage_c_small.log`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/pytest_stage_c_small.log`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/collect_stage_c_full.log`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/pytest_stage_c_full.log`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/telemetry_stage_c_small.json --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/telemetry_stage_c_full.json --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T210900Z/stage_c_warm_cache_report.json`
Pitfalls To Avoid:
- Treat `log_scale_baseline` as optional: only add it when Stage A telemetry recorded a source; otherwise keep the legacy clamp so uncalibrated runs still hit ±`log_scale_max_delta_uncalibrated`.
- Keep baseline/delta tensors on `config.device` with `requires_grad=False` so Stage C doesn’t accidentally attempt to optimize scale parameters.
- Do not disturb ROI/validation scope wiring (REFINE-011/012) or best-snapshot persistence (REFINE-013) while touching the closure.
- Capture collect-only logs before each pytest run and tee test output; missing selector artifacts block the ledger.
- No tolerance tweaks—if REFINE-007 still fails after the baseline fix, collect telemetry and stop.
If Blocked:
- If χ² regression remains >0.05% after the baseline wiring lands, archive both telemetry JSONs plus the summarizer report, note the failure signature in docs/fix_plan.md, and pause for supervisor guidance before attempting any gate changes.
Findings Applied (Mandatory):
- REFINE-007 — Stage C improvements are validated via χ²+detector-offset telemetry; keep the gate intact.
- REFINE-010 — Stage A auto-panel heuristics remain the authority for ROI vs panel scope.
- REFINE-011/REFINE-012 — Validation scope and closure ROI mode stay aligned with Stage A telemetry after the scale fix.
- REFINE-013 — Best-snapshot persistence/rehydration must continue to populate telemetry before logging final χ².
- REFINE-014 — Orientation tensors still come from `param_deltas['orientation_vec']['final']`; do not regress the recent fix.
- REFINE-015 — Stage C must reuse Stage A’s log-scale baseline before exponentiating so canonical χ² matches Stage A before detector offsets change.
Pointers:
- docs/spec-db-workflow.md:62 — Stage C detector-offset spec and gate expectations.
- docs/TESTING_GUIDE.md:48 — Canonical Stage C smoketest commands and env requirements.
- docs/fix_plan.md:33,1250 — Current PERF-WARM-SIM-001 status and the log-scale baseline Do Now.
- dbex/refinement/stage_a_impl.py:1280-1296 — Stage A log-scale baseline clamp logic to mirror.
- dbex/refinement/stage_c.py:170-246 & dbex/refinement/stage_c_impl.py:504-914 — Stage C telemetry reconstruction and closure locations that need the baseline tensor.
- plans/active/PERF-WARM-SIM-001/reports/2025-12-01T204500Z/telemetry_stage_c_full.json — Evidence of the 0.067% χ² regression even with detector offsets fixed.
Next Up (optional):
- If the baseline fix lands quickly and smoketests pass, capture a short diff of the telemetry JSONs vs the 2025-11-23 PASS artifacts to document that Stage C χ² now matches Stage A before detector offsets change.
