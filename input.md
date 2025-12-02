Summary: Inline the Stage C parameter/optimizer helpers into `StageC` so the class owns its LBFGS wiring instead of calling `stage_c_impl`.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-04T140000Z/
Do Now:
  - Implement: dbex/refinement/stage_c.py::StageC._build_stage_c_params — Move the body of `_build_stage_c_params` out of `stage_c_impl.py` into a private helper (or folded into `StageC.run`) that constructs `distance_offset_raw`, `stage_c_optimizer`, the ROI metadata, `StageCContext`, and the `StageCTelemetryState`. The helper should accept the existing `RefinementSharedContext`, `StageAContext`, Stage A telemetry, and sampled panel IDs instead of dozens of optional kwargs, and return the typed context + telemetry dataclasses alongside the `param_values` dict that `_build_lbfgs_closure` consumes. Remove the import of `_build_stage_c_params` and update `StageC.run` to unpack the tuple from the new helper instead of the old dict-of-lists plumbing.
  - Implement: dbex/refinement/stage_c.py::StageC._run_lbfgs — Port the entirety of `_run_stage_c_lbfgs` into a new private method that takes `compute_loss_stage_c`, `closure_stage_c`, `StageCContext`, the collector, telemetry dataclass, and the canonical `param_values`. This helper should return `(stage_result, refinement_telemetry, status, message, bragg_full_stage_c, param_deltas)` so `StageC.run` can reuse the output when building artifacts. Keep the observer/collector sequencing identical (baseline validation, LBFGS step, fallback seeding, final validation) and ensure `_retarget_stage_a_detectors` is still called for warm-cache reconstructions.
  - Implement: dbex/refinement/stage_c_impl.py — Delete `_build_stage_c_params` and `_run_stage_c_lbfgs` from this module now that their logic lives on the class, leaving `_retarget_stage_a_detectors` (and any supporting imports) as the only helper until Phase C3 removes the file entirely. Trim unused imports/constants and update module docstrings accordingly.
How-To Map:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T140000Z/pytest_stage_b_guard.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T140000Z/pytest_stage_c_smoke.log
Pitfalls To Avoid:
  - Do not reintroduce dict-based `stage_c_context` plumbing; the typed `StageCContext` and `StageCTelemetryState` must remain the sole carriers of Stage C metadata (ARCH-STAGE-CTX-001).
  - Keep `_build_lbfgs_closure` signature narrowed to contexts/param dicts only; avoid adding new optional legacy parameters even temporarily.
  - Preserve Stage C observer sequencing: baseline validation, collector-driven LBFGS step, fallback sample seeding, final validation, and `StageResult` finalization must all happen in the same order so telemetry stays spec-compliant (ARCH-TELEMETRY-001).
  - Maintain ROI/panel validation semantics (`force_panel_validation`, `validation_scope`, ROI counts) exactly; these feed REFINE-007/REFINE-012 gates and the Stage C smoke selector.
  - Environment Freeze: touch only repo-tracked python modules/tests; no pip installs or new third-party scripts.
  - When removing helpers from `stage_c_impl.py`, ensure no other module imports them; update the module docstring/import list to avoid unused dependencies.
If Blocked:
  - If StageC cannot build its parameters without additional shared context data, stop and capture the failing stack trace plus any intermediate dataclasses to `plans/active/ARCH-REFACTOR-001/reports/2025-12-04T140000Z/blocker.md` and ping me before widening scope.
  - If LBFGS telemetry diverges (e.g., empty `loss_trace_sample` or different status), archive the pytest log + `collector` dump in the same artifacts directory and note the regression in docs/fix_plan.md so we can reassess Phase C2.
Findings Applied (Mandatory):
  - ARCH-STAGE-CTX-001 — Stage helpers must consume typed contexts/telemetry instead of 11-parameter dicts; the new helpers must keep everything on dataclasses.
  - ARCH-ENGINE-002 — Stage wrappers remain the canonical engine seam; refactors cannot change the StageResult/telemetry schema that downstream consumers expect.
  - ARCH-TELEMETRY-001 — Observer-driven telemetry collection stays the source of truth; collector.finalize() + `StageResult.to_legacy_dict()` must remain untouched when moving the helper logic.
Pointers:
  - dbex/refinement/stage_c.py:650 — Current `StageC.run` path that still imports `_build_stage_c_params`/`_run_stage_c_lbfgs` and unpacks dicts.
  - dbex/refinement/stage_c_impl.py:224 — Legacy helper bodies being inlined; use these definitions as the source when creating the new private methods.
Next Up (optional):
  - Once StageC stops importing `stage_c_impl`, move `_retarget_stage_a_detectors` in-house and delete the module (Phase C3).
