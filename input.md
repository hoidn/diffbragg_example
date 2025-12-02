Summary: Inline Stage C’s LBFGS closure so `StageC.run` owns the compute/closure helpers, keeps warm-cache/telemetry parity untouched, and retire the legacy helper export.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full (expected +0.067 % chi² regression per PERF-WARM-SIM-001; capture log/telemetry so the signature matches prior loops)
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T063500Z/

Do Now:
- FocusItem: ARCH-STAGE-CONTEXT-001 Phase B.2.3 — Stage C closure inlining.
- Implement: `dbex/refinement/stage_c.py::StageC._build_lbfgs_closure` — copy the current `_build_stage_c_lbfgs_closure` body from `dbex/refinement/stage_c_impl.py` into a private method on `StageC`, keeping the nested `compute_loss_stage_c` / `closure_stage_c` functions, RefinementSharedContext parameters, warm-cache retargeting, trusted-mask parity (REFINE-016), validation-scope guardrails (REFINE-011/012/015), and panel-diagnostics hook intact. Update `StageC.run` to call the new method instead of importing the helper.
- Update: Remove `_build_stage_c_lbfgs_closure` from `dbex/refinement/stage_c_impl.py` (replace with a short comment pointing to `StageC._build_lbfgs_closure`), drop the helper import from `dbex/refinement/stage_c.py`, and clean up any now-unused imports. Leave `_retarget_stage_a_detectors`, `_build_stage_c_params`, and `_run_stage_c_lbfgs` untouched.
- Validate: rerun the Stage C smokes.
  1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md mkdir -p plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T063500Z`
  2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T063500Z/pytest_stage_c_small.log`
  3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T063500Z/pytest_stage_c_full.log` (full-detector run will continue to fail REFINE-007 with the known +0.067 % chi² regression; capture the log/telemetry so the signature matches 2025-12-01 artifacts).

How-To Map:
- Keep the lazy imports that live inside the closure (nanobrag_bridge + nanobrag_torch) to avoid circular imports and preserve warm-cache performance.
- Maintain the `shared_context` compatibility shim: StageC.run will pass the dataclass, but the helper still needs the ValueError guard for any legacy tooling.
- Preserve the env-gated panel diagnostics (`DBEX_STAGE_C_PANEL_DIAG_DIR`) and trusted mask application. The stage_c_impl comment should mirror the Stage B note (“moved to StageC._build_lbfgs_closure”) so future searches land on the class method.
- When running `test_stage_c_detector_microslip`, use the canonical env flags from docs/TESTING_GUIDE (`AUTHORITATIVE_CMDS_DOC`, `KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`, `DBEX_SMOKE_SIGMA_SOURCE=cli_override`, `DBEX_SMOKE_DETECTOR_SIZE` per selector). Archive pytest logs under the reserved artifact directory, even for the known full-detector failure.

Pitfalls To Avoid:
- Do not touch `_build_stage_c_params` or `_run_stage_c_lbfgs`; only relocate the closure builder. Any behavioral change risks violating REFINE-011/012/015/016 instrumentation.
- Keep the warm-cache retargeting path intact (StageAContext simulators must still be rebuilt before panel-mode loss). Dropping the `_retarget_stage_a_detectors` call will break PERF-WARM-SIM-001 evidence.
- Ensure trust-mask gating (REFINE-016) and sigma-floor accumulators remain; removing any of those will desync Stage A vs Stage C chi².
- Avoid inserting `.item()` on tensors that require gradients (distance offsets, orientation/scale tensors). That would detach the graph and break LBFGS.
- Stage C full detector is known to fail due to PERF-WARM-SIM-001; do not relax REFINE-007 thresholds or skip the run. Capture the log/telemetry and reference the existing findings instead.
- Keep the closure’s env var detection (`DBEX_STAGE_C_PANEL_DIAG_DIR`) so panel diagnostics still work; tools under PERF-WARM-SIM-001 depend on that JSON.
- No environment changes — honor the Environment Freeze (record missing deps in docs/fix_plan.md if encountered).

If Blocked:
- If the relocation causes circular-import or missing-symbol errors, stop after capturing the traceback, stash the diff, and write `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T063500Z/blocked.md` with the error + git diff. Link that note in docs/fix_plan.md under the same initiative.
- If the small-detector smoketest regresses, archive the pytest log/telemetry under the artifact dir and flag it in docs/fix_plan.md. For the full-detector run, treat only deviations from the known PERF-WARM-SIM-001 signature as regressions; otherwise document “expected failure” with a pointer to the prior telemetry.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage wrappers must own their LBFGS closures and consume typed refinement contexts; this move eliminates the final helper export.
- REFINE-011 / REFINE-012 — Stage C validations must force panel mode whenever Stage A telemetry reports panel validations; the relocated closure must keep that guard intact.
- REFINE-016 — Trusted-mask parity between Stage A and Stage C ROI closures/panel validations must stay in place so chi² comparisons remain valid.

Pointers:
- dbex/refinement/stage_c_impl.py:386-760 — existing `_build_stage_c_lbfgs_closure` implementation that needs to be transplanted (note panel diagnostics + warm cache retargeting).
- dbex/refinement/stage_c.py:240-520 — StageC.run wiring where the closure is invoked and StageCArtifacts assembled.
- plans/active/ARCH-STAGE-CONTEXT-001/implementation.md:74-87 — Phase B.2 checklist (B2.3) and validation expectations for this loop.
- docs/fix_plan.md (ARCH-STAGE-CONTEXT-001 entry @ 2025-12-02T063500Z) — canonical Do Now + artifact path for this loop.

Next Up (optional):
- Phase B.3 — replace the mutable telemetry dicts with dataclasses after all three closures live on their Stage classes.
