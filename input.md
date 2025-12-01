Summary: Restore Stage C ROI-mode closures while keeping panel validations explicit so detector-offset runs stop regressing, then prove the fix with both Stage C smoketests.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T174500Z/collect_stage_c_small.log; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T174500Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T174500Z/pytest_stage_c_small.log; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T174500Z/collect_stage_c_full.log; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T174500Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T174500Z/pytest_stage_c_full.log
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T174500Z/
Do Now:
- Implement: dbex/refinement/stage_c_impl.py::_build_stage_c_params (and the `_run_stage_c_lbfgs` telemetry/perf-counter emission) so Stage C ROI closures remain active whenever Stage A telemetry reports `roi_mode="roi"` even if panel validations are forced; plumb a separate `validation_scope` field through `stage_c_context`/perf counters and teach tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip to assert the new telemetry, proving closures vs validations stay aligned with REFINE-011.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T174500Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T174500Z/pytest_stage_c_full.log
How-To Map:
1. Update `dbex/refinement/stage_c_impl.py` to drop the `and not force_panel_validation` guard for ROI closures, compute `validation_scope = "panel"` whenever the Stage A perf counters set `force_panel_validation`, and include that scope in `stage_c_context` and the perf-counter dict emitted by `_run_stage_c_lbfgs`.
2. Adjust `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` so it checks both `roi_mode` (closure mode) and the new `validation_scope` perf-counter field, expecting `"panel"` whenever Stage B/C is enabled or the ROI threshold disables sampling.
3. Run the mapped collect-only command for the small dataset and ensure it succeeds (guards the selector health before code runs).
4. Execute the small-detector smoketest with telemetry (env vars above) and capture `pytest_stage_c_small.log` plus `telemetry_stage_c_small.json`.
5. Repeat the collect-only and telemetry runs for the full detector (commands above) so we have canonical evidence for the ROI-mode fix.
6. Re-run `plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py` pointing at the new telemetry files, writing both the JSON report and CLI output into the same artifact directory.
Pitfalls To Avoid:
- Do not remove the `force_panel_validation` guard when calling `compute_loss_stage_c` for full validations—panel scope is still required for REFINE-007.
- Keep ROI closures gated on Stage A telemetry (`roi_mode`) plus warm cache availability; do not invent new knobs or sample fractions.
- Stage C perf counters must advertise both `roi_mode` and the new `validation_scope`; avoid overwriting one with the other or changing key names (tools read them today).
- Leave Stage B/C env vars intact (`KMP_DUPLICATE_LIB_OK`, `NANOBRAGG_DISABLE_COMPILE`, `DBEX_SMOKE_SIGMA_SOURCE`) so telemetry stays comparable to earlier loops.
- When editing the smoketest, keep `_record_stage_telemetry` call order untouched—only extend the assertions.
- If the pytest selector still fails after the ROI-mode fix, do not rerun blindly; capture telemetry/logs once and stop for supervisor review.
If Blocked:
- Archive the failing collect/run logs plus telemetry into `plans/active/PERF-WARM-SIM-001/reports/2025-12-01T174500Z/`, quote the failure signature in docs/fix_plan.md Attempts History, and set galph_memory state=blocked so we can decide between reverting the ROI change or recalibrating REFINE-007.
Findings Applied (Mandatory):
- REFINE-010 (docs/findings.md:65) — Stage A automatically forces panel closures when canonical ROI count ≤32 or Stage B/C run; Stage C must follow the same heuristic for telemetry.
- REFINE-011 (docs/findings.md:72) — Full validations must use the same population as Stage A panel scope via `force_panel_validation`; our change keeps that guard in place.
- REFINE-012 (docs/findings.md:73) — ROI-mode provenance must be recorded; we’re refining it so closures stay ROI-aware while validation scope is explicit.
- REFINE-007 (docs/findings.md:60) — Chi² regression gate (≤0.05%) remains the acceptance metric; evidence from the updated smokes must show the gate passing again before any tolerance discussion.
Pointers:
- docs/spec-db-workflow.md:90 — Optimization Strategy clause that permits ROI minibatching when periodic full validations occur.
- docs/findings.md:65-74 — REFINE-010/011/012 gate rationale that drives this ROI/validation alignment.
- dbex/refinement/stage_c_impl.py:178-340 — Current Stage C ROI-mode + `force_panel_validation` logic we need to adjust.
- tests/dbex/test_torch_refine_smoke.py:990-1250 — Stage C smoketest assertions and telemetry recording hook that must add the new perf-counter field.
Next Up (optional): If Stage C still regresses after ROI closures return, prep a follow-up plan to adjust LBFGS hyperparameters or document a REFINE-007 gate recalibration backed by the new telemetry.
