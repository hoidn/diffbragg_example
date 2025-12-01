Summary: Disable Stage C ROI-mode closures whenever Stage A telemetry enforces panel validations so the LBFGS population matches the REFINE-007 chi² gate, then rerun the Stage C detector microslip smokes with telemetry + warm-cache summarizer to confirm the +0.067 % regression disappears.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T193800Z/collect_stage_c_small.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T193800Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small \| tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T193800Z/pytest_stage_c_small.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T193800Z/collect_stage_c_full.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T193800Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full \| tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T193800Z/pytest_stage_c_full.log
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T193800Z/
Do Now:
- Implement: dbex/refinement/stage_c_impl.py::_build_stage_c_params — gate `stage_c_roi_mode_active` on `not force_panel_validation`, add a `roi_mode_reason="validation_scope_panel"` branch, and ensure the perf-counter payload mirrors the new ROI-mode behavior so Stage C closures switch to panel mode whenever Stage A telemetry reports `validation_scope="panel"`.
- Validate: Re-run `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` for both detector sizes plus the warm-cache summarizer so the new telemetry proves `roi_mode="panel"` on the canonical detector, detector-offset reductions ≥99.999 %, and chi² regression ≤0.05 %.
How-To Map:
1. Edit `dbex/refinement/stage_c_impl.py::_build_stage_c_params` (~lines 180-230) so `stage_c_roi_mode_active` requires `not force_panel_validation`. Add a new `roi_mode_reason` clause (e.g., `"validation_scope_panel"`) when ROI mode is disabled because Stage A forced panel validations, and keep the existing reasons for other cases.
2. Ensure `stage_c_roi_mode_label`/`validation_scope` stay consistent (panel when either ROI disabled or validations forced). No other modules should see ROI closures active when telemetry advertises `validation_scope="panel"`.
3. Rebuild the repo artifacts for Stage C smokes:
   - Run the mapped collect-only commands to capture selector health logs for both detector sizes.
   - Execute the small-detector smoketest with telemetry env vars set as in Mapped tests, saving stdout to `pytest_stage_c_small.log` and telemetry JSON to the artifact directory.
   - Repeat for the full detector smoketest.
   - Invoke the warm-cache summarizer: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-01T193800Z/telemetry_stage_c_small.json --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-01T193800Z/telemetry_stage_c_full.json --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T193800Z/stage_c_warm_cache_report.json`.
4. Verify the full-detector telemetry reports `perf_counters['roi_mode']=="panel"` and `roi_mode_reason=="validation_scope_panel"` alongside ≤0.05 % chi² regression; if not, stop and capture the failure evidence under the artifacts path.
Pitfalls To Avoid:
- Do not relax the REFINE-007 chi² or detector-offset gates; the fix must land within the existing 0.05 % tolerance.
- Keep the ROI-mode toggle fully telemetry-driven—no hard-coded detector-size checks or env overrides.
- Preserve existing REFINE-012 provenance strings; only add the new `"validation_scope_panel"` reason instead of mutating prior meanings.
- Ensure `stage_c_roi_count_total/sample` stay accurate when ROI mode is forcibly disabled (report canonical ROI counts, not zero).
- Continue to set `KMP_DUPLICATE_LIB_OK=TRUE` and `NANOBRAGG_DISABLE_COMPILE=1` for every smoketest run per Testing Guide.
- Capture collect-only logs before executing pytest so selector health evidence exists if runs fail early.
- Leave `_record_stage_telemetry` untouched so failures still emit JSON before assertions fire.
If Blocked:
- If the full-detector smoketest still regresses >0.05 %, archive the failing telemetry/logs in the artifacts directory, note the regression signature in docs/fix_plan.md Attempts History, and halt further edits so we can re-scope the plan.
Findings Applied (Mandatory):
- REFINE-007 — Stage C must not regress chi² vs Stage A beyond 0.05 % while delivering ≥80 % detector-offset reduction; this change aligns the optimization/validation populations to satisfy that gate.
- REFINE-010 — Stage A ROI auto-panel heuristics remain the source of truth; detect Stage A’s ROI/validation scope via telemetry and avoid ad-hoc thresholds.
- REFINE-011 — When Stage A forces panel validations, downstream stages must match that population; disabling ROI closures enforces this.
- REFINE-012 — Maintain ROI-mode provenance and telemetry so tooling can trace why ROI closures were (not) active.
Pointers:
- docs/fix_plan.md:193800 — New Phase D.4 entry describing the ROI-mode alignment plan and artifact path.
- dbex/refinement/stage_c_impl.py:180-220 — Stage C parameter builder where `stage_c_roi_mode_active` and `roi_mode_reason` are defined.
- tests/dbex/test_torch_refine_smoke.py:954 — Stage C detector microslip smoketest enforcing REFINE-007/011/012 gates.
Next Up (optional):
- If ROI closures staying disabled proves too expensive, capture a profiling run comparing ROI vs panel closure timing so we can consider adaptive minibatching in a follow-up loop.
