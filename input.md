Summary: Inline Stage B’s LBFGS closure so `StageB.run` owns the compute/closure helpers, keeps CPU fallback + warm-cache telemetry untouched, and retire the legacy helper export.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small (expected failure logged per `reports/2025-12-02T020900Z/blocked.md`)
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T052800Z/

Do Now:
- FocusItem: ARCH-STAGE-CONTEXT-001 Phase B.2 — move Stage wrappers away from helper exports.
- Implement: `dbex/refinement/stage_b.py::StageB._build_lbfgs_closure` — copy the existing `_build_stage_b_lbfgs_closure` body from `dbex/refinement/stage_b_impl.py` into a private method on `StageB`, keeping the nested `compute_loss_stage_b` / `closure_stage_b` functions, the `RefinementSharedContext` typed path, CPU fallback routing, and the env-gated panel diagnostics hook exactly as-is. Update `StageB.run` to call the method instead of the helper, drop the `_build_stage_b_lbfgs_closure` import, and leave `_build_stage_b_params` / `_run_stage_b_lbfgs` untouched.
- Update: Remove `_build_stage_b_lbfgs_closure` from `dbex/refinement/stage_b_impl.py` (replace with a comment like Stage A’s note), adjust the module docstring and `dbex/refinement/context.py` references so they point at the new Stage-owned closure, and delete the unused import from `dbex/nanobrag_refinement.py`.
- Validate: rerun the Stage B smokes per TESTING_GUIDE.
  1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md mkdir -p plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T052800Z`
  2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T052800Z/pytest_stage_b_shell.log`
  3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T052800Z/pytest_stage_b_per_reflection.log` (expected to reproduce the ASU-modifier gradient defect; capture the log and reference the existing blocked note).

How-To Map:
- Keep the lazy imports embedded in the nested functions (`dbex.nanobrag_bridge`, `nanobrag_torch.models`, etc.) to preserve warm-cache behavior and circular-import safety.
- Preserve the `shared_context` compatibility shim so legacy callers (if any) still receive the ValueError guard; only StageB.run should send the typed context, but external tooling may still exercise the legacy path.
- After deleting the helper, update `dbex/refinement/stage_b_impl.py`’s “Provides” section + comment similar to Stage A so future readers know the closure now lives on the Stage class, and trim any unused imports introduced by the removal.
- When running the tests, use the canonical env flags from docs/TESTING_GUIDE (`KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`, `DBEX_SMOKE_SIGMA_SOURCE=cli_override`, `DBEX_SMOKE_DETECTOR_SIZE=small`). Archive pytest logs in the reserved artifact directory.

Pitfalls To Avoid:
- Do not rewrite `_run_stage_b_lbfgs` or `_build_stage_b_params`; only relocate the closure builder. Changing Stage B optimization semantics would violate REFINE-008.
- Preserve CPU fallback (`use_stage_b_cpu_fallback`) and warm-cache plumbing — that code is performance-critical and validated by PERF-WARM-011/012.
- Maintain telemetry accumulation (`variance_floor_*`, perf counters, baseline parity diff fields) so `StageBArtifacts` and RefinementTelemetry stay schema-compatible.
- Leave the softplus + clamp logic untouched for shell modifiers and the ASU modifier exp/clamp path; altering these would change physics gates.
- Keep the env-gated per-panel diagnostics (`DBEX_STAGE_C_PANEL_DIAG_DIR`) emitting identical JSON so PERF-WARM-SIM-001 tooling keeps working.
- Update doc references (`dbex/refinement/context.py`, `docs/fix_plan.md`) and remove the unused helper import from `dbex/nanobrag_refinement.py`; stale references will confuse future loops.
- Per-reflection smoke currently fails due to the known gradient-flow issue; do not treat that as a regression, but do capture the failure log so we can keep the evidence thread tied to `reports/2025-12-02T020900Z/blocked.md`.

If Blocked:
- If the closure relocation introduces circular-import issues or undefined symbols, stop after capturing the traceback, add the details to `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T052800Z/blocked.md`, and flag it in docs/fix_plan.md so we can reassess helper placement.
- If either smoke selector fails with a new regression (e.g., shell mode no longer passes), archive the pytest log + telemetry in the artifacts directory and record the error signature plus git diff in the same blocked.md. If only the per-reflection failure reproduces the known ASU gradient defect, note “expected failure — see 2025-12-02T020900Z blocked.md” and proceed.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — eliminate the Stage B 11-argument helper clump by moving the closure logic into the Stage wrapper and keeping typed contexts authoritative.
- REFINE-008 — Stage B smokes must preserve the ±1 % modifier / ≤1e-6 loss regression gate, so the relocated closure must not perturb physics, shells, or telemetry.

Pointers:
- dbex/refinement/stage_b_impl.py:816-1190 — current `_build_stage_b_lbfgs_closure` body to relocate; note the shared-context shim + CPU fallback logic.
- dbex/refinement/stage_b.py:200-410 — StageB.run wiring where the closure is invoked and StageBArtifacts assembled.
- docs/spec-db-workflow.md:59-64 — Stage B normative behavior (tricubic+halo requirement, modifier gates) to keep in mind while relocating code.
- plans/active/ARCH-STAGE-CONTEXT-001/implementation.md:70-86 — Phase B.2 checklist describing this subtask and validation expectations.

Next Up (optional):
- B2.3 — repeat the inlining for `_build_stage_c_lbfgs_closure` once Stage B lands, then proceed to Phase B.3 telemetry dataclasses.
