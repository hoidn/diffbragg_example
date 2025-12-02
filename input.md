Summary: Add Stage C to the typed RefinementSharedContext pipeline so Stage helpers no longer juggle 10+ positional args and telemetry/artifacts stay aligned with the Stage A/B refactors.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: main
Mapped tests:
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T022454Z/

Do Now:
- Implement: Extend `dbex/refinement/context.py::RefinementSharedContext` with an optional `baseline_detector` field (default `None`) and teach `.from_inputs(...)` to accept it. Update `StageA.run` and `StageB.run` to pass the baseline detector when constructing the shared context so downstream stages can reuse it without extra kwargs.
- Implement: In `dbex/refinement/stage_c.py`, import `RefinementSharedContext`, build it once (using the existing sigma floor cache dict) and pass it to `_build_stage_c_params`, `_build_stage_c_lbfgs_closure`, and any other helper calls instead of threading config/device/dtype/detector/inputs individually.
- Implement: Add a `shared_context: Optional[RefinementSharedContext] = None` compatibility shim to `dbex/refinement/stage_c_impl.py::_build_stage_c_params` and `_build_stage_c_lbfgs_closure`. When `shared_context` is provided, derive `config`, `device`, `dtype`, `detector`, `hkl_*`, `panel_slices`, and `sigma_floor_sq_cache` from it; retain the legacy code path when the dataclass is absent. Keep ROI/warm-cache logic untouched aside from reading the shared context.
- Implement: Thread the shared context through Stage C helper invocations (including any warm-cache dictionary builds) while leaving legacy kwargs for external callers. Ensure telemetry still records `validation_scope`, `roi_mode_reason`, etc. untouched.
- Validate: Capture `--collect-only` plus full runs for `test_stage_c_detector_microslip` on both `--smoke-detector-size=small` and `full`, writing logs/telemetry into the new artifact directory. Then rerun `test_stage_a_engine_delegation_telemetry` to prove the extended dataclass didn’t regress Stage A telemetry injection.

How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T022454Z/collect_stage_c.log`
2. Small detector run: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T022454Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T022454Z/pytest_stage_c_small.log`
3. Full detector run: same command as step 2 but set `DBEX_SMOKE_DETECTOR_SIZE=full` and swap the telemetry/log filenames to `telemetry_stage_c_full.json` / `pytest_stage_c_full.log`.
4. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T022454Z/pytest_stage_a_engine.log`

Pitfalls To Avoid:
- Keep the legacy Stage C helper signatures working; external tools may still call them with individual args while we roll out the dataclass.
- Don’t mutate the warm-cache structures when extracting references from the shared context—`sigma_floor_sq_cache` must remain the same dict so Stage A/B/C reuse it safely.
- Preserve Stage C ROI/validation telemetry (`roi_mode_reason`, `validation_scope`); the refactor should be mechanical and must not change REFINE-010/011/012 behavior.
- No env churn: use the existing virtualenv/toolchain; if an import fails, stop and log the blocker instead of installing packages.

If Blocked:
- If the shared-context shim exposes missing fields (e.g., baseline detector absent), capture the exception plus stack trace in `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T022454Z/blocked.md`, update docs/fix_plan.md with the failure signature, and halt.
- If Stage C smoketests continue to fail after the refactor (unrelated to existing PERF-WARM diagnostics), archive the telemetry/logs, mark the initiative blocked in galph_memory.md, and await supervisor direction before attempting more code changes.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage helpers must stop passing 10+ positional args; this change wires Stage C into the typed context.
- ARCH-ENGINE-002 / ARCH-ENGINE-003 — RefinementStage wrappers must honor the engine protocol and telemetry schema; rerunning `test_stage_a_engine_delegation_telemetry` verifies the enrichment is still in place.

Pointers:
- plans/active/ARCH-STAGE-CONTEXT-001/implementation.md:40 — Phase A checklist outlining Stage C typed-context scope.
- docs/fix_plan.md:86 — Fix-plan entry summarizing the initiative and current next actions.
- docs/data_dependency_manifest.md:50 — Smoke-test data dependencies/env overrides referenced in the How-To map.
