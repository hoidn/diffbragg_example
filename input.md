Summary: Remove `stage_c_impl.py` by moving the warm-cache retarget helper into `StageC` and scrubbing unused imports so Stage C lives entirely under `dbex/refinement/stage_c.py`.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-04T150500Z/
Do Now:
  - Implement: dbex/refinement/stage_c.py::StageC._retarget_stage_a_detectors — Relocate the entire helper (tensor math, PERF-WARM-016 debug hook, ROI simulator refresh, GRADIENT-004 safeguards) into `StageC` as a private helper/method. Update `_build_lbfgs_closure` and `_run_lbfgs` to call the local helper and drop the import from `dbex.refinement.stage_c_impl`. Keep the StageAContext mutations, `distance_deltas_mm` tensor behavior, and `_STAGE_C_CACHE_DEBUG_PATH` semantics unchanged.
  - Implement: dbex/refinement/stage_c.py::StageC.run — Remove the `stage_c_impl` doc references/import at the top of the file, ensure the module docstring states that StageC owns all implementation helpers, and double-check that the warm-cache and final reconstruction loops only call the newly inlined helper (no residual references to the deleted module).
  - Implement: dbex/nanobrag_refinement.py + dbex/refinement/stage_c_impl.py — Drop the unused `_retarget_stage_a_detectors` import/comment in `nanobrag_refinement.py`, then delete `dbex/refinement/stage_c_impl.py` entirely so `rg stage_c_impl` returns no hits. If any tooling/docs still point at the deleted module, update them to reference `dbex/refinement/stage_c.py`.
How-To Map:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T150500Z/pytest_stage_c_smoke.log
Pitfalls To Avoid:
  - Keep the debug hook behavior identical: `_STAGE_C_CACHE_DEBUG_PATH` and `_STAGE_C_RETARGET_CALL_COUNTER` must still gate JSON snapshots; do not log unless the env var is set.
  - Preserve autograd links by keeping `distance_deltas_mm` tensors on-device (`tensor + delta`); never convert offsets to `.item()` or detach when copying into detector configs (GRADIENT-004).
  - StageAContext arrays are mutated in place; ensure `dataclasses.replace` is used when cloning configs so cached detector/simulator references remain consistent with Stage A warm cache rules (PERF-WARM-013).
  - After deleting `stage_c_impl.py`, verify there are no stray imports (run `rg stage_c_impl` or rely on CI); missing this will break imports at module load.
  - Environment Freeze: touch only repo-tracked sources/tests; do not pip install tools to replace the helper.
If Blocked:
  - If another module unexpectedly depends on `stage_c_impl`, stop, capture the offending stack or `rg` results into `plans/active/ARCH-REFACTOR-001/reports/2025-12-04T150500Z/blocker.md`, and ping me before introducing new public helpers.
  - If Stage C smoke diverges (telemetry or chi² drift), archive the pytest log plus any extra diagnostics in the artifacts directory and log the regression in docs/fix_plan.md so we can reassess Phase C.3 scope.
Findings Applied (Mandatory):
  - ARCH-STAGE-CTX-001 — Stage helpers must consume typed contexts/dataclasses instead of mutable dicts; moving the retarget helper into `StageC` keeps the data clump localized.
  - GRADIENT-004 — Detector retargeting must keep distance offsets as tensors so Stage C gradients remain valid; the moved helper must preserve that behavior.
  - REFINE-012 — Stage C ROI/panel validation semantics rely on matching Stage A detector state; the helper move cannot change when panel vs ROI caches are retargeted.
Pointers:
  - dbex/refinement/stage_c.py:34 — Current import list/docstring still references `stage_c_impl`.
  - dbex/refinement/stage_c.py:300 & 1005 — Warm-cache and reconstruction loops that call `_retarget_stage_a_detectors`.
  - dbex/refinement/stage_c_impl.py:1 — Helper to move; delete this file after transplanting into StageC.
Next Up (optional):
  - Once Stage C owns the retarget helper, Phase C.4 begins Stage B strictness/inlining so `stage_b_impl.py` can be retired.
