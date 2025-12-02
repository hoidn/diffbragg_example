Summary: Seed Stage C telemetry with a true baseline snapshot before LBFGS so panel-mode χ² traces always include the Stage A reference and REFINE-007 regressions are diagnosable without ad-hoc probes.
Mode: Perf
InitiativeType: perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: main
Mapped tests:
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-02T050500Z/

Do Now:
- Implement: In `dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs` (near lines 560-930) evaluate `compute_loss_stage_c` across all panels once *before* `_apply_baseline_detector_prior()` to capture the Stage A panel-mode χ² / masked-MSE while `distance_offset_raw` is still zero. Seed `loss_trace_full_c`, `chi_squared_trace_full_c`, `masked_mse_trace_full_c`, `chi_squared_best_c`, `masked_mse_best_c`, `best_loss_full_c`, and `best_params_snapshot_c` with this iteration `-1` baseline so telemetry JSON always includes the canonical reference.
- Implement: Update `plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py` to parse the new baseline tuple from `chi_squared_trace_full` and surface `stage_c_initial_chi2` plus Δ% vs Stage A in the warm-cache report, keeping the script stdlib-only.
- Implement: Tighten `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` so it asserts `telemetry_c.chi_squared_trace_full[0]` now matches the Stage A final χ² within a 1e-6 relative tolerance and document the guaranteed baseline row.
- Validate: Capture `pytest --collect-only` for the Stage C smoketest, then rerun the small + full detector selectors with telemetry routed to the new artifact directory and regenerate `stage_c_warm_cache_report.json` so the refreshed summary proves the baseline row is present.

How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-02T050500Z/collect_stage_c.log`
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-02T050500Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-02T050500Z/pytest_stage_c_small.log`
3. Repeat step 2 with `DBEX_SMOKE_DETECTOR_SIZE=full` and matching telemetry/log paths (`telemetry_stage_c_full.json`, `pytest_stage_c_full.log`).
4. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-02T050500Z/telemetry_stage_c_small.json --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-02T050500Z/telemetry_stage_c_full.json --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-02T050500Z/stage_c_warm_cache_report.json`

Pitfalls To Avoid:
- Run the baseline evaluation in a `torch.no_grad()` block so the initial full-loss doesn’t pollute gradient buffers before LBFGS starts.
- Don’t mutate Stage A telemetry; all seeding lives inside Stage C’s `telemetry_state` lists so Stage A perf counters remain untouched.
- Store the seed entry with iteration `-1` to avoid off-by-one regressions in consumers that expect monotonically increasing iteration numbers.
- Keep the summarizer stdlib-only—no project imports or numpy while parsing the new fields.

If Blocked:
- If seeding the baseline throws because telemetry arrays are missing, capture the stack trace plus current telemetry_state contents in `plans/active/PERF-WARM-SIM-001/reports/2025-12-02T050500Z/blocked.md`, update docs/fix_plan.md, and halt instead of guessing.
- If the smoketest still reports χ² regressions after the baseline row appears, archive the refreshed telemetry/warm-cache report and flag PERF-WARM-SIM-001 as still blocked so we can escalate root-cause analysis next loop.

Findings Applied:
- REFINE-007 — Panel-mode χ² must never regress >0.05%; the baseline row gives us an invariant reference for that guard.
- REFINE-013 — Best-snapshot persistence required a canonical snapshot before LBFGS; seeding the telemetry satisfies that lesson.
- PHYSICS-LOSS-001/002 — Dual-metric telemetry (χ² + masked-MSE plus sigma-floor stats) must survive the refactor.

Pointers:
- dbex/refinement/stage_c_impl.py:560-930 — `_run_stage_c_lbfgs` where the baseline evaluation and telemetry seeding belong.
- tests/dbex/test_torch_refine_smoke.py:954-1254 — Stage C smoketest hooks that need the new baseline assertion.
- plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py:1-175 — Summarizer to update so the new telemetry fields show up in the report.
