Summary: Inline Stage B’s parameter builder inside `StageB` so the engine path no longer depends on `stage_b_impl`, and drop the legacy dict input path now that the engine always supplies a `RefinementContext`.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation
Branch: main
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-04T160500Z/
Do Now:
  - Implement: dbex/refinement/stage_b.py::StageB.run — Remove the `hasattr(ctx, 'refinement_inputs')` fallback and require `inputs['context']` (a `RefinementContext`). Raise a clear ValueError if it’s missing so the stage mirrors `RefinementEngine.run`. Update the branch that extracts detector/beam/crystal/inputs so it reads only from the context object.
  - Implement: dbex/refinement/stage_b.py::_build_stage_b_params (new private helper) — Transplant the logic currently in `dbex/refinement/stage_b_impl.py::_build_stage_b_params` so the StageB class builds its params/optimizer/telemetry from `RefinementSharedContext` + Stage A artifacts without routing through `stage_b_impl`. Keep the CPU fallback (GRADIENT-003), ROI sampling, and telemetry collector wiring identical. You can leave the legacy helper in stage_b_impl for now, but StageB must no longer import it.
  - Validate: run the mapped Stage B guard unit and Stage B shell smoketest with canonical env flags, saving `pytest_stage_b_cpu_guard.log` and `pytest_stage_b_shell.log` into the artifacts directory.
How-To Map:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T160500Z/pytest_stage_b_cpu_guard.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T160500Z/pytest_stage_b_shell.log
Pitfalls To Avoid:
  - Do not revert to dict-mutating telemetry writes inside `_check_stage_b_baseline_parity`; collectors own those fields per ARCH-STAGE-CTX-002.
  - Keep the CPU fallback guard (config.stage_b_full_eval_on_cpu + CUDA) identical so gradients still flow on CPU when GRADIENT-003 is triggered.
  - Preserve shell vs per-reflection mode behavior (modifier clamps, optimizer selection, and StageBArtifacts metadata) — Stage C reconstruction depends on those artifacts downstream.
  - Retain the `stage_b_cache_mode`, `stage_b_roi_label`, and sampled index bookkeeping so REFINE-FLOW-001 telemetry still reports cache/ROI mode correctly.
  - Avoid touching Stage C or Stage A logic this loop; only Stage B should change.
  - Environment Freeze: do not introduce new dependencies or edit nanobrag_torch; all work stays under `dbex/refinement` + tests.
If Blocked:
  - Capture failing pytest output plus stack traces into `plans/active/ARCH-REFACTOR-001/reports/2025-12-04T160500Z/blocker.log`, note the blocking signature in docs/fix_plan.md under this initiative, and stop—don’t start redesigning stage_b_impl hookups without a supervisor handoff.
  - If the context requirement breaks an unexpected caller, log the offending stack + inputs and restore the fallback only with my approval; otherwise leave the ValueError so we can trace it next loop.
Findings Applied (Mandatory):
  - docs/findings.md:71 (REFINE-FLOW-001) — Baseline parity guard must remain active when the builder moves; keep JSON emission + telemetry fields intact.
  - docs/findings.md:84 (ARCH-STAGE-CTX-002) — No dict assignment on StageBTelemetryState; all diagnostics flow through the collector helper methods.
  - docs/findings.md:78 (GRADIENT-003) — CPU fallback must keep tensors on CPU-native HKL grids; ensure the inline builder still clones Stage A context when the fallback predicate is true.
Pointers:
  - plans/active/ARCH-REFACTOR-001/implementation.md:90 — Phase C.4 checklist (context strictness + helper move scope).
  - docs/fix_plan.md:52 — ARCH-REFACTOR-001 ledger entry with Attempts History and blocking rules.
  - docs/spec-db-workflow.md:76 — Stage B spec (halo/interpolation requirements and optimizer contract).
  - docs/findings.md:71 — REFINE-FLOW-001 parity guard requirements.
  - docs/findings.md:84 — ARCH-STAGE-CTX-002 telemetry discipline.
Next Up (optional):
  - Port `_run_stage_b_lbfgs` into StageB and relocate the ASU/shell utilities so `stage_b_impl.py` can be retired once the CLI moves to the engine path.
