Summary: Persist Stage C best-snapshot telemetry so the microslip smoketests stop reporting the last (regressed) LBFGS iterate and REFINE-007 can pass again on both detector sizes.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T175316Z/collect_stage_c_small.log; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T175316Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T175316Z/pytest_stage_c_small.log; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T175316Z/collect_stage_c_full.log; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T175316Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T175316Z/pytest_stage_c_full.log
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T175316Z/
Do Now:
- Implement: dbex/refinement/stage_c_impl.py::_build_stage_c_lbfgs (and `_run_stage_c_lbfgs`) so best-snapshot tuples (`best_loss_full_c`, `chi_squared_best_c`, `masked_mse_best_c`, `best_params_snapshot_c`) are written back to `telemetry_state` whenever they change, and the final telemetry/Bragg regeneration reloads that snapshot before logging chi².
- Validate: Run `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` with both `--smoke-detector-size=small` and `--smoke-detector-size=full` (commands above) so REFINE-007 proves ≤0.05% chi² regression and ≥80% offset reduction once the best-snapshot bug is fixed.
How-To Map:
1. In `_build_stage_c_lbfgs`, after updating `best_loss_full_c`, `chi_squared_best_c`, `masked_mse_best_c`, or `best_params_snapshot_c`, immediately assign the new values back into `telemetry_state[...]` so `_run_stage_c_lbfgs` can see them later.
2. In `_run_stage_c_lbfgs`, mirror that persistence when the final candidate validation runs: compare against the stored best tuple, update `telemetry_state` accordingly, and always reload `distance_offset_raw` from `best_params_snapshot_c` before the final `compute_loss_stage_c`/`bragg_full` generation.
3. Ensure `chi_squared_trace_full` appends the restored best value (not the degraded candidate) and keep `_record_stage_telemetry` ahead of the REFINE-007 asserts so logs exist even on failure.
4. Re-run the mapped collect-only command for the small detector to confirm the selector still collects.
5. Execute the small-detector smoketest with telemetry env vars set, capture the pytest log + JSON, and expect χ² regression ≤0.05% with `roi_mode`/`validation_scope` unchanged.
6. Repeat the collect-only + telemetry run for the full detector; archive logs under the artifact directory.
7. Run `plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py --telemetry-small ... --telemetry-full ... --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T175316Z/stage_c_warm_cache_report.json` so the Phase D.4 telemetry trend stays comparable.
Pitfalls To Avoid:
- Do not relax REFINE-007 tolerances; the goal is to fix Stage C telemetry, not mask the regression.
- Keep `_record_stage_telemetry` before the asserts so failures still capture JSON evidence.
- Do not touch Stage C optimizer hyperparameters or ROI sampling knobs in this loop—only fix the telemetry persistence bug.
- Preserve the existing env vars (`AUTHORITATIVE_CMDS_DOC`, `DBEX_SMOKE_SIGMA_SOURCE`, `KMP_DUPLICATE_LIB_OK`, `NANOBRAGG_DISABLE_COMPILE`) so runs remain comparable to previous artifacts.
- When persisting best tuples, avoid mutating the tensor objects in place—keep the CPU list snapshot so `distance_offset_raw` can reload cleanly.
- Ensure collect-only runs succeed before firing the expensive smoketests; if a selector stops collecting, halt and capture the issue.
- Keep telemetry key names stable (`roi_mode`, `validation_scope`, `chi_squared_trace_full`) to avoid breaking existing analyzers/scripts.
If Blocked:
- Stop after the first failing selector, archive the log + telemetry JSON in this loop’s artifact dir, and record the failure signature plus stack trace in docs/fix_plan.md Attempts History. Set galph_memory to `state=blocked` so we regroup before considering tolerance adjustments.
Findings Applied (Mandatory):
- REFINE-007 — Stage C detector microslip tests must show ≤0.05% chi² regression and ≥80% offset reduction; fixing the best-snapshot persistence should restore that guarantee.
- REFINE-010 — Stage A auto-panel policy dictates when ROI closures are active; Stage C must keep following the telemetry signal we already plumbed.
- REFINE-011 — Full validations must run in panel scope whenever Stage B/C are enabled; the best-snapshot fix must preserve this guard.
- REFINE-012 — ROI-mode provenance stays diagnostic (`roi_mode_reason`, `validation_scope`) and cannot regress while touching telemetry.
Pointers:
- docs/spec-db-workflow.md:120-150 — ROI minibatching clause + panel-validation contract driving this fix.
- docs/findings.md:60-78 — REFINE-007/010/011/012 guardrails cited above.
- dbex/refinement/stage_c_impl.py:300-780 — Closure + optimizer logic that currently drops the best snapshot.
- tests/dbex/test_torch_refine_smoke.py:1080-1280 — Smoketest asserts and telemetry recorder that expose the regression.
Next Up (optional): If χ² still regresses after this fix, prep a follow-up loop to capture per-iteration chi² traces and reconsider LBFGS tolerances before any gate changes.
