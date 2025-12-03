### Turn Summary
Hoisted Stage A/C shared dependencies to module scope: json, Path, Detector, Crystal, Simulator, config factories, warnings moved from inline to module-level imports per ARCH-ENGINE-002.
Removed ~18 inline import statements from Stage A/C hot-path helpers (_build_stage_a_context, _compute_panel_loss, _retarget_stage_a_detectors, _run_stage_c_lbfgs, diagnostics writers); left geometry helpers and circular-dep imports as documented exceptions.
Stage A smoke tests passed (test_stage_a_expansion 7.42s, test_stage_a_engine_delegation_telemetry 7.33s); Stage C smoke failed with pre-existing ARCH-TELEMETRY-001 collector issue (closure_evals=0, early_stop).
Next: Supervisor reviews Stage C failure alignment with ARCH-TELEMETRY-001 work; Phase C process-noise cleanup deferred until telemetry stabilizes.
Artifacts: plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-03T223500Z/ (pytest_stage_a_expansion.log, pytest_stage_a_engine_telemetry.log, pytest_stage_c_smoke.log, stage_a/c_inline_imports_check.txt)

### Turn Summary
Scoped Stage A/C lazy-import cleanup for ARCH-LAZY-IMPORTS-001 under the problems.md guard while staying in planning/Mode none.
Updated plans/active/ARCH-LAZY-IMPORTS-001/implementation.md and docs/fix_plan.md with the Stage A/C hoist scope, validation selectors, and artifacts path.
Next: Ralph hoists the Stage A/C imports, reruns the Stage A/B/C smoketests listed in input.md, and saves the logs under the reserved report directory.
Artifacts: plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-03T223500Z/
