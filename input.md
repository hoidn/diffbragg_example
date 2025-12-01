Summary: Capture Stage B parity evidence by logging per-panel chi² + parameter snapshots when the REFINE-FLOW-001 guard fires, then prove the guard/test matrix still passes on the small detector.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T153327Z/telemetry_stage_bc_small.json pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small; pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T153327Z/
Do Now:
- Implement: dbex/refinement/stage_b_impl.py::_run_stage_b_lbfgs — replace the placeholder JSON payload with a real per-panel chi²/masked-MSE breakdown (loop over panels with `compute_loss_stage_b([pid], is_full=True, force_panel_eval=True)`), record the Stage A canonical snapshot plus the reconstructed tensors Stage B actually used, and write the diff file into the `DBEX_SMOKE_TELEMETRY_PATH` directory (or cwd fallback) before raising the REFINE-FLOW-001 RuntimeError.
- Implement: tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload — add a deterministic unit test that stubs the canonical baseline chi² to force the guard, asserts the RuntimeError message cites REFINE-FLOW-001, and inspects `stage_b_baseline_diff.json` for the new schema (per-panel list + parameter snapshots).
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T153327Z/telemetry_stage_bc_small.json pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T153327Z/pytest_stage_bc_small.log, then pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload > plans/active/ARCH-REFINE-001/reports/2025-12-01T153327Z/pytest_stage_b_guard.log.
How-To Map:
1. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small > plans/active/ARCH-REFINE-001/reports/2025-12-01T153327Z/collect_stage_bc_small.log
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T153327Z/telemetry_stage_bc_small.json pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T153327Z/pytest_stage_bc_small.log
3. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload > plans/active/ARCH-REFINE-001/reports/2025-12-01T153327Z/pytest_stage_b_guard.log
Pitfalls To Avoid:
- Do not relax the 0.1% REFINE-FLOW-001 tolerance or swallow the RuntimeError; the guard must stay loud when parity fails.
- Reuse the existing Stage A warm cache/context when looping per panel so we don’t instantiate new simulators or mutate Stage A telemetry.
- Keep JSON writing stdlib-only and derive the artifacts directory from DBEX_SMOKE_TELEMETRY_PATH; never hard-code timestamped paths.
- Only emit `stage_b_baseline_diff_path` when the guard raises so the smoketest assertion (expecting None on pass) stays valid.
- Ensure the unit test forces the guard without allocating CUDA tensors (use CPU tensors and small dummy inputs) so it stays cheap and deterministic.
- Don’t introduce additional dependencies or scripts; stick to the Environment Freeze and existing fixtures/data listed in docs/data_dependency_manifest.md.
- Preserve variance-weighted chi² semantics in the per-panel breakdown; no ad-hoc metrics or ROI-only sampling for the guard.
If Blocked:
- If the per-panel instrumentation can’t be wired because `stage_b_eval_stage_a_ctx` lacks panel simulators, capture the stack trace, the failing telemetry JSON, and the partially written diff file (if any), update docs/fix_plan.md Attempts History with the error signature, and pause further changes until the context bug is resolved.
Findings Applied (Mandatory):
- REFINE-FLOW-001 — Guard Stage B baseline parity within 0.1% and provide actionable diagnostics when it fails.
- ARCH-ENGINE-003 — Ensure the new telemetry fields flow through RefinementTelemetry rather than bypassing the engine contract.
- PHYSICS-LOSS-001 — All comparisons remain in variance-weighted chi² space; no alternate metrics.
- POLICY-001 — Environment stays frozen; no new dependencies or rebuild steps.
Pointers:
- docs/fix_plan.md:719 — Phase E.1 scope and updated instrumentation plan.
- docs/findings.md:71 — REFINE-FLOW-001 context and tolerance requirements.
- dbex/refinement/stage_b_impl.py:1107 — Current guard stub that needs the per-panel JSON payload.
- tests/dbex/test_torch_refine_smoke.py:1400 — Smoke assertions that consume the Stage B parity telemetry.
- docs/data_dependency_manifest.md:52 — refGeom_small + sigma assets used by the small-detector smoke selectors.
Next Up (optional): Phase E.2 — once instrumentation lands, patch Stage B reconstruction helpers so the guard never trips on canonical runs and rerun the same selectors.
