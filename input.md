Summary: Rehydrate Stage C best-snapshot telemetry after the LBFGS step so the smoketests log the optimal chi² sample (not the last iterate) and REFINE-007 passes again.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T181100Z/collect_stage_c_small.log; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T181100Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T181100Z/pytest_stage_c_small.log; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T181100Z/collect_stage_c_full.log; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T181100Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T181100Z/pytest_stage_c_full.log
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T181100Z/
Do Now:
- Implement: dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs (touching `_build_stage_c_lbfgs` as needed) so the best-snapshot tuples persisted in `telemetry_state` are reloaded immediately after `stage_c_optimizer.step(closure_stage_c)`/`_apply_baseline_detector_prior()`—`final_loss_value_c`, `chi_squared_trace_full`, and the Bragg regeneration must consume the refreshed tuples, and emit a targeted error if `chi_squared_best_c` never populates.
- Validate: Run the small + full detector variants of `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` with the telemetry env vars above so REFINE-007 proves ≤0.05% chi² regression alongside ≥80% offset reduction, then re-run the warm-cache summarizer on both telemetry JSONs.
How-To Map:
1. In `_run_stage_c_lbfgs`, move the `telemetry_state[...]` reads for `chi_squared_best_c`, `best_loss_full_c`, `masked_mse_best_c`, and `best_params_snapshot_c` to immediately after the LBFGS step (or re-read them there) so locals reflect closure updates before the final validation block executes; raise a descriptive RuntimeError if any tuple stays at `(inf, -1)` by the time the final trace is appended.
2. Ensure the final trace append (`loss_trace_full_c`/`chi_squared_trace_full_c`) records the refreshed best tuple and that `distance_offset_raw` is reloaded from the stored snapshot before regenerating `bragg_full`; keep `_build_stage_c_lbfgs` persistence hooks intact and only convert the best tuples to list wrappers if rehydration proves insufficient.
3. Capture the small-detector collect-only log first to double-check selector health, then run the mapped small smoketest with telemetry env vars and archive the pytest log plus JSON to the new artifact directory.
4. Repeat the collect-only + smoketest flow for the full detector, reusing the same env vars but pointing telemetry output at the `_full` JSON.
5. Run `plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-01T181100Z/telemetry_stage_c_small.json --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-01T181100Z/telemetry_stage_c_full.json --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T181100Z/stage_c_warm_cache_report.json` so Phase D.4 telemetry stays comparable.
6. Update `summary.md` in the artifact directory with the key diff and attach the pytest + telemetry filenames so we can stitch the evidence trail quickly.
Pitfalls To Avoid:
- Do not relax the REFINE-007 gate; the goal is to fix telemetry, not mask the regression.
- Keep `_record_stage_telemetry` before all asserts so failures still emit JSON.
- Avoid changing LBFGS hyperparameters or ROI sampling toggles in this loop—only touch the telemetry rehydration logic.
- Preserve the telemetry schema (`chi_squared_best_c`, `best_loss_full_c`, `roi_mode`, `validation_scope`), since probes/scripts consume these keys.
- Remember that Stage C closures already run in ROI mode; do not accidentally disable that path while editing the best tuple plumbing.
- Use the canonical env vars (`AUTHORITATIVE_CMDS_DOC`, `DBEX_SMOKE_SIGMA_SOURCE`, `KMP_DUPLICATE_LIB_OK`, `NANOBRAGG_DISABLE_COMPILE`) so results remain comparable to earlier loops.
- If best tuples never populate, stop and record the failure—do not force the test to pass by overriding telemetry values.
If Blocked:
- Halt after the first failed smoketest, archive its pytest log + telemetry JSON in the artifact directory, note the failure signature in docs/fix_plan.md Attempts History, and set galph_memory to `state=blocked` so we can regroup before pursuing gate adjustments.
Findings Applied (Mandatory):
- REFINE-007 — Stage C smoketests must report ≤0.05% chi² regression with ≥80% offset reduction; telemetry rehydration must restore that guarantee rather than loosening tolerances.
- REFINE-010 — Stage A auto-panel policy still dictates ROI closures; the fix cannot reintroduce ROI-mode drift.
- REFINE-011 — Panel-scope validations remain mandatory when Stage B/C run; ensure the final telemetry still reflects panel validation scope while closures stay ROI-aware.
- REFINE-012 — `roi_mode_reason` and `validation_scope` telemetry must stay intact so tooling can prove closure vs validation populations.
- REFINE-013 — Persisted best tuples must be reloaded after the LBFGS step; this loop specifically addresses the stale-local issue identified in the latest artifacts.
Pointers:
- docs/spec-db-workflow.md:124 — Optimization Strategy clause permitting ROI minibatching with full-panel validations.
- docs/fix_plan.md:1062 — Current PERF-WARM-SIM-001 Phase D.4 plan + commands for this effort.
- dbex/refinement/stage_c_impl.py:338 — Closure + telemetry-state plumbing that now persists best tuples.
- dbex/refinement/stage_c_impl.py:691 — `_run_stage_c_lbfgs` block where the locals must be refreshed after `stage_c_optimizer.step`.
- tests/dbex/test_torch_refine_smoke.py:954 — Stage C detector microslip smoketest asserting REFINE-007 telemetry.
Next Up (optional): Capture a per-iteration chi² trace (via summarize script) if the refreshed telemetry still diverges so we can consider LBFGS tolerance tuning in the next loop.
