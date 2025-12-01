Summary: Rehydrate Stage C best-snapshot telemetry after LBFGS so REFINE-007 evaluations log the stored best chi² before rerunning the Stage C detector microslip smokes.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/collect_stage_c_small.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small \| tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/pytest_stage_c_small.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/collect_stage_c_full.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full \| tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/pytest_stage_c_full.log
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/
Do Now:
- Implement: dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs must refresh the persisted `chi_squared_best_c`, `masked_mse_best_c`, `best_loss_full_c`, and `best_params_snapshot_c` from `telemetry_state` immediately after the LBFGS step so the final validation, trace append, and Bragg regeneration consume the true best snapshot; raise a targeted RuntimeError if the tuples never populated instead of logging the last iterate.
- Validate: Re-run `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` for `--smoke-detector-size=small` and `--smoke-detector-size=full` with telemetry capture, then rerun the warm-cache summarizer so REFINE-007 proves ≤0.05% chi² regression, ≥80% offset reduction, and `chi_squared_trace_full[-1]` equals the Stage A final entry.
How-To Map:
1. In `dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs` (around line 641), move the `telemetry_state[...]` reads for the best tuples to immediately after `stage_c_optimizer.step(closure_stage_c)`/`_apply_baseline_detector_prior()` and assert `chi_squared_best_c[0] < float("inf")` once a best snapshot exists; if it remains infinite after the first full validation, raise `RuntimeError("Stage C best snapshot never recorded")`.
2. Ensure the refreshed tuples drive `final_loss_value_c`, the `loss_trace_full_c`/`chi_squared_trace_full_c` append, and the `distance_offset_raw` reload before regenerating `bragg_full`; keep the REFINE-013 persistence hooks intact and only convert to list wrappers if the refreshed tuples still fail to propagate.
3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/collect_stage_c_small.log`
4. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small \| tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/pytest_stage_c_small.log`
5. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/collect_stage_c_full.log`
6. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full \| tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/pytest_stage_c_full.log`
7. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/telemetry_stage_c_small.json --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/telemetry_stage_c_full.json --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/stage_c_warm_cache_report.json`
8. Update `plans/active/PERF-WARM-SIM-001/reports/2025-12-01T183500Z/summary.md` with the code diff summary, chi² deltas, and log filenames.
Pitfalls To Avoid:
- Do not relax REFINE-007 thresholds; the telemetry fix must make the existing ≤0.05% gate pass.
- Keep Stage A ROI/panel policy untouched—only rehydrate Stage C best tuples.
- Preserve `roi_mode`, `validation_scope`, and `roi_mode_reason` telemetry fields so REFINE-010/011/012 evidence stays intact.
- Retain `_record_stage_telemetry` before asserts; failures must still emit JSON.
- Ensure `distance_offset_raw` reload uses tensors on the original device/dtype; do not detach to numpy mid-run.
- Use the canonical smoke env flags (AUTHORITATIVE_CMDS_DOC, DBEX_SMOKE_SIGMA_SOURCE, KMP_DUPLICATE_LIB_OK, NANOBRAGG_DISABLE_COMPILE) to keep runs comparable to prior artifacts.
- Capture collect-only logs before each smoketest so selector health is documented.
- If best tuples remain `inf`, stop and record the failure; do not overwrite telemetry with guessed numbers.
If Blocked:
- Stop after the first failing smoketest, save its pytest log + telemetry to the artifact directory, capture the error signature in docs/fix_plan.md Attempts History, and flag Galph memory as `state=blocked` so we can reassess the best-snapshot plumbing before rerunning tests.
Findings Applied (Mandatory):
- REFINE-007 — Chi² gate stays at ≤0.05% regression with ≥80% detector offset reduction; the refreshed telemetry must satisfy the spec instead of changing the threshold.
- REFINE-010 — Stage A ROI auto-panel policy remains the authority; Stage C must continue to follow the telemetry-driven ROI decision when restoring best snapshots.
- REFINE-011 — Panel-scope validations stay mandatory when Stage B or C runs, so the refreshed telemetry must still tag `validation_scope="panel"`.
- REFINE-012 — `roi_mode_reason`/`validation_scope` provenance fields cannot regress; confirm the rehydration leaves them unchanged.
- REFINE-013 — Persisted best tuples must be reloaded after LBFGS; this loop completes that requirement by rehydrating `_run_stage_c_lbfgs`.
Pointers:
- docs/spec-db-workflow.md:124 — Optimization Strategy clause allowing ROI minibatching with full-panel validations.
- docs/fix_plan.md:1077 — Current PERF-WARM-SIM-001 Phase D.4 scope describing the best-snapshot rehydration plan.
- dbex/refinement/stage_c_impl.py:600 — Closure logic persisting best tuples into `telemetry_state`.
- tests/dbex/test_torch_refine_smoke.py:954 — Stage C detector microslip smoketest applying REFINE-007/011 checks.
Next Up (optional):
- If the refreshed telemetry still shows residual regressions, capture per-iteration chi² traces via the summarizer to decide whether LBFGS tolerances need tuning in a follow-on loop.
