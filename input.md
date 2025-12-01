Summary: Align Stage C “full” validations with the new Stage A panel baseline and rerun the Stage C detector microslip smokes (small + full) so REFINE-007 parity is restored.
Mode: Parity
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/
Do Now:
- Implement: dbex/refinement/stage_a.py::StageA.run — tag telemetry/perf counters with the `force_panel_validation` flag (`validation_scope="panel"` when true) so downstream stages (and tests) know when the canonical chi² is panel-scope.
- Implement: dbex/refinement/stage_c_impl.py::_build_stage_c_lbfgs_closure / _run_stage_c_lbfgs and dbex/refinement/stage_c.py::StageC.run — plumb the Stage A validation flag into Stage C, allow `compute_loss_stage_c(..., force_panel_eval=True)` to bypass ROI-mode for full validations, and ensure Stage C initial/final telemetry uses panel evaluations whenever Stage A canonical telemetry does.
- Validate: Run the Stage C detector microslip smoketest twice (small + full) with the canonical env flags, capturing collect-only logs plus telemetry JSONs under the new artifact directory; tests must pass with ≤0.05% χ² regression on the full detector.
How-To Map:
1. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/collect_stage_c_small.log
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/pytest_stage_c_small.log
3. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/collect_stage_c_full.log
4. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/pytest_stage_c_full.log
Pitfalls To Avoid:
- Keep `NANOBRAGG_DISABLE_COMPILE=1` and run on the canonical CUDA device; perf counters/telemetry are only comparable under the frozen env.
- Do NOT relax REFINE-007 chi²/offset gates or tweak test thresholds; the fix must make the gate pass, not silence it.
- Preserve ROI-mode closures for Stage C sampling—only the “full” validations should bypass ROI slicing when panel scope is requested.
- Telemetry dicts are large; stream read/write and assert the new `validation_scope` field exists before trusting outputs.
- Reuse the canonical datasets from docs/data_dependency_manifest.md; missing assets are blockers to record, not reasons to invent new fixtures.
- Avoid touching warm-cache factory helpers or shared simulator code—scope stays within Stage A/B/C modules cited above.
- Capture all logs/telemetry under the new timestamped artifact dir; prior reports remain immutable.
If Blocked:
- If either smoketest still fails the χ² gate after the code change, stop immediately, archive the failing log/telemetry under the artifact dir, and log the regression signature plus suspected cause in docs/fix_plan.md Attempts History and galph_memory (state=blocked) before proceeding.
Findings Applied (Mandatory):
- REFINE-007 — enforce the detector-offset and chi² regression gates when reviewing Stage C telemetry.
- REFINE-010 — Stage A auto-panel rule (≤32 ROIs or Stage C enabled) remains in effect; validation scope must respect it.
- REFINE-011 — new finding documenting the ROI-vs-panel mismatch; this Do Now implements its mitigation.
Pointers:
- docs/fix_plan.md §PERF-WARM-SIM-001 (2025-12-01T163900Z entry) — planning notes + commands for this loop.
- plans/active/PERF-WARM-SIM-001/implementation.md (Phase D) — context on Stage C warm-cache scope and exit criteria.
- docs/spec-db-workflow.md §§62-75 — Stage C detector refinement contract and telemetry expectations cited by the smoketest.
