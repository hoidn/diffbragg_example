Summary: Move Stage A's LBFGS closure inline so `StageA.run` owns the loss/telemetry lifecycle instead of delegating to `_build_stage_a_lbfgs_closure`, and keep the warm-cache/shared-context plumbing intact.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T040500Z/

Do Now:
- Implement: Inline the Stage A closure helper.
  1. In `dbex/refinement/stage_a.py::StageA`, add a private method (e.g., `_build_lbfgs_closure`) whose body is the current `_build_stage_a_lbfgs_closure` from `dbex/refinement/stage_a_impl.py:1225+`. Keep the nested `compute_loss_stage_a` and `closure_stage_a` functions, the ROI/panel branching, and the diagnostics plumbing (panel diag env hook, trusted-mask provenance, warm-cache retarget calls). The method should accept `param_values`, `telemetry_state`, `stage_a_context`, and the existing `RefinementSharedContext`. Return the `(compute_loss, closure)` tuple exactly as before.
  2. Update `StageA.run` to call `self._build_lbfgs_closure(...)` instead of importing `_build_stage_a_lbfgs_closure`. Remove the unused import from the top of the file. Ensure the rest of the method (params unpack, `_run_stage_a_lbfgs`, telemetry packaging) remains unchanged.
  3. Delete `_build_stage_a_lbfgs_closure` from `dbex/refinement/stage_a_impl.py`, plus any `__all__`/docstring references. The other helpers (`_build_stage_a_params`, `_run_stage_a_lbfgs`, `_compute_panel_loss`, warm-cache utilities) stay put.
  4. Update docstrings/comments that currently mention the helper (e.g., `dbex/refinement/context.py` lines ~420/537) so they describe the new StageA-owned closure.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` for each command.
  1. `mkdir -p plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T040500Z`
  2. `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T040500Z/telemetry_stage_a_small.json pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T040500Z/pytest_stage_a_small.log`

How-To Map:
- New helper lives inside StageA, but you still need `RefinementSharedContext`. Import it lazily (`from dbex.refinement.context import RefinementSharedContext`) inside `StageA.run` or reuse the existing call before building the closure.
- When copying the helper body, keep the lazy imports that live inside the nested functions (`nanobrag_bridge`, `nanobrag_torch`, etc.) and the ROI diagnostics env hook so PERF-WARM-SIM-001 instrumentation keeps working.
- The panel diag collector writes JSON under `DBEX_STAGE_C_PANEL_DIAG_DIR`; ensure the new method respects that env variable and appends to `telemetry_state['panel_loss_diag_a']` exactly as before.
- Re-run the Stage A smoke with the canonical env flags (`KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`, `DBEX_SMOKE_SIGMA_SOURCE=cli_override`, etc.) and store logs/telemetry in the reserved artifacts directory.

Pitfalls To Avoid:
- Do not change `_run_stage_a_lbfgs` or `_compute_panel_loss`; only relocate the closure builder. Any telemetry/ROI behavior changes are out-of-scope.
- Preserve the `shared_context` compatibility shim (legacy dict inputs vs dataclass). If you simplify arguments, document it and ensure no external caller still relies on the legacy path.
- Keep the warm-cache retarget logic intact. `_retarget_stage_a_detectors` and `_retarget_stage_a_simulators` must still be invoked before panel-mode loss calculations.
- Trusted-mask parity (REFINE-016) and the `variance_floor_*` counters must not drift. Verify telemetry diffs only reflect the removal of the helper import.
- Maintain the Stage A perf counters (`cache_mode`, `roi_mode`, `validation_scope`). Engine/tests key off these fields.
- Doc comments (`dbex/refinement/context.py`, `docs/fix_plan.md` references) need to match the new structure; do not leave stale references to `_build_stage_a_lbfgs_closure`.

If Blocked:
- If the nested closure references something that cannot live inside StageA (e.g., circular import with `nanobrag_bridge`), capture the stack trace, note the offending symbol, and stop—log the issue in `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T040500Z/blocked.md` and in galph_memory so we can reassess.
- If the Stage A smoke fails, archive `pytest_stage_a_small.log` and the telemetry JSON in the artifacts directory, annotate the failure signature (selector, error snippet) in docs/fix_plan.md Attempts History, and wait for further guidance.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage closures must stop passing 10–15 positional arguments and mutable dicts; inlining the closure removes the helper clump and keeps context ownership inside StageA.

Pointers:
- dbex/refinement/stage_a_impl.py:1225 — Current `_build_stage_a_lbfgs_closure` body to migrate.
- dbex/refinement/stage_a.py:31-260 — StageA.run orchestrator that will call the new private helper.
- dbex/refinement/context.py:415-575 — Shared context/telemetry dataclasses referencing the Stage A helper; update wording if needed.
- docs/fix_plan.md:86 — Fix-plan entry describing Phase B.2 expectations and artifact path for this loop.
